import hashlib
import io
import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.database.db import SessionLocal
from app.main import app
from app.models.account_security import RequestBudget
from app.models.jobs import ProcessingJob
from app.models.tables import Content
from app.providers.web_search import SearchUnavailable
from app.services import search_jobs
from app.services.processing import process_next, process_search_next


def image():
    output = io.BytesIO()
    Image.new('RGB', (64, 64), 'purple').save(output, format='PNG')
    return output.getvalue()


def signup(client):
    response = client.post('/api/auth/signup', json={
        'email': secrets.token_hex(8) + '@search.invalid', 'password': 'search-test-password-123'})
    return {'Authorization': 'Bearer ' + response.json()['token']}


def upload(client, headers):
    result = client.post('/api/content/upload', headers=headers, params={'title': 'Owned original'},
        files={'file': ('original.png', image(), 'image/png')})
    assert result.status_code == 201
    return result.json()['id']


@pytest.fixture
def configured(monkeypatch):
    settings = search_jobs.get_settings()
    monkeypatch.setattr(search_jobs, 'get_settings', lambda: Settings(
        media_root=settings.media_root, serpapi_api_key='test-private-key',
        search_monthly_unit_limit=250, search_user_monthly_unit_limit=40))
    monkeypatch.setattr(search_jobs, 'search', lambda images: [
        {'url': 'https://www.instagram.com/reel/candidate', 'matchType': 'exact', 'verified': False}])


def test_job_is_idempotent_owned_and_restorable(configured):
    with TestClient(app) as client:
        owner, other = signup(client), signup(client)
        content = upload(client, owner)
        endpoint = '/api/discovery/' + content + '/web-search-job'
        body = {'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)}
        assert client.get(endpoint, headers=owner).json()['jobId'] is None
        assert client.get(endpoint, headers=other).status_code == 404
        assert client.post(endpoint, headers=other, json=body).status_code == 404
        assert client.post(endpoint, headers=owner, json={}).status_code == 422
        submitted = client.post(endpoint, headers=owner, json=body)
        assert submitted.status_code == 202
        job = submitted.json()['jobId']
        duplicate = client.post(endpoint, headers=owner, json=body)
        assert duplicate.json()['jobId'] == job
        assert client.get('/api/jobs/' + job, headers=other).status_code == 404
        with SessionLocal() as db:
            stored = db.get(ProcessingJob, job)
            key = hashlib.sha256(('serpapi-user:' + stored.user_id).encode()).hexdigest()
            assert db.get(RequestBudget, key).count == 2
        assert process_search_next()
        completed = client.get(endpoint, headers=owner).json()
        assert completed['state'] == 'complete'
        assert completed['result']['unitsUsed'] == 2
        assert completed['result']['results'][0]['matchType'] == 'exact'
        assert client.post(endpoint, headers=owner, json=body).json()['result'] == completed['result']
        assert not process_search_next()


def test_running_receipt_observable_and_empty_search_completes(configured, monkeypatch):
    with TestClient(app) as client:
        owner = signup(client)
        content = upload(client, owner)
        endpoint = '/api/discovery/' + content + '/web-search-job'
        response = client.post(endpoint, headers=owner, json={
            'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)})
        job_id = response.json()['jobId']

        def search(images):
            # Query through a separate session, as Android does while provider
            # work is executing. The durable committed state is running.
            with SessionLocal() as db:
                assert db.get(ProcessingJob, job_id).state == 'running'
            return []

        monkeypatch.setattr(search_jobs, 'search', search)
        assert process_next()
        completed = client.get(endpoint, headers=owner).json()
        assert completed['state'] == 'complete'
        assert completed['result']['results'] == []


def test_provider_failure_is_not_automatically_replayed(configured, monkeypatch):
    with TestClient(app) as client:
        owner = signup(client)
        content = upload(client, owner)
        endpoint = '/api/discovery/' + content + '/web-search-job'
        response = client.post(endpoint, headers=owner, json={
            'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)})
        calls = []

        def unavailable(images):
            calls.append(True)
            raise SearchUnavailable('Reverse search unavailable. Try again later.')

        monkeypatch.setattr(search_jobs, 'search', unavailable)
        assert process_search_next()
        assert not process_search_next()
        status = client.get('/api/jobs/' + response.json()['jobId'], headers=owner).json()
        assert status['state'] == 'error'
        assert status['result'] is None
        assert len(calls) == 1


@pytest.mark.parametrize('receipt_age', ['fresh', 'stale', 'legacy'])
def test_crash_recovery_has_claim_grace_and_never_replays(configured, monkeypatch, receipt_age):
    with TestClient(app) as client:
        owner = signup(client)
        content = upload(client, owner)
        endpoint = '/api/discovery/' + content + '/web-search-job'
        response = client.post(endpoint, headers=owner, json={
            'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)})
        job_id = response.json()['jobId']

        def interrupted(images):
            raise SystemExit('Simulated process termination')

        monkeypatch.setattr(search_jobs, 'search', interrupted)
        with pytest.raises(SystemExit):
            process_search_next()
        with SessionLocal() as db:
            stored = db.get(ProcessingJob, job_id)
            assert stored.state == 'running'
            assert 'startedAt' in stored.payload
            if receipt_age == 'stale':
                stored.payload = {**stored.payload, 'startedAt':
                    (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()}
            elif receipt_age == 'legacy':
                stored.payload = {key: value for key, value in stored.payload.items() if key != 'startedAt'}
            db.commit()
            search_jobs.recover_interrupted(db)
        expected = 'running' if receipt_age == 'fresh' else 'unknown'
        assert client.get(endpoint, headers=owner).json()['state'] == expected
        assert not process_search_next()
        if receipt_age == 'fresh':
            # A later sweep resolves a real crash after the claim grace expires.
            with SessionLocal() as db:
                stored = db.get(ProcessingJob, job_id)
                stored.payload = {**stored.payload, 'startedAt':
                    (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()}
                db.commit()
                search_jobs.recover_interrupted(db)
            assert client.get(endpoint, headers=owner).json()['state'] == 'unknown'
            assert not process_search_next()


def test_failed_quota_reservation_does_not_partially_charge(configured, monkeypatch):
    settings = search_jobs.get_settings()
    monkeypatch.setattr(search_jobs, 'get_settings', lambda: Settings(
        media_root=settings.media_root, serpapi_api_key='test-private-key',
        search_monthly_unit_limit=250, search_user_monthly_unit_limit=1))
    with TestClient(app) as client:
        owner = signup(client)
        content = upload(client, owner)
        endpoint = '/api/discovery/' + content + '/web-search-job'
        body = {'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)}
        assert client.post(endpoint, headers=owner, json=body).status_code == 429
        assert client.get(endpoint, headers=owner).json()['jobId'] is None
        assert client.post(endpoint, headers=owner, json=body).status_code == 429
        assert not process_search_next()


def test_search_rejects_files_outside_owner_storage(configured):
    with TestClient(app) as client:
        owner, other = signup(client), signup(client)
        content, other_content = upload(client, owner), upload(client, other)
        with SessionLocal() as db:
            # A corrupted/imported URI must not cause another user's original
            # to be sent to the external search provider.
            db.get(Content, content).local_uri = db.get(Content, other_content).local_uri
            db.commit()
        endpoint = '/api/discovery/' + content + '/web-search-job'
        response = client.post(endpoint, headers=owner, json={
            'consent_to_search_provider': True, 'request_id': secrets.token_hex(16)})
        assert response.status_code == 409
        assert client.get(endpoint, headers=owner).json()['jobId'] is None
