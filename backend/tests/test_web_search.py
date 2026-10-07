import io, secrets
import pytest
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
    settings=Settings(media_root=original_settings.media_root,serpapi_api_key='private-key')
    monkeypatch.setattr(api,'get_settings',lambda:settings)
    monkeypatch.setattr(api,'search',lambda images:[{'url':'https://example.test/result','verified':False}])
    with TestClient(app) as client:
        headers=signup(client);other=signup(client)
        data=picture()
        content=client.post('/api/content/upload?title=Real-original',headers=headers,files={'file':('original.png',data,'image/png')}).json()['id']
        endpoint='/api/discovery/'+content
        assert client.post(endpoint+'/web-search',headers=headers,json={}).status_code==422
        assert client.post(endpoint+'/web-search',headers=other,json={'consent_to_search_provider':True}).status_code==404
        result=client.post(endpoint+'/web-search',headers=headers,json={'consent_to_search_provider':True})
        assert result.status_code==200 and result.json()['unitsUsed']==2
        result=client.post(endpoint+'/compare',headers=headers,files={'file':('candidate.png',data,'image/png')})
        assert result.status_code==200 and result.json()['similarity']==1
        assert client.post(endpoint+'/compare',headers=other,files={'file':('candidate.png',data,'image/png')}).status_code==404
        assert client.post(endpoint+'/compare',headers=headers,files={'file':('bad.png',b'bad','image/png')}).status_code==422

def test_provider_results_redaction_and_deduplication(monkeypatch):
    monkeypatch.setattr(provider,'get_settings',lambda:Settings(serpapi_api_key='private-key'))
    captured=[]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):
            captured.append(kwargs)
            assert url=='https://serpapi.com/image'
            assert len(kwargs['files']['image'][1])<=500000
            return SimpleNamespace(status_code=200,json=lambda:{'image_id':'uploaded'})
        def get(self,url,**kwargs):
            captured.append(kwargs)
            if kwargs['params']['type']=='exact_matches':
                return SimpleNamespace(status_code=200,json=lambda:{'exact_matches':[
                    {'link':'https://www.instagram.com/reel/exact','title':'Copied reel','source':'Instagram'},
                    {'link':'javascript:evil'}]})
            return SimpleNamespace(status_code=200,json=lambda:{'visual_matches':[
                {'link':'https://example.test/a','title':'Similar result','source':'Example'},
                {'link':'https://www.instagram.com/reel/exact','title':'Duplicate row','source':'Instagram'}]})
    monkeypatch.setattr(provider.httpx,'Client',Client)
    results=provider.search([__import__('base64').b64encode(picture()).decode()])
    assert len(results)==2 and results[0]['verified'] is False
    assert results[0]['url']=='https://www.instagram.com/reel/exact'
    assert results[0]['matchType']=='exact' and results[0]['instagram'] is True
    assert captured[0]['data']['api_key']=='private-key'
    assert captured[1]['params']['engine']=='google_lens'
    assert captured[1]['params']['image_id']=='uploaded'
    assert captured[1]['params']['type']=='exact_matches'
    assert captured[2]['params']['type']=='visual_matches'
    assert 'private-key' not in str(results)
    assert provider.safe_url('https://user:pass@example.test') is None


@pytest.mark.parametrize('empty_type', ['exact_matches', 'visual_matches'])
def test_successful_empty_query_preserves_other_matches_and_continues_frames(monkeypatch, empty_type):
    monkeypatch.setattr(provider, 'get_settings', lambda: Settings(serpapi_api_key='private-key'))
    calls = []

    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {'image_id': 'uploaded'})
        def get(self, url, **kwargs):
            search_type = kwargs['params']['type']
            calls.append(search_type)
            if search_type == empty_type:
                row = {'search_metadata': {'status': 'Success'},
                       'error': "Google Lens hasn't returned any results for this query."}
            else:
                row = {search_type: [{'link': 'https://www.instagram.com/reel/candidate'}]}
            return SimpleNamespace(status_code=200, json=lambda: row)

    monkeypatch.setattr(provider.httpx, 'Client', Client)
    image = __import__('base64').b64encode(picture()).decode()
    results = provider.search([image, image])
    assert calls == ['exact_matches', 'visual_matches'] * 2
    assert len(results) == 1 and results[0]['frames'] == [0, 1]
    assert results[0]['matchType'] == ('similar' if empty_type == 'exact_matches' else 'exact')


@pytest.mark.parametrize('row', [
    {'exact_matches': []},
    {'search_metadata': {'status': 'Success'}},
    {'search_metadata': {'status': 'Success'},
     'error': "Google hasn't returned any results for this query."},
])
def test_valid_empty_response_returns_no_candidates(row):
    assert provider.result_items(row, 'exact_matches') == []


def test_empty_message_does_not_discard_results_if_provider_includes_them():
    item = {'link': 'https://example.test/result'}
    row = {'search_metadata': {'status': 'Success'},
           'error': "Google hasn't returned any results for this query.",
           'exact_matches': [item]}
    assert provider.result_items(row, 'exact_matches') == [item]


@pytest.mark.parametrize('row', [
    {'search_metadata': {'status': 'Success'}, 'error': 'Your searches are exhausted'},
    {'search_metadata': {'status': 'Error'},
     'error': "Google Lens hasn't returned any results for this query."},
    {'error': 'Invalid API key'},
])
def test_provider_failures_are_not_treated_as_empty_results(row):
    with pytest.raises(provider.SearchUnavailable):
        provider.result_items(row, 'exact_matches')


@pytest.mark.parametrize('row', [
    {}, [], {'search_metadata': []}, {'exact_matches': {}}, {'error': {}},
])
def test_malformed_search_responses_remain_failures(row):
    with pytest.raises(ValueError):
        provider.result_items(row, 'exact_matches')
