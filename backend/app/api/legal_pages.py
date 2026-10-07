import html
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.config import get_settings
router=APIRouter()

@router.get('/{page}', response_class=HTMLResponse)
def legal_page(page:str):
    if page not in ('privacy','terms','data-deletion'):raise HTTPException(404)
    support=html.escape(get_settings().support_email)
    texts={
        'privacy': ('Ditto privacy information', "<p>Ditto stores your account email, password hash, sessions, uploaded originals, fingerprints, case evidence, drafts and decisions. Connected Instagram tokens are encrypted on the server and used to access the media you authorize.</p><p>When you request Gemini drafting, the title, recipient and draft context are sent to Google. The app asks you to confirm this first. Free-tier inputs may be used by Google to improve its products. Video files are not sent for this drafting feature. If you separately choose reverse web search, the image or five sampled video frames are sent to SerpApi for Google Lens search, after a confirmation prompt. SerpApi may retain search uploads and parameters under its provider policies; Ditto does not promise immediate deletion from the search provider.</p><p>Data is used to provide account access, manage originals and cases, and secure the service. Disconnect Instagram in Profile to remove its stored token; revoke the grant separately in Instagram Apps and websites. Account deletion removes active records and queues private media cleanup. Operator-managed backups may retain copies until their configured retention period expires.</p><p>Contact support to request access, corrections or help with deletion.</p>"),
        'terms': ('Using Ditto', "<p>Upload content you own or have permission to process. Do not use Ditto to harass others, send deceptive claims or access accounts without consent.</p><p>Similarity is evidence to review, not proof of ownership, infringement or permission. You are responsible for checking the original, candidate, recipient and message before deciding what to do.</p><p>Ditto compares submitted media and can return unverified public web-image leads when search is configured. It does not search all Instagram posts. Email enquiries require your explicit approval and a verified account; delivery depends on the configured provider. Connected services depend on availability and granted permissions.</p><p>Fees and any commercial subscription terms must be presented before purchase; this version has no paid checkout.</p>"),
        'data-deletion': ('Delete your data', "<p>Open Ditto Profile ? Account security ? Delete account, or use the link below. Confirm your email and password. Active account records, cases, sessions and stored Instagram connection are removed; private media cleanup is retried if storage is temporarily unavailable. This does not remove your Instagram posts. Backup copies are retained until the operator?s backup retention period expires.</p><p><a href='/account/delete'>Delete account</a></p>")}
    title,body=texts[page]
    owner=html.escape(get_settings().operator_name)
    if owner: body="<p>Operator: "+owner+"</p>"+body
    return HTMLResponse('<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title></head><body><main><h1>'+title+'</h1>'+body+'<p>Support: <a href="mailto:'+support+'">'+support+'</a></p></main></body></html>',headers={'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'",'Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
