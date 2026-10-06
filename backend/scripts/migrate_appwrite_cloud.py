"""Additive migration from a frozen SQLite snapshot; originals are revalidated.

Historical/demo rows remain private archives, never new verified infringement cases.
Default is a read-only inventory. --apply requires a stopped source and private key.
"""
import argparse
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.auth import secure_cipher
from cloud.client import ACCOUNTS, RECORDS, Client, CloudError, ident
from cloud.files import CHUNK_BYTES, MAX_BYTES, Files
from cloud.oauth import connection_id
from cloud.store import Store, digest, encode, payload, now
from cloud.worker import measured
from scripts.plan_cloud_migration import inventory


def snapshot_rows(path):
    with sqlite3.connect(path.resolve(strict=True).as_uri() + '?mode=ro', uri=True) as source:
        with sqlite3.connect(':memory:') as db:
            source.backup(db)
            db.row_factory = sqlite3.Row
            names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            if any(not re.fullmatch('[a-z_]+', name) for name in names):
                raise ValueError('Unexpected table name')
            tables = {name: [dict(row) for row in db.execute('SELECT * FROM "' + name + '"')] for name in names}
            keys = {name: [r['name'] for r in db.execute('PRAGMA table_info("' + name + '")') if r['pk']] for name in names}
            refs = {name: [dict(r) for r in db.execute('PRAGMA foreign_key_list("' + name + '")')] for name in names}
    return tables, keys, refs


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def utc(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return date.replace(tzinfo=date.tzinfo or timezone.utc).isoformat()


def insert_record(store, owner, kind, value, identity, *, state='active', expires=None):
    try:
        old = store.client.get(RECORDS, identity)
        if old['owner_id'] != owner or old['kind'] != kind or canonical(json.loads(old['payload'])) != canonical(value):
            raise ValueError('Existing target differs; nothing will be overwritten')
        return False
    except CloudError as exc:
        if exc.status != 404:
            raise
    store.create(owner, kind, value, row_id=identity, state=state, expires=expires)
    return True


def migrate_file(store, owner, identity, value, data):
    """Use the tested upload journal to reconcile lost native chunk receipts."""
    from cloud.media_api import upload_chunk
    try:
        row = store.owned(owner, identity, 'original')
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        row = None
    if row:
        saved = payload(row)
        if any(saved.get(k) != value[k] for k in ('sha256', 'size', 'fileId', 'migrationSourceHash')) or row['state'] != 'uploading':
            raise ValueError('Interrupted migration differs; not overwritten')
    else:
        with store.client.transaction() as tx:
            store.guard(owner, tx)
            cleanup = store.job('operator', 'delete_file', {'fileId': value['fileId']},
                tx=tx, delay=now() + timedelta(days=7))
            row = store.create(owner, 'original', {**value, 'offset': 0, 'receipts': {}, 'inFlight': None,
                'filename': value['fileId'] + ('.mp4' if value['kind'] == 'video' else '.jpg'),
                'cleanupJob': cleanup['$id']}, row_id=identity, state='uploading', tx=tx)
    for offset in range(payload(row)['offset'], len(data), CHUNK_BYTES):
        upload_chunk(store, owner, identity, offset, data[offset:offset+CHUNK_BYTES])
    files = Files(store.client)
    if not files.complete(files.metadata(value['fileId']), len(data)) or hashlib.sha256(files.download(value['fileId'])).hexdigest() != value['sha256']:
        raise ValueError('Migrated file integrity differs')
    with store.client.transaction() as tx:
        store.guard(owner, tx)
        row = store.owned(owner, identity, 'original', tx=tx, lock=True)
        cleanup = store.owned('operator', payload(row)['cleanupJob'], 'job', tx=tx, lock=True)
        if cleanup['state'] != 'queued':
            raise ValueError('Migration upload expired; review before retrying')
        store.update(cleanup, payload(cleanup), state='cancelled', tx=tx)
        store.update(row, {**payload(row), **value}, state='ready', tx=tx)


def migrate(store, tables, keys, refs, media_root):
    users = {r['id']: r for r in tables.get('users', []) if r.get('email') and r.get('salt') and r.get('password_hash')}
    verified = {r['user_id'] for r in tables.get('account_verifications', [])}
    for uid, row in users.items():
        ident(uid)
        if not re.fullmatch('[a-f0-9]{64}', row['salt']) or not re.fullmatch('[a-f0-9]{64}', row['password_hash']):
            raise ValueError('Unsupported password format')
        account = {'email': row['email'].strip().lower(), 'display_name': row['display_name'], 'salt': row['salt'],
            'password_hash': row['password_hash'], 'verified': uid in verified, 'closing': False,
            'auth_epoch': 0, 'reset_generation': 0, 'revision': 0}
        try:
            old = store.client.get(ACCOUNTS, uid)
            if any(old[field] != account[field] for field in ('email', 'salt', 'password_hash')) or old['closing']:
                raise ValueError('Existing account differs; not overwritten')
        except CloudError as exc:
            if exc.status != 404:
                raise
            store.client.create(ACCOUNTS, uid, account)
    # Derive ownership using declared foreign keys, never guess from row ordering.
    ownership = {}
    for table, rows in tables.items():
        for row in rows:
            key = tuple(row[k] for k in keys[table])
            owner = row.get('user_id') or (row.get('id') if table == 'users' else None)
            if owner in users:
                ownership[(table, key)] = owner
    for _ in range(len(tables)):
        changed = False
        for table, rows in tables.items():
            for row in rows:
                target = (table, tuple(row[k] for k in keys[table]))
                if target in ownership:
                    continue
                owners = set()
                for ref in refs[table]:
                    for parent in tables.get(ref['table'], []):
                        if row.get(ref['from']) is not None and row[ref['from']] == parent.get(ref['to']):
                            parent_key = (ref['table'], tuple(parent[k] for k in keys[ref['table']]))
                            if parent_key in ownership:
                                owners.add(ownership[parent_key])
                if len(owners) > 1:
                    raise ValueError('Ambiguous row ownership')
                if owners:
                    ownership[target] = owners.pop()
                    changed = True
        if not changed:
            break
    counts = {'accounts': len(users), 'archivedRows': 0, 'originals': 0, 'originalsWithoutUsableMedia': 0}
    for table, rows in tables.items():
        for row in rows:
            key = tuple(row[k] for k in keys[table])
            owner = ownership.get((table, key), 'operator')
            value = {'table': table, 'record': row, 'notice': 'Historical integration data; not a new infringement decision.'}
            encode(value)  # Validate capacity before requesting a write.
            insert_record(store, owner, 'archive', value, digest('archive:' + table + ':' + canonical(key))[:32])
            counts['archivedRows'] += 1
    media_root = media_root.resolve(strict=True)
    remote = {r['content_id']: r for r in tables.get('remote_media', [])}
    for row in tables.get('content', []):
        uid = row.get('user_id')
        if uid not in users:
            continue
        source_hash = digest(canonical(row))
        identity = row['id'] if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,35}', row['id']) else digest('original:' + row['id'])[:32]
        try:
            old = store.owned(uid, identity, 'original')
            if payload(old).get('migrationSourceHash') != source_hash:
                raise ValueError('Existing original differs; not overwritten')
            if old['state'] == 'ready':
                counts['originals'] += 1
                continue
            if old['state'] != 'uploading':
                raise ValueError('Existing migration is not resumable; review privately')
        except Exception as exc:
            if not isinstance(exc, HTTPException) or exc.status_code != 404:
                raise
        data = None
        reference = remote.get(row['id'])
        if reference:
            if reference['user_id'] != uid:
                raise ValueError('Remote file ownership differs')
            Files(store.client).metadata(reference['file_id'])
            data = Files(store.client).download(reference['file_id'])
        elif row.get('local_uri'):
            path = Path(row['local_uri']).resolve()
            if path.is_relative_to(media_root) and path.is_file() and path.stat().st_size <= MAX_BYTES:
                data = path.read_bytes()
        if not data:
            counts['originalsWithoutUsableMedia'] += 1
            continue
        hashes = measured(data, row['kind'])
        file_id = digest('migrated-file:' + uid + ':' + row['id'])[:32]
        if reference:
            file_id = reference['file_id']
        value = {'id': identity, 'title': row['title'], 'kind': row['kind'], 'perceptualHash': hashes[0], 'hashes': hashes,
            'paletteSeed': row['palette_seed'], 'publishedAt': utc(row['published_at']), 'sourcePlatform': row['source_platform'],
            'fileId': file_id, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'contentType': 'video/mp4' if row['kind'] == 'video' else (mimetypes.guess_type(row.get('local_uri') or '')[0] or 'image/jpeg'),
            'migrationSourceHash': source_hash}
        if reference:
            insert_record(store, uid, 'original', value, identity, state='ready')
        else:
            migrate_file(store, uid, identity, value, data)
        counts['originals'] += 1
    # Tokens remain encrypted with the same private key, checked before transfer.
    for row in tables.get('instagram_connections', []):
        uid = row['user_id']
        if uid not in users:
            continue
        secure_cipher().decrypt(row['encrypted_token'].encode())
        claim_id = digest('instagram-owner:' + row['instagram_user_id'])[:32]
        insert_record(store, uid, 'instagram_claim', {}, claim_id)
        insert_record(store, uid, 'instagram', {'instagramId': row['instagram_user_id'], 'username': row['username'],
            'claimId': claim_id, 'token': row['encrypted_token'], 'refreshedAt': utc(row['refreshed_at'])},
            connection_id(uid), expires=datetime.fromisoformat(utc(row['expires_at'])))
    return counts


from fastapi import HTTPException

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True)
    parser.add_argument('--media-root', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--source-frozen', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps(inventory(args.sqlite), indent=2))
    else:
        if not args.source_frozen or not args.media_root or not os.getenv('APPWRITE_DEPLOY_KEY'):
            raise SystemExit('Apply requires --source-frozen, --media-root and private APPWRITE_DEPLOY_KEY. No source data is deleted.')
        try:
            old_key = Path(__file__).resolve().parents[2] / '.ditto-data/token-encryption.key'
            if not os.getenv('TOKEN_ENCRYPTION_KEY') and old_key.is_file():
                from cryptography.fernet import Fernet
                value = old_key.read_text(encoding='utf-8').strip()
                Fernet(value.encode())
                os.environ['TOKEN_ENCRYPTION_KEY'] = value
            tables, keys, refs = snapshot_rows(args.sqlite)
            with Client(os.environ['APPWRITE_DEPLOY_KEY']) as client:
                result = migrate(Store(client), tables, keys, refs, args.media_root)
            print(json.dumps({'migration': result, 'sourceDeleted': False, 'cutoverPerformed': False}, indent=2))
        except Exception:
            raise SystemExit('Migration stopped; source retained. Inspect schema, ownership and media locally before retrying. No private row is printed.') from None
