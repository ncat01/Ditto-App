package com.ditto.app.ui.screens

import kotlinx.serialization.json.*
import java.net.URI
import java.security.MessageDigest

internal data class SearchLead(val title: String, val url: String, val source: String, val exact: Boolean)

internal data class SearchReceipt(
    val id: String?,
    val state: String?,
    val leads: List<SearchLead> = emptyList(),
    val notice: String = "",
    val error: String = ""
) {
    val active: Boolean get() = state in setOf("queued", "running")
}

/** Mirrors the server's idempotent search identity, so a lost POST response can be recovered exactly. */
internal fun searchReceiptId(userId: String, contentId: String, requestId: String): String =
    MessageDigest.getInstance("SHA-256").digest("$userId:$contentId:$requestId".toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(it) }.take(32)

/** A missing or malformed result must never become a successful zero-match search. */
internal fun readSearchReceipt(raw: String): SearchReceipt {
    val row = Json.parseToJsonElement(raw) as? JsonObject ?: error("Invalid search receipt.")
    fun JsonObject.text(key: String): String? = (get(key) as? JsonPrimitive)?.contentOrNull
    val id = row.text("jobId") ?: row.text("id")
    val state = row.text("state")
    if (id == null && state == null) {
        require(row.containsKey("jobId") && row.containsKey("state")) { "Invalid search receipt." }
        require(row["result"] == null || row["result"] == JsonNull) { "Invalid search receipt." }
        return SearchReceipt(null, null)
    }
    require(id?.matches(Regex("[a-zA-Z0-9._-]{1,36}")) == true) { "Invalid search receipt." }
    require(state in setOf("queued", "running", "complete", "error", "unknown", "cancelled")) { "Invalid search status." }
    if (state != "complete") return SearchReceipt(id, state, error = row.text("error").orEmpty())
    val result = row["result"] as? JsonObject ?: error("The saved search result is unavailable.")
    val matches = result["results"] as? JsonArray ?: error("The saved search results are unreadable.")
    val leads = matches.map { match ->
        val lead = match as? JsonObject ?: error("Invalid matching post.")
        val url = lead.text("url") ?: error("Matching post has no source.")
        val uri = URI(url)
        require(uri.scheme in setOf("https", "http") && !uri.host.isNullOrBlank() && uri.userInfo == null) { "Invalid matching source." }
        SearchLead(lead.text("title").orEmpty(), url, lead.text("source").orEmpty(), lead.text("matchType") == "exact")
    }
    return SearchReceipt(id, state, leads, result.text("notice").orEmpty())
}
