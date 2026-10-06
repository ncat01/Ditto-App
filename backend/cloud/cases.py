"""Human-reviewed cases and explicit email dispatch; no automatic legal claims."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.config import get_settings
from cloud.auth import current
from cloud.client import CloudError, RECORDS
from cloud.deps import get_store
from cloud.store import digest, now, payload, stamp

router = APIRouter(prefix='/api')
TERMINAL = {'closed', 'resolved'}


def compared_case(original, candidate, score, identity):
    first, second = payload(original), payload(candidate)
    when = stamp()
    return {'id': identity, 'contentId': original['$id'], 'contentTitle': first['title'], 'contentPaletteSeed': 1,
        'candidate': {'id': candidate['$id'], 'mediaKind': second.get('kind', 'video'), 'platform': 'Submitted evidence', 'accountName': 'Not identified',
            'accountHandle': '', 'sourceUrl': second.get('sourceUrl', ''), 'caption': '', 'followerCount': 0,
            'monetized': False, 'hashSimilarity': score, 'visualSimilarity': score, 'captionSimilarity': 0,
            'faceSimilarity': 0, 'postedAt': when, 'transformNote': 'Posting date, account identity, permission and attribution are unverified.',
            'paletteSeed': 1, 'discoveredAt': when, 'attributionPresent': False, 'permissionGranted': False},
        'classification': None, 'confidence': None, 'severity': None,
        'verificationSummary': 'Visual similarity only; a person must review the original, source and permission.',
        'verificationSignals': [], 'evidenceSummary': 'Measured pHash comparison of user-submitted media.',
        'verificationEngine': 'Measured pHash; no infringement classifier',
        'recommendedAction': 'review_request', 'actionReasoning': 'Review evidence before contacting a recipient.',
        'actionFactors': [], 'draftSubject': 'Content reuse enquiry', 'draftBody': '', 'tone': 'professional',
        'planEngine': 'Human review', 'currentState': 'pending_approval', 'escalationLevel': 0,
        'followUpCount': 0, 'createdAt': when, 'updatedAt': when, 'nextFollowUpAt': None,
        'lastActionAt': None, 'history': [], 'dispatchStatus': None}


def history(value, new_state, action, note):
    when = stamp()
    event = {'timestamp': when, 'previousState': value['currentState'], 'newState': new_state,
             'agent': 'human', 'action': action, 'reasoning': note}
    value['history'] = (value.get('history', []) + [event])[-100:]
    value.update(currentState=new_state, updatedAt=when)
    return event


@router.get('/cases')
def cases(account=Depends(current), store=Depends(get_store)):
    return [payload(row) for row in store.owned_rows(account['$id'], 'case')]


@router.get('/cases/{case_id}')
def case(case_id: str, account=Depends(current), store=Depends(get_store)):
    return payload(store.owned(account['$id'], case_id, 'case'))


@router.get('/cases/{case_id}/candidate-media')
def candidate_media(case_id: str, account=Depends(current), store=Depends(get_store)):
    from cloud.files import Files
    from fastapi.responses import Response
    case = payload(store.owned(account['$id'], case_id, 'case'))
    row = store.owned(account['$id'], case['candidate']['id'], 'candidate')
    if row['state'] != 'ready':
        raise HTTPException(409, 'Candidate is still processing.')
    value = payload(row)
    return Response(Files(store.client).download(value['fileId']), media_type=value['contentType'],
        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.get('/dashboard/stats')
def stats(account=Depends(current), store=Depends(get_store)):
    rows = [payload(row) for row in store.owned_rows(account['$id'], 'case')]
    count = lambda state: sum(r['currentState'] == state for r in rows)
    return {'contentMonitored': sum(1 for _ in store.owned_rows(account['$id'], 'original', state='ready')),
        'openCases': sum(r['currentState'] not in TERMINAL for r in rows), 'awaitingResponse': count('awaiting_response'),
        'resolved': count('resolved'), 'escalated': count('escalated'), 'pendingApproval': count('pending_approval'),
        'totalCases': len(rows), 'verifiedReposts': 0, 'falsePositives': 0, 'averageConfidence': 0,
        'resolutionRate': count('resolved') / len(rows) if rows else 0}


class Note(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


def close_case(store, uid, case_id, state, note):
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, case_id, 'case', tx=tx, lock=True)
        value = payload(row)
        if value['currentState'] in TERMINAL:
            return value
        if value.get('dispatchStatus') == 'sending':
            raise HTTPException(409, 'Delivery is in progress. Check its status before closing.')
        if value.get('dispatchJob'):
            job = store.owned(uid, value['dispatchJob'], 'job', tx=tx, lock=True)
            if job['state'] == 'queued':
                store.update(job, payload(job), state='cancelled', tx=tx)
        event = history(value, state, 'Case closed by creator', note or 'Creator closed this case; no outcome inferred.')
        value['nextFollowUpAt'] = None
        store.create(uid, 'history', event, parent=case_id, tx=tx)
        store.update(row, value, tx=tx)
    return value


@router.post('/cases/{case_id}/reject')
def reject(case_id: str, body: Note, account=Depends(current), store=Depends(get_store)):
    return close_case(store, account['$id'], case_id, 'closed', body.note)


@router.post('/cases/{case_id}/resolve')
def resolve(case_id: str, body: Note, account=Depends(current), store=Depends(get_store)):
    return close_case(store, account['$id'], case_id, 'resolved', body.note)


class Edit(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    tone: str = Field(default='professional', pattern='^(professional|firm|neutral)$')


@router.post('/cases/{case_id}/edit-action')
def edit(case_id: str, body: Edit, account=Depends(current), store=Depends(get_store)):
    with store.client.transaction() as tx:
        store.guard(account['$id'], tx)
        row = store.owned(account['$id'], case_id, 'case', tx=tx, lock=True)
        value = payload(row)
        if value['currentState'] in TERMINAL or value.get('dispatchStatus') in ('queued', 'sending'):
            raise HTTPException(409, 'This case cannot be edited while closed or sending.')
        value.update(draftBody=body.body, tone=body.tone, updatedAt=stamp())
        store.update(row, value, tx=tx)
    return value


class EmailApproval(BaseModel):
    recipient: str = Field(max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    editedBody: str = Field(min_length=1, max_length=4000)
    requestId: str = Field(pattern=r'^[a-f0-9]{32}$')
    evidenceReviewed: bool
    recipientConfirmed: bool
    reminderDays: int = Field(default=0, ge=0, le=30)


@router.post('/cases/{case_id}/approve')
def approve(case_id: str, body: EmailApproval, account=Depends(current), store=Depends(get_store)):
    from app.services.account_email import require_email
    require_email()
    if not get_settings().cloud_email_outreach_enabled:
        raise HTTPException(503, 'Email outreach is not enabled by the operator.')
    if not account['verified'] or not body.evidenceReviewed or not body.recipientConfirmed:
        raise HTTPException(409, 'Verify your email and confirm the evidence and recipient before sending.')
    if not body.editedBody.strip():
        raise HTTPException(422, 'Review and write a message before sending.')
    uid = account['$id']
    identity = digest('email:' + uid + ':' + body.requestId)[:32]
    with store.client.transaction() as tx:
        store.guard(uid, tx)
        row = store.owned(uid, case_id, 'case', tx=tx, lock=True)
        value = payload(row)
        try:
            existing = store.owned(uid, identity, 'job', tx=tx)
            args = payload(existing)['args']
            if args['caseId'] != case_id or args['recipient'] != body.recipient or args['body'] != body.editedBody:
                raise HTTPException(409, 'Request identifier was already used for a different message.')
            return value
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        if value['currentState'] != 'pending_approval' or value.get('dispatchStatus') in ('queued', 'sending', 'unknown'):
            raise HTTPException(409, 'This case is not ready for a new approved message.')
        store.consume('outreach:' + uid, 3, 86400)
        store.consume('outreach:global', 20, 86400)
        job = store.job(uid, 'outreach_email', {'caseId': case_id, 'recipient': body.recipient,
            'body': body.editedBody, 'subject': value['draftSubject'], 'reminderDays': body.reminderDays,
            'replyTo': account['email']}, row_id=identity, parent=case_id, tx=tx)
        value.update(draftBody=body.editedBody, dispatchStatus='queued', dispatchJob=identity, updatedAt=stamp())
        store.update(row, value, tx=tx)
        store.activity(uid, 'human', 'Email approved', 'Recipient and evidence confirmed; delivery queued.', case_id, tx)
    store.wake(job['$id'])
    return value
