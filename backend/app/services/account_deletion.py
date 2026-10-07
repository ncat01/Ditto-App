import re, shutil
from pathlib import Path
from sqlalchemy import select, delete
from app.config import get_settings
from app.database.db import Base, SessionLocal
from app.models.tables import Content, Case
from app.models.account_security import MediaDeletion

def delete_records(db, user_id):
    from app.models.remote_media import RemoteMedia, RemoteMediaDeletion
    from app.models.jobs import ProcessingJob
    # Finish in-flight work before taking dependent record/case snapshots. A
    # worker holds its receipt row until result creation commits. Waiting later
    # in the deletion loop could miss those newly created child records.
    db.scalars(select(ProcessingJob).where(ProcessingJob.user_id == user_id)
               .order_by(ProcessingJob.id).with_for_update()).all()
    for file_id in db.scalars(select(RemoteMedia.file_id).where(RemoteMedia.user_id == user_id)):
        if not db.get(RemoteMediaDeletion, file_id):
            db.add(RemoteMediaDeletion(file_id=file_id))
    db.flush()
    contents = list(db.scalars(select(Content.id).where(Content.user_id == user_id)))
    cases = list(db.scalars(select(Case.id).where(Case.content_id.in_(contents))))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in ('users', 'media_deletions', 'request_budgets'): continue
        predicates = []
        if 'user_id' in table.c: predicates.append(table.c.user_id == user_id)
        if 'content_id' in table.c: predicates.append(table.c.content_id.in_(contents))
        if 'case_id' in table.c: predicates.append(table.c.case_id.in_(cases))
        if table.name == 'content': predicates.append(table.c.id.in_(contents))
        if table.name == 'cases': predicates.append(table.c.id.in_(cases))
        if predicates:
            from sqlalchemy import or_
            db.execute(delete(table).where(or_(*predicates)))
    db.add(MediaDeletion(user_id=user_id))
    db.execute(delete(Base.metadata.tables['users']).where(Base.metadata.tables['users'].c.id == user_id))
    db.commit()

def purge_media():
    root = Path(get_settings().media_root).resolve()
    with SessionLocal() as db:
        for row in db.scalars(select(MediaDeletion)).all():
            if not re.fullmatch(r'[a-f0-9]{32}', row.user_id): continue
            raw = root / row.user_id
            target = raw.resolve()
            if target.parent != root or raw.is_symlink(): continue
            try:
                if target.exists(): shutil.rmtree(target)
                db.delete(row); db.commit()
            except OSError:
                db.rollback()  # The durable job is retried at startup or the next purge.
    from app.models.remote_media import RemoteMediaDeletion
    from app.providers.appwrite_storage import delete_private
    from app.providers.appwrite import AppwriteUnavailable
    with SessionLocal() as db:
        for row in db.scalars(select(RemoteMediaDeletion)).all():
            from datetime import datetime, timezone
            if row.not_before.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                continue
            try:
                delete_private(row.file_id)
                db.delete(row)
                db.commit()
            except (AppwriteUnavailable, ValueError):
                db.rollback()  # Keep the job when provider access is temporarily unavailable.
