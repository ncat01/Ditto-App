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
from app.services.seed import seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ditto")

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        created = 0  # Each authenticated user explicitly seeds their own corpus.
        if created:
            logger.info("Seeded %s demo cases", created)
    finally:
        db.close()
    logger.info("Ditto backend ready. Demo mode: %s", settings.demo_mode)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Ditto",
    description="An Agentic AI Content Credit System — detection, verification, "
                "human-approved action, and autonomous follow-up.",
    version="1.0.0",
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

app.include_router(auth_router)
app.include_router(router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace to the client."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ditto hit an unexpected error. The request was not applied."},
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "Ditto",
        "tagline": "Stay on it until it's resolved.",
        "docs": "/docs",
        "health": "/api/health",
    }
