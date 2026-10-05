"""Expiring opaque sessions; only token digests are persisted."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
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
def signup(body: Credentials):
    with SessionLocal() as db:
        email = body.email.strip().lower()
        if db.scalar(select(User).where(User.email==email)):
            raise HTTPException(409,"Account already exists")
        salt = secrets.token_hex(32)
        user = User(id=uuid.uuid4().hex,display_name=body.display_name,handle="",email=email,salt=salt,password_hash=password_hash(body.password,salt))
        db.add(user); db.flush()
        from app.models.ledger import CreatorProfile
        db.add(CreatorProfile(user_id=user.id,display_name=user.display_name,handle="",preferences={}))
        return issue(db,user)

@router.post("/login")
def login(body: Credentials):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email==body.email.strip().lower()))
        if not user or not user.salt or not hmac.compare_digest(user.password_hash,password_hash(body.password,user.salt)):
            raise HTTPException(401,"Email or password is incorrect")
        return issue(db,user)

@router.get("/me")
def me(user_id=Depends(current_user)):
    with SessionLocal() as db:
        user=db.get(User,user_id)
        return {"id":user.id,"email":user.email,"displayName":user.display_name}

@router.post("/logout")
def logout(request: Request, user_id=Depends(current_user)):
    token=request.headers.get("Authorization","").removeprefix("Bearer ")
    with SessionLocal() as db:
        session=db.get(AuthSession,hashlib.sha256(token.encode()).hexdigest())
        if session: db.delete(session); db.commit()
    return {"loggedOut":True}
