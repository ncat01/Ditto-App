import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File
from pydantic import BaseModel
from app.database.db import get_db
from app.config import get_settings
from app.models.tables import Content
from app.models.account_security import WebSearchRecord
from app.providers.web_search import query_images,search,SearchUnavailable
from app.services.request_budget import consume,consume_monthly

router=APIRouter(prefix='/api/discovery',tags=['Web discovery'])
@router.get('/status')
def status(db=Depends(get_db)):
    return {'configured':bool(get_settings().serpapi_api_key.get_secret_value()),
            'outreach':get_settings().outreach_is_live,'provider':'SerpApi Google Lens',
            'monthlyImageLimit':get_settings().search_monthly_unit_limit}

class Consent(BaseModel):
    consent_to_search_provider: bool = False
    request_id: str | None = None


@router.post('/{content_id}/web-search-job', status_code=202)
def submit_web_search(content_id: str, body: Consent, db=Depends(get_db)):
    from app.services.search_jobs import enqueue
    return enqueue(db, content_id, body)


@router.get('/{content_id}/web-search-job')
def latest_web_search(content_id: str, db=Depends(get_db)):
    from app.services.search_jobs import latest
    return latest(db, content_id)

@router.post('/{content_id}/web-search')
def web_search(content_id:str,body:Consent,db=Depends(get_db)):
    item=db.get(Content,content_id)
    if not item or item.user_id!=db.info['user_id']:raise HTTPException(404,'Original unavailable')
    if not body.consent_to_search_provider:raise HTTPException(422,'Confirm sharing the image or sampled video frames with SerpApi and Google Lens before searching.')
    settings=get_settings()
    if not settings.serpapi_api_key.get_secret_value():raise HTTPException(503,'Web search is not configured by the service operator.')
    root=Path(settings.media_root).resolve()/db.info['user_id']
    path=Path(item.local_uri).resolve() if item.local_uri else None
    if not path or not path.is_relative_to(root) or not path.is_file():raise HTTPException(409,'Upload or import an original first. Sample content cannot be sent for web search.')
    consume('web-search:'+db.info['user_id'],10,86400)
    try:images=query_images(path,item.kind)
    except (ValueError,OSError):raise HTTPException(422,'Original cannot be decoded for search.') from None
    # Each frame uses one exact-match query and one visual-match query.
    search_units=len(images)*2
    consume('serpapi-hour',45,3600,search_units)
    consume_monthly('serpapi-user:'+db.info['user_id'],settings.search_user_monthly_unit_limit,search_units)
    consume_monthly('serpapi-project',settings.search_monthly_unit_limit,search_units)
    try:results=search(images)
    except SearchUnavailable as exc:raise HTTPException(503,str(exc)) from None
    identity=uuid.uuid4().hex
    db.add(WebSearchRecord(id=identity,user_id=db.info['user_id'],content_id=item.id,results=results,created_at=datetime.now(timezone.utc).replace(tzinfo=None)));db.commit()
    return {'id':identity,'provider':'SerpApi Google Lens','results':results,'unitsUsed':search_units,
            'coverage':'publicly_indexed_web_pages',
            'notice':'Possible matches are ordered with exact Instagram links first. Open each source to confirm the account, post date and permission.'}


@router.post('/{content_id}/compare')
async def compare_candidate(content_id:str,file: UploadFile = File(...),db=Depends(get_db)):
    import tempfile,os
    from app.matching.hasher import fingerprint,similarity
    from app.matching.video import frames,compare
    item=db.get(Content,content_id)
    if not item or item.user_id!=db.info['user_id']:raise HTTPException(404,'Original unavailable')
    settings=get_settings();root=Path(settings.media_root).resolve()/db.info['user_id']
    path=Path(item.local_uri).resolve() if item.local_uri else None
    if not path or not path.is_relative_to(root) or not path.is_file():raise HTTPException(409,'Upload or import an original first.')
    consume('compare:'+db.info['user_id'],30,3600)
    data=await file.read(25*1024*1024+1)
    if len(data)>25*1024*1024:raise HTTPException(413,'Candidate exceeds 25 MB.')
    suffix='.mp4' if item.kind=='video' else '.jpg'
    temporary=None
    try:
        if item.kind=='video':
            with tempfile.NamedTemporaryFile(dir=root,suffix=suffix,delete=False) as output:
                output.write(data);temporary=Path(output.name)
            original_hashes=frames(str(path));candidate_hashes=frames(str(temporary));score=compare(original_hashes,candidate_hashes)
            algorithm='Visual similarity analysis across five video frames'
        else:
            original_hashes=[fingerprint(path.read_bytes())];candidate_hashes=[fingerprint(data)];score=similarity(original_hashes[0],candidate_hashes[0]);algorithm='Visual similarity analysis'
    except (ValueError,OSError):raise HTTPException(422,'Candidate cannot be decoded as the same media type as your original.') from None
    finally:
        if temporary:temporary.unlink(missing_ok=True)
    result={'similarity':round(score,4),'algorithm':algorithm,'originalHashes':original_hashes,'candidateHashes':candidate_hashes,'notice':'Measured similarity is not a probability of infringement. Review publication dates, credit, ownership and permission separately. No message was sent.'}
    identity=uuid.uuid4().hex
    db.add(WebSearchRecord(id=identity,user_id=db.info['user_id'],content_id=item.id,results=[result],created_at=datetime.now(timezone.utc).replace(tzinfo=None)));db.commit()
    return result
