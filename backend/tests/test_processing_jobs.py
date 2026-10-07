import io
import uuid
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.services.processing import process_next


def test_durable_comparison_creates_only_owned_review_case():
    with TestClient(app) as client:
        accounts = [client.post('/api/auth/signup', json={'email': uuid.uuid4().hex+'@job.invalid',
                    'password': 'test-processing-password'}).json() for _ in range(2)]
        owner, other = [{'Authorization': 'Bearer '+a['token']} for a in accounts]
        image = io.BytesIO()
        Image.new('RGB', (64,64), 'blue').save(image, format='PNG')
        content = client.post('/api/content/upload', headers=owner, params={'title': 'Original'},
                              files={'file': ('original.png',image.getvalue(),'image/png')}).json()
        assert client.get('/api/cases',headers=owner).json() == []
        response = client.post('/api/discovery/'+content['id']+'/compare-job', headers=owner,
                               files={'file': ('candidate.png',image.getvalue(),'image/png')})
        assert response.status_code == 202
        job = response.json()['jobId']
        assert client.get('/api/jobs/'+job,headers=other).status_code == 404
        assert process_next()
        result = client.get('/api/jobs/'+job,headers=owner).json()
        assert result['state'] == 'complete'
        assert result['result']['similarity'] == 1
        identity = result['result']['caseId']
        assert len(client.get('/api/cases',headers=owner).json()) == 1
        assert not process_next()
        assert client.get('/api/cases/'+identity+'/candidate-media',headers=owner).content == image.getvalue()
        assert client.get('/api/cases/'+identity+'/candidate-media',headers=other).status_code == 404
