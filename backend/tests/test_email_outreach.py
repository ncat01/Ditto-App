import io
import smtplib
import uuid
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
from app.database.db import SessionLocal
from app.models.account_security import AccountVerification
from app.models.tables import _now
from app.services.processing import process_next


@pytest.mark.parametrize('uncertain',[False,True])
def test_exact_approval_and_uncertain_attempt_never_retries(monkeypatch,uncertain):
    settings=get_settings()
    for key,value in {'cloud_email_outreach_enabled':True,'smtp_host':'smtp.invalid','smtp_port':465,
                      'smtp_from':'operator@example.test','smtp_user':'operator','smtp_password':'test-only'}.items():
        monkeypatch.setattr(settings,key,value)
    messages=[]
    class SMTP:
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def login(self,*args): pass
        def send_message(self,message):
            messages.append(message)
            if uncertain: raise smtplib.SMTPServerDisconnected('test interruption')
            return {}
    monkeypatch.setattr(smtplib,'SMTP_SSL',SMTP)
    with TestClient(app) as client:
        account=client.post('/api/auth/signup',json={'email':uuid.uuid4().hex+'@outreach.invalid',
                            'password':'test-outreach-password'}).json()
        headers={'Authorization':'Bearer '+account['token']}
        image=io.BytesIO();Image.new('RGB',(64,64),'blue').save(image,format='PNG')
        original=client.post('/api/content/upload',headers=headers,params={'title':'Original'},
                              files={'file':('original.png',image.getvalue(),'image/png')}).json()
        response=client.post('/api/discovery/'+original['id']+'/compare-job',headers=headers,
                              files={'file':('candidate.png',image.getvalue(),'image/png')})
        assert process_next()
        case=client.get('/api/jobs/'+response.json()['jobId'],headers=headers).json()['result']['caseId']
        body={'requestId':uuid.uuid4().hex,'recipient':'reviewed@example.test','editedBody':'Exact approved body',
              'evidenceReviewed':True,'recipientConfirmed':True,'reminderDays':0}
        path='/api/cases/'+case+'/approve'
        assert client.post(path,headers=headers,json=body).status_code==403
        with SessionLocal() as db:
            db.add(AccountVerification(user_id=account['user']['id'],verified_at=_now()));db.commit()
        assert client.post(path,headers=headers,json={**body,'evidenceReviewed':False}).status_code==422
        receipt=client.post(path,headers=headers,json=body)
        assert receipt.status_code==202
        assert client.post(path,headers=headers,json=body).json()==receipt.json()
        assert client.post(path,headers=headers,json={**body,'requestId':uuid.uuid4().hex}).status_code==409
        assert process_next()
        state=client.get('/api/jobs/'+receipt.json()['dispatchJob'],headers=headers).json()['state']
        assert state==('unknown' if uncertain else 'complete')
        assert not process_next()
        assert len(messages)==1 and messages[0]['To']==body['recipient']
        assert messages[0].get_content().strip()==body['editedBody']
