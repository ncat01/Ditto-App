package com.ditto.app.domain.agents

import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.Severity
import com.ditto.app.domain.model.Signal
import com.ditto.app.domain.model.VerificationResult
import kotlin.math.abs
import kotlin.math.min

/**
 * Deterministic verification engine used in Demo Mode.
 *
 * It is NOT an LLM. It reasons over the same signal set a vision-capable LLM would be
 * given — hash similarity, visual similarity, caption context, account context,
 * monetization and publication order — using an explicit weighted rule set, so demo
 * runs are reproducible. Every result is labelled "Demo Verification Agent" in the UI
 * so no live-AI claim is ever implied (report §51).
 */
class MockVerificationAgent : VerificationAgent {

    override val displayName: String = "Demo Verification Agent (on-device, deterministic)"

    override suspend fun verify(
        content: ContentItem,
        candidate: CandidateMatch
    ): VerificationResult {
        val hash = candidate.hashSimilarity
        val visual = candidate.visualSimilarity
        val caption = candidate.captionSimilarity

        // Publication order: content posted AFTER the original supports reuse.
        val postedAfterOriginal = candidate.postedAt > content.publishedAt
        val daysAfter = ((candidate.postedAt - content.publishedAt) / 86_400_000L)

        // --- Weighted evidence score -------------------------------------------------
        var score = (hash * 0.45) + (visual * 0.35) + (caption * 0.10)
        if (postedAfterOriginal) score += 0.10 else score -= 0.15

        // Face similarity only matters when the candidate is not a pixel-level match:
        // high face similarity + low hash similarity is the likeness-misuse signature.
        val likenessSignature = candidate.id == "cand_005" // Explicit simulated scenario, not face-based inference.

        val classification = when {
            likenessSignature -> Classification.GENUINE_LIKENESS_MISUSE
            score >= 0.72 && postedAfterOriginal -> Classification.GENUINE_REPOST
            else -> Classification.FALSE_POSITIVE
        }

        // Confidence: distance from the decision boundary, not the raw score.
        val boundary = if (likenessSignature) 0.80 else 0.72
        val margin = abs(score - boundary)
        val confidence = when (classification) {
            Classification.FALSE_POSITIVE -> min(0.94, 0.55 + margin * 1.4)
            Classification.GENUINE_LIKENESS_MISUSE ->
                min(0.97, 0.60 + candidate.faceSimilarity * 0.35)
            Classification.GENUINE_REPOST -> min(0.98, 0.62 + margin * 1.8)
        }.coerceIn(0.50, 0.98)

        val severity = severityFor(classification, candidate, score)

        val signals = buildList {
            add(Signal("Hash similarity", pct(hash), hash >= 0.70))
            add(Signal("Visual similarity", pct(visual), visual >= 0.70))
            add(Signal("Caption context", pct(caption), caption >= 0.60))
            add(
                Signal(
                    "Publication order",
                    if (postedAfterOriginal) "Posted ${daysAfter}d after original"
                    else "Posted before original",
                    postedAfterOriginal
                )
            )
            add(
                Signal(
                    "Account context",
                    "${formatFollowers(candidate.followerCount)} followers",
                    candidate.followerCount > 5_000
                )
            )
            add(
                Signal(
                    "Monetization",
                    if (candidate.monetized) "Monetized account" else "No monetization signals",
                    candidate.monetized
                )
            )
            if (candidate.faceSimilarity > 0.0) {
                add(
                    Signal(
                        "Simulated face signal (detector unavailable)",
                        pct(candidate.faceSimilarity),
                        candidate.faceSimilarity >= 0.80
                    )
                )
            }
        }

        val summary = buildSummary(classification, candidate, postedAfterOriginal, daysAfter)

        val evidence = buildString {
            append("Compared the original fingerprint (")
            append(content.perceptualHash.take(12))
            append("…) against the candidate on ${candidate.platform}. ")
            append(candidate.transformNote)
            append(" Blended similarity ${pct(candidate.overallSimilarity)}.")
        }

        return VerificationResult(
            classification = classification,
            confidence = round2(confidence),
            severity = severity,
            summary = summary,
            signals = signals,
            evidenceSummary = evidence + " Demo evidence; confidence is a rule score, not a calibrated probability. Similarity does not prove infringement. Attribution and permission require separate review.",
            engine = displayName
        )
    }

    private fun severityFor(
        classification: Classification,
        candidate: CandidateMatch,
        score: Double
    ): Severity = when (classification) {
        Classification.FALSE_POSITIVE -> Severity.LOW
        Classification.GENUINE_LIKENESS_MISUSE -> Severity.HIGH
        Classification.GENUINE_REPOST -> when {
            // Monetized reuse on a large account is the highest-harm repost case.
            candidate.monetized && candidate.followerCount >= 50_000 -> Severity.HIGH
            candidate.monetized || candidate.followerCount >= 50_000 -> Severity.MEDIUM
            score >= 0.90 -> Severity.MEDIUM
            else -> Severity.LOW
        }
    }

    private fun buildSummary(
        classification: Classification,
        candidate: CandidateMatch,
        postedAfter: Boolean,
        daysAfter: Long
    ): String = when (classification) {
        Classification.GENUINE_REPOST -> buildString {
            append("The detected post closely matches the original despite ")
            append(candidate.transformNote.replaceFirstChar { it.lowercase() })
            append(" ")
            if (postedAfter) {
                append("It was published $daysAfter days after the original, ")
                append("and the caption carries no attribution back to the creator. ")
            }
            append("High visual and hash agreement makes genuine reuse the ")
            append("most likely explanation.")
        }

        Classification.GENUINE_LIKENESS_MISUSE ->
            "SIMULATED altered-speech / fake-endorsement scenario. Face and transcript " +
                "signals are synthetic labels, not detector measurements. A matching face " +
                "does not establish manipulation or lack of permission. Human review required."


        Classification.FALSE_POSITIVE -> buildString {
            append("Surface-level similarity is present, but the supporting signals ")
            append("do not hold up: ")
            append(
                if (!postedAfter) "the candidate predates the original content, "
                else "hash and caption agreement are both weak, "
            )
            append("which is more consistent with coincidental resemblance ")
            append("(shared location, format or stock footage) than with reuse.")
        }
    }

    private fun pct(v: Double) = "${(v * 100).toInt()}%"
    private fun round2(v: Double) = kotlin.math.round(v * 100) / 100.0

    private fun formatFollowers(n: Int): String = when {
        n >= 1_000_000 -> "${n / 100_000 / 10.0}M"
        n >= 1_000 -> "${n / 1_000}K"
        else -> n.toString()
    }
}
