"""Resumable uploads; hashing is queued instead of blocking an HTTP Function."""
import hashlib
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from cloud.auth import current
from cloud.client import RECORDS, CloudError
from cloud.deps import get_store
from cloud.files import Files, CHUNK_BYTES, MAX_BYTES
from cloud.store import now, payload, stamp

router = APIRouter(prefix='/api/content')
MIMES = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp',
         'video/mp4': 'mp4', 'video/quicktime': 'mov'}


class UploadStart(BaseModel):
    title: str = Field(default='Uploaded original', min_length=1, max_length=256)
    content_type: str
    size: int = Field(ge=1, le=MAX_BYTES)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source: str = Field(default='Device upload', max_length=64)
    purpose: str = Field(default='original', pattern=r'^(original|candidate)$')
    original_id: str = Field(default='', max_length=36)


def public_original(row):
    value = payload(row)
    return {key: value[key] for key in ('id', 'title', 'kind', 'perceptualHash',
            'paletteSeed', 'publishedAt', 'sourcePlatform')}


@router.post('/uploads/start', status_code=201)
def start(body: UploadStart, account=Depends(current), store=Depends(get_store)):
    if body.content_type not in MIMES:
        raise HTTPException(415, 'Uploads support JPEG, PNG, WebP, MP4 and MOV.')
    uid = account['$id']
    kind = 'video' if body.content_type.startswith('video/') else 'image'
    store.consume('upload:' + uid, 20, 3600)
    store.consume('upload-bytes:global', 1_000_000_000, 86400, weight=body.size)
    identity, file_id = uuid.uuid4().hex, uuid.uuid4().hex
    value = {'id': identity, 'title': body.title.strip() or 'Uploaded original', 'kind': kind,
             'perceptualHash': '', 'paletteSeed': 1, 'publishedAt': stamp(),
             'sourcePlatform': body.source, 'fileId': file_id, 'size': body.size,
             'sha256': body.sha256, 'contentType': body.content_type,
             'filename': file_id + '.' + MIMES[body.content_type],
             'offset': 0, 'receipts': {}, 'inFlight': None}
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        if body.purpose == 'candidate':
            original = store.owned(uid, body.original_id, 'original', tx=tx, lock=True)
            if original['state'] != 'ready' or payload(original)['kind'] != kind:
                raise HTTPException(409, 'Choose a ready original of the same media type.')
        cleanup = store.job('operator', 'delete_file', {'fileId': file_id},
                            delay=now() + timedelta(minutes=30), tx=tx)
        value['cleanupJob'] = cleanup['$id']
        store.create(uid, body.purpose, value, row_id=identity, parent=body.original_id,
                     state='uploading', tx=tx)
    return {'id': identity, 'chunkBytes': CHUNK_BYTES, 'uploadedBytes': 0}


@router.post('/uploads/{upload_id}/chunks')
async def chunk(upload_id: str, request: Request, offset: int = 0,
                account=Depends(current), store=Depends(get_store)):
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > CHUNK_BYTES:
            raise HTTPException(413, 'Chunk exceeds 5,000,000 bytes.')
    return await run_in_threadpool(upload_chunk, store, account['$id'], upload_id, offset, bytes(data))


def upload_chunk(store, uid, upload_id, offset, data):
    row = store.owned(uid, upload_id)
    if row['kind'] not in ('original', 'candidate'):
        raise HTTPException(404, 'Upload unavailable')
    value = payload(row)
    if row['state'] != 'uploading':
        raise HTTPException(409, 'Upload has already been submitted.')
    if offset < 0 or offset % CHUNK_BYTES or offset >= value['size'] or len(data) != min(CHUNK_BYTES, value['size'] - offset):
        raise HTTPException(422, 'Invalid chunk offset or length.')
    checksum = hashlib.sha256(data).hexdigest()
    if offset < value['offset']:
        if value['receipts'].get(str(offset)) != checksum:
            raise HTTPException(409, 'Retry bytes differ from the accepted chunk.')
        return {'id': upload_id, 'uploadedBytes': value['offset']}
    if offset != value['offset']:
        raise HTTPException(409, 'Upload chunks in order.')
    files = Files(store.client)
    try:
        remote = files.metadata(value['fileId'])
    except CloudError as exc:
        if exc.status != 404:
            raise
        remote = None
    already_stored = bool(remote and remote.get('chunksUploaded') == offset // CHUNK_BYTES + 1)
    if remote and (remote.get('sizeOriginal') != value['size'] or
                   remote.get('chunksUploaded') not in (offset // CHUNK_BYTES, offset // CHUNK_BYTES + 1)):
        raise HTTPException(409, 'Remote upload differs; start a new upload.')
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, upload_id, tx=tx, lock=True)
        value = payload(row)
        if row['state'] != 'uploading' or value['offset'] != offset:
            raise HTTPException(409, 'Upload changed; refresh its status.')
        flight = value.get('inFlight')
        if flight:
            if flight['offset'] != offset or flight['sha256'] != checksum:
                raise HTTPException(409, 'Retry bytes differ from the reserved chunk.')
            if not already_stored and flight['until'] > stamp():
                raise HTTPException(409, 'Chunk is still being uploaded; retry shortly.', headers={'Retry-After': '60'})
        elif already_stored:
            raise HTTPException(409, 'Unexpected remote upload state. Start a new upload.')
        value['inFlight'] = {'offset': offset, 'sha256': checksum, 'until': stamp(now() + timedelta(seconds=60))}
        store.update(row, value, tx=tx)
    if not already_stored:
        files.chunk(value['fileId'], value['filename'], data, offset, value['size'])
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, upload_id, tx=tx, lock=True)
        value = payload(row)
        flight = value.get('inFlight')
        if row['state'] != 'uploading' or value['offset'] != offset or not flight or flight['sha256'] != checksum:
            raise HTTPException(409, 'Upload changed; refresh its status.')
        value['offset'] = offset + len(data)
        value['receipts'][str(offset)] = checksum
        value['inFlight'] = None
        store.update(row, value, tx=tx)
    return {'id': upload_id, 'uploadedBytes': value['offset']}


@router.get('/uploads/{upload_id}')
def upload_status(upload_id: str, account=Depends(current), store=Depends(get_store)):
    row = store.owned(account['$id'], upload_id)
    if row['kind'] not in ('original', 'candidate'):
        raise HTTPException(404, 'Upload unavailable')
    value = payload(row)
    return {'id': upload_id, 'uploadedBytes': value['offset'], 'size': value['size'],
            'state': row['state'], 'jobId': value.get('jobId')}


@router.post('/uploads/{upload_id}/complete', status_code=202)
def complete(upload_id: str, account=Depends(current), store=Depends(get_store)):
    uid = account['$id']
    initial = store.owned(uid, upload_id)
    if initial['kind'] not in ('original', 'candidate'):
        raise HTTPException(404, 'Upload unavailable')
    value = payload(initial)
    if initial['state'] != 'uploading' and value.get('jobId'):
        return {'id': upload_id, 'jobId': value['jobId'], 'state': initial['state']}
    remote = Files(store.client).metadata(value['fileId'])
    if value['offset'] != value['size'] or not Files(store.client).complete(remote, value['size']):
        raise HTTPException(409, 'Upload all chunks before submitting.')
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, upload_id, tx=tx, lock=True)
        value = payload(row)
        if row['state'] != 'uploading':
            if value.get('jobId'):
                return {'id': upload_id, 'jobId': value['jobId'], 'state': row['state']}
            raise HTTPException(409, 'Upload changed; refresh its status.')
        job_type = 'fingerprint' if row['kind'] == 'original' else 'compare'
        job = store.job(uid, job_type, {'uploadId': upload_id, 'originalId': row['parent_id']}, parent=upload_id, tx=tx)
        value['jobId'] = job['$id']
        store.update(row, value, state='pending', tx=tx)
        cleanup = store.owned('operator', value['cleanupJob'], 'job', tx=tx, lock=True)
        if cleanup['state'] != 'queued':
            raise HTTPException(409, 'Upload expired; start a new upload.')
        store.update(cleanup, payload(cleanup), state='cancelled', tx=tx)
    store.wake(job['$id'])
    return {'id': upload_id, 'jobId': job['$id'], 'state': 'pending'}


@router.get('')
def originals(account=Depends(current), store=Depends(get_store)):
    return [public_original(row) for row in store.owned_rows(account['$id'], 'original', state='ready')]


@router.get('/{content_id}/scans')
def processing_history(content_id: str, account=Depends(current), store=Depends(get_store)):
    store.owned(account['$id'], content_id, 'original')
    results = []
    for row in store.owned_rows(account['$id'], 'job', limit=100):
        value = payload(row)
        args = value['args']
        if content_id not in (args.get('originalId'), args.get('uploadId')):
            continue
        result = value.get('result') or {}
        results.append({'id': row['$id'], 'stage': row['state'], 'candidates': 1 if isinstance(result, dict) and result.get('caseId') else 0,
            'createdAt': row.get('$createdAt', value.get('createdAt', stamp())), 'error': value.get('error')})
    return results[-5:][::-1]


@router.get('/{content_id}/media')
def media(content_id: str, account=Depends(current), store=Depends(get_store)):
    row = store.owned(account['$id'], content_id, 'original')
    if row['state'] != 'ready':
        raise HTTPException(409, 'Original is still processing.')
    value = payload(row)
    data = Files(store.client).download(value['fileId'])
    return Response(data, media_type=value['contentType'],
                    headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})
