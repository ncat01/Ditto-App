package com.ditto.app.ui.screens

import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.ditto.app.core.BackendConnection
import com.ditto.app.core.BackendApi
import com.ditto.app.core.ServiceLocator
import com.ditto.app.data.repository.RemoteDittoRepository
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.DittoCard
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CancellationException
import android.content.Intent
import android.net.Uri
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import org.json.JSONArray
import org.json.JSONObject
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts

private fun connectedApi(context: android.content.Context): BackendApi {
    val session=BackendConnection(context).session() ?: error("Sign into your Ditto cloud account first.")
    return BackendApi(session.endpoint,session.token)
}

@Composable
fun EmailOutreachCard(caseId: String, body: String) {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var configured by remember(caseId) { mutableStateOf(false) }
    var recipient by remember(caseId) { mutableStateOf("") }
    var reviewed by remember(caseId) { mutableStateOf(false) }
    var reminder by remember(caseId) { mutableStateOf(false) }
    var busy by remember(caseId) { mutableStateOf(false) }
    var confirm by remember(caseId) { mutableStateOf(false) }
    var message by remember(caseId) { mutableStateOf<String?>(null) }
    val requestId=remember(caseId,body,recipient) { java.util.UUID.randomUUID().toString().replace("-","") }
    LaunchedEffect(caseId) {
        try { configured=withContext(Dispatchers.IO) { JSONObject(connectedApi(context).request("api/discovery/status")).optBoolean("outreach") } }
        catch(e:CancellationException) { throw e }
        catch(e:Exception) { configured=false }
    }
    if(!configured) {
        Text("Email outreach is currently unavailable. You can review evidence and edit your draft.",style=MaterialTheme.typography.bodySmall)
        return
    }
    Text("Email a reviewed request",style=MaterialTheme.typography.titleSmall)
    OutlinedTextField(recipient,{recipient=it.take(254)},label={Text("Confirmed recipient email")},singleLine=true,enabled=!busy,modifier=Modifier.fillMaxWidth())
    Row { Checkbox(reviewed,{reviewed=it},enabled=!busy); Text("I checked ownership, permission and the recipient.",style=MaterialTheme.typography.bodySmall) }
    Row { Checkbox(reminder,{reminder=it},enabled=!busy); Text("Remind me to review this in 7 days. No automatic follow-up email.",style=MaterialTheme.typography.bodySmall) }
    SecondaryButton(text=if(busy) "Checking delivery status" else "Review and send email",
        enabled=!busy && reviewed && body.isNotBlank() && recipient.matches(Regex("[^\\s@]+@[^\\s@]+\\.[^\\s@]+")),
        modifier=Modifier.fillMaxWidth(),onClick={confirm=true})
    message?.let { Text(it,style=MaterialTheme.typography.bodySmall) }
    if(confirm) AlertDialog(onDismissRequest={confirm=false},title={Text("Send to $recipient?")},
        text={ Column { Text(body.take(4000)); Text("This sends a real email. Your verified account email is used for replies.",style=MaterialTheme.typography.bodySmall) } },
        dismissButton={TextButton(onClick={confirm=false}) {Text("Cancel")}},
        confirmButton={TextButton(onClick={
            confirm=false;busy=true
            scope.launch {
                try {
                    withContext(Dispatchers.IO) {
                        val api=connectedApi(context)
                        val receipt=JSONObject(api.request("api/cases/$caseId/approve",JSONObject()
                            .put("recipient",recipient).put("editedBody",body).put("requestId",requestId)
                            .put("evidenceReviewed",reviewed).put("recipientConfirmed",true).put("reminderDays",if(reminder) 7 else 0).toString()))
                        api.awaitJob(receipt.getString("dispatchJob"))
                        (ServiceLocator.repository(context) as? RemoteDittoRepository)?.refresh()
                    }
                    message="Email accepted by the mail service. Delivery and a response are not yet confirmed."
                } catch(e:CancellationException) {throw e}
                catch(e:Exception) {message=e.message ?: "Delivery not confirmed. Check status before sending again."}
                finally {busy=false}
            }
        }) {Text("Send approved email")}})
}

@Composable
fun InstagramConnectionCard() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val lifecycleOwner = LocalLifecycleOwner.current
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var confirmDisconnect by remember { mutableStateOf(false) }
    fun refresh() {
        if (busy) return
        busy = true
        scope.launch {
            try {
                status = withContext(Dispatchers.IO) {
                    JSONObject(connectedApi(context).request("api/integrations/instagram/status"))
                }
                message = null
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) { message = e.message ?: "Connection status unavailable. Try again." }
            finally { busy = false }
        }
    }
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) refresh()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(Unit) { refresh() }
    val connected = status?.optBoolean("connected") == true
    DittoCard {
        Text("Connect Instagram", style = MaterialTheme.typography.titleMedium)
        Text(if (connected) "Connected as @${status?.optString("username")}" else
            "Link your Creator or Business account through Instagram to import your own videos. You can also upload originals from your device.",
            style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        if (!connected) {
            SecondaryButton(text = if (busy) "Checking connection?" else "Continue with Instagram",
                enabled = !busy && status?.optBoolean("configured") == true,
                modifier = Modifier.fillMaxWidth(), onClick = {
                    busy = true; message = null
                    scope.launch {
                        try {
                            val api = connectedApi(context)
                            val result = withContext(Dispatchers.IO) {
                                JSONObject(api.request("api/integrations/instagram/connect", "{}"))
                            }
                            val uri = Uri.parse(result.getString("authorizationUrl"))
                            val origin = Uri.parse(api.endpoint)
                            require(uri.scheme == "https" && uri.host == origin.host && uri.port == origin.port &&
                                uri.userInfo == null && uri.path == "/api/integrations/instagram/begin") {
                                "Instagram sign-in address is invalid. Contact support."
                            }
                            context.startActivity(Intent(Intent.ACTION_VIEW, uri))
                            message = "Finish signing in in your browser, then return to Ditto."
                        } catch (e: CancellationException) { throw e }
                        catch (e: Exception) { message = e.message ?: "Could not open Instagram sign-in." }
                        finally { busy = false }
                    }
                })
            if (status?.optBoolean("configured") == false)
                Text("Instagram connection is currently unavailable. Device uploads still work.", style = MaterialTheme.typography.bodySmall)
        }
        SecondaryButton(text = "Refresh connection", enabled = !busy,
            onClick = { refresh() }, modifier = Modifier.fillMaxWidth())
        if (connected) TextButton(enabled = !busy, onClick = { confirmDisconnect = true }) { Text("Disconnect Instagram") }
        message?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
    }
    if (confirmDisconnect) AlertDialog(onDismissRequest = { confirmDisconnect = false },
        title = { Text("Disconnect Instagram?") },
        text = { Text("Ditto will remove its stored Instagram connection. Imported originals remain in your library. You can also remove Ditto from Instagram?s Apps and websites settings.") },
        dismissButton = { TextButton(onClick = { confirmDisconnect = false }) { Text("Cancel") } },
        confirmButton = { TextButton(onClick = {
            confirmDisconnect = false; busy = true
            scope.launch {
                try {
                    withContext(Dispatchers.IO) { connectedApi(context).request("api/integrations/instagram/disconnect", "{}") }
                    status = null; message = "Instagram disconnected."
                } catch (e: CancellationException) { throw e }
                catch (e: Exception) { message = e.message ?: "Could not disconnect. Try again." }
                finally { busy = false; refresh() }
            }
        }) { Text("Disconnect") } })
}

@Composable
fun InstagramImportCard(onImported: () -> Unit) {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var posts by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    fun load() {
        busy=true;message=null
        scope.launch {
            try {
                posts=withContext(Dispatchers.IO) {
                    val rows=JSONArray(connectedApi(context).awaitResult("api/integrations/instagram/posts"))
                    (0 until rows.length()).map { rows.getJSONObject(it) }
                }
                if(posts.isEmpty()) message="No posts in your linked Instagram account yet."
            } catch(e:Exception) { message=e.message ?: "Instagram unavailable." }
            finally { busy=false }
        }
    }
    DittoCard {
        Text("Your Instagram originals",style=MaterialTheme.typography.titleMedium)
        Text("Import a video or Reel from your linked Creator account (up to 20 MB).",style=MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        SecondaryButton(text=if(busy) "Working…" else "Load Instagram posts",onClick={load()},enabled=!busy,modifier=Modifier.fillMaxWidth())
        message?.let { Text(it,style=MaterialTheme.typography.bodySmall) }
        posts.forEach { post ->
            Spacer(Modifier.height(8.dp))
            Text(post.optString("caption").take(100).ifBlank { "Instagram original" })
            if(post.optString("mediaType")=="VIDEO") {
                SecondaryButton(text="Import video",enabled=!busy,onClick={
                    busy=true;message=null
                    scope.launch {
                        try {
                            withContext(Dispatchers.IO) { connectedApi(context).awaitResult("api/integrations/instagram/import/${post.getString("id")}","{}") }
                            message="Video imported. It is now in your library."
                            withContext(Dispatchers.IO) { (ServiceLocator.repository(context) as? RemoteDittoRepository)?.refresh() }
                            onImported()
                        } catch(e:Exception) { message=e.message ?: "Import failed." }
                        finally {busy=false}
                    }
                },modifier=Modifier.fillMaxWidth())
            } else Text("${post.optString("mediaType")} — video import only",style=MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun GeminiDraftButton(caseId: String, enabled: Boolean, onSave: (String) -> Unit) {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var busy by remember(caseId) { mutableStateOf(false) }
    var error by remember(caseId) { mutableStateOf<String?>(null) }
    var draft by remember(caseId) { mutableStateOf<String?>(null) }
    var confirm by remember(caseId) { mutableStateOf(false) }
    SecondaryButton(text=if(busy) "Drafting with Gemini…" else "Draft with Gemini",enabled=enabled && !busy,onClick={confirm=true},modifier=Modifier.fillMaxWidth())
    error?.let { Text(it,style=MaterialTheme.typography.bodySmall) }
    if(confirm) AlertDialog(onDismissRequest={confirm=false},title={Text("Draft with Gemini?")},text={Text("The title, recipient and current draft will be sent to Google. Free-tier inputs may be used to improve its products. You will review the result before saving. No video is sent.")},confirmButton={TextButton(onClick={
        confirm=false;busy=true;error=null
        scope.launch {
            try {draft=withContext(Dispatchers.IO) { JSONObject(connectedApi(context).awaitResult("api/cases/$caseId/ai-draft","{\"consent_to_google\":true}")).getString("body") }}
            catch(e:Exception) {error=e.message ?: "Gemini unavailable."}
            finally {busy=false}
        }
    }) {Text("Generate draft")}},dismissButton={TextButton(onClick={confirm=false}) {Text("Cancel")}})
    draft?.let { preview ->
        AlertDialog(onDismissRequest={draft=null},title={Text("Review Gemini draft")},text={
            Column { Text("Saving changes the draft only. Sending still requires approval.",style=MaterialTheme.typography.bodySmall)
                OutlinedTextField(value=preview,onValueChange={draft=it.take(4000)},label={Text("Message")},modifier=Modifier.fillMaxWidth().heightIn(max=300.dp)) }
        },confirmButton={TextButton(enabled=enabled && preview.isNotBlank(),onClick={onSave(preview);draft=null}) {Text("Save draft")}},dismissButton={TextButton(onClick={draft=null}) {Text("Discard")}})
    }
}


@Composable
fun AccountSecurityCard() {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var busy by remember {mutableStateOf(false)}
    var verified by remember {mutableStateOf(false)}
    var message by remember {mutableStateOf<String?>(null)}
    fun check() {
        scope.launch {
            try {verified=withContext(Dispatchers.IO) {JSONObject(connectedApi(context).request("api/auth/me")).optBoolean("emailVerified")}}
            catch(e:CancellationException) {throw e}
            catch(e:Exception) {message=e.message}
        }
    }
    LaunchedEffect(Unit) {check()}
    DittoCard {
        Text("Account security",style=MaterialTheme.typography.titleMedium)
        Text(if(verified) "Email verified" else "Verify your email to confirm this account belongs to you.",style=MaterialTheme.typography.bodySmall)
        if(!verified) SecondaryButton(text="Send verification email",enabled=!busy,onClick={
            busy=true
            scope.launch {
                try {withContext(Dispatchers.IO) {connectedApi(context).request("api/auth/request-verification","{}")};message="Open the verification link in your email, then refresh here."}
                catch(e:CancellationException) {throw e}
                catch(e:Exception) {message=e.message ?: "Email unavailable."}
                finally {busy=false}
            }
        },modifier=Modifier.fillMaxWidth())
        TextButton(enabled=!busy,onClick={check()}) {Text("Refresh verification")}
        val endpoint=BackendConnection(context).endpoint()
        Row {
            TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(endpoint+"privacy")))}) {Text("Privacy")}
            TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(endpoint+"terms")))}) {Text("Terms")}
            TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(endpoint+"account/delete")))}) {Text("Delete account")}
        }
        message?.let {Text(it,style=MaterialTheme.typography.bodySmall)}
    }
}


@Composable
fun ContentDiscoveryCard(contentId: String) {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var busy by remember {mutableStateOf(false)}
    var message by remember {mutableStateOf<String?>(null)}
    var results by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    var confirmSearch by remember {mutableStateOf(false)}
    var configured by remember {mutableStateOf(false)}
    LaunchedEffect(contentId) {
        try {configured=withContext(Dispatchers.IO) {JSONObject(connectedApi(context).request("api/discovery/status")).optBoolean("configured")}}
        catch(e:CancellationException) {throw e}
        catch(e:Exception) {message=e.message}
    }
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if(uri!=null) {
            busy=true;message=null
            scope.launch {
                try {
                    val result=withContext(Dispatchers.IO) {
                        val data=context.contentResolver.openInputStream(uri)?.use { input ->
                            val output=java.io.ByteArrayOutputStream()
                            val buffer=ByteArray(8192)
                            while(true) {val size=input.read(buffer);if(size<0)break;require(output.size()+size<=20_000_000) {"Candidate exceeds 20 MB."};output.write(buffer,0,size)}
                            output.toByteArray()
                        } ?: error("Cannot read candidate.")
                        val mime=context.contentResolver.getType(uri) ?: "application/octet-stream"
                        val body=MultipartBody.Builder().setType(MultipartBody.FORM)
                            .addFormDataPart("file","candidate",data.toRequestBody(mime.toMediaType())).build()
                        val api=connectedApi(context)
                        JSONObject(if(api.supportsChunkedUpload()) api.uploadMedia(data,mime,"Submitted comparison","Submitted evidence",contentId)
                            else api.request("api/discovery/$contentId/compare",body=body))
                    }
                    message="Measured similarity: ${(result.getDouble("similarity")*100).toInt()}%. ${result.getString("algorithm")}. ${result.getString("notice") }"
                } catch(e:CancellationException) {throw e}
                catch(e:Exception) {message=e.message ?: "Comparison unavailable."}
                finally {busy=false}
            }
        }
    }
    DittoCard {
        Text("Find and compare reposts",style=MaterialTheme.typography.titleMedium)
        Text("Search leads on the public web, or select a suspected repost to compare against this original. Use the same media type.",style=MaterialTheme.typography.bodySmall)
        SecondaryButton(text="Compare a suspected repost",enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo))})
        SecondaryButton(text=if(busy) "Working?" else "Reverse search the web",enabled=!busy && configured,modifier=Modifier.fillMaxWidth(),onClick={confirmSearch=true})
        if(!configured) Text("Web search is currently unavailable. Candidate comparison is available for your uploaded originals.",style=MaterialTheme.typography.bodySmall)
        message?.let {Text(it,style=MaterialTheme.typography.bodySmall)}
        results.forEach { result ->
            Text(result.optString("title").ifBlank {"Unverified search lead"},style=MaterialTheme.typography.titleSmall)
            Text(result.getString("url"),style=MaterialTheme.typography.bodySmall,maxLines=2)
            TextButton(onClick={
                val uri=Uri.parse(result.getString("url"))
                if(uri.scheme in listOf("https","http") && uri.host!=null && uri.userInfo==null)
                    context.startActivity(Intent(Intent.ACTION_VIEW,uri))
            }) {Text("Review source in browser")}
        }
    }
    if(confirmSearch) AlertDialog(onDismissRequest={confirmSearch=false},title={Text("Search with Google?")},
        text={Text("Ditto sends this image, or five sampled video frames, to Google Vision Web Detection. Results are unverified leads and may miss reposts. Nothing is sent to the source account.")},
        dismissButton={TextButton(onClick={confirmSearch=false}) {Text("Cancel")}},
        confirmButton={TextButton(onClick={
            confirmSearch=false;busy=true;message=null;results=emptyList()
            scope.launch {
                try {
                    val result=withContext(Dispatchers.IO) {JSONObject(connectedApi(context).awaitResult("api/discovery/$contentId/web-search","{\"consent_to_google\":true}"))}
                    val rows=result.getJSONArray("results")
                    results=(0 until rows.length()).map {rows.getJSONObject(it)}
                    message=if(results.isEmpty()) "No web leads returned. This does not establish that no reposts exist." else result.getString("notice")
                } catch(e:CancellationException) {throw e}
                catch(e:Exception) {message=e.message ?: "Search unavailable."}
                finally {busy=false}
            }
        }) {Text("Search")}})
}
