"""Slow provider work executes privately, with durable state and owner checks."""
import hashlib
import json
import smtplib
import ssl
import tempfile
import uuid
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path
from fastapi import HTTPException
from cloud.client import CloudError
from cloud.files import CHUNK_BYTES, MAX_BYTES, Files
from cloud.store import digest, now, payload, stamp


def import_video(store, job):
    from cloud.oauth import reader
    from cloud.worker import measured
    from cloud.media_api import public_original
    uid = job['owner_id']
    args = payload(job)['args']
    api, instagram_id, connection = reader(store, uid)
    if args['mediaId'] not in {item.id for item in api.media(instagram_id, 25)}:
        raise ValueError('Media is not in the authorized account')
    item = api.media_item(args['mediaId'])
    identity = digest('instagram-import:' + uid + ':' + item.id)[:32]
    try:
        previous = store.owned(uid, identity, 'original')
        if previous['state'] == 'ready':
            return public_original(previous)
        if previous['state'] != 'error':
            raise ValueError('Import is already processing; check its job status')
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
    data = api.download_video(item)
    if len(data) > MAX_BYTES:
        raise ValueError('Instagram import exceeds 20 MB')
    file_id = uuid.uuid4().hex
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        active = store.owned(uid, connection['$id'], 'instagram', tx=tx, lock=True)
        if payload(active)['instagramId'] != instagram_id:
            raise ValueError('Instagram connection changed')
        cleanup = store.job('operator', 'delete_file', {'fileId': file_id}, tx=tx, delay=now() + timedelta(minutes=10))
        value = {'id': identity, 'title': item.caption[:256] or 'Instagram original', 'kind': 'video',
            'perceptualHash': '', 'paletteSeed': 1, 'publishedAt': item.timestamp or stamp(),
            'sourcePlatform': 'Instagram', 'sourceUrl': item.permalink, 'fileId': file_id,
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'contentType': 'video/mp4',
            'filename': file_id + '.mp4', 'jobId': job['$id'], 'offset': len(data)}
        try:
            old = store.owned(uid, identity, 'original', tx=tx, lock=True)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            old = None
        if old is None:
            store.create(uid, 'original', value, row_id=identity, state='importing', tx=tx)
        elif old['state'] == 'error':
            store.update(old, value, state='importing', tx=tx)
        else:
            raise ValueError('Another import already reserved this original')
    files = Files(store.client)
    for offset in range(0, len(data), CHUNK_BYTES):
        files.chunk(file_id, value['filename'], data[offset:offset + CHUNK_BYTES], offset, len(data))
    value['hashes'] = measured(data, 'video')
    value['perceptualHash'] = value['hashes'][0]
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        active = store.owned(uid, connection['$id'], 'instagram', tx=tx, lock=True)
        if payload(active)['instagramId'] != instagram_id:
            raise ValueError('Instagram connection changed')
        row = store.owned(uid, identity, 'original', tx=tx, lock=True)
        locked_cleanup = store.owned('operator', cleanup['$id'], 'job', tx=tx, lock=True)
        if locked_cleanup['state'] != 'queued':
            raise ValueError('Import expired')
        store.update(locked_cleanup, payload(locked_cleanup), state='cancelled', tx=tx)
        store.update(row, value, state='ready', tx=tx)
        store.activity(uid, 'ingestion', 'Instagram original imported', 'Private video imported from the authorized account.', tx=tx)
    return public_original({**row, 'payload': json.dumps(value)})


def outreach(store, job):
    from cloud.cases import history
    from app.services.account_email import require_email
    settings = require_email()
    if not settings.cloud_email_outreach_enabled:
        raise ValueError('Outreach disabled')
    uid, args = job['owner_id'], payload(job)['args']
    with store.client.transaction() as tx:
        account = store.guard(uid, tx)
        row = store.owned(uid, args['caseId'], 'case', tx=tx, lock=True)
        value = payload(row)
        if not account['verified'] or value['currentState'] in ('closed', 'resolved') or value.get('dispatchJob') != job['$id']:
            raise ValueError('Dispatch no longer authorized')
        if value.get('dispatchStatus') != 'queued':
            raise ValueError('Dispatch already attempted; never resend automatically')
        value['dispatchStatus'] = 'sending'
        store.update(row, value, tx=tx)
    message = EmailMessage()
    message['From'], message['To'], message['Reply-To'] = settings.smtp_from, args['recipient'], args['replyTo']
    message['Subject'] = args['subject'] or 'Content reuse enquiry'
    message['Message-ID'] = '<' + job['$id'] + '@ditto.local>'
    message.set_content(args['body'])
    try:
        with (smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=20)
              if settings.smtp_port == 465 else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)) as client:
            if settings.smtp_port == 587:
                client.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        with store.client.transaction() as tx:
            row = store.owned(uid, args['caseId'], 'case', tx=tx, lock=True)
            value = payload(row)
            value['dispatchStatus'] = 'unknown'
            store.update(row, value, tx=tx)
        raise ValueError('Delivery status unknown; do not resend automatically') from None
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, args['caseId'], 'case', tx=tx, lock=True)
        value = payload(row)
        value.update(dispatchStatus='accepted', lastActionAt=stamp())
        event = history(value, 'awaiting_response', 'Email accepted by SMTP', 'Acceptance is not delivery, receipt or a response.')
        store.create(uid, 'history', event, parent=row['$id'], tx=tx)
        if args['reminderDays']:
            due = now() + timedelta(days=args['reminderDays'])
            value['nextFollowUpAt'] = stamp(due)
            store.job(uid, 'followup_reminder', {'caseId': row['$id']}, parent=row['$id'], delay=due, tx=tx)
        store.update(row, value, tx=tx)
    return {'accepted': True, 'delivered': None}


def execute(store, job):
    from cloud.oauth import exchange, reader
    uid, value = job['owner_id'], payload(job)
    args, kind = value['args'], value['type']
    if kind == 'instagram_exchange':
        return exchange(store, job)
    if kind == 'instagram_posts':
        api, identity, _ = reader(store, uid)
        return [{'id': item.id, 'mediaType': item.media_type, 'caption': item.caption,
                 'permalink': item.permalink, 'timestamp': item.timestamp} for item in api.media(identity, 25)]
    if kind == 'instagram_import':
        return import_video(store, job)
    if kind == 'outreach_email':
        return outreach(store, job)
    if kind == 'followup_reminder':
        with store.client.transaction() as tx:
            store.guard(uid, tx)
            row = store.owned(uid, args['caseId'], 'case', tx=tx, lock=True)
            case = payload(row)
            if case['currentState'] == 'awaiting_response':
                store.activity(uid, 'follow_up', 'Review your outreach',
                    'Check for a response before deciding whether to contact the recipient again. No follow-up was sent.', row['$id'], tx)
                case['nextFollowUpAt'] = None
                case['followUpCount'] += 1
                store.update(row, case, tx=tx)
        return {'reminder': True, 'messageSent': False}
    if not args.get('consent'):
        raise ValueError('Provider consent required')
    if kind == 'ai_draft':
        from app.providers.gemini import generate_draft
        case = payload(store.owned(uid, args['caseId'], 'case'))
        return generate_draft({'title': case['contentTitle'], 'recipient': case['candidate']['accountHandle'],
                               'draft': case['draftBody'], 'action': case['recommendedAction']}).model_dump()
    if kind == 'web_search':
        from app.providers.web_search import query_images, search
        original = store.owned(uid, args['originalId'], 'original')
        if original['state'] != 'ready':
            raise ValueError('Original not ready')
        content = payload(original)
        data = Files(store.client).download(content['fileId'])
        with tempfile.TemporaryDirectory(prefix='ditto-search-') as directory:
            path = Path(directory) / 'media'
            path.write_bytes(data)
            results = search(query_images(path, content['kind']))
        notice = 'Unverified public-web leads; review sources. No result does not prove that reposts are absent.'
        with store.client.transaction() as tx:
            store.guard(uid, tx)
            store.create(uid, 'web_search', {'results': results, 'notice': notice}, parent=original['$id'], tx=tx)
        return {'results': results, 'notice': notice}
    raise ValueError('Unsupported provider job')
