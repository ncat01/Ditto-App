"""Browser-bound one-time Instagram authorization for a signed-in Ditto user."""
import secrets,html
from urllib.parse import urlencode
from datetime import timedelta
from fastapi import APIRouter,Depends,Request,HTTPException
from fastapi.responses import RedirectResponse,HTMLResponse
from sqlalchemy import delete,update,select
from sqlalchemy.exc import IntegrityError
from app.database.db import get_db,SessionLocal
from app.models.tables import AuthSession
from app.models.integrations import InstagramOAuthAttempt,InstagramConnection
from app.services.instagram_oauth import now,digest,cipher,require_oauth,callback_url,exchange_code
from app.config import get_settings
from app.providers.instagram import InstagramUnavailable

router=APIRouter(prefix='/api/integrations/instagram',tags=['Instagram connection'])
COOKIE='ditto_ig_browser'

def browser_page(message,status=200):
    response=HTMLResponse('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ditto Instagram connection</title></head><body style="font:18px system-ui;background:#fffaf2;color:#343034;padding:40px"><h1>Ditto</h1><p>'+html.escape(message)+'</p><p>Return to Ditto. Your connection status updates automatically.</p></body></html>',status_code=status,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"})
    response.delete_cookie(COOKIE,path='/api/integrations/instagram');return response

@router.post('/connect')
def connect(request:Request,db=Depends(get_db)):
    base=require_oauth()
    state=secrets.token_urlsafe(32)
    db.execute(delete(InstagramOAuthAttempt).where(InstagramOAuthAttempt.user_id==db.info['user_id']))
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    db.add(InstagramOAuthAttempt(state_hash=digest(state),user_id=db.info['user_id'],session_hash=digest(token),cookie_hash=None,expires_at=now()+timedelta(minutes=10)))
    db.commit()
    return {'authorizationUrl':base+'/api/integrations/instagram/begin?'+urlencode({'ticket':state})}

@router.get('/begin')
def begin(ticket:str):
    require_oauth()
    with SessionLocal() as db:
        attempt=db.get(InstagramOAuthAttempt,digest(ticket))
        session=db.get(AuthSession,attempt.session_hash) if attempt else None
        if not attempt or attempt.expires_at<=now() or not session or session.expires_at<=now():raise HTTPException(400,'Connection link expired. Start again in Ditto.')
        cookie=secrets.token_urlsafe(32)
        changed=db.execute(update(InstagramOAuthAttempt).where(InstagramOAuthAttempt.state_hash==digest(ticket),InstagramOAuthAttempt.cookie_hash.is_(None)).values(cookie_hash=digest(cookie)))
        if changed.rowcount!=1:raise HTTPException(400,'Connection link already used. Start again in Ditto.')
        db.commit()
    url='https://www.instagram.com/oauth/authorize?'+urlencode({'client_id':get_settings().instagram_app_id,'redirect_uri':callback_url(),'response_type':'code','scope':'instagram_business_basic','state':ticket,'enable_fb_login':'0','force_authentication':'1'})
    response=RedirectResponse(url,status_code=302,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    response.set_cookie(COOKIE,cookie,max_age=600,secure=True,httponly=True,samesite='lax',path='/api/integrations/instagram')
    return response

@router.get('/callback')
def callback(request:Request,state:str='',code:str='',error:str=''):
    if not state or len(state)>256 or len(code)>4096:return browser_page('Connection link is invalid. Please start again in Ditto.',400)
    with SessionLocal() as db:
        attempt=db.get(InstagramOAuthAttempt,digest(state))
        session=db.get(AuthSession,attempt.session_hash) if attempt else None
        cookie=request.cookies.get(COOKIE,'')
        if not attempt or not cookie or not attempt.cookie_hash or attempt.cookie_hash!=digest(cookie) or attempt.expires_at<=now() or not session or session.expires_at<=now():
            return browser_page('Connection expired or browser verification failed. Please start again in Ditto.',400)
        uid=attempt.user_id
        removed=db.execute(delete(InstagramOAuthAttempt).where(InstagramOAuthAttempt.state_hash==digest(state),InstagramOAuthAttempt.cookie_hash==digest(cookie)))
        db.commit()
        if removed.rowcount!=1:return browser_page('Connection link already used. Please start again.',400)
        if error or not code:return browser_page('Instagram connection cancelled. You can continue with manual uploads.')
        try:
            token,expires,profile=exchange_code(code)
            # A logged-out session cannot finish connecting after the network round trip.
            active=db.get(AuthSession,session.token_hash,populate_existing=True)
            if not active or active.expires_at<=now():return browser_page('Your Ditto session ended. Sign in and try again.',400)
            other=db.scalar(select(InstagramConnection).where(InstagramConnection.instagram_user_id==profile.user_id,InstagramConnection.user_id!=uid))
            if other:return browser_page('This Instagram account is already connected to another Ditto account.',409)
            existing=db.get(InstagramConnection,uid)
            if existing:db.delete(existing);db.flush()
            db.add(InstagramConnection(user_id=uid,instagram_user_id=profile.user_id,username=profile.username,encrypted_token=cipher().encrypt(token.encode()).decode(),expires_at=expires,refreshed_at=now()))
            db.commit()
        except InstagramUnavailable as exc:return browser_page(str(exc),503)
        except IntegrityError:
            db.rollback();return browser_page('This Instagram account is already connected. Please reconnect from its owner account.',409)
    return browser_page('Instagram connected successfully. Your credentials stay on the server.')

@router.get('/status')
def status(db=Depends(get_db)):
    connection=db.get(InstagramConnection,db.info['user_id'])
    configured=True
    try:require_oauth()
    except HTTPException:configured=False
    return {'configured':configured,'connected':bool(connection and connection.expires_at>now()),'username':connection.username if connection else None,'expiresAt':connection.expires_at if connection else None}

@router.post('/disconnect')
def disconnect(db=Depends(get_db)):
    connection=db.get(InstagramConnection,db.info['user_id'])
    if connection:db.delete(connection)
    db.execute(delete(InstagramOAuthAttempt).where(InstagramOAuthAttempt.user_id==db.info['user_id']))
    db.commit()
    return {'disconnected':True,'note':'Ditto removed the stored connection. You can also remove Ditto from Instagram Apps and Websites.'}
