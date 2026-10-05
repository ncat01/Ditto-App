import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

def test_measured_media_clock_approval_and_resolution():
    with TestClient(app) as c:
        token=c.post('/api/auth/signup',json={'email':f'{uuid.uuid4().hex}@example.test','password':'secure-demo-123'}).json()['token']
        c.headers['Authorization']='Bearer '+token
        c.post('/api/demo/seed')
        cases=c.get('/api/cases').json()
        for suffix in ['cand_007','cand_008']:
            case=next(x for x in cases if x['candidate']['id'].endswith(suffix))
            assert case['recommendedAction']=='log_only'
            assert case['currentState']=='closed'
        simulated=next(x for x in cases if x['candidate']['id'].endswith('cand_005'))
        assert simulated['recommendedAction']=='review_request'
        assert 'SIMULATED' in simulated['verificationSummary']
        case=next(x for x in cases if x['candidate']['id'].endswith('cand_001'))
        cid=case['id']
        assert c.post(f'/api/cases/{cid}/approve',json={}).json()['currentState']=='awaiting_response'
        assert c.post('/api/demo/advance-clock').status_code==200
        assert c.get(f'/api/cases/{cid}').json()['currentState']=='escalated'
        assert c.post(f'/api/cases/{cid}/approve',json={}).json()['currentState']=='awaiting_response'
        assert c.post(f'/api/cases/{cid}/simulate-followup',json={'outcome':'attribution_added'}).json()['currentState']=='resolved'
        path=Path(__file__).resolve().parents[2]/'demo_data/videos/original_1.mp4'
        response=c.post('/api/content/upload',params={'title':'Real generated video'},files={'file':('original.mp4',path.read_bytes(),'video/mp4')})
        assert response.status_code==201,response.text
        media=response.json()
        assert len(media['perceptualHash'].split('|'))==5
        assert c.get(f"/api/content/{media['id']}/media").status_code==200
        assert c.post('/api/scan',json={'contentId':media['id']}).json()==[]
        assert c.post('/api/content/upload',files={'file':('bad.mp4',b'invalid','video/mp4')}).status_code==422
