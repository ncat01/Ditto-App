"""Separate Appwrite deployment candidate; never imports the SQLite application."""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from cloud import auth, media_api, oauth, cases, discovery
from cloud.auth import current
from cloud.client import CloudError
from cloud.deps import get_store
from cloud.store import payload


def create_app(client_factory=None):
    app = FastAPI(title='Ditto Appwrite backend candidate', docs_url=None, redoc_url=None)
    app.state.client_factory = client_factory
    app.include_router(auth.router)
    app.include_router(media_api.router)
    app.include_router(oauth.router)
    app.include_router(cases.router)
    app.include_router(discovery.router)
    from app.api.account_pages import router as account_pages
    from app.api.legal_pages import router as legal_pages
    app.include_router(account_pages)

    @app.exception_handler(CloudError)
    async def unavailable(request, exc):
        return JSONResponse({'detail': 'Cloud operation unavailable; retry or check its status.'}, status_code=503)

    @app.get('/api/health')
    def health():
        from app.config import get_settings
        from app.services.account_email import require_email
        settings = get_settings()
        try:
            oauth.origin()
            instagram = True
        except HTTPException:
            instagram = False
        try:
            require_email()
            email = True
        except Exception:
            email = False
        return {'status': 'ok', 'metadata': 'Appwrite TablesDB',
                'capabilities': {'uploadProtocol': 'chunked-appwrite-v1',
                    'maxUploadBytes': 20_000_000, 'commercialReady': False,
                    'instagram': instagram, 'outreach': email and settings.cloud_email_outreach_enabled,
                    'accountEmail': email, 'webSearch': bool(settings.google_cloud_api_key.get_secret_value()),
                    'automatedInstagramDiscovery': False},
                'readinessNotice': 'Deployment health does not certify Meta approval or commercial launch readiness.'}

    @app.get('/api/jobs/{job_id}')
    def job_status(job_id: str, account=Depends(current), store=Depends(get_store)):
        row = store.owned(account['$id'], job_id, 'job')
        value = payload(row)
        return {'id': job_id, 'state': row['state'], 'result': value.get('result'), 'error': value.get('error')}

    @app.get('/api/activity')
    def activity(account=Depends(current), store=Depends(get_store)):
        return [payload(row) for row in store.owned_rows(account['$id'], 'activity', limit=100)]

    app.include_router(legal_pages)
    return app


app = create_app()
