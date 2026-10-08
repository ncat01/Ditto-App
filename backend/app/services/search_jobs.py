"""Durable reverse searches with a quota reservation and a persistent receipt.

The queued job and quota counters commit together. Once provider work starts the
receipt becomes running; a restart never automatically repeats that work.
"""
import hashlib
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.models.account_security import RequestBudget, WebSearchRecord
from app.models.jobs import ProcessingJob
from app.models.tables import ActivityEvent, Content
from app.providers.web_search import query_images, search, safe_url, SearchUnavailable

RECOVERY_GRACE = timedelta(minutes=2)


def log_search(db, job, title, detail):
    db.add(ActivityEvent(user_id=job.user_id,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        agent='discovery', title=title, detail=detail))


def original_path(user_id, item):
    root = Path(get_settings().media_root).resolve() / user_id
    path = Path(item.local_uri).resolve() if item.local_uri else None
    if not path or not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Private original unavailable')
    return path


def receipt(job):
    return {'jobId': job.id, 'state': job.state, 'result': job.result,
            'error': job.error}


def search_result(identity, results, units):
    return {'id': identity, 'provider': 'SerpApi Google Lens', 'results': results,
            'unitsUsed': units, 'coverage': 'publicly_indexed_web_pages',
            'notice': 'Possible matches are ordered with exact Instagram links first. '
                      'Open each source to confirm the account, post date and permission.'}


def reserve(db, key, limit, window, weight=1, retry_after=86400):
    """Reserve quota in the same transaction that creates the queued receipt."""
    if db.get_bind().dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    key = hashlib.sha256(key.encode()).hexdigest()
    statement = insert(RequestBudget).values(key=key, window=window, count=weight)
    statement = statement.on_conflict_do_update(index_elements=['key'], set_={
        'window': window,
        'count': case((RequestBudget.window == window, RequestBudget.count + weight),
                      else_=weight)}).returning(RequestBudget.count)
    count = db.execute(statement).scalar_one()
    if count > limit:
        raise HTTPException(429, 'Search or request allowance reached. Please try again later.',
                            headers={'Retry-After': str(retry_after)})


def enqueue(db, content_id, body):
    user_id = db.info['user_id']
    original = db.scalar(select(Content).where(Content.id == content_id,
                         Content.user_id == user_id).with_for_update())
    if not original:
        raise HTTPException(404, 'Original unavailable')
    if not body.consent_to_search_provider:
        raise HTTPException(422, 'Confirm sharing the image or sampled video frames '
                            'with SerpApi and Google Lens before searching.')
    request_id = body.request_id or ''
    if not re.fullmatch(r'[a-zA-Z0-9]{1,36}', request_id):
        raise HTTPException(422, 'A valid search request receipt is required.')
    identity = hashlib.sha256((user_id + ':' + content_id + ':' + request_id).encode()).hexdigest()[:32]
    existing = db.get(ProcessingJob, identity)
    if existing:
        return receipt(existing)
    settings = get_settings()
    if not settings.serpapi_api_key.get_secret_value():
        raise HTTPException(503, 'Web search is not configured by the service operator.')
    try:
        path = original_path(user_id, original)
    except ValueError:
        raise HTTPException(409, 'Upload or import an original first.') from None
    try:
        images = query_images(path, original.kind)
    except (ValueError, OSError):
        raise HTTPException(422, 'Original cannot be decoded for search.') from None
    units = len(images) * 2
    now = datetime.now(timezone.utc)
    month = now.year * 12 + now.month
    try:
        reserve(db, 'web-search:' + user_id, 10, int(time.time()) // 86400)
        reserve(db, 'serpapi-hour', 45, int(time.time()) // 3600, units, 3600)
        reserve(db, 'serpapi-user:' + user_id, settings.search_user_monthly_unit_limit, month, units)
        reserve(db, 'serpapi-project', settings.search_monthly_unit_limit, month, units)
        job = ProcessingJob(id=identity, user_id=user_id, state='queued', payload={
            'kind': 'web_search', 'originalId': content_id,
            'searchUnits': units, 'frameCount': len(images), 'consent': True})
        db.add(job)
        log_search(db, job, 'Search requested',
                   'Your original is queued. Results will appear when the search finishes.')
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        # Concurrent retries with the same receipt cannot reserve quota twice.
        db.rollback()
        existing = db.get(ProcessingJob, identity)
        if existing:
            return receipt(existing)
        raise
    return receipt(job)


def latest(db, content_id):
    user_id = db.info['user_id']
    original = db.get(Content, content_id)
    if not original or original.user_id != user_id:
        raise HTTPException(404, 'Original unavailable')
    job = db.scalar(select(ProcessingJob).where(
        ProcessingJob.user_id == user_id,
        ProcessingJob.payload['kind'].as_string() == 'web_search',
        ProcessingJob.payload['originalId'].as_string() == content_id)
        .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc()).limit(1))
    if job:
        return receipt(job)
    # Earlier app versions saved completed searches without a ProcessingJob.
    # Read those results directly; restoring them neither runs the provider nor
    # creates a receipt or quota reservation. The same legacy table also holds
    # direct comparison scores, which must not become web-search results.
    records = db.scalars(select(WebSearchRecord).where(
        WebSearchRecord.user_id == user_id, WebSearchRecord.content_id == content_id)
        .order_by(WebSearchRecord.created_at.desc(), WebSearchRecord.id.desc()))
    for record in records:
        if not isinstance(record.results, list):
            continue
        if record.results:
            results = [row for row in record.results
                       if isinstance(row, dict) and safe_url(row.get('url'))]
            if not results:
                continue
        else:
            # A completed zero-match search is [], whereas a comparison always
            # stores a nonempty measured-similarity object without source URLs.
            results = []
        return {'jobId': record.id, 'state': 'complete', 'error': None, 'result': {
            'id': record.id, 'provider': 'SerpApi Google Lens', 'results': results,
            'coverage': 'publicly_indexed_web_pages',
            'notice': 'Saved earlier search. Open each source to confirm the account, '
                      'post date and permission; these saved results may have changed.'}}
    return {'jobId': None, 'state': None, 'result': None, 'error': None}


def recover_interrupted(db):
    """On worker startup stop abandoned provider attempts without replaying them.

    PostgreSQL skips receipts locked by another live worker, including during a
    rolling deploy. Fresh claims have a grace interval covering the short gap
    between committing running and reacquiring the row lock. Periodic recovery
    catches a real crash after that interval. Attempts predating this receipt
    format have no startedAt and can be recovered immediately.
    """
    jobs = db.scalars(select(ProcessingJob).where(
        ProcessingJob.state == 'running',
        ProcessingJob.payload['kind'].as_string() == 'web_search')
        .with_for_update(skip_locked=True)).all()
    cutoff = datetime.now(timezone.utc) - RECOVERY_GRACE
    for job in jobs:
        started_at = job.payload.get('startedAt')
        if isinstance(started_at, str):
            try:
                started = datetime.fromisoformat(started_at)
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if started > cutoff:
                    continue
            except ValueError:
                pass
        job.state = 'unknown'
        job.error = 'Search was interrupted. Its provider usage is unconfirmed. '
        job.error += 'Start a new search explicitly if needed.'
        log_search(db, job, 'Search interrupted',
                   'The search did not finish. Open your original to review its saved status.')
    db.commit()


def deliver(db, job):
    # Decode/validate before committing the provider-attempt receipt, so invalid
    # or deleted media never leaves a running job or touches the search provider.
    identity = job.id
    try:
        original = db.get(Content, job.payload['originalId'])
        if not original or original.user_id != job.user_id:
            raise ValueError('Original unavailable')
        path = original_path(job.user_id, original)
        images = query_images(path, original.kind)
        if len(images) != job.payload['frameCount'] or not job.payload.get('consent'):
            raise ValueError('Search preparation changed')
    except (ValueError, OSError, KeyError):
        job.state = 'error'
        job.error = 'Original could not be prepared for search. Upload a valid image or video.'
        log_search(db, job, 'Search could not start', job.error)
        db.commit()
        return
    job.state = 'running'
    # Reassign JSON, because an in-place mutation is not tracked by this column.
    job.payload = {**job.payload, 'startedAt': datetime.now(timezone.utc).isoformat()}
    log_search(db, job, 'Search started',
               'Checking publicly indexed pages for possible copies of your original.')
    db.commit()
    # Hold a row lock through the provider request. A second live worker cannot
    # mistake this committed running receipt for an interrupted search.
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == identity)
                    .with_for_update().execution_options(populate_existing=True))
    if not job or job.state != 'running':
        return
    try:
        results = search(images)
        record_id = uuid.uuid4().hex
        db.add(WebSearchRecord(id=record_id, user_id=job.user_id,
            content_id=job.payload['originalId'], results=results,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
        job.result = search_result(record_id, results, job.payload['searchUnits'])
        job.state = 'complete'
        job.error = None
        detail = (f'Found {len(results)} possible matches. Open the sources to review them.'
                  if results else 'No indexed matches found. This does not prove that no repost exists.')
        log_search(db, job, 'Search complete', detail)
    except SearchUnavailable as exc:
        job.state = 'error'
        job.error = str(exc)[:256]
        log_search(db, job, 'Search could not finish', job.error)
    except Exception:
        # This receipt has already been committed as running. Never return it to
        # queued when an unexpected provider failure occurs.
        job.state = 'error'
        job.error = 'Search could not be completed. Start a new search explicitly if needed.'
        log_search(db, job, 'Search could not finish', job.error)
    db.commit()
