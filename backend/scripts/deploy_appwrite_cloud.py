"""One private runner: plan, stage disabled Functions, then verify live contracts.

Never purchases a plan, publishes Functions, migrates data or exposes a credential.
Use a temporary server key in APPWRITE_DEPLOY_KEY; the runtime uses dynamic keys.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.client import ACCOUNTS, BUDGETS, RECORDS, DATABASE, Client, CloudError, ident, query
from cloud.files import Files, BUCKET
from cloud.schema import TABLES, table_creation
from cloud.store import encode, stamp
from scripts.package_appwrite_cloud import package

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = 'python-3.12'
REPORT = ROOT / '.ditto-data/cloud-deployment.json'
RUNTIME_SCOPES = ['databases.read', 'tables.read', 'rows.read', 'rows.write', 'files.read', 'files.write', 'executions.write']
MANAGEMENT_SCOPES = ['databases.read', 'tables.read', 'tables.write', 'columns.read', 'columns.write', 'indexes.read',
                     'indexes.write', 'rows.read', 'rows.write', 'buckets.read', 'files.read', 'files.write',
                     'functions.read', 'functions.write', 'executions.read', 'executions.write', 'rules.read']
SECRET_NAMES = ('INSTAGRAM_APP_SECRET', 'TOKEN_ENCRYPTION_KEY', 'SMTP_PASSWORD', 'GOOGLE_CLOUD_API_KEY', 'GEMINI_API_KEY')
PUBLIC_NAMES = ('PUBLIC_BASE_URL', 'INSTAGRAM_APP_ID', 'META_API_VERSION', 'SMTP_HOST', 'SMTP_PORT',
                'SMTP_USER', 'SMTP_FROM', 'SUPPORT_EMAIL', 'OPERATOR_NAME', 'VISION_MONTHLY_UNIT_LIMIT')


def configuration():
    # Only explicitly allowlisted values can leave the runner. Never deploy the
    # management key, legacy account-wide Meta token or an entire environment.
    values = {name: os.environ[name] for name in SECRET_NAMES + PUBLIC_NAMES if os.getenv(name)}
    values.update(DITTO_DEMO_MODE='false', APPWRITE_ENDPOINT='https://sgp.cloud.appwrite.io/v1',
                  APPWRITE_PROJECT_ID='6ac46d45002b91afdd73', CLOUD_EMAIL_OUTREACH_ENABLED='false',
                  SUPPORT_EMAIL=values.get('SUPPORT_EMAIL', 'svarsha.t@gmail.com'),
                  OPERATOR_NAME=values.get('OPERATOR_NAME', 'Svarsha T'))
    return values


def plan():
    return {'action': 'plan only', 'project': '6ac46d45002b91afdd73', 'database': DATABASE,
            'functions': ['ditto-api', 'ditto-worker'], 'runtime': 'python-3.12',
            'managementKeyPresent': bool(os.getenv('APPWRITE_DEPLOY_KEY')),
            'managementScopes': MANAGEMENT_SCOPES, 'runtimeScopes': RUNTIME_SCOPES,
            'privateConfigurationPresent': {name: bool(os.getenv(name)) for name in SECRET_NAMES + PUBLIC_NAMES},
            'stage': 'Create isolated schema and disabled private Functions; upload allowlisted code; run live probes.',
            'publicLaunchPerformed': False, 'billingChanges': False,
            'remainingLaunchInputs': ['stable HTTPS origin and Meta redirect/review', 'SMTP inbox verification',
                'encrypted backup and restore drill', 'frozen-source migration review', 'private Android signing and device checks']}


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    os.chmod(temporary, 0o600)
    temporary.replace(REPORT)


def schema(client, sleep=time.sleep):
    for spec in TABLES:
        print('Schema table: ' + spec['tableId'], flush=True)
        path = f'/tablesdb/{DATABASE}/tables/' + spec['tableId']
        try:
            existing = client.request('GET', path)
        except CloudError as exc:
            if exc.status != 404:
                raise
            client.request('POST', f'/tablesdb/{DATABASE}/tables', json={**table_creation(spec), 'permissions': [], 'rowSecurity': True, 'enabled': True})
            existing = None
        for attempt in range(60):
            existing = client.request('GET', path)
            if existing.get('$permissions') != [] or existing.get('rowSecurity') is not True:
                print('Schema access check: ' + json.dumps({'privatePermissions': existing.get('$permissions') == [], 'rowSecurity': existing.get('rowSecurity') is True}), flush=True)
                raise ValueError('Candidate schema has unexpected permissions')
            columns = {row['key']: row for row in existing.get('columns', [])}
            indexes = {row['key']: row for row in existing.get('indexes', [])}
            if attempt == 0:
                for expected in spec['columns']:
                    if expected.get('encrypt') and expected['key'] not in columns:
                        body = {k: v for k, v in expected.items() if k != 'type'}
                        client.request('POST', path + '/columns/' + expected['type'], json=body)
                for expected in spec['indexes']:
                    if expected['key'] not in indexes:
                        client.request('POST', path + '/indexes', json=expected)
            if any(row.get('status') in ('failed', 'stuck') for row in list(columns.values()) + list(indexes.values())):
                print('Schema build has failed or stuck definitions; inspect this table in Appwrite.', flush=True)
                raise ValueError('Schema build failed')
            if all(columns.get(c['key'], {}).get('status') == 'available' for c in spec['columns']) and all(indexes.get(i['key'], {}).get('status') == 'available' for i in spec['indexes']):
                break
            sleep(2)
        else:
            print('Schema definitions still pending after waiting.', flush=True)
            raise ValueError('Schema build pending; rerun later')
        for expected in spec['columns']:
            actual = columns[expected['key']]
            if any(actual.get(k) != v for k, v in expected.items()):
                print('Column definition mismatch: ' + json.dumps({'column': expected['key'], 'expected': expected, 'actual': {k: actual.get(k) for k in expected}}), flush=True)
                raise ValueError('Existing candidate schema differs; not repaired destructively')
        for expected in spec['indexes']:
            if any(indexes[expected['key']].get(k) != v for k, v in expected.items()):
                print('Index definition mismatch: ' + json.dumps({'index': expected['key'], 'expected': expected, 'actual': {k: indexes[expected['key']].get(k) for k in expected}}), flush=True)
                raise ValueError('Existing candidate index differs')


def private_storage(client):
    value = client.request('GET', '/storage/buckets/' + BUCKET)
    print('Storage checks: ' + json.dumps({
        'privatePermissions': value.get('$permissions') == [],
        'fileSecurityEnabled': value.get('fileSecurity') is True,
        'encryptionEnabled': value.get('encryption') is True,
        'maximumBytes': value.get('maximumFileSize') if isinstance(value.get('maximumFileSize'), int) else None,
        'missingExtensions': sorted({'jpg', 'png', 'webp', 'mp4', 'mov'} - set(value.get('allowedFileExtensions', [])))
    }), flush=True)
    if (value.get('$permissions') != [] or value.get('fileSecurity') is not True or
            value.get('encryption') is not True or not 0 < value.get('maximumFileSize', 0) <= 20_000_000):
        raise ValueError('Storage privacy/encryption/20 MB limit must be verified first')
    if not {'jpg', 'png', 'webp', 'mp4', 'mov'}.issubset(set(value.get('allowedFileExtensions', []))):
        raise ValueError('Required media extensions are unavailable')


def configure_storage(client):
    """Apply approved private-media policy together; preserve other bucket flags."""
    path = '/storage/buckets/' + BUCKET
    current = client.request('GET', path)
    if current.get('$permissions') != []:
        raise ValueError('Unexpected bucket access; review before changing permissions')
    body = {key: current[key] for key in ('name', 'enabled', 'compression', 'antivirus', 'transformations') if key in current}
    body.update(permissions=[], fileSecurity=True, encryption=True, maximumFileSize=20_000_000,
                allowedFileExtensions=['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov'])
    client.request('PUT', path, json=body)
    private_storage(client)


def definition(identity):
    return {'name': 'Ditto API' if identity == 'ditto-api' else 'Ditto private worker',
            'execute': [], 'events': [], 'schedule': '', 'timeout': 30 if identity == 'ditto-api' else 300, 'enabled': False,
            'logging': False, 'entrypoint': 'cloud/main_api.py' if identity == 'ditto-api' else 'cloud/main_worker.py',
            'commands': 'pip install --no-cache-dir pip==26.2.1 -r requirements.txt', 'scopes': RUNTIME_SCOPES}


def select_media_runtime(client):
    global RUNTIME
    available = client.request('GET', '/functions/runtimes').get('runtimes', [])
    ids = {item.get('$id', item.get('key', item.get('id'))) for item in available}
    for candidate in ('python-ml-3.12', 'python-ml-3.11'):
        if candidate in ids:
            RUNTIME = candidate
            print('Selected available media runtime: ' + RUNTIME, flush=True)
            return
    print('No supported Python ML runtime returned by this project; staging stopped before another native compilation.', flush=True)
    raise ValueError('Compatible media runtime unavailable')


def generated_origin(client):
    rules = client.request('GET', '/proxy/rules', params=[('queries[]', query('equal', 'deploymentResourceId', ['ditto-api']))]).get('rules', [])
    import re
    for rule in rules:
        domain = rule.get('domain', '')
        if rule.get('deploymentResourceId') == 'ditto-api' and re.fullmatch(r'[a-zA-Z0-9-]+\.sgp\.appwrite\.run', domain):
            return 'https://' + domain
    return None


def function(client, identity):
    value = definition(identity)
    try:
        current = client.request('GET', '/functions/' + identity)
        # Never disable/replace an already published service while staging.
        if current.get('enabled') or current.get('execute') or current.get('schedule'):
            raise ValueError('Function is already enabled; use a reviewed rolling deployment')
        if current.get('runtime') not in ('python-3.12', 'python-ml-3.12', 'python-ml-3.11') or current.get('name') != value['name']:
            raise ValueError('Existing Function runtime differs')
        client.request('PUT', '/functions/' + identity, json={**value, 'runtime': RUNTIME})
    except CloudError as exc:
        if exc.status != 404:
            raise
        client.request('POST', '/functions', json={'functionId': identity, 'runtime': RUNTIME, **value})
    existing = client.request('GET', '/functions/' + identity + '/variables').get('variables', [])
    variables = {item['key']: item['$id'] for item in existing}
    forbidden = {'APPWRITE_API_KEY', 'APPWRITE_DEPLOY_KEY', 'APPWRITE_SETUP_KEY', 'META_ACCESS_TOKEN'}
    if forbidden.intersection(variables):
        raise ValueError('Long-lived credential found in Function variables; review privately')
    for name, value in configuration().items():
        body = {'key': name, 'value': value, 'secret': name in SECRET_NAMES or name == 'SMTP_USER'}
        if name in variables:
            client.request('PUT', '/functions/' + identity + '/variables/' + ident(variables[name]), json=body)
        else:
            client.request('POST', '/functions/' + identity + '/variables', json={**body, 'variableId': hashlib.sha256(name.encode()).hexdigest()[:32]})


def build(client, identity, archive, sleep=time.sleep):
    spec = definition(identity)
    with archive.open('rb') as code:
        result = client.request('POST', '/functions/' + identity + '/deployments',
            data={'activate': 'false', 'entrypoint': spec['entrypoint'], 'commands': spec['commands']},
            files={'code': (archive.name, code, 'application/gzip')})
    deployment = ident(result['$id'])
    print('Function deployment ID: ' + deployment, flush=True)
    previous_status = None
    for attempt in range(180):
        result = client.request('GET', '/functions/' + identity + '/deployments/' + deployment)
        status = result.get('status')
        if status != previous_status:
            print('Function build status: ' + (status if status in ('waiting', 'processing', 'building', 'ready', 'failed', 'canceled', 'queued') else 'unknown'), flush=True)
            previous_status = status
        if result.get('status') == 'ready':
            client.request('PATCH', '/functions/' + identity + '/deployment', json={'deploymentId': deployment})
            return deployment
        if result.get('status') in ('failed', 'canceled'):
            print('Build failed. Open Appwrite Functions > ' + identity + ' > Deployments > Build logs. Review the package error; do not share credentials or full logs.', flush=True)
            raise ValueError('Function build failed; inspect private Console without copying logs into chat')
        sleep(3)
    print('Build is still pending after nine minutes. Inspect the existing deployment before creating another build.', flush=True)
    raise ValueError('Function build still pending; inspect Console before retrying')


def execute(client, path, method='GET', body=None, headers=None):
    result = client.request('POST', '/functions/ditto-api/executions', json={
        'path': path, 'method': method, 'async': False, 'headers': headers or {'Content-Type': 'application/json'},
        'body': json.dumps(body) if body is not None else ''}, timeout=40)
    if result.get('status') != 'completed':
        raise ValueError('Function execution did not complete')
    return result.get('responseStatusCode'), result.get('responseBody', '')


def verify(client):
    private_storage(client)
    accounts, probe_emails, owned_job = [], [], None
    file_id = uuid.uuid4().hex
    try:
        # Real native transactions, private schema, account isolation and logout.
        for _ in range(2):
            email, password = uuid.uuid4().hex + '@probe.invalid', uuid.uuid4().hex
            probe_emails.append(email)
            status, body = execute(client, '/api/auth/signup', 'POST', {'email': email, 'password': password})
            if status != 201:
                raise ValueError('Live account contract failed')
            value = json.loads(body)
            accounts.append(value['user']['id'])
            if value['user']['email'] != email:
                raise ValueError('Live account contract differs')
            headers = {'Authorization': 'Bearer ' + value['token'], 'Content-Type': 'application/json'}
            status, body = execute(client, '/api/auth/me', headers=headers)
            if status != 200 or json.loads(body)['id'] != accounts[-1]:
                raise ValueError('Live session contract failed')
            if len(accounts) == 1:
                owned_job = uuid.uuid4().hex
                client.create(RECORDS, owned_job, {'owner_id': accounts[0], 'kind': 'job', 'parent_id': '',
                    'state': 'complete', 'payload': encode({'result': {'generatedProbe': True}, 'error': None}),
                    'revision': 0, 'expires_at': None})
                if execute(client, '/api/jobs/' + owned_job, headers=headers)[0] != 200:
                    raise ValueError('Owner cannot read their processing receipt')
            elif execute(client, '/api/jobs/' + owned_job, headers=headers)[0] != 404:
                raise ValueError('Account isolation failed')
            if execute(client, '/api/content/' + (accounts[0] if len(accounts) == 2 else uuid.uuid4().hex) + '/media', headers=headers)[0] != 404:
                raise ValueError('Unavailable media must not disclose data')
            if execute(client, '/api/auth/logout', 'POST', {}, headers)[0] != 200 or execute(client, '/api/auth/me', headers=headers)[0] != 401:
                raise ValueError('Logout revocation failed')
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (16, 16), (20, 80, 120)).save(buffer, format='PNG')
        data = buffer.getvalue()
        files = Files(client)
        files.chunk(file_id, file_id + '.png', data, 0, len(data))
        if files.download(file_id) != data:
            raise ValueError('Private storage integrity failed')
        status, body = execute(client, '/api/health')
        if status != 200 or json.loads(body)['capabilities']['uploadProtocol'] != 'chunked-appwrite-v1':
            raise ValueError('Live health contract differs')
        for path in ('/privacy', '/terms', '/data-deletion', '/account/delete'):
            if execute(client, path)[0] != 200:
                raise ValueError('Public policy/account route unavailable')
        return {'nativeTransactions': True, 'privateStorageIntegrity': True, 'sessionLogout': True,
                'twoGeneratedAccounts': True, 'policyRoutes': True, 'externalMessagesSent': False,
                'realDeviceOAuth': False, 'commercialLaunchCertified': False}
    finally:
        # IDs are generated by this probe; never delete other accounts/files.
        Files(client).delete(file_id)
        # Reconcile a signup whose HTTP response was lost. Only generated probe
        # email identities may be selected; never sweep arbitrary user accounts.
        for email in probe_emails:
            for row in client.rows(ACCOUNTS, [query('equal', 'email', [email])]):
                if row.get('email') != email:
                    raise ValueError('Probe account filter differs')
                if row['$id'] not in accounts:
                    accounts.append(row['$id'])
        for uid in accounts:
            rows = list(client.rows(RECORDS, [query('equal', 'owner_id', [uid])]))
            for row in rows:
                if row['owner_id'] != uid:
                    raise ValueError('Probe cleanup ownership differs')
                client.delete(RECORDS, row['$id'])
            client.delete(ACCOUNTS, uid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--configure-storage', action='store_true', help='Apply the approved private bucket settings together; requires buckets.write.')
    args = parser.parse_args()
    # Reuse the existing private Codespaces encryption key, preserving migrated
    # Instagram credentials. Never generate a replacement for an existing key.
    old_key = ROOT / '.ditto-data/token-encryption.key'
    if not os.getenv('TOKEN_ENCRYPTION_KEY') and old_key.is_file():
        from cryptography.fernet import Fernet
        value = old_key.read_text(encoding='utf-8').strip()
        Fernet(value.encode())
        os.environ['TOKEN_ENCRYPTION_KEY'] = value
    if not args.stage and not args.verify and not args.configure_storage:
        print(json.dumps(plan(), indent=2))
        return
    key = os.getenv('APPWRITE_DEPLOY_KEY')
    if not key:
        raise SystemExit('Runner requires private APPWRITE_DEPLOY_KEY. The existing storage-only key cannot deploy Functions.')
    report = json.loads(REPORT.read_text(encoding='utf-8')) if args.verify and not args.stage and REPORT.exists() else {}
    report.update(startedAt=stamp(), publicLaunchPerformed=False, billingChanges=False)
    if args.stage and urlsplit(os.getenv('PUBLIC_BASE_URL', '')).hostname and urlsplit(os.getenv('PUBLIC_BASE_URL', '')).hostname.endswith('.github.dev'):
        # A development origin cannot become the commercial callback by accident.
        os.environ.pop('PUBLIC_BASE_URL', None)
    with Client(key) as client:
        if args.configure_storage:
            configure_storage(client)
            if not args.stage and not args.verify:
                print('Private bucket settings verified. No files deleted or deployment published.')
                return
        if args.stage:
            print('Deployment step: verify private storage settings', flush=True)
            private_storage(client)
            print('Deployment step: prepare isolated database schema', flush=True)
            schema(client)
            select_media_runtime(client)
            archive = ROOT / 'output/ditto-appwrite-candidate.tar.gz'
            report['bundle'] = package(archive)
            report['deployments'] = {}
            for identity in ('ditto-api', 'ditto-worker'):
                print('Deployment step: configure ' + identity, flush=True)
                function(client, identity)
                print('Deployment step: build ' + identity, flush=True)
                report['deployments'][identity] = build(client, identity, archive)
                if identity == 'ditto-api' and not os.getenv('PUBLIC_BASE_URL'):
                    base = generated_origin(client)
                    if base:
                        os.environ['PUBLIC_BASE_URL'] = base
                        function(client, identity)
                        report['deployments'][identity] = build(client, identity, archive)
                save(report)
            report['publicBaseUrl'] = os.getenv('PUBLIC_BASE_URL', '')
        print('Deployment step: verify live accounts and private storage', flush=True)
        report['verification'] = verify(client)
        report['finishedAt'] = stamp()
        save(report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except CloudError as exc:
        # CloudError stores only a numeric status and validated symbolic type;
        # never include response bodies, request headers or secret values.
        print('Appwrite failure: HTTP ' + str(exc.status) + '; code=' + exc.code, flush=True)
        raise SystemExit('Deployment stopped. The step above identifies where it failed. Source retained; nothing published.') from None
    except Exception:
        raise SystemExit('Deployment stopped safely. Check private scope/configuration/build status; no credential or provider response was printed. Existing source retained; nothing was published.') from None
