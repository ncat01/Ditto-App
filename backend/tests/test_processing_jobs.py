import io
import uuid
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.services.processing import process_next


@pytest.mark.parametrize('kind', ['image', 'video'])
def test_durable_comparison_creates_only_owned_review_case(kind, tmp_path):
    with TestClient(app) as client:
        accounts = [client.post('/api/auth/signup', json={'email': uuid.uuid4().hex+'@job.invalid',
                    'password': 'test-processing-password'}).json() for _ in range(2)]
        owner, other = [{'Authorization': 'Bearer '+a['token']} for a in accounts]
        if kind == 'image':
            image = io.BytesIO()
            Image.new('RGB', (64,64), 'blue').save(image, format='PNG')
            data, extension, mime = image.getvalue(), 'png', 'image/png'
        else:
            import cv2
            import numpy as np
            path = tmp_path / 'original.mp4'
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64,64))
            assert writer.isOpened(), 'Test video encoder must be available'
            try:
                for index in range(10):
                    frame = np.zeros((64,64,3), dtype=np.uint8)
                    frame[:, :, 0] = np.arange(64, dtype=np.uint8) * 4
                    frame[index:index+20, 10:40, 1] = 200
                    writer.write(frame)
            finally:
                writer.release()
            data, extension, mime = path.read_bytes(), 'mp4', 'video/mp4'
        content = client.post('/api/content/upload', headers=owner, params={'title': 'Original'},
                              files={'file': ('original.'+extension,data,mime)}).json()
        assert client.get('/api/cases',headers=owner).json() == []
        response = client.post('/api/discovery/'+content['id']+'/compare-job', headers=owner,
                               files={'file': ('candidate.'+extension,data,mime)})
        assert response.status_code == 202
        job = response.json()['jobId']
        assert client.get('/api/jobs/'+job,headers=other).status_code == 404
        assert process_next()
        result = client.get('/api/jobs/'+job,headers=owner).json()
        assert result['state'] == 'complete'
        assert result['result']['similarity'] == 1
        identity = result['result']['caseId']
        cases = client.get('/api/cases',headers=owner).json()
        assert len(cases) == 1
        assert cases[0]['candidate']['mediaKind'] == kind
        assert client.get('/api/cases/'+identity,headers=owner).json()['candidate']['mediaKind'] == kind
        assert not process_next()
        assert client.get('/api/content/'+content['id']+'/media',headers=owner).content == data
        assert client.get('/api/cases/'+identity+'/candidate-media',headers=owner).content == data
        assert client.get('/api/cases/'+identity+'/candidate-media',headers=other).status_code == 404
