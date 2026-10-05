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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.EmptyState
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.clockTime
import com.ditto.app.ui.components.relativeTime
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

@Composable
fun ActivityScreen(vm: DittoViewModel, onOpenCase: (String) -> Unit) {
    val activity by vm.activity.collectAsStateWithLifecycle()
    val engines = vm.engineNames

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Eyebrow("Activity")
            Spacer(Modifier.height(6.dp))
            Text(
                "Agent activity",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "Every autonomous decision Ditto has made, in order.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }

        item {
            DittoCard(background = DittoColors.BackgroundAlt) {
                Eyebrow("Active engines")
                Spacer(Modifier.height(8.dp))
                EngineLine("Matching", engines.matcher)
                EngineLine("Discovery", engines.discovery)
                EngineLine("Verification", engines.verification)
            }
        }

        if (activity.isEmpty()) {
            item {
                EmptyState(
                    title = "Nothing yet.",
                    body = "Your agent activity will appear here as Ditto scans, verifies and follows up."
                )
            }
        } else {
            items(activity, key = { it.id }) { event ->
                ActivityRow(
                    event = event,
                    onClick = { event.caseId?.let(onOpenCase) }
                )
            }
        }
    }
}

@Composable
private fun EngineLine(label: String, value: String) {
    Row(Modifier.padding(vertical = 3.dp)) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextTertiary,
            modifier = Modifier.width(92.dp)
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
private fun ActivityRow(event: ActivityEvent, onClick: () -> Unit) {
    DittoCard(
        onClick = if (event.caseId != null) onClick else null,
        contentPadding = 14
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    clockTime(event.timestamp),
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextTertiary
                )
                Spacer(Modifier.height(6.dp))
                Box(
                    Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(event.agent.dotColor())
                )
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    event.agent.label,
                    style = MaterialTheme.typography.labelSmall,
                    color = DittoColors.SecondaryBlue
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    event.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = DittoColors.TextPrimary
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    event.detail,
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
            Text(
                relativeTime(event.timestamp),
                style = MaterialTheme.typography.bodySmall,
                color = DittoColors.TextTertiary
            )
        }
    }
}
