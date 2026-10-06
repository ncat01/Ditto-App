from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.db import Base

class AccountToken(Base):
    __tablename__ = 'account_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class AccountVerification(Base):
    __tablename__ = 'account_verifications'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime)

class RequestBudget(Base):
    __tablename__ = 'request_budgets'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer)

class MediaDeletion(Base):
    __tablename__ = 'media_deletions'
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)

class WebSearchRecord(Base):
    __tablename__ = 'web_search_records'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    content_id: Mapped[str] = mapped_column(ForeignKey('content.id'), index=True)
    results: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
