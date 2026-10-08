import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings
from app.services import account_email


@pytest.mark.parametrize('port,origin,configured', [
    (587, 'https://example.test', True),
    (465, 'https://example.test', True),
    (0, 'https://example.test', False),
    (587, 'http://example.test', False),
])
def test_account_email_capability_matches_requirement(monkeypatch, port, origin, configured):
    settings = Settings(smtp_host='smtp.example.test', smtp_from='support@example.test',
                        smtp_port=port, public_base_url=origin)
    monkeypatch.setattr(account_email, 'get_settings', lambda: settings)
    assert settings.account_email_configured is configured
    if configured:
        assert account_email.require_email() is settings
    else:
        with pytest.raises(HTTPException) as error:
            account_email.require_email()
        assert error.value.status_code == 503


def test_health_reports_account_email_capability_without_secrets():
    from app.api.routes import settings
    with TestClient(app) as client:
        result = client.get('/api/health')
        assert result.status_code == 200
        assert result.json()['capabilities']['accountEmail'] == settings.account_email_configured
        assert 'smtp_password' not in result.text
