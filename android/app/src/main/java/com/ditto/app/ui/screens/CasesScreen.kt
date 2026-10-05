package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.ui.components.CaseCard
import com.ditto.app.ui.components.EmptyState
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

private enum class CaseFilter(val label: String, val states: Set<CaseState>?) {
    ALL("All", null),
    NEW("New", setOf(CaseState.NEW, CaseState.VERIFIED)),
    PENDING("Pending", setOf(CaseState.PENDING_APPROVAL)),
    AWAITING("Awaiting", setOf(CaseState.SENT, CaseState.AWAITING_RESPONSE)),
    ESCALATED("Escalated", setOf(CaseState.ESCALATED)),
    RESOLVED("Resolved", setOf(CaseState.RESOLVED, CaseState.CLOSED))
}

private enum class CaseSort(val label: String) {
    UPDATED("Last updated"),
    CONFIDENCE("Confidence"),
    SEVERITY("Severity"),
    NEWEST("Newest")
}

@Composable
fun CasesScreen(vm: DittoViewModel, onOpenCase: (String) -> Unit) {
    val cases by vm.cases.collectAsStateWithLifecycle()
    var filter by remember { mutableStateOf(CaseFilter.ALL) }
    var sort by remember { mutableStateOf(CaseSort.UPDATED) }
    var query by remember { mutableStateOf("") }

    var severity by remember { mutableStateOf("Any severity") }
    var category by remember { mutableStateOf("Any category") }
    var confidence by remember { mutableStateOf("Any confidence") }
    val visible = remember(cases, filter, sort, query, severity, category, confidence) {
        cases
            .filter { case -> filter.states?.contains(case.state) ?: true }
            .filter { severity=="Any severity" || it.verification?.severity?.label==severity }
            .filter { category=="Any category" || it.verification?.classification?.label==category }
            .filter { confidence=="Any confidence" || (if(confidence=="High rule score") (it.verification?.confidence ?: 0.0)>=.8 else (it.verification?.confidence ?: 0.0)<.8) }
            .filter { case ->
                query.isBlank() || listOf(
                    case.id,
                    case.candidate.accountHandle,
                    case.candidate.accountName,
                    case.candidate.platform,
                    case.contentTitle
                ).any { it.contains(query, ignoreCase = true) }
            }
            .sortedWith(
                when (sort) {
                    CaseSort.UPDATED -> compareByDescending { it.updatedAt }
                    CaseSort.NEWEST -> compareByDescending { it.createdAt }
                    CaseSort.CONFIDENCE -> compareByDescending {
                        it.verification?.confidence ?: 0.0
                    }
                    CaseSort.SEVERITY -> compareByDescending {
                        it.verification?.severity?.rank ?: 0
                    }
                }
            )
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Eyebrow("Cases")
            Spacer(Modifier.height(6.dp))
            Text(
                "Case management",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "${cases.count { it.state.isOpen }} open · ${cases.size} total",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }

        item {
            Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                androidx.compose.material3.TextButton(onClick={ val choices=listOf("Any severity","Low","Medium","High");severity=choices[(choices.indexOf(severity)+1)%choices.size] }) { Text(severity) }
                androidx.compose.material3.TextButton(onClick={ val choices=listOf("Any category","Genuine Repost","Simulated Likeness Misuse","False Positive");category=choices[(choices.indexOf(category)+1)%choices.size] }) { Text(category) }
                androidx.compose.material3.TextButton(onClick={ val choices=listOf("Any confidence","High rule score","Needs review");confidence=choices[(choices.indexOf(confidence)+1)%choices.size] }) { Text(confidence) }
            }
        }
        item {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = {
                    Text(
                        "Search account, case ID or platform",
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextTertiary
                    )
                },
                singleLine = true,
                textStyle = MaterialTheme.typography.bodyMedium.copy(
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
        }

        item {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CaseFilter.entries.forEach { f ->
                    val count = cases.count { f.states?.contains(it.state) ?: true }
                    FilterChip(
                        label = "${f.label} $count",
                        selected = filter == f,
                        onClick = { filter = f }
                    )
                }
            }
        }

        item {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Sort",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextTertiary
                )
                CaseSort.entries.forEach { s ->
                    Text(
                        text = s.label,
                        style = MaterialTheme.typography.labelMedium,
                        color = if (sort == s) DittoColors.PrimaryBlue
                        else DittoColors.TextTertiary,
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .clickable { sort = s }
                            .padding(horizontal = 6.dp, vertical = 4.dp)
                    )
                }
            }
        }

        if (visible.isEmpty()) {
            item {
                EmptyState(
                    title = if (cases.isEmpty()) "You're all clear."
                    else "Nothing matches that view.",
                    body = if (cases.isEmpty())
                        "No active content-credit cases right now. Run a scan to start monitoring."
                    else "Try a different filter or clear your search."
                )
            }
        } else {
            items(visible, key = { it.id }) { case ->
                CaseCard(case = case, onClick = { onOpenCase(case.id) })
            }
        }
    }
}

@Composable
private fun FilterChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (selected) DittoColors.PrimaryBlue else DittoColors.Surface)
            .border(
                1.dp,
                if (selected) DittoColors.PrimaryBlue else DittoColors.Border,
                RoundedCornerShape(6.dp)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = if (selected) DittoColors.TextOnDark else DittoColors.TextSecondary
        )
    }
}
