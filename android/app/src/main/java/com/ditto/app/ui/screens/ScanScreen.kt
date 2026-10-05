package com.ditto.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.expandVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.ScanStage
import com.ditto.app.ui.components.CaseCard
import com.ditto.app.ui.components.DemoModeBanner
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.EvidenceVisual
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.PrimaryButton
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.SectionHeading
import com.ditto.app.ui.components.relativeTime
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel
import com.ditto.app.viewmodel.ScanViewModel

private val SCAN_STAGES = listOf(
    ScanStage.INGESTING,
    ScanStage.FINGERPRINTING,
    ScanStage.DISCOVERING,
    ScanStage.VERIFYING,
    ScanStage.PREPARING
)

@Composable
fun ScanScreen(onOpenCase: (String) -> Unit) {
    val scanVm: ScanViewModel = viewModel(factory = ScanViewModel.Factory)
    val appVm: DittoViewModel = viewModel(factory = DittoViewModel.Factory)
    val state by scanVm.state.collectAsStateWithLifecycle()
    val library by appVm.content.collectAsStateWithLifecycle()

    val context = androidx.compose.ui.platform.LocalContext.current
    var uploadTitle by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf("My original") }
    var uploadSource by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf("Local upload") }
    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            runCatching { context.contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            val isVideo = context.contentResolver.getType(uri)?.startsWith("video/") == true
            scanVm.ingest(uploadTitle, uri.toString(), isVideo, uploadSource)
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Eyebrow("Scan")
            Spacer(Modifier.height(6.dp))
            Text(
                "Your originals",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "Select an original to fingerprint and scan the synthetic corpus. Live discovery is unavailable.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }

        item { DemoModeBanner(scanVm.discoveryName) }
        if(com.ditto.app.core.BackendConnection(context).enabled()) {
            item { InstagramConnectionCard() }
            item { InstagramImportCard(onImported = { scanVm.clear() }) }
        }

        item {
            androidx.compose.material3.OutlinedTextField(value=uploadTitle,onValueChange={uploadTitle=it.take(120)},label={Text("Title for your upload")},singleLine=true,modifier=Modifier.fillMaxWidth())
        }
        item {
            androidx.compose.material3.OutlinedTextField(value=uploadSource,onValueChange={uploadSource=it.take(256)},label={Text("Source metadata (platform or URL)")},singleLine=true,modifier=Modifier.fillMaxWidth())
        }
        // --- upload / selection ---
        if (state.selectedContent == null) {
            item {
                UploadDropZone(
                    isBusy = state.isIngesting,
                    onChoose = {
                        picker.launch(
                            PickVisualMediaRequest(
                                ActivityResultContracts.PickVisualMedia.ImageAndVideo
                            )
                        )
                    }
                )
            }

            if (library.isNotEmpty()) {
                item {
                    SectionHeading("Or pick from your library")
                }
                items(library, key = { it.id }) { item ->
                    ContentRow(item = item, onClick = { scanVm.selectContent(item) })
                }
            }
        } else {
            item {
                SelectedContentCard(
                    content = state.selectedContent!!,
                    matcherName = scanVm.matcherName,
                    onChange = { scanVm.clear() }
                )
            }
        }

        state.selectedContent?.let { selected ->
            item {
                Text("Scan history",style=MaterialTheme.typography.titleMedium)
                if(com.ditto.app.core.BackendConnection(context).enabled()) {
                    ServerScanHistory(selected.id,state.isScanning)
                } else {
                    val db=com.ditto.app.data.local.DittoDatabase.get(context,com.ditto.app.core.ServiceLocator.activeUser!!)
                    val jobs by androidx.compose.runtime.remember(selected.id) { db.scanJobDao().observe(selected.id) }.collectAsStateWithLifecycle(initialValue=emptyList())
                    jobs.take(5).forEach { job -> Text("${relativeTime(job.startedAt)} • ${job.stage} • ${job.candidates} candidates${job.error?.let { " • $it" } ?: ""}",style=MaterialTheme.typography.bodySmall) }
                    if(jobs.isEmpty()) Text("No scan has run for this original yet.",style=MaterialTheme.typography.bodySmall)
                }
                selected.localUri?.let { uri -> if(selected.kind==com.ditto.app.domain.model.ContentKind.VIDEO || uri.endsWith(".mp4")) com.ditto.app.ui.components.VideoPreview(uri,"Preview your original") }
            }
        }
        // --- error ---
        state.error?.let { message ->
            item { ScanErrorCard(message = message, onRetry = { scanVm.startScan() }) }
        }

        // --- scan action / progress ---
        if (state.selectedContent != null && state.stage == ScanStage.IDLE) {
            item {
                PrimaryButton(
                    text = "Scan for matches",
                    onClick = { scanVm.startScan() },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        if (state.stage != ScanStage.IDLE) {
            item {
                ScanProgressCard(
                    currentStage = state.stage,
                    message = state.stageMessage,
                    isScanning = state.isScanning
                )
            }
        }

        // --- results ---
        if (state.stage == ScanStage.DONE) {
            item {
                SectionHeading(
                    if (state.candidatesFound == 0) "No potential matches found"
                    else "${state.candidatesFound} potential match" +
                        "${if (state.candidatesFound == 1) "" else "es"} found"
                )
            }

            if (state.results.isEmpty() && state.candidatesFound == 0) {
                item {
                    DittoCard {
                        Text(
                            "Nothing found this time.",
                            style = MaterialTheme.typography.titleMedium,
                            color = DittoColors.TextPrimary
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "Ditto checked the discovery corpus and found no candidate reuse " +
                                "of this content. It stays monitored for future scans.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = DittoColors.TextSecondary
                        )
                    }
                }
            } else {
                items(state.results, key = { it.id }) { case ->
                    CaseCard(case = case, onClick = { onOpenCase(case.id) })
                }
            }

            item {
                SecondaryButton(
                    text = "Scan something else",
                    onClick = { scanVm.clear() },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@Composable
private fun ServerScanHistory(id: String, scanning: Boolean) {
    val context=androidx.compose.ui.platform.LocalContext.current
    val lines by androidx.compose.runtime.produceState<List<String>?>(null,id,scanning) {
        value=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val session=com.ditto.app.core.BackendConnection(context).session() ?: error("Sign in again.")
                val rows=org.json.JSONArray(com.ditto.app.core.BackendApi(session.endpoint,session.token).request("api/content/$id/scans"))
                if(rows.length()==0) listOf("No server scan has run for this original yet.")
                else (0 until minOf(5,rows.length())).map { i-> val j=rows.getJSONObject(i);"${j.getString("stage")} • ${j.getInt("candidates")} candidates • ${j.getString("createdAt")}" }
            } catch(e:kotlinx.coroutines.CancellationException) { throw e } catch(e:Exception) { listOf("Server scan history unavailable. Resume your Codespace.") }
        }
    }
    (lines ?: listOf("Loading server scan history…")).forEach { Text(it,style=MaterialTheme.typography.bodySmall) }
}

@Composable
private fun UploadDropZone(isBusy: Boolean, onChoose: () -> Unit) {
    val shape = RoundedCornerShape(10.dp)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(DittoColors.BackgroundAlt)
            .border(1.dp, DittoColors.Border, shape)
            .clickable(enabled = !isBusy, onClick = onChoose)
            .padding(vertical = 34.dp, horizontal = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier
                .size(46.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(DittoColors.LightBlue),
            contentAlignment = Alignment.Center
        ) {
            Text("↑", style = MaterialTheme.typography.headlineMedium, color = DittoColors.PrimaryBlue)
        }
        Spacer(Modifier.height(14.dp))
        Text(
            if (isBusy) "Reading your file…" else "Drop content here",
            style = MaterialTheme.typography.titleMedium,
            color = DittoColors.TextPrimary
        )
        Spacer(Modifier.height(4.dp))
        Text(
            if (isBusy) "Generating a perceptual fingerprint"
            else "Choose an image or video from your device",
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextSecondary,
            textAlign = TextAlign.Center
        )
        if (!isBusy) {
            Spacer(Modifier.height(16.dp))
            SecondaryButton(text = "Choose from device", onClick = onChoose)
        }
    }
}

@Composable
private fun ContentRow(item: ContentItem, onClick: () -> Unit) {
    DittoCard(onClick = onClick, contentPadding = 12) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            EvidenceVisual(
                seed = item.paletteSeed,
                localUri = item.localUri,
                modifier = Modifier.size(48.dp),
                cornerRadius = 6
            )
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    item.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = DittoColors.TextPrimary,
                    maxLines = 1
                )
                Text(
                    "${item.kind.wire.replaceFirstChar { it.uppercase() }} · " +
                        "published ${relativeTime(item.publishedAt)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
            Text("→", style = MaterialTheme.typography.titleMedium, color = DittoColors.SecondaryBlue)
        }
    }
}

@Composable
private fun SelectedContentCard(
    content: ContentItem,
    matcherName: String,
    onChange: () -> Unit
) {
    DittoCard {
        Row(verticalAlignment = Alignment.Top) {
            EvidenceVisual(
                seed = content.paletteSeed,
                localUri = content.localUri,
                modifier = Modifier.size(84.dp),
                label = "Original"
            )
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Eyebrow("Selected")
                Spacer(Modifier.height(4.dp))
                Text(
                    content.title,
                    style = MaterialTheme.typography.titleMedium,
                    color = DittoColors.TextPrimary
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "pHash ${content.perceptualHash.take(16)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
                Text(
                    matcherName,
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextTertiary
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        HairlineDivider()
        Spacer(Modifier.height(10.dp))
        Text(
            "Change selection",
            style = MaterialTheme.typography.labelMedium,
            color = DittoColors.SecondaryBlue,
            modifier = Modifier.clickable(onClick = onChange)
        )
    }
}

/**
 * Meaningful staged progress — each stage reflects real pipeline work rather than a
 * timed placeholder bar (report §14).
 */
@Composable
private fun ScanProgressCard(
    currentStage: ScanStage,
    message: String,
    isScanning: Boolean
) {
    val transition = rememberInfiniteTransition(label = "pulse")
    val pulse by transition.animateFloat(
        initialValue = 0.35f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(760), RepeatMode.Reverse),
        label = "pulseAlpha"
    )
    val currentIndex = SCAN_STAGES.indexOf(currentStage)
        .let { if (currentStage == ScanStage.DONE) SCAN_STAGES.size else it }

    DittoCard {
        Eyebrow(if (isScanning) "Scanning" else "Scan complete")
        Spacer(Modifier.height(12.dp))
        SCAN_STAGES.forEachIndexed { index, stage ->
            val done = index < currentIndex
            val active = index == currentIndex && isScanning
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(vertical = 5.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    Modifier
                        .size(if (active) 10.dp else 8.dp)
                        .clip(CircleShape)
                        .alpha(if (active) pulse else 1f)
                        .background(
                            when {
                                done -> DittoColors.Success
                                active -> DittoColors.PrimaryBlue
                                else -> DittoColors.SurfaceSunken
                            }
                        )
                )
                Spacer(Modifier.width(12.dp))
                Text(
                    text = stage.label,
                    style = if (active) MaterialTheme.typography.titleSmall
                    else MaterialTheme.typography.bodyMedium,
                    color = when {
                        done -> DittoColors.TextPrimary
                        active -> DittoColors.PrimaryBlue
                        else -> DittoColors.TextTertiary
                    },
                    modifier = Modifier.weight(1f)
                )
                if (done) {
                    Text("✓", style = MaterialTheme.typography.labelMedium, color = DittoColors.Success)
                }
            }
        }
        AnimatedVisibility(visible = message.isNotBlank(), enter = fadeIn() + expandVertically()) {
            Column {
                Spacer(Modifier.height(10.dp))
                HairlineDivider()
                Spacer(Modifier.height(10.dp))
                Text(
                    message,
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
        }
    }
}

@Composable
private fun ScanErrorCard(message: String, onRetry: () -> Unit) {
    DittoCard(background = DittoColors.DangerBg, borderColor = DittoColors.Danger.copy(alpha = 0.3f)) {
        Text(
            "Ditto couldn't complete the scan.",
            style = MaterialTheme.typography.titleMedium,
            color = DittoColors.Danger
        )
        Spacer(Modifier.height(4.dp))
        Text(
            message,
            style = MaterialTheme.typography.bodyMedium,
            color = DittoColors.TextSecondary
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Your original remains in the selected account's storage.",
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextSecondary
        )
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PrimaryButton(text = "Try again", onClick = onRetry, modifier = Modifier.weight(1f))
        }
    }
}
