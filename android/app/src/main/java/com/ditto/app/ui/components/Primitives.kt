package com.ditto.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.Severity
import com.ditto.app.ui.theme.DittoColors

/** Uppercase tracked-out eyebrow label used above section headings. */
@Composable
fun Eyebrow(text: String, modifier: Modifier = Modifier, color: Color = DittoColors.SecondaryBlue) {
    Text(
        text = text.uppercase(),
        style = MaterialTheme.typography.labelSmall,
        color = color,
        modifier = modifier
    )
}

/** The standard Ditto card: white, hairline border, restrained radius, no elevation. */
@Composable
fun DittoCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    background: Color = DittoColors.Surface,
    borderColor: Color = DittoColors.Border,
    contentPadding: Int = 16,
    content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit
) {
    val base = modifier
        .fillMaxWidth()
        .clip(RoundedCornerShape(22.dp))
        .background(background)
        .border(BorderStroke(1.dp, borderColor), RoundedCornerShape(22.dp))
    Column(
        modifier = (if (onClick != null) base.clickable(onClick = onClick) else base)
            .padding(contentPadding.dp),
        content = content
    )
}

@Composable
fun SectionHeading(
    title: String,
    modifier: Modifier = Modifier,
    trailing: @Composable (() -> Unit)? = null
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = DittoColors.TextPrimary
        )
        trailing?.invoke()
    }
}

/** Small status pill. Colours stay muted so they never dominate the page. */
@Composable
fun StatusPill(
    text: String,
    fg: Color,
    bg: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = text.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = fg,
            maxLines = 1
        )
    }
}

@Composable
fun StatePill(state: CaseState, modifier: Modifier = Modifier) {
    val (fg, bg) = state.pillColors()
    StatusPill(state.label, fg, bg, modifier)
}

fun CaseState.pillColors(): Pair<Color, Color> = when (this) {
    CaseState.NEW -> DittoColors.SecondaryBlue to DittoColors.BlueTint
    CaseState.VERIFIED -> DittoColors.SecondaryBlue to DittoColors.BlueTint
    CaseState.PENDING_APPROVAL -> DittoColors.Warning to DittoColors.WarningBg
    CaseState.SENT -> DittoColors.PrimaryBlue to DittoColors.LightBlue
    CaseState.AWAITING_RESPONSE -> DittoColors.PrimaryBlue to DittoColors.LightBlue
    CaseState.ESCALATED -> DittoColors.Danger to DittoColors.DangerBg
    CaseState.RESOLVED -> DittoColors.Success to DittoColors.SuccessBg
    CaseState.CLOSED -> DittoColors.Neutral to DittoColors.NeutralBg
}

@Composable
fun SeverityPill(severity: Severity, modifier: Modifier = Modifier) {
    val (fg, bg) = when (severity) {
        Severity.HIGH -> DittoColors.Danger to DittoColors.DangerBg
        Severity.MEDIUM -> DittoColors.Warning to DittoColors.WarningBg
        Severity.LOW -> DittoColors.Neutral to DittoColors.NeutralBg
    }
    StatusPill("${severity.label} severity", fg, bg, modifier)
}

@Composable
fun ClassificationPill(classification: Classification, modifier: Modifier = Modifier) {
    val (fg, bg) = when (classification) {
        Classification.GENUINE_REPOST -> DittoColors.PrimaryBlue to DittoColors.LightBlue
        Classification.GENUINE_LIKENESS_MISUSE -> DittoColors.Danger to DittoColors.DangerBg
        Classification.FALSE_POSITIVE -> DittoColors.Neutral to DittoColors.NeutralBg
    }
    StatusPill(classification.label, fg, bg, modifier)
}

/** Thin horizontal rule used to separate content without adding a card. */
@Composable
fun HairlineDivider(modifier: Modifier = Modifier, color: Color = DittoColors.BorderSubtle) {
    Box(
        modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(color)
    )
}

/** Labelled metric with an animated bar — used for the similarity breakdown. */
@Composable
fun MetricBar(
    label: String,
    value: Double,
    modifier: Modifier = Modifier,
    barColor: Color = DittoColors.SecondaryBlue
) {
    val animated by animateFloatAsState(
        targetValue = value.toFloat().coerceIn(0f, 1f),
        animationSpec = tween(650),
        label = "metric"
    )
    Column(modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                label,
                style = MaterialTheme.typography.bodySmall,
                color = DittoColors.TextSecondary
            )
            Text(
                "${(value * 100).toInt()}%",
                style = MaterialTheme.typography.titleSmall,
                color = DittoColors.TextPrimary
            )
        }
        Spacer(Modifier.height(6.dp))
        Box(
            Modifier
                .fillMaxWidth()
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(DittoColors.SurfaceSunken)
        ) {
            Box(
                Modifier
                    .fillMaxWidth(animated)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(barColor)
            )
        }
    }
}

/** Large figure + caption used on the dashboard summary grid. */
@Composable
fun StatTile(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
    accent: Color = DittoColors.PrimaryBlue,
    onClick: (() -> Unit)? = null
) {
    DittoCard(modifier = modifier, onClick = onClick, contentPadding = 14) {
        Text(
            text = value,
            style = MaterialTheme.typography.displaySmall,
            color = accent
        )
        Spacer(Modifier.height(2.dp))
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = DittoColors.TextSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

/** A signal row: tick or dash plus name and value. */
@Composable
fun SignalRow(
    name: String,
    value: String,
    supports: Boolean,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier
                .size(16.dp)
                .clip(CircleShape)
                .background(
                    if (supports) DittoColors.SuccessBg else DittoColors.NeutralBg
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = if (supports) "✓" else "–",
                style = MaterialTheme.typography.labelSmall,
                color = if (supports) DittoColors.Success else DittoColors.TextTertiary
            )
        }
        Spacer(Modifier.width(10.dp))
        Text(
            name,
            style = MaterialTheme.typography.bodyMedium,
            color = DittoColors.TextPrimary,
            modifier = Modifier.weight(1f)
        )
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.TextSecondary
        )
    }
}

/** Banner that states plainly whether data is simulated (report §51). */
@Composable
fun DemoModeBanner(text: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(DittoColors.BlueTint)
            .border(BorderStroke(1.dp, DittoColors.LightBlue), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier
                .size(6.dp)
                .clip(CircleShape)
                .background(DittoColors.SecondaryBlue)
                .clearAndSetSemantics { }
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text,
            style = MaterialTheme.typography.bodySmall,
            color = DittoColors.PrimaryBlue
        )
    }
}

/** A quotation-shaped d: authorship, echoed without losing its origin. */
@Composable
fun DittoMark(size: Int = 32, modifier: Modifier = Modifier) {
    androidx.compose.foundation.Image(
        painter = androidx.compose.ui.res.painterResource(com.ditto.app.R.drawable.ic_ditto_mark),
        contentDescription = "Ditto logo", modifier = modifier.size(size.dp)
    )
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    Surface(
        modifier = modifier.height(48.dp),
        shape = RoundedCornerShape(18.dp),
        color = if (enabled) DittoColors.PrimaryBlue else DittoColors.SurfaceSunken,
        onClick = onClick,
        enabled = enabled
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text,
                style = MaterialTheme.typography.labelLarge,
                color = if (enabled) DittoColors.TextOnDark else DittoColors.TextTertiary
            )
        }
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    contentColor: Color = DittoColors.PrimaryBlue
) {
    Surface(
        modifier = modifier.height(48.dp),
        shape = RoundedCornerShape(18.dp),
        color = DittoColors.Surface,
        border = BorderStroke(1.dp, DittoColors.Border),
        onClick = onClick,
        enabled = enabled
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text,
                style = MaterialTheme.typography.labelLarge,
                color = if (enabled) contentColor else DittoColors.TextTertiary
            )
        }
    }
}
