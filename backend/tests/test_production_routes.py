"""Production must never turn a demo action into a claimed live action."""
import secrets
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import settings


def test_production_refuses_demo_controls_and_sandbox_dispatch():
    # Start in development mode so this isolated test needs no SMTP/OAuth secrets.
    with TestClient(app) as client:
        account = client.post('/api/auth/signup', json={
            'email': secrets.token_hex(8) + '@example.test',
            'password': 'production-gate-test-123',
        }).json()
        client.headers['Authorization'] = 'Bearer ' + account['token']
        assert client.post('/api/demo/seed').status_code == 200
        cases = client.get('/api/cases').json()
        pending = next(c for c in cases if c['currentState'] == 'pending_approval')
        case_id = pending['id']
        with patch.object(settings, 'demo_mode', False), \
             patch('app.services.case_service.approve_case') as dispatch, \
             patch('app.services.case_service.run_follow_up') as follow_up:
            assert client.post('/api/demo/seed').status_code == 409
            assert client.get('/api/demo/ground-truth').status_code == 404
            assert client.post('/api/demo/advance-clock').status_code == 409
            assert client.get(f'/api/cases/{case_id}/candidate-media').status_code == 404
            result = client.post(f'/api/cases/{case_id}/approve', json={})
            assert result.status_code == 503
            assert 'No message was sent' in result.json()['detail']
            assert client.post(f'/api/cases/{case_id}/simulate-followup', json={'outcome': 'no_response'}).status_code == 409
            dispatch.assert_not_called()
            follow_up.assert_not_called()
            assert client.get(f'/api/cases/{case_id}').json()['currentState'] == pending['currentState']
