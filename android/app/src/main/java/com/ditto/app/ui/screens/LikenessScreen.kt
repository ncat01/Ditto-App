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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.Eyebrow
import com.ditto.app.ui.components.HairlineDivider
import com.ditto.app.ui.components.StatusPill
import com.ditto.app.ui.theme.DittoColors

/**
 * Honest status page for the likeness-misuse capability: the detection architecture
 * exists (face-embedding signal, classification, severity mapping) but the production
 * pipeline is P2. The screen says so plainly rather than implying it ships today.
 */
@Composable
fun LikenessScreen(onBack: () -> Unit) {
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
            Row(verticalAlignment = Alignment.CenterVertically) {
                Eyebrow("AI Likeness Protection")
                Spacer(Modifier.width(8.dp))
                StatusPill("Coming in P2", DittoColors.Warning, DittoColors.WarningBg)
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "Protecting your likeness",
                style = MaterialTheme.typography.displaySmall,
                color = DittoColors.TextPrimary
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Ditto will detect potential unauthorized AI-generated uses of your likeness " +
                    "— cases where your face appears in content you never filmed.",
                style = MaterialTheme.typography.bodyMedium,
                color = DittoColors.TextSecondary
            )
        }

        item {
            DittoCard {
                Eyebrow("Why this is a different problem")
                Spacer(Modifier.height(10.dp))
                Text(
                    "A repost shares pixels with the original, so perceptual hashing finds it. " +
                        "A generated likeness shares no frame with anything you published — " +
                        "the hash match is near zero while the facial geometry still matches " +
                        "you closely. That inverted signature is what the pipeline looks for.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = DittoColors.TextSecondary
                )
            }
        }

        item {
            DittoCard {
                Eyebrow("What is already in place")
                Spacer(Modifier.height(12.dp))
                StatusLine("Face-similarity signal in the candidate model", true)
                StatusLine("Likeness-misuse classification path in the Verification Agent", true)
                StatusLine("High-severity mapping and escalation policy", true)
                StatusLine("Seeded likeness case in the demo corpus", true)
                Spacer(Modifier.height(14.dp))
                HairlineDivider()
                Spacer(Modifier.height(12.dp))
                Eyebrow("What P2 adds")
                Spacer(Modifier.height(12.dp))
                StatusLine("InsightFace / ArcFace embedding extraction on device", false)
                StatusLine("Meta Ad Library discovery for commercial ad misuse", false)
                StatusLine("Consent-registry enrolment for the creator's reference face", false)
                StatusLine("Face-swap artefact detection", false)
            }
        }

        item {
            DittoCard(background = DittoColors.BlueTint, borderColor = DittoColors.LightBlue) {
                Text(
                    "Scope note",
                    style = MaterialTheme.typography.titleSmall,
                    color = DittoColors.PrimaryBlue
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "Commercial-ad coverage in the Meta Ad Library is researcher-gated, so " +
                        "the demo uses a synthetic ad corpus for this case. The repost " +
                        "pipeline is the fully implemented MVP.",
                    style = MaterialTheme.typography.bodySmall,
                    color = DittoColors.TextSecondary
                )
            }
        }
    }
}

@Composable
private fun StatusLine(text: String, done: Boolean) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            Modifier
                .width(18.dp)
                .height(18.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(if (done) DittoColors.SuccessBg else DittoColors.SurfaceSunken),
            contentAlignment = Alignment.Center
        ) {
            Text(
                if (done) "✓" else "·",
                style = MaterialTheme.typography.labelSmall,
                color = if (done) DittoColors.Success else DittoColors.TextTertiary
            )
        }
        Spacer(Modifier.width(10.dp))
        Text(
            text,
            style = MaterialTheme.typography.bodyMedium,
            color = if (done) DittoColors.TextPrimary else DittoColors.TextSecondary,
            modifier = Modifier.weight(1f)
        )
    }
}
