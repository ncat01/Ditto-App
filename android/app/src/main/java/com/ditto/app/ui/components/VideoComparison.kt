package com.ditto.app.ui.components

import android.net.Uri
import android.widget.VideoView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.ditto.app.domain.model.Case

@Composable
fun VideoPreview(uri: String, title: String, modifier: Modifier = Modifier) {
    var player by remember(uri) { mutableStateOf<VideoView?>(null) }
    var playing by remember(uri) { mutableStateOf(false) }
    var failed by remember(uri) { mutableStateOf(false) }
    Column(modifier) {
        Text(title,style=MaterialTheme.typography.labelMedium)
        AndroidView(factory={ context -> VideoView(context).apply {
            setVideoURI(Uri.parse(uri));setOnPreparedListener { seekTo(100);it.isLooping=true }
            setOnErrorListener { _,_,_ -> failed=true;true }; player=this
        } },modifier=Modifier.fillMaxWidth().height(150.dp))
        TextButton(enabled=!failed,onClick={ playing=!playing; if(playing)player?.start() else player?.pause() }) { Text(if(failed) "Playback unavailable" else if(playing) "Pause" else "Play • 00:00–00:03") }
    }
    DisposableEffect(uri) { onDispose { player?.stopPlayback() } }
}

@Composable
fun VideoComparison(case: Case) {
    ServerVideoComparison(case)
}

@Composable
private fun ServerVideoComparison(case: Case) {
    val context=LocalContext.current
    var clips by remember(case.id) { mutableStateOf<Pair<String,String>?>(null) }
    var error by remember(case.id) { mutableStateOf<String?>(null) }
    var isImage by remember(case.id) { mutableStateOf(false) }
    LaunchedEffect(case.id) {
        try { clips=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            val session=com.ditto.app.core.BackendConnection(context).session() ?: error("Sign in again to view private media.")
            val api=com.ditto.app.core.BackendApi(session.endpoint,session.token) { com.ditto.app.core.BackendConnection(context).accessToken(session.userId) }
            isImage=org.json.JSONObject(api.request("api/cases/${case.id}")).getJSONObject("candidate").optString("mediaKind")=="image"
            val scope=java.security.MessageDigest.getInstance("SHA-256").digest((session.endpoint+session.userId).toByteArray()).joinToString("") { "%02x".format(it) }
            val extension=if(isImage) "image" else "mp4"
            val original=api.download("api/content/${case.contentId}/media",java.io.File(context.cacheDir,"server-media/$scope/${case.id}-original.$extension"))
            val candidate=api.download("api/cases/${case.id}/candidate-media",java.io.File(context.cacheDir,"server-media/$scope/${case.id}-candidate.$extension"))
            Uri.fromFile(original).toString() to Uri.fromFile(candidate).toString()
        } } catch(e:kotlinx.coroutines.CancellationException) { throw e } catch(e:Exception) { error=e.message ?: "Server media unavailable." }
    }
    clips?.let { (original,candidate) ->
        Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
            if(isImage) {
                coil.compose.AsyncImage(model=original,contentDescription="Private original",modifier=Modifier.weight(1f).height(180.dp))
                coil.compose.AsyncImage(model=candidate,contentDescription="Submitted candidate",modifier=Modifier.weight(1f).height(180.dp))
            } else {
                VideoPreview(original,"Original",Modifier.weight(1f))
                VideoPreview(candidate,if(case.candidate.isSubmittedMedia) "Submitted candidate" else "Candidate",Modifier.weight(1f))
            }
        }
    } ?: Text(error ?: "Loading private server videos…",style=MaterialTheme.typography.bodySmall)
    Text("Private evidence. Review ownership, attribution and permission separately. Face and manipulation detectors are unavailable.",style=MaterialTheme.typography.bodySmall)
}
