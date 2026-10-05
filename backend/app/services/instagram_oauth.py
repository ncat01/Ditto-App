"""Instagram OAuth helpers. Provider credentials never enter API responses."""
import hashlib,os
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit
import httpx
from cryptography.fernet import Fernet,InvalidToken
from fastapi import HTTPException
from sqlalchemy import select
from app.config import get_settings
from app.models.integrations import InstagramConnection
from app.providers.instagram import InstagramReader,InstagramUnavailable

KEY_FILE=Path(__file__).resolve().parents[3]/'.ditto-data/token-encryption.key'

def now():return datetime.now(timezone.utc).replace(tzinfo=None)
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def cipher():
    settings=get_settings()
    key=settings.token_encryption_key.get_secret_value()
    if not key and settings.demo_mode and KEY_FILE.is_file():key=KEY_FILE.read_text().strip()
    try:return Fernet(key.encode())
    except (ValueError,TypeError):raise HTTPException(503,'Instagram secure storage is not configured.') from None

def base_url():
    settings=get_settings();base=settings.public_base_url.rstrip('/')
    u=urlsplit(base)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:
        raise HTTPException(503,'Instagram sign-in is not configured by the service operator yet.')
    return base

def require_oauth():
    if not get_settings().instagram_app_secret.get_secret_value():raise HTTPException(503,'Instagram sign-in is not configured by the service operator yet.')
    cipher();return base_url()

def callback_url():return base_url()+'/api/integrations/instagram/callback'

def exchange_code(code):
    settings=get_settings()
    secret=settings.instagram_app_secret.get_secret_value()
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as c:
            short=c.post('https://api.instagram.com/oauth/access_token',data={
                'client_id':settings.instagram_app_id,'client_secret':secret,'grant_type':'authorization_code',
                'redirect_uri':callback_url(),'code':code})
            if short.status_code!=200:raise InstagramUnavailable('Instagram did not authorize the connection. Please reconnect.')
            token=short.json()['access_token']
            long=c.get('https://graph.instagram.com/access_token',params={
                'grant_type':'ig_exchange_token','client_secret':secret,'access_token':token})
            if long.status_code!=200:raise InstagramUnavailable('Instagram could not issue an extended connection. Please reconnect.')
            result=long.json();token=result['access_token'];seconds=int(result['expires_in'])
            if not isinstance(token,str) or not token or not 0<seconds<=366*86400:raise ValueError()
        profile=InstagramReader(token).profile()
        return token,now()+timedelta(seconds=seconds),profile
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        raise InstagramUnavailable('Instagram connection could not be completed. Please reconnect.') from None

def connected_reader(db,user_id):
    connection=db.get(InstagramConnection,user_id)
    if not connection:raise HTTPException(409,'Connect your Instagram account first.')
    if connection.expires_at<=now():raise HTTPException(409,'Instagram connection expired. Reconnect your account.')
    try:token=cipher().decrypt(connection.encrypted_token.encode()).decode()
    except (InvalidToken,UnicodeError):raise HTTPException(503,'Instagram secure storage unavailable. Contact support.') from None
    # Refresh only when needed and at least 24h after issuance/previous refresh.
    if connection.expires_at<now()+timedelta(days=14) and connection.refreshed_at<now()-timedelta(days=1):
        try:
            with httpx.Client(timeout=30,follow_redirects=False) as client:
                response=client.get('https://graph.instagram.com/refresh_access_token',params={'grant_type':'ig_refresh_token','access_token':token})
            if response.status_code!=200:raise ValueError()
            result=response.json();fresh=result['access_token'];ttl=int(result['expires_in'])
            if not isinstance(fresh,str) or not fresh or not 0<ttl<=366*86400:raise ValueError()
            connection.encrypted_token=cipher().encrypt(fresh.encode()).decode()
            connection.expires_at=now()+timedelta(seconds=ttl);connection.refreshed_at=now();db.commit();token=fresh
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            raise HTTPException(503,'Instagram could not refresh the connection. Try again or reconnect.') from None
    return InstagramReader(token),connection.instagram_user_id
