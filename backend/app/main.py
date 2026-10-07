"""Ditto backend entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.auth import router as auth_router
from app.config import get_settings
from app.database.db import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("ditto")

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.demo_mode:
        if not settings.support_email or not settings.operator_name:
            raise RuntimeError("Production requires SUPPORT_EMAIL and OPERATOR_NAME.")
    init_db()
    from app.services.account_deletion import purge_media
    purge_media()
    logger.info("Ditto backend ready.")
    import threading
    stop = threading.Event()
    worker = None
    if settings.processing_worker_enabled:
        from app.services.processing import run
        worker = threading.Thread(target=run, args=(stop,), daemon=True, name='ditto-processing')
        worker.start()
    try:
        yield
    finally:
        stop.set()
        if worker:
            worker.join(timeout=10)


app = FastAPI(
    lifespan=lifespan,
    title="Ditto",
    description="An Agentic AI Content Credit System — detection, verification, "
                "human-approved action, and autonomous follow-up.",
    version="1.8.8",
    docs_url="/docs" if settings.demo_mode else None,
    redoc_url="/redoc" if settings.demo_mode else None,
    openapi_url="/openapi.json" if settings.demo_mode else None,
)

# The Android client talks to this API directly; a browser dashboard may be added
# later, so CORS is permissive in development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.demo_mode else [],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.instagram_oauth import router as instagram_router
app.include_router(instagram_router)
app.include_router(auth_router)
from app.api.account_pages import router as account_pages_router
app.include_router(account_pages_router)
app.include_router(router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace to the client."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ditto hit an unexpected error. Refresh your data before retrying."},
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "Ditto",
        "version": "1.8.8",
        "tagline": "Stay on it until it's resolved.",
        "docs": "/docs",
        "health": "/api/health",
    }

from app.api.web_search import router as web_search_router
app.include_router(web_search_router)
from app.api.legal_pages import router as legal_pages_router
app.include_router(legal_pages_router)
from app.api.processing import router as processing_router
app.include_router(processing_router)
