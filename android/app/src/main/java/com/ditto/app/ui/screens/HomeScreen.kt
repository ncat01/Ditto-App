package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.AgentKind
import com.ditto.app.ui.components.CaseCard
import com.ditto.app.ui.components.DemoModeBanner
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.DittoMark
import com.ditto.app.ui.components.EmptyState
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.SectionHeading
import com.ditto.app.ui.components.StatTile
import com.ditto.app.ui.components.relativeTime
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel
import java.util.Calendar

@Composable
fun HomeScreen(
    vm: DittoViewModel,
    onOpenCase: (String) -> Unit,
    onSeeAllCases: () -> Unit,
    onOpenFollowUp: () -> Unit,
    onOpenAnalytics: () -> Unit,
    onOpenScan: () -> Unit
) {
    val stats by vm.stats.collectAsStateWithLifecycle()
    val activity by vm.activity.collectAsStateWithLifecycle()
    val settings by vm.settings.collectAsStateWithLifecycle()
    val cases by vm.cases.collectAsStateWithLifecycle()
    val connected=com.ditto.app.core.BackendConnection(androidx.compose.ui.platform.LocalContext.current).enabled()
    val attention = remember(cases) { DittoViewModel.needingAttention(cases).take(3) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            top = 24.dp, bottom = 28.dp
        ),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                DittoMark(size = 48)
                Spacer(Modifier.width(8.dp))
                Text("ditto", style = MaterialTheme.typography.displayMedium, color = DittoColors.TextPrimary)
                Spacer(Modifier.weight(1f))
                com.ditto.app.ui.components.StatusPill("Creator space", DittoColors.DeepBlue, DittoColors.LightBlue)
            }
            Spacer(Modifier.height(20.dp))
            com.ditto.app.ui.components.CreatorHero(greeting(), onOpenScan)
        }

        item {
            DemoModeBanner(
                if(connected) "Connected sandbox — server data, synthetic discovery and no live outreach."
                else if (settings.demoMode)
                    "Demo Mode — synthetic discovery corpus. No live platform actions are sent."
                else
                    "Live providers are not configured. Scans continue to use the demo corpus."
            )
        }

        item {
            Box(Modifier.fillMaxWidth().clip(androidx.compose.foundation.shape.RoundedCornerShape(20.dp))
                .background(androidx.compose.ui.graphics.Brush.horizontalGradient(listOf(androidx.compose.ui.graphics.Color(0xFFFFD6E5),androidx.compose.ui.graphics.Color(0xFFFFDFCB),androidx.compose.ui.graphics.Color(0xFFFFEDB8)))).clickable(onClick=onSeeAllCases).padding(20.dp)) {
                Column {
                    Text("${stats.pendingApproval + stats.escalated} approvals need you",style=MaterialTheme.typography.titleLarge,color=DittoColors.TextPrimary)
                    Text("Review the evidence and exact message before any sandbox action.",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary)
                }
            }
        }
        // --- summary grid ---
        item {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatTile(
                        value = stats.contentMonitored.toString(),
                        label = "Content monitored",
                        modifier = Modifier.weight(1f),
                        onClick = onOpenScan
                    )
                    StatTile(
                        value = stats.openCases.toString(),
                        label = "Open cases",
                        modifier = Modifier.weight(1f),
                        onClick = onSeeAllCases
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatTile(
                        value = stats.awaitingResponse.toString(),
                        label = "Awaiting response",
                        modifier = Modifier.weight(1f),
                        accent = DittoColors.SecondaryBlue,
                        onClick = onOpenFollowUp
                    )
                    StatTile(
                        value = stats.resolved.toString(),
                        label = "Resolved",
                        modifier = Modifier.weight(1f),
                        accent = DittoColors.Success,
                        onClick = onOpenAnalytics
                    )
                }
            }
        }

        // --- agent activity ---
        item {
            SectionHeading(
                title = "Behind the scenes"
            )
        }
        item {
            DittoCard {
                if (activity.isEmpty()) {
                    Text(
                        "Your agent activity will appear here.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )
                } else {
                    activity.take(4).forEachIndexed { index, event ->
                        AgentTimelineRow(
                            event = event,
                            isLast = index == activity.take(4).lastIndex
                        )
                    }
                }
            }
        }

        // --- cases needing attention ---
        item {
            SectionHeading(
                title = "Cases needing attention",
                trailing = {
                    Text(
                        "All cases",
                        style = MaterialTheme.typography.labelMedium,
                        color = DittoColors.SecondaryBlue,
                        modifier = Modifier.clickable(onClick = onSeeAllCases)
                    )
                }
            )
        }

        if (attention.isEmpty()) {
            item {
                DittoCard {
                    Text(
                        "You're all clear.",
                        style = MaterialTheme.typography.titleMedium,
                        color = DittoColors.TextPrimary
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        if (cases.isEmpty())
                            "No content-credit cases yet. Run a scan to start monitoring."
                        else "Nothing is waiting on your approval right now.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )
                }
            }
        } else {
            items(attention, key = { it.id }) { case ->
                CaseCard(case = case, onClick = { onOpenCase(case.id) })
            }
        }

        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun AgentTimelineRow(event: ActivityEvent, isLast: Boolean) {
    Row(verticalAlignment = Alignment.Top) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(event.agent.dotColor())
            )
            if (!isLast) {
                Box(
                    Modifier
                        .width(1.dp)
                        .height(34.dp)
                        .background(DittoColors.BorderSubtle)
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.padding(bottom = if (isLast) 0.dp else 10.dp)) {
            Text(
                text = event.title,
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
            Text(
                text = "${event.agent.label} · ${relativeTime(event.timestamp)}",
                style = MaterialTheme.typography.bodySmall,
                color = DittoColors.TextSecondary
            )
        }
    }
}

internal fun AgentKind.dotColor() = when (this) {
    AgentKind.INGESTION -> DittoColors.TextTertiary
    AgentKind.DISCOVERY -> DittoColors.SecondaryBlue
    AgentKind.VERIFICATION -> DittoColors.PrimaryBlue
    AgentKind.ACTION_PLANNING -> DittoColors.Warning
    AgentKind.FOLLOW_UP -> DittoColors.DeepBlue
    AgentKind.HUMAN -> DittoColors.Success
}

private fun greeting(): String {
    val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    return when {
        hour < 12 -> "Good morning"
        hour < 17 -> "Good afternoon"
        else -> "Good evening"
    }
}
