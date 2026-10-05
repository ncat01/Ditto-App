"""Normalized records complement the existing denormalized case read model."""
from datetime import datetime
from sqlalchemy import String,Text,JSON,DateTime,ForeignKey,Boolean,Integer
from sqlalchemy.orm import Mapped,mapped_column
from app.database.db import Base
from app.models.tables import _now

class CreatorProfile(Base):
    __tablename__='creator_profiles'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    display_name: Mapped[str]=mapped_column(String(128))
    handle: Mapped[str]=mapped_column(String(128),default='')
    preferences: Mapped[dict]=mapped_column(JSON,default=dict)

class Fingerprint(Base):
    __tablename__='fingerprints'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    content_id: Mapped[str]=mapped_column(ForeignKey('content.id'),index=True)
    algorithm: Mapped[str]=mapped_column(String(64))
    frame_hashes: Mapped[list]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=_now)

class ScanJob(Base):
    __tablename__='scan_jobs'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    content_id: Mapped[str]=mapped_column(ForeignKey('content.id'),index=True)
    stage: Mapped[str]=mapped_column(String(32),index=True)
    stages: Mapped[list]=mapped_column(JSON,default=list)
    candidates: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=_now)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class Evidence(Base):
    __tablename__='evidence'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'),index=True)
    kind: Mapped[str]=mapped_column(String(32))
    payload: Mapped[dict]=mapped_column(JSON)
    simulated: Mapped[bool]=mapped_column(Boolean,default=True)

class AgentDecision(Base):
    __tablename__='agent_decisions'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'),index=True)
    component: Mapped[str]=mapped_column(String(32))
    provider: Mapped[str]=mapped_column(String(64),default='deterministic-demo')
    model: Mapped[str]=mapped_column(String(128),default='rules-v1')
    output: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=_now)

class Approval(Base):
    __tablename__='approvals'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'),index=True)
    user_id: Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True,index=True)
    decision: Mapped[str]=mapped_column(String(32))
    recipient: Mapped[str]=mapped_column(String(128))
    channel: Mapped[str]=mapped_column(String(32),default='sandbox')
    body: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=_now)

class Notification(Base):
    __tablename__='notifications'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey('cases.id'),index=True)
    title: Mapped[str]=mapped_column(String(256))
    read: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=_now)
