"""Agent contracts. Decision-making components, not chatbots.

Mock implementations back Demo Mode; LLM-backed implementations satisfy the same
protocols and can be swapped in without touching the service layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.models.enums import (
    ActionType,
    CaseState,
    Classification,
    FollowUpOutcome,
    MessageTone,
    Severity,
)


@dataclass
class Signal:
    name: str
    value: str
    supports_match: bool


@dataclass
class VerificationResult:
    classification: Classification
    confidence: float
    severity: Severity
    summary: str
    signals: list[Signal] = field(default_factory=list)
    evidence_summary: str = ""
    engine: str = ""


@dataclass
class ActionPlan:
    action: ActionType
    priority: Severity
    reasoning: str
    factors: list[str]
    draft_subject: str
    draft_body: str
    tone: MessageTone
    engine: str


@dataclass
class FollowUpDecision:
    outcome: FollowUpOutcome
    next_state: CaseState
    escalate_to: ActionType | None
    headline: str
    reasoning: str


class VerificationAgent(Protocol):
    display_name: str

    def verify(self, content, candidate) -> VerificationResult: ...


class ActionPlanningAgent(Protocol):
    display_name: str

    def plan(
        self, content, candidate, verification, prior_escalation_level: int,
        tone: MessageTone = MessageTone.PROFESSIONAL,
    ) -> ActionPlan: ...


class FollowUpAgent(Protocol):
    display_name: str

    def evaluate(self, case, observed: FollowUpOutcome) -> FollowUpDecision: ...


class DiscoveryProvider(Protocol):
    display_name: str

    def discover(self, content) -> list: ...
