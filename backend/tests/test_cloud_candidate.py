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
