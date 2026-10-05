"""Domain enums. These mirror the Kotlin domain layer exactly so the Android client
can talk to either the on-device repository or this backend without translation."""
from __future__ import annotations

from enum import Enum


class CaseState(str, Enum):
    NEW = "new"
    VERIFIED = "verified"
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    AWAITING_RESPONSE = "awaiting_response"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        return self in (CaseState.RESOLVED, CaseState.CLOSED)

    @property
    def is_open(self) -> bool:
        return not self.is_terminal


class Classification(str, Enum):
    GENUINE_REPOST = "genuine_repost"
    GENUINE_LIKENESS_MISUSE = "genuine_likeness_misuse"
    FALSE_POSITIVE = "false_positive"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return {"low": 1, "medium": 2, "high": 3}[self.value]


class ActionType(str, Enum):
    LOG_ONLY = "log_only"
    ATTRIBUTION_REQUEST = "attribution_request"
    FORMAL_TAKEDOWN = "formal_takedown"
    REVIEW_REQUEST = "review_request"

    @property
    def tier(self) -> int:
        return {"log_only": 0, "attribution_request": 1, "formal_takedown": 2, "review_request": 1}[self.value]

    @property
    def label(self) -> str:
        return {
            "review_request": "Human Review Request",
            "log_only": "Log Only",
            "attribution_request": "Attribution Request",
            "formal_takedown": "Formal Takedown Notice",
        }[self.value]


class MessageTone(str, Enum):
    PROFESSIONAL = "professional"
    FIRM = "firm"
    NEUTRAL = "neutral"


class AgentKind(str, Enum):
    INGESTION = "ingestion"
    DISCOVERY = "discovery"
    VERIFICATION = "verification"
    ACTION_PLANNING = "action_planning"
    FOLLOW_UP = "follow_up"
    HUMAN = "human"


class FollowUpOutcome(str, Enum):
    NO_RESPONSE = "no_response"
    PARTIAL_RESPONSE = "partial_response"
    HOSTILE_RESPONSE = "hostile_response"
    ATTRIBUTION_ADDED = "attribution_added"
    CONTENT_REMOVED = "content_removed"
