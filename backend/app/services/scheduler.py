"""Durable sandbox follow-ups; a restart reads persisted deadlines again."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from app.models.tables import DemoClock,Case,Content
from app.models.enums import FollowUpOutcome

def now(db):
    clock=db.get(DemoClock,db.info.get('user_id',''))
    return datetime.now(timezone.utc)+timedelta(days=clock.offset_days if clock else 0)

def check_due(db):
    from app.services.case_service import run_follow_up
    cases=db.scalars(select(Case).join(Content).where(Content.user_id==db.info['user_id'],Case.current_state=='awaiting_response',Case.next_followup_at<=now(db))).all()
    for case in cases:run_follow_up(db,case.id,FollowUpOutcome.NO_RESPONSE)
    return len(cases)

def advance(db,days):
    clock=db.get(DemoClock,db.info['user_id'])
    if not clock:
        clock=DemoClock(user_id=db.info['user_id'],offset_days=0);db.add(clock)
    clock.offset_days+=days;db.commit()
    return check_due(db)
