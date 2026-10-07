package com.ditto.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.ContentKind
import com.ditto.app.ui.theme.DittoColors
import java.util.concurrent.TimeUnit

/** The standard case row used on Home, Cases, Scan results and Follow-up. */
@Composable
fun CaseCard(
    case: Case,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    showAction: Boolean = true,
    previewUri: String? = null,
    previewKind: ContentKind? = null
) {
    val similarityAvailable = case.candidate.overallSimilarity.let { it.isFinite() && it in 0.0..1.0 }
    DittoCard(modifier = modifier, onClick = onClick) {
        Row(verticalAlignment = Alignment.Top) {
            if (previewKind == ContentKind.VIDEO) {
                Box(Modifier.size(64.dp).background(DittoColors.BackgroundAlt), contentAlignment = Alignment.Center) {
                    Text("Video", style = MaterialTheme.typography.labelSmall)
                }
            } else {
                EvidenceVisual(
                    seed = case.candidate.paletteSeed,
                    modifier = Modifier.size(64.dp),
                    localUri = previewUri,
                    label = "Private original",
                    cornerRadius = 6
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            text = case.candidate.accountHandle,
                            style = MaterialTheme.typography.titleMedium,
                            color = DittoColors.TextPrimary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "${case.candidate.platform} · ${case.id}",
                            style = MaterialTheme.typography.bodySmall,
                            color = DittoColors.TextSecondary,
                            maxLines = 1
                        )
                    }
                    StatePill(case.state)
                }

                Spacer(Modifier.height(10.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = if (similarityAvailable) "${case.similarityPct}%" else "Unavailable",
                        style = MaterialTheme.typography.titleLarge,
                        color = DittoColors.PrimaryBlue
                    )
                    Spacer(Modifier.width(4.dp))
                    Text(
                        text = "Content similarity",
                        style = MaterialTheme.typography.bodySmall,
                        color = DittoColors.TextSecondary
                    )
                    Spacer(Modifier.width(10.dp))
                    case.verification?.let { SeverityPill(it.severity) }
                }
            }
        }

        if (showAction && case.plan != null && case.plan.action != ActionType.LOG_ONLY) {
            Spacer(Modifier.height(12.dp))
            HairlineDivider()
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = actionLead(case.state),
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = case.plan.action.label,
                    style = MaterialTheme.typography.titleSmall,
                    color = DittoColors.PrimaryBlue,
                    modifier = Modifier.weight(1f)
                )
                Text(
                    text = "Review →",
                    style = MaterialTheme.typography.labelMedium,
                    color = DittoColors.SecondaryBlue
                )
            }
        }
    }
}

private fun actionLead(state: CaseState): String = when (state) {
    CaseState.PENDING_APPROVAL -> "Recommended:"
    CaseState.ESCALATED -> "Escalated to:"
    CaseState.SENT, CaseState.AWAITING_RESPONSE -> "Sent:"
    CaseState.RESOLVED -> "Resolved after:"
    else -> "Action:"
}

/**
 * Vertical lifecycle timeline. Every state in the report's lifecycle is shown; the
 * current one is highlighted and future states are drawn as hollow markers.
 */
@Composable
fun CaseStateTimeline(
    current: CaseState,
    modifier: Modifier = Modifier
) {
    // The canonical happy path; terminal variants swap in at the end.
    val path = listOf(
        CaseState.NEW,
        CaseState.VERIFIED,
        CaseState.PENDING_APPROVAL,
        CaseState.SENT,
        CaseState.AWAITING_RESPONSE,
        CaseState.ESCALATED,
        if (current == CaseState.CLOSED) CaseState.CLOSED else CaseState.RESOLVED
    )
    val currentIndex = path.indexOf(current).let { if (it == -1) 0 else it }

    Column(modifier.fillMaxWidth()) {
        path.forEachIndexed { index, state ->
            val reached = index <= currentIndex
            val isCurrent = index == currentIndex
            Row(verticalAlignment = Alignment.Top) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        Modifier
                            .size(if (isCurrent) 14.dp else 10.dp)
                            .clip(CircleShape)
                            .background(
                                when {
                                    isCurrent -> DittoColors.PrimaryBlue
                                    reached -> DittoColors.SecondaryBlue
                                    else -> DittoColors.SurfaceSunken
                                }
                            )
                    )
                    if (index != path.lastIndex) {
                        Box(
                            Modifier
                                .width(2.dp)
                                .height(26.dp)
                                .background(
                                    if (index < currentIndex) DittoColors.SecondaryBlue
                                    else DittoColors.SurfaceSunken
                                )
                        )
                    }
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.padding(bottom = if (index == path.lastIndex) 0.dp else 12.dp)) {
                    Text(
                        text = state.label,
                        style = if (isCurrent) MaterialTheme.typography.titleSmall
                        else MaterialTheme.typography.bodyMedium,
                        color = when {
                            isCurrent -> DittoColors.PrimaryBlue
                            reached -> DittoColors.TextPrimary
                            else -> DittoColors.TextTertiary
                        }
                    )
                    if (isCurrent) {
                        Text(
                            text = "Current state",
                            style = MaterialTheme.typography.bodySmall,
                            color = DittoColors.TextSecondary
                        )
                    }
                }
            }
        }
    }
}

/** Empty state: heading, body, optional action. Never a blank screen (report §41). */
@Composable
fun EmptyState(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        DittoMark(size = 40)
        Spacer(Modifier.height(18.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = DittoColors.TextPrimary,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = body,
            style = MaterialTheme.typography.bodyMedium,
            color = DittoColors.TextSecondary,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
        if (actionLabel != null && onAction != null) {
            Spacer(Modifier.height(20.dp))
            SecondaryButton(text = actionLabel, onClick = onAction)
        }
    }
}

/** Friendly relative time used across the activity feed and case rows. */
fun relativeTime(timestamp: Long, now: Long = System.currentTimeMillis()): String {
    val diff = now - timestamp
    if (diff < 0) {
        val ahead = -diff
        return when {
            ahead < TimeUnit.HOURS.toMillis(24) -> "today"
            ahead < TimeUnit.DAYS.toMillis(2) -> "tomorrow"
            else -> "in ${TimeUnit.MILLISECONDS.toDays(ahead)} days"
        }
    }
    return when {
        diff < TimeUnit.MINUTES.toMillis(1) -> "just now"
        diff < TimeUnit.HOURS.toMillis(1) ->
            "${TimeUnit.MILLISECONDS.toMinutes(diff)}m ago"
        diff < TimeUnit.DAYS.toMillis(1) ->
            "${TimeUnit.MILLISECONDS.toHours(diff)}h ago"
        diff < TimeUnit.DAYS.toMillis(2) -> "yesterday"
        diff < TimeUnit.DAYS.toMillis(30) ->
            "${TimeUnit.MILLISECONDS.toDays(diff)}d ago"
        else -> "${TimeUnit.MILLISECONDS.toDays(diff) / 30}mo ago"
    }
}

fun clockTime(timestamp: Long): String =
    java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault())
        .format(java.util.Date(timestamp))

/** Animated counter used on the dashboard so figures feel live. */
@Composable
fun AnimatedCount(value: Int): String {
    val animated by animateFloatAsState(
        targetValue = value.toFloat(),
        animationSpec = tween(700),
        label = "count"
    )
    return animated.toInt().toString()
}
