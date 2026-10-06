import io, secrets
from types import SimpleNamespace
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.providers import web_search as provider
from app.api import web_search as api
from app.config import Settings

def picture(color='red'):
    buffer=io.BytesIO();Image.new('RGB',(64,64),color).save(buffer,format='PNG');return buffer.getvalue()

def signup(client):
    data=client.post('/api/auth/signup',json={'email':secrets.token_hex(8)+'@example.test','password':'strong-password-123'}).json()
    return {'Authorization':'Bearer '+data['token']}

def test_real_hash_comparison_and_search_consent(monkeypatch):
    original_settings=api.get_settings()
    settings=Settings(media_root=original_settings.media_root,google_cloud_api_key='private-key')
    monkeypatch.setattr(api,'get_settings',lambda:settings)
    monkeypatch.setattr(api,'search',lambda images:[{'url':'https://example.test/result','verified':False}])
    with TestClient(app) as client:
        headers=signup(client);other=signup(client)
        data=picture()
        content=client.post('/api/content/upload?title=Real-original',headers=headers,files={'file':('original.png',data,'image/png')}).json()['id']
        endpoint='/api/discovery/'+content
        assert client.post(endpoint+'/web-search',headers=headers,json={}).status_code==422
        assert client.post(endpoint+'/web-search',headers=other,json={'consent_to_google':True}).status_code==404
        result=client.post(endpoint+'/web-search',headers=headers,json={'consent_to_google':True})
        assert result.status_code==200 and result.json()['unitsUsed']==1
        result=client.post(endpoint+'/compare',headers=headers,files={'file':('candidate.png',data,'image/png')})
        assert result.status_code==200 and result.json()['similarity']==1
        assert client.post(endpoint+'/compare',headers=other,files={'file':('candidate.png',data,'image/png')}).status_code==404
        assert client.post(endpoint+'/compare',headers=headers,files={'file':('bad.png',b'bad','image/png')}).status_code==422

def test_provider_results_redaction_and_deduplication(monkeypatch):
    monkeypatch.setattr(provider,'get_settings',lambda:Settings(google_cloud_api_key='private-key'))
    captured=[]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):
            captured.append(kwargs)
            return SimpleNamespace(status_code=200,json=lambda:{'responses':[{'webDetection':{'fullMatchingImages':[{'url':'https://example.test/a'},{'url':'javascript:evil'}],'pagesWithMatchingImages':[{'url':'https://example.test/a'}]}}]})
    monkeypatch.setattr(provider.httpx,'Client',Client)
    results=provider.search(['encoded-image'])
    assert len(results)==1 and results[0]['verified'] is False
    assert captured[0]['headers']['X-Goog-Api-Key']=='private-key'
    assert captured[0]['json']['requests'][0]['features'][0]['type']=='WEB_DETECTION'
    assert 'private-key' not in str(results)
    assert provider.safe_url('https://user:pass@example.test') is None
