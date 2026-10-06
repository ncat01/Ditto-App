import secrets, hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.api import auth
from app.services import account_email, account_deletion
from app.database.db import SessionLocal
from app.models.tables import User, Content
from app.models.account_security import AccountToken, AccountVerification

PASSWORD = 'original-password-123'

def signup(client):
    email = secrets.token_hex(10) + '@example.test'
    data = client.post('/api/auth/signup', json={'email':email,'password':PASSWORD}).json()
    return email, data['user']['id'], {'Authorization':'Bearer '+data['token']}

def email_capture(monkeypatch):
    sent = []
    monkeypatch.setattr(account_email, 'require_email', lambda: None)
    monkeypatch.setattr(account_email, 'send_account_email', lambda email, purpose, token: sent.append((email,purpose,token)))
    return sent

def test_reset_revokes_sessions_and_consumes_token(monkeypatch):
    sent = email_capture(monkeypatch)
    with TestClient(app) as client:
        email, uid, headers = signup(client)
        assert client.post('/api/auth/recovery',json={'email':email}).status_code == 200
        token = sent[-1][2]
        with SessionLocal() as db:
            assert db.get(AccountToken, hashlib.sha256(token.encode()).hexdigest()).user_id == uid
            assert db.get(AccountToken, token) is None
        body = {'token':token,'password':'new-password-456'}
        assert client.post('/api/auth/reset-password',json=body).status_code == 200
        assert client.get('/api/auth/me',headers=headers).status_code == 401
        assert client.post('/api/auth/reset-password',json=body).status_code == 400
        assert client.post('/api/auth/login',json={'email':email,'password':PASSWORD}).status_code == 401
        assert client.post('/api/auth/login',json={'email':email,'password':body['password']}).status_code == 200
        unknown = client.post('/api/auth/recovery',json={'email':'missing-'+secrets.token_hex(8)+'@example.test'})
        assert unknown.status_code == 200
        assert 'If the account exists' in unknown.json()['message']

def test_verification_expiry_and_one_time_use(monkeypatch):
    sent = email_capture(monkeypatch)
    with TestClient(app) as client:
        email, uid, headers = signup(client)
        assert client.post('/api/auth/request-verification',headers=headers).status_code == 200
        token = sent[-1][2]
        body = {'token':token}
        assert client.post('/api/auth/verify-email',json=body).status_code == 200
        assert client.post('/api/auth/verify-email',json=body).status_code == 400
        with SessionLocal() as db: assert db.get(AccountVerification, uid)
        assert client.post('/api/auth/recovery',json={'email':email}).status_code == 200
        token = sent[-1][2]
        with SessionLocal() as db:
            row = db.get(AccountToken,hashlib.sha256(token.encode()).hexdigest())
            row.expires_at = datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=1); db.commit()
        assert client.post('/api/auth/reset-password',json={'token':token,'password':PASSWORD}).status_code == 400

def test_delete_is_scoped_and_media_is_removed(monkeypatch,tmp_path):
    monkeypatch.setattr(account_deletion,'get_settings',lambda:SimpleNamespace(media_root=str(tmp_path)))
    with TestClient(app) as client:
        email, uid, headers = signup(client)
        _, other, other_headers = signup(client)
        assert client.post('/api/demo/seed',headers=headers).status_code == 200
        folder=tmp_path/uid; folder.mkdir(); (folder/'private.mp4').write_bytes(b'private')
        other_folder=tmp_path/other;other_folder.mkdir();(other_folder/'private.mp4').write_bytes(b'other')
        assert client.post('/api/auth/delete-account',headers=headers,json={'password':'wrong-password'}).status_code == 401
        assert folder.exists()
        assert client.post('/api/auth/delete-account',headers=headers,json={'password':PASSWORD}).status_code == 200
        assert not folder.exists() and other_folder.exists()
        assert client.get('/api/auth/me',headers=headers).status_code == 401
        assert client.get('/api/auth/me',headers=other_headers).status_code == 200
        with SessionLocal() as db:
            assert db.get(User,uid) is None
            assert not db.query(Content).filter(Content.user_id==uid).count()

def test_login_budget_and_safe_account_pages():
    with TestClient(app) as client:
        email, _, _ = signup(client)
        for _ in range(10): assert client.post('/api/auth/login',json={'email':email,'password':'wrong-password'}).status_code == 401
        result = client.post('/api/auth/login',json={'email':email,'password':'wrong-password'})
        assert result.status_code == 429 and result.headers['Retry-After']
        page=client.get('/account/reset-password')
        assert page.status_code == 200 and page.headers['Cache-Control']=='no-store'
        assert "frame-ancestors 'none'" in page.headers['Content-Security-Policy']
        assert 'history.replaceState' in page.text
        assert client.get('/account/unknown').status_code == 404
