from app.config import Settings

def test_prefixed_dotenv_is_read(tmp_path,monkeypatch):
    for key in ('DITTO_DATABASE_URL','database_url','DITTO_DEMO_MODE','demo_mode','DITTO_MEDIA_ROOT','media_root'):
        monkeypatch.delenv(key,raising=False)
    path=tmp_path/'.env'
    path.write_text('DITTO_DATABASE_URL=sqlite:////workspace/data/ditto.db\nDITTO_DEMO_MODE=false\nDITTO_MEDIA_ROOT=/workspace/media\n')
    settings=Settings(_env_file=path)
    assert settings.database_url=='sqlite:////workspace/data/ditto.db'
    assert not settings.demo_mode
    assert settings.media_root=='/workspace/media'

def test_current_environment_overrides_dotenv(tmp_path,monkeypatch):
    path=tmp_path/'.env';path.write_text('DITTO_DATABASE_URL=sqlite:///stale.db\n')
    monkeypatch.setenv('DITTO_DATABASE_URL','sqlite:///current.db')
    assert Settings(_env_file=path).database_url=='sqlite:///current.db'
