"""Existing Ditto opaque-session contract backed exclusively by Appwrite."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet
from app.config import get_settings
from cloud.client import ACCOUNTS, RECORDS, CloudError, query
from cloud.deps import get_store
from cloud.store import digest, now, payload, stamp

router = APIRouter(prefix='/api/auth')


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(default='Creator', min_length=1, max_length=128)


class EmailRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordReset(TokenRequest):
    password: str = Field(min_length=10, max_length=128)


class PasswordRequest(BaseModel):
    password: str = Field(min_length=10, max_length=128)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 210000).hex()


def expires(row):
    try:
        return datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
    except (KeyError, TypeError, ValueError):
        raise CloudError() from None


def secure_cipher():
    try:
        return Fernet(get_settings().token_encryption_key.get_secret_value().encode())
    except (ValueError, TypeError):
        raise HTTPException(503, 'Secure token storage is unavailable.') from None


def account_by_email(store, email):
    rows = list(store.client.rows(ACCOUNTS, [query('equal', 'email', [email])], limit=1))
    if rows and rows[0].get('email') != email:
        raise CloudError()
    return rows[0] if rows else None


def user_out(account):
    return {'id': account['$id'], 'email': account['email'],
            'displayName': account['display_name'], 'emailVerified': account['verified']}


def issue(store, account, tx=None):
    token = secrets.token_urlsafe(32)
    until = now() + timedelta(days=7)
    store.create(account['$id'], 'session', {'digest': digest(token), 'epoch': account['auth_epoch']},
                 row_id=digest(token)[:32], expires=until, tx=tx)
    return {'token': token, 'expiresAt': stamp(until), 'user': user_out(account)}


def current(request: Request, store=Depends(get_store)):
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer ') or not 32 <= len(header[7:]) <= 256:
        raise HTTPException(401, 'Sign in required or session expired')
    token = header[7:]
    try:
        row = store.client.get(RECORDS, digest(token)[:32])
        session = payload(row)
        if row.get('kind') != 'session' or row.get('state') != 'active' or expires(row) <= now():
            raise HTTPException(401, 'Sign in required or session expired')
        if not hmac.compare_digest(session.get('digest', ''), digest(token)):
            raise HTTPException(401, 'Sign in required or session expired')
        account = store.client.get(ACCOUNTS, row['owner_id'])
        if account['closing'] or session.get('epoch') != account['auth_epoch']:
            raise HTTPException(401, 'Sign in required or session expired')
        return account
    except CloudError as exc:
        if exc.status == 404:
            raise HTTPException(401, 'Sign in required or session expired') from None
        raise


@router.post('/signup', status_code=201)
def signup(body: Credentials, store=Depends(get_store)):
    store.consume('signup:global', 200, 3600)
    salt = secrets.token_hex(32)
    uid = uuid.uuid4().hex
    account = {'email': body.email.strip().lower(), 'display_name': body.display_name.strip() or 'Creator',
               'salt': salt, 'password_hash': password_hash(body.password, salt),
               'verified': False, 'closing': False, 'auth_epoch': 0, 'reset_generation': 0, 'revision': 0}
    try:
        with store.client.transaction() as tx:
            account = store.client.create(ACCOUNTS, uid, account, tx)
            result = issue(store, account, tx)
        return result
    except CloudError as exc:
        if exc.status == 409:
            raise HTTPException(409, 'Account already exists') from None
        raise


@router.post('/login')
def login(body: Credentials, store=Depends(get_store)):
    email = body.email.strip().lower()
    store.consume('login:global', 1000, 3600)
    store.consume('login:' + email, 10, 900)
    account = account_by_email(store, email)
    computed = password_hash(body.password, account['salt'] if account else '00' * 32)
    if not account or account['closing'] or not hmac.compare_digest(account['password_hash'], computed):
        raise HTTPException(401, 'Email or password is incorrect')
    with store.client.transaction() as tx:
        fresh = store.guard(account['$id'], tx)
        if not hmac.compare_digest(fresh['password_hash'], computed):
            raise HTTPException(401, 'Email or password is incorrect')
        return_value = issue(store, fresh, tx)
    return return_value


@router.get('/me')
def me(account=Depends(current)):
    return user_out(account)


@router.post('/logout')
def logout(request: Request, account=Depends(current), store=Depends(get_store)):
    identity = digest(request.headers['Authorization'][7:])[:32]
    store.client.delete(RECORDS, identity)
    return {'loggedOut': True}


def enqueue_token(store, account, purpose):
    from app.services.account_email import require_email
    require_email()
    token = secrets.token_urlsafe(32)
    until = now() + timedelta(minutes=30)
    with store.client.transaction() as tx:
        account = store.guard(account['$id'], tx)
        generation = account['reset_generation']
        if purpose == 'reset':
            generation = store.client.increment(ACCOUNTS, account['$id'], 'reset_generation', tx)['reset_generation']
        store.create(account['$id'], purpose, {'digest': digest(token), 'generation': generation},
                     row_id=digest(token)[:32], expires=until, tx=tx)
        job = store.job(account['$id'], 'account_email', {'recipient': account['email'], 'purpose': purpose,
            'sealedToken': secure_cipher().encrypt(token.encode()).decode(), 'expiresAt': stamp(until)}, tx=tx)
    store.wake(job['$id'])


@router.post('/recovery')
def recovery(body: EmailRequest, store=Depends(get_store)):
    from app.services.account_email import require_email
    require_email()
    email = body.email.strip().lower()
    store.consume('recovery:' + email, 3, 3600)
    store.consume('recovery:global', 100, 3600)
    account = account_by_email(store, email)
    if account and not account['closing']:
        try:
            enqueue_token(store, account, 'reset')
        except (CloudError, HTTPException):
            # The same response is returned for an absent account or failed queue.
            # No raw token or recipient is logged.
            pass
    return {'message': 'If the account exists, a password reset email will arrive shortly.'}


@router.post('/request-verification')
def request_verification(account=Depends(current), store=Depends(get_store)):
    if account['verified']:
        return {'message': 'Your email is already verified.'}
    store.consume('verify:' + account['$id'], 3, 3600)
    enqueue_token(store, account, 'verify')
    return {'message': 'Verification email queued. Check your inbox shortly.'}


def consume_token(store, token, purpose, password=None):
    identity = digest(token)[:32]
    try:
        initial = store.client.get(RECORDS, identity)
        with store.client.transaction() as tx:
            account = store.guard(initial['owner_id'], tx)
            row = store.owned(account['$id'], identity, purpose, tx=tx, lock=True)
            data = payload(row)
            if row['state'] != 'active' or expires(row) <= now() or not hmac.compare_digest(data['digest'], digest(token)):
                raise HTTPException(400, 'Link expired or invalid. Request a new link.')
            if purpose == 'reset':
                if data.get('generation') != account['reset_generation']:
                    raise HTTPException(400, 'Link expired or invalid. Request a new link.')
                salt = secrets.token_hex(32)
                store.client.increment(ACCOUNTS, account['$id'], 'auth_epoch', tx)
                store.client.patch(ACCOUNTS, account['$id'], {'salt': salt, 'password_hash': password_hash(password, salt)}, tx)
            else:
                store.client.patch(ACCOUNTS, account['$id'], {'verified': True}, tx)
            store.client.delete(RECORDS, identity, tx)
    except (CloudError, HTTPException) as exc:
        if isinstance(exc, CloudError) and exc.status not in (404, 409):
            raise
        if isinstance(exc, HTTPException) and exc.status_code not in (400, 401, 404):
            raise
        raise HTTPException(400, 'Link expired or invalid. Request a new link.') from None


@router.post('/reset-password')
def reset_password(body: PasswordReset, store=Depends(get_store)):
    consume_token(store, body.token, 'reset', body.password)
    return {'message': 'Password updated. Sign in again on your devices.'}


@router.post('/verify-email')
def verify_email(body: TokenRequest, store=Depends(get_store)):
    consume_token(store, body.token, 'verify')
    return {'verified': True}


@router.post('/delete-account')
def delete_account(body: PasswordRequest, account=Depends(current), store=Depends(get_store)):
    store.consume('delete:' + account['$id'], 5, 900)
    if not hmac.compare_digest(account['password_hash'], password_hash(body.password, account['salt'])):
        raise HTTPException(401, 'Password is incorrect.')
    with store.client.transaction() as tx:
        fresh = store.guard(account['$id'], tx)
        if not hmac.compare_digest(fresh['password_hash'], account['password_hash']):
            raise HTTPException(401, 'Password changed. Sign in again.')
        store.client.patch(ACCOUNTS, account['$id'], {'closing': True}, tx)
        store.client.increment(ACCOUNTS, account['$id'], 'auth_epoch', tx)
        job = store.job('operator', 'delete_account', {'owner': account['$id']}, tx=tx)
    store.wake(job['$id'])
    return {'deleted': True, 'message': 'Account access revoked. Records and private files are queued for deletion.'}
