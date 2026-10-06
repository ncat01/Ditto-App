"""Publish only a verified private deployment with explicit operator evidence.

External attestations are operator statements, never automated approval claims.
No billing/plan change, source deletion or Android publication is performed.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import deploy_appwrite_cloud as deploy
from cloud.client import Client, CloudError
from cloud.store import stamp

GATES = ('metaPublicUserAuthorizationVerified', 'smtpSenderAndInboxVerified', 'restoreDrillVerified',
         'frozenSourceMigrationReviewed', 'androidDeviceFlowsVerified', 'signingKeySeparatelyBackedUp',
         'privacyAndRetentionPolicyApproved', 'studentHostingQuotasReviewed', 'limitedDiscoveryScopeDisclosed')


def validate_evidence(evidence, report, archive):
    if not all(evidence.get(name) is True for name in GATES):
        raise ValueError('External launch checks remain incomplete')
    if evidence.get('operator') != 'Svarsha T':
        raise ValueError('Operator evidence is required')
    if not report.get('verification', {}).get('privateStorageIntegrity') or not report.get('verification', {}).get('sessionLogout'):
        raise ValueError('Live staging checks did not pass')
    fingerprint = hashlib.sha256(archive.read_bytes()).hexdigest()
    if report.get('bundle', {}).get('sha256') != fingerprint or evidence.get('bundleSha256') != fingerprint:
        raise ValueError('Evidence does not match the built deployment')
    base = evidence.get('publicBaseUrl', '').rstrip('/')
    url = urlsplit(base)
    if (url.scheme != 'https' or not url.hostname or url.path or url.query or url.fragment or url.username or
            url.hostname.endswith(('.github.dev', '.invalid', '.example')) or url.hostname in ('localhost', '127.0.0.1')):
        raise ValueError('A stable production HTTPS root is required')
    if base != report.get('publicBaseUrl', '').rstrip('/'):
        raise ValueError('Origin differs from the staged deployment and Meta redirect')
    if evidence.get('metaRedirectUrl') != base + '/api/integrations/instagram/callback':
        raise ValueError('Meta redirect must exactly match the deployed origin')
    return base


def publish(client, evidence, report, archive):
    base = validate_evidence(evidence, report, archive)
    # Runtime provider secrets cannot be read back by the management API. Their
    # presence is checked through the private Function capability contract.
    code, raw = deploy.execute(client, '/api/health')
    health = json.loads(raw)
    if code != 200 or not health['capabilities'].get('instagram') or not health['capabilities'].get('accountEmail'):
        raise ValueError('Instagram and account email are not configured in the staged Function')
    for identity, deployment in report['deployments'].items():
        value = client.request('GET', '/functions/' + identity)
        if value.get('enabled') or value.get('execute') or value.get('schedule'):
            raise ValueError('Expected a private, stopped deployment')
        if value.get('deploymentId') != deployment or value.get('live') is not True:
            raise ValueError('Function deployment/configuration changed since verification')
    # Private worker remains inaccessible to anonymous callers. API application
    # routes enforce opaque Ditto sessions and per-owner data access.
    worker = deploy.definition('ditto-worker')
    client.request('PUT', '/functions/ditto-worker', json={**worker, 'enabled': True, 'schedule': '*/5 * * * *'})
    api = deploy.definition('ditto-api')
    try:
        client.request('PUT', '/functions/ditto-api', json={**api, 'enabled': True, 'execute': ['any']})
        import httpx
        with httpx.Client(base_url=base, timeout=40, follow_redirects=False) as public:
            result = public.get('/api/health')
            if result.status_code != 200 or result.json()['metadata'] != 'Appwrite TablesDB':
                raise ValueError('Public HTTPS health differs')
            if public.get('/api/content').status_code != 401:
                raise ValueError('Public content must require authentication')
    except Exception:
        client.request('PUT', '/functions/ditto-api', json=api)
        client.request('PUT', '/functions/ditto-worker', json=worker)
        raise
    return {'publishedAt': stamp(), 'publicBaseUrl': base, 'billingChanges': False,
            'workerPublicAccess': False, 'externalChecks': 'Operator attested; not independently certified by this script.',
            'emailOutreachEnabled': False, 'note': 'Outreach remains off until a separate reviewed provider activation. No app-store publication performed.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if not args.publish:
        print(json.dumps({'mode': 'plan only', 'requiredOperatorEvidence': GATES, 'cloudWrites': 0}))
    else:
        try:
            evidence = json.loads(args.evidence.read_text(encoding='utf-8'))
            report = json.loads(deploy.REPORT.read_text(encoding='utf-8'))
            archive = deploy.ROOT / 'output/ditto-appwrite-candidate.tar.gz'
            validate_evidence(evidence, report, archive)
            with Client(os.environ['APPWRITE_DEPLOY_KEY']) as client:
                result = publish(client, evidence, report, archive)
            report['launch'] = result
            deploy.save(report)
            print(json.dumps(result, indent=2))
        except Exception:
            raise SystemExit('Launch stopped. Review unmet evidence, private runtime configuration and live checks. No key or provider response is printed. Check Function status before retrying if a network interruption occurred.') from None
