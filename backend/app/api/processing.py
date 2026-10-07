import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from app.database.db import get_db
from app.config import get_settings
from app.models.jobs import ProcessingJob, CandidateMedia
from app.models.tables import Content
from app.services.processing import private_path
from app.services.request_budget import consume

router = APIRouter(prefix='/api', tags=['Processing'])


@router.post('/discovery/{content_id}/compare-job', status_code=202)
async def submit(content_id: str, file: UploadFile = File(...), db=Depends(get_db)):
    original = db.get(Content,content_id)
    if not original or original.user_id != db.info['user_id']:
        raise HTTPException(404,'Original unavailable')
    consume('processing:'+db.info['user_id'],30,3600)
    data = await file.read(25*1024*1024+1)
    if not data or len(data)>25*1024*1024:
        raise HTTPException(413,'Candidate must be nonempty and no larger than 25 MB.')
    identity = uuid.uuid4().hex
    root = Path(get_settings().media_root).resolve()/db.info['user_id']
    root.mkdir(parents=True,exist_ok=True)
    target = root/(identity+('.mp4' if original.kind=='video' else '.image'))
    try:
        target.write_bytes(data)
        db.add(ProcessingJob(id=identity,user_id=db.info['user_id'],state='queued',
                            payload={'originalId':content_id,'candidatePath':str(target)}))
        db.commit()
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {'jobId':identity,'state':'queued'}


@router.get('/jobs/{identity}')
def status(identity: str,db=Depends(get_db)):
    job = db.get(ProcessingJob,identity)
    if not job or job.user_id != db.info['user_id']:
        raise HTTPException(404,'Processing job unavailable')
    return {'id':job.id,'state':job.state,'result':job.result,'error':job.error}


@router.get('/cases/{case_id}/candidate-media')
def candidate(case_id: str,db=Depends(get_db)):
    media = db.get(CandidateMedia,case_id)
    if not media or media.user_id != db.info['user_id']:
        raise HTTPException(404,'Candidate media unavailable')
    try:
        path = private_path(media.user_id,media.path)
    except ValueError:
        raise HTTPException(404,'Candidate media unavailable') from None
    return FileResponse(path,headers={'Cache-Control':'private, no-store'})
