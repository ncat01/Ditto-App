package com.ditto.app.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.unit.dp
import com.ditto.app.ui.theme.*

@Composable
fun CreatorHero(greeting: String, onScan: () -> Unit) {
    val motion = rememberInfiniteTransition(label = "creator glow")
    val drift by motion.animateFloat(0f, 14f, infiniteRepeatable(tween(3500), RepeatMode.Reverse), label = "drift")
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp))
        .background(Brush.linearGradient(listOf(Color(0xFFFFCEDF), Color(0xFFFFD8C7), Color(0xFFFFECB3))))) {
        Canvas(Modifier.matchParentSize()) {
            drawCircle(Color(0xFFFFB24A).copy(alpha=.36f), 82.dp.toPx(), Offset(size.width-10.dp.toPx(), 24.dp.toPx()+drift))
            drawCircle(Color(0xFFFFF6D6).copy(alpha=.65f), 58.dp.toPx(), Offset(size.width-10.dp.toPx(), 24.dp.toPx()+drift))
            drawCircle(Color(0xFFEF7B95).copy(alpha=.20f), 68.dp.toPx(), Offset(size.width-30.dp.toPx(), size.height))
        }
        Column(Modifier.padding(24.dp), verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Eyebrow("$greeting, creator", color=DittoColors.DeepBlue)
            Text("Make your mark.", style=MaterialTheme.typography.displayMedium, color=DittoColors.TextPrimary)
            Text("We'll watch the echoes.", style=HandwritingStyle, color=DittoColors.SecondaryBlue)
            Text("Find potential reposts. Check the evidence. Choose what happens next.", style=MaterialTheme.typography.bodyMedium, color=DittoColors.TextSecondary)
            Spacer(Modifier.height(4.dp))
            PrimaryButton("Scan for matches", onScan, Modifier.fillMaxWidth())
        }
    }
}
