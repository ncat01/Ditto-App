"""Verify a hosted API with temporary generated accounts and image; never print tokens."""
import argparse
import io
import secrets
import time
import httpx
from PIL import Image


def await_job(client, job_id, headers):
    for _ in range(240):
        response = client.get('/api/jobs/'+job_id, headers=headers)
        assert response.status_code == 200, 'Job receipt unavailable'
        result = response.json()
        if result['state'] in ('complete', 'error', 'unknown', 'cancelled'):
            assert result['state'] == 'complete', 'Job did not complete: '+str(result.get('error'))
            return result['result']
        time.sleep(1)
    raise AssertionError('Job is still processing; check its saved receipt before retrying')


def verify(origin, reverse_search=False):
    password = secrets.token_urlsafe(24)
    accounts = []
    with httpx.Client(base_url=origin, timeout=35) as client:
        try:
            response = client.get('/api/health')
            assert response.status_code == 200 and response.json()['database'] == 'connected'
            print('HTTPS database health: verified')
            for _ in range(2):
                response = client.post('/api/auth/signup', json={
                    'email':'deployment-'+secrets.token_hex(6)+'@example.test', 'password':password})
                assert response.status_code == 201, 'Signup failed'
                accounts.append(response.json())
            a,b = accounts
            owner = {'Authorization':'Bearer '+a['token']}
            other = {'Authorization':'Bearer '+b['token']}
            assert client.get('/api/cases', headers=owner).json() == []
            image = io.BytesIO()
            Image.new('RGB',(64,64),'blue').save(image,format='PNG')
            response = client.post('/api/content/upload', headers=owner,
                params={'title':'Deployment verification image'},
                files={'file':('verification.png',image.getvalue(),'image/png')})
            assert response.status_code == 201, 'Private upload failed: '+str(response.status_code)
            identity = response.json()['id']
            response = client.get('/api/content/'+identity+'/media', headers=owner)
            assert response.status_code == 200 and response.content == image.getvalue()
            assert client.get('/api/content/'+identity+'/media', headers=other).status_code == 404
            print('Empty signup, private upload/playback and cross-user isolation: verified')
            if reverse_search:
                status = client.get('/api/discovery/status', headers=owner).json()
                assert status['configured'] and status['provider'] == 'SerpApi Google Lens'
                endpoint = '/api/discovery/'+identity+'/web-search-job'
                assert client.post(endpoint, headers=owner, json={}).status_code == 422
                assert client.get(endpoint, headers=other).status_code == 404
                assert client.post(endpoint, headers=other,
                    json={'consent_to_search_provider':True}).status_code == 404
                request = {'consent_to_search_provider':True, 'request_id':secrets.token_hex(16)}
                response = client.post(endpoint, headers=owner,
                    json=request)
                assert response.status_code == 202, 'Live reverse search submission failed: '+str(response.status_code)
                search_job = response.json()['jobId']
                duplicate = client.post(endpoint, headers=owner, json=request)
                assert duplicate.status_code == 202 and duplicate.json()['jobId'] == search_job
                assert client.get('/api/jobs/'+search_job, headers=other).status_code == 404
                result = await_job(client, search_job, owner)
                assert result['provider'] == 'SerpApi Google Lens' and result['unitsUsed'] == 2
                assert all(row['verified'] is False for row in result['results'])
                restored = client.get(endpoint, headers=owner).json()
                assert restored['jobId'] == search_job and restored['state'] == 'complete'
                assert restored['result'] == result
                print('Live queued SerpApi search, restored results, consent, duplicate submission and isolation: verified')
                print('Generated-image leads returned:',len(result['results']))
            response = client.post('/api/discovery/'+identity+'/compare-job', headers=owner,
                files={'file':('candidate.png',image.getvalue(),'image/png')})
            assert response.status_code == 202
            job = response.json()['jobId']
            assert client.get('/api/jobs/'+job,headers=other).status_code == 404
            result = await_job(client, job, owner)
            assert result['similarity'] == 1
            case = result['caseId']
            assert len(client.get('/api/cases',headers=owner).json()) == 1
            assert client.get('/api/cases/'+case+'/candidate-media',headers=owner).content == image.getvalue()
            assert client.get('/api/cases/'+case+'/candidate-media',headers=other).status_code == 404
            print('Durable comparison job, real review case and private candidate: verified')
            response = client.post('/api/auth/refresh',json={'refreshToken':a['refreshToken']})
            assert response.status_code == 200
            a.update(response.json())
            assert client.get('/api/auth/me', headers=owner).status_code == 401
            print('Refresh-token rotation: verified')
        finally:
            for account in accounts:
                response = client.post('/api/auth/delete-account',
                    headers={'Authorization':'Bearer '+account['token']}, json={'password':password})
                assert response.status_code == 200, 'Temporary account cleanup requires attention'
            print('Temporary accounts and generated media: removed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin')
    parser.add_argument('--reverse-search', action='store_true',
        help='Send one generated image to the configured search provider; consumes two searches.')
    args = parser.parse_args()
    if not args.origin.startswith('https://'):
        raise SystemExit('HTTPS required')
    verify(args.origin,args.reverse_search)
