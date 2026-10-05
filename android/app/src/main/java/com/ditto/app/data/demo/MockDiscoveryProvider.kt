package com.ditto.app.data.demo

import com.ditto.app.domain.agents.DiscoveryProvider
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.ContentItem
import java.util.UUID
import java.util.concurrent.TimeUnit
import kotlin.math.abs
import kotlin.random.Random

/**
 * Demo discovery corpus (report §8). Returns seeded candidates for known demo content,
 * and for freshly uploaded content synthesises plausible candidates derived from the
 * upload's own fingerprint so a live scan during the viva still produces results.
 *
 * Deliberately does NOT scrape Instagram — that would breach its Terms of Service.
 * Real providers (Google Vision Web Detection, Meta Graph, Meta Ad Library) implement
 * this same interface.
 */
class MockDiscoveryProvider(private val corpus: VideoCorpus) : DiscoveryProvider {

    override val displayName: String = "Demo discovery corpus (synthetic, no live scraping)"

    private val platforms = listOf("Instagram", "Instagram", "TikTok", "Facebook")

    private val handles = listOf(
        "Repost Central" to "@repost.central",
        "Daily Clip Vault" to "@dailyclipvault",
        "Viral Reels Hub" to "@viralreelshub",
        "Trend Archive" to "@trend.archive",
        "Clip Curator" to "@clip.curator"
    )

    private val captions = listOf(
        "Found this and had to share 🔥 #reels #viral",
        "This is everything ✨ credit to the creator",
        "Saving this one for later 📌",
        "POV: the perfect shot #contentcreator",
        "Obsessed with this 😍 follow for more"
    )

    private val transforms = listOf(
        "Cropped to 4:5 with a watermark overlay.",
        "Re-encoded at a lower bitrate with a caption bar burned in.",
        "Aspect ratio changed to 1:1, original audio retained.",
        "Zoom-cropped and re-uploaded with a text overlay.",
        "Mirrored horizontally and re-encoded."
    )

    override suspend fun discover(content: ContentItem): List<CandidateMatch> {
        val seeded = DemoCorpus.candidatesFor(content.id)
        if (seeded.isNotEmpty()) return seeded.map { corpus.measured(it) }
        return emptyList() // Synthetic corpus only; uploaded media has no discovered sources.
    }

    /**
     * Derive candidates deterministically from the content's own hash so repeated scans
     * of the same upload give the same results — important for a reproducible demo.
     */
    private fun synthesise(content: ContentItem): List<CandidateMatch> {
        val seed = content.perceptualHash.hashCode()
        val rng = Random(seed)
        val count = 2 + rng.nextInt(2) // 2-3 candidates

        return (0 until count).map { i ->
            val (name, handle) = handles[abs(seed + i * 31) % handles.size]
            // One clear true positive, the rest progressively weaker.
            val strong = i == 0
            val hash = if (strong) 0.88 + rng.nextDouble() * 0.09
            else 0.38 + rng.nextDouble() * 0.30
            val visual = (hash + (rng.nextDouble() - 0.4) * 0.08).coerceIn(0.25, 0.98)
            val caption = if (strong) 0.60 + rng.nextDouble() * 0.30
            else 0.10 + rng.nextDouble() * 0.35

            CandidateMatch(
                id = "cand_live_${UUID.randomUUID().toString().take(8)}",
                contentId = content.id,
                platform = platforms[abs(seed + i * 7) % platforms.size],
                accountName = name,
                accountHandle = handle,
                sourceUrl = "https://demo-corpus.local/post/${abs(seed + i)}",
                caption = captions[abs(seed + i * 13) % captions.size],
                followerCount = listOf(3_200, 28_500, 91_000, 240_000)[abs(seed + i * 5) % 4],
                monetized = strong && (abs(seed) % 2 == 0),
                hashSimilarity = round2(hash),
                visualSimilarity = round2(visual),
                captionSimilarity = round2(caption),
                faceSimilarity = 0.0,
                // Candidates always post after the original in the demo corpus.
                postedAt = content.publishedAt + TimeUnit.DAYS.toMillis(3L + i * 4),
                transformNote = transforms[abs(seed + i * 3) % transforms.size],
                paletteSeed = content.paletteSeed,
                discoveredAt = System.currentTimeMillis()
            )
        }
    }

    private fun round2(v: Double) = kotlin.math.round(v * 100) / 100.0
}
