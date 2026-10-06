"""Durable media processing. Provider failures never become synthetic matches."""
import hashlib
import json
import hmac
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from fastapi import HTTPException
from cloud.client import ACCOUNTS, RECORDS, CloudError, query
from cloud.files import Files
from cloud.media_api import public_original
from cloud.store import digest, now, payload, stamp


def due(row):
    from datetime import datetime
    return datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00')) <= now()


def claim(store, job_id):
    with store.client.transaction() as tx:
        row = store.client.increment(RECORDS, job_id, 'revision', tx)
        value = payload(row)
        if row['kind'] != 'job' or row['state'] != 'queued' or not due(row):
            return None
        if row['owner_id'] != 'operator':
            store.guard(row['owner_id'], tx)
        value['lease'] = uuid.uuid4().hex
        value['attempts'] += 1
        store.update(row, value, state='processing', tx=tx, expires=now() + timedelta(minutes=5))
    return {**row, 'payload': json.dumps(value)}


def finish(store, job, result=None, error=None):
    with store.client.transaction() as tx:
        if job['owner_id'] != 'operator':
            store.guard(job['owner_id'], tx)
        row = store.owned(job['owner_id'], job['$id'], 'job', tx=tx, lock=True)
        value = payload(row)
        if row['state'] != 'processing' or value.get('lease') != payload(job).get('lease'):
            return
        value.update(result=result, error=error)
        store.update(row, value, state='error' if error else 'complete', tx=tx)


def measured(data, kind):
    if not data:
        raise ValueError('Empty media')
    if kind == 'image':
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Image exceeds the supported dimensions')
            image.verify()
        from app.matching.hasher import fingerprint
        return [fingerprint(data)]
    from app.matching.video import frames
    with tempfile.TemporaryDirectory(prefix='ditto-hash-') as directory:
        path = Path(directory) / 'media.mp4'
        path.write_bytes(data)
        return frames(str(path))


def fingerprint(store, job):
    uid = job['owner_id']
    args = payload(job)['args']
    row = store.owned(uid, args['uploadId'])
    if row['kind'] not in ('original', 'candidate'):
        raise ValueError('Invalid media job')
    value = payload(row)
    if row['state'] == 'ready':
        return public_original(row)
    if row['state'] != 'pending' or value.get('jobId') != job['$id']:
        raise ValueError('Invalid media job state')
    data = Files(store.client).download(value['fileId'])
    if len(data) != value['size'] or not hmac.compare_digest(hashlib.sha256(data).hexdigest(), value['sha256']):
        raise ValueError('Upload integrity check failed')
    hashes = measured(data, value['kind'])
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, row['$id'], tx=tx, lock=True)
        value = payload(row)
        if row['state'] != 'pending' or value.get('jobId') != job['$id']:
            raise ValueError('Media state changed')
        value['hashes'] = hashes
        value['perceptualHash'] = hashes[0]
        if row['kind'] == 'candidate':
            original = store.owned(uid, args['originalId'], 'original', tx=tx, lock=True)
            original_value = payload(original)
            if original['state'] != 'ready' or original_value['kind'] != value['kind']:
                raise ValueError('Original unavailable')
            from app.matching.video import compare
            result = {'originalId': original['$id'], 'candidateId': row['$id'],
                      'similarity': compare(original_value['hashes'], hashes),
                      'notice': 'Measured visual similarity only. Review ownership, permission and context before acting.'}
            value['comparison'] = result
        else:
            result = {key: value[key] for key in ('id', 'title', 'kind', 'perceptualHash', 'paletteSeed', 'publishedAt', 'sourcePlatform')}
        store.update(row, value, state='ready', tx=tx)
        store.activity(uid, 'Matching', 'Media processed',
                       'Private media fingerprinted; no infringement decision was made.', tx=tx)
    return result


def delete_account(store, job):
    uid = payload(job)['args']['owner']
    try:
        account = store.client.get(ACCOUNTS, uid)
    except CloudError as exc:
        if exc.status == 404:
            return {'cleanup': 'complete'}
        raise
    if not account.get('closing'):
        raise ValueError('Account is not closed')
    # Collect before deleting: cursor pagination must never use a deleted row.
    rows = list(store.client.rows(RECORDS, [query('equal', 'owner_id', [uid])]))
    for row in rows:
        if row['owner_id'] != uid:
            raise CloudError()
        if row['kind'] in ('original', 'candidate'):
            Files(store.client).delete(payload(row)['fileId'])
    for row in rows:
        try:
            store.client.delete(RECORDS, row['$id'])
        except CloudError as exc:
            if exc.status != 404:
                raise
    store.client.delete(ACCOUNTS, uid)
    return {'cleanup': 'complete'}


def run_job(store, job_id):
    job = claim(store, job_id)
    if not job:
        return
    kind = payload(job)['type']
    try:
        if kind in ('fingerprint', 'compare'):
            result = fingerprint(store, job)
        elif kind == 'delete_file' and job['owner_id'] == 'operator':
            Files(store.client).delete(payload(job)['args']['fileId'])
            result = {'cleanup': 'complete'}
        elif kind == 'delete_account' and job['owner_id'] == 'operator':
            result = delete_account(store, job)
        elif kind == 'account_email':
            from cloud.auth import secure_cipher
            from app.services.account_email import send_account_email
            args = payload(job)['args']
            if args['expiresAt'] <= stamp():
                raise ValueError('Email link expired')
            token = secure_cipher().decrypt(args['sealedToken'].encode()).decode()
            link = store.owned(job['owner_id'], digest(token)[:32], args['purpose'])
            from cloud.auth import expires
            account = store.client.get(ACCOUNTS, job['owner_id'])
            if expires(link) <= now() or (args['purpose'] == 'reset' and
                    payload(link)['generation'] != account['reset_generation']):
                raise ValueError('Email link superseded')
            send_account_email(args['recipient'], args['purpose'], token)
            result = {'accepted': True}
        else:
            raise ValueError('Unsupported job type')
        finish(store, job, result=result)
    except (CloudError, HTTPException, ValueError, OSError):
        if job['owner_id'] == 'operator' and kind in ('delete_file', 'delete_account'):
            with store.client.transaction() as tx:
                row = store.owned('operator', job['$id'], 'job', tx=tx, lock=True)
                value = payload(row)
                if row['state'] == 'processing' and value.get('lease') == payload(job).get('lease'):
                    value['error'] = 'Cleanup pending; storage was unavailable.'
                    # Cleanup is idempotent and may safely retry. Do not erase the
                    # account until every owned file has actually been removed.
                    store.update(row, value, state='queued', tx=tx,
                                 expires=now() + timedelta(minutes=min(60, 2 ** min(value['attempts'], 6))))
            return
        # No retries for SMTP: an interrupted send can already have been accepted.
        # Media failures receive a durable cleanup task, including checksum errors.
        if kind in ('fingerprint', 'compare'):
            row = store.owned(job['owner_id'], payload(job)['args']['uploadId'])
            store.job('operator', 'delete_file', {'fileId': payload(row)['fileId']})
        finish(store, job, error='Processing failed. No result or delivery is confirmed.')


def sweep(store, limit=3):
    # Expired leases are recorded as unknown, never silently sent a second time.
    stale = list(store.client.rows(RECORDS, [query('equal', 'kind', ['job']),
                 query('equal', 'state', ['processing']), query('lessThanEqual', 'expires_at', [stamp()])], limit=limit))
    for row in stale:
        with store.client.transaction() as tx:
            locked = store.owned(row['owner_id'], row['$id'], 'job', tx=tx, lock=True)
            if locked['state'] == 'processing' and due(locked):
                value = payload(locked)
                value['error'] = 'Worker interrupted; processing or delivery status is unknown.'
                retry = locked['owner_id'] == 'operator' and value['type'] in ('delete_file', 'delete_account')
                store.update(locked, value, state='queued' if retry else 'unknown', tx=tx,
                             expires=now() + timedelta(minutes=1) if retry else None)
                if value['type'] in ('fingerprint', 'compare'):
                    upload = store.owned(locked['owner_id'], value['args']['uploadId'], tx=tx)
                    store.job('operator', 'delete_file', {'fileId': payload(upload)['fileId']}, tx=tx)
    queued = list(store.client.rows(RECORDS, [query('equal', 'kind', ['job']),
                  query('equal', 'state', ['queued']), query('lessThanEqual', 'expires_at', [stamp()])], limit=limit))
    for row in queued:
        try:
            run_job(store, row['$id'])
        except (CloudError, HTTPException):
            continue
