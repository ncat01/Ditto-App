"""Encrypted export/restore for a frozen cloud service; no user data is printed.

Back up DITTO_BACKUP_KEY separately. Restore only to empty private tables/bucket.
Active sessions, OAuth attempts and pending messages are invalidated on restore.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.fernet import Fernet
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.client import ACCOUNTS, RECORDS, BUDGETS, Client, CloudError, query
from cloud.files import Files, BUCKET, CHUNK_BYTES, MAX_BYTES
from cloud.store import payload, encode, stamp

TABLES = (ACCOUNTS, RECORDS, BUDGETS)


def frozen(client):
    for identity in ('ditto-api', 'ditto-worker'):
        value = client.request('GET', '/functions/' + identity)
        if value.get('enabled') or value.get('execute') or value.get('schedule'):
            raise ValueError('Freeze API and scheduled worker first')
        pending = client.request('GET', '/functions/' + identity + '/executions',
            params=[('queries[]', query('equal', 'status', ['waiting', 'processing'])), ('queries[]', query('limit', values=[1]))])
        if pending.get('total', 0) or pending.get('executions'):
            raise ValueError('Wait for in-flight executions before a consistent backup')
    bucket = client.request('GET', '/storage/buckets/' + BUCKET)
    if bucket.get('$permissions') != [] or bucket.get('fileSecurity') is not True:
        raise ValueError('Bucket is not private')


def file_rows(client):
    cursor = None
    while True:
        queries = [query('limit', values=[100]), query('orderAsc', '$id')]
        if cursor:
            queries.append(query('cursorAfter', values=[cursor]))
        page = client.request('GET', '/storage/buckets/' + BUCKET + '/files', params=[('queries[]', q) for q in queries])['files']
        for row in page:
            client.private(row)
            yield row
        if len(page) < 100:
            return
        following = page[-1]['$id']
        if following == cursor:
            raise ValueError('File pagination stalled')
        cursor = following


def backup(client, target, cipher):
    frozen(client)
    if target.exists():
        raise ValueError('Backup destination already exists')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.partial')
    counts = {'rows': 0, 'files': 0, 'bytes': 0}
    chain, sequence = hashlib.sha256(), 0
    with temporary.open('xb') as output:
        os.chmod(temporary, 0o600)
        def write(value, final=False):
            nonlocal sequence
            plain = json.dumps({'sequence': sequence, **value}, separators=(',', ':')).encode()
            if not final:
                chain.update(plain)
            output.write(cipher.encrypt(plain) + b'\n')
            sequence += 1
        write({'type': 'header', 'format': 'ditto-cloud-backup-v1', 'createdAt': stamp()})
        for table in TABLES:
            for row in client.rows(table, []):
                write({'type': 'row', 'table': table, 'row': row})
                counts['rows'] += 1
        for meta in file_rows(client):
            if meta['sizeOriginal'] > MAX_BYTES or meta['chunksUploaded'] != meta['chunksTotal']:
                raise ValueError('Incomplete or oversized file prevents consistent backup')
            data = Files(client).download(meta['$id'])
            if len(data) != meta['sizeOriginal']:
                raise ValueError('File integrity differs')
            write({'type': 'file', 'id': meta['$id'], 'name': meta['name'], 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            for offset in range(0, len(data), 64_000):
                write({'type': 'chunk', 'offset': offset, 'data': base64.b64encode(data[offset:offset+64_000]).decode()})
            counts['files'] += 1
            counts['bytes'] += len(data)
        write({'type': 'end', 'counts': counts, 'digest': chain.hexdigest()}, final=True)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(target)
    return counts


def read_backup(source, cipher):
    chain = hashlib.sha256()
    ended = False
    with source.open('rb') as input:
        for sequence, line in enumerate(input):
            if ended or len(line) > 300_000:
                raise ValueError('Unexpected backup frame')
            plain = cipher.decrypt(line.strip())
            value = json.loads(plain)
            if value.get('sequence') != sequence:
                raise ValueError('Backup frames reordered')
            if sequence == 0 and (value.get('type') != 'header' or value.get('format') != 'ditto-cloud-backup-v1'):
                raise ValueError('Unsupported backup format')
            if value['type'] == 'end':
                if value['digest'] != chain.hexdigest():
                    raise ValueError('Backup checksum differs')
                ended = True
            else:
                chain.update(plain)
            yield value
    if not ended:
        raise ValueError('Backup incomplete; cannot restore')


def restored_row(table, row):
    value = {k: v for k, v in row.items() if not k.startswith('$')}
    if table == ACCOUNTS:
        value['auth_epoch'] += 1
        value['reset_generation'] += 1
    if table == RECORDS:
        if value['kind'] in ('session', 'oauth', 'verify', 'reset'):
            return None
        if value['kind'] == 'job' and value['state'] in ('queued', 'processing'):
            job = payload(row)
            if row['owner_id'] == 'operator' and job['type'] in ('delete_account', 'delete_file'):
                value['state'] = 'queued'
                value['expires_at'] = stamp()
            else:
                value['state'] = 'unknown'
                job['error'] = 'Restored after interruption. No delivery or processing result is confirmed; review before retrying.'
                value['payload'] = encode(job)
        if value['kind'] == 'case':
            case = payload(row)
            if case.get('dispatchStatus') in ('queued', 'sending'):
                case['dispatchStatus'] = 'unknown'
                value['payload'] = encode(case)
    return value


def restore(client, source, cipher):
    # Authenticate the ENTIRE backup before the first write, including truncation.
    for _ in read_backup(source, cipher):
        pass
    frozen(client)
    if any(list(client.rows(t, [], limit=1)) for t in TABLES) or next(file_rows(client), None):
        raise ValueError('Restore target must be empty; existing records are never overwritten')
    counts = {'rows': 0, 'files': 0}
    meta, data = None, bytearray()
    def flush():
        if meta is None:
            return
        if len(data) != meta['size'] or hashlib.sha256(data).hexdigest() != meta['sha256']:
            raise ValueError('Restored file checksum differs')
        for offset in range(0, len(data), CHUNK_BYTES):
            Files(client).chunk(meta['id'], meta['name'], bytes(data[offset:offset+CHUNK_BYTES]), offset, len(data))
        counts['files'] += 1
    for frame in read_backup(source, cipher):
        kind = frame['type']
        if kind == 'row':
            if frame['table'] not in TABLES:
                raise ValueError('Unexpected table')
            value = restored_row(frame['table'], frame['row'])
            if value is not None:
                client.create(frame['table'], frame['row']['$id'], value)
                counts['rows'] += 1
        elif kind == 'file':
            flush()
            if not 0 < frame['size'] <= MAX_BYTES:
                raise ValueError('Unsupported file size')
            meta, data = frame, bytearray()
        elif kind == 'chunk':
            if meta is None or frame['offset'] != len(data):
                raise ValueError('Unexpected file chunk')
            data.extend(base64.b64decode(frame['data'], validate=True))
            if len(data) > meta['size']:
                raise ValueError('Restored file too large')
        elif kind == 'end':
            flush()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'inspect', 'restore'))
    parser.add_argument('--file', type=Path, required=True)
    args = parser.parse_args()
    cipher = Fernet(os.environ['DITTO_BACKUP_KEY'].encode())
    if args.action == 'inspect':
        counts = None
        for frame in read_backup(args.file, cipher):
            if frame['type'] == 'end':
                counts = frame['counts']
        print(json.dumps({'authenticatedBackup': True, 'counts': counts, 'cloudWrites': 0}))
        return
    with Client(os.environ['APPWRITE_DEPLOY_KEY']) as client:
        counts = (backup if args.action == 'backup' else restore)(client, args.file, cipher)
    print(json.dumps({'operation': args.action, 'counts': counts, 'published': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Backup/restore stopped. Check frozen state, private key, target and schema. No record, provider response or credential is printed; partial output is not a verified backup.') from None
