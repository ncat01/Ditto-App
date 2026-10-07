package com.ditto.app.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import com.ditto.app.ui.theme.DittoColors
import kotlinx.coroutines.isActive
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

private data class AuraBurst(
    val id: Long,
    val origin: Offset,
    val bornAtMillis: Long,
    val colorIndex: Int
)

/**
 * Ditto's ambient canvas. It observes completed pointer events without consuming
 * them, so buttons, scrolling and Android accessibility gestures keep working.
 * Every press releases a small cluster that separates and fades like an echo.
 */
@Composable
fun InteractiveAuraBackground(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit
) {
    val bursts = remember { mutableStateListOf<AuraBurst>() }
    var frameMillis by remember { mutableLongStateOf(0L) }
    var nextId by remember { mutableLongStateOf(0L) }
    val ambient = rememberInfiniteTransition(label = "ditto-aura")
    val drift by ambient.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(14_000), RepeatMode.Reverse),
        label = "aura-drift"
    )

    LaunchedEffect(Unit) {
        while (isActive) {
            withFrameNanos { frameMillis = it / 1_000_000L }
            bursts.removeAll { frameMillis - it.bornAtMillis > 1_050L }
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) {
                        val event = awaitPointerEvent(PointerEventPass.Final)
                        event.changes.forEach { change ->
                            if (change.pressed && !change.previousPressed) {
                                bursts += AuraBurst(
                                    id = nextId++,
                                    origin = change.position,
                                    bornAtMillis = frameMillis,
                                    colorIndex = (nextId % 4).toInt()
                                )
                                while (bursts.size > 8) bursts.removeAt(0)
                            }
                        }
                    }
                }
            }
    ) {
        Canvas(Modifier.fillMaxSize()) {
            drawRect(
                Brush.verticalGradient(
                    listOf(DittoColors.Background, DittoColors.BackgroundAlt, DittoColors.Background)
                )
            )

            val palette = listOf(
                DittoColors.AuraViolet,
                DittoColors.AuraPink,
                DittoColors.AuraAqua,
                DittoColors.AuraGold
            )
            val shift = sin(drift * PI).toFloat()
            val ambientOrbs = listOf(
                Triple(Offset(size.width * (.08f + .08f * shift), size.height * .14f), size.minDimension * .34f, palette[0]),
                Triple(Offset(size.width * .96f, size.height * (.28f + .06f * shift)), size.minDimension * .28f, palette[1]),
                Triple(Offset(size.width * (.12f - .05f * shift), size.height * .72f), size.minDimension * .30f, palette[2]),
                Triple(Offset(size.width * .88f, size.height * (.88f - .05f * shift)), size.minDimension * .26f, palette[3])
            )
            ambientOrbs.forEach { (center, radius, color) ->
                drawCircle(
                    brush = Brush.radialGradient(
                        listOf(color.copy(alpha = .18f), color.copy(alpha = .055f), Color.Transparent),
                        center = center,
                        radius = radius
                    ),
                    radius = radius,
                    center = center
                )
            }

            bursts.forEach { burst ->
                val progress = ((frameMillis - burst.bornAtMillis) / 1_050f).coerceIn(0f, 1f)
                val eased = 1f - (1f - progress) * (1f - progress)
                val alpha = (1f - progress).coerceAtLeast(0f)
                val color = palette[burst.colorIndex]
                drawCircle(
                    color = color.copy(alpha = alpha * .20f),
                    radius = 18f + 90f * eased,
                    center = burst.origin
                )
                repeat(7) { index ->
                    val angle = index * (2f * PI.toFloat() / 7f) + burst.colorIndex * .35f
                    val distance = 20f + 116f * eased
                    val center = burst.origin + Offset(cos(angle) * distance, sin(angle) * distance)
                    drawCircle(
                        color = palette[(burst.colorIndex + index) % palette.size].copy(alpha = alpha * .52f),
                        radius = (13f - 8f * eased).coerceAtLeast(3f),
                        center = center
                    )
                }
            }
        }
        content()
    }
}
