"""Authoritative case lifecycle — the server-side twin of the Kotlin state machine.

Report §39: the domain layer enforces valid transitions; the client cannot set a
state directly, it can only request an action that implies one.
"""
from __future__ import annotations

from app.models.enums import CaseState

ALLOWED: dict[CaseState, set[CaseState]] = {
    CaseState.NEW: {CaseState.VERIFIED, CaseState.CLOSED},
    CaseState.VERIFIED: {CaseState.PENDING_APPROVAL, CaseState.CLOSED},
    CaseState.PENDING_APPROVAL: {CaseState.SENT, CaseState.CLOSED},
    CaseState.SENT: {CaseState.AWAITING_RESPONSE, CaseState.RESOLVED, CaseState.CLOSED},
    CaseState.AWAITING_RESPONSE: {
        CaseState.ESCALATED,
        CaseState.RESOLVED,
        CaseState.CLOSED,
    },
    # An escalated case returns to the approval gate at a higher action tier;
    # approving it dispatches again, hence ESCALATED -> SENT.
    CaseState.ESCALATED: {
        CaseState.SENT,
        CaseState.AWAITING_RESPONSE,
        CaseState.RESOLVED,
        CaseState.CLOSED,
    },
    CaseState.RESOLVED: set(),
    CaseState.CLOSED: set(),
}


class InvalidTransition(Exception):
    """Raised when a caller requests a transition the lifecycle forbids."""


def can_transition(source: CaseState, target: CaseState) -> bool:
    return target in ALLOWED.get(source, set())


def next_states(source: CaseState) -> set[CaseState]:
    return ALLOWED.get(source, set())


def assert_transition(source: CaseState, target: CaseState) -> CaseState:
    if not can_transition(source, target):
        allowed = ", ".join(sorted(s.value for s in next_states(source))) or "none (terminal)"
        raise InvalidTransition(
            f"Illegal transition {source.value} -> {target.value}. "
            f"Allowed from {source.value}: {allowed}"
        )
    return target
