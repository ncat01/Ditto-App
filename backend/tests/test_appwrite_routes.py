import io
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.api.routes import settings
from app.database.db import SessionLocal
from app.models.remote_media import RemoteMedia, RemoteMediaDeletion
from app.models.tables import Content
from app.providers.appwrite import AppwriteUnavailable
from types import SimpleNamespace
import secrets


def image():
    buffer = io.BytesIO()
    Image.new('RGB', (32, 32), '#ffcccc').save(buffer, 'JPEG')
    return buffer.getvalue()


def test_remote_upload_playback_and_account_deletion_are_owner_scoped():
    with TestClient(app) as client:
        owner = client.post('/api/auth/signup', json={'email':'remote-owner@example.test','password':'secure-password-123'}).json()
        other = client.post('/api/auth/signup', json={'email':'remote-other@example.test','password':'secure-password-123'}).json()
        client.headers['Authorization'] = 'Bearer ' + owner['token']
        with patch.object(settings, 'media_storage', 'appwrite'), patch('app.providers.appwrite_storage.upload_private') as upload:
            response = client.post('/api/content/upload', files={'file':('photo.jpg', image(), 'image/jpeg')})
        assert response.status_code == 201, response.text
        content_id = response.json()['id']
        upload.assert_called_once()
        with SessionLocal() as db:
            remote = db.get(RemoteMedia, content_id)
            assert remote.user_id == owner['user']['id']
            file_id = remote.file_id
            assert db.get(RemoteMediaDeletion, file_id) is None
        with patch('app.providers.appwrite_storage.download_private', return_value=image()) as download:
            assert client.get(f'/api/content/{content_id}/media').status_code == 200
            download.assert_called_once_with(file_id)
            client.headers['Authorization'] = 'Bearer ' + other['token']
            assert client.get(f'/api/content/{content_id}/media').status_code == 404
            assert download.call_count == 1
        client.headers['Authorization'] = 'Bearer ' + owner['token']
        with patch('app.providers.appwrite_storage.delete_private', side_effect=AppwriteUnavailable('offline')):
            assert client.post('/api/auth/delete-account', json={'password':'secure-password-123'}).status_code == 200
        with SessionLocal() as db:
            assert db.get(RemoteMedia, content_id) is None
            assert db.get(RemoteMediaDeletion, file_id) is not None


def test_remote_failure_rolls_back_original_and_keeps_cleanup_job():
    with TestClient(app) as client:
        account = client.post('/api/auth/signup', json={'email':'remote-failure@example.test','password':'secure-password-123'}).json()
        client.headers['Authorization'] = 'Bearer ' + account['token']
        with patch.object(settings, 'media_storage', 'appwrite'), patch('app.providers.appwrite_storage.upload_private', side_effect=AppwriteUnavailable('offline')):
            response = client.post('/api/content/upload', files={'file':('photo.jpg', image(), 'image/jpeg')})
        assert response.status_code == 503
        with SessionLocal() as db:
            assert db.scalar(select(Content).where(Content.user_id == account['user']['id'])) is None
            assert db.scalar(select(RemoteMediaDeletion)) is not None


def test_instagram_import_uses_private_remote_storage_and_is_idempotent():
    post = SimpleNamespace(id='987654', caption='An original video', timestamp='2026-10-06T10:00:00Z')
    reader = SimpleNamespace(media=lambda *args: [post], media_item=lambda *args: post,
                             download_video=lambda *args: b'test-video')
    with TestClient(app) as client:
        account = client.post('/api/auth/signup', json={
            'email': secrets.token_hex(8) + '@example.test', 'password': 'secure-password-123'}).json()
        client.headers['Authorization'] = 'Bearer ' + account['token']
        with patch.object(settings, 'media_storage', 'appwrite'), \
             patch('app.services.instagram_oauth.connected_reader', return_value=(reader, '123')), \
             patch('app.matching.video.frames', return_value=['0123456789abcdef'] * 5), \
             patch('app.providers.appwrite_storage.upload_private') as upload:
            result = client.post('/api/integrations/instagram/import/987654')
            assert result.status_code == 200, result.text
            repeated = client.post('/api/integrations/instagram/import/987654')
            assert repeated.json()['id'] == result.json()['id']
            upload.assert_called_once()
        with SessionLocal() as db:
            remote = db.get(RemoteMedia, result.json()['id'])
            assert remote.user_id == account['user']['id']
            assert db.get(RemoteMediaDeletion, remote.file_id) is None
            assert db.get(Content, remote.content_id).source_platform == 'Instagram:987654'


def test_instagram_remote_failure_does_not_leave_a_saved_original():
    post = SimpleNamespace(id='987655', caption='A video', timestamp='2026-10-06T10:00:00Z')
    reader = SimpleNamespace(media=lambda *args: [post], media_item=lambda *args: post,
                             download_video=lambda *args: b'test-video')
    with TestClient(app) as client:
        account = client.post('/api/auth/signup', json={
            'email': secrets.token_hex(8) + '@example.test', 'password': 'secure-password-123'}).json()
        client.headers['Authorization'] = 'Bearer ' + account['token']
        with patch.object(settings, 'media_storage', 'appwrite'), \
             patch('app.services.instagram_oauth.connected_reader', return_value=(reader, '123')), \
             patch('app.matching.video.frames', return_value=['0123456789abcdef'] * 5), \
             patch('app.providers.appwrite_storage.upload_private', side_effect=AppwriteUnavailable('offline')):
            response = client.post('/api/integrations/instagram/import/987655')
            assert response.status_code == 503
        with SessionLocal() as db:
            assert db.scalar(select(Content).where(Content.user_id == account['user']['id'])) is None
