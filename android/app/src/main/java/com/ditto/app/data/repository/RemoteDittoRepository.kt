package com.ditto.app.data.repository

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.Uri
import com.ditto.app.core.*
import com.ditto.app.domain.model.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.*
import java.time.*

/** Server owns all mutations. Snapshot data is memory-only and cleared at logout. */
class RemoteDittoRepository(private val context: Context, private val session: ServerSession): DittoRepository {
    private val api=BackendApi(session.endpoint,session.token) { com.ditto.app.core.BackendConnection(context).accessToken(session.userId) }
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private val mutex=Mutex()
    private val cases=MutableStateFlow<List<Case>>(emptyList())
    private val activity=MutableStateFlow<List<ActivityEvent>>(emptyList())
    private val content=MutableStateFlow<List<ContentItem>>(emptyList())
    private val emptyStats=DashboardStats(0,0,0,0,0,0,0,0,0,0.0,0.0)
    private val stats=MutableStateFlow(emptyStats)
    val connectionError=MutableStateFlow<String?>(null)
    private val publicationLock=Any()
    @Volatile private var closed=false
    private val connectivity=context.applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
    private var callbackRegistered=false
    private var connectedNetwork: Network?=null
    private val networkCallback=object: ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
            if(closed) return
            val validated=capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            if(!validated && connectedNetwork==network) {
                connectedNetwork=null
                publishIfOpen {connectionError.value="Connection paused. We will reconnect automatically."}
            } else if(validated && connectedNetwork!=network) {
                connectedNetwork=network
                scope.launch { refreshSafely() }
            }
        }
        override fun onLost(network: Network) {
            if(closed) return
            if(connectedNetwork==network) {
                connectedNetwork=null
                publishIfOpen {connectionError.value="Connection paused. We will reconnect automatically."}
            }
        }
    }
    private fun publishIfOpen(block: () -> Unit) = synchronized(publicationLock) {
        if(!closed) block()
    }
    init {
        callbackRegistered=runCatching {connectivity?.registerDefaultNetworkCallback(networkCallback);connectivity!=null}.getOrDefault(false)
        scope.launch { while(isActive) { refreshSafely(); delay(15000) } }
    }
    private suspend fun refreshSafely() {
        try {refresh()}
        catch(e:CancellationException) {throw e}
        catch(e:Exception) {publishIfOpen {connectionError.value=backendFailureMessage("api/dashboard",e)}}
    }
    fun close() {
        // Refresh may have been launched by a screen's external coroutine. Its
        // blocking HTTP response must not restore an account snapshot at logout.
        synchronized(publicationLock) {
            closed=true
            cases.value=emptyList();activity.value=emptyList();content.value=emptyList()
            stats.value=emptyStats;connectionError.value=null
        }
        if(callbackRegistered) runCatching {connectivity?.unregisterNetworkCallback(networkCallback)}
        callbackRegistered=false
        scope.cancel()
    }
    override val verificationEngineName="Review ownership and permission before acting"
    override val discoveryProviderName="Submitted media comparison and configured web search; no platform-wide Instagram search"
    override val matcherName="Visual similarity analysis"
    override fun observeCases(): Flow<List<Case>> = cases
    override fun observeCase(id:String): Flow<Case?> = cases.map { rows-> rows.firstOrNull { it.id==id } }
    override fun observeActivity(): Flow<List<ActivityEvent>> = activity
    override fun observeContent(): Flow<List<ContentItem>> = content
    override fun observeStats(): Flow<DashboardStats> = stats
    suspend fun refresh() = mutex.withLock {
        if(closed) return@withLock
        // Publish a complete snapshot only after every request succeeds.
        val nextCases=JSONArray(api.request("api/cases")).objects().map(::caseFrom)
        val mediaScope=java.security.MessageDigest.getInstance("SHA-256").digest((session.endpoint+session.userId).toByteArray()).joinToString("") { "%02x".format(it) }
        val nextContent=JSONArray(api.request("api/content")).objects().map(::contentFrom).map { item ->
            val name=java.security.MessageDigest.getInstance("SHA-256").digest(item.id.toByteArray()).joinToString("") { "%02x".format(it) }
            val file=java.io.File(context.cacheDir,"server-media/$mediaScope/$name.${if(item.kind==ContentKind.VIDEO) "mp4" else "image"}")
            runCatching { item.copy(localUri=Uri.fromFile(api.download("api/content/${item.id}/media",file)).toString()) }.getOrDefault(item)
        }
        val nextActivity=JSONArray(api.request("api/activity")).objects().map { ActivityEvent(it.getLong("id"),it.time("timestamp"),AgentKind.from(it.getString("agent")),it.getString("title"),it.getString("detail"),it.nullString("caseId")) }
        val s=JSONObject(api.request("api/dashboard/stats"))
        val nextStats=DashboardStats(s.getInt("contentMonitored"),s.getInt("openCases"),s.getInt("awaitingResponse"),s.getInt("resolved"),s.getInt("escalated"),s.getInt("pendingApproval"),s.getInt("totalCases"),s.getInt("verifiedReposts"),s.getInt("falsePositives"),s.getDouble("averageConfidence"),s.getDouble("resolutionRate"))
        publishIfOpen {
            cases.value=nextCases; content.value=nextContent; activity.value=nextActivity
            stats.value=nextStats;connectionError.value=null
        }
    }
    private suspend fun <T> result(path: String, block: suspend ()->T): DittoResult<T> = withContext(Dispatchers.IO) {
        try { DittoResult.Ok(block()) } catch(e:CancellationException) { throw e } catch(e:Exception) { DittoResult.Err(backendFailureMessage(path,e,mutation=true)) }
    }
    private suspend fun refreshAfterAction(message: String) {
        try {refresh()}
        catch(e:CancellationException) {throw e}
        catch(e:Exception) {publishIfOpen {connectionError.value=message}}
    }
    override suspend fun ingest(title:String,uri:String?,isVideo:Boolean,source:String): DittoResult<ContentItem> = result("api/content/upload") {
        require(uri!=null) { "Choose a media file." }
        val parsed=Uri.parse(uri)
        val mime=context.contentResolver.getType(parsed) ?: if(isVideo) "video/mp4" else "image/jpeg"
        val bytes=context.contentResolver.openInputStream(parsed)?.use { input ->
            val out=java.io.ByteArrayOutputStream();val buffer=ByteArray(8192);var total=0
            while(true) { val n=input.read(buffer);if(n<0) break;total+=n;require(total<=20_000_000) { "Uploads must be 20 MB or smaller." };out.write(buffer,0,n) }
            out.toByteArray()
        } ?: error("Cannot read selected media.")
        require(bytes.size<=20_000_000) { "Uploads must be 20 MB or smaller." }
        val response=if(api.supportsChunkedUpload()) api.uploadMedia(bytes,mime,title,source) else {
            val body=MultipartBody.Builder().setType(MultipartBody.FORM).addFormDataPart("file",if(isVideo) "original.mp4" else "original.image",bytes.toRequestBody(mime.toMediaType())).build()
            val q=java.net.URLEncoder.encode(title,"UTF-8")+"&source="+java.net.URLEncoder.encode(source,"UTF-8")
            api.request("api/content/upload?title=$q",body=body)
        }
        val item=contentFrom(JSONObject(response))
        // An accepted upload remains successful when the following read fails.
        publishIfOpen {content.value=listOf(item)+content.value.filterNot {it.id==item.id}}
        refreshAfterAction("Original uploaded. Reconnecting to update your library.")
        content.value.firstOrNull { it.id==item.id } ?: item
    }
    override fun scan(contentId:String): Flow<DittoResult<ScanProgress>> = flow {
        emit(DittoResult.Ok(ScanProgress(ScanStage.INGESTING,"Submitting your original to the backend.")))
        val r=result("api/scan") {
            val rows=JSONArray(api.request("api/scan",JSONObject().put("contentId",contentId).toString())).objects().map(::caseFrom)
            publishIfOpen {cases.value=rows+cases.value.filterNot {existing->rows.any {it.id==existing.id}}}
            refreshAfterAction("Comparison saved. Reconnecting to update your activity.")
            ScanProgress(ScanStage.DONE,"Comparison complete. Review the evidence.",rows.size,rows.map { it.id })
        }
        emit(r)
    }.flowOn(Dispatchers.IO)
    private suspend fun mutate(id:String,action:String,body:JSONObject): DittoResult<Case> = result("api/cases/$id/$action") {
        val c=caseFrom(JSONObject(api.request("api/cases/$id/$action",body.toString())))
        // Mutation receipt is authoritative even when a later snapshot refresh fails.
        publishIfOpen {cases.value=listOf(c)+cases.value.filterNot { it.id==c.id }}
        refreshAfterAction("Action saved. Reconnecting to update your dashboard.")
        c
    }
    override suspend fun approve(caseId:String,editedBody:String?,tone:MessageTone?)=mutate(caseId,"approve",JSONObject().put("editedBody",editedBody).put("tone",tone?.wire))
    override suspend fun reject(caseId:String,note:String?)=mutate(caseId,"reject",JSONObject().put("note",note))
    override suspend fun saveDraft(caseId:String,body:String,tone:MessageTone)=mutate(caseId,"edit-action",JSONObject().put("body",body).put("tone",tone.wire))
    override suspend fun runFollowUp(caseId:String,outcome:FollowUpOutcome)=mutate(caseId,"simulate-followup",JSONObject().put("outcome",outcome.wire))
    override suspend fun resolve(caseId:String,note:String?)=mutate(caseId,"resolve",JSONObject().put("note",note))
    override suspend fun casesAwaitingFollowUp()=cases.value.filter { it.state==CaseState.AWAITING_RESPONSE }

}

private fun JSONArray.objects()=(0 until length()).map { getJSONObject(it) }
private fun JSONObject.nullString(key:String)=if(isNull(key)) null else optString(key).takeIf { it.isNotEmpty() }
private fun JSONObject.strings(key:String)=(optJSONArray(key) ?: JSONArray()).let { a->(0 until a.length()).map { a.getString(it) } }
private fun JSONObject.time(key:String): Long {
    val text=getString(key)
    return runCatching { OffsetDateTime.parse(text).toInstant().toEpochMilli() }.getOrElse { LocalDateTime.parse(text).toInstant(ZoneOffset.UTC).toEpochMilli() }
}
private fun JSONObject.optionalTime(key:String)=if(isNull(key)) null else time(key)
private fun contentFrom(j:JSONObject)=ContentItem(j.getString("id"),j.getString("title"),ContentKind.from(j.getString("kind")),null,j.getString("perceptualHash"),j.getInt("paletteSeed"),j.time("publishedAt"),j.time("publishedAt"),j.getString("sourcePlatform"))
private fun caseFrom(j:JSONObject): Case {
    val id=j.getString("id");val contentId=j.getString("contentId");val c=j.getJSONObject("candidate")
    val candidate=CandidateMatch(c.getString("id"),contentId,c.getString("platform"),c.getString("accountName"),c.getString("accountHandle"),c.getString("sourceUrl"),c.getString("caption"),c.getInt("followerCount"),c.getBoolean("monetized"),c.getDouble("hashSimilarity"),c.getDouble("visualSimilarity"),c.getDouble("captionSimilarity"),c.getDouble("faceSimilarity"),c.time("postedAt"),c.getString("transformNote"),c.getInt("paletteSeed"),c.time("discoveredAt"),c.optBoolean("attributionPresent"),c.optBoolean("permissionGranted"))
    val severity=Severity.from(j.optString("severity"))
    val verification=j.nullString("classification")?.let { VerificationResult(Classification.from(it),j.optDouble("confidence",0.0),severity,j.optString("verificationSummary"),(j.optJSONArray("verificationSignals") ?: JSONArray()).objects().map { s->Signal(s.getString("name"),s.getString("value"),s.getBoolean("supportsMatch")) },j.optString("evidenceSummary"),j.optString("verificationEngine")) }
    val plan=j.nullString("recommendedAction")?.let { ActionPlan(ActionType.from(it),severity,j.optString("actionReasoning"),j.strings("actionFactors"),j.optString("draftSubject"),j.optString("draftBody"),MessageTone.from(j.optString("tone")),j.optString("planEngine")) }
    val history=(j.optJSONArray("history") ?: JSONArray()).objects().map { h->CaseHistoryEntry(caseId=id,timestamp=h.time("timestamp"),previousState=h.nullString("previousState")?.let(CaseState::from),newState=h.nullString("newState")?.let(CaseState::from),agent=AgentKind.from(h.getString("agent")),action=h.getString("action"),reasoning=h.getString("reasoning")) }
    return Case(id,contentId,j.getString("contentTitle"),j.getInt("contentPaletteSeed"),candidate,verification,plan,CaseState.from(j.getString("currentState")),j.getInt("escalationLevel"),j.getInt("followUpCount"),j.time("createdAt"),j.time("updatedAt"),j.optionalTime("nextFollowUpAt"),j.optionalTime("lastActionAt"),history)
}
