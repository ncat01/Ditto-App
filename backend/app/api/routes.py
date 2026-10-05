"""HTTP surface. Errors are mapped to precise status codes; an illegal state
transition returns 409 Conflict rather than a generic 500."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import schemas
from app.config import get_settings
from app.database.db import get_db
from app.discovery import corpus
from app.matching import hasher
from app.models.enums import CaseState, Classification
from app.models.tables import ActivityEvent, Case, Content
from app.services import case_service, seed as seed_service
from app.services.state_machine import InvalidTransition

router = APIRouter(prefix="/api")
settings = get_settings()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "video/mp4", "video/quicktime", "video/webm",
}


# ---------------------------------------------------------------- serialisation


def _case_out(case: Case) -> schemas.CaseOut:
    c = case.candidate
    return schemas.CaseOut(
        id=case.id,
        contentId=case.content_id,
        contentTitle=case.content.title if case.content else "",
        contentPaletteSeed=case.content.palette_seed if case.content else 1,
        candidate=schemas.CandidateOut(
            id=c.id, platform=c.platform, accountName=c.account_name,
            accountHandle=c.account_handle, sourceUrl=c.source_url, caption=c.caption,
            followerCount=c.follower_count, monetized=c.monetized,
            hashSimilarity=c.hash_similarity, visualSimilarity=c.visual_similarity,
            captionSimilarity=c.caption_similarity, faceSimilarity=c.face_similarity,
            postedAt=c.posted_at, transformNote=c.transform_note,
            paletteSeed=c.palette_seed, discoveredAt=c.discovered_at,
            attributionPresent=c.attribution_present, permissionGranted=c.permission_granted,
        ),
        classification=case.classification,
        confidence=case.confidence,
        severity=case.severity,
        verificationSummary=case.verification_summary,
        verificationSignals=case.verification_signals or [],
        evidenceSummary=case.evidence_summary,
        verificationEngine=case.verification_engine,
        recommendedAction=case.recommended_action,
        actionReasoning=case.action_reasoning,
        actionFactors=case.action_factors or [],
        draftSubject=case.draft_subject,
        draftBody=case.draft_body,
        tone=case.tone,
        planEngine=case.plan_engine,
        currentState=case.current_state,
        escalationLevel=case.escalation_level,
        followUpCount=case.follow_up_count,
        createdAt=case.created_at,
        updatedAt=case.updated_at,
        nextFollowUpAt=case.next_followup_at,
        lastActionAt=case.last_action_at,
        history=[
            schemas.HistoryOut(
                timestamp=h.timestamp, previousState=h.previous_state,
                newState=h.new_state, agent=h.agent, action=h.action,
                reasoning=h.reasoning,
            )
            for h in case.history
        ],
    )


# ---------------------------------------------------------------- health


@router.get("/health", response_model=schemas.HealthOut)
def health(db: Session = Depends(get_db)) -> schemas.HealthOut:
    try:
        db.execute(select(func.count()).select_from(Case))
        database = "connected"
    except Exception:
        database = "unavailable"
    return schemas.HealthOut(
        status="ok",
        demoMode=settings.demo_mode,
        database=database,
        providers=settings.provider_status(),
    )


# ---------------------------------------------------------------- content


@router.post("/content/upload", response_model=schemas.ContentOut, status_code=201)
async def upload_content(
    title: str = "Uploaded content",
    source: str = "Local upload",
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> schemas.ContentOut:
    data: bytes | None = None
    kind = "image"
    if file is not None:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '{file.content_type}'. "
                       f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
            )
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
            )
        kind = "video" if file.content_type.startswith("video") else "image"

    clean_title = schemas.IngestRequest(title=title, kind=kind).title
    try:
        item = case_service.ingest_content(db, clean_title, data, kind)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    item.user_id = db.info["user_id"]
    item.source_platform = schemas._sanitize(source)[:64] or "Local upload"
    db.commit()
    return schemas.ContentOut(
        id=item.id, title=item.title, kind=item.kind,
        perceptualHash=item.perceptual_hash, paletteSeed=item.palette_seed,
        publishedAt=item.published_at, sourcePlatform=item.source_platform,
    )


@router.get("/content", response_model=list[schemas.ContentOut])
def list_content(db: Session = Depends(get_db)) -> list[schemas.ContentOut]:
    items = db.scalars(select(Content).where(Content.user_id == db.info["user_id"]).order_by(Content.created_at.desc())).all()
    return [
        schemas.ContentOut(
            id=i.id, title=i.title, kind=i.kind, perceptualHash=i.perceptual_hash,
            paletteSeed=i.palette_seed, publishedAt=i.published_at,
            sourcePlatform=i.source_platform,
        )
        for i in items
    ]


# ---------------------------------------------------------------- scan


@router.post("/scan", response_model=list[schemas.CaseOut])
def scan(body: schemas.ScanRequest, db: Session = Depends(get_db)) -> list[schemas.CaseOut]:
    try:
        cases = case_service.scan_content(db, body.contentId)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_case_out(c) for c in cases]


# ---------------------------------------------------------------- cases


@router.get("/cases", response_model=list[schemas.CaseOut])
def list_cases(
    state: CaseState | None = None, db: Session = Depends(get_db)
) -> list[schemas.CaseOut]:
    stmt = select(Case).join(Content).where(Content.user_id == db.info["user_id"]).order_by(Case.updated_at.desc())
    if state is not None:
        stmt = stmt.where(Case.current_state == state.value)
    return [_case_out(c) for c in db.scalars(stmt).all()]


@router.get("/cases/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)) -> schemas.CaseOut:
    case = db.get(Case, case_id)
    if case is None or case.content.user_id != db.info["user_id"]:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return _case_out(case)


def _mutate(fn, *args):
    try:
        return _case_out(fn(*args))
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/approve", response_model=schemas.CaseOut)
def approve(
    case_id: str, body: schemas.ApproveRequest, db: Session = Depends(get_db)
) -> schemas.CaseOut:
    return _mutate(case_service.approve_case, db, case_id, body.editedBody, body.tone)


@router.post("/cases/{case_id}/reject", response_model=schemas.CaseOut)
def reject(
    case_id: str, body: schemas.RejectRequest, db: Session = Depends(get_db)
) -> schemas.CaseOut:
    return _mutate(case_service.reject_case, db, case_id, body.note)


@router.post("/cases/{case_id}/edit-action", response_model=schemas.CaseOut)
def edit_action(
    case_id: str, body: schemas.EditActionRequest, db: Session = Depends(get_db)
) -> schemas.CaseOut:
    return _mutate(case_service.edit_action, db, case_id, body.body, body.tone)


@router.post("/cases/{case_id}/simulate-followup", response_model=schemas.CaseOut)
def simulate_followup(
    case_id: str, body: schemas.FollowUpRequest, db: Session = Depends(get_db)
) -> schemas.CaseOut:
    return _mutate(case_service.run_follow_up, db, case_id, body.outcome)


@router.post("/cases/{case_id}/resolve", response_model=schemas.CaseOut)
def resolve(
    case_id: str, body: schemas.ResolveRequest, db: Session = Depends(get_db)
) -> schemas.CaseOut:
    return _mutate(case_service.resolve_case, db, case_id, body.note)


# ---------------------------------------------------------------- dashboard


@router.get("/dashboard/stats", response_model=schemas.StatsOut)
def stats(db: Session = Depends(get_db)) -> schemas.StatsOut:
    cases = db.scalars(select(Case).join(Content).where(Content.user_id == db.info["user_id"])).all()
    content_count = db.scalar(select(func.count()).select_from(Content).where(Content.user_id == db.info["user_id"])) or 0
    verified = [c for c in cases if c.classification]
    confidences = [c.confidence for c in verified if c.confidence is not None]
    resolved = sum(1 for c in cases if c.current_state == CaseState.RESOLVED.value)
    closed = sum(1 for c in cases if c.current_state == CaseState.CLOSED.value)

    return schemas.StatsOut(
        contentMonitored=content_count,
        openCases=sum(1 for c in cases if CaseState(c.current_state).is_open),
        awaitingResponse=sum(
            1 for c in cases
            if c.current_state in (CaseState.AWAITING_RESPONSE.value, CaseState.SENT.value)
        ),
        resolved=resolved,
        escalated=sum(1 for c in cases if c.current_state == CaseState.ESCALATED.value),
        pendingApproval=sum(
            1 for c in cases if c.current_state == CaseState.PENDING_APPROVAL.value
        ),
        totalCases=len(cases),
        verifiedReposts=sum(
            1 for c in verified if c.classification == Classification.GENUINE_REPOST.value
        ),
        falsePositives=sum(
            1 for c in verified if c.classification == Classification.FALSE_POSITIVE.value
        ),
        averageConfidence=(sum(confidences) / len(confidences)) if confidences else 0.0,
        resolutionRate=((resolved + closed) / len(cases)) if cases else 0.0,
    )


@router.get("/activity", response_model=list[schemas.ActivityOut])
def activity(limit: int = 100, db: Session = Depends(get_db)) -> list[schemas.ActivityOut]:
    limit = max(1, min(limit, 500))
    events = db.scalars(
        select(ActivityEvent).where(ActivityEvent.user_id == db.info["user_id"]).order_by(ActivityEvent.timestamp.desc()).limit(limit)
    ).all()
    return [
        schemas.ActivityOut(
            id=e.id, timestamp=e.timestamp, agent=e.agent, title=e.title,
            detail=e.detail, caseId=e.case_id,
        )
        for e in events
    ]


# ---------------------------------------------------------------- demo control


@router.post("/demo/seed")
def seed_demo(force: bool = False, db: Session = Depends(get_db)) -> dict:
    created = seed_service.seed(db, force=force)
    return {"casesCreated": created, "corpus": corpus.DISPLAY_NAME}


@router.get("/demo/ground-truth")
def ground_truth() -> dict:
    """Labelled ground truth for the evaluation harness (report §9)."""
    return {
        "matcher": hasher.DISPLAY_NAME,
        "corpus": corpus.DISPLAY_NAME,
        "labels": {c.id: c.ground_truth for c in corpus.CANDIDATES},
    }

@router.get("/content/{content_id}/media")
def media(content_id: str, db: Session = Depends(get_db)):
    from pathlib import Path
    from fastapi.responses import FileResponse
    item=db.get(Content,content_id)
    if not item or item.user_id!=db.info["user_id"] or not item.local_uri:
        raise HTTPException(404,"Media unavailable")
    path=Path(item.local_uri).resolve()
    roots=[Path(settings.media_root),Path(__file__).resolve().parents[3]/"demo_data/videos"]
    if not any(path.is_relative_to(root.resolve()) for root in roots) or not path.is_file():
        raise HTTPException(404,"Media unavailable")
    return FileResponse(path,media_type="video/mp4" if item.kind=="video" else "application/octet-stream")

@router.get("/cases/{case_id}/candidate-media")
def candidate_media(case_id: str, db: Session = Depends(get_db)):
    """Only the matching generated asset, after checking this case's owner."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    case=db.get(Case,case_id)
    if not case or case.content.user_id!=db.info["user_id"]:
        raise HTTPException(404,"Case unavailable")
    key=case.candidate.id.split(":")[-1]
    kinds={"cand_001":"crop","cand_002":"caption","cand_003":"unrelated","cand_004":"resize","cand_005":"fake_endorsement","cand_006":"watermark","cand_007":"credited","cand_008":"authorized","cand_009":"ambiguous"}
    if key not in kinds: raise HTTPException(404,"Candidate media unavailable")
    path=Path(__file__).resolve().parents[3]/"demo_data/videos"/f"{case.candidate.palette_seed}_{kinds[key]}.mp4"
    if not path.is_file():raise HTTPException(404,"Candidate media unavailable")
    return FileResponse(path,media_type="video/mp4")

@router.post("/demo/advance-clock")
def advance_clock(days: int = 7, db: Session = Depends(get_db)):
    if not settings.demo_mode: raise HTTPException(409,"Demo clock unavailable outside demo mode")
    if not 1<=days<=365: raise HTTPException(422,"Days must be between 1 and 365")
    from app.services.scheduler import advance,now
    count=advance(db,days)
    return {"demoTime":now(db),"casesChecked":count,"adapter":"sandbox"}

@router.get("/content/{content_id}/scans")
def scan_history(content_id: str, db: Session = Depends(get_db)):
    from app.models.ledger import ScanJob
    item=db.get(Content,content_id)
    if not item or item.user_id!=db.info["user_id"]:raise HTTPException(404,"Original unavailable")
    jobs=db.scalars(select(ScanJob).where(ScanJob.content_id==content_id).order_by(ScanJob.created_at.desc())).all()
    return [{"id":j.id,"stage":j.stage,"stages":j.stages,"candidates":j.candidates,"createdAt":j.created_at,"finishedAt":j.finished_at} for j in jobs]

@router.get("/notifications")
def notifications(db: Session = Depends(get_db)):
    from app.models.ledger import Notification
    rows=db.scalars(select(Notification).where(Notification.user_id==db.info["user_id"]).order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id":n.id,"caseId":n.case_id,"title":n.title,"read":n.read,"createdAt":n.created_at} for n in rows]

@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: Session = Depends(get_db)):
    from app.models.ledger import Notification
    n=db.get(Notification,notification_id)
    if not n or n.user_id!=db.info["user_id"]:raise HTTPException(404,"Notification unavailable")
    n.read=True;db.commit();return {"read":True}

@router.post("/cases/{case_id}/ai-draft")
def ai_draft(case_id: str, db: Session = Depends(get_db)):
    """Explicit Gemini preview; the existing approval and edit flow remains authoritative."""
    from app.providers.gemini import generate_draft, ProviderUnavailable
    case = db.get(Case, case_id)
    if not case or case.content.user_id != db.info['user_id']:
        raise HTTPException(404, 'Case unavailable')
    if case.current_state not in ('pending_approval', 'escalated') or case.recommended_action == 'log_only':
        raise HTTPException(409, 'Only a pending action can have an AI draft')
    context = {'title': case.content.title[:200], 'recipient': case.candidate.account_handle[:128],
        'action': case.recommended_action, 'tone': case.tone,
        'existing_draft': (case.draft_body or '')[:4000], 'sandbox': True}
    # Release the read transaction during the provider network call. No case data is mutated.
    db.rollback()
    try:
        draft = generate_draft(context)
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    return {**draft.model_dump(), 'engine': 'Gemini draft preview', 'requiresApproval': True,
        'saved': False, 'sent': False}
