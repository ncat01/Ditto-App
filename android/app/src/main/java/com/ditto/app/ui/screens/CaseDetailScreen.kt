package com.ditto.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.ui.components.CaseStateTimeline
import com.ditto.app.ui.components.ClassificationPill
import com.ditto.app.ui.components.ComparisonStrip
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.EvidenceTransform
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.MetricBar
import com.ditto.app.ui.components.PrimaryButton
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.components.SectionHeading
import com.ditto.app.ui.components.SeverityPill
import com.ditto.app.ui.components.SignalRow
import com.ditto.app.ui.components.StatePill
import com.ditto.app.ui.components.relativeTime
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.CaseDetailViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseDetailScreen(caseId: String, onBack: () -> Unit) {
    val vm: CaseDetailViewModel = viewModel(
        factory = CaseDetailViewModel.factory(caseId),
        key = caseId
    )
    val case by vm.case.collectAsStateWithLifecycle()
    val ui by vm.ui.collectAsStateWithLifecycle()

    var showApproval by remember { mutableStateOf(false) }
    var showEditor by remember { mutableStateOf(false) }
    var showFollowUp by remember { mutableStateOf(false) }
    var reasoningExpanded by remember { mutableStateOf(true) }
    var historyExpanded by remember { mutableStateOf(false) }
    var evidenceExpanded by remember { mutableStateOf(false) }

    val c = case
    if (c == null) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(20.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                "Case not found.",
                style = MaterialTheme.typography.headlineSmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "This case may have been removed. Go back and pick another.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
            Spacer(Modifier.height(18.dp))
            SecondaryButton(text = "Back to cases", onClick = onBack)
        }
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 20.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // ---------- header ----------
        item {
            Text(
                "← Back",
                style = MaterialTheme.typography.labelMedium,
                color = DittoColors.SecondaryBlue,
                modifier = Modifier.clickable(onClick = onBack)
            )
            Spacer(Modifier.height(14.dp))
            Eyebrow("Case ${c.id}")
            Spacer(Modifier.height(6.dp))
            Text(
                text = c.verification?.classification?.label ?: "Awaiting verification",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatePill(c.state)
                c.verification?.let { SeverityPill(it.severity) }
            }
        }

        // ---------- agent decision banner ----------
        ui.lastDecision?.let { headline ->
            item {
                AnimatedVisibility(visible = true, enter = fadeIn() + expandVertically()) {
                    DittoCard(
                        background = DittoColors.BlueTint,
                        borderColor = DittoColors.LightBlue
                    ) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                headline,
                                style = MaterialTheme.typography.titleMedium,
                                color = DittoColors.PrimaryBlue,
                                modifier = Modifier.weight(1f)
                            )
                            Text(
                                "✕",
                                style = MaterialTheme.typography.labelMedium,
                                color = DittoColors.SecondaryBlue,
                                modifier = Modifier.clickable { vm.dismissDecision() }
                            )
                        }
                        ui.lastDecisionDetail?.takeIf { it.isNotBlank() }?.let {
                            Spacer(Modifier.height(6.dp))
                            Text(
                                it,
                                style = MaterialTheme.typography.bodyMedium,
                                color = DittoColors.TextSecondary
                            )
                        }
                    }
                }
            }
        }

        ui.error?.let { message ->
            item {
                DittoCard(
                    background = DittoColors.DangerBg,
                    borderColor = DittoColors.Danger.copy(alpha = 0.3f)
                ) {
                    Text(
                        "That action isn't available.",
                        style = MaterialTheme.typography.titleMedium,
                        color = DittoColors.Danger
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        message,
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "Dismiss",
                        style = MaterialTheme.typography.labelMedium,
                        color = DittoColors.SecondaryBlue,
                        modifier = Modifier.clickable { vm.dismissError() }
                    )
                }
            }
        }

        // ---------- evidence comparison ----------
        item {
            SectionHeading("Evidence")
        }
        item {
            DittoCard {
                com.ditto.app.ui.components.VideoComparison(c)
                Spacer(Modifier.height(12.dp))
                Text(
                    c.candidate.transformNote,
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
                Spacer(Modifier.height(14.dp))
                HairlineDivider()
                Spacer(Modifier.height(14.dp))

                MetricBar("Content similarity", c.candidate.overallSimilarity)
                Spacer(Modifier.height(12.dp))
                MetricBar("Visual match", c.candidate.visualSimilarity)
                Spacer(Modifier.height(12.dp))
                MetricBar("Hash similarity", c.candidate.hashSimilarity)
                Spacer(Modifier.height(12.dp))
                if(c.candidate.platform != "Submitted evidence") MetricBar("Caption similarity", c.candidate.captionSimilarity)
                else Text("Caption, account identity and permission have not been verified.",style=MaterialTheme.typography.bodySmall)
                c.verification?.let {
                    Spacer(Modifier.height(12.dp))
                    MetricBar(
                        "Rule confidence (uncalibrated)",
                        it.confidence,
                        barColor = DittoColors.PrimaryBlue
                    )
                }

                Spacer(Modifier.height(14.dp))
                ExpandRow(
                    label = if (evidenceExpanded) "Hide metadata" else "Show metadata",
                    expanded = evidenceExpanded,
                    onToggle = { evidenceExpanded = !evidenceExpanded }
                )
                AnimatedVisibility(
                    visible = evidenceExpanded,
                    enter = fadeIn() + expandVertically(),
                    exit = fadeOut() + shrinkVertically()
                ) {
                    Column {
                        Spacer(Modifier.height(10.dp))
                        MetaRow("Platform", c.candidate.platform)
                        MetaRow("Account", "${c.candidate.accountName} ${c.candidate.accountHandle}")
                        MetaRow("Followers", if(c.candidate.platform == "Submitted evidence") "Unknown" else formatFollowers(c.candidate.followerCount))
                        MetaRow(
                            "Monetization",
                            if(c.candidate.platform == "Submitted evidence") "Unknown" else if (c.candidate.monetized) "Indicators present" else "None detected"
                        )
                        MetaRow("Source", c.candidate.sourceUrl)
                        MetaRow("Caption", c.candidate.caption)
                        MetaRow("Detected post", if(c.candidate.platform == "Submitted evidence") "Posting date unknown" else relativeTime(c.candidate.postedAt))
                        MetaRow("Original content", c.contentTitle)
                        MetaRow("Discovered", relativeTime(c.candidate.discoveredAt))
                    }
                }
            }
        }

        // ---------- verification agent ----------
        c.verification?.let { v ->
            item {
                SectionHeading("Verification Agent")
            }
            item {
                DittoCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        ClassificationPill(v.classification)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "${(v.confidence * 100).toInt()}% rule confidence",
                            style = MaterialTheme.typography.titleSmall,
                            color = DittoColors.TextPrimary
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    Text(
                        "Decision summary",
                        style = MaterialTheme.typography.titleSmall,
                        color = DittoColors.TextPrimary
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        v.summary,
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )

                    Spacer(Modifier.height(14.dp))
                    ExpandRow(
                        label = if (reasoningExpanded) "Hide signals considered"
                        else "Show signals considered",
                        expanded = reasoningExpanded,
                        onToggle = { reasoningExpanded = !reasoningExpanded }
                    )
                    AnimatedVisibility(
                        visible = reasoningExpanded,
                        enter = fadeIn() + expandVertically(),
                        exit = fadeOut() + shrinkVertically()
                    ) {
                        Column {
                            Spacer(Modifier.height(6.dp))
                            v.signals.forEach { s ->
                                SignalRow(s.name, s.value, s.supportsMatch)
                            }
                            Spacer(Modifier.height(8.dp))
                            HairlineDivider()
                            Spacer(Modifier.height(10.dp))
                            Text(
                                v.evidenceSummary,
                                style = MaterialTheme.typography.bodySmall,
                                color = DittoColors.TextSecondary
                            )
                            Spacer(Modifier.height(10.dp))
                            Text(
                                v.engine,
                                style = MaterialTheme.typography.bodySmall,
                                color = DittoColors.TextTertiary
                            )
                        }
                    }
                }
            }
        }

        // ---------- action planning agent ----------
        c.plan?.let { plan ->
            item { SectionHeading("Action-Planning Agent") }
            item {
                DittoCard {
                    Eyebrow(
                        if (c.state == CaseState.PENDING_APPROVAL) "Recommended action"
                        else "Action"
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        plan.action.label,
                        style = MaterialTheme.typography.headlineSmall,
                        color = DittoColors.PrimaryBlue
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        plan.reasoning,
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )
                    if (plan.factors.isNotEmpty()) {
                        Spacer(Modifier.height(14.dp))
                        HairlineDivider()
                        Spacer(Modifier.height(10.dp))
                        Text(
                            "Policy factors",
                            style = MaterialTheme.typography.titleSmall,
                            color = DittoColors.TextPrimary
                        )
                        Spacer(Modifier.height(6.dp))
                        plan.factors.forEach { f ->
                            Row(Modifier.padding(vertical = 3.dp)) {
                                Text(
                                    "·",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = DittoColors.SecondaryBlue
                                )
                                Spacer(Modifier.width(8.dp))
                                Text(
                                    f,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = DittoColors.TextSecondary
                                )
                            }
                        }
                    }
                    Spacer(Modifier.height(10.dp))
                    Text(
                        plan.engine,
                        style = MaterialTheme.typography.bodySmall,
                        color = DittoColors.TextTertiary
                    )
                }
            }

            // ---------- human approval gate ----------
            if (c.state == CaseState.PENDING_APPROVAL || c.state == CaseState.ESCALATED) {
                if (plan.action != ActionType.LOG_ONLY) {
                    item {
                        DittoCard(
                            background = DittoColors.BackgroundAlt,
                            borderColor = DittoColors.Border
                        ) {
                            Eyebrow("Human approval required", color = DittoColors.Warning)
                            Spacer(Modifier.height(6.dp))
                            Text(
                                "Nothing is sent until you approve.",
                                style = MaterialTheme.typography.titleMedium,
                                color = DittoColors.TextPrimary
                            )
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "Ditto drafts and recommends. The decision to act is yours.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = DittoColors.TextSecondary
                            )
                            Spacer(Modifier.height(16.dp))
                            if(com.ditto.app.core.BackendConnection(androidx.compose.ui.platform.LocalContext.current).enabled()) {
                                GeminiDraftButton(caseId, !ui.busy) { body -> vm.saveDraft(body, c.plan.tone) }
                                EmailOutreachCard(caseId, c.plan.draftBody)
                                Spacer(Modifier.height(10.dp))
                            }
                            if(!com.ditto.app.core.BackendConnection(androidx.compose.ui.platform.LocalContext.current).enabled()) {
                            PrimaryButton(
                                text = "Approve action",
                                onClick = { showApproval = true },
                                enabled = !ui.busy,
                                modifier = Modifier.fillMaxWidth()
                            )
                            }
                            Spacer(Modifier.height(10.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                SecondaryButton(
                                    text = "Edit draft",
                                    onClick = { showEditor = true },
                                    enabled = !ui.busy,
                                    modifier = Modifier.weight(1f)
                                )
                                SecondaryButton(
                                    text = "Reject",
                                    onClick = { vm.reject(null) },
                                    enabled = !ui.busy,
                                    contentColor = DittoColors.Danger,
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }
                    }
                }
            }
        }

        // ---------- follow-up ----------
        if (c.state == CaseState.AWAITING_RESPONSE || c.state == CaseState.ESCALATED) {
            item { SectionHeading("Follow-Up Agent") }
            item {
                DittoCard {
                    Row(Modifier.fillMaxWidth()) {
                        Column(Modifier.weight(1f)) {
                            Eyebrow("Last action")
                            Text(
                                c.lastActionAt?.let { relativeTime(it) } ?: "—",
                                style = MaterialTheme.typography.titleSmall,
                                color = DittoColors.TextPrimary
                            )
                        }
                        Column(Modifier.weight(1f)) {
                            Eyebrow("Next check")
                            Text(
                                c.nextFollowUpAt?.let { relativeTime(it) } ?: "—",
                                style = MaterialTheme.typography.titleSmall,
                                color = DittoColors.TextPrimary
                            )
                        }
                        Column(Modifier.weight(1f)) {
                            Eyebrow("Cycles")
                            Text(
                                c.followUpCount.toString(),
                                style = MaterialTheme.typography.titleSmall,
                                color = DittoColors.TextPrimary
                            )
                        }
                    }
                    Spacer(Modifier.height(14.dp))
                    Text(
                        "The weekly re-check runs on a schedule. Run it now to see the agent " +
                            "decide with a simulated outcome.",
                        style = MaterialTheme.typography.bodySmall,
                        color = DittoColors.TextSecondary
                    )
                    Spacer(Modifier.height(14.dp))
                    PrimaryButton(
                        text = "Simulate weekly follow-up",
                        onClick = { showFollowUp = true },
                        enabled = !ui.busy,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // ---------- lifecycle ----------
        item { SectionHeading("Case lifecycle") }
        item {
            DittoCard {
                CaseStateTimeline(current = c.state)
            }
        }

        // ---------- history ----------
        item {
            DittoCard {
                ExpandRow(
                    label = "Case history (${c.history.size})",
                    expanded = historyExpanded,
                    onToggle = { historyExpanded = !historyExpanded }
                )
                AnimatedVisibility(
                    visible = historyExpanded,
                    enter = fadeIn() + expandVertically(),
                    exit = fadeOut() + shrinkVertically()
                ) {
                    Column {
                        Spacer(Modifier.height(12.dp))
                        c.history.forEach { h ->
                            Column(Modifier.padding(bottom = 14.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(
                                        Modifier
                                            .size(6.dp)
                                            .clip(CircleShape)
                                            .background(h.agent.dotColor())
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text(
                                        h.action,
                                        style = MaterialTheme.typography.titleSmall,
                                        color = DittoColors.TextPrimary,
                                        modifier = Modifier.weight(1f)
                                    )
                                    Text(
                                        relativeTime(h.timestamp),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = DittoColors.TextTertiary
                                    )
                                }
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "${h.agent.label}" +
                                        if (h.previousState != null && h.newState != null &&
                                            h.previousState != h.newState
                                        ) " · ${h.previousState.label} → ${h.newState.label}"
                                        else "",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = DittoColors.SecondaryBlue,
                                    modifier = Modifier.padding(start = 14.dp)
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    h.reasoning,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = DittoColors.TextSecondary,
                                    modifier = Modifier.padding(start = 14.dp)
                                )
                            }
                        }
                    }
                }
            }
        }

        // ---------- manual resolve ----------
        if (c.state == CaseState.AWAITING_RESPONSE || c.state == CaseState.ESCALATED ||
            c.state == CaseState.SENT
        ) {
            item {
                SecondaryButton(
                    text = "Mark as resolved",
                    onClick = { vm.resolve(null) },
                    enabled = !ui.busy,
                    contentColor = DittoColors.Success,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }

    // ---------- approval sheet ----------
    if (showApproval && c.plan != null) {
        ApprovalSheet(
            case = c,
            onDismiss = { showApproval = false },
            onApprove = {
                showApproval = false
                vm.approve(null, null)
            }
        )
    }

    // ---------- draft editor ----------
    if (showEditor && c.plan != null) {
        DraftEditorSheet(
            initialBody = c.plan.draftBody,
            initialTone = c.plan.tone,
            actionLabel = c.plan.action.label,
            onDismiss = { showEditor = false },
            onSave = { body, tone ->
                showEditor = false
                vm.saveDraft(body, tone)
            },
            onApprove = { body, tone ->
                showEditor = false
                vm.approve(body, tone)
            }
        )
    }

    // ---------- follow-up outcome sheet ----------
    if (showFollowUp) {
        FollowUpSheet(
            onDismiss = { showFollowUp = false },
            onPick = { outcome ->
                showFollowUp = false
                vm.runFollowUp(outcome)
            }
        )
    }
}

@Composable
private fun ExpandRow(label: String, expanded: Boolean, onToggle: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onToggle),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = DittoColors.SecondaryBlue
        )
        Text(
            if (expanded) "−" else "+",
            style = MaterialTheme.typography.titleMedium,
            color = DittoColors.SecondaryBlue
        )
    }
}

@Composable
private fun MetaRow(label: String, value: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextTertiary,
            modifier = Modifier.width(110.dp)
        )
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextPrimary,
            modifier = Modifier.weight(1f)
        )
    }
}

private fun formatFollowers(n: Int): String = when {
    n >= 1_000_000 -> "${n / 100_000 / 10.0}M"
    n >= 1_000 -> "${n / 1_000}K"
    else -> n.toString()
}
