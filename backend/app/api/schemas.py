"""Pydantic request/response models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    ActionType,
    CaseState,
    Classification,
    FollowUpOutcome,
    MessageTone,
    Severity,
)

MAX_TEXT = 20_000


def _sanitize(value: str) -> str:
    """Strip control characters and cap length on user-supplied text."""
    cleaned = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return cleaned[:MAX_TEXT]


class SignalOut(BaseModel):
    name: str
    value: str
    supportsMatch: bool


class CandidateOut(BaseModel):
    id: str
    mediaKind: Literal['image', 'video'] = 'video'
    platform: str
    accountName: str
    accountHandle: str
    sourceUrl: str
    caption: str
    followerCount: int
    monetized: bool
    hashSimilarity: float
    visualSimilarity: float
    captionSimilarity: float
    faceSimilarity: float
    postedAt: datetime
    transformNote: str
    paletteSeed: int
    discoveredAt: datetime
    attributionPresent: bool = False
    permissionGranted: bool = False


class HistoryOut(BaseModel):
    timestamp: datetime
    previousState: CaseState | None
    newState: CaseState | None
    agent: str
    action: str
    reasoning: str


class CaseOut(BaseModel):
    id: str
    contentId: str
    contentTitle: str
    contentPaletteSeed: int
    candidate: CandidateOut
    classification: Classification | None
    confidence: float | None
    severity: Severity | None
    verificationSummary: str | None
    verificationSignals: list[SignalOut] = Field(default_factory=list)
    evidenceSummary: str | None
    verificationEngine: str | None
    recommendedAction: ActionType | None
    actionReasoning: str | None
    actionFactors: list[str] = Field(default_factory=list)
    draftSubject: str | None
    draftBody: str | None
    tone: MessageTone | None
    planEngine: str | None
    currentState: CaseState
    escalationLevel: int
    followUpCount: int
    createdAt: datetime
    updatedAt: datetime
    nextFollowUpAt: datetime | None
    lastActionAt: datetime | None
    history: list[HistoryOut] = Field(default_factory=list)


class ContentOut(BaseModel):
    id: str
    title: str
    kind: str
    perceptualHash: str
    paletteSeed: int
    publishedAt: datetime
    sourcePlatform: str


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    kind: str = Field(default="image")

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return _sanitize(v)

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, v: str) -> str:
        if v not in ("image", "video"):
            raise ValueError("kind must be 'image' or 'video'")
        return v


class ScanRequest(BaseModel):
    contentId: str = Field(min_length=1, max_length=64)


class ApproveRequest(BaseModel):
    editedBody: str | None = None
    tone: MessageTone | None = None
    recipient: str = ''
    requestId: str = ''
    evidenceReviewed: bool = False
    recipientConfirmed: bool = False
    reminderDays: int = 0

    @field_validator("editedBody")
    @classmethod
    def clean_body(cls, v: str | None) -> str | None:
        return _sanitize(v) if v else v


class RejectRequest(BaseModel):
    note: str | None = None

    @field_validator("note")
    @classmethod
    def clean_note(cls, v: str | None) -> str | None:
        return _sanitize(v) if v else v


class EditActionRequest(BaseModel):
    body: str = Field(min_length=1)
    tone: MessageTone = MessageTone.PROFESSIONAL

    @field_validator("body")
    @classmethod
    def clean_body(cls, v: str) -> str:
        return _sanitize(v)


class FollowUpRequest(BaseModel):
    outcome: FollowUpOutcome = FollowUpOutcome.NO_RESPONSE


class ResolveRequest(BaseModel):
    note: str | None = None


class StatsOut(BaseModel):
    contentMonitored: int
    openCases: int
    awaitingResponse: int
    resolved: int
    escalated: int
    pendingApproval: int
    totalCases: int
    verifiedReposts: int
    falsePositives: int
    averageConfidence: float
    resolutionRate: float


class ActivityOut(BaseModel):
    id: int
    timestamp: datetime
    agent: str
    title: str
    detail: str
    caseId: str | None


class HealthOut(BaseModel):
    status: str
    demoMode: bool
    database: str
    providers: dict[str, str]
