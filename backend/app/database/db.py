"""SQLAlchemy setup. SQLite by default for zero-setup demos; the models use no
SQLite-specific types, so pointing DITTO_DATABASE_URL at PostgreSQL is the only
change needed for a production deployment (report §5)."""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

_connect_args = (
    {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}
)
database_url = settings.database_url
if database_url.startswith(('postgres://', 'postgresql://')):
    database_url = 'postgresql+psycopg://' + database_url.split('://', 1)[1]
engine = create_engine(database_url, connect_args=_connect_args, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    db = SessionLocal()
    try:
        if request.url.path != "/api/health":
            from app.api.auth import current_user
            db.info["user_id"] = current_user(request)
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import tables  # noqa: F401  (registers the mappers)

    from app.models import ledger, integrations, account_security, remote_media, refresh_tokens, jobs
    Base.metadata.create_all(bind=engine)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
