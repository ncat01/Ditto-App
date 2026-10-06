"""Expiring opaque sessions; only token digests are persisted."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database.db import SessionLocal
from app.models.tables import User, AuthSession

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(default="Creator", min_length=1, max_length=128)

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210000).hex()

def current_user(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    with SessionLocal() as db:
        session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(401, "Sign in required or session expired")
        return session.user_id

def issue(db, user):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc)+timedelta(days=7)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=expires))
    db.commit()
    return {"token":token,"expiresAt":expires,"user":{"id":user.id,"displayName":user.display_name,"email":user.email}}

@router.post("/signup", status_code=201)
def signup(body: Credentials, request: Request):
    from app.services.request_budget import consume
    consume("signup:" + (request.client.host if request.client else "unknown"), 200, 3600)
    with SessionLocal() as db:
        email = body.email.strip().lower()
        if db.scalar(select(User).where(User.email==email)):
            raise HTTPException(409,"Account already exists")
        salt = secrets.token_hex(32)
        user = User(id=uuid.uuid4().hex,display_name=body.display_name,handle="",email=email,salt=salt,password_hash=password_hash(body.password,salt))
        db.add(user)
        try: db.flush()
        except IntegrityError:
            db.rollback(); raise HTTPException(409,"Account already exists") from None
        from app.models.ledger import CreatorProfile
        db.add(CreatorProfile(user_id=user.id,display_name=user.display_name,handle="",preferences={}))
        return issue(db,user)

@router.post("/login")
def login(body: Credentials, request: Request):
    from app.services.request_budget import consume
    consume("login:" + (request.client.host if request.client else "unknown") + ":" + body.email.strip().lower(), 10, 900)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email==body.email.strip().lower()))
        computed = password_hash(body.password,user.salt if user and user.salt else "00"*32)
        if not user or not user.salt or not hmac.compare_digest(user.password_hash,computed):
            raise HTTPException(401,"Email or password is incorrect")
        return issue(db,user)

@router.get("/me")
def me(user_id=Depends(current_user)):
    with SessionLocal() as db:
        user=db.get(User,user_id)
        from app.models.account_security import AccountVerification
        return {"id":user.id,"email":user.email,"displayName":user.display_name,"emailVerified":bool(db.get(AccountVerification,user.id))}

@router.post("/logout")
def logout(request: Request, user_id=Depends(current_user)):
    token=request.headers.get("Authorization","").removeprefix("Bearer ")
    with SessionLocal() as db:
        session=db.get(AuthSession,hashlib.sha256(token.encode()).hexdigest())
        if session: db.delete(session); db.commit()
    return {"loggedOut":True}


class EmailRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)

class PasswordReset(TokenRequest):
    password: str = Field(min_length=10, max_length=128)

@router.post('/recovery')
def request_recovery(body: EmailRequest, request: Request):
    from app.services.account_email import require_email, send_account_email
    from app.services.request_budget import consume
    from app.models.account_security import AccountToken
    from sqlalchemy import delete
    require_email()
    consume('recovery:' + body.email.lower(), 3, 3600)
    consume('recovery-ip:' + (request.client.host if request.client else 'unknown'), 20, 3600)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
        if user:
            token = secrets.token_urlsafe(32)
            db.execute(delete(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == 'reset'))
            row = AccountToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, purpose='reset', expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=30))
            db.add(row); db.commit()
            send_account_email(user.email, 'reset', token)
    return {'message': 'If the account exists, a password reset email will arrive shortly.'}

@router.post('/reset-password')
def reset_password(body: PasswordReset):
    from app.models.account_security import AccountToken
    from sqlalchemy import delete
    with SessionLocal() as db:
        digest = hashlib.sha256(body.token.encode()).hexdigest()
        row = db.get(AccountToken, digest)
        if not row or row.purpose != 'reset' or row.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(400, 'Reset link expired or invalid. Request a new link.')
        user = db.get(User, row.user_id)
        removed = db.execute(delete(AccountToken).where(AccountToken.token_hash == digest))
        if removed.rowcount != 1: raise HTTPException(400, 'Reset link already used.')
        user.salt = secrets.token_hex(32)
        user.password_hash = password_hash(body.password, user.salt)
        db.execute(delete(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == "reset"))
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        db.commit()
    return {'message': 'Password updated. Sign in again on your devices.'}

@router.post('/request-verification')
def request_verification(user_id=Depends(current_user)):
    from app.services.account_email import require_email, send_account_email
    from app.services.request_budget import consume
    from app.models.account_security import AccountToken
    from sqlalchemy import delete
    require_email(); consume('verify:' + user_id, 3, 3600)
    with SessionLocal() as db:
        user = db.get(User, user_id)
        token = secrets.token_urlsafe(32)
        db.execute(delete(AccountToken).where(AccountToken.user_id == user_id, AccountToken.purpose == 'verify'))
        db.add(AccountToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user_id, purpose='verify', expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=30)))
        db.commit(); send_account_email(user.email, 'verify', token)
    return {'message': 'Verification email sent.'}

@router.post('/verify-email')
def verify_email(body: TokenRequest):
    from app.models.account_security import AccountToken, AccountVerification
    from sqlalchemy import delete
    with SessionLocal() as db:
        digest = hashlib.sha256(body.token.encode()).hexdigest()
        row = db.get(AccountToken, digest)
        if not row or row.purpose != 'verify' or row.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(400, 'Verification link expired or invalid.')
        if db.execute(delete(AccountToken).where(AccountToken.token_hash == digest)).rowcount != 1:
            raise HTTPException(400, 'Verification link already used.')
        if not db.get(AccountVerification, row.user_id):
            db.add(AccountVerification(user_id=row.user_id, verified_at=datetime.now(timezone.utc).replace(tzinfo=None)))
        db.commit()
    return {'verified': True}


class DeleteAccount(BaseModel):
    password: str = Field(min_length=10, max_length=128)

@router.post('/delete-account')
def delete_account(body: DeleteAccount, user_id=Depends(current_user)):
    from app.services.account_deletion import delete_records, purge_media
    from app.services.request_budget import consume
    consume('delete:' + user_id, 5, 900)
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user or not user.salt or not hmac.compare_digest(user.password_hash, password_hash(body.password, user.salt)):
            raise HTTPException(401, 'Password is incorrect.')
        delete_records(db, user_id)
    purge_media()
    return {'deleted': True, 'message': 'Account access and records removed. Private media deletion is queued if storage is temporarily unavailable.'}
