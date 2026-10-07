import hashlib
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database.db import SessionLocal
from app.models.tables import User


def credentials():
    return {'email': uuid.uuid4().hex + '@auth-test.invalid', 'password': 'reviewed-test-password'}


def test_refresh_rotates_and_reuse_revokes_the_entire_family():
    with TestClient(app) as client:
        signed = client.post('/api/auth/signup', json=credentials()).json()
        old_access = {'Authorization': 'Bearer ' + signed['token']}
        rotated = client.post('/api/auth/refresh', json={'refreshToken': signed['refreshToken']})
        assert rotated.status_code == 200
        new = rotated.json()
        assert new['refreshToken'] != signed['refreshToken']
        assert client.get('/api/auth/me', headers=old_access).status_code == 401
        assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + new['token']}).status_code == 200
        assert client.post('/api/auth/refresh', json={'refreshToken': signed['refreshToken']}).status_code == 401
        assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + new['token']}).status_code == 401
        assert client.post('/api/auth/refresh', json={'refreshToken': new['refreshToken']}).status_code == 401


def test_logout_revokes_refresh_and_new_passwords_are_argon2():
    with TestClient(app) as client:
        signed = client.post('/api/auth/signup', json=credentials()).json()
        lifetime = datetime.fromisoformat(signed['expiresAt'].replace('Z', '+00:00')) - datetime.now(timezone.utc)
        assert 0 < lifetime.total_seconds() <= 900
        with SessionLocal() as db:
            assert db.get(User, signed['user']['id']).password_hash.startswith('$argon2id$')
        assert client.post('/api/auth/logout', headers={'Authorization': 'Bearer ' + signed['token']}).status_code == 200
        assert client.post('/api/auth/refresh', json={'refreshToken': signed['refreshToken']}).status_code == 401


def test_existing_pbkdf2_accounts_upgrade_only_after_correct_password():
    details = credentials()
    with TestClient(app) as client:
        signed = client.post('/api/auth/signup', json=details).json()
        salt = 'ab' * 32
        legacy = hashlib.pbkdf2_hmac('sha256', details['password'].encode(), bytes.fromhex(salt), 210000).hex()
        with SessionLocal() as db:
            user = db.get(User, signed['user']['id'])
            user.salt, user.password_hash = salt, legacy
            db.commit()
        assert client.post('/api/auth/login', json={**details, 'password': 'incorrect-password'}).status_code == 401
        with SessionLocal() as db:
            assert db.get(User, signed['user']['id']).password_hash == legacy
        assert client.post('/api/auth/login', json=details).status_code == 200
        with SessionLocal() as db:
            assert db.get(User, signed['user']['id']).password_hash.startswith('$argon2id$')
