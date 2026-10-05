package com.ditto.app.data.repository

import com.ditto.app.data.local.ActivityEntity
import com.ditto.app.data.local.CaseEntity
import com.ditto.app.data.local.CaseHistoryEntity
import com.ditto.app.data.local.ContentEntity
import com.ditto.app.domain.model.ActionPlan
import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.AgentKind
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseHistoryEntry
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.ContentKind
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.domain.model.Severity
import com.ditto.app.domain.model.Signal
import com.ditto.app.domain.model.VerificationResult
import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json

private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

@Serializable
private data class SignalDto(val name: String, val value: String, val supportsMatch: Boolean)

private val signalListSerializer = ListSerializer(SignalDto.serializer())
private val stringListSerializer = ListSerializer(String.serializer())

fun List<Signal>.encode(): String = json.encodeToString(
    signalListSerializer,
    map { SignalDto(it.name, it.value, it.supportsMatch) }
)

fun String?.decodeSignals(): List<Signal> = runCatching {
    this?.let {
        json.decodeFromString(signalListSerializer, it)
            .map { d -> Signal(d.name, d.value, d.supportsMatch) }
    }.orEmpty()
}.getOrDefault(emptyList())

fun List<String>.encodeStrings(): String = json.encodeToString(stringListSerializer, this)

fun String?.decodeStrings(): List<String> = runCatching {
    this?.let { json.decodeFromString(stringListSerializer, it) }.orEmpty()
}.getOrDefault(emptyList())

fun ContentEntity.toDomain() = ContentItem(
    id = id,
    title = title,
    kind = ContentKind.from(kind),
    localUri = localUri,
    perceptualHash = perceptualHash,
    paletteSeed = paletteSeed,
    publishedAt = publishedAt,
    createdAt = createdAt,
    sourcePlatform = sourcePlatform
)

fun ContentItem.toEntity() = ContentEntity(
    id = id,
    title = title,
    kind = kind.wire,
    localUri = localUri,
    perceptualHash = perceptualHash,
    paletteSeed = paletteSeed,
    publishedAt = publishedAt,
    createdAt = createdAt,
    sourcePlatform = sourcePlatform
)

fun CaseEntity.toCandidate() = CandidateMatch(
    id = candidateId,
    contentId = contentId,
    platform = platform,
    accountName = accountName,
    accountHandle = accountHandle,
    sourceUrl = sourceUrl,
    caption = caption,
    followerCount = followerCount,
    monetized = monetized,
    hashSimilarity = hashSimilarity,
    visualSimilarity = visualSimilarity,
    captionSimilarity = captionSimilarity,
    faceSimilarity = faceSimilarity,
    postedAt = postedAt,
    transformNote = transformNote,
    paletteSeed = candidatePaletteSeed,
    discoveredAt = discoveredAt,
    attributionPresent = attributionPresent,
    permissionGranted = permissionGranted
)

fun CaseEntity.toDomain(history: List<CaseHistoryEntry> = emptyList()): Case {
    val verification = classification?.let {
        VerificationResult(
            classification = Classification.from(it),
            confidence = confidence ?: 0.0,
            severity = Severity.from(severity.orEmpty()),
            summary = verificationSummary.orEmpty(),
            signals = verificationSignals.decodeSignals(),
            evidenceSummary = evidenceSummary.orEmpty(),
            engine = verificationEngine.orEmpty()
        )
    }
    val plan = recommendedAction?.let {
        ActionPlan(
            action = ActionType.from(it),
            priority = Severity.from(actionPriority.orEmpty()),
            reasoning = actionReasoning.orEmpty(),
            factors = actionFactors.decodeStrings(),
            draftSubject = draftSubject.orEmpty(),
            draftBody = draftBody.orEmpty(),
            tone = MessageTone.from(tone.orEmpty()),
            engine = planEngine.orEmpty()
        )
    }
    return Case(
        id = id,
        contentId = contentId,
        contentTitle = contentTitle,
        contentPaletteSeed = contentPaletteSeed,
        candidate = toCandidate(),
        verification = verification,
        plan = plan,
        state = CaseState.from(currentState),
        escalationLevel = escalationLevel,
        followUpCount = followUpCount,
        createdAt = createdAt,
        updatedAt = updatedAt,
        nextFollowUpAt = nextFollowUpAt,
        lastActionAt = lastActionAt,
        history = history
    )
}

fun Case.toEntity() = CaseEntity(
    id = id,
    contentId = contentId,
    contentTitle = contentTitle,
    contentPaletteSeed = contentPaletteSeed,
    candidateId = candidate.id,
    platform = candidate.platform,
    accountName = candidate.accountName,
    accountHandle = candidate.accountHandle,
    sourceUrl = candidate.sourceUrl,
    caption = candidate.caption,
    followerCount = candidate.followerCount,
    monetized = candidate.monetized,
    hashSimilarity = candidate.hashSimilarity,
    visualSimilarity = candidate.visualSimilarity,
    captionSimilarity = candidate.captionSimilarity,
    faceSimilarity = candidate.faceSimilarity,
    postedAt = candidate.postedAt,
    transformNote = candidate.transformNote,
    candidatePaletteSeed = candidate.paletteSeed,
    discoveredAt = candidate.discoveredAt,
    attributionPresent = candidate.attributionPresent,
    permissionGranted = candidate.permissionGranted,
    classification = verification?.classification?.wire,
    confidence = verification?.confidence,
    severity = verification?.severity?.wire,
    verificationSummary = verification?.summary,
    verificationSignals = verification?.signals?.encode(),
    evidenceSummary = verification?.evidenceSummary,
    verificationEngine = verification?.engine,
    recommendedAction = plan?.action?.wire,
    actionPriority = plan?.priority?.wire,
    actionReasoning = plan?.reasoning,
    actionFactors = plan?.factors?.encodeStrings(),
    draftSubject = plan?.draftSubject,
    draftBody = plan?.draftBody,
    tone = plan?.tone?.wire,
    planEngine = plan?.engine,
    currentState = state.wire,
    escalationLevel = escalationLevel,
    followUpCount = followUpCount,
    createdAt = createdAt,
    updatedAt = updatedAt,
    nextFollowUpAt = nextFollowUpAt,
    lastActionAt = lastActionAt
)

fun CaseHistoryEntity.toDomain() = CaseHistoryEntry(
    id = id,
    caseId = caseId,
    timestamp = timestamp,
    previousState = previousState?.let { CaseState.from(it) },
    newState = newState?.let { CaseState.from(it) },
    agent = AgentKind.from(agent),
    action = action,
    reasoning = reasoning
)

fun ActivityEntity.toDomain() = ActivityEvent(
    id = id,
    timestamp = timestamp,
    agent = AgentKind.from(agent),
    title = title,
    detail = detail,
    caseId = caseId
)
