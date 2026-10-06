"""Explicit provider consent and durable, quota-limited requests."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.config import get_settings
from cloud.auth import current
from cloud.deps import get_store
from cloud.oauth import enqueue
from cloud.store import payload

router = APIRouter(prefix='/api')


class Consent(BaseModel):
    consent_to_google: bool = False


@router.get('/discovery/status')
def status(account=Depends(current)):
    return {'configured': bool(get_settings().google_cloud_api_key.get_secret_value()),
            'scope': 'Public web-image leads only; no platform-wide Instagram search.',
            'outreach': get_settings().cloud_email_outreach_enabled}


@router.post('/discovery/{content_id}/web-search', status_code=202)
def search(content_id: str, body: Consent, account=Depends(current), store=Depends(get_store)):
    if not body.consent_to_google:
        raise HTTPException(409, 'Confirm sending the image or five sampled video frames to Google.')
    if not get_settings().google_cloud_api_key.get_secret_value():
        raise HTTPException(503, 'Web search is not configured.')
    row = store.owned(account['$id'], content_id, 'original')
    if row['state'] != 'ready':
        raise HTTPException(409, 'Wait for your original to finish processing.')
    units = 5 if payload(row)['kind'] == 'video' else 1
    date = datetime.now(timezone.utc)
    month = date.strftime('%Y-%m')
    next_month = datetime(date.year + (date.month == 12), date.month % 12 + 1, 1, tzinfo=timezone.utc)
    store.consume('vision', get_settings().vision_monthly_unit_limit, 31 * 86400, weight=units,
                  period=(month, int(next_month.timestamp())))
    return enqueue(store, account['$id'], 'web_search', {'originalId': content_id, 'consent': True})


@router.post('/cases/{case_id}/ai-draft', status_code=202)
def draft(case_id: str, body: Consent, account=Depends(current), store=Depends(get_store)):
    if not body.consent_to_google:
        raise HTTPException(409, 'Confirm sharing the draft context with Google.')
    if not get_settings().gemini_api_key.get_secret_value():
        raise HTTPException(503, 'AI drafting is not configured.')
    store.owned(account['$id'], case_id, 'case')
    return enqueue(store, account['$id'], 'ai_draft', {'caseId': case_id, 'consent': True})
