package com.ditto.app.data.repository

import android.content.Context
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
    private val api=BackendApi(session.endpoint,session.token)
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private val mutex=Mutex()
    private val cases=MutableStateFlow<List<Case>>(emptyList())
    private val activity=MutableStateFlow<List<ActivityEvent>>(emptyList())
    private val content=MutableStateFlow<List<ContentItem>>(emptyList())
    private val stats=MutableStateFlow(DashboardStats(0,0,0,0,0,0,0,0,0,0.0,0.0))
    val connectionError=MutableStateFlow<String?>(null)
    init { scope.launch { while(isActive) { try { refresh() } catch(e:CancellationException) { throw e } catch(e:Exception) { connectionError.value=e.message ?: "Backend unavailable" }; delay(15000) } } }
    fun close() { scope.cancel(); cases.value=emptyList();activity.value=emptyList();content.value=emptyList() }
    override val verificationEngineName="Server rule-based verifier (no live LLM)"
    override val discoveryProviderName="Server synthetic corpus; live platform discovery unavailable"
    override val matcherName="Server measured five-frame pHash"
    override fun observeCases(): Flow<List<Case>> = cases
    override fun observeCase(id:String): Flow<Case?> = cases.map { rows-> rows.firstOrNull { it.id==id } }
    override fun observeActivity(): Flow<List<ActivityEvent>> = activity
    override fun observeContent(): Flow<List<ContentItem>> = content
    override fun observeStats(): Flow<DashboardStats> = stats
    suspend fun refresh() = mutex.withLock {
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
        cases.value=nextCases; content.value=nextContent; activity.value=nextActivity; stats.value=nextStats;connectionError.value=null
    }
    private suspend fun <T> result(block: suspend ()->T): DittoResult<T> = withContext(Dispatchers.IO) {
        try { DittoResult.Ok(block()) } catch(e:CancellationException) { throw e } catch(e:Exception) { DittoResult.Err(e.message ?: "Cannot reach backend. Resume the Codespace and check its public test port.") }
    }
    override suspend fun ingest(title:String,uri:String?,isVideo:Boolean,source:String): DittoResult<ContentItem> = result {
        require(uri!=null) { "Choose a media file." }
        val parsed=Uri.parse(uri)
        val mime=context.contentResolver.getType(parsed) ?: if(isVideo) "video/mp4" else "image/jpeg"
        val bytes=context.contentResolver.openInputStream(parsed)?.use { input ->
            val out=java.io.ByteArrayOutputStream();val buffer=ByteArray(8192);var total=0
            while(true) { val n=input.read(buffer);if(n<0) break;total+=n;require(total<=25*1024*1024) { "Uploads must be 25 MB or smaller." };out.write(buffer,0,n) }
            out.toByteArray()
        } ?: error("Cannot read selected media.")
        require(bytes.size<=25*1024*1024) { "Uploads must be 25 MB or smaller." }
        val body=MultipartBody.Builder().setType(MultipartBody.FORM).addFormDataPart("file",if(isVideo) "original.mp4" else "original.image",bytes.toRequestBody(mime.toMediaType())).build()
        val q=java.net.URLEncoder.encode(title,"UTF-8")+"&source="+java.net.URLEncoder.encode(source,"UTF-8")
        val item=contentFrom(JSONObject(api.request("api/content/upload?title=$q",body=body)))
        refresh();item
    }
    override fun scan(contentId:String): Flow<DittoResult<ScanProgress>> = flow {
        emit(DittoResult.Ok(ScanProgress(ScanStage.INGESTING,"Submitting your original to the backend.")))
        val r=result {
            val rows=JSONArray(api.request("api/scan",JSONObject().put("contentId",contentId).toString())).objects().map(::caseFrom)
            refresh();ScanProgress(ScanStage.DONE,"Server scan complete. Discovery is synthetic; outreach remains sandboxed.",rows.size,rows.map { it.id })
        }
        emit(r)
    }.flowOn(Dispatchers.IO)
    private suspend fun mutate(id:String,action:String,body:JSONObject): DittoResult<Case> = result {
        val c=caseFrom(JSONObject(api.request("api/cases/$id/$action",body.toString())))
        // Mutation receipt is authoritative even when a later snapshot refresh fails.
        cases.value=listOf(c)+cases.value.filterNot { it.id==c.id }
        runCatching { refresh() }.onFailure { connectionError.value="Action recorded; dashboard refresh unavailable." }
        c
    }
    override suspend fun approve(caseId:String,editedBody:String?,tone:MessageTone?)=mutate(caseId,"approve",JSONObject().put("editedBody",editedBody).put("tone",tone?.wire))
    override suspend fun reject(caseId:String,note:String?)=mutate(caseId,"reject",JSONObject().put("note",note))
    override suspend fun saveDraft(caseId:String,body:String,tone:MessageTone)=mutate(caseId,"edit-action",JSONObject().put("body",body).put("tone",tone.wire))
    override suspend fun runFollowUp(caseId:String,outcome:FollowUpOutcome)=mutate(caseId,"simulate-followup",JSONObject().put("outcome",outcome.wire))
    override suspend fun resolve(caseId:String,note:String?)=mutate(caseId,"resolve",JSONObject().put("note",note))
    override suspend fun casesAwaitingFollowUp()=cases.value.filter { it.state==CaseState.AWAITING_RESPONSE }
    override suspend fun seedDemoData(force:Boolean): DittoResult<Int> = result {
        require(!force) { "Server audit data cannot be reset. Create another test account." }
        val n=JSONObject(api.request("api/demo/seed","{}")).getInt("casesCreated");refresh();n
    }
    override suspend fun resetDemoData(): DittoResult<Int> = DittoResult.Err("Server audit data cannot be reset. Create another test account.")
    suspend fun advanceClock(): DittoResult<Int> = result { val n=JSONObject(api.request("api/demo/advance-clock","{}")).getInt("casesChecked");refresh();n }
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
