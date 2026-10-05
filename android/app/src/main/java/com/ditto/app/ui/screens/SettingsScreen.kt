package com.ditto.app.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.BuildConfig
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.DittoMark
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.StatusPill
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

@Composable
fun SettingsScreen(
    vm: DittoViewModel,
    onOpenLikeness: () -> Unit,
    onOpenAnalytics: () -> Unit
) {
    val settings by vm.settings.collectAsStateWithLifecycle()
    val stats by vm.stats.collectAsStateWithLifecycle()
    val engines = vm.engineNames
    val connected=com.ditto.app.core.BackendConnection(androidx.compose.ui.platform.LocalContext.current).enabled()
    val context=androidx.compose.ui.platform.LocalContext.current
    val scope=androidx.compose.runtime.rememberCoroutineScope()

    var showGuide by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }
    if(showGuide) {
        androidx.compose.ui.window.Dialog(onDismissRequest={showGuide=false},properties=androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth=false)) {
            CreatorTutorial(connected,onFinish={showGuide=false})
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
            Eyebrow("Profile")
            Spacer(Modifier.height(6.dp))
            Text(
                "Your creator space",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
        }

        item {
            SecondaryButton(text="How to use Ditto",onClick={showGuide=true},modifier=Modifier.fillMaxWidth())
        }
        // ---- profile ----
        item {
            DittoCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier
                            .size(48.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(DittoColors.LightBlue),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            settings.creatorName.take(1),
                            style = MaterialTheme.typography.headlineSmall,
                            color = DittoColors.PrimaryBlue
                        )
                    }
                    Spacer(Modifier.width(14.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            if(connected) "Server creator account" else settings.creatorName,
                            style = MaterialTheme.typography.titleMedium,
                            color = DittoColors.TextPrimary
                        )
                        Text(
                            if(connected) "Connected test • separate from offline accounts" else settings.creatorHandle,
                            style = MaterialTheme.typography.bodySmall,
                            color = DittoColors.TextSecondary
                        )
                    }
                }
                Spacer(Modifier.height(14.dp))
                HairlineDivider()
                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth()) {
                    ProfileStat("Content", stats.contentMonitored.toString(), Modifier.weight(1f))
                    ProfileStat("Open cases", stats.openCases.toString(), Modifier.weight(1f))
                    ProfileStat("Resolved", stats.resolved.toString(), Modifier.weight(1f))
                }
            }
        }

        // ---- demo mode ----
        item {
            DittoCard {
                Eyebrow("Demo mode")
                Spacer(Modifier.height(10.dp))
                ToggleRow(
                    title = "Demo Mode",
                    subtitle = if(connected) "Connected to your test backend. Discovery and outreach remain sandboxed." else "Offline demo is active. Log out to choose Connected test.",
                    checked = true,
                    onChange = {},
                    enabled = false
                )
                Spacer(Modifier.height(6.dp))
                HairlineDivider()
                Spacer(Modifier.height(6.dp))
                ToggleRow(
                    title = "Presentation Mode",
                    subtitle = "Saved presentation preference. The same measured pipeline runs in both settings.",
                    checked = settings.presentationMode,
                    onChange = vm::setPresentationMode
                )
                Spacer(Modifier.height(14.dp))
                SecondaryButton(
                    text = if(connected) "Load server sample cases" else "Reset demo data",
                    onClick = { if(connected) scope.launch {
                        val result=kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { com.ditto.app.core.ServiceLocator.repository(context).seedDemoData(false) }
                        vm.showMessage(when(result) { is com.ditto.app.data.repository.DittoResult.Ok -> "Server sample cases loaded."; is com.ditto.app.data.repository.DittoResult.Err -> result.message })
                    } else vm.resetDemoData() },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        // ---- agent configuration ----
        item {
            DittoCard {
                Eyebrow("Agent preferences")
                Spacer(Modifier.height(10.dp))
                ToggleRow(
                    title = "Require human approval",
                    subtitle = "Always on. Ditto drafts and recommends, but never sends an " +
                        "attribution request or takedown notice without your approval.",
                    checked = true,
                    onChange = {},
                    enabled = false
                )
                Spacer(Modifier.height(6.dp))
                HairlineDivider()
                Spacer(Modifier.height(6.dp))
                ToggleRow(
                    title = "Notify on escalation",
                    subtitle = "Saved preference. Push delivery is unavailable in this offline demo.",
                    checked = settings.notifyOnEscalation,
                    onChange = vm::setNotifyEscalation
                )
                Spacer(Modifier.height(6.dp))
                HairlineDivider()
                Spacer(Modifier.height(6.dp))
                ToggleRow(
                    title = "Notify on new case",
                    subtitle = "Saved preference. Review new cases in Activity; push delivery is unavailable.",
                    checked = settings.notifyOnNewCase,
                    onChange = vm::setNotifyNewCase
                )
            }
        }

        item {
            DittoCard {
                Eyebrow("Privacy")
                Text(if(connected) "Accounts, case records and uploads are stored on the configured backend. Server snapshots refresh while signed in; external platform delivery is unavailable. Deleting a Codespace deletes its stored data." else "Media and case databases stay in private app storage for this account. OS backup is disabled. There is no cloud sync or live platform delivery.",style=MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(12.dp))
                SecondaryButton(text="Instagram connection status",onClick={vm.showMessage("Instagram is not connected. This build uses generated demo videos and local uploads; no Instagram login or discovery adapter is installed.")},modifier=Modifier.fillMaxWidth())
            }
        }
        // ---- connected platforms ----
        item {
            DittoCard {
                Eyebrow("Connected platforms")
                Spacer(Modifier.height(12.dp))
                IntegrationRow("Meta Graph API", "Not configured", false)
                IntegrationRow("Google Cloud Vision", "Not configured", false)
                IntegrationRow("Meta Ad Library", "Not configured", false)
                IntegrationRow("LLM verification", "Not configured", false)
                IntegrationRow("On-device pHash", "Active", true)
                IntegrationRow("Demo discovery corpus", "Active", true)
                Spacer(Modifier.height(12.dp))
                HairlineDivider()
                Spacer(Modifier.height(10.dp))
                Text(
                    "Provider credentials are never stored in this app. They live in the " +
                        "backend's environment, and Ditto falls back to Demo Mode when a " +
                        "provider is unavailable.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
        }

        // ---- engines ----
        item {
            DittoCard(background = DittoColors.BackgroundAlt) {
                Eyebrow("Active engines")
                Spacer(Modifier.height(10.dp))
                EngineRow("Matching", engines.matcher)
                EngineRow("Discovery", engines.discovery)
                EngineRow("Verification", engines.verification)
                Spacer(Modifier.height(10.dp))
                HairlineDivider()
                Spacer(Modifier.height(10.dp))
                EngineRow("Backend", BuildConfig.API_BASE_URL)
                EngineRow("Storage", "Room / SQLite (on-device)")
            }
        }

        // ---- links ----
        item {
            DittoCard(contentPadding = 0) {
                LinkRow("AI Likeness Protection", "Coming in P2", onOpenLikeness)
                HairlineDivider()
                LinkRow("Analytics", "Detection and resolution metrics", onOpenAnalytics)
            }
        }

        // ---- about ----
        item {
            DittoCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    DittoMark(size = 32)
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text(
                            "Ditto",
                            style = MaterialTheme.typography.titleMedium,
                            color = DittoColors.TextPrimary
                        )
                        Text(
                            "Version ${BuildConfig.VERSION_NAME}",
                            style = MaterialTheme.typography.bodySmall,
                            color = DittoColors.TextSecondary
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
                Text(
                    "Stay on it until it's resolved.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = DittoColors.TextSecondary
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "An agentic AI content credit system. Ditto finds where your content " +
                        "gets reused, verifies it, recommends an action, and keeps the case " +
                        "open until it resolves.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextTertiary
                )
            }
        }
    }
}

@Composable
private fun ProfileStat(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier) {
        Text(
            value,
            style = MaterialTheme.typography.titleLarge,
            color = DittoColors.PrimaryBlue
        )
        Text(
            label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = DittoColors.TextSecondary
        )
    }
}

@Composable
private fun ToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onChange: (Boolean) -> Unit,
    enabled: Boolean = true
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.Top
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(2.dp))
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = DittoColors.TextSecondary
            )
        }
        Spacer(Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onChange,
            enabled = enabled,
            colors = SwitchDefaults.colors(
                checkedThumbColor = DittoColors.Surface,
                checkedTrackColor = DittoColors.PrimaryBlue,
                checkedBorderColor = DittoColors.PrimaryBlue,
                uncheckedThumbColor = DittoColors.TextTertiary,
                uncheckedTrackColor = DittoColors.SurfaceMuted,
                uncheckedBorderColor = DittoColors.Border,
                disabledCheckedThumbColor = DittoColors.Surface,
                disabledCheckedTrackColor = DittoColors.SecondaryBlue
            )
        )
    }
}

@Composable
private fun IntegrationRow(name: String, status: String, active: Boolean) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            name,
            style = MaterialTheme.typography.bodyMedium,
            color = DittoColors.TextPrimary,
            modifier = Modifier.weight(1f)
        )
        StatusPill(
            status,
            if (active) DittoColors.Success else DittoColors.TextTertiary,
            if (active) DittoColors.SuccessBg else DittoColors.NeutralBg
        )
    }
}

@Composable
private fun EngineRow(label: String, value: String) {
    Row(Modifier.padding(vertical = 3.dp)) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextTertiary,
            modifier = Modifier.width(88.dp)
        )
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextSecondary,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun LinkRow(title: String, subtitle: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = DittoColors.TextSecondary
            )
        }
        Text("â†’", style = MaterialTheme.typography.titleMedium, color = DittoColors.SecondaryBlue)
    }
}

