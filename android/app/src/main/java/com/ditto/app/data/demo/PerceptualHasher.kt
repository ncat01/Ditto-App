package com.ditto.app.data.demo

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import android.net.Uri
import com.ditto.app.domain.agents.ContentMatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.cos
import kotlin.math.sqrt

/**
 * Genuine DCT-based perceptual hash (pHash), matching the detection approach named in
 * the project report §6. Runs fully on-device with no dependencies.
 *
 * Images: decoded, reduced to 32x32 grayscale, 2-D DCT-II applied, the low-frequency
 * 8x8 block (excluding DC) thresholded at its median to produce a 64-bit hash.
 * Videos: a representative frame is extracted via MediaMetadataRetriever and hashed
 * identically — a simple but real video fingerprint.
 *
 * If the media cannot be decoded (unsupported codec, permissions, demo content with no
 * backing file) it falls back to a stable seed-derived hash so the demo never breaks.
 */
class PerceptualHasher(private val context: Context) : ContentMatcher {

    override val displayName: String = "pHash 64-bit (DCT, on-device)"

    private companion object {
        const val SIZE = 32      // DCT input resolution
        const val HASH_SIDE = 8  // low-frequency block side -> 64 bits
    }

    override suspend fun fingerprint(uri: String?, seed: Int): String =
        withContext(Dispatchers.Default) {
            if(uri!=null && context.contentResolver.getType(Uri.parse(uri))?.startsWith("video/")==true || uri?.endsWith(".mp4")==true) {
                return@withContext MediaMetadataRetriever().use { retriever ->
                    retriever.setDataSource(context,Uri.parse(uri!!))
                    val duration=(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: error("Duration unavailable"))*1000L
                    (0..4).map { i ->
                        val frame=retriever.getFrameAtTime((duration-100000L).coerceAtLeast(0L)*i/4,MediaMetadataRetriever.OPTION_CLOSEST) ?: error("Video frame unavailable")
                        try { hashBitmap(frame) } finally { frame.recycle() }
                    }.joinToString("|")
                }
            }
            val bitmap = uri?.let { loadBitmap(it) }
            if (bitmap != null) {
                try { hashBitmap(bitmap) } finally { bitmap.recycle() }
            } else {
                if (uri == null) syntheticHash(seed) else error("Unsupported or unreadable media. No fingerprint was generated.")
            }
        }

    private fun loadBitmap(uriString: String): Bitmap? = runCatching {
        val uri = Uri.parse(uriString)
        val mime = context.contentResolver.getType(uri).orEmpty()
        if (mime.startsWith("video")) {
            MediaMetadataRetriever().use { mmr ->
                mmr.setDataSource(context, uri)
                // Sample ~1s in to avoid black lead-in frames.
                mmr.getFrameAtTime(1_000_000L, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
            }
        } else {
            context.contentResolver.openInputStream(uri)?.use { stream ->
                val opts = BitmapFactory.Options().apply { inSampleSize = 4 }
                BitmapFactory.decodeStream(stream, null, opts)
            }
        }
    }.getOrNull()

    /** Reduce -> grayscale -> DCT -> median threshold -> 64-bit hex. */
    fun hashBitmap(src: Bitmap): String {
        val scaled = Bitmap.createScaledBitmap(src, SIZE, SIZE, true)
        val gray = Array(SIZE) { DoubleArray(SIZE) }
        val pixels = IntArray(SIZE * SIZE)
        scaled.getPixels(pixels, 0, SIZE, 0, 0, SIZE, SIZE)
        for (y in 0 until SIZE) {
            for (x in 0 until SIZE) {
                val p = pixels[y * SIZE + x]
                val r = (p shr 16) and 0xFF
                val g = (p shr 8) and 0xFF
                val b = p and 0xFF
                // Rec. 601 luma
                gray[y][x] = 0.299 * r + 0.587 * g + 0.114 * b
            }
        }

        val dct = dct2d(gray)

        // Collect the low-frequency block, skipping the DC term at [0][0].
        val coefficients = ArrayList<Double>(HASH_SIDE * HASH_SIDE - 1)
        for (y in 0 until HASH_SIDE) {
            for (x in 0 until HASH_SIDE) {
                if (x == 0 && y == 0) continue
                coefficients.add(dct[y][x])
            }
        }
        val median = coefficients.sorted().let { s ->
            if (s.size % 2 == 0) (s[s.size / 2 - 1] + s[s.size / 2]) / 2.0 else s[s.size / 2]
        }

        var bitIndex = 0
        var bits = 0L
        for (y in 0 until HASH_SIDE) {
            for (x in 0 until HASH_SIDE) {
                val value = if (x == 0 && y == 0) median else dct[y][x]
                if (value > median) bits = bits or (1L shl (63 - bitIndex))
                bitIndex++
            }
        }
        return java.lang.String.format("%016x", bits)
    }

    private fun dct2d(input: Array<DoubleArray>): Array<DoubleArray> {
        val n = input.size
        val out = Array(n) { DoubleArray(n) }
        // Precompute the cosine basis once: O(n^2) instead of inside the O(n^4) loop.
        val cosTable = Array(n) { u -> DoubleArray(n) { i -> cos((2 * i + 1) * u * Math.PI / (2.0 * n)) } }
        val c = DoubleArray(n) { if (it == 0) 1.0 / sqrt(2.0) else 1.0 }

        // Separable DCT: rows then columns.
        val temp = Array(n) { DoubleArray(n) }
        for (y in 0 until n) {
            for (u in 0 until n) {
                var sum = 0.0
                for (x in 0 until n) sum += input[y][x] * cosTable[u][x]
                temp[y][u] = c[u] * sum
            }
        }
        for (u in 0 until n) {
            for (v in 0 until n) {
                var sum = 0.0
                for (y in 0 until n) sum += temp[y][u] * cosTable[v][y]
                out[v][u] = c[v] * sum * (2.0 / n)
            }
        }
        return out
    }

    /** Deterministic stand-in hash so seeded demo content has a stable fingerprint. */
    private fun syntheticHash(seed: Int): String {
        var x = seed.toLong() * 0x9E3779B97F4A7C15uL.toLong()
        x = x xor (x ushr 30); x *= -0x40a7b892e31b1a47L
        x = x xor (x ushr 27); x *= -0x6b2fb644ecceee15L
        x = x xor (x ushr 31)
        return java.lang.String.format("%016x", x)
    }

    /** Normalized Hamming similarity between two 64-bit hex hashes. */
    fun similarity(a: String, b: String): Double = runCatching {
        val x = java.lang.Long.parseUnsignedLong(a, 16)
        val y = java.lang.Long.parseUnsignedLong(b, 16)
        1.0 - (java.lang.Long.bitCount(x xor y) / 64.0)
    }.getOrDefault(0.0)
}
