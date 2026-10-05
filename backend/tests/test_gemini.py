import json
from types import SimpleNamespace
import pytest
from app.providers import gemini
from app.config import Settings

def configure(monkeypatch,status=200,body=None):
    monkeypatch.setattr(gemini,'get_settings',lambda:Settings(gemini_api_key='test-secret'))
    class Client:
        def __init__(self,**kwargs): assert kwargs['follow_redirects'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            assert headers['x-goog-api-key']=='test-secret'
            assert 'test-secret' not in url
            return SimpleNamespace(status_code=status,json=lambda:body)
    monkeypatch.setattr(gemini.httpx,'Client',Client)

def test_valid_draft(monkeypatch):
    configure(monkeypatch,body={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({'subject':'Credit request','body':'Please review potential reuse.'})}]}}]})
    assert gemini.generate_draft({}).subject=='Credit request'

@pytest.mark.parametrize('status',[400,401,403,404,429,500,302])
def test_provider_errors(monkeypatch,status):
    configure(monkeypatch,status,{'error':'test-secret'})
    with pytest.raises(gemini.ProviderUnavailable) as exc:gemini.generate_draft({})
    assert 'test-secret' not in str(exc.value)

def test_invalid_responses(monkeypatch):
    for body in ({},{'candidates':[{'finishReason':'MAX_TOKENS'}]},{'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}'}]}}]}):
        configure(monkeypatch,body=body)
        with pytest.raises(gemini.ProviderUnavailable):gemini.generate_draft({})

def test_missing_key_and_redaction(monkeypatch):
    monkeypatch.setattr(gemini,'get_settings',lambda:Settings(gemini_api_key=''))
    with pytest.raises(gemini.ProviderUnavailable):gemini.generate_draft({})
    assert 'test-secret' not in repr(Settings(gemini_api_key='test-secret'))
