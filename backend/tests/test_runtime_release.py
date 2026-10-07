"""Release guards must hold even if an old demo environment variable is supplied."""
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.matching.hasher import fingerprint


def test_missing_media_never_creates_a_fingerprint():
    with pytest.raises(ValueError, match='real media file'):
        fingerprint(None)


def test_synthetic_routes_are_not_registered_and_accounts_start_empty():
    with TestClient(app) as client:
        response = client.post('/api/auth/signup', json={
            'email': secrets.token_hex(8)+'@example.test', 'password':'release-test-password'})
        assert response.status_code == 201
        headers = {'Authorization':'Bearer '+response.json()['token']}
        for path in ['/api/demo/seed', '/api/demo/advance-clock', '/api/cases/unknown/simulate-followup']:
            assert client.post(path, headers=headers).status_code == 404
        assert client.get('/api/cases', headers=headers).json() == []
        assert client.get('/api/content', headers=headers).json() == []


def test_production_source_cannot_import_evaluation_agents():
    root = Path(__file__).resolve().parents[1]/'app'
    for path in root.rglob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert 'MockVerificationAgent' not in source
        assert 'MockActionPlanningAgent' not in source
        assert 'MockFollowUpAgent' not in source
        assert 'synthetic_hash' not in source
        assert 'demo_data/videos' not in source
