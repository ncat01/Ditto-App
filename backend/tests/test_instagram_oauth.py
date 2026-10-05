import secrets
from urllib.parse import urlsplit,parse_qs
from datetime import timedelta
from types import SimpleNamespace
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings
from app.api import instagram_oauth as api
from app.services import instagram_oauth as service
from app.models.integrations import InstagramConnection
from app.database.db import SessionLocal

def configure(monkeypatch):
    settings=Settings(instagram_app_secret='test-secret',public_base_url='https://ditto.example',token_encryption_key=Fernet.generate_key().decode())
    monkeypatch.setattr(service,'get_settings',lambda:settings);monkeypatch.setattr(api,'get_settings',lambda:settings)
    return settings

def signup(c):
    r=c.post('/api/auth/signup',json={'email':secrets.token_hex(8)+'@example.test','password':'secure-demo-123'}).json()
    return r['user']['id'],{'Authorization':'Bearer '+r['token']}

def begin(c,a):
    r=c.post('/api/integrations/instagram/connect',headers=a);assert r.status_code==200,r.text
    r=c.get(r.json()['authorizationUrl'],follow_redirects=False);assert r.status_code==302
    query=parse_qs(urlsplit(r.headers['location']).query)
    assert query['scope']==['instagram_business_basic']
    assert 'test-secret' not in r.headers['location']
    assert 'HttpOnly' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    return query['state'][0]

def test_encryption_isolation_replay_disconnect(monkeypatch):
    settings=configure(monkeypatch)
    monkeypatch.setattr(api,'exchange_code',lambda code:('private-token',service.now()+timedelta(days=60),SimpleNamespace(user_id='987654321',username='my_creator')))
    with TestClient(app,base_url='https://ditto.example') as c:
        uid,a=signup(c);_,b=signup(c)
        assert c.post('/api/integrations/instagram/connect').status_code==401
        state=begin(c,a)
        r=c.get('/api/integrations/instagram/callback',params={'state':state,'code':'code'})
        assert r.status_code==200,r.text
        assert 'private-token' not in r.text
        assert c.get('/api/integrations/instagram/callback',params={'state':state,'code':'code'}).status_code==400
        status=c.get('/api/integrations/instagram/status',headers=a).json()
        assert status['connected'] and status['username']=='my_creator'
        assert not c.get('/api/integrations/instagram/status',headers=b).json()['connected']
        with SessionLocal() as db:
            encrypted=db.get(InstagramConnection,uid).encrypted_token
            assert 'private-token' not in encrypted
            assert Fernet(settings.token_encryption_key.get_secret_value()).decrypt(encrypted.encode())==b'private-token'
        state=begin(c,b)
        assert c.get('/api/integrations/instagram/callback',params={'state':state,'code':'code'}).status_code==409
        assert c.post('/api/integrations/instagram/disconnect',headers=a).status_code==200
        assert not c.get('/api/integrations/instagram/status',headers=a).json()['connected']

def test_cookie_denial_logout(monkeypatch):
    configure(monkeypatch)
    with TestClient(app,base_url='https://ditto.example') as c:
        _,a=signup(c);state=begin(c,a);c.cookies.clear()
        assert c.get('/api/integrations/instagram/callback',params={'state':state,'code':'code'}).status_code==400
        state=begin(c,a)
        assert c.get('/api/integrations/instagram/callback',params={'state':state,'error':'access_denied'}).status_code==200
        assert not c.get('/api/integrations/instagram/status',headers=a).json()['connected']
        state=begin(c,a);c.post('/api/auth/logout',headers=a)
        assert c.get('/api/integrations/instagram/callback',params={'state':state,'code':'code'}).status_code==400

def test_missing_configuration(monkeypatch):
    monkeypatch.setattr(service,'get_settings',lambda:Settings(instagram_app_secret=''))
    with TestClient(app) as c:
        _,a=signup(c)
        assert c.post('/api/integrations/instagram/connect',headers=a).status_code==503
