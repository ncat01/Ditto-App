"""Case orchestration: discovery -> verification -> action planning -> approval gate
-> follow-up. Every state write goes through the state machine.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.action_planning import MockActionPlanningAgent
from app.agents.follow_up import MockFollowUpAgent
from app.agents.verification import MockVerificationAgent
from app.config import get_settings
from app.discovery import corpus
from app.matching import hasher
from app.models.enums import (
    ActionType,
    AgentKind,
    CaseState,
    Classification,
    FollowUpOutcome,
    MessageTone,
)
from app.models.tables import (
    ActionDraft,
    DispatchAttempt,
    ActivityEvent,
    CandidateMatch,
    Case,
    CaseHistory,
    Content,
    FollowUpEvent,
)
from app.models.ledger import Fingerprint, ScanJob, Evidence, AgentDecision, Approval, Notification
from app.services.state_machine import InvalidTransition, assert_transition

settings = get_settings()
verifier = MockVerificationAgent()
planner = MockActionPlanningAgent()
follow_up_agent = MockFollowUpAgent()


def _now(db) -> datetime:
    from app.services.scheduler import now
    return now(db)


def _follow_up_due(db) -> datetime:
    return _now(db) + timedelta(days=settings.follow_up_interval_days)


# ---------------------------------------------------------------- helpers


def _log_activity(db: Session, agent: AgentKind, title: str, detail: str,
                  case_id: str | None = None) -> None:
    db.add(
        ActivityEvent(
            user_id=db.info.get("user_id"),timestamp=_now(db), agent=agent.value, title=title,
            detail=detail, case_id=case_id,
        )
    )


def _record_history(db: Session, case_id: str, previous: CaseState | None,
                    new: CaseState | None, agent: AgentKind, action: str,
                    reasoning: str) -> None:
    db.add(
        CaseHistory(
            case_id=case_id, timestamp=_now(db),
            previous_state=previous.value if previous else None,
            new_state=new.value if new else None,
            agent=agent.value, action=action, reasoning=reasoning,
        )
    )


def _apply_transition(db: Session, case: Case, target: CaseState, agent: AgentKind,
                      action: str, reasoning: str) -> None:
    """The only path that writes a new state. Raises InvalidTransition when refused."""
    source = CaseState(case.current_state)
    assert_transition(source, target)
    case.current_state = target.value
    case.updated_at = _now(db)
    _record_history(db, case.id, source, target, agent, action, reasoning)


def _next_case_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Case)) or 0
    return f"DIT-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------- ingestion


def ingest_content(db: Session, title: str, data: bytes | None, kind: str,
                   seed: int | None = None, commit: bool = True) -> Content:
    seed = seed or (int(_now(db).timestamp()) % 7) + 1
    from pathlib import Path
    from app.matching.video import frames
    media_id=uuid.uuid4().hex
    local_uri=None
    if data:
        directory=Path(settings.media_root).resolve()/db.info.get("user_id","legacy")
        directory.mkdir(parents=True,exist_ok=True)
        target=directory/(media_id+(".mp4" if kind=="video" else ".image"))
        target.write_bytes(data)
        try:
            fingerprint="|".join(frames(target)) if kind=="video" else hasher.fingerprint(data,seed)
        except Exception:
            target.unlink(missing_ok=True)
            raise ValueError("Unsupported or unreadable media; no fingerprint was generated")
        local_uri=str(target)
    else:
        fingerprint=hasher.synthetic_hash(seed)

    item = Content(
        id=f"content_{uuid.uuid4().hex[:8]}",
        title=title or "Untitled upload",
        kind=kind,
        user_id=db.info.get("user_id"),
        local_uri=local_uri,
        perceptual_hash=fingerprint,
        palette_seed=seed,
        published_at=_now(db),
        created_at=_now(db),
        source_platform="Local upload",
    )
    db.add(item)
    db.flush()
    db.add(Fingerprint(id=uuid.uuid4().hex,content_id=item.id,algorithm="phash-dct-64",frame_hashes=item.perceptual_hash.split("|")))
    _log_activity(
        db, AgentKind.INGESTION, "Fingerprint generated",
        f"{item.title} -> pHash {item.perceptual_hash[:12]}… ({hasher.DISPLAY_NAME})",
    )
    if commit:
        db.commit()
    return item


# ---------------------------------------------------------------- scan pipeline


def scan_content(db: Session, content_id: str) -> list[Case]:
    content = db.get(Content, content_id)
    if content is None or (db.info.get("user_id") and content.user_id != db.info["user_id"]):
        raise ValueError(f"Content {content_id} not found")

    job=ScanJob(id=uuid.uuid4().hex,content_id=content_id,stage="discovery",stages=["candidate_discovery"],created_at=_now(db))
    db.add(job);db.flush()
    if not db.scalar(select(Fingerprint).where(Fingerprint.content_id==content_id)):
        db.add(Fingerprint(id=uuid.uuid4().hex,content_id=content_id,algorithm="phash-dct-64",frame_hashes=content.perceptual_hash.split("|")))
    from dataclasses import replace
    demo_id = content_id.split(":")[-1]
    seeds = [replace(item, id=f"{db.info.get('user_id', 'legacy')}:{item.id}", content_id=content_id)
             for item in corpus.candidates_for(demo_id)]
    if not seeds:
        # Freshly uploaded content has no seeded corpus entry; derive candidates
        # from its own fingerprint so a live scan still produces results.
        seeds = []  # No invented discoveries for uploaded media.
    from pathlib import Path
    from app.matching.video import frames, compare
    videos=Path(__file__).resolve().parents[3]/"demo_data/videos"
    kinds={"cand_001":"crop","cand_002":"caption","cand_003":"unrelated","cand_004":"resize","cand_005":"fake_endorsement","cand_006":"watermark","cand_007":"credited","cand_008":"authorized","cand_009":"ambiguous"}
    for item in seeds:
        key=item.id.split(":")[-1]
        score=compare(frames(videos/f"original_{item.palette_seed}.mp4"),frames(videos/f"{item.palette_seed}_{kinds[key]}.mp4"))
        item.hash_similarity=score; item.visual_similarity=score
        item.source_url=f"https://demo.invalid/{key}"
        if key == "cand_005":
            item.transform_note = "SIMULATED fake endorsement with authored altered-speech scripts. No face, ASR or manipulation detector ran."
        item.transform_note += " Measured five aligned video frames; synthetic generated asset."
    job.stage="verification";job.stages=["candidate_discovery","similarity_analysis","verification"];job.candidates=len(seeds)
    created: list[Case] = []

    for seed in seeds:
        existing = db.scalar(
            select(Case).where(Case.candidate_id == seed.id)
        )
        if existing is not None:
            continue
        candidate = db.get(CandidateMatch, seed.id)
        if candidate is None:
            candidate = CandidateMatch(
                id=seed.id, content_id=seed.content_id, platform=seed.platform,
                account_name=seed.account_name, account_handle=seed.account_handle,
                source_url=seed.source_url, caption=seed.caption,
                follower_count=seed.follower_count, monetized=seed.monetized,
                hash_similarity=seed.hash_similarity,
                visual_similarity=seed.visual_similarity,
                caption_similarity=seed.caption_similarity,
                face_similarity=seed.face_similarity,
                attribution_present=seed.attribution_present,permission_granted=seed.permission_granted,
                posted_at=corpus.candidate_posted_at(seed),
                transform_note=seed.transform_note, palette_seed=seed.palette_seed,
                discovered_at=_now(db),
            )
            db.add(candidate)
            db.flush()
        created.append(_create_case(db, content, candidate))

    _log_activity(
        db, AgentKind.DISCOVERY, "Discovery complete",
        f"{len(seeds)} candidate(s) surfaced for \"{content.title}\"",
    )
    db.commit()
    job.stage="complete";job.stages=job.stages+["case_creation","complete"];job.finished_at=_now(db)
    db.commit()
    return created


def _create_case(db: Session, content: Content, candidate: CandidateMatch) -> Case:
    case = Case(
        id=_next_case_id(db),
        content_id=content.id,
        candidate_id=candidate.id,
        current_state=CaseState.NEW.value,
        escalation_level=0,
        follow_up_count=0,
        created_at=_now(db),
        updated_at=_now(db),
    )
    db.add(case)
    db.flush()
    _record_history(
        db, case.id, None, CaseState.NEW, AgentKind.DISCOVERY, "Case opened",
        f"Candidate {candidate.account_handle} on {candidate.platform} surfaced by "
        f"{corpus.DISPLAY_NAME}",
    )

    # --- Verification Agent ---
    v = verifier.verify(content, candidate)
    case.classification = v.classification.value
    case.confidence = v.confidence
    case.severity = v.severity.value
    case.verification_summary = v.summary
    case.verification_signals = [
        {"name": s.name, "value": s.value, "supportsMatch": s.supports_match}
        for s in v.signals
    ]
    case.evidence_summary = v.evidence_summary
    case.verification_engine = v.engine
    _apply_transition(
        db, case, CaseState.VERIFIED, AgentKind.VERIFICATION,
        f"Verified as {v.classification.value}", v.summary,
    )
    _log_activity(
        db, AgentKind.VERIFICATION, f"Verified as {v.classification.value}",
        f"{candidate.account_handle} · {int(v.confidence * 100)}% confidence", case.id,
    )

    # --- Action-Planning Agent ---
    plan = planner.plan(content, candidate, v, prior_escalation_level=0)
    case.recommended_action = plan.action.value
    case.action_priority = plan.priority.value
    case.action_reasoning = plan.reasoning
    case.action_factors = plan.factors
    case.draft_subject = plan.draft_subject
    case.draft_body = plan.draft_body
    case.tone = plan.tone.value
    case.plan_engine = plan.engine

    if plan.action is ActionType.LOG_ONLY:
        _apply_transition(
            db, case, CaseState.CLOSED, AgentKind.ACTION_PLANNING,
            "Logged, no action", plan.reasoning,
        )
        _log_activity(
            db, AgentKind.ACTION_PLANNING, "Logged without action",
            f"{candidate.account_handle} · {v.classification.value}", case.id,
        )
    else:
        _apply_transition(
            db, case, CaseState.PENDING_APPROVAL, AgentKind.ACTION_PLANNING,
            f"Recommends {plan.action.label}", plan.reasoning,
        )
        _log_activity(
            db, AgentKind.ACTION_PLANNING, f"{plan.action.label} recommended",
            f"{candidate.account_handle} · awaiting human approval", case.id,
        )
    db.add(Evidence(id=uuid.uuid4().hex,case_id=case.id,kind="video_similarity",simulated=True,payload={"hashSimilarity":candidate.hash_similarity,"visualSimilarity":candidate.visual_similarity,"frameSamples":5,"attributionPresent":candidate.attribution_present,"permissionGranted":candidate.permission_granted,"confidenceCalibrated":False,"manipulationDetector":"unavailable"}))
    for component,output in [("verification",{"classification":case.classification,"confidence":case.confidence,"summary":v.summary}),("action_planning",{"action":plan.action.value,"reasoning":plan.reasoning})]:
        db.add(AgentDecision(id=uuid.uuid4().hex,case_id=case.id,component=component,output=output))
    if content.user_id:db.add(Notification(id=uuid.uuid4().hex,user_id=content.user_id,case_id=case.id,title="Case ready for review" if plan.action is not ActionType.LOG_ONLY else "Match logged without action"))
    return case


# ---------------------------------------------------------------- approval gate


def approve_case(db: Session, case_id: str, edited_body: str | None = None,
                 tone: MessageTone | None = None) -> Case:
    case = _require_case(db, case_id)
    state = CaseState(case.current_state)
    if state not in (CaseState.PENDING_APPROVAL, CaseState.ESCALATED):
        raise InvalidTransition(
            f"Only a case awaiting approval can be approved; this case is {state.value}."
        )
    if not case.recommended_action or case.recommended_action == ActionType.LOG_ONLY.value:
        raise InvalidTransition("This case has no outbound action to approve.")

    if edited_body is not None:
        case.draft_body = edited_body
    if tone is not None:
        case.tone = tone.value

    db.add(Approval(id=uuid.uuid4().hex,case_id=case.id,user_id=db.info.get("user_id"),decision="approved",recipient=case.candidate.account_handle,body=case.draft_body or ""))
    action = ActionType(case.recommended_action)
    case.escalation_level = max(case.escalation_level, action.tier)
    case.last_action_at = _now(db)
    case.next_followup_at = _follow_up_due(db)

    transport_note = (
        "Prepared and recorded. Sandboxed outreach — nothing was transmitted."
    )
    db.add(
        ActionDraft(
            case_id=case.id, action=action.value, tone=case.tone or "professional",
            subject=case.draft_subject or "", body=case.draft_body or "",
            approved_at=_now(db), transmitted=False,
            transport_note=transport_note,
        )
    )

    db.add(DispatchAttempt(id=f"{case.id}:{case.follow_up_count}:{case.escalation_level}",
        case_id=case.id,recipient=case.candidate.account_handle,body=case.draft_body or "",success=True))
    db.flush()  # Dispatch success is durably recorded in the same transaction.
    _apply_transition(
        db, case, CaseState.SENT, AgentKind.HUMAN, f"Approved: {action.label}",
        f"Human reviewer approved the proposed {action.label.lower()}. {transport_note}",
    )
    _apply_transition(
        db, case, CaseState.AWAITING_RESPONSE, AgentKind.FOLLOW_UP, "Awaiting response",
        "Outreach dispatched. The Follow-Up Agent will re-evaluate this case at the next "
        "weekly interval.",
    )
    _log_activity(
        db, AgentKind.HUMAN, f"{action.label} approved",
        f"{case.candidate.account_handle} · {transport_note}", case.id,
    )
    db.commit()
    return case


def reject_case(db: Session, case_id: str, note: str | None = None) -> Case:
    case = _require_case(db, case_id)
    state = CaseState(case.current_state)
    if state not in (CaseState.PENDING_APPROVAL, CaseState.ESCALATED):
        raise InvalidTransition(
            f"Only a case awaiting approval can be rejected; this case is {state.value}."
        )
    db.add(Approval(id=uuid.uuid4().hex,case_id=case.id,user_id=db.info.get("user_id"),decision="rejected",recipient=case.candidate.account_handle,body=case.draft_body or ""))
    _apply_transition(
        db, case, CaseState.CLOSED, AgentKind.HUMAN, "Rejected by reviewer",
        note or "Human reviewer rejected the proposed action. Nothing was sent.",
    )
    _log_activity(
        db, AgentKind.HUMAN, "Action rejected",
        f"{case.candidate.account_handle} · case closed without outreach", case.id,
    )
    db.commit()
    return case


def edit_action(db: Session, case_id: str, body: str, tone: MessageTone) -> Case:
    case = _require_case(db, case_id)
    if case.current_state not in ("pending_approval","escalated"):
        raise InvalidTransition("Only a pending action can be edited")
    if not case.recommended_action:
        raise InvalidTransition("This case has no draft to edit.")
    case.draft_body = body
    case.tone = tone.value
    case.updated_at = _now(db)
    state = CaseState(case.current_state)
    _record_history(
        db, case.id, state, state, AgentKind.HUMAN, "Draft edited",
        f"Reviewer edited the outgoing message (tone: {tone.value}).",
    )
    db.commit()
    return case


# ---------------------------------------------------------------- follow-up


def run_follow_up(db: Session, case_id: str, observed: FollowUpOutcome) -> Case:
    case = _require_case(db, case_id)
    state = CaseState(case.current_state)
    if state not in (CaseState.AWAITING_RESPONSE, CaseState.ESCALATED):
        raise InvalidTransition(
            f"Follow-up only applies to a case awaiting a response; this case is "
            f"{state.value}."
        )

    decision = follow_up_agent.evaluate(case, observed)
    db.add(AgentDecision(id=uuid.uuid4().hex,case_id=case.id,component="follow_up",output={"outcome":observed.value,"reasoning":decision.reasoning,"state":decision.next_state.value}))
    case.follow_up_count += 1
    case.next_followup_at = None if decision.next_state.is_terminal else _follow_up_due(db)

    if decision.escalate_to is not None:
        plan = planner.plan(
            case.content, case.candidate,
            _verification_view(case),
            prior_escalation_level=decision.escalate_to.tier,
            tone=MessageTone(case.tone or "professional"),
        )
        case.recommended_action = plan.action.value
        case.action_reasoning = plan.reasoning
        case.action_factors = plan.factors
        case.draft_subject = plan.draft_subject
        case.draft_body = plan.draft_body
        case.escalation_level = max(case.escalation_level, decision.escalate_to.tier)

    if decision.next_state == state:
        case.updated_at = _now(db)
        _record_history(
            db, case.id, state, state, AgentKind.FOLLOW_UP,
            decision.headline, decision.reasoning,
        )
    else:
        _apply_transition(
            db, case, decision.next_state, AgentKind.FOLLOW_UP,
            decision.headline, decision.reasoning,
        )

    db.add(
        FollowUpEvent(
            case_id=case.id, timestamp=_now(db), observed_outcome=observed.value,
            decision=decision.headline, reasoning=decision.reasoning,
            resulting_state=case.current_state,
        )
    )
    _log_activity(
        db, AgentKind.FOLLOW_UP, decision.headline.rstrip("."),
        f"{case.id} · observed: {observed.value}", case.id,
    )
    db.commit()
    return case


def resolve_case(db: Session, case_id: str, note: str | None = None) -> Case:
    case = _require_case(db, case_id)
    case.next_followup_at = None
    _apply_transition(
        db, case, CaseState.RESOLVED, AgentKind.HUMAN, "Marked resolved",
        note or "Reviewer confirmed the case is resolved. Follow-up cancelled.",
    )
    _log_activity(
        db, AgentKind.HUMAN, "Case resolved",
        f"{case.candidate.account_handle} · {case.id}", case.id,
    )
    db.commit()
    return case


def cases_due_for_follow_up(db: Session) -> list[Case]:
    """Driven by the scheduler (cron / Celery beat) on the weekly interval."""
    return list(
        db.scalars(
            select(Case).where(
                Case.current_state.in_(
                    [CaseState.AWAITING_RESPONSE.value, CaseState.ESCALATED.value]
                ),
                Case.next_followup_at.isnot(None),
                Case.next_followup_at <= _now(db),
            )
        )
    )


# ---------------------------------------------------------------- internals


def _require_case(db: Session, case_id: str) -> Case:
    case = db.scalar(select(Case).where(Case.id==case_id).with_for_update())
    if case is None or (db.info.get("user_id") and case.content.user_id != db.info["user_id"]):
        raise ValueError(f"Case {case_id} not found")
    return case


def _verification_view(case: Case):
    """Rebuild the agent-facing verification object from persisted columns."""
    from app.agents.base import VerificationResult
    from app.models.enums import Severity

    return VerificationResult(
        classification=Classification(case.classification),
        confidence=case.confidence or 0.0,
        severity=Severity(case.severity or "low"),
        summary=case.verification_summary or "",
        signals=[],
        evidence_summary=case.evidence_summary or "",
        engine=case.verification_engine or "",
    )
