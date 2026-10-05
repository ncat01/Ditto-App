package com.ditto.app.domain.agents

import com.ditto.app.domain.model.ActionPlan
import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.domain.model.Severity
import com.ditto.app.domain.model.VerificationResult

/**
 * Implements the project's headline contribution: a **confidence-calibrated escalation
 * policy** (report §3). Rather than a fixed "3 strikes" rule, the agent scores each case
 * on weighted, case-specific signals — confidence, severity, monetization, account reach,
 * platform and prior escalation history — and maps that score onto an action tier.
 *
 * The weights are declared as named constants so the policy can be tuned and evaluated
 * against a human-reviewer baseline, which is the evaluation method in report §9.
 */
class MockActionPlanningAgent : ActionPlanningAgent {

    override val displayName: String = "Demo Action-Planning Agent (policy-scored)"

    private companion object {
        const val W_CONFIDENCE = 0.35
        const val W_SEVERITY = 0.25
        const val W_MONETIZATION = 0.20
        const val W_REACH = 0.10
        const val W_HISTORY = 0.10

        // Action-tier thresholds on the aggregate escalation score.
        const val T_ATTRIBUTION = 0.45
        const val T_TAKEDOWN = 0.75

        /**
         * A confirmed match above this confidence always warrants at least an
         * attribution request. The escalation policy decides how hard to push, not
         * whether the creator gets credit at all: without this floor a
         * high-confidence repost on a small, non-monetized account scores below
         * [T_ATTRIBUTION] and would be silently logged.
         */
        const val CONFIRMED_MATCH_CONFIDENCE = 0.75
    }

    override suspend fun plan(
        content: ContentItem,
        candidate: CandidateMatch,
        verification: VerificationResult,
        priorEscalationLevel: Int,
        tone: MessageTone
    ): ActionPlan {
        if(candidate.attributionPresent || candidate.permissionGranted) return ActionPlan(
            ActionType.LOG_ONLY,Severity.LOW,"Credit is present or the demo permission registry explicitly authorizes reuse. A similar video alone does not warrant enforcement.",
            listOf("Attribution checked separately","Permission checked separately"),"","",tone,displayName)
        // A false positive never produces outbound action, whatever the other signals say.
        if (verification.classification == Classification.FALSE_POSITIVE) {
            return ActionPlan(
                action = ActionType.LOG_ONLY,
                priority = Severity.LOW,
                reasoning = "Verification classified this candidate as a false positive " +
                    "at ${pct(verification.confidence)} confidence. No outbound action is " +
                    "warranted; the case is logged so the same candidate is not re-surfaced " +
                    "on the next scan.",
                factors = listOf(
                    "Classification: False positive",
                    "Confidence: ${pct(verification.confidence)}",
                    "No outbound action permitted for false positives"
                ),
                draftSubject = "",
                draftBody = "",
                tone = tone,
                engine = displayName
            )
        }

        if (verification.classification == Classification.GENUINE_LIKENESS_MISUSE || verification.confidence < 0.75) {
            return ActionPlan(ActionType.REVIEW_REQUEST, verification.severity,
                "Evidence is simulated or confidence is low. Review attribution, permission and manipulation separately before proposing enforcement.",
                listOf("Human review required", "No validated manipulation detector", "Confidence is an uncalibrated rule score"),
                "Review evidence for ${content.title}",
                "SANDBOX REVIEW REQUEST: Please review this synthetic scenario. No accusation, infringement determination or takedown is being made. Confirm attribution and permission, then assess any manipulation evidence independently.",
                tone,displayName)
        }
        val confidenceScore = normalizeConfidence(verification.confidence)
        val severityScore = when (verification.severity) {
            Severity.LOW -> 0.20; Severity.MEDIUM -> 0.60; Severity.HIGH -> 1.00
        }
        val monetizationScore = if (candidate.monetized) 1.0 else 0.15
        val reachScore = reachScore(candidate.followerCount)
        val historyScore = (priorEscalationLevel / 2.0).coerceIn(0.0, 1.0)

        val score = (confidenceScore * W_CONFIDENCE) +
            (severityScore * W_SEVERITY) +
            (monetizationScore * W_MONETIZATION) +
            (reachScore * W_REACH) +
            (historyScore * W_HISTORY)

        var action = when {
            score >= T_TAKEDOWN -> ActionType.FORMAL_TAKEDOWN
            score >= T_ATTRIBUTION -> ActionType.ATTRIBUTION_REQUEST
            verification.confidence >= CONFIRMED_MATCH_CONFIDENCE ->
                ActionType.ATTRIBUTION_REQUEST
            else -> ActionType.LOG_ONLY
        }

        // Escalation ratchet: a follow-up round never proposes a weaker action than the
        // tier already attempted on this case.
        if (action.tier < priorEscalationLevel) {
            action = ActionType.entries.first { it.tier == priorEscalationLevel.coerceAtMost(2) }
        }

        val factors = buildList {
            add("Confidence ${pct(verification.confidence)} (weight ${pctW(W_CONFIDENCE)})")
            add("Severity ${verification.severity.label} (weight ${pctW(W_SEVERITY)})")
            add(
                (if (candidate.monetized) "Monetized account" else "Non-monetized account") +
                    " (weight ${pctW(W_MONETIZATION)})"
            )
            add("Reach ${formatFollowers(candidate.followerCount)} followers (weight ${pctW(W_REACH)})")
            add(
                if (priorEscalationLevel == 0) "First detected incident (no prior action)"
                else "Policy escalation tier $priorEscalationLevel proposed; check timeline for actual dispatches"
            )
            add(
                "Aggregate escalation score ${"%.2f".format(score)} → ${action.label}" +
                    if (score < T_ATTRIBUTION && action == ActionType.ATTRIBUTION_REQUEST) {
                        " (raised to the confirmed-match floor)"
                    } else ""
            )
        }

        val reasoning = buildReasoning(action, verification, candidate, priorEscalationLevel, score)
        val (subject, body) = draftFor(action, content, candidate, verification, tone)

        return ActionPlan(
            action = action,
            priority = verification.severity,
            reasoning = reasoning,
            factors = factors,
            draftSubject = subject,
            draftBody = body,
            tone = tone,
            engine = displayName
        )
    }

    /** Maps raw confidence onto 0..1 with the useful band starting at 0.5. */
    private fun normalizeConfidence(c: Double) = ((c - 0.50) / 0.48).coerceIn(0.0, 1.0)

    private fun reachScore(followers: Int) = when {
        followers >= 500_000 -> 1.0
        followers >= 100_000 -> 0.80
        followers >= 25_000 -> 0.55
        followers >= 5_000 -> 0.30
        else -> 0.10
    }

    private fun buildReasoning(
        action: ActionType,
        v: VerificationResult,
        c: CandidateMatch,
        priorLevel: Int,
        score: Double
    ): String = when {
        action == ActionType.FORMAL_TAKEDOWN && score < T_TAKEDOWN ->
            "No response triggered a proposed higher tier. The rule score ${"%.2f".format(score)} remains below the initial ${T_TAKEDOWN} threshold. This is an escalation proposal, not proof of infringement, and requires fresh approval."
        else -> when (action) {
        ActionType.REVIEW_REQUEST -> "Human review is required before any enforcement recommendation."
        ActionType.LOG_ONLY ->
            "Signals are consistent with reuse but fall below the action threshold " +
                "(score ${"%.2f".format(score)} vs ${T_ATTRIBUTION} required). " +
                "The case is logged and monitored rather than actioned, which avoids " +
                "contacting an account on thin evidence."

        ActionType.ATTRIBUTION_REQUEST -> buildString {
            append("${pct(v.confidence)}-confidence ${v.classification.label.lowercase()} ")
            append(if (c.monetized) "on a monetized account. " else "with no monetization signals. ")
            append(
                if (priorLevel == 0) "This is the first detected incident for this account, "
                else "Prior contact has been attempted, "
            )
            if (score < T_ATTRIBUTION) {
                append("Reach and monetization are low, but the match is confirmed, so ")
                append("the creator is still owed credit. ")
            }
            append("so a proportionate attribution request is the appropriate first step ")
            append("rather than a formal notice.")
        }

        ActionType.FORMAL_TAKEDOWN -> buildString {
            append("Escalation score ${"%.2f".format(score)} exceeds the formal-notice ")
            append("threshold of $T_TAKEDOWN. Drivers: ${pct(v.confidence)} confidence, ")
            append("${v.severity.label.lowercase()} severity")
            if (c.monetized) append(", monetized reuse")
            if (c.followerCount >= 100_000) {
                append(", significant reach (${formatFollowers(c.followerCount)})")
            }
            if (priorLevel > 0) append(", and no resolution from the earlier attribution request")
            append(". A formal takedown notice is warranted.")
        }
    }

    }

    private fun draftFor(
        action: ActionType,
        content: ContentItem,
        c: CandidateMatch,
        v: VerificationResult,
        tone: MessageTone
    ): Pair<String, String> {
        val handle = c.accountHandle
        return when (action) {
            ActionType.REVIEW_REQUEST -> "Human review" to "Review evidence; no external enforcement."
            ActionType.LOG_ONLY -> "" to ""

            ActionType.ATTRIBUTION_REQUEST -> {
                val subject = "Attribution request for \"${content.title}\""
                val body = when (tone) {
                    MessageTone.PROFESSIONAL -> """
                        Hi $handle,

                        We noticed that your recent post on ${c.platform} appears to reuse
                        original content titled "${content.title}", first published on
                        ${friendlyDate(content.publishedAt)}.

                        Our review found a ${pct(c.overallSimilarity)} content match. We're
                        glad the work resonated — we'd simply like it credited.

                        Could you please add clear attribution to the original creator in the
                        caption? If you'd prefer to remove the post instead, that works too.

                        Thanks for your time,
                        Sent via Ditto on behalf of the creator
                    """.trimIndent()

                    MessageTone.FIRM -> """
                        Hi $handle,

                        Your post on ${c.platform} reuses original content titled
                        "${content.title}" (published ${friendlyDate(content.publishedAt)})
                        without attribution. Our review found a ${pct(c.overallSimilarity)}
                        content match.

                        Please add clear credit to the original creator in the caption, or
                        remove the post, within 7 days.

                        We would prefer to resolve this directly rather than through a formal
                        platform notice.

                        Sent via Ditto on behalf of the creator
                    """.trimIndent()

                    MessageTone.NEUTRAL -> """
                        Hi $handle,

                        This is a notice regarding your post on ${c.platform}, which our
                        review matched at ${pct(c.overallSimilarity)} against original content
                        titled "${content.title}", published ${friendlyDate(content.publishedAt)}.

                        We are requesting attribution to the original creator.

                        Sent via Ditto on behalf of the creator
                    """.trimIndent()
                }
                subject to body
            }

            ActionType.FORMAL_TAKEDOWN -> {
                val subject = "Formal notice of unauthorized use — \"${content.title}\""
                val body = """
                    FORMAL NOTICE OF UNAUTHORIZED USE

                    Platform: ${c.platform}
                    Reported account: $handle
                    Reported URL: ${c.sourceUrl}
                    Original work: "${content.title}"
                    First published: ${friendlyDate(content.publishedAt)}

                    We are the rights holder of the original work identified above. The
                    reported post appears similar. Permission and attribution must be confirmed by the reviewer.

                    Evidence of match:
                      - Content similarity: ${pct(c.overallSimilarity)}
                      - Verification confidence: ${pct(v.confidence)}
                      - Assessed severity: ${v.severity.label}
                      - Observed modifications: ${c.transformNote}
                      ${if (c.monetized) "- The reported account shows monetization indicators" else ""}

                    Review the timeline for prior contact; this draft does not establish that contact occurred.

                    We request removal of the infringing material, or the addition of clear
                    attribution to the original creator, under the platform's copyright policy.

                    We have a good-faith belief that the use described is not authorized by the
                    rights holder, its agent, or the law.

                    Submitted via Ditto on behalf of the creator
                """.trimIndent()
                subject to body
            }
        }
    }

    private fun friendlyDate(ts: Long): String {
        val d = java.text.SimpleDateFormat("d MMMM yyyy", java.util.Locale.US)
        return d.format(java.util.Date(ts))
    }

    private fun pct(v: Double) = "${(v * 100).toInt()}%"
    private fun pctW(v: Double) = "${(v * 100).toInt()}%"

    private fun formatFollowers(n: Int): String = when {
        n >= 1_000_000 -> "${n / 100_000 / 10.0}M"
        n >= 1_000 -> "${n / 1_000}K"
        else -> n.toString()
    }
}
