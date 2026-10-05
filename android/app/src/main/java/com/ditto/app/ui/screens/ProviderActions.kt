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

private fun connectedApi(context: android.content.Context): BackendApi {
    val session=BackendConnection(context).session() ?: error("Sign into your Ditto cloud account first.")
    return BackendApi(session.endpoint,session.token)
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
                    val rows=JSONArray(connectedApi(context).request("api/integrations/instagram/posts"))
                    (0 until rows.length()).map { rows.getJSONObject(it) }
                }
                if(posts.isEmpty()) message="No posts in your linked Instagram account yet."
            } catch(e:Exception) { message=e.message ?: "Instagram unavailable." }
            finally { busy=false }
        }
    }
    DittoCard {
        Text("Your Instagram originals",style=MaterialTheme.typography.titleMedium)
        Text("Import a video or Reel from your linked Creator account (up to 25 MB).",style=MaterialTheme.typography.bodySmall)
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
                            withContext(Dispatchers.IO) { connectedApi(context).request("api/integrations/instagram/import/${post.getString("id")}","{}") }
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
            try {draft=withContext(Dispatchers.IO) { JSONObject(connectedApi(context).request("api/cases/$caseId/ai-draft","{}")).getString("body") }}
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
