package com.ditto.app.data.repository

import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.DashboardStats
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.domain.model.ScanStage
import kotlinx.coroutines.flow.Flow

/** Result wrapper so callers never deal in thrown exceptions for expected failures. */
sealed interface DittoResult<out T> {
    data class Ok<T>(val value: T) : DittoResult<T>
    data class Err(val message: String, val recoverable: Boolean = true) : DittoResult<Nothing>
}

data class ScanProgress(
    val stage: ScanStage,
    val message: String,
    val candidatesFound: Int = 0,
    val casesCreated: List<String> = emptyList()
)

/**
 * The single contract the UI depends on. The server supplies account data
 * entirely on-device; a Retrofit-backed implementation serves the FastAPI backend.
 */
interface DittoRepository {
    fun observeCases(): Flow<List<Case>>
    fun observeCase(id: String): Flow<Case?>
    fun observeActivity(): Flow<List<ActivityEvent>>
    fun observeContent(): Flow<List<ContentItem>>
    fun observeStats(): Flow<DashboardStats>

    suspend fun ingest(title: String, uri: String?, isVideo: Boolean, source: String = "Local upload"): DittoResult<ContentItem>

    /** Emits progress through every scan stage, creating cases as it goes. */
    fun scan(contentId: String): Flow<DittoResult<ScanProgress>>

    suspend fun approve(caseId: String, editedBody: String?, tone: MessageTone?): DittoResult<Case>
    suspend fun reject(caseId: String, note: String?): DittoResult<Case>
    suspend fun saveDraft(caseId: String, body: String, tone: MessageTone): DittoResult<Case>
    suspend fun runFollowUp(caseId: String, outcome: FollowUpOutcome): DittoResult<Case>
    suspend fun resolve(caseId: String, note: String?): DittoResult<Case>

    /** Cases whose next weekly re-check is due (report §21). */
    suspend fun casesAwaitingFollowUp(): List<Case>


    val verificationEngineName: String
    val discoveryProviderName: String
    val matcherName: String
}

val OPEN_STATES = listOf(
    CaseState.NEW, CaseState.VERIFIED, CaseState.PENDING_APPROVAL,
    CaseState.SENT, CaseState.AWAITING_RESPONSE, CaseState.ESCALATED
)
