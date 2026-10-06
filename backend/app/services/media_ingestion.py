"""Persist uploads and Instagram imports through the same private storage path."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from app.config import get_settings
from app.database.db import SessionLocal
from app.models.remote_media import RemoteMedia, RemoteMediaDeletion
from app.services import case_service


def persist_original(db, title, data, kind, source, *, extension=None, published_at=None):
    settings = get_settings()
    remote_id = None
    if settings.media_storage == 'appwrite':
        if not data or extension not in {'jpg', 'png', 'webp', 'mp4', 'mov'}:
            raise ValueError('A supported media file is required for Appwrite storage.')
        if len(data) > 20_000_000:
            raise ValueError('Appwrite originals are limited to 20 MB.')
        remote_id = uuid.uuid4().hex
        # This reservation survives an upload failure or interrupted process.
        with SessionLocal() as cleanup_db:
            cleanup_db.add(RemoteMediaDeletion(file_id=remote_id,
                not_before=datetime.now(timezone.utc) + timedelta(minutes=10)))
            cleanup_db.commit()
    item = None
    try:
        item = case_service.ingest_content(db, title, data, kind, commit=False)
        if remote_id:
            from app.providers.appwrite_storage import upload_private
            upload_private(Path(item.local_uri), remote_id, remote_id + '.' + extension)
            db.add(RemoteMedia(content_id=item.id, user_id=db.info['user_id'], file_id=remote_id))
            pending = db.get(RemoteMediaDeletion, remote_id)
            if pending:
                db.delete(pending)
        item.source_platform = source[:64]
        if published_at is not None:
            item.published_at = published_at
        db.commit()
        return item
    except Exception:
        db.rollback()
        if item and item.local_uri:
            Path(item.local_uri).unlink(missing_ok=True)
        raise
