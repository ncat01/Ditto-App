"""Remote file ownership and durable cleanup, independent of provider credentials."""
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database.db import Base


class RemoteMedia(Base):
    __tablename__ = 'remote_media'
    content_id: Mapped[str] = mapped_column(ForeignKey('content.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    file_id: Mapped[str] = mapped_column(String(36), unique=True)


class RemoteMediaDeletion(Base):
    # No foreign key: cleanup must survive removal of the account and original.
    __tablename__ = 'remote_media_deletions'
    file_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    not_before: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
