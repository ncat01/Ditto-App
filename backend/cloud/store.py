"""Owner-scoped private metadata and durable jobs in Appwrite TablesDB."""
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from cloud.client import ACCOUNTS, BUDGETS, RECORDS, CloudError, query


def now():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or now()).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def encode(value):
    text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(text.encode()) > 128_000:
        raise HTTPException(413, 'Record exceeds the supported size.')
    return text


def payload(row):
    try:
        value = json.loads(row['payload'])
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (KeyError, TypeError, ValueError):
        raise CloudError() from None


class Store:
    def __init__(self, client):
        self.client = client

    def create(self, owner, kind, data, *, row_id=None, parent='', state='active', expires=None, tx=None):
        return self.client.create(RECORDS, row_id or uuid.uuid4().hex, {
            'owner_id': owner, 'kind': kind, 'parent_id': parent,
            'state': state, 'payload': encode(data), 'revision': 0,
            'expires_at': stamp(expires) if expires else None,
        }, tx)

    def owned(self, owner, row_id, kind=None, *, tx=None, lock=False):
        try:
            row = (self.client.increment(RECORDS, row_id, 'revision', tx) if lock
                   else self.client.get(RECORDS, row_id, tx))
        except CloudError as exc:
            if exc.status == 404:
                raise HTTPException(404, 'Record unavailable') from None
            raise
        if row.get('owner_id') != owner or kind and row.get('kind') != kind:
            raise HTTPException(404, 'Record unavailable')
        return row

    def owned_rows(self, owner, kind, *, parent=None, state=None, limit=None):
        filters = [query('equal', 'owner_id', [owner]), query('equal', 'kind', [kind])]
        if parent is not None:
            filters.append(query('equal', 'parent_id', [parent]))
        if state is not None:
            filters.append(query('equal', 'state', [state]))
        for row in self.client.rows(RECORDS, filters, limit=limit):
            if row.get('owner_id') != owner or row.get('kind') != kind:
                raise CloudError()
            yield row

    def guard(self, owner, tx):
        # Stage a write BEFORE reading the current account. Conflicting mutations
        # cannot commit against an account closed by a concurrent deletion.
        account = self.client.increment(ACCOUNTS, owner, 'revision', tx)
        if account.get('closing'):
            raise HTTPException(401, 'Account deletion is in progress.')
        return account

    def update(self, row, data, *, state=None, tx=None, expires=None):
        change = {'payload': encode(data)}
        if state is not None:
            change['state'] = state
        if expires is not None:
            change['expires_at'] = stamp(expires)
        return self.client.patch(RECORDS, row['$id'], change, tx)

    def consume(self, scope, maximum, seconds, *, weight=1):
        if maximum < weight or weight <= 0:
            raise HTTPException(429, 'Request allowance exhausted.', headers={'Retry-After': str(seconds)})
        current = int(time.time())
        bucket = current // seconds
        identity = digest(scope + ':' + str(bucket))[:32]
        for attempt in range(5):
            try:
                with self.client.transaction() as tx:
                    try:
                        row = self.client.increment(BUDGETS, identity, 'count', tx, weight)
                    except CloudError as exc:
                        if exc.status != 404:
                            raise
                        row = self.client.create(BUDGETS, identity, {
                            'count': weight, 'expires_at': stamp(datetime.fromtimestamp((bucket + 1) * seconds, timezone.utc)),
                        }, tx)
                    if row['count'] > maximum:
                        raise HTTPException(429, 'Request allowance exhausted.',
                            headers={'Retry-After': str((bucket + 1) * seconds - current)})
                return
            except CloudError as exc:
                if exc.status != 409 or attempt == 4:
                    raise

    def activity(self, owner, agent, title, detail, case_id=None, tx=None):
        # Android stores event IDs as Long; random IDs avoid cross-user sequences.
        identity = uuid.uuid4().hex
        value = {'id': int(identity[:15], 16), 'timestamp': stamp(), 'agent': agent,
                 'title': title, 'detail': detail, 'caseId': case_id}
        return self.create(owner, 'activity', value, row_id=identity, tx=tx)

    def job(self, owner, job_type, args, *, parent='', tx=None, delay=None, row_id=None):
        value = {'type': job_type, 'args': args, 'attempts': 0, 'result': None,
                 'error': None, 'notBefore': stamp(delay) if delay else None}
        return self.create(owner, 'job', value, parent=parent, state='queued', tx=tx,
                           row_id=row_id, expires=delay or now())

    def wake(self, job_id):
        # A scheduled worker also finds queued jobs, so an execution API outage
        # never discards durable work. The dynamic key is not stored in job data.
        try:
            self.client.request('POST', '/functions/ditto-worker/executions', json={
                'body': encode({'jobId': job_id}), 'async': True,
                'method': 'POST', 'path': '/', 'headers': {'Content-Type': 'application/json'},
            })
        except CloudError:
            pass
