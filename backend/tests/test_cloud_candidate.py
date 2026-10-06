"""Contract/security checks for the isolated Appwrite candidate (no live cloud calls)."""
import copy
import hashlib
import io
import json
import uuid
from contextlib import contextmanager
from datetime import timedelta
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from cloud.api import create_app
from cloud.auth import consume_token
from cloud.client import ACCOUNTS, BUDGETS, RECORDS, Client, CloudError
from cloud.store import Store, digest, now, payload, stamp
from cloud.worker import run_job, sweep


def test_inline_table_indexes_use_attributes_without_changing_stored_schema():
    from cloud.schema import TABLES, table_creation
    original = copy.deepcopy(TABLES)
    for spec in TABLES:
        request = table_creation(spec)
        assert all(not column.get('encrypt') for column in request['columns'])
        for expected, sent in zip(spec['indexes'], request['indexes']):
            assert sent['attributes'] == expected['columns']
            assert 'columns' not in sent
            assert sent['orders'] == expected['orders']
    assert TABLES == original


class MemoryClient:
    def __init__(self):
        self.data = {ACCOUNTS: {}, RECORDS: {}, BUDGETS: {}}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @contextmanager
    def transaction(self):
        snapshot = copy.deepcopy(self.data)
        try:
            yield 'transaction'
        except Exception:
            self.data = snapshot
            raise

    def get(self, table, identity, tx=None):
        if identity not in self.data[table]:
            raise CloudError(404)
        return copy.deepcopy(self.data[table][identity])

    def create(self, table, identity, data, tx=None):
        if identity in self.data[table] or (table == ACCOUNTS and any(r['email'] == data['email'] for r in self.data[table].values())):
            raise CloudError(409)
        self.data[table][identity] = {'$id': identity, '$permissions': [], **data}
        return self.get(table, identity)

    def increment(self, table, identity, column, tx=None, value=1):
        row = self.get(table, identity)
        return self.patch(table, identity, {column: row[column] + value}, tx)

    def patch(self, table, identity, data, tx=None):
        self.get(table, identity)
        self.data[table][identity].update(data)
        return self.get(table, identity)

    def delete(self, table, identity, tx=None):
        self.get(table, identity)
        del self.data[table][identity]
        return {}

    def rows(self, table, queries, limit=None):
        rows = list(self.data[table].values())
        for raw in queries:
            q = json.loads(raw)
            if q['method'] == 'equal':
                rows = [r for r in rows if r.get(q['attribute']) in q['values']]
            elif q['method'] == 'lessThanEqual':
                rows = [r for r in rows if r.get(q['attribute']) and r[q['attribute']] <= q['values'][0]]
        yield from copy.deepcopy(rows[:limit] if limit else rows)

    def request(self, *args, **kwargs):
        return {}  # Async wake is advisory; durable job stays in the records table.


@pytest.fixture
def cloud():
    db = MemoryClient()
    with TestClient(create_app(lambda: db)) as api:
        yield api, db


def signup(api, email='creator@example.com'):
    response = api.post('/api/auth/signup', json={'email': email, 'password': 'creator-password'})
    assert response.status_code == 201, response.text
    value = response.json()
    return value, {'Authorization': 'Bearer ' + value['token']}


def test_cloud_session_private_and_logout_revokes(cloud):
    api, db = cloud
    value, headers = signup(api)
    assert api.get('/api/auth/me', headers=headers).json()['id'] == value['user']['id']
    serialized = json.dumps(db.data)
    assert value['token'] not in serialized
    assert 'creator-password' not in serialized
    assert all(r['$permissions'] == [] for table in db.data.values() for r in table.values())
    assert api.post('/api/auth/logout', headers=headers).status_code == 200
    assert api.get('/api/auth/me', headers=headers).status_code == 401


def test_cloud_owner_cannot_read_other_job(cloud):
    api, db = cloud
    first, _ = signup(api)
    _, second = signup(api, 'other@example.com')
    job = Store(db).job(first['user']['id'], 'fingerprint', {'uploadId': 'private-id'})
    assert api.get('/api/jobs/' + job['$id'], headers=second).status_code == 404


def test_cloud_reset_token_one_use_revokes_old_session(cloud):
    api, db = cloud
    first, headers = signup(api)
    store = Store(db)
    token = 'a-secret-reset-token-' + 'a' * 32
    store.create(first['user']['id'], 'reset', {'digest': digest(token), 'generation': 0},
                 row_id=digest(token)[:32], expires=now() + timedelta(minutes=10))
    response = api.post('/api/auth/reset-password', json={'token': token, 'password': 'updated-password'})
    assert response.status_code == 200
    assert api.get('/api/auth/me', headers=headers).status_code == 401
    assert api.post('/api/auth/reset-password', json={'token': token, 'password': 'again-password'}).status_code == 400
    assert api.post('/api/auth/login', json={'email': first['user']['email'], 'password': 'updated-password'}).status_code == 200


def test_cloud_deletion_revokes_access_and_worker_removes_records(cloud):
    api, db = cloud
    value, headers = signup(api)
    assert api.post('/api/auth/delete-account', headers=headers, json={'password': 'creator-password'}).status_code == 200
    assert api.get('/api/auth/me', headers=headers).status_code == 401
    sweep(Store(db))
    assert not db.data[ACCOUNTS]
    assert all(r['owner_id'] == 'operator' for r in db.data[RECORDS].values())


def test_cloud_budget_failed_reservation_rolls_back(cloud):
    _, db = cloud
    store = Store(db)
    store.consume('example', 5, 3600, weight=4)
    with pytest.raises(HTTPException) as error:
        store.consume('example', 5, 3600, weight=2)
    assert error.value.status_code == 429
    assert list(db.data[BUDGETS].values())[0]['count'] == 4


def png_bytes():
    out = io.BytesIO()
    Image.new('RGB', (80, 80), 'blue').save(out, 'PNG')
    return out.getvalue()


def test_cloud_hash_worker_uses_real_file_and_hides_internal_job_args(cloud, monkeypatch):
    api, db = cloud
    value, headers = signup(api)
    data = png_bytes()
    response = api.post('/api/content/uploads/start', headers=headers,
        json={'content_type': 'image/png', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    assert response.status_code == 201
    identity = response.json()['id']
    store = Store(db)
    row = store.owned(value['user']['id'], identity)
    record = payload(row)
    job = store.job(value['user']['id'], 'fingerprint', {'uploadId': identity})
    record['offset'] = len(data)
    record['jobId'] = job['$id']
    store.update(row, record, state='pending')
    monkeypatch.setattr('cloud.worker.Files.download', lambda *args: data)
    run_job(store, job['$id'])
    status = api.get('/api/jobs/' + job['$id'], headers=headers).json()
    assert status['state'] == 'complete'
    assert len(status['result']['perceptualHash']) == 16
    assert 'args' not in status and 'fileId' not in json.dumps(status)
    assert len(api.get('/api/content', headers=headers).json()) == 1


def test_cloud_corrupt_upload_queues_cleanup_without_visible_original(cloud, monkeypatch):
    api, db = cloud
    value, headers = signup(api)
    data = png_bytes()
    identity = api.post('/api/content/uploads/start', headers=headers,
        json={'content_type': 'image/png', 'size': len(data), 'sha256': '0' * 64}).json()['id']
    store = Store(db)
    row = store.owned(value['user']['id'], identity)
    record = payload(row)
    job = store.job(value['user']['id'], 'fingerprint', {'uploadId': identity})
    record['jobId'] = job['$id']
    store.update(row, record, state='pending')
    monkeypatch.setattr('cloud.worker.Files.download', lambda *args: data)
    run_job(store, job['$id'])
    assert api.get('/api/content', headers=headers).json() == []
    assert api.get('/api/jobs/' + job['$id'], headers=headers).json()['state'] == 'error'
    cleanups = [r for r in db.data[RECORDS].values() if r['kind'] == 'job' and payload(r)['type'] == 'delete_file']
    assert len(cleanups) == 2  # expiry cleanup plus immediate failed-media cleanup


def test_cloud_expired_email_lease_never_resends(cloud, monkeypatch):
    api, db = cloud
    value, _ = signup(api)
    store = Store(db)
    job = store.job(value['user']['id'], 'account_email', {})
    store.update(job, {**payload(job), 'lease': 'old'}, state='processing', expires=now() - timedelta(minutes=1))
    monkeypatch.setattr('app.services.account_email.send_account_email', lambda *args: pytest.fail('Must not resend'))
    sweep(store)
    assert store.owned(value['user']['id'], job['$id'])['state'] == 'unknown'


def test_rest_client_preserves_v1_path_and_redacts_provider_secrets(monkeypatch):
    from app.config import Settings
    monkeypatch.setattr('cloud.client.get_settings', lambda: Settings())
    seen = []
    def transport(request):
        seen.append(str(request.url))
        return httpx.Response(403, json={'type': 'general_unauthorized_scope', 'message': 'secret-private-value'})
    with Client('private-key', transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(CloudError) as error:
            client.get(RECORDS, 'row')
    assert '/v1/tablesdb/' in seen[0]
    assert 'secret-private-value' not in str(error.value)


def test_rest_client_refuses_public_record(monkeypatch):
    from app.config import Settings
    monkeypatch.setattr('cloud.client.get_settings', lambda: Settings())
    with Client('private-key', transport=httpx.MockTransport(lambda r: httpx.Response(200,
          json={'$id': 'row', '$permissions': ['read("any")']}))) as client:
        with pytest.raises(CloudError, match='unavailable'):
            client.get(RECORDS, 'row')


def test_cloud_deletion_retries_storage_failure_without_erasing_account(cloud, monkeypatch):
    api, db = cloud
    value, headers = signup(api)
    store = Store(db)
    store.create(value['user']['id'], 'original', {'fileId': 'private-file'})
    api.post('/api/auth/delete-account', headers=headers, json={'password': 'creator-password'})
    def unavailable(*args):
        raise CloudError(503)
    monkeypatch.setattr('cloud.worker.Files.delete', unavailable)
    sweep(store)
    assert db.data[ACCOUNTS][value['user']['id']]['closing'] is True
    jobs = list(store.owned_rows('operator', 'job'))
    assert jobs[0]['state'] == 'queued'
    assert db.data[RECORDS]


def test_function_adapter_keeps_trusted_key_out_of_http_headers():
    import asyncio
    from types import SimpleNamespace
    from cloud.main_api import dispatch
    class Response:
        def json(self, value, code):
            return {'status': code, 'value': value}
        def binary(self, data, code, headers):
            return {'status': code, 'data': data, 'headers': headers}
    context = SimpleNamespace(req=SimpleNamespace(body_binary=b'abc', method='POST', path='/upload',
        query_string='offset=0', headers={'x-appwrite-key': 'private-runtime-key', 'authorization': 'Bearer session',
                                          'content-type': 'application/octet-stream'}), res=Response())
    async def application(scope, receive, send):
        assert scope['ditto.cloud_key'] == 'private-runtime-key'
        assert b'x-appwrite-key' not in dict(scope['headers'])
        assert (await receive())['body'] == b'abc'
        await send({'type': 'http.response.start', 'status': 201, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'ok'})
    result = asyncio.run(dispatch(context, application))
    assert result['status'] == 201 and result['data'] == b'ok'
    assert 'private-runtime-key' not in str(result)


def test_function_package_excludes_sqlite_and_secrets(tmp_path):
    import tarfile
    from scripts.package_appwrite_cloud import package
    target = tmp_path / 'candidate.tar.gz'
    package(target)
    with tarfile.open(target) as archive:
        names = archive.getnames()
        assert 'cloud/main_api.py' in names and 'cloud/main_worker.py' in names
        assert 'requirements.txt' in names
        assert not any('.env' in n or '.db' in n or 'database.py' in n or 'token-encryption' in n for n in names)


def test_cloud_upload_end_to_end_and_retry_integrity(cloud, monkeypatch):
    api, db = cloud
    value, headers = signup(api)
    _, intruder = signup(api, 'intruder@example.com')
    data = png_bytes()
    remote = {}
    def metadata(self, file_id):
        if file_id not in remote:
            raise CloudError(404)
        return remote[file_id]['meta']
    def chunk(self, file_id, name, content, offset, size):
        assert content == data and offset == 0 and size == len(data)
        remote[file_id] = {'bytes': content, 'meta': {'$id': file_id, '$permissions': [],
             'sizeOriginal': size, 'chunksTotal': 1, 'chunksUploaded': 1}}
        return remote[file_id]['meta']
    monkeypatch.setattr('cloud.files.Files.metadata', metadata)
    monkeypatch.setattr('cloud.files.Files.chunk', chunk)
    monkeypatch.setattr('cloud.files.Files.download', lambda self, identity: remote[identity]['bytes'])
    identity = api.post('/api/content/uploads/start', headers=headers,
        json={'content_type': 'image/png', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}).json()['id']
    endpoint = '/api/content/uploads/' + identity
    assert api.post(endpoint + '/chunks', headers=intruder, content=data).status_code == 404
    assert api.post(endpoint + '/chunks', headers=headers, content=data).json()['uploadedBytes'] == len(data)
    assert api.post(endpoint + '/chunks', headers=headers, content=data).status_code == 200
    changed = bytes([data[0] ^ 1]) + data[1:]
    assert api.post(endpoint + '/chunks', headers=headers, content=changed).status_code == 409
    response = api.post(endpoint + '/complete', headers=headers)
    assert response.status_code == 202, response.text
    job_id = response.json()['jobId']
    assert api.post(endpoint + '/complete', headers=headers).json()['jobId'] == job_id
    run_job(Store(db), job_id)
    assert api.get('/api/jobs/' + job_id, headers=headers).json()['state'] == 'complete'
    assert api.get('/api/content/' + identity + '/media', headers=headers).content == data
    assert api.get('/api/content/' + identity + '/media', headers=intruder).status_code == 404


def test_cloud_upload_reconciles_remote_chunk_after_lost_metadata_commit(cloud, monkeypatch):
    api, db = cloud
    value, headers = signup(api)
    data = png_bytes()
    identity = api.post('/api/content/uploads/start', headers=headers,
        json={'content_type': 'image/png', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}).json()['id']
    store = Store(db)
    row = store.owned(value['user']['id'], identity)
    record = payload(row)
    record['inFlight'] = {'offset': 0, 'sha256': hashlib.sha256(data).hexdigest(), 'until': stamp(now() + timedelta(minutes=1))}
    store.update(row, record)
    monkeypatch.setattr('cloud.files.Files.metadata', lambda self, file_id: {'$id': file_id,
        '$permissions': [], 'sizeOriginal': len(data), 'chunksTotal': 1, 'chunksUploaded': 1})
    monkeypatch.setattr('cloud.files.Files.chunk', lambda *args: pytest.fail('Already stored; must not upload twice'))
    result = api.post('/api/content/uploads/' + identity + '/chunks', headers=headers, content=data)
    assert result.status_code == 200 and result.json()['uploadedBytes'] == len(data)


def provider_settings(monkeypatch):
    from app.config import Settings
    from cryptography.fernet import Fernet
    settings = Settings(public_base_url='https://ditto.example', instagram_app_secret='secret',
        token_encryption_key=Fernet.generate_key().decode(), smtp_host='smtp.example', smtp_port=465,
        smtp_from='support@example.com', cloud_email_outreach_enabled=True, google_cloud_api_key='key', gemini_api_key='key')
    for target in ('cloud.oauth.get_settings', 'cloud.auth.get_settings', 'cloud.cases.get_settings',
                   'cloud.discovery.get_settings', 'app.services.account_email.get_settings'):
        monkeypatch.setattr(target, lambda: settings)
    return settings


def add_case(db, uid):
    from cloud.cases import compared_case
    store = Store(db)
    original = store.create(uid, 'original', {'title': 'My original'}, state='ready')
    candidate = store.create(uid, 'candidate', {'sourceUrl': ''}, state='ready')
    identity = uuid.uuid4().hex
    store.create(uid, 'case', compared_case(original, candidate, 0.9, identity), row_id=identity)
    return identity


def test_oauth_browser_ticket_single_use_and_wrong_browser_rejected(cloud, monkeypatch):
    api, db = cloud
    provider_settings(monkeypatch)
    value, headers = signup(api)
    auth_url = api.post('/api/integrations/instagram/connect', headers=headers).json()['authorizationUrl']
    from urllib.parse import urlsplit, parse_qs
    ticket = parse_qs(urlsplit(auth_url).query)['ticket'][0]
    response = api.get('/api/integrations/instagram/begin?ticket=' + ticket, follow_redirects=False)
    assert response.status_code == 302
    assert 'instagram_business_basic' in response.headers['location']
    assert 'Secure' in response.headers['set-cookie'] and 'HttpOnly' in response.headers['set-cookie']
    assert api.get('/api/integrations/instagram/begin?ticket=' + ticket, follow_redirects=False).status_code == 400
    assert api.get('/api/integrations/instagram/callback?state=' + ticket + '&code=provider-code').status_code == 400
    cookie = response.cookies['ditto_instagram_browser']
    result = api.get('/api/integrations/instagram/callback?state=' + ticket + '&code=provider-code',
                     headers={'Cookie': 'ditto_instagram_browser=' + cookie})
    assert result.status_code == 200
    jobs = [r for r in db.data[RECORDS].values() if r['kind'] == 'job']
    assert len(jobs) == 1 and payload(jobs[0])['type'] == 'instagram_exchange'
    assert 'provider-code' not in json.dumps(db.data)
    assert api.get('/api/integrations/instagram/callback?state=' + ticket + '&code=provider-code',
                   headers={'Cookie': 'ditto_instagram_browser=' + cookie}).status_code == 400


def test_oauth_ticket_revoked_with_source_session(cloud, monkeypatch):
    api, db = cloud
    provider_settings(monkeypatch)
    value, headers = signup(api)
    url = api.post('/api/integrations/instagram/connect', headers=headers).json()['authorizationUrl']
    api.post('/api/auth/logout', headers=headers)
    response = api.get('/api/integrations/instagram/begin?' + url.split('?')[1], follow_redirects=False)
    assert response.status_code in (400, 503)
    assert not any(r['kind'] == 'job' for r in db.data[RECORDS].values())


def test_provider_consent_and_owner_checks(cloud, monkeypatch):
    api, db = cloud
    provider_settings(monkeypatch)
    first, headers = signup(api)
    _, other = signup(api, 'second@example.com')
    original = Store(db).create(first['user']['id'], 'original', {'kind': 'image'}, state='ready')
    endpoint = '/api/discovery/' + original['$id'] + '/web-search'
    assert api.post(endpoint, headers=headers, json={}).status_code == 409
    assert api.post(endpoint, headers=other, json={'consent_to_google': True}).status_code == 404
    assert api.post(endpoint, headers=headers, json={'consent_to_google': True}).status_code == 202


def test_email_approval_is_idempotent_and_real_send_requires_verified_email(cloud, monkeypatch):
    api, db = cloud
    provider_settings(monkeypatch)
    value, headers = signup(api)
    uid = value['user']['id']
    identity = add_case(db, uid)
    body = {'recipient': 'recipient@example.com', 'editedBody': 'Please review this potential reuse.',
        'requestId': uuid.uuid4().hex, 'evidenceReviewed': True, 'recipientConfirmed': True, 'reminderDays': 7}
    endpoint = '/api/cases/' + identity + '/approve'
    assert api.post(endpoint, headers=headers, json=body).status_code == 409
    db.patch(ACCOUNTS, uid, {'verified': True})
    first = api.post(endpoint, headers=headers, json=body)
    assert first.status_code == 200, first.text
    job_id = first.json()['dispatchJob']
    assert api.post(endpoint, headers=headers, json=body).json()['dispatchJob'] == job_id
    sent = []
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def send_message(self, message): sent.append(message)
    monkeypatch.setattr('cloud.provider_jobs.smtplib.SMTP_SSL', SMTP)
    run_job(Store(db), job_id)
    run_job(Store(db), job_id)
    assert len(sent) == 1 and sent[0]['To'] == 'recipient@example.com'
    case = api.get('/api/cases/' + identity, headers=headers).json()
    assert case['dispatchStatus'] == 'accepted' and case['currentState'] == 'awaiting_response'
    assert case['nextFollowUpAt'] and case['classification'] is None
    assert api.get('/api/jobs/' + job_id, headers=headers).json()['result']['delivered'] is None


def test_email_outage_unknown_status_cannot_be_reapproved(cloud, monkeypatch):
    api, db = cloud
    provider_settings(monkeypatch)
    value, headers = signup(api)
    uid = value['user']['id']
    db.patch(ACCOUNTS, uid, {'verified': True})
    identity = add_case(db, uid)
    body = {'recipient': 'recipient@example.com', 'editedBody': 'Reviewed message',
        'requestId': uuid.uuid4().hex, 'evidenceReviewed': True, 'recipientConfirmed': True}
    endpoint = '/api/cases/' + identity + '/approve'
    job = api.post(endpoint, headers=headers, json=body).json()['dispatchJob']
    def unavailable(*args, **kwargs): raise OSError('private SMTP response')
    monkeypatch.setattr('cloud.provider_jobs.smtplib.SMTP_SSL', unavailable)
    run_job(Store(db), job)
    case = api.get('/api/cases/' + identity, headers=headers).json()
    assert case['dispatchStatus'] == 'unknown'
    body['requestId'] = uuid.uuid4().hex
    assert api.post(endpoint, headers=headers, json=body).status_code == 409
    assert 'private SMTP response' not in api.get('/api/jobs/' + job, headers=headers).text


def test_comparison_creates_owner_scoped_case_with_actual_candidate_media(cloud, monkeypatch):
    api, db = cloud
    first, headers = signup(api)
    _, other = signup(api, 'other-comparison@example.com')
    uid, data, store = first['user']['id'], png_bytes(), Store(db)
    from cloud.worker import measured
    hashes = measured(data, 'image')
    original = store.create(uid, 'original', {'id': 'original', 'title': 'Owned original', 'kind': 'image', 'hashes': hashes}, state='ready')
    candidate = store.create(uid, 'candidate', {'title': 'Submitted candidate', 'kind': 'image', 'fileId': 'file',
        'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'contentType': 'image/png'}, state='pending')
    job = store.job(uid, 'compare', {'uploadId': candidate['$id'], 'originalId': original['$id']})
    store.update(candidate, {**payload(candidate), 'jobId': job['$id']})
    monkeypatch.setattr('cloud.worker.Files.download', lambda *args: data)
    run_job(store, job['$id'])
    result = api.get('/api/jobs/' + job['$id'], headers=headers).json()
    assert result['state'] == 'complete' and result['result']['similarity'] == 1
    identity = result['result']['caseId']
    case = api.get('/api/cases/' + identity, headers=headers).json()
    assert case['classification'] is None and case['candidate']['mediaKind'] == 'image'
    assert case['candidate']['hashSimilarity'] == 1
    assert api.get('/api/cases/' + identity + '/candidate-media', headers=headers).content == data
    assert api.get('/api/cases/' + identity + '/candidate-media', headers=other).status_code == 404
    stats = api.get('/api/dashboard/stats', headers=headers).json()
    assert stats['totalCases'] == 1 and stats['verifiedReposts'] == 0


def test_monthly_allowance_does_not_reset_at_fixed_epoch_boundary(monkeypatch):
    db = MemoryClient()
    store = Store(db)
    monkeypatch.setattr('cloud.store.time.time', lambda: 100)
    store.consume('vision', 2, 101, period=('month', 1000))
    monkeypatch.setattr('cloud.store.time.time', lambda: 102)
    store.consume('vision', 2, 101, period=('month', 1000))
    with pytest.raises(HTTPException) as error:
        store.consume('vision', 2, 101, period=('month', 1000))
    assert error.value.status_code == 429


def test_migration_preserves_password_and_archives_historical_cases_without_activating_them(tmp_path, monkeypatch):
    from scripts.migrate_appwrite_cloud import migrate
    from cloud.auth import password_hash
    db, uid, salt = MemoryClient(), uuid.uuid4().hex, 'ab' * 32
    media = tmp_path / 'original.png'
    media.write_bytes(png_bytes())
    user = {'id': uid, 'email': 'migration@example.com', 'display_name': 'Creator', 'salt': salt,
            'password_hash': password_hash('migration-password', salt)}
    content = {'id': uuid.uuid4().hex, 'user_id': uid, 'title': 'Real original', 'kind': 'image',
        'local_uri': str(media), 'palette_seed': 1, 'published_at': stamp(), 'source_platform': 'Device'}
    oldcase = {'id': uuid.uuid4().hex, 'user_id': uid, 'classification': 'demo_repost'}
    tables = {'users': [user], 'content': [content], 'cases': [oldcase]}
    keys = {t: ['id'] for t in tables}
    refs = {t: [] for t in tables}
    files = {}
    monkeypatch.setattr('cloud.files.Files.metadata', lambda self, identity: ({'$id': identity, 'sizeOriginal': len(files[identity]), 'chunksUploaded': 1, 'chunksTotal': 1}
        if identity in files else (_ for _ in ()).throw(CloudError(404))))
    monkeypatch.setattr('cloud.files.Files.chunk', lambda self, identity, name, data, offset, size: files.update({identity: data}))
    monkeypatch.setattr('cloud.files.Files.download', lambda self, identity: files[identity])
    first = migrate(Store(db), tables, keys, refs, tmp_path)
    second = migrate(Store(db), tables, keys, refs, tmp_path)
    assert first == second and first['originals'] == 1
    assert db.get(ACCOUNTS, uid)['password_hash'] == user['password_hash']
    assert not any(r['kind'] == 'case' for r in db.data[RECORDS].values())
    assert len(list(Store(db).owned_rows(uid, 'archive'))) == 3
    assert media.read_bytes() == png_bytes()
    tables['users'][0]['password_hash'] = '00' * 32
    with pytest.raises(ValueError, match='Existing account differs'):
        migrate(Store(db), tables, keys, refs, tmp_path)


def test_encrypted_backup_authenticated_before_restore_and_sessions_revoked(cloud, tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    from scripts import backup_appwrite_cloud as backup
    api, db = cloud
    account, headers = signup(api)
    uid = account['user']['id']
    job = Store(db).job(uid, 'outreach_email', {'recipient': 'private@example.com', 'body': 'private message'})
    monkeypatch.setattr(backup, 'frozen', lambda client: None)
    monkeypatch.setattr(backup, 'file_rows', lambda client: iter([]))
    cipher, target = Fernet(Fernet.generate_key()), tmp_path / 'snapshot.enc'
    counts = backup.backup(db, target, cipher)
    assert counts['rows'] >= 3 and b'private message' not in target.read_bytes()
    broken = tmp_path / 'truncated.enc'
    broken.write_bytes(b'\n'.join(target.read_bytes().splitlines()[:-1]) + b'\n')
    empty = MemoryClient()
    with pytest.raises(ValueError, match='incomplete'):
        backup.restore(empty, broken, cipher)
    assert not any(empty.data.values())
    restored = backup.restore(empty, target, cipher)
    assert restored['rows'] > 0 and empty.get(ACCOUNTS, uid)['auth_epoch'] == 1
    assert not list(Store(empty).owned_rows(uid, 'session'))
    assert Store(empty).owned(uid, job['$id'])['state'] == 'unknown'
    with pytest.raises(ValueError, match='empty'):
        backup.restore(empty, target, cipher)


def test_deployment_plan_never_exports_secrets_and_refuses_replacing_live_function(monkeypatch):
    from scripts import deploy_appwrite_cloud as deploy
    monkeypatch.setenv('APPWRITE_DEPLOY_KEY', 'private-management-key')
    monkeypatch.setenv('INSTAGRAM_APP_SECRET', 'private-instagram-secret')
    monkeypatch.setenv('META_ACCESS_TOKEN', 'legacy-token-never-deploy')
    assert 'private-management-key' not in json.dumps(deploy.plan())
    assert 'private-instagram-secret' not in json.dumps(deploy.plan())
    assert 'APPWRITE_DEPLOY_KEY' not in deploy.configuration()
    assert 'META_ACCESS_TOKEN' not in deploy.configuration()
    class Live:
        def request(self, method, path, **kwargs):
            assert method == 'GET', 'A live function must never be modified by staging'
            return {'enabled': True}
    with pytest.raises(ValueError, match='already enabled'):
        deploy.function(Live(), 'ditto-api')


def test_backup_frame_reordering_is_rejected(cloud, tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    from scripts import backup_appwrite_cloud as backup
    api, db = cloud
    signup(api)
    monkeypatch.setattr(backup, 'frozen', lambda client: None)
    monkeypatch.setattr(backup, 'file_rows', lambda client: iter([]))
    cipher, path = Fernet(Fernet.generate_key()), tmp_path / 'snapshot.enc'
    backup.backup(db, path, cipher)
    frames = path.read_bytes().splitlines()
    frames[1], frames[2] = frames[2], frames[1]
    path.write_bytes(b'\n'.join(frames) + b'\n')
    with pytest.raises(ValueError, match='reordered'):
        list(backup.read_backup(path, cipher))


def test_launch_refuses_missing_evidence_before_cloud_writes(tmp_path):
    from scripts.launch_appwrite_cloud import publish
    class NoWrites:
        def request(self, *args, **kwargs):
            pytest.fail('Unapproved launch must not contact the cloud')
    with pytest.raises(ValueError, match='incomplete'):
        publish(NoWrites(), {}, {}, tmp_path / 'absent.tar.gz')


def test_launch_failure_restores_private_function_configuration(tmp_path, monkeypatch):
    from scripts import launch_appwrite_cloud as launch
    archive = tmp_path / 'bundle.tar.gz'
    archive.write_bytes(b'generated test bundle')
    fingerprint = hashlib.sha256(archive.read_bytes()).hexdigest()
    evidence = {name: True for name in launch.GATES}
    evidence.update(operator='Svarsha T', bundleSha256=fingerprint,
        publicBaseUrl='https://generated.sgp.appwrite.run',
        metaRedirectUrl='https://generated.sgp.appwrite.run/api/integrations/instagram/callback')
    report = {'bundle': {'sha256': fingerprint}, 'publicBaseUrl': evidence['publicBaseUrl'],
        'verification': {'privateStorageIntegrity': True, 'sessionLogout': True},
        'deployments': {'ditto-api': 'api-build', 'ditto-worker': 'worker-build'}}
    monkeypatch.setattr(launch.deploy, 'execute', lambda *args: (200, json.dumps({'capabilities': {'instagram': True, 'accountEmail': True}})))
    class FailPublic:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args): raise RuntimeError('Public endpoint unavailable')
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: FailPublic())
    class Management:
        def __init__(self): self.updates = []
        def request(self, method, path, **kwargs):
            if method == 'GET':
                return {'enabled': False, 'execute': [], 'schedule': '', 'live': True,
                    'deploymentId': report['deployments'][path.rsplit('/', 1)[1]]}
            self.updates.append((path, kwargs['json']))
            return {}
    client = Management()
    with pytest.raises(RuntimeError):
        launch.publish(client, evidence, report, archive)
    assert [item[0] for item in client.updates[-2:]] == ['/functions/ditto-api', '/functions/ditto-worker']
    assert all(not item[1]['enabled'] and not item[1]['execute'] and not item[1]['schedule'] for item in client.updates[-2:])
