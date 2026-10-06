package com.ditto.app.domain.model

/**
 * Case lifecycle exactly as defined in the Ditto project report §5:
 * new -> pending_approval -> sent -> awaiting_response -> escalated -> resolved/closed
 */
enum class CaseState(val wire: String, val label: String) {
    NEW("new", "New"),
    VERIFIED("verified", "Verified"),
    PENDING_APPROVAL("pending_approval", "Pending Approval"),
    SENT("sent", "Sent"),
    AWAITING_RESPONSE("awaiting_response", "Awaiting Response"),
    ESCALATED("escalated", "Escalated"),
    RESOLVED("resolved", "Resolved"),
    CLOSED("closed", "Closed");

    val isTerminal: Boolean get() = this == RESOLVED || this == CLOSED
    val isOpen: Boolean get() = !isTerminal

    companion object {
        fun from(wire: String): CaseState =
            entries.firstOrNull { it.wire == wire } ?: NEW
    }
}

/** Verification Agent output classes (report §4, layer 3). */
enum class Classification(val wire: String, val label: String) {
    GENUINE_REPOST("genuine_repost", "Genuine Repost"),
    GENUINE_LIKENESS_MISUSE("genuine_likeness_misuse", "Simulated Likeness Misuse"),
    FALSE_POSITIVE("false_positive", "False Positive");

    companion object {
        fun from(wire: String): Classification =
            entries.firstOrNull { it.wire == wire } ?: FALSE_POSITIVE
    }
}

enum class Severity(val wire: String, val label: String, val rank: Int) {
    LOW("low", "Low", 1),
    MEDIUM("medium", "Medium", 2),
    HIGH("high", "High", 3);

    companion object {
        fun from(wire: String): Severity =
            entries.firstOrNull { it.wire == wire } ?: LOW
    }
}

/** Action-Planning Agent output (report §4, layer 4). */
enum class ActionType(val wire: String, val label: String, val tier: Int) {
    LOG_ONLY("log_only", "Log Only", 0),
    ATTRIBUTION_REQUEST("attribution_request", "Attribution Request", 1),
    FORMAL_TAKEDOWN("formal_takedown", "Formal Takedown Notice", 2),
    REVIEW_REQUEST("review_request", "Human Review Request", 1);

    companion object {
        fun from(wire: String): ActionType =
            entries.firstOrNull { it.wire == wire } ?: LOG_ONLY
    }
}

enum class MessageTone(val wire: String, val label: String) {
    PROFESSIONAL("professional", "Professional"),
    FIRM("firm", "Firm"),
    NEUTRAL("neutral", "Neutral");

    companion object {
        fun from(wire: String): MessageTone =
            entries.firstOrNull { it.wire == wire } ?: PROFESSIONAL
    }
}

/** Which agent produced a decision — used for the activity feed and audit trail. */
enum class AgentKind(val wire: String, val label: String) {
    INGESTION("ingestion", "Ingestion"),
    DISCOVERY("discovery", "Discovery"),
    VERIFICATION("verification", "Verification Agent"),
    ACTION_PLANNING("action_planning", "Action-Planning Agent"),
    FOLLOW_UP("follow_up", "Follow-Up Agent"),
    HUMAN("human", "Human Reviewer");

    companion object {
        fun from(wire: String): AgentKind =
            entries.firstOrNull { it.wire == wire } ?: VERIFICATION
    }
}

/** Simulated outcomes the Follow-Up Agent can observe (report §21). */
enum class FollowUpOutcome(val wire: String, val label: String) {
    NO_RESPONSE("no_response", "No response"),
    PARTIAL_RESPONSE("partial_response", "Partial response"),
    HOSTILE_RESPONSE("hostile_response", "Hostile response"),
    ATTRIBUTION_ADDED("attribution_added", "Attribution added"),
    CONTENT_REMOVED("content_removed", "Content removed");

    companion object {
        fun from(wire: String): FollowUpOutcome =
            entries.firstOrNull { it.wire == wire } ?: NO_RESPONSE
    }
}

enum class ContentKind(val wire: String) { IMAGE("image"), VIDEO("video");
    companion object { fun from(w: String) = entries.firstOrNull { it.wire == w } ?: IMAGE }
}

/** A piece of the creator's own content (Layer 1 — Ingestion). */
data class ContentItem(
    val id: String,
    val title: String,
    val kind: ContentKind,
    val localUri: String?,
    val perceptualHash: String,
    val paletteSeed: Int,
    val publishedAt: Long,
    val createdAt: Long,
    val sourcePlatform: String = "Local upload"
)

/** A discovery result before verification (Layer 2 — Discovery). */
data class CandidateMatch(
    val id: String,
    val contentId: String,
    val platform: String,
    val accountName: String,
    val accountHandle: String,
    val sourceUrl: String,
    val caption: String,
    val followerCount: Int,
    val monetized: Boolean,
    val hashSimilarity: Double,
    val visualSimilarity: Double,
    val captionSimilarity: Double,
    val faceSimilarity: Double,
    val postedAt: Long,
    val transformNote: String,
    val paletteSeed: Int,
    val discoveredAt: Long,
    val attributionPresent: Boolean = false,
    val permissionGranted: Boolean = false
) {
    /** Blended similarity shown as the headline "% similarity" figure. */
    val overallSimilarity: Double
        get() = if(platform == "Submitted evidence") hashSimilarity else (hashSimilarity * 0.45) + (visualSimilarity * 0.40) + (captionSimilarity * 0.15)
}

data class VerificationResult(
    val classification: Classification,
    val confidence: Double,
    val severity: Severity,
    val summary: String,
    val signals: List<Signal>,
    val evidenceSummary: String,
    val engine: String
)

data class Signal(val name: String, val value: String, val supportsMatch: Boolean)

data class ActionPlan(
    val action: ActionType,
    val priority: Severity,
    val reasoning: String,
    val factors: List<String>,
    val draftSubject: String,
    val draftBody: String,
    val tone: MessageTone,
    val engine: String
)

data class FollowUpDecision(
    val outcome: FollowUpOutcome,
    val nextState: CaseState,
    val escalateTo: ActionType?,
    val reasoning: String,
    val headline: String
)

data class CaseHistoryEntry(
    val id: Long = 0,
    val caseId: String,
    val timestamp: Long,
    val previousState: CaseState?,
    val newState: CaseState?,
    val agent: AgentKind,
    val action: String,
    val reasoning: String
)

/** The central aggregate: one detected case. */
data class Case(
    val id: String,
    val contentId: String,
    val contentTitle: String,
    val contentPaletteSeed: Int,
    val candidate: CandidateMatch,
    val verification: VerificationResult?,
    val plan: ActionPlan?,
    val state: CaseState,
    val escalationLevel: Int,
    val followUpCount: Int,
    val createdAt: Long,
    val updatedAt: Long,
    val nextFollowUpAt: Long?,
    val lastActionAt: Long?,
    val history: List<CaseHistoryEntry> = emptyList()
) {
    val similarityPct: Int get() = (candidate.overallSimilarity * 100).toInt()
    val confidencePct: Int get() = ((verification?.confidence ?: 0.0) * 100).toInt()
}

data class DashboardStats(
    val contentMonitored: Int,
    val openCases: Int,
    val awaitingResponse: Int,
    val resolved: Int,
    val escalated: Int,
    val pendingApproval: Int,
    val totalCases: Int,
    val verifiedReposts: Int,
    val falsePositives: Int,
    val averageConfidence: Double,
    val resolutionRate: Double
)

data class ActivityEvent(
    val id: Long,
    val timestamp: Long,
    val agent: AgentKind,
    val title: String,
    val detail: String,
    val caseId: String?
)

/** Progress stages surfaced by the scan screen (report §14). */
enum class ScanStage(val label: String) {
    IDLE("Idle"),
    INGESTING("Ingesting"),
    FINGERPRINTING("Generating fingerprint"),
    DISCOVERING("Discovering candidates"),
    VERIFYING("Verifying matches"),
    PREPARING("Preparing cases"),
    DONE("Complete")
}
