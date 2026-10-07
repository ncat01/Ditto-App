package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
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
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.PrimaryButton
import com.ditto.app.ui.components.SecondaryButton
import com.ditto.app.ui.theme.DittoColors

/** Review an exact message through the configured delivery provider. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalSheet(
    case: Case,
    onDismiss: () -> Unit,
    onApprove: () -> Unit
) {
    val plan = case.plan ?: return
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = DittoColors.BackgroundAlt,
        dragHandle = null
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(top = 20.dp, bottom = 28.dp)
        ) {
            Eyebrow("Approval required")
            Spacer(Modifier.height(8.dp))
            Text(
                "Approve ${plan.action.label.lowercase()}?",
                style = MaterialTheme.typography.headlineMedium,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(18.dp))

            DetailLine("Recipient", case.candidate.accountHandle)
            DetailLine("Platform", case.candidate.platform)
            DetailLine("Action", plan.action.label)
            DetailLine("Tone", plan.tone.label)
            DetailLine("Case", case.id)

            Spacer(Modifier.height(16.dp))
            HairlineDivider()
            Spacer(Modifier.height(16.dp))

            Text(
                "Draft message",
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(8.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .heightIn(max = 240.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(DittoColors.Surface)
                    .border(1.dp, DittoColors.Border, RoundedCornerShape(8.dp))
                    .verticalScroll(rememberScrollState())
                    .padding(14.dp)
            ) {
                Text(
                    plan.draftBody,
                    style = MaterialTheme.typography.bodySmall.copy(
                        fontFamily = FontFamily.Monospace
                    ),
                    color = DittoColors.TextPrimary
                )
            }

            Spacer(Modifier.height(14.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(DittoColors.WarningBg)
                    .padding(12.dp)
            ) {
                Text(
                    "Review the exact recipient and message before approving. Unavailable delivery channels cannot send.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.Warning
                )
            }

            Spacer(Modifier.height(20.dp))
            EmailOutreachCard(case.id, plan.draftBody)
            Spacer(Modifier.height(10.dp))
            SecondaryButton(
                text = "Defer for now",
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

/** Action draft editor with tone selection (report §19). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DraftEditorSheet(
    initialBody: String,
    initialTone: MessageTone,
    actionLabel: String,
    onDismiss: () -> Unit,
    onSave: (String, MessageTone) -> Unit,
    onApprove: (String, MessageTone) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var body by remember { mutableStateOf(initialBody) }
    var tone by remember { mutableStateOf(initialTone) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = DittoColors.BackgroundAlt,
        dragHandle = null
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(top = 20.dp, bottom = 28.dp)
        ) {
            Eyebrow("Edit draft")
            Spacer(Modifier.height(8.dp))
            Text(
                actionLabel,
                style = MaterialTheme.typography.headlineMedium,
                color = DittoColors.TextPrimary
            )

            Spacer(Modifier.height(18.dp))
            Text(
                "Tone",
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MessageTone.entries.forEach { option ->
                    ToneChip(
                        label = option.label,
                        selected = tone == option,
                        onClick = { tone = option },
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            Spacer(Modifier.height(18.dp))
            OutlinedTextField(
                value = body,
                onValueChange = { body = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 200.dp, max = 320.dp),
                textStyle = MaterialTheme.typography.bodySmall.copy(
                    fontFamily = FontFamily.Monospace,
                    color = DittoColors.TextPrimary
                ),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = DittoColors.SecondaryBlue,
                    unfocusedBorderColor = DittoColors.Border,
                    focusedContainerColor = DittoColors.Surface,
                    unfocusedContainerColor = DittoColors.Surface,
                    cursorColor = DittoColors.PrimaryBlue
                ),
                shape = RoundedCornerShape(8.dp)
            )

            Spacer(Modifier.height(18.dp))
            PrimaryButton(
                text = "Save & approve",
                onClick = { onApprove(body, tone) },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton(
                    text = "Save draft",
                    onClick = { onSave(body, tone) },
                    modifier = Modifier.weight(1f)
                )
                SecondaryButton(
                    text = "Defer for now",
                    onClick = onDismiss,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

/** Follow-up observations require real evidence from a configured provider. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FollowUpSheet(onDismiss: () -> Unit, onPick: (FollowUpOutcome) -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = DittoColors.BackgroundAlt) {
        Column(Modifier.fillMaxWidth().padding(20.dp)) {
            Eyebrow("Follow-up")
            Text("Automatic re-check unavailable", style = MaterialTheme.typography.headlineMedium)
            Spacer(Modifier.height(12.dp))
            Text("No observation provider is connected for this case. Review new evidence before changing its status.", style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(20.dp))
            SecondaryButton(text = "Close", onClick = onDismiss, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun ToneChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (selected) DittoColors.PrimaryBlue else DittoColors.Surface)
            .border(
                1.dp,
                if (selected) DittoColors.PrimaryBlue else DittoColors.Border,
                RoundedCornerShape(6.dp)
            )
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = if (selected) DittoColors.TextOnDark else DittoColors.TextSecondary
        )
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextTertiary,
            modifier = Modifier.width(96.dp)
        )
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            color = DittoColors.TextPrimary,
            modifier = Modifier.weight(1f)
        )
    }
}
