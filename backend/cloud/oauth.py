"""Per-user Instagram browser authorization and asynchronous own-media imports."""
import secrets
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlsplit
import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from app.config import get_settings
from app.providers.instagram import InstagramReader, InstagramUnavailable
from cloud.auth import current, expires, secure_cipher
from cloud.client import ACCOUNTS, RECORDS, CloudError
from cloud.deps import get_store
from cloud.store import digest, now, payload, stamp

router = APIRouter(prefix='/api/integrations/instagram')


def origin():
    url = get_settings().public_base_url.rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise HTTPException(503, 'Instagram sign-in is not configured.')
    if not get_settings().instagram_app_secret.get_secret_value():
        raise HTTPException(503, 'Instagram sign-in is not configured.')
    secure_cipher()
    return url


def connection_id(owner):
    return digest('instagram-connection:' + owner)[:32]


def valid_attempt(store, ticket, cookie=None, tx=None, lock=False):
    try:
        row = store.client.get(RECORDS, digest(ticket)[:32], tx)
        session = store.client.get(RECORDS, payload(row)['session'], tx)
        account = store.client.get(ACCOUNTS, row['owner_id'], tx)
    except CloudError as exc:
        if exc.status != 404:
            raise
        raise HTTPException(400, 'Sign-in expired. Start again from Ditto.') from None
    if row['kind'] != 'oauth' or expires(row) <= now():
        raise HTTPException(400, 'Sign-in expired. Start again from Ditto.')
    value = payload(row)
    if session['kind'] != 'session' or session['state'] != 'active' or session['owner_id'] != row['owner_id'] or expires(session) <= now() or account['closing'] or payload(session)['epoch'] != account['auth_epoch']:
        raise HTTPException(400, 'Sign-in expired. Start again from Ditto.')
    if cookie is not None and value.get('cookie') != digest(cookie):
        raise HTTPException(400, 'Sign-in browser changed. Start again from Ditto.')
    return store.owned(row['owner_id'], row['$id'], 'oauth', tx=tx, lock=True) if lock else row


@router.get('/status')
def status(account=Depends(current), store=Depends(get_store)):
    try:
        origin()
        configured = True
    except HTTPException:
        configured = False
    try:
        row = store.owned(account['$id'], connection_id(account['$id']), 'instagram')
        value = payload(row)
        return {'configured': configured, 'connected': expires(row) > now(), 'username': value['username']}
    except (HTTPException, CloudError) as exc:
        if getattr(exc, 'status_code', getattr(exc, 'status', 0)) != 404:
            raise
        return {'configured': configured, 'connected': False}


@router.post('/connect')
def connect(request: Request, account=Depends(current), store=Depends(get_store)):
    base = origin()
    store.consume('oauth:' + account['$id'], 10, 3600)
    ticket = secrets.token_urlsafe(32)
    with store.client.transaction() as tx:
        store.guard(account['$id'], tx)
        store.create(account['$id'], 'oauth', {'session': digest(request.headers['Authorization'][7:])[:32]},
                     row_id=digest(ticket)[:32], state='issued', expires=now() + timedelta(minutes=10), tx=tx)
    return {'authorizationUrl': base + '/api/integrations/instagram/begin?' + urlencode({'ticket': ticket})}


@router.get('/begin')
def begin(ticket: str, store=Depends(get_store)):
    origin()
    if not 32 <= len(ticket) <= 256:
        raise HTTPException(400, 'Invalid sign-in request.')
    cookie = secrets.token_urlsafe(32)
    with store.client.transaction() as tx:
        row = valid_attempt(store, ticket, tx=tx, lock=True)
        store.guard(row['owner_id'], tx)
        if row['state'] != 'issued':
            raise HTTPException(400, 'Sign-in already started. Start again from Ditto.')
        store.update(row, {**payload(row), 'cookie': digest(cookie)}, state='browser', tx=tx)
    response = RedirectResponse('https://www.instagram.com/oauth/authorize?' + urlencode({
        'client_id': get_settings().instagram_app_id, 'redirect_uri': origin() + '/api/integrations/instagram/callback',
        'response_type': 'code', 'scope': 'instagram_business_basic', 'state': ticket,
        'enable_fb_login': '0', 'force_authentication': '1'}), status_code=302)
    response.set_cookie('ditto_instagram_browser', cookie, max_age=600, secure=True, httponly=True,
                        samesite='lax', path='/api/integrations/instagram')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('/callback')
def callback(request: Request, state: str = '', code: str = '', error: str = '', store=Depends(get_store)):
    cookie = request.cookies.get('ditto_instagram_browser', '')
    if not 32 <= len(state) <= 256 or not cookie:
        raise HTTPException(400, 'Sign-in expired. Start again from Ditto.')
    with store.client.transaction() as tx:
        row = valid_attempt(store, state, cookie, tx=tx, lock=True)
        store.guard(row['owner_id'], tx)
        if row['state'] != 'browser':
            raise HTTPException(400, 'Sign-in already consumed. Start again from Ditto.')
        value = payload(row)
        job = None
        if not error and code and len(code) <= 4096:
            job = store.job(row['owner_id'], 'instagram_exchange', {'attempt': row['$id'],
                'code': secure_cipher().encrypt(code.removesuffix('#_').encode()).decode()}, tx=tx)
        store.update(row, value, state='pending' if job else 'cancelled', tx=tx)
    if job:
        store.wake(job['$id'])
    response = HTMLResponse('<!doctype html><html lang="en"><title>Ditto Instagram connection</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><h1>Return to Ditto</h1><p>' +
        ('Connection is processing. Refresh Instagram connection in Ditto.' if job else 'Authorization was cancelled. You can reconnect from Ditto.') + '</p></html>',
        headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'"})
    response.delete_cookie('ditto_instagram_browser', path='/api/integrations/instagram', secure=True, httponly=True, samesite='lax')
    return response


@router.post('/disconnect')
def disconnect(account=Depends(current), store=Depends(get_store)):
    uid = account['$id']
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        try:
            row = store.owned(uid, connection_id(uid), 'instagram', tx=tx, lock=True)
            store.client.delete(RECORDS, payload(row)['claimId'], tx)
            store.client.delete(RECORDS, row['$id'], tx)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        attempts = list(store.owned_rows(uid, 'oauth'))
        for attempt in attempts:
            locked = store.owned(uid, attempt['$id'], 'oauth', tx=tx, lock=True)
            store.update(locked, payload(locked), state='cancelled', tx=tx)
    return {'connected': False}


def enqueue(store, uid, kind, args):
    store.consume(kind + ':' + uid, 10, 3600)
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        job = store.job(uid, kind, args, tx=tx)
    store.wake(job['$id'])
    return {'jobId': job['$id'], 'state': 'queued'}


@router.get('/posts', status_code=202)
def posts(account=Depends(current), store=Depends(get_store)):
    return enqueue(store, account['$id'], 'instagram_posts', {})


class ImportRequest(BaseModel):
    media_id: str = Field(pattern=r'^\d{1,64}$')


@router.post('/import', status_code=202)
def import_post(body: ImportRequest, account=Depends(current), store=Depends(get_store)):
    return enqueue(store, account['$id'], 'instagram_import', {'mediaId': body.media_id})


@router.post('/import/{media_id}', status_code=202)
def import_by_id(media_id: str, account=Depends(current), store=Depends(get_store)):
    body = ImportRequest(media_id=media_id)
    return enqueue(store, account['$id'], 'instagram_import', {'mediaId': body.media_id})


def exchange(store, job):
    uid = job['owner_id']
    args = payload(job)['args']
    attempt = store.owned(uid, args['attempt'], 'oauth')
    if attempt['state'] != 'pending' or expires(attempt) <= now():
        raise ValueError('Authorization no longer pending')
    code = secure_cipher().decrypt(args['code'].encode()).decode()
    settings = get_settings()
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        short = client.post('https://api.instagram.com/oauth/access_token', data={
            'client_id': settings.instagram_app_id, 'client_secret': settings.instagram_app_secret.get_secret_value(),
            'grant_type': 'authorization_code', 'redirect_uri': origin() + '/api/integrations/instagram/callback', 'code': code})
        if short.status_code != 200:
            raise ValueError('Authorization denied')
        long = client.get('https://graph.instagram.com/access_token', params={
            'grant_type': 'ig_exchange_token', 'client_secret': settings.instagram_app_secret.get_secret_value(),
            'access_token': short.json()['access_token']})
        if long.status_code != 200:
            raise ValueError('Authorization denied')
        result = long.json()
        token, seconds = result['access_token'], int(result['expires_in'])
        if not isinstance(token, str) or not token or not 0 < seconds <= 366 * 86400:
            raise ValueError('Invalid provider token')
    profile = InstagramReader(token).profile()
    claim_id = digest('instagram-owner:' + profile.user_id)[:32]
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        attempt = store.owned(uid, args['attempt'], 'oauth', tx=tx, lock=True)
        session = store.owned(uid, payload(attempt)['session'], 'session', tx=tx, lock=True)
        account = store.client.get(ACCOUNTS, uid, tx)
        if attempt['state'] != 'pending' or expires(session) <= now() or payload(session)['epoch'] != account['auth_epoch']:
            raise ValueError('Authorization revoked')
        try:
            claim = store.client.get(RECORDS, claim_id, tx)
            if claim['owner_id'] != uid or claim['kind'] != 'instagram_claim':
                raise ValueError('Instagram account already linked')
        except CloudError as exc:
            if exc.status != 404:
                raise
            store.create(uid, 'instagram_claim', {}, row_id=claim_id, tx=tx)
        identity = connection_id(uid)
        value = {'instagramId': profile.user_id, 'username': profile.username, 'claimId': claim_id,
                 'token': secure_cipher().encrypt(token.encode()).decode(), 'refreshedAt': stamp()}
        try:
            previous = store.owned(uid, identity, 'instagram', tx=tx, lock=True)
            old_claim = payload(previous)['claimId']
            if old_claim != claim_id:
                store.client.delete(RECORDS, old_claim, tx)
            store.update(previous, value, tx=tx, expires=now() + timedelta(seconds=seconds))
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            store.create(uid, 'instagram', value, row_id=identity, expires=now() + timedelta(seconds=seconds), tx=tx)
        store.update(attempt, payload(attempt), state='complete', tx=tx)
    return {'connected': True, 'username': profile.username}


def reader(store, uid):
    row = store.owned(uid, connection_id(uid), 'instagram')
    if expires(row) <= now():
        raise ValueError('Instagram connection expired')
    value = payload(row)
    token = secure_cipher().decrypt(value['token'].encode()).decode()
    refreshed = datetime.fromisoformat(value['refreshedAt'].replace('Z', '+00:00'))
    if expires(row) < now() + timedelta(days=14) and refreshed < now() - timedelta(days=1):
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            response = client.get('https://graph.instagram.com/refresh_access_token',
                params={'grant_type': 'ig_refresh_token', 'access_token': token})
        if response.status_code != 200:
            raise ValueError('Instagram refresh unavailable')
        result = response.json()
        fresh, ttl = result['access_token'], int(result['expires_in'])
        if not isinstance(fresh, str) or not fresh or not 0 < ttl <= 366 * 86400:
            raise ValueError('Invalid refreshed token')
        with store.client.transaction() as tx:
            store.guard(uid, tx)
            locked = store.owned(uid, row['$id'], 'instagram', tx=tx, lock=True)
            if payload(locked)['token'] != value['token']:
                raise ValueError('Instagram connection changed; retry')
            value.update(token=secure_cipher().encrypt(fresh.encode()).decode(), refreshedAt=stamp())
            store.update(locked, value, expires=now() + timedelta(seconds=ttl), tx=tx)
        token = fresh
    return InstagramReader(token), value['instagramId'], row
