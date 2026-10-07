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
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.BuildConfig
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.DittoMark
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.StatusPill
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.ui.theme.HandwritingStyle
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
    val signOut=LocalSignOut.current

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
            Row(verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(18.dp)).background(DittoColors.Surface.copy(alpha=.88f)),contentAlignment=Alignment.Center) { DittoMark(size=42) }
                Spacer(Modifier.width(12.dp))
                Column {
                    Eyebrow("Profile")
                    Text("Your creator space",style=MaterialTheme.typography.displaySmall,color=DittoColors.TextPrimary)
                }
            }
            Text(
                "everything in one place",
                style = HandwritingStyle.copy(fontSize = 28.sp, lineHeight = 31.sp),
                color = DittoColors.SecondaryBlue
            )
        }

        item {
            SecondaryButton(text="How to use Ditto",onClick={showGuide=true},modifier=Modifier.fillMaxWidth())
        }
        if (connected) {
            item { InstagramConnectionCard() }
            item { AccountSecurityCard() }
        }
        // ---- profile ----
        item {
            DittoCard(background=DittoColors.BlueTint.copy(alpha=.90f),borderColor=DittoColors.LightBlue) {
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
                            if(connected) "Ditto member" else settings.creatorName,
                            style = MaterialTheme.typography.titleMedium,
                            color = DittoColors.TextPrimary
                        )
                        Text(
                            if(connected) "Private Ditto account" else settings.creatorHandle,
                            style = MaterialTheme.typography.bodySmall,
                            color = DittoColors.TextSecondary
                        )
                    }
                    if(connected) StatusPill("Private",DittoColors.Aqua,DittoColors.AquaTint)
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

        item {
            DittoCard {
                Eyebrow("Privacy")
                Text("Your originals and case records are private to your account. Cases are created when you request a comparison. Review evidence before approving any action.",style=MaterialTheme.typography.bodySmall)
            }
        }

        // ---- links ----
        item {
            DittoCard(contentPadding = 0) {
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
                    "Upload your originals, search for possible copies and review the evidence before taking action.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextTertiary
                )
            }
        }
        item {
            SecondaryButton(text="Log out",onClick=signOut,modifier=Modifier.fillMaxWidth())
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
        Text("›", style = MaterialTheme.typography.titleLarge, color = DittoColors.SecondaryBlue)
    }
}

