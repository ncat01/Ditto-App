from types import SimpleNamespace
import pytest
from app.providers import instagram
from app.config import Settings

def configure(monkeypatch, status=200, body=None):
    monkeypatch.setattr(instagram,'get_settings',lambda:Settings(meta_access_token='private-test-token'))
    class Client:
        def __init__(self,**kwargs):assert kwargs['follow_redirects'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url,params,headers):
            assert headers['Authorization']=='Bearer private-test-token'
            assert 'private-test-token' not in url and 'access_token' not in params
            return SimpleNamespace(status_code=status,json=lambda:body)
    monkeypatch.setattr(instagram.httpx,'Client',Client)
    return instagram.InstagramReader()

def test_profile(monkeypatch):
    reader=configure(monkeypatch,body={'user_id':'123','username':'creator','extra':'ignored'})
    assert reader.profile().user_id=='123'

def test_empty_media(monkeypatch):
    assert configure(monkeypatch,body={'data':[]}).media('123')==[]

def test_media(monkeypatch):
    reader=configure(monkeypatch,body={'data':[{'id':'456','media_type':'VIDEO'}]})
    assert reader.media('123')[0].id=='456'

@pytest.mark.parametrize('status,code',[(400,190),(403,10),(429,4),(500,None),(302,None)])
def test_errors_redacted(monkeypatch,status,code):
    reader=configure(monkeypatch,status,{'error':{'code':code,'message':'private-test-token'}})
    with pytest.raises(instagram.InstagramUnavailable) as exc:reader.profile()
    assert 'private-test-token' not in str(exc.value)

def test_malformed(monkeypatch):
    with pytest.raises(instagram.InstagramUnavailable):configure(monkeypatch,body={}).profile()
    with pytest.raises(instagram.InstagramUnavailable):configure(monkeypatch,body={'data':{}}).media('123')

def test_missing_secret_and_invalid_id(monkeypatch):
    monkeypatch.setattr(instagram,'get_settings',lambda:Settings(meta_access_token=''))
    reader=instagram.InstagramReader()
    with pytest.raises(instagram.InstagramUnavailable):reader.profile()
    with pytest.raises(instagram.InstagramUnavailable):reader.media('../me')
    assert 'private-test-token' not in repr(Settings(meta_access_token='private-test-token'))

def test_download_rejects_non_meta_hosts_and_nonvideo(monkeypatch):
    reader=configure(monkeypatch,body={})
    for url in ('http://cdninstagram.com/a','https://127.0.0.1/a','https://evil.example/a','https://fakecdninstagram.com/a','https://s.cdninstagram.com:8080/a'):
        item=instagram.MediaItem(id='1',media_type='VIDEO',media_url=url)
        with pytest.raises(instagram.InstagramUnavailable):reader.download_video(item)
    with pytest.raises(instagram.InstagramUnavailable):reader.download_video(instagram.MediaItem(id='1',media_type='IMAGE'))

def test_binding_requires_user_and_current_token(monkeypatch,tmp_path):
    import json
    from app.services import instagram_binding as binding
    monkeypatch.setattr(binding,'get_settings',lambda:Settings(meta_access_token='test-secret'))
    path=tmp_path/'binding.json';monkeypatch.setattr(binding,'BINDING_FILE',path)
    path.write_text(json.dumps({'ditto_user_id':'owner','instagram_user_id':'123','token_digest':binding.token_digest()}))
    assert binding.owner_binding('owner')['instagram_user_id']=='123'
    assert binding.owner_binding('other') is None
    monkeypatch.setattr(binding,'get_settings',lambda:Settings(meta_access_token='changed-secret'))
    assert binding.owner_binding('owner') is None
