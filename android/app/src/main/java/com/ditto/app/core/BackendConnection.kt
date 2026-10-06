package com.ditto.app.core

import android.content.Context
import com.ditto.app.BuildConfig
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class ServerSession(val userId: String, val token: String, val expiresAt: Long, val endpoint: String)

/** Only endpoint/mode are plain preferences; server tokens use the Android Keystore vault. */
class BackendConnection(private val context: Context) {
    private val prefs=context.getSharedPreferences("backend_connection",0)
    private val vault=LocalAccounts(context)
    fun enabled()=prefs.getBoolean("enabled",false)
    fun endpoint()=prefs.getString("endpoint","") ?: ""
    fun configure(enabled: Boolean, value: String) {
        val normalized=if(enabled) normalize(value) else endpoint()
        if(normalized!=endpoint() || enabled!=enabled()) vault.removeSecret("backend_session")
        prefs.edit().putBoolean("enabled",enabled).putString("endpoint",normalized).commit()
    }
    fun session(): ServerSession? = runCatching {
        val data=JSONObject(vault.secret("backend_session") ?: return null)
        val expires=data.getLong("expires")
        if(expires<=System.currentTimeMillis() || data.getString("endpoint")!=endpoint()) return null
        ServerSession(data.getString("user"),data.getString("token"),expires,endpoint())
    }.getOrNull()
    fun authenticate(email: String,password: String,signup: Boolean): String {
        val data=JSONObject(BackendApi(endpoint(),null).request("api/auth/${if(signup) "signup" else "login"}",JSONObject().put("email",email.trim()).put("password",password).toString()))
        val id=data.getJSONObject("user").getString("id")
        val expires=java.time.OffsetDateTime.parse(data.getString("expiresAt")).toInstant().toEpochMilli()
        vault.saveSecret("backend_session",JSONObject().put("user",id).put("token",data.getString("token")).put("expires",expires).put("endpoint",endpoint()).toString())
        return id
    }
    fun logout() {
        vault.removeSecret("backend_session")
        // Remote revocation is attempted by the caller before local cleanup.
    }
    companion object {
        fun normalize(value: String): String {
            val url=value.trim().toHttpUrlOrNull()
                ?: error("Enter a valid backend URL.")
            val local=url.host in listOf("10.0.2.2","127.0.0.1","localhost")
            require(url.scheme=="https" || (BuildConfig.DEBUG && local)) { "Use an HTTPS backend URL." }
            require(url.username.isEmpty() && url.password.isEmpty() && url.query==null && url.fragment==null && url.encodedPath=="/") { "Paste the backend root URL, without credentials or /api paths." }
            return url.toString()
        }
    }
}

class BackendApi(val endpoint: String, private val token: String?) {
    private val client=OkHttpClient.Builder().connectTimeout(15,TimeUnit.SECONDS).readTimeout(120,TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false).build()
    fun supportsChunkedUpload(): Boolean = JSONObject(request("api/health")).optJSONObject("capabilities")?.optString("uploadProtocol") == "chunked-appwrite-v1"
    suspend fun awaitResult(path: String, json: String?=null, body: RequestBody?=null): String {
        val response=request(path,json,body)
        val queued=runCatching { JSONObject(response) }.getOrNull()
        val jobId=queued?.optString("jobId")?.takeIf { it.isNotBlank() } ?: return response
        return awaitJob(jobId)
    }
    suspend fun awaitJob(jobId: String): String {
        require(jobId.matches(Regex("[a-zA-Z0-9._-]{1,36}"))) { "Invalid processing receipt." }
        repeat(160) {
            kotlinx.coroutines.delay(1500)
            val job=JSONObject(request("api/jobs/$jobId"))
            when(job.getString("state")) {
                "complete" -> return job.get("result").toString()
                "error","unknown","cancelled" -> error(job.optString("error").ifBlank { "Processing stopped. Check its status before submitting again." })
            }
        }
        error("Still processing. Job $jobId is saved; refresh later before submitting again.")
    }
    suspend fun uploadMedia(bytes: ByteArray, mime: String, title: String, source: String, originalId: String?=null): String {
        require(bytes.isNotEmpty() && bytes.size<=20_000_000) { "Media must be 20 MB or smaller." }
        val sha=java.security.MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
        val start=JSONObject(request("api/content/uploads/start",JSONObject().put("title",title)
            .put("content_type",mime).put("size",bytes.size).put("sha256",sha).put("source",source)
            .put("purpose",if(originalId==null) "original" else "candidate").put("original_id",originalId ?: "").toString()))
        val id=start.getString("id")
        require(id.matches(Regex("[a-zA-Z0-9._-]{1,36}"))) { "Invalid upload receipt." }
        val chunk=start.getInt("chunkBytes")
        require(chunk==5_000_000) { "Unsupported chunk size." }
        var offset=start.getInt("uploadedBytes")
        while(offset<bytes.size) {
            kotlinx.coroutines.delay(1)
            val part=bytes.copyOfRange(offset,minOf(offset+chunk,bytes.size))
            val receipt=JSONObject(request("api/content/uploads/$id/chunks?offset=$offset",body=part.toRequestBody("application/octet-stream".toMediaType())))
            val next=receipt.getInt("uploadedBytes")
            require(next==offset+part.size) { "Unexpected upload progress; check upload status." }
            offset=next
        }
        return awaitResult("api/content/uploads/$id/complete","{}")
    }
    fun download(path: String, destination: java.io.File): java.io.File {
        if(destination.isFile) return destination
        val request=Request.Builder().url(endpoint+path).apply { if(token!=null) header("Authorization","Bearer $token") }.build()
        client.newCall(request).execute().use { response ->
            require(response.isSuccessful) { "Private media unavailable (${response.code})." }
            val body=response.body ?: error("Media unavailable.")
            require(body.contentLength()<=25*1024*1024) { "Media exceeds the download limit." }
            destination.parentFile?.mkdirs()
            val temporary=java.io.File(destination.path+".part")
            try {
                body.byteStream().use { input -> temporary.outputStream().use { output ->
                    val buffer=ByteArray(8192);var total=0
                    while(true) { val n=input.read(buffer);if(n<0)break;total+=n;require(total<=25*1024*1024) { "Media exceeds the download limit." };output.write(buffer,0,n) }
                } }
                require(temporary.renameTo(destination)) { "Could not save private media." }
            } finally { temporary.delete() }
            return destination
        }
    }
    fun request(path: String, json: String?=null, body: RequestBody?=null): String {
        val request=Request.Builder().url(endpoint+path).apply {
            if(token!=null) header("Authorization","Bearer $token")
            if(body!=null) post(body) else if(json!=null) post(json.toRequestBody("application/json".toMediaType()))
        }.build()
        client.newCall(request).execute().use { response ->
            val text=response.body?.string() ?: ""
            if(!response.isSuccessful) {
                if(response.code in 300..399) error("The backend redirected the request. Check the configured service address or contact support.")
                if(response.code==401) error("Server session expired. Log out and sign in again.")
                val detail=runCatching { JSONObject(text).optString("detail") }.getOrDefault("")
                error(if(detail.isNotBlank() && detail.length<500) detail else "Backend request failed (${response.code}).")
            }
            return text
        }
    }
}
