package com.ditto.app.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.domain.model.CaseState
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.MetricBar
import com.ditto.app.ui.components.StatTile
import com.ditto.app.ui.components.pillColors
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

@Composable
fun AnalyticsScreen(vm: DittoViewModel, onBack: () -> Unit) {
    val stats by vm.stats.collectAsStateWithLifecycle()
    val cases by vm.cases.collectAsStateWithLifecycle()

    val distribution = CaseState.entries
        .map { state -> state to cases.count { it.state == state } }
        .filter { it.second > 0 }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 20.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                "← Back",
                style = MaterialTheme.typography.labelMedium,
                color = DittoColors.SecondaryBlue,
                modifier = Modifier.clickable(onClick = onBack)
            )
            Spacer(Modifier.height(14.dp))
            Eyebrow("Analytics")
            Spacer(Modifier.height(6.dp))
            Text(
                "Performance",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
        }

        item {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatTile(
                        stats.contentMonitored.toString(),
                        "Content scanned",
                        Modifier.weight(1f)
                    )
                    StatTile(
                        stats.totalCases.toString(),
                        "Potential matches",
                        Modifier.weight(1f)
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatTile(
                        stats.verifiedReposts.toString(),
                        "Verified reposts",
                        Modifier.weight(1f),
                        accent = DittoColors.SecondaryBlue
                    )
                    StatTile(
                        stats.falsePositives.toString(),
                        "False positives",
                        Modifier.weight(1f),
                        accent = DittoColors.Neutral
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatTile(
                        stats.resolved.toString(),
                        "Cases resolved",
                        Modifier.weight(1f),
                        accent = DittoColors.Success
                    )
                    StatTile(
                        stats.escalated.toString(),
                        "Cases escalated",
                        Modifier.weight(1f),
                        accent = DittoColors.Danger
                    )
                }
            }
        }

        item {
            DittoCard {
                Eyebrow("Quality")
                Spacer(Modifier.height(14.dp))
                MetricBar("Average verification confidence", stats.averageConfidence)
                Spacer(Modifier.height(14.dp))
                MetricBar(
                    "Resolution rate",
                    stats.resolutionRate,
                    barColor = DittoColors.Success
                )
                Spacer(Modifier.height(14.dp))
                HairlineDivider()
                Spacer(Modifier.height(12.dp))
                Text(
                    "Resolution rate counts cases that reached a resolved or closed state, " +
                        "including those closed as false positives without outreach.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
        }

        item {
            DittoCard {
                Eyebrow("Case distribution")
                Spacer(Modifier.height(14.dp))
                if (distribution.isEmpty()) {
                    Text(
                        "No cases yet.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextSecondary
                    )
                } else {
                    val max = distribution.maxOf { it.second }.coerceAtLeast(1)
                    distribution.forEach { (state, count) ->
                        val (fg, _) = state.pillColors()
                        DistributionRow(
                            label = state.label,
                            count = count,
                            fraction = count.toFloat() / max,
                            color = fg
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DistributionRow(label: String, count: Int, fraction: Float, color: Color) {
    val animated by animateFloatAsState(fraction, tween(650), label = "dist")
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextSecondary,
            modifier = Modifier.width(120.dp)
        )
        Box(
            Modifier
                .weight(1f)
                .height(8.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(DittoColors.SurfaceSunken)
        ) {
            Box(
                Modifier
                    .fillMaxWidth(animated)
                    .height(8.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(color)
            )
        }
        Spacer(Modifier.width(10.dp))
        Text(
            count.toString(),
            style = MaterialTheme.typography.titleSmall,
            color = DittoColors.TextPrimary
        )
    }
}
