package com.ditto.app.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "content")
data class ContentEntity(
    @PrimaryKey val id: String,
    val title: String,
    val kind: String,
    val localUri: String?,
    val perceptualHash: String,
    val paletteSeed: Int,
    val publishedAt: Long,
    val createdAt: Long,
    val sourcePlatform: String
)

@Entity(
    tableName = "cases",
    indices = [Index("contentId"), Index("currentState")]
)
data class CaseEntity(
    @PrimaryKey val id: String,
    val contentId: String,
    val contentTitle: String,
    val contentPaletteSeed: Int,

    // --- candidate (denormalised for fast list rendering) ---
    val candidateId: String,
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
    val candidatePaletteSeed: Int,
    val discoveredAt: Long,
    @androidx.room.ColumnInfo(defaultValue="0") val attributionPresent: Boolean = false,
    @androidx.room.ColumnInfo(defaultValue="0") val permissionGranted: Boolean = false,

    // --- verification ---
    val classification: String?,
    val confidence: Double?,
    val severity: String?,
    val verificationSummary: String?,
    val verificationSignals: String?,   // JSON
    val evidenceSummary: String?,
    val verificationEngine: String?,

    // --- action plan ---
    val recommendedAction: String?,
    val actionPriority: String?,
    val actionReasoning: String?,
    val actionFactors: String?,         // JSON
    val draftSubject: String?,
    val draftBody: String?,
    val tone: String?,
    val planEngine: String?,

    // --- lifecycle ---
    val currentState: String,
    val escalationLevel: Int,
    val followUpCount: Int,
    val createdAt: Long,
    val updatedAt: Long,
    val nextFollowUpAt: Long?,
    val lastActionAt: Long?
)

@Entity(tableName = "case_history", indices = [Index("caseId")])
data class CaseHistoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val caseId: String,
    val timestamp: Long,
    val previousState: String?,
    val newState: String?,
    val agent: String,
    val action: String,
    val reasoning: String
)

@Entity(tableName = "activity")
data class ActivityEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long,
    val agent: String,
    val title: String,
    val detail: String,
    val caseId: String?
)
