package com.ditto.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.EmptyState
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.StatePill
import com.ditto.app.ui.components.relativeTime
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

/**
 * The follow-up queue (report §21). Each row shows what the persistence agent is
 * tracking; opening a case runs the actual state machine.
 */
@Composable
fun FollowUpScreen(
    vm: DittoViewModel,
    onBack: () -> Unit,
    onOpenCase: (String) -> Unit
) {
    val cases by vm.cases.collectAsStateWithLifecycle()
    val awaiting = remember(cases) { DittoViewModel.awaitingResponse(cases) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 20.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                "← Back",
                style = MaterialTheme.typography.labelMedium,
                color = DittoColors.SecondaryBlue,
                modifier = Modifier.clickable(onClick = onBack)
            )
            Spacer(Modifier.height(14.dp))
            Eyebrow("Follow-Up Agent")
            Spacer(Modifier.height(6.dp))
            Text(
                if (awaiting.isEmpty()) "No cases awaiting response"
                else "${awaiting.size} case${if (awaiting.size == 1) "" else "s"} awaiting response",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "The agent re-evaluates each open case on a weekly schedule and decides " +
                    "whether to wait, nudge, escalate or resolve.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }

        if (awaiting.isEmpty()) {
            item {
                EmptyState(
                    title = "Nothing to chase.",
                    body = "No case is currently waiting on a response. Approved actions " +
                        "will appear here for weekly follow-up.",
                    actionLabel = "Back to dashboard",
                    onAction = onBack
                )
            }
        } else {
            items(awaiting, key = { it.id }) { case ->
                DittoCard(onClick = { onOpenCase(case.id) }) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                case.candidate.accountHandle,
                                style = MaterialTheme.typography.titleMedium,
                                color = DittoColors.TextPrimary
                            )
                            Text(
                                "${case.candidate.platform} · ${case.id}",
                                style = MaterialTheme.typography.bodySmall,
                                color = DittoColors.TextSecondary
                            )
                        }
                        StatePill(case.state)
                    }
                    Spacer(Modifier.height(12.dp))
                    HairlineDivider()
                    Spacer(Modifier.height(12.dp))
                    Row(Modifier.fillMaxWidth()) {
                        FollowUpStat(
                            "Last action",
                            case.lastActionAt?.let { relativeTime(it) } ?: "—",
                            Modifier.weight(1f)
                        )
                        FollowUpStat(
                            "Next check",
                            case.nextFollowUpAt?.let { relativeTime(it) } ?: "—",
                            Modifier.weight(1f)
                        )
                        FollowUpStat(
                            "Cycles run",
                            case.followUpCount.toString(),
                            Modifier.weight(1f)
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    SecondaryButton(
                        text = "Run follow-up",
                        onClick = { onOpenCase(case.id) },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }
    }
}

@Composable
private fun FollowUpStat(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier) {
        Eyebrow(label)
        Spacer(Modifier.height(2.dp))
        Text(
            value,
            style = MaterialTheme.typography.titleSmall,
            color = DittoColors.TextPrimary
        )
    }
}
