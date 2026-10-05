package com.ditto.app.data.repository

import com.ditto.app.data.demo.DemoCorpus
import com.ditto.app.data.local.ActivityEntity
import com.ditto.app.data.local.CaseHistoryEntity
import com.ditto.app.data.local.DittoDatabase
import com.ditto.app.domain.agents.ActionPlanningAgent
import com.ditto.app.domain.agents.ContentMatcher
import com.ditto.app.domain.agents.DiscoveryProvider
import com.ditto.app.domain.agents.FollowUpAgent
import com.ditto.app.domain.agents.VerificationAgent
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
import com.ditto.app.domain.model.DashboardStats
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import com.ditto.app.domain.model.ScanStage
import com.ditto.app.domain.statemachine.CaseStateMachine
import com.ditto.app.domain.statemachine.TransitionError
import androidx.room.withTransaction
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.delay
import java.util.UUID
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Demo Mode repository: the full Ditto pipeline running on-device against Room.
 * Every state change goes through [CaseStateMachine]; the UI cannot bypass it.
 */
class LocalDittoRepository(
    private val clock: () -> Long,
    private val context: android.content.Context,
    private val userId: String,
    private val db: DittoDatabase,
    private val videoCorpus: com.ditto.app.data.demo.VideoCorpus,
    private val matcher: ContentMatcher,
    private val discovery: DiscoveryProvider,
    private val verifier: VerificationAgent,
    private val planner: ActionPlanningAgent,
    private val followUp: FollowUpAgent
) : DittoRepository {

    override val verificationEngineName: String get() = verifier.displayName
    override val discoveryProviderName: String get() = discovery.displayName
    override val matcherName: String get() = matcher.displayName

    private val caseCounter = AtomicInteger(0)
    private val mutationLock = Mutex()

    private companion object {
        val FOLLOW_UP_INTERVAL: Long = TimeUnit.DAYS.toMillis(7)
    }

    // ---------------------------------------------------------------- observation

    override fun observeCases(): Flow<List<Case>> =
        db.caseDao().observeAll().map { list -> list.map { it.toDomain() } }

    override fun observeCase(id: String): Flow<Case?> =
        combine(
            db.caseDao().observeById(id),
            db.caseHistoryDao().observeForCase(id)
        ) { entity, history ->
            entity?.toDomain(history.map { it.toDomain() })
        }

    override fun observeActivity(): Flow<List<ActivityEvent>> =
        db.activityDao().observeRecent().map { list -> list.map { it.toDomain() } }

    override fun observeContent(): Flow<List<ContentItem>> =
        db.contentDao().observeAll().map { list -> list.map { it.toDomain() } }

    override fun observeStats(): Flow<DashboardStats> =
        combine(
            db.caseDao().observeAll(),
            db.contentDao().observeAll()
        ) { cases, content ->
            val domain = cases.map { it.toDomain() }
            val verified = domain.filter { it.verification != null }
            val reposts = verified.count {
                it.verification!!.classification == Classification.GENUINE_REPOST
            }
            val falsePositives = verified.count {
                it.verification!!.classification == Classification.FALSE_POSITIVE
            }
            val resolved = domain.count { it.state == CaseState.RESOLVED }
            val closed = domain.count { it.state == CaseState.CLOSED }
            DashboardStats(
                contentMonitored = content.size,
                openCases = domain.count { it.state.isOpen },
                awaitingResponse = domain.count {
                    it.state == CaseState.AWAITING_RESPONSE || it.state == CaseState.SENT
                },
                resolved = resolved,
                escalated = domain.count { it.state == CaseState.ESCALATED },
                pendingApproval = domain.count { it.state == CaseState.PENDING_APPROVAL },
                totalCases = domain.size,
                verifiedReposts = reposts,
                falsePositives = falsePositives,
                averageConfidence = verified
                    .mapNotNull { it.verification?.confidence }
                    .average().takeIf { !it.isNaN() } ?: 0.0,
                resolutionRate = if (domain.isEmpty()) 0.0
                else (resolved + closed).toDouble() / domain.size
            )
        }

    // ---------------------------------------------------------------- ingestion

    override suspend fun ingest(
        title: String,
        uri: String?,
        isVideo: Boolean,
        source: String
    ): DittoResult<ContentItem> = runCatching {
        val seed = (clock() % 7).toInt() + 1
        require(title.isNotBlank()) { "Enter a title for your original." }
        val storedUri=uri?.let {
            val source=android.net.Uri.parse(it)
            val mime=context.contentResolver.getType(source).orEmpty()
            require(mime.startsWith("image/") || mime.startsWith("video/")) { "Choose an image or video." }
            val directory=java.io.File(context.filesDir,"originals/$userId").apply { mkdirs() }
            val file=java.io.File(directory,"${UUID.randomUUID()}${if(mime.startsWith("video/")) ".mp4" else ".image"}")
            try {
                context.contentResolver.openInputStream(source)?.use { input -> file.outputStream().use { output ->
                    val buffer=ByteArray(8192);var total=0
                    while(true) { val read=input.read(buffer);if(read<0)break;total+=read;require(total<=25*1024*1024) { "Media exceeds the 25 MB limit." };output.write(buffer,0,read) }
                } } ?: error("Could not open media")
                android.net.Uri.fromFile(file).toString()
            } catch(e:Exception) { file.delete();throw e }
        }
        val hash = matcher.fingerprint(storedUri, seed)
        val now = clock()
        val item = ContentItem(
            id = "content_${UUID.randomUUID().toString().take(8)}",
            title = title.ifBlank { "Untitled upload" },
            kind = if (isVideo) ContentKind.VIDEO else ContentKind.IMAGE,
            localUri = storedUri,
            perceptualHash = hash,
            paletteSeed = seed,
            publishedAt = now,
            createdAt = now,
            sourcePlatform = source.ifBlank { "Local upload" }.take(256)
        )
        db.contentDao().upsert(item.toEntity())
        logActivity(
            AgentKind.INGESTION,
            "Fingerprint generated",
            "${item.title} → pHash ${hash.take(12)}… (${matcher.displayName})",
            null
        )
        item
    }.fold(
        onSuccess = { DittoResult.Ok(it) },
        onFailure = { DittoResult.Err("Couldn't process that file. ${it.message.orEmpty()}") }
    )

    // ---------------------------------------------------------------- scan pipeline

    override fun scan(contentId: String): Flow<DittoResult<ScanProgress>> = flow {
        var content = db.contentDao().byId(contentId)?.toDomain()
            ?: run {
                emit(DittoResult.Err("That content is no longer available. Try re-uploading."))
                return@flow
            }

        var job=com.ditto.app.data.local.ScanJobEntity(UUID.randomUUID().toString(),contentId,clock(),"ingesting",content.perceptualHash)
        db.scanJobDao().save(job)
        emit(DittoResult.Ok(ScanProgress(ScanStage.INGESTING, "Reading ${content.title}")))
        delay(320)

        val fingerprint=runCatching { matcher.fingerprint(content.localUri,content.paletteSeed) }.getOrElse {
            db.scanJobDao().save(job.copy(stage="failed",error=it.message))
            emit(DittoResult.Err("Fingerprint unavailable. ${it.message}"));return@flow
        }
        content=content.copy(perceptualHash=fingerprint)
        db.contentDao().upsert(content.toEntity())
        job=job.copy(stage="fingerprinting",fingerprint=fingerprint);db.scanJobDao().save(job)
        emit(
            DittoResult.Ok(
                ScanProgress(
                    ScanStage.FINGERPRINTING,
                    "pHash ${content.perceptualHash.take(12)}…"
                )
            )
        )
        delay(360)

        emit(
            DittoResult.Ok(
                ScanProgress(ScanStage.DISCOVERING, "Querying ${discovery.displayName}")
            )
        )
        job=job.copy(stage="discovery");db.scanJobDao().save(job)
        val candidates = runCatching { discovery.discover(content) }.getOrElse {
            db.scanJobDao().save(job.copy(stage="failed",error=it.message))
            emit(DittoResult.Err("Discovery provider unavailable. ${it.message.orEmpty()}"))
            return@flow
        }
        logActivity(
            AgentKind.DISCOVERY,
            "Discovery complete",
            "${candidates.size} candidate${if (candidates.size == 1) "" else "s"} " +
                "surfaced for \"${content.title}\"",
            null
        )
        delay(420)

        emit(
            DittoResult.Ok(
                ScanProgress(
                    ScanStage.VERIFYING,
                    "Verifying ${candidates.size} candidates",
                    candidatesFound = candidates.size
                )
            )
        )

        job=job.copy(stage="verification",candidates=candidates.size);db.scanJobDao().save(job)
        val created = mutableListOf<String>()
        for (candidate in candidates) {
            // Skip candidates that already have a case so re-scans don't duplicate.
            if (db.caseDao().countByCandidate(candidate.id) > 0) continue
            val caseId = createCaseFor(content, candidate)
            created += caseId
            delay(220)
        }

        emit(
            DittoResult.Ok(
                ScanProgress(
                    ScanStage.PREPARING,
                    "Preparing cases",
                    candidatesFound = candidates.size,
                    casesCreated = created
                )
            )
        )
        delay(260)

        db.scanJobDao().save(job.copy(stage="complete"))
        emit(
            DittoResult.Ok(
                ScanProgress(
                    ScanStage.DONE,
                    if (candidates.isEmpty()) "No potential matches found"
                    else "${candidates.size} potential match" +
                        "${if (candidates.size == 1) "" else "es"} found",
                    candidatesFound = candidates.size,
                    casesCreated = created
                )
            )
        )
    }

    /**
     * Runs Verification -> Action Planning -> state transitions for one candidate,
     * writing every step to the audit trail.
     */
    private suspend fun createCaseFor(content: ContentItem, candidate: CandidateMatch): String {
        val now = clock()
        val caseId = nextCaseId()

        var case = Case(
            id = caseId,
            contentId = content.id,
            contentTitle = content.title,
            contentPaletteSeed = content.paletteSeed,
            candidate = candidate,
            verification = null,
            plan = null,
            state = CaseState.NEW,
            escalationLevel = 0,
            followUpCount = 0,
            createdAt = now,
            updatedAt = now,
            nextFollowUpAt = null,
            lastActionAt = null
        )
        db.caseDao().upsert(case.toEntity())
        recordHistory(
            caseId, null, CaseState.NEW, AgentKind.DISCOVERY,
            "Case opened",
            "Candidate ${candidate.accountHandle} on ${candidate.platform} surfaced by " +
                discovery.displayName
        )

        // --- Verification Agent ---------------------------------------------------
        val verification = verifier.verify(content, candidate)
        case = case.copy(verification = verification, updatedAt = clock())
        applyTransition(
            case, CaseState.VERIFIED, AgentKind.VERIFICATION,
            "Verified as ${verification.classification.label}",
            verification.summary
        )
        logActivity(
            AgentKind.VERIFICATION,
            "Verified as ${verification.classification.label}",
            "${candidate.accountHandle} · ${(verification.confidence * 100).toInt()}% confidence",
            caseId
        )
        case = case.copy(state = CaseState.VERIFIED)

        // --- Action-Planning Agent ------------------------------------------------
        val plan = planner.plan(content, candidate, verification, priorEscalationLevel = 0)
        case = case.copy(plan = plan, updatedAt = clock())

        if (plan.action == ActionType.LOG_ONLY) {
            // Log-only cases close immediately — nothing is ever sent.
            applyTransition(
                case, CaseState.CLOSED, AgentKind.ACTION_PLANNING,
                "Logged, no action", plan.reasoning
            )
            logActivity(
                AgentKind.ACTION_PLANNING, "Logged without action",
                "${candidate.accountHandle} · ${verification.classification.label}", caseId
            )
        } else {
            applyTransition(
                case, CaseState.PENDING_APPROVAL, AgentKind.ACTION_PLANNING,
                "Recommends ${plan.action.label}", plan.reasoning
            )
            logActivity(
                AgentKind.ACTION_PLANNING, "${plan.action.label} recommended",
                "${candidate.accountHandle} · awaiting human approval", caseId
            )
        }
        return caseId
    }

    // ---------------------------------------------------------------- approval gate

    override suspend fun approve(
        caseId: String,
        editedBody: String?,
        tone: MessageTone?
    ): DittoResult<Case> = mutate(caseId) { case ->
        val plan = case.plan ?: return@mutate DittoResult.Err("This case has no proposed action.")
        if (case.state != CaseState.PENDING_APPROVAL && case.state != CaseState.ESCALATED) {
            return@mutate DittoResult.Err(
                "Only a case awaiting approval can be approved. " +
                    "This case is ${case.state.label}."
            )
        }
        val updatedPlan = plan.copy(
            draftBody = editedBody ?: plan.draftBody,
            tone = tone ?: plan.tone
        )
        val now = clock()
        val staged = case.copy(
            plan = updatedPlan,
            escalationLevel = maxOf(case.escalationLevel, updatedPlan.action.tier),
            lastActionAt = now,
            nextFollowUpAt = now + FOLLOW_UP_INTERVAL,
            updatedAt = now
        )
        applyTransition(
            staged, CaseState.SENT, AgentKind.HUMAN,
            "Approved: ${updatedPlan.action.label}",
            "Human reviewer approved the proposed ${updatedPlan.action.label.lowercase()}. " +
                "Message prepared and dispatched to the sandboxed outreach queue " +
                "(no live platform message is sent in Demo Mode). " +
                "Sandbox receipt: recipient=${case.candidate.accountHandle}; channel=sandbox; body=${updatedPlan.draftBody}"
        )
        logActivity(
            AgentKind.HUMAN, "${updatedPlan.action.label} approved",
            "${case.candidate.accountHandle} · message prepared (simulated send)", caseId
        )

        // Dispatch immediately moves the case to awaiting_response so the weekly
        // follow-up loop can pick it up.
        val sent = staged.copy(state = CaseState.SENT)
        applyTransition(
            sent, CaseState.AWAITING_RESPONSE, AgentKind.FOLLOW_UP,
            "Awaiting response",
            "Outreach dispatched. The Follow-Up Agent will re-evaluate this case at the " +
                "next weekly interval, or immediately when a manual check is run."
        )
        DittoResult.Ok(loadCase(caseId)!!)
    }

    override suspend fun reject(caseId: String, note: String?): DittoResult<Case> =
        mutate(caseId) { case ->
            if (case.state != CaseState.PENDING_APPROVAL && case.state != CaseState.ESCALATED) {
                return@mutate DittoResult.Err(
                    "Only a case awaiting approval can be rejected. " +
                        "This case is ${case.state.label}."
                )
            }
            applyTransition(
                case, CaseState.CLOSED, AgentKind.HUMAN,
                "Rejected by reviewer",
                note?.takeIf { it.isNotBlank() }
                    ?: "Human reviewer rejected the proposed action. No outreach was sent " +
                    "and the case is closed."
            )
            logActivity(
                AgentKind.HUMAN, "Action rejected",
                "${case.candidate.accountHandle} · case closed without outreach", caseId
            )
            DittoResult.Ok(loadCase(caseId)!!)
        }

    override suspend fun saveDraft(
        caseId: String,
        body: String,
        tone: MessageTone
    ): DittoResult<Case> = mutate(caseId) { case ->
        if(case.state != CaseState.PENDING_APPROVAL && case.state != CaseState.ESCALATED) return@mutate DittoResult.Err("Only a pending action can be edited.")
        val plan = case.plan ?: return@mutate DittoResult.Err("This case has no draft to edit.")
        val updated = case.copy(
            plan = plan.copy(draftBody = body, tone = tone),
            updatedAt = clock()
        )
        db.caseDao().upsert(updated.toEntity())
        recordHistory(
            caseId, case.state, case.state, AgentKind.HUMAN,
            "Draft edited",
            "Reviewer edited the outgoing message (tone: ${tone.label}). " +
                "The case remains at ${case.state.label} pending approval."
        )
        DittoResult.Ok(loadCase(caseId)!!)
    }

    // ---------------------------------------------------------------- follow-up loop

    override suspend fun runFollowUp(
        caseId: String,
        outcome: FollowUpOutcome
    ): DittoResult<Case> = mutate(caseId) { case ->
        if (case.state != CaseState.AWAITING_RESPONSE && case.state != CaseState.ESCALATED) {
            return@mutate DittoResult.Err(
                "Follow-up only applies to a case awaiting a response. " +
                    "This case is ${case.state.label}."
            )
        }
        val decision = followUp.evaluate(case, outcome)
        val now = clock()

        var updated = case.copy(
            followUpCount = case.followUpCount + 1,
            nextFollowUpAt = if (decision.nextState.isTerminal) null
            else now + FOLLOW_UP_INTERVAL,
            updatedAt = now
        )

        // An escalation raises the action tier and returns to the approval gate:
        // the agent proposes, the human still decides.
        decision.escalateTo?.let { target ->
            val content = db.contentDao().byId(case.contentId)?.toDomain()
            val verification = case.verification
            if (content != null && verification != null) {
                val newPlan = planner.plan(
                    content, case.candidate, verification,
                    priorEscalationLevel = target.tier,
                    tone = case.plan?.tone ?: MessageTone.PROFESSIONAL
                )
                updated = updated.copy(
                    plan = newPlan,
                    escalationLevel = maxOf(updated.escalationLevel, target.tier)
                )
            }
        }

        if (decision.nextState == case.state) {
            db.caseDao().upsert(updated.toEntity())
            recordHistory(
                caseId, case.state, case.state, AgentKind.FOLLOW_UP,
                decision.headline, decision.reasoning
            )
        } else {
            applyTransition(
                updated, decision.nextState, AgentKind.FOLLOW_UP,
                decision.headline, decision.reasoning
            )
        }

        logActivity(
            AgentKind.FOLLOW_UP,
            decision.headline.removeSuffix("."),
            "${case.id} · observed: ${outcome.label}",
            caseId
        )
        DittoResult.Ok(loadCase(caseId)!!)
    }

    override suspend fun resolve(caseId: String, note: String?): DittoResult<Case> =
        mutate(caseId) { case ->
            val result = CaseStateMachine.transition(case.state, CaseState.RESOLVED)
            if (result is CaseStateMachine.TransitionResult.Rejected) {
                return@mutate DittoResult.Err(result.reason)
            }
            applyTransition(
                case.copy(nextFollowUpAt = null), CaseState.RESOLVED, AgentKind.HUMAN,
                "Marked resolved",
                note?.takeIf { it.isNotBlank() }
                    ?: "Reviewer confirmed the case is resolved. Follow-up cancelled."
            )
            logActivity(
                AgentKind.HUMAN, "Case resolved",
                "${case.candidate.accountHandle} · ${case.id}", caseId
            )
            DittoResult.Ok(loadCase(caseId)!!)
        }

    override suspend fun casesAwaitingFollowUp(): List<Case> =
        db.caseDao()
            .byStates(listOf(CaseState.AWAITING_RESPONSE.wire, CaseState.ESCALATED.wire))
            .map { it.toDomain() }

    // ---------------------------------------------------------------- seeding

    override suspend fun seedDemoData(force: Boolean): DittoResult<Int> = runCatching {
        if (!force && db.caseDao().count() > 0) return@runCatching 0
        if (force) {
            db.caseHistoryDao().clear()
            db.caseDao().clear()
            db.activityDao().clear()
        }

        val measuredContent = DemoCorpus.content.map { videoCorpus.original(it) }
        db.contentDao().upsertAll(measuredContent.map { it.toEntity() })
        var created = 0

        for (seeded in DemoCorpus.candidates) {
            val content = measuredContent.first { it.id == seeded.match.contentId }
            val caseId = createCaseFor(content, videoCorpus.measured(seeded.match))
            created++

            // Advance the seeded cases to the varied states the demo script expects,
            // driving each one through the real state machine rather than writing
            // states directly.
            when (seeded.match.id) {
                "cand_001" -> Unit // stays PENDING_APPROVAL
                "cand_002" -> {
                    approve(caseId, null, null)
                    runFollowUp(caseId, FollowUpOutcome.NO_RESPONSE)
                }
                "cand_003" -> Unit // false positive -> already CLOSED by the planner
                "cand_004" -> {
                    approve(caseId, null, null)
                    runFollowUp(caseId, FollowUpOutcome.ATTRIBUTION_ADDED)
                }
                "cand_005" -> Unit // likeness misuse -> PENDING_APPROVAL
                "cand_006" -> approve(caseId, null, null) // AWAITING_RESPONSE
            }
        }
        created
    }.fold(
        onSuccess = { DittoResult.Ok(it) },
        onFailure = { DittoResult.Err("Couldn't seed demo data: ${it.message.orEmpty()}") }
    )

    override suspend fun resetDemoData(): DittoResult<Int> {
        com.ditto.app.core.DemoClock.reset(context,userId)
        return seedDemoData(force=true)
    }

    // ---------------------------------------------------------------- internals

    /**
     * The only path that writes a new state. Refuses illegal transitions via the
     * state machine and records every accepted transition in case history.
     */
    private suspend fun applyTransition(
        case: Case,
        to: CaseState,
        agent: AgentKind,
        action: String,
        reasoning: String
    ) {
        when (val result = CaseStateMachine.transition(case.state, to)) {
            is CaseStateMachine.TransitionResult.Rejected ->
                throw TransitionError(result.reason)

            is CaseStateMachine.TransitionResult.Success -> {
                val updated = case.copy(
                    state = result.state,
                    updatedAt = clock()
                )
                db.caseDao().upsert(updated.toEntity())
                recordHistory(case.id, case.state, result.state, agent, action, reasoning)
            }
        }
    }

    private suspend fun recordHistory(
        caseId: String,
        from: CaseState?,
        to: CaseState?,
        agent: AgentKind,
        action: String,
        reasoning: String
    ) {
        db.caseHistoryDao().insert(
            CaseHistoryEntity(
                caseId = caseId,
                timestamp = clock(),
                previousState = from?.wire,
                newState = to?.wire,
                agent = agent.wire,
                action = action,
                reasoning = reasoning
            )
        )
    }

    private suspend fun logActivity(
        agent: AgentKind,
        title: String,
        detail: String,
        caseId: String?
    ) {
        db.activityDao().insert(
            ActivityEntity(
                timestamp = clock(),
                agent = agent.wire,
                title = title,
                detail = detail,
                caseId = caseId
            )
        )
    }

    private suspend fun loadCase(id: String): Case? {
        val entity = db.caseDao().byId(id) ?: return null
        val history = db.caseHistoryDao().forCase(id).map { it.toDomain() }
        return entity.toDomain(history)
    }

    /** Loads a case, runs [block], and converts any thrown transition error to an Err. */
    private suspend fun mutate(
        caseId: String,
        block: suspend (Case) -> DittoResult<Case>
    ): DittoResult<Case> = runCatching {
        val case = loadCase(caseId)
            ?: return DittoResult.Err("Case $caseId not found.", recoverable = false)
        mutationLock.withLock {
            db.withTransaction {
                val fresh = loadCase(caseId) ?: error("Case unavailable")
                block(fresh)
            }
        }
    }.getOrElse { e ->
        when (e) {
            is TransitionError -> DittoResult.Err(e.message ?: "Invalid state transition.")
            else -> DittoResult.Err("Something went wrong: ${e.message.orEmpty()}")
        }
    }

    private suspend fun nextCaseId(): String {
        if (caseCounter.get() == 0) caseCounter.set(db.caseDao().count())
        val n = caseCounter.incrementAndGet()
        return "DIT-${UUID.randomUUID().toString().take(12)}"
    }
}
