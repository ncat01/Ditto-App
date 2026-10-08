package com.ditto.app.ui.screens

import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.AgentKind

private val technicalActivity = Regex(
    "p\\s?hash|perceptual[ -]?hash|fingerprint|imagehash|pillow|hamming|frame[ -]?hash|\\b[0-9a-f]{16,64}\\b",
    RegexOption.IGNORE_CASE
)
private val connectionFailure = Regex(
    "unable to resolve|unknownhost|hostname|failed to connect|connection refused|network is unreachable|no route to host|name or service not known|sockettimeout|timed out|timeout|sslhandshake|certpath",
    RegexOption.IGNORE_CASE
)
private val developerDetails = Regex(
    "https?://|\\.railway\\.app|exception|traceback|stack ?trace|\\bHTTP\\s+\\d{3}|\\b(?:api|backend|sdk)\\b",
    RegexOption.IGNORE_CASE
)
private val unsuccessfulActivity = Regex(
    "\\b(?:failed|failure|error|unavailable|stopped|cancelled|exception)\\b",
    RegexOption.IGNORE_CASE
)

/** Older server history and platform exceptions stay out of customer screens. */
internal fun safeCustomerMessage(raw: String?, fallback: String): String {
    val value = raw?.trim().orEmpty()
    return when {
        value.isBlank() -> fallback
        connectionFailure.containsMatchIn(value) -> "Couldn't reach Ditto. Check your internet connection and try again."
        technicalActivity.containsMatchIn(value) || developerDetails.containsMatchIn(value) || value.length > 300 -> fallback
        else -> value
    }
}

internal fun customerServiceStatus(raw: String): String {
    val normalized = raw.lowercase()
    return when {
        "session" in normalized || "sign in again" in normalized || "log in again" in normalized ->
            "Your session needs to be renewed. Sign out in Profile and log in again."
        connectionFailure.containsMatchIn(raw) || "internet" in normalized || "network" in normalized ->
            "Couldn't reach Ditto. Check your internet connection; we'll try again automatically."
        else -> "Ditto couldn't update this page. We'll try again automatically."
    }
}

internal data class CustomerActivityText(val category: String, val title: String, val detail: String)

internal fun customerActivityText(event: ActivityEvent): CustomerActivityText {
    val category = when (event.agent) {
        AgentKind.INGESTION -> "Your originals"
        AgentKind.DISCOVERY -> "Search"
        AgentKind.VERIFICATION -> "Comparison"
        AgentKind.ACTION_PLANNING -> "Suggested next step"
        AgentKind.FOLLOW_UP -> "Case update"
        AgentKind.HUMAN -> "Your action"
    }
    val failure = unsuccessfulActivity.containsMatchIn(event.title) ||
        unsuccessfulActivity.containsMatchIn(event.detail) || connectionFailure.containsMatchIn(event.detail)
    val fallbackTitle = if (failure) "$category couldn't finish" else when (event.agent) {
        AgentKind.INGESTION -> "Original ready"
        AgentKind.DISCOVERY -> "Search update"
        AgentKind.VERIFICATION -> "Comparison ready"
        AgentKind.ACTION_PLANNING -> "Next step ready for review"
        AgentKind.FOLLOW_UP -> "Case updated"
        AgentKind.HUMAN -> "Action recorded"
    }
    val fallbackDetail = if (failure) "This action did not finish. Open the original or case to check its status before trying again."
        else when (event.agent) {
            AgentKind.INGESTION -> "Your original is ready for search and comparison."
            AgentKind.DISCOVERY -> "Check your original for saved search results and possible matching sources."
            AgentKind.VERIFICATION -> "Review the media, source and permission before deciding what to do."
            AgentKind.ACTION_PLANNING -> "Review the suggested next step. Nothing is sent without your approval."
            AgentKind.FOLLOW_UP -> "Open the case to review its latest update."
            AgentKind.HUMAN -> "Your change was recorded. Open the case to review it."
        }
    return CustomerActivityText(
        category,
        safeCustomerMessage(event.title, fallbackTitle),
        safeCustomerMessage(event.detail, fallbackDetail)
    )
}
