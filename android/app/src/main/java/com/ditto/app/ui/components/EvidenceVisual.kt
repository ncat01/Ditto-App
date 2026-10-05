package com.ditto.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import androidx.compose.ui.graphics.asImageBitmap
import com.ditto.app.ui.theme.DittoColors
import kotlin.math.abs
import kotlin.random.Random

/**
 * Procedurally generated stand-in imagery for the synthetic corpus.
 *
 * The seeded demo corpus ships no photographs, so each item is drawn deterministically
 * from its palette seed: a horizon, a sun/subject disc and a foreground mass. The same
 * seed always draws the same scene, which lets a "detected" copy be rendered with a
 * visible crop, watermark or caption bar so the evidence comparison in report §49 is
 * genuinely visible rather than asserted.
 *
 * When real content is uploaded, [localUri] is rendered instead via Coil.
 */

/** Transformations applied to a detected copy, mirroring the corpus transform note. */
data class EvidenceTransform(
    val cropped: Boolean = false,
    val watermarked: Boolean = false,
    val captionBar: Boolean = false,
    val mirrored: Boolean = false
) {
    companion object {
        /** Infer the visible transform from the corpus's human-readable note. */
        fun fromNote(note: String): EvidenceTransform {
            val n = note.lowercase()
            return EvidenceTransform(
                cropped = "crop" in n || "aspect" in n || "zoom" in n,
                watermarked = "watermark" in n,
                captionBar = "caption" in n || "text overlay" in n,
                mirrored = "mirror" in n
            )
        }
    }
}

@Composable
fun EvidenceVisual(
    seed: Int,
    modifier: Modifier = Modifier,
    localUri: String? = null,
    transform: EvidenceTransform = EvidenceTransform(),
    label: String? = null,
    cornerRadius: Int = 8
) {
    val shape = RoundedCornerShape(cornerRadius.dp)
    Box(
        modifier
            .clip(shape)
            .background(DittoColors.SurfaceSunken)
            .border(1.dp, DittoColors.BorderSubtle, shape)
    ) {
        if (localUri?.endsWith(".mp4") == true) {
            val context=androidx.compose.ui.platform.LocalContext.current
            val bitmap=androidx.compose.runtime.remember(localUri) { runCatching {
                android.media.MediaMetadataRetriever().use { retriever -> retriever.setDataSource(context,android.net.Uri.parse(localUri));retriever.getFrameAtTime(100000L) }
            }.getOrNull() }
            if(bitmap!=null) androidx.compose.foundation.Image(bitmap.asImageBitmap(),contentDescription=label ?: "Generated video preview",modifier=Modifier.fillMaxSize(),contentScale=androidx.compose.ui.layout.ContentScale.Crop)
        } else if (localUri != null) {
            AsyncImage(
                model = localUri,
                contentDescription = label ?: "Content preview",
                modifier = Modifier.fillMaxSize(),
                contentScale = androidx.compose.ui.layout.ContentScale.Crop
            )
        } else {
            SyntheticScene(seed = seed, transform = transform)
        }

        if (transform.watermarked) {
            Text(
                text = "@reposted",
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.72f),
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(6.dp)
            )
        }

        if (transform.captionBar) {
            Box(
                Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .background(Color.Black.copy(alpha = 0.55f))
                    .padding(horizontal = 6.dp, vertical = 4.dp)
            ) {
                Text(
                    "WAIT FOR IT…",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White.copy(alpha = 0.9f),
                    maxLines = 1
                )
            }
        }

        label?.let {
            Box(
                Modifier
                    .align(Alignment.BottomStart)
                    .padding(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(Color.Black.copy(alpha = 0.45f))
                    .padding(horizontal = 6.dp, vertical = 3.dp)
            ) {
                Text(
                    it.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White.copy(alpha = 0.92f)
                )
            }
        }
    }
}

@Composable
private fun SyntheticScene(seed: Int, transform: EvidenceTransform) {
    val (deep, warm) = DittoColors.evidencePalette(seed)
    val rng = Random(seed * 7919)
    // A crop pushes the scene's content off-centre and enlarges it.
    val zoom = if (transform.cropped) 1.28f else 1f
    val shiftX = if (transform.cropped) 0.10f else 0f
    val mirror = if (transform.mirrored) -1f else 1f

    val horizonRatio = 0.52f + rng.nextFloat() * 0.12f
    val sunX = 0.30f + rng.nextFloat() * 0.40f
    val hillSeed = rng.nextFloat()

    Canvas(Modifier.fillMaxSize()) {
        val w = size.width
        val h = size.height
        val horizon = h * horizonRatio

        // Sky gradient
        drawRect(
            brush = Brush.verticalGradient(
                colors = listOf(deep, warm),
                startY = 0f,
                endY = horizon
            ),
            size = Size(w, horizon)
        )

        // Sun / subject disc
        val r = (h * 0.11f) * zoom
        val cx = (w * ((sunX + shiftX - 0.5f) * mirror + 0.5f))
        drawCircle(
            color = Color.White.copy(alpha = 0.82f),
            radius = r,
            center = Offset(cx, horizon - r * 1.15f)
        )

        // Water / ground
        drawRect(
            brush = Brush.verticalGradient(
                colors = listOf(
                    deep.copy(alpha = 0.88f),
                    Color.Black.copy(alpha = 0.55f)
                ),
                startY = horizon,
                endY = h
            ),
            topLeft = Offset(0f, horizon),
            size = Size(w, h - horizon)
        )

        // Reflection of the disc
        drawCircle(
            color = warm.copy(alpha = 0.22f),
            radius = r * 0.85f,
            center = Offset(cx, horizon + r * 0.9f)
        )

        // Foreground silhouette mass
        val peak = horizon - h * (0.06f + hillSeed * 0.10f) * zoom
        val path = androidx.compose.ui.graphics.Path().apply {
            moveTo(0f, h)
            lineTo(0f, horizon + h * 0.04f)
            cubicTo(
                w * 0.25f, peak,
                w * 0.55f, horizon + h * 0.10f,
                w, horizon - h * 0.02f
            )
            lineTo(w, h)
            close()
        }
        drawPath(path, color = Color.Black.copy(alpha = 0.42f))
    }
}

/**
 * Side-by-side comparison of an original and its detected copy, with the transform
 * applied to the right-hand panel so the difference is visible.
 */
@Composable
fun ComparisonStrip(
    originalSeed: Int,
    detectedSeed: Int,
    transform: EvidenceTransform,
    modifier: Modifier = Modifier,
    originalUri: String? = null,
    height: Int = 150
) {
    androidx.compose.foundation.layout.Row(
        modifier.fillMaxWidth(),
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(10.dp)
    ) {
        EvidenceVisual(
            seed = originalSeed,
            localUri = originalUri,
            label = "Original",
            modifier = Modifier
                .weight(1f)
                .height(height.dp)
        )
        EvidenceVisual(
            seed = detectedSeed,
            transform = transform,
            label = "Detected",
            modifier = Modifier
                .weight(1f)
                .height(height.dp)
        )
    }
}
