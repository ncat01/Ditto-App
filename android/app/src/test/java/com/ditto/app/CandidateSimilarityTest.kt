package com.ditto.app

import com.ditto.app.domain.model.CandidateMatch
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CandidateSimilarityTest {
    @Test
    fun exactSubmittedCopiesShowOneHundredPercentForBothServerPlatforms() {
        listOf("Submitted media", "Submitted evidence").forEach { platform ->
            val candidate = submittedCandidate(platform, 1.0)
            assertEquals("Exact comparison on $platform", 1.0, candidate.overallSimilarity, 0.0001)
            assertTrue("Submitted metadata must remain unverified", candidate.isSubmittedMedia)
        }
    }

    @Test
    fun submittedComparisonScoreIsNotReducedByAnUnverifiedCaption() {
        val candidate = submittedCandidate("Submitted media", 0.73)
        assertEquals(0.73, candidate.overallSimilarity, 0.0001)
    }

    private fun submittedCandidate(platform: String, score: Double) = CandidateMatch(
        id = "comparison",
        contentId = "original",
        platform = platform,
        accountName = "Not identified",
        accountHandle = "",
        sourceUrl = "",
        caption = "",
        followerCount = 0,
        monetized = false,
        hashSimilarity = score,
        visualSimilarity = score,
        captionSimilarity = 0.0,
        faceSimilarity = 0.0,
        postedAt = 0,
        transformNote = "",
        paletteSeed = 1,
        discoveredAt = 0
    )
}
