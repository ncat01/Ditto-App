"""Seeds the demo corpus and drives the seeded cases into varied lifecycle states
through the real state machine (never by writing states directly)."""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.discovery import corpus
from app.models.enums import FollowUpOutcome
from app.models.tables import (
    ActionDraft,
    ActivityEvent,
    CandidateMatch,
    Case,
    CaseHistory,
    Content,
    FollowUpEvent,
)
from app.services import case_service


def seed(db: Session, force: bool = False) -> int:
    user = db.info.get("user_id")
    existing = db.scalar(select(func.count()).select_from(Case).join(Content).where(Content.user_id == user)) or 0
    if existing and not force:
        return 0

    if force:
        raise ValueError("Server demo reset is disabled to preserve account audit records. Create a new demo account.")

    from pathlib import Path
    from app.matching.video import frames
    videos = Path(__file__).resolve().parents[3] / "demo_data/videos"
    for item in corpus.CONTENT:
        db.add(
            Content(
                id=f"{user}:{item.id}", user_id=user, title=item.title, kind=item.kind,
                local_uri=str(videos/f"original_{item.palette_seed}.mp4"),
                perceptual_hash="|".join(frames(videos/f"original_{item.palette_seed}.mp4")), palette_seed=item.palette_seed,
                published_at=corpus.content_published_at(item),
                created_at=corpus.content_published_at(item),
                source_platform="Generated demo asset",
            )
        )
    db.commit()

    created = 0
    for item in corpus.CONTENT:
        for case in case_service.scan_content(db, f"{user}:{item.id}"):
            created += 1
            # Advance seeded cases through the real lifecycle so the demo opens
            # with a realistic spread of states.
            cid = case.candidate_id.split(":")[-1]
            if cid == "cand_002":
                case_service.approve_case(db, case.id)
                case_service.run_follow_up(db, case.id, FollowUpOutcome.NO_RESPONSE)
            elif cid == "cand_004":
                case_service.approve_case(db, case.id)
                case_service.run_follow_up(db, case.id, FollowUpOutcome.ATTRIBUTION_ADDED)
            elif cid == "cand_006":
                case_service.approve_case(db, case.id)
    return created
