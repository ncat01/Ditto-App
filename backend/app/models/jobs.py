from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.db import Base


class ProcessingJob(Base):
    __tablename__ = 'processing_jobs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    state: Mapped[str] = mapped_column(String(16), default='queued', index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CandidateMedia(Base):
    __tablename__ = 'candidate_media'
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    path: Mapped[str] = mapped_column(String(1024))
