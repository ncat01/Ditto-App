from __future__ import annotations

import uuid

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from sqlalchemy.orm import Session

from app.config import get_settings

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

def _now(db) -> datetime:
    from app.services.scheduler import now
    return now(db)

def _follow_up_due(db) -> datetime:
    return _now(db) + timedelta(days=settings.follow_up_interval_days)

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
        raise ValueError("A real media file is required; fingerprint unavailable")

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
        db, AgentKind.INGESTION, "Original prepared",
        f"{item.title} is ready for visual matching.",
    )
    if commit:
        db.commit()
    return item

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

def _require_case(db: Session, case_id: str) -> Case:
    case = db.scalar(select(Case).where(Case.id==case_id).with_for_update())
    if case is None or (db.info.get("user_id") and case.content.user_id != db.info["user_id"]):
        raise ValueError(f"Case {case_id} not found")
    return case


def approve_case(db, case_id, edited_body=None, tone=None):
    _require_case(db, case_id)
    raise InvalidTransition("Use exact recipient/message approval through a configured delivery provider. No message was sent.")
