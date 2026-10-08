package com.ditto.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ditto.app.core.BackendConnection
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.ui.components.*
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel
import com.ditto.app.viewmodel.ScanViewModel

@Composable
fun ScanScreen(onOpenCase: (String) -> Unit, onHome: () -> Unit) {
    val scanVm: ScanViewModel = viewModel(factory = ScanViewModel.Factory)
    val appVm: DittoViewModel = viewModel(factory = DittoViewModel.Factory)
    val state by scanVm.state.collectAsStateWithLifecycle()
    val library by appVm.content.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val listState = rememberLazyListState()
    var uploadTitle by remember { mutableStateOf("My original") }
    var importedId by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(importedId, library) {
        val id = importedId ?: return@LaunchedEffect
        library.firstOrNull { it.id == id }?.let {
            scanVm.selectContent(it)
            importedId = null
        }
    }
    LaunchedEffect(state.selectedContent?.id) {
        if (state.selectedContent != null) listState.scrollToItem(0)
    }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri: Uri? ->
        if (uri != null) {
            runCatching { context.contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            val isVideo = context.contentResolver.getType(uri)?.startsWith("video/") == true
            scanVm.ingest(uploadTitle, uri.toString(), isVideo, "Device upload")
        }
    }
    LazyColumn(
        state = listState,
        modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Eyebrow("Find copies", modifier = Modifier.weight(1f))
                TextButton(onClick = onHome) { Text("Home") }
            }
            Spacer(Modifier.height(6.dp))
            Text("Your originals", style = MaterialTheme.typography.displaySmall, color = DittoColors.TextPrimary)
            Spacer(Modifier.height(6.dp))
            Text(
                if (state.selectedContent == null) "Choose an original, then tap Find copies to search for matching posts."
                else "Your original is selected. Start a search below or review your saved results.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }
        val selected = state.selectedContent
        if (selected != null) {
            item { SelectedContentCard(selected, onChange = { scanVm.clear() }) }
            item { ContentDiscoveryCard(selected.id, onOpenCase) }
        } else {
            item {
                DittoCard(background = DittoColors.BlueTint.copy(alpha = .88f)) {
                    Eyebrow("Three steps")
                    Spacer(Modifier.height(8.dp))
                    WorkflowStep("1", "Choose your original", "Pick a saved original, import your Reel or upload a file you own.")
                    WorkflowStep("2", "Tap Find copies", "Confirm sharing selected images, then follow your search as it runs.")
                    WorkflowStep("3", "Review matching posts", "Open the source to check the account, date and permission.")
                }
            }
            if (library.isNotEmpty()) {
                item { SectionHeading("Choose a saved original") }
                items(library.sortedByDescending { it.publishedAt }, key = { it.id }) { item ->
                    ContentRow(item = item, onClick = { if (!state.isIngesting) scanVm.selectContent(item) })
                }
            }
            if (BackendConnection(context).enabled()) {
                item { InstagramConnectionCard() }
                item { InstagramImportCard(onImported = { importedId = it }) }
            }
            item {
                SectionHeading("Upload an original")
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = uploadTitle,
                    onValueChange = { uploadTitle = it.take(120) },
                    label = { Text("Original title") },
                    singleLine = true,
                    enabled = !state.isIngesting,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(10.dp))
                UploadDropZone(isBusy = state.isIngesting, onChoose = {
                    picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo))
                })
            }
        }
        state.error?.let { message ->
            item { DittoCard { Text(message, style = MaterialTheme.typography.bodySmall) } }
        }
    }
}

@Composable
private fun WorkflowStep(number: String, title: String, detail: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.size(28.dp).clip(CircleShape).background(DittoColors.PrimaryBlue), contentAlignment = Alignment.Center) {
            Text(number, style = MaterialTheme.typography.labelMedium, color = DittoColors.TextOnDark)
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall, color = DittoColors.TextPrimary)
            Text(detail, style = MaterialTheme.typography.bodySmall, color = DittoColors.TextSecondary)
        }
    }
}

@Composable
private fun UploadDropZone(isBusy: Boolean, onChoose: () -> Unit) {
    val shape = RoundedCornerShape(16.dp)
    Column(
        modifier = Modifier.fillMaxWidth().clip(shape).background(DittoColors.BackgroundAlt)
            .border(1.dp, DittoColors.Border, shape).clickable(enabled = !isBusy, onClick = onChoose)
            .padding(vertical = 24.dp, horizontal = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(if (isBusy) "Saving your original…" else "Choose an image or video", style = MaterialTheme.typography.titleMedium, color = DittoColors.TextPrimary)
        Spacer(Modifier.height(6.dp))
        Text("After saving, tap Find copies to start the search.", style = MaterialTheme.typography.bodySmall, color = DittoColors.TextSecondary, textAlign = TextAlign.Center)
        if (!isBusy) {
            Spacer(Modifier.height(14.dp))
            SecondaryButton(text = "Choose from device", onClick = onChoose)
        }
    }
}

@Composable
private fun ContentRow(item: ContentItem, onClick: () -> Unit) {
    DittoCard(onClick = onClick, contentPadding = 12) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            EvidenceVisual(seed = item.paletteSeed, localUri = item.localUri, modifier = Modifier.size(48.dp), cornerRadius = 6)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(item.title, style = MaterialTheme.typography.titleSmall, color = DittoColors.TextPrimary, maxLines = 1)
                Text("${item.kind.wire.replaceFirstChar { it.uppercase() }} · Added ${relativeTime(item.publishedAt)}", style = MaterialTheme.typography.bodySmall, color = DittoColors.TextSecondary)
            }
            Text("Select →", style = MaterialTheme.typography.labelMedium, color = DittoColors.SecondaryBlue)
        }
    }
}

@Composable
private fun SelectedContentCard(content: ContentItem, onChange: () -> Unit) {
    DittoCard {
        Row(verticalAlignment = Alignment.Top) {
            EvidenceVisual(seed = content.paletteSeed, localUri = content.localUri, modifier = Modifier.size(72.dp), label = "Original")
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Eyebrow("Selected original")
                Spacer(Modifier.height(4.dp))
                Text(content.title, style = MaterialTheme.typography.titleMedium, color = DittoColors.TextPrimary)
                TextButton(onClick = onChange) { Text("Choose another original") }
            }
        }
    }
}
