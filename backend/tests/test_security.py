import os
import tempfile
os.environ['DITTO_DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
from fastapi.testclient import TestClient
from app.main import app

def test_accounts_isolation_sessions_and_pipeline(monkeypatch):
    with TestClient(app) as client:
        def signup(email):
            response=client.post('/api/auth/signup',json={'email':email,'password':'secure-demo-123'})
            assert response.status_code==201,response.text
            return {'Authorization':'Bearer '+response.json()['token']}
        a=signup('alpha@example.test');b=signup('beta@example.test')
        assert client.get('/api/cases').status_code==401
        assert client.post('/api/demo/seed',headers=a).status_code==200
        cases=client.get('/api/cases',headers=a).json()
        assert cases
        assert client.get('/api/cases',headers=b).json()==[]
        notices=client.get('/api/notifications',headers=a).json()
        assert notices
        assert client.get('/api/notifications',headers=b).json()==[]
        assert client.post('/api/notifications/'+notices[0]['id']+'/read',headers=b).status_code==404
        original=cases[0]['contentId']
        assert client.get('/api/content/'+original+'/scans',headers=b).status_code==404
        assert client.get('/api/content/'+original+'/scans',headers=a).json()[0]['stage']=='complete'
        cid=cases[0]['id']
        assert client.get('/api/cases/'+cid,headers=b).status_code==404
        assert client.get('/api/cases/'+cid+'/candidate-media',headers=b).status_code==404
        assert client.get('/api/cases/'+cid+'/candidate-media',headers=a).status_code==200
        credited=next(c for c in cases if c['candidate']['id'].endswith('cand_007'))
        assert credited['candidate']['attributionPresent'] is True
        authorized=next(c for c in cases if c['candidate']['id'].endswith('cand_008'))
        assert authorized['candidate']['permissionGranted'] is True
        assert client.post('/api/cases/'+cid+'/approve',headers=b,json={}).status_code==404
        pending=next(c for c in cases if c['currentState']=='pending_approval')
        cid=pending['id']
        from app.providers import gemini
        def preview(context):
            return gemini.Draft(subject='Sample subject',body='Sample preview')
        monkeypatch.setattr(gemini,'generate_draft',preview)
        assert client.post('/api/cases/'+cid+'/ai-draft',headers=b).status_code==404
        draft=client.post('/api/cases/'+cid+'/ai-draft',headers=a)
        assert draft.status_code==200
        assert draft.json()['saved'] is False and draft.json()['sent'] is False
        assert client.get('/api/cases/'+cid,headers=a).json()['draftBody']==pending['draftBody']
        assert client.post('/api/cases/'+cid+'/approve',headers=a,json={}).status_code==200
        assert client.post('/api/cases/'+cid+'/ai-draft',headers=a).status_code==409
        assert client.post('/api/cases/'+cid+'/approve',headers=a,json={}).status_code==409
        from app.services import instagram_binding
        from app.providers import instagram
        from types import SimpleNamespace
        from pathlib import Path
        owner=client.get('/api/auth/me',headers=a).json()['id']
        class Reader:
            def media(self,*args): return [SimpleNamespace(id='456',caption='My real original',media_type='VIDEO',timestamp='2026-10-06T00:00:00+00:00')]
            def media_item(self,mid): return self.media()[0]
            def download_video(self,item):return (Path(__file__).resolve().parents[2]/'demo_data/videos/original_1.mp4').read_bytes()
        from app.services import instagram_oauth
        from fastapi import HTTPException
        def connected(db,uid):
            if uid!=owner:raise HTTPException(409,'Connect your Instagram account first.')
            return Reader(),'123'
        monkeypatch.setattr(instagram_oauth,'connected_reader',connected)
        assert client.get('/api/integrations/instagram/posts',headers=b).status_code==409
        assert client.post('/api/integrations/instagram/import/456',headers=b).status_code==409
        assert client.get('/api/integrations/instagram/posts',headers=a).json()[0]['id']=='456'
        assert client.post('/api/integrations/instagram/import/999',headers=a).status_code==404
        imported=client.post('/api/integrations/instagram/import/456',headers=a)
        assert imported.status_code==200,imported.text
        assert imported.json()['sourcePlatform']=='Instagram:456'
        assert client.post('/api/integrations/instagram/import/456',headers=a).json()['id']==imported.json()['id']
        assert client.get('/api/content/'+imported.json()['id']+'/media',headers=b).status_code==404
        assert client.get('/api/content/'+imported.json()['id']+'/media',headers=a).status_code==200
        assert client.post('/api/auth/logout',headers=a).status_code==200
        assert client.get('/api/auth/me',headers=a).status_code==401
        login=client.post('/api/auth/login',json={'email':'alpha@example.test','password':'secure-demo-123'})
        assert login.status_code==200
        fresh={'Authorization':'Bearer '+login.json()['token']}
        assert client.get('/api/cases/'+cid,headers=fresh).status_code==200
        assert client.post('/api/auth/login',json={'email':'alpha@example.test','password':'wrong-password'}).status_code==401
