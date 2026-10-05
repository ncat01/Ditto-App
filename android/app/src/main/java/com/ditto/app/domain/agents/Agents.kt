package com.ditto.app.domain.agents

import com.ditto.app.domain.model.ActionPlan
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.FollowUpDecision
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.domain.model.VerificationResult

/**
 * Agent contracts. Each agent is a decision-making component — not a chatbot.
 * Mock implementations back the offline demo; LLM-backed implementations can be
 * dropped in without touching callers (report §6, §30).
 */

interface DiscoveryProvider {
    /** Human-readable name shown in the UI so demo vs. live is never ambiguous. */
    val displayName: String
    suspend fun discover(content: ContentItem): List<CandidateMatch>
}

interface ContentMatcher {
    val displayName: String
    /** Perceptual hash of the content at [uri]; falls back to a stable synthetic hash. */
    suspend fun fingerprint(uri: String?, seed: Int): String
}

interface VerificationAgent {
    val displayName: String
    suspend fun verify(content: ContentItem, candidate: CandidateMatch): VerificationResult
}

interface ActionPlanningAgent {
    val displayName: String
    suspend fun plan(
        content: ContentItem,
        candidate: CandidateMatch,
        verification: VerificationResult,
        priorEscalationLevel: Int,
        tone: MessageTone = MessageTone.PROFESSIONAL
    ): ActionPlan
}

interface FollowUpAgent {
    val displayName: String
    suspend fun evaluate(case: Case, observed: FollowUpOutcome): FollowUpDecision
}
