"""Exact approved SMTP messages. An uncertain attempt is never retried automatically."""
import hashlib
import re
import smtplib
import ssl
import uuid
from datetime import timedelta
from email.message import EmailMessage
from fastapi import HTTPException
from sqlalchemy import select
from app.config import get_settings
from app.models.tables import Case, Content, User, CaseHistory, _now
from app.models.jobs import ProcessingJob
from app.models.ledger import Approval
from app.models.account_security import AccountVerification


def enqueue(db,case_id,body):
    user_id = db.info['user_id']
    case = db.scalar(select(Case).join(Content).where(Case.id==case_id,Content.user_id==user_id)
                     .with_for_update())
    if not case:
        raise HTTPException(404,'Case unavailable')
    if not re.fullmatch(r'[a-zA-Z0-9]{1,36}',body.requestId):
        raise HTTPException(422,'A valid request receipt is required')
    identity = hashlib.sha256((user_id+':'+case_id+':'+body.requestId).encode()).hexdigest()[:32]
    existing = db.get(ProcessingJob,identity)
    recipient = body.recipient.strip()
    text = (body.editedBody or '').strip()
    if existing:
        if existing.payload.get('recipient')!=recipient or existing.payload.get('body')!=text:
            raise HTTPException(409,'This receipt belongs to a different approved message')
        return {'dispatchJob':identity}
    if not body.evidenceReviewed or not body.recipientConfirmed:
        raise HTTPException(422,'Confirm the evidence and exact recipient before sending')
    if not re.fullmatch(r'[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+',recipient) or len(recipient)>254:
        raise HTTPException(422,'A valid recipient email is required')
    if not text or len(text)>4000 or body.reminderDays not in (0,7):
        raise HTTPException(422,'Review a message of 1–4000 characters and valid reminder preference')
    if case.current_state != 'pending_approval':
        raise HTTPException(409,'This case is not awaiting approval; check its delivery status')
    receipts=db.scalars(select(ProcessingJob).where(ProcessingJob.user_id==user_id)).all()
    if any(j.payload.get('kind')=='email' and j.payload.get('caseId')==case_id and
           j.state in ('queued','unknown','complete') for j in receipts):
        raise HTTPException(409,'An approved email already has a receipt. Check its status before sending again.')
    if not db.get(AccountVerification,user_id):
        raise HTTPException(403,'Verify your account email before sending outreach')
    user = db.get(User,user_id)
    db.add(Approval(id=uuid.uuid4().hex,case_id=case.id,user_id=user_id,decision='approved',
                    recipient=recipient,channel='email',body=text))
    db.add(ProcessingJob(id=identity,user_id=user_id,state='queued',payload={
        'kind':'email','caseId':case.id,'recipient':recipient,'body':text,
        'subject':'Content credit inquiry','replyTo':user.email,'reminderDays':body.reminderDays}))
    db.commit()
    return {'dispatchJob':identity}


def deliver(db,job):
    settings = get_settings()
    args = dict(job.payload)
    identity = job.id
    if not settings.outreach_is_live:
        job.state='error';job.error='Email sender unavailable. No attempt was made.'
        case=db.get(Case,args['caseId'])
        if case: case.current_state='pending_approval'
        db.commit()
        return
    # Commit this receipt before touching SMTP. A process crash leaves "unknown",
    # which the queue never selects again, including after a restart.
    job.state='unknown';job.error='Delivery status is unconfirmed. Do not resend automatically.'
    db.commit()
    message=EmailMessage()
    message['From']=settings.smtp_from
    message['To']=args['recipient']
    message['Reply-To']=args['replyTo']
    message['Subject']=args['subject']
    message['Message-ID']='<'+identity+'@ditto.local>'
    message.set_content(args['body'])
    try:
        connection = (smtplib.SMTP_SSL(settings.smtp_host,settings.smtp_port,
                       context=ssl.create_default_context(),timeout=20) if settings.smtp_port==465
                      else smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=20))
        with connection as client:
            if settings.smtp_port==587: client.starttls(context=ssl.create_default_context())
            client.login(settings.smtp_user,settings.smtp_password)
            refused=client.send_message(message)
            if refused: return
    except (OSError,smtplib.SMTPException):
        return
    job=db.get(ProcessingJob,identity)
    if not job: return
    job.state='complete';job.error=None
    job.result={'status':'accepted','notice':'Mail service accepted the email; delivery and response are unconfirmed.'}
    case=db.get(Case,args['caseId'])
    if case:
        case.current_state='awaiting_response';case.last_action_at=_now()
        case.next_followup_at=(_now()+timedelta(days=7)) if args['reminderDays']==7 else None
        db.add(CaseHistory(case_id=case.id,previous_state='pending_approval',new_state='awaiting_response',
            agent='human',action='Approved email accepted by SMTP',
            reasoning='Exact approved recipient and message submitted. Delivery and reply remain unconfirmed.'))
    db.commit()
