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
import com.ditto.app.data.demo.VideoCorpus
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
    val context=LocalContext.current
    if(com.ditto.app.core.BackendConnection(context).enabled()) {
        ServerVideoComparison(case)
        return
    }
    val corpus=remember { VideoCorpus(context) }
    val kind=when(case.candidate.id) { "cand_001"->"crop";"cand_002"->"caption";"cand_003"->"unrelated";"cand_004"->"resize";"cand_005"->"fake_endorsement";"cand_007"->"credited";"cand_008"->"authorized";"cand_009"->"ambiguous";else->"watermark" }
    val original=remember(case.id) { Uri.fromFile(corpus.asset("original_${case.contentPaletteSeed}.mp4")).toString() }
    val copy=remember(case.id) { Uri.fromFile(corpus.asset("${case.candidate.paletteSeed}_${kind}.mp4")).toString() }
    if(case.candidate.id=="cand_005") {
        Text("SIMULATED ALTERED SPEECH",style=MaterialTheme.typography.titleSmall)
        Text("Authored original script: ‘I do not endorse this skincare product.’\nAuthored candidate script: ‘I recommend this skincare product.’\nThese are demo labels, not extracted transcripts. The abstract video has no person's likeness or speech. ASR, face embeddings and manipulation detection are unavailable.",style=MaterialTheme.typography.bodySmall)
    }
    Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
        VideoPreview(original,"Original",Modifier.weight(1f))
        VideoPreview(copy,"Candidate • demo",Modifier.weight(1f))
    }
    Text("Samples at 0%, 25%, 50%, 75%, 100% of the clip. Attribution: ${if(case.candidate.attributionPresent) "credit present" else "not found in demo metadata"}. Permission: ${if(case.candidate.permissionGranted) "authorized in demo registry" else "unknown"}. Generated demo assets.",style=MaterialTheme.typography.bodySmall)
}

@Composable
private fun ServerVideoComparison(case: Case) {
    val context=LocalContext.current
    var clips by remember(case.id) { mutableStateOf<Pair<String,String>?>(null) }
    var error by remember(case.id) { mutableStateOf<String?>(null) }
    LaunchedEffect(case.id) {
        try { clips=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            val session=com.ditto.app.core.BackendConnection(context).session() ?: error("Sign in again to view private media.")
            val api=com.ditto.app.core.BackendApi(session.endpoint,session.token)
            val scope=java.security.MessageDigest.getInstance("SHA-256").digest((session.endpoint+session.userId).toByteArray()).joinToString("") { "%02x".format(it) }
            val original=api.download("api/content/${case.contentId}/media",java.io.File(context.cacheDir,"server-media/$scope/${case.id}-original.mp4"))
            val candidate=api.download("api/cases/${case.id}/candidate-media",java.io.File(context.cacheDir,"server-media/$scope/${case.id}-candidate.mp4"))
            Uri.fromFile(original).toString() to Uri.fromFile(candidate).toString()
        } } catch(e:kotlinx.coroutines.CancellationException) { throw e } catch(e:Exception) { error=e.message ?: "Server media unavailable." }
    }
    clips?.let { (original,candidate) ->
        Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
            VideoPreview(original,"Server original",Modifier.weight(1f))
            VideoPreview(candidate,"Server candidate • demo",Modifier.weight(1f))
        }
    } ?: Text(error ?: "Loading private server videos…",style=MaterialTheme.typography.bodySmall)
    Text("Authenticated server assets. Attribution: ${if(case.candidate.attributionPresent) "credit present" else "unknown or absent in demo metadata"}. Permission: ${if(case.candidate.permissionGranted) "authorized in demo registry" else "unknown"}. Discovery is synthetic; no live manipulation detector or extracted transcripts.",style=MaterialTheme.typography.bodySmall)
}
