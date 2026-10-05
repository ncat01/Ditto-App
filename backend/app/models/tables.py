"""Persistence model. Mirrors the Android Room schema one-for-one."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Content(Base):
    __tablename__ = "content"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(16))
    local_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    perceptual_hash: Mapped[str] = mapped_column(Text)
    palette_seed: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    source_platform: Mapped[str] = mapped_column(String(64), default="Local upload")

    cases: Mapped[list["Case"]] = relationship(back_populates="content")


class CandidateMatch(Base):
    __tablename__ = "candidate_matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_id: Mapped[str] = mapped_column(ForeignKey("content.id"))
    platform: Mapped[str] = mapped_column(String(64))
    account_name: Mapped[str] = mapped_column(String(128))
    account_handle: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(Text)
    caption: Mapped[str] = mapped_column(Text, default="")
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    monetized: Mapped[bool] = mapped_column(Boolean, default=False)
    hash_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    visual_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    caption_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    attribution_present: Mapped[bool] = mapped_column(Boolean,default=False)
    permission_granted: Mapped[bool] = mapped_column(Boolean,default=False)
    face_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    transform_note: Mapped[str] = mapped_column(Text, default="")
    palette_seed: Mapped[int] = mapped_column(Integer, default=1)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(ForeignKey("content.id"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidate_matches.id"))

    # verification
    classification: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_signals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_engine: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # action plan
    recommended_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    draft_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    plan_engine: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # lifecycle
    current_state: Mapped[str] = mapped_column(String(32), default="new")
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    content: Mapped[Content] = relationship(back_populates="cases")
    candidate: Mapped[CandidateMatch] = relationship()
    history: Mapped[list["CaseHistory"]] = relationship(
        back_populates="case", order_by="CaseHistory.timestamp"
    )


class CaseHistory(Base):
    __tablename__ = "case_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    agent: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(256))
    reasoning: Mapped[str] = mapped_column(Text, default="")

    case: Mapped[Case] = relationship(back_populates="history")


class ActivityEvent(Base):
    __tablename__ = "activity"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"),nullable=True,index=True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    agent: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(256))
    detail: Mapped[str] = mapped_column(Text, default="")
    case_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ActionDraft(Base):
    """Sandboxed outreach record. In Demo Mode `transmitted` is always False."""

    __tablename__ = "action_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    action: Mapped[str] = mapped_column(String(32))
    tone: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    transmitted: Mapped[bool] = mapped_column(Boolean, default=False)
    transport_note: Mapped[str] = mapped_column(Text, default="")


class FollowUpEvent(Base):
    __tablename__ = "followup_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    observed_outcome: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(256))
    reasoning: Mapped[str] = mapped_column(Text, default="")
    resulting_state: Mapped[str] = mapped_column(String(32))

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class DispatchAttempt(Base):
    __tablename__ = "dispatch_attempts"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    recipient: Mapped[str] = mapped_column(String(128))
    channel: Mapped[str] = mapped_column(String(32), default="sandbox")
    body: Mapped[str] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)

class DemoClock(Base):
    __tablename__ = "demo_clocks"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"),primary_key=True)
    offset_days: Mapped[int] = mapped_column(Integer,default=0)
