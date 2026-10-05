"""Durable, per-account Instagram authorizations and one-time browser handoffs."""
from datetime import datetime
from sqlalchemy import String,Text,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from app.database.db import Base

class InstagramConnection(Base):
    __tablename__='instagram_connections'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    instagram_user_id: Mapped[str]=mapped_column(String(64),unique=True)
    username: Mapped[str]=mapped_column(String(128))
    encrypted_token: Mapped[str]=mapped_column(Text)
    expires_at: Mapped[datetime]=mapped_column(DateTime)
    refreshed_at: Mapped[datetime]=mapped_column(DateTime)

class InstagramOAuthAttempt(Base):
    __tablename__='instagram_oauth_attempts'
    state_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    session_hash: Mapped[str]=mapped_column(String(64))
    cookie_hash: Mapped[str|None]=mapped_column(String(64),nullable=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime)
