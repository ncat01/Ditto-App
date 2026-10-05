package com.ditto.app.data.demo

import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.ContentKind
import java.util.concurrent.TimeUnit

/**
 * Synthetic, fully-labelled discovery corpus — the classroom substitute for live
 * scraping described in report §8. Every entry carries known ground truth so
 * precision/recall can be measured, and the positive examples use exactly the
 * transformations the report proposes: crop, watermark, re-encode, aspect-ratio
 * change and caption overlay.
 */
object DemoCorpus {

    private fun daysAgo(n: Long) = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(n)

    val creatorName = "Alex Morgan"
    val creatorHandle = "@alexmorgan.shoots"

    /** The creator's own published content (Layer 1 ground truth). */
    val content: List<ContentItem> = listOf(
        ContentItem(
            id = "content_001",
            title = "Sunset Travel Reel",
            kind = ContentKind.VIDEO,
            localUri = null,
            perceptualHash = "c3f1a04d8b2e7615",
            paletteSeed = 1,
            publishedAt = daysAgo(62),
            createdAt = daysAgo(62),
            sourcePlatform = "Instagram (own)"
        ),
        ContentItem(
            id = "content_002",
            title = "Studio Portrait Series",
            kind = ContentKind.IMAGE,
            localUri = null,
            perceptualHash = "9a72e5c1f0d43b88",
            paletteSeed = 2,
            publishedAt = daysAgo(48),
            createdAt = daysAgo(48),
            sourcePlatform = "Instagram (own)"
        ),
        ContentItem(
            id = "content_003",
            title = "Coastal Drone Pass",
            kind = ContentKind.VIDEO,
            localUri = null,
            perceptualHash = "5e0bd7431ca9f262",
            paletteSeed = 3,
            publishedAt = daysAgo(35),
            createdAt = daysAgo(35),
            sourcePlatform = "Instagram (own)"
        ),
        ContentItem(
            id = "content_004",
            title = "Morning Market Walk",
            kind = ContentKind.VIDEO,
            localUri = null,
            perceptualHash = "71c4a9e2350fb8d6",
            paletteSeed = 4,
            publishedAt = daysAgo(21),
            createdAt = daysAgo(21),
            sourcePlatform = "Instagram (own)"
        ),
        ContentItem(
            id = "content_005",
            title = "Rooftop Golden Hour",
            kind = ContentKind.IMAGE,
            localUri = null,
            perceptualHash = "e2d80b67a145c3f9",
            paletteSeed = 5,
            publishedAt = daysAgo(12),
            createdAt = daysAgo(12),
            sourcePlatform = "Instagram (own)"
        )
    )

    /**
     * Seeded candidates keyed by content id, with labelled ground truth.
     * [groundTruth] is what a human labeller recorded, used by the evaluation harness.
     */
    data class SeededCandidate(val match: CandidateMatch, val groundTruth: String)

    private val baseCandidates: List<SeededCandidate> = listOf(
        // --- content_001: classic crop + watermark repost (true positive) -------------
        SeededCandidate(
            CandidateMatch(
                id = "cand_001",
                contentId = "content_001",
                platform = "Instagram",
                accountName = "Travel Reuploads",
                accountHandle = "@travel_reuploads",
                sourceUrl = "https://instagram.com/reel/demo-Cx7Kq2ZtA",
                caption = "Golden hour hits different 🌅 #travel #sunset #reels",
                followerCount = 84_300,
                monetized = false,
                hashSimilarity = 0.94,
                visualSimilarity = 0.96,
                captionSimilarity = 0.87,
                faceSimilarity = 0.0,
                postedAt = daysAgo(9),
                transformNote = "Cropped to 4:5 with a watermark overlay in the lower-right corner.",
                paletteSeed = 1,
                discoveredAt = daysAgo(2)
            ),
            groundTruth = "genuine_repost"
        ),
        // --- content_003: monetized, high-reach repost (true positive, high severity) --
        SeededCandidate(
            CandidateMatch(
                id = "cand_002",
                contentId = "content_003",
                platform = "Instagram",
                accountName = "Aerial Daily",
                accountHandle = "@aerial.daily",
                sourceUrl = "https://instagram.com/reel/demo-Dp4Mn8Yq1",
                caption = "Drone shot of the week ✈️ Link in bio for our presets!",
                followerCount = 612_000,
                monetized = true,
                hashSimilarity = 0.97,
                visualSimilarity = 0.98,
                captionSimilarity = 0.62,
                faceSimilarity = 0.0,
                postedAt = daysAgo(28),
                transformNote = "Re-encoded at a lower bitrate with a burned-in caption bar at the top.",
                paletteSeed = 3,
                discoveredAt = daysAgo(24)
            ),
            groundTruth = "genuine_repost"
        ),
        // --- content_002: coincidental similarity (true negative) ---------------------
        SeededCandidate(
            CandidateMatch(
                id = "cand_003",
                contentId = "content_002",
                platform = "Pinterest",
                accountName = "Portrait Lighting Ideas",
                accountHandle = "@portraitlighting",
                sourceUrl = "https://pinterest.com/pin/demo-8841203",
                caption = "Soft key light setup — studio inspiration board",
                followerCount = 12_400,
                monetized = false,
                hashSimilarity = 0.48,
                visualSimilarity = 0.55,
                captionSimilarity = 0.31,
                faceSimilarity = 0.12,
                postedAt = daysAgo(94),
                transformNote = "Similar studio lighting setup and framing, different subject.",
                paletteSeed = 2,
                discoveredAt = daysAgo(18)
            ),
            groundTruth = "false_positive"
        ),
        // --- content_004: repost, partial attribution, resolved path ------------------
        SeededCandidate(
            CandidateMatch(
                id = "cand_004",
                contentId = "content_004",
                platform = "Instagram",
                accountName = "City Food Diary",
                accountHandle = "@cityfooddiary",
                sourceUrl = "https://instagram.com/reel/demo-Bt2Lm9Wr6",
                caption = "Saturday market runs 🥬 (repost)",
                followerCount = 9_800,
                monetized = false,
                hashSimilarity = 0.95,
                visualSimilarity = 0.93,
                captionSimilarity = 0.71,
                faceSimilarity = 0.0,
                postedAt = daysAgo(16),
                transformNote = "Aspect ratio changed to 1:1 with the original audio retained.",
                paletteSeed = 4,
                discoveredAt = daysAgo(14)
            ),
            groundTruth = "genuine_repost"
        ),
        // --- content_005: likeness misuse (P2 architecture demonstration) -------------
        SeededCandidate(
            CandidateMatch(
                id = "cand_005",
                contentId = "content_005",
                platform = "Ad Library (synthetic)",
                accountName = "GlowUp Skincare Co",
                accountHandle = "@glowup.skincare",
                sourceUrl = "https://example-adlibrary.demo/ad/8813--synthetic",
                caption = "Real results, real people. Try GlowUp today.",
                followerCount = 41_000,
                monetized = true,
                hashSimilarity = 0.31,
                visualSimilarity = 0.44,
                captionSimilarity = 0.08,
                faceSimilarity = 0.91,
                postedAt = daysAgo(6),
                transformNote =
                    "No frame-level match to any published original, but facial geometry " +
                        "matches the creator closely — consistent with a generated likeness.",
                paletteSeed = 5,
                discoveredAt = daysAgo(3)
            ),
            groundTruth = "genuine_likeness_misuse"
        ),
        // --- content_001: second infringer, no response -> escalation path ------------
        SeededCandidate(
            CandidateMatch(
                id = "cand_006",
                contentId = "content_001",
                platform = "Instagram",
                accountName = "Wanderlust Clips",
                accountHandle = "@wanderlust.clips",
                sourceUrl = "https://instagram.com/reel/demo-Az9Pq3Vk4",
                caption = "Sunsets like these 🔥 follow for daily travel content",
                followerCount = 158_000,
                monetized = true,
                hashSimilarity = 0.92,
                visualSimilarity = 0.94,
                captionSimilarity = 0.55,
                faceSimilarity = 0.0,
                postedAt = daysAgo(41),
                transformNote = "Zoom-cropped with a text overlay covering the original corner mark.",
                paletteSeed = 1,
                discoveredAt = daysAgo(38)
            ),
            groundTruth = "genuine_repost"
        )
    )

    val candidates = baseCandidates + listOf(
        SeededCandidate(baseCandidates[0].match.copy(id="cand_007",accountHandle="@credited.demo",caption="Credit: @alexmorgan.shoots",attributionPresent=true,monetized=false),"genuine_repost"),
        SeededCandidate(baseCandidates[0].match.copy(id="cand_008",accountHandle="@authorized.demo",permissionGranted=true,monetized=false),"genuine_repost"),
        SeededCandidate(baseCandidates[0].match.copy(id="cand_009",accountHandle="@ambiguous.demo",captionSimilarity=0.0,monetized=false),"genuine_repost")
    )

    fun candidatesFor(contentId: String): List<CandidateMatch> =
        candidates.filter { it.match.contentId == contentId }.map { it.match }

    fun groundTruthFor(candidateId: String): String? =
        candidates.firstOrNull { it.match.id == candidateId }?.groundTruth
}
