package com.ditto.app.core

import android.content.Context
import com.ditto.app.BuildConfig
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLException

data class ServerSession(val userId: String, val token: String, val expiresAt: Long, val endpoint: String)

class BackendRequestException(message: String, cause: Throwable? = null, val status: Int? = null) : IllegalStateException(message, cause)

/** A timeout response can arrive while a submitted operation is still running. */
internal fun isDefiniteBackendRejection(failure: Throwable): Boolean =
    (failure as? BackendRequestException)?.status?.let {it in 400..499 && it != 408} == true

/** Network diagnostics belong in logs, never in a customer-facing error. */
internal fun backendFailureMessage(path: String, failure: Throwable, mutation: Boolean = false): String {
    if (failure is BackendRequestException) return failure.message ?: "Ditto could not complete this request."
    val causes = generateSequence(failure) { it.cause }.take(8).toList()
    val networkFailure = causes.firstOrNull { it is IOException }
    if (networkFailure != null) {
        val route = path.substringBefore('?')
        if (networkFailure is SSLException) {
            return "Ditto could not establish a secure connection. Try again shortly or contact support."
        }
        if (mutation && networkFailure !is UnknownHostException && networkFailure !is ConnectException) {
            return when {
                route.endsWith("/web-search-job") -> "Search status could not be confirmed. Reopen your original to check before searching again."
                route.contains("compare") || route == "api/scan" -> "Comparison status could not be confirmed. Check your activity before submitting again."
                route.startsWith("api/content") -> "Upload status could not be confirmed. Check your originals before uploading again."
                route == "api/auth/signup" -> "Account creation could not be confirmed. Try signing in before creating it again."
                route == "api/auth/refresh" -> "Your session could not reconnect. Check your connection and try again."
                route == "api/auth/login" -> "Cannot reach Ditto to sign in. Check your connection and try again."
                else -> "The action could not be confirmed. Check its saved status before trying again."
            }
        }
        return when {
            route == "api/auth/login" -> "Cannot reach Ditto to sign in. Check your connection and try again."
            route == "api/auth/signup" -> "Cannot reach Ditto to create your account. Check your connection and try again."
            route == "api/auth/refresh" -> "Your session could not reconnect. Check your connection and try again."
            networkFailure is SocketTimeoutException -> "Ditto is taking longer to respond. Check your connection; we will reconnect automatically."
            route.contains("/media") -> "Cannot download this media yet. Check your connection and try again."
            else -> "Cannot reach Ditto. Check your internet connection; we will reconnect automatically."
        }
    }
    if (failure is org.json.JSONException) return "Ditto returned an unreadable response. Try again shortly."
    return failure.message?.takeIf { it.isNotBlank() && it.length <= 240 }
        ?: "Ditto could not complete this request. Try again."
}

internal fun canRetryBackendRequest(method: String, failure: IOException): Boolean =
    method == "GET" && failure !is SSLException && failure !is java.io.FileNotFoundException

internal fun backendErrorMessage(path: String, status: Int, responseBody: String): String {
    if (status in 300..399) {
        return "The service redirected the request. Contact Ditto support."
    }
    if (status == 401 && path == "api/auth/login") {
        return "Email or password is incorrect."
    }
    val detail = runCatching { JSONObject(responseBody).opt("detail") }.getOrNull()
    val parsedMessage = when (detail) {
        is String -> detail
        is JSONArray -> detail.optJSONObject(0)?.optString("msg").orEmpty()
        else -> ""
    }.trim()
    // Local JVM tests use Android's stub JSONObject, so retain a narrow fallback
    // for the two simple error fields returned by FastAPI/Pydantic.
    val serverMessage = parsedMessage.ifBlank {
        Regex("\\\"(?:msg|detail)\\\"\\s*:\\s*\\\"([^\\\"]{1,240})\\\"")
            .find(responseBody)?.groupValues?.get(1).orEmpty()
    }
    val normalized = serverMessage.lowercase()
    return when {
        "at least 10 characters" in normalized -> "Password must be at least 10 characters."
        "valid email" in normalized || "email address" in normalized -> "Enter a valid email address."
        status == 401 && "password" in normalized -> "Password is incorrect."
        status == 401 -> "Your session expired. Log in again."
        serverMessage.isNotBlank() && serverMessage.length <= 240 &&
            '{' !in serverMessage && '[' !in serverMessage -> serverMessage
        status >= 500 -> "Ditto is temporarily unavailable. Try again shortly."
        else -> "Request could not be completed. Try again."
    }
}

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
        if(data.getString("endpoint")!=endpoint()) return null
        if(expires<=System.currentTimeMillis() && data.optLong("refreshExpires",0)<=System.currentTimeMillis()) return null
        ServerSession(data.getString("user"),data.getString("token"),expires,endpoint())
    }.getOrNull()
    fun authenticate(email: String,password: String,signup: Boolean): String {
        val data=JSONObject(BackendApi(endpoint(),null).request("api/auth/${if(signup) "signup" else "login"}",JSONObject().put("email",email.trim()).put("password",password).toString()))
        val id=data.getJSONObject("user").getString("id")
        val expires=java.time.OffsetDateTime.parse(data.getString("expiresAt")).toInstant().toEpochMilli()
        saveSession(data, id, expires)
        return id
    }
    private fun saveSession(data: JSONObject, id: String, expires: Long) {
        val stored=JSONObject().put("user",id).put("token",data.getString("token"))
            .put("expires",expires).put("endpoint",endpoint())
        if(data.has("refreshToken")) {
            stored.put("refreshToken",data.getString("refreshToken"))
            stored.put("refreshExpires",java.time.OffsetDateTime.parse(data.getString("refreshExpiresAt")).toInstant().toEpochMilli())
        }
        vault.saveSecret("backend_session",stored.toString())
    }
    /** Called on the request's IO thread; mutations are never retried automatically. */
    fun accessToken(expectedUser: String): String = synchronized(refreshLock) {
        val current=session() ?: error("Please sign in again.")
        require(current.userId==expectedUser) { "Account changed. Refresh this screen." }
        if(current.expiresAt > System.currentTimeMillis()+30_000) return@synchronized current.token
        val stored=JSONObject(vault.secret("backend_session") ?: error("Please sign in again."))
        val refresh=stored.optString("refreshToken")
        require(refresh.isNotBlank()) { "Please sign in again." }
        val data=JSONObject(BackendApi(endpoint(),null).request("api/auth/refresh",JSONObject().put("refreshToken",refresh).toString()))
        val id=data.getJSONObject("user").getString("id")
        require(id==expectedUser) { "Unexpected account in session response." }
        val expires=java.time.OffsetDateTime.parse(data.getString("expiresAt")).toInstant().toEpochMilli()
        saveSession(data,id,expires)
        data.getString("token")
    }
    fun logout() = synchronized(refreshLock) {
        vault.removeSecret("backend_session")
        // Remote revocation is attempted by the caller before local cleanup.
    }
    companion object {
        private val refreshLock=Any()
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

class BackendApi(val endpoint: String, private val token: String?, private val tokenProvider: (() -> String)? = null) {
    private val client=OkHttpClient.Builder().connectTimeout(15,TimeUnit.SECONDS).readTimeout(120,TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false)
        // POSTs can submit uploads, rotate sessions or enqueue a search. Only
        // explicitly retried GETs may be replayed after a connection failure.
        .retryOnConnectionFailure(false).build()
    private fun <T> execute(request: Request, path: String, read: (Response) -> T): T {
        var attempt=0
        while(true) {
            try {
                return client.newCall(request).execute().use(read)
            } catch(failure: IOException) {
                if(attempt==0 && canRetryBackendRequest(request.method,failure)) {
                    attempt++
                    continue
                }
                throw BackendRequestException(backendFailureMessage(path,failure,request.method!="GET"),failure)
            }
        }
    }
    fun supportsChunkedUpload(): Boolean = JSONObject(request("api/health")).optJSONObject("capabilities")?.optString("uploadProtocol") == "chunked-appwrite-v1"
    suspend fun awaitResult(path: String, json: String?=null, body: RequestBody?=null): String {
        val response=request(path,json,body)
        val queued=runCatching { JSONObject(response) }.getOrNull()
        val jobId=queued?.optString("jobId")?.takeIf { it.isNotBlank() } ?: return response
        return awaitJob(jobId)
    }
    suspend fun awaitJob(jobId: String): String {
        require(jobId.matches(Regex("[a-zA-Z0-9._-]{1,36}"))) { "Invalid processing receipt." }
        repeat(600) {
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
        val request=Request.Builder().url(endpoint+path).apply { if(token!=null) header("Authorization","Bearer ${tokenProvider?.invoke() ?: token}") }.build()
        return execute(request,path) { response ->
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
            destination
        }
    }
    fun request(path: String, json: String?=null, body: RequestBody?=null): String {
        val request=Request.Builder().url(endpoint+path).apply {
            if(token!=null) header("Authorization","Bearer ${tokenProvider?.invoke() ?: token}")
            if(body!=null) post(body) else if(json!=null) post(json.toRequestBody("application/json".toMediaType()))
        }.build()
        return execute(request,path) { response ->
            val text=response.body?.string() ?: ""
            if(!response.isSuccessful) {
                throw BackendRequestException(backendErrorMessage(path, response.code, text),status=response.code)
            }
            text
        }
    }
}
