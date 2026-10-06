from unittest.mock import patch
from app.database.db import SessionLocal, init_db
from app.models.remote_media import RemoteMediaDeletion
from app.services.account_deletion import purge_media
from app.providers.appwrite import AppwriteUnavailable


def test_remote_deletion_survives_provider_failure_then_retries():
    init_db()
    file_id = 'cleanup-test-original'
    with SessionLocal() as db:
        db.add(RemoteMediaDeletion(file_id=file_id))
        db.commit()
    with patch('app.providers.appwrite_storage.delete_private', side_effect=AppwriteUnavailable('Temporarily unavailable')):
        purge_media()
    with SessionLocal() as db:
        assert db.get(RemoteMediaDeletion, file_id) is not None
    with patch('app.providers.appwrite_storage.delete_private') as remove:
        purge_media()
        remove.assert_any_call(file_id)
    with SessionLocal() as db:
        assert db.get(RemoteMediaDeletion, file_id) is None
