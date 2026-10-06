"""Run as a single worker process. Every external action still requires approval."""
import sys,time,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database.db import SessionLocal
from app.models.tables import User
from app.services.scheduler import check_due
def tick():
    from app.services.account_deletion import purge_media
    purge_media()
    with SessionLocal() as db:ids=list(db.scalars(select(User.id)))
    for user in ids:
        with SessionLocal() as db:
            db.info['user_id']=user
            try:check_due(db)
            except Exception:db.rollback();logging.exception('Follow-up failed; retry next tick')
if '--once' in sys.argv:tick()
else:
    while True:tick();time.sleep(30)
