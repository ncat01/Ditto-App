"""PostgreSQL-backed jobs; commit comparison cases/results atomically.

Workers hold a row lock until commit. A killed process rolls back the claim so
another worker can retry the deterministic comparison without duplicate cases.
Email and reverse searches commit attempt receipts before external provider work.
Reverse searches use their own worker so they do not delay comparisons.
"""
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy import select, or_
from app.database.db import SessionLocal
from app.config import get_settings
from app.models.jobs import ProcessingJob, CandidateMedia
from app.models.tables import Content, CandidateMatch, Case, CaseHistory
from app.models.ledger import Evidence, Notification
from app.matching.hasher import fingerprint, similarity
from app.matching.video import frames, compare


def private_path(user_id, value):
    root = Path(get_settings().media_root).resolve()/user_id
    path = Path(value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Private media unavailable')
    return path


def process_next(include_search=True):
    with SessionLocal() as db:
        statement = select(ProcessingJob).where(ProcessingJob.state == 'queued')
        if not include_search:
            kind = ProcessingJob.payload['kind'].as_string()
            statement = statement.where(or_(kind != 'web_search', kind.is_(None)))
        job = db.scalar(statement.order_by(ProcessingJob.created_at)
                        .with_for_update(skip_locked=True).limit(1))
        if not job:
            return False
        if job.payload.get('kind') == 'email':
            from app.services.email_outreach import deliver
            deliver(db,job)
            return True
        if job.payload.get('kind') == 'web_search':
            from app.services.search_jobs import deliver
            deliver(db, job)
            return True
        try:
            original = db.get(Content, job.payload['originalId'])
            if not original or original.user_id != job.user_id:
                raise ValueError('Original unavailable')
            a = private_path(job.user_id, original.local_uri)
            b = private_path(job.user_id, job.payload['candidatePath'])
            if original.kind == 'video':
                ah,bh = frames(a),frames(b)
                score = compare(ah,bh)
            else:
                ah,bh = [fingerprint(a.read_bytes())],[fingerprint(b.read_bytes())]
                score = similarity(ah[0],bh[0])
            identity = 'DIT-'+uuid.uuid4().hex[:12]
            candidate = CandidateMatch(id=uuid.uuid4().hex,content_id=original.id,
                platform='Submitted evidence',account_name='Submitted candidate',account_handle='',
                source_url='',hash_similarity=score,visual_similarity=score,
                transform_note='Visual similarity comparison. Permission, credit and infringement require human review.')
            db.add(candidate);db.flush()
            case = Case(id=identity,content_id=original.id,candidate_id=candidate.id,
                current_state='pending_approval',recommended_action='review_request',
                verification_summary='Measured similarity only; no infringement determination.',
                verification_engine='Visual similarity analysis',verification_signals=[],
                evidence_summary='Candidate uploaded by the account owner for comparison.',
                action_reasoning='Review ownership, publication dates, permission and attribution before taking action.',
                action_factors=[],draft_subject='Content credit inquiry',draft_body='',tone='professional',
                plan_engine='Human review required')
            db.add(case);db.flush()
            db.add(CandidateMedia(case_id=identity,user_id=job.user_id,path=str(b)))
            db.add(Evidence(id=uuid.uuid4().hex,case_id=identity,kind='measured_similarity',simulated=False,
                payload={'similarity':score,'originalHashes':ah,'candidateHashes':bh,
                         'faceDetector':'unavailable','manipulationDetector':'unavailable'}))
            db.add(CaseHistory(case_id=identity,previous_state=None,new_state='pending_approval',
                agent='human',action='Submitted evidence ready',reasoning='Measured comparison completed; human review required.'))
            db.add(Notification(id=uuid.uuid4().hex,user_id=job.user_id,case_id=identity,title='Submitted evidence ready for review'))
            job.result={'caseId':identity,'similarity':round(score,4),'algorithm':'Visual similarity analysis',
                        'notice':'Similarity does not establish infringement. No message was sent.'}
            job.state='complete'
        except (ValueError, OSError, KeyError):
            job.state='error';job.error='Media could not be compared. Check the original and candidate files.'
        db.commit()
        return True


def process_search_next():
    with SessionLocal() as db:
        job = db.scalar(select(ProcessingJob).where(
            ProcessingJob.state == 'queued',
            ProcessingJob.payload['kind'].as_string() == 'web_search')
            .order_by(ProcessingJob.created_at).with_for_update(skip_locked=True).limit(1))
        if not job:
            return False
        from app.services.search_jobs import deliver
        deliver(db, job)
        return True


def run(stop):
    import logging
    import threading
    import time
    from app.services.search_jobs import recover_interrupted
    with SessionLocal() as db:
        recover_interrupted(db)

    def search_loop():
        while not stop.is_set():
            try:
                worked = process_search_next()
            except Exception:
                logging.getLogger('ditto').error('Search receipt could not be finalized; provider attempt will not be replayed.')
                worked = False
            stop.wait(0.2 if worked else 2)

    search_worker = threading.Thread(target=search_loop, daemon=True, name='ditto-search')
    search_worker.start()
    next_recovery = time.monotonic() + 30
    while not stop.is_set():
        if time.monotonic() >= next_recovery:
            try:
                with SessionLocal() as db:
                    recover_interrupted(db)
            except Exception:
                logging.getLogger('ditto').error('Interrupted search receipts could not be checked; checking again later.')
            next_recovery = time.monotonic() + 30
        try:
            worked = process_next(include_search=False)
        except Exception:
            logging.getLogger('ditto').error('Processing transaction failed; claim rolled back for retry.')
            worked = False
        stop.wait(0.2 if worked else 2)
