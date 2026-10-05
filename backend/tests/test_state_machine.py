"""Lifecycle guarantees. These are the rules the UI cannot bypass."""
from __future__ import annotations

import pytest

from app.models.enums import CaseState
from app.services.state_machine import (
    InvalidTransition,
    assert_transition,
    can_transition,
    next_states,
)


def test_happy_path_is_allowed():
    path = [
        (CaseState.NEW, CaseState.VERIFIED),
        (CaseState.VERIFIED, CaseState.PENDING_APPROVAL),
        (CaseState.PENDING_APPROVAL, CaseState.SENT),
        (CaseState.SENT, CaseState.AWAITING_RESPONSE),
        (CaseState.AWAITING_RESPONSE, CaseState.ESCALATED),
        (CaseState.ESCALATED, CaseState.RESOLVED),
    ]
    for source, target in path:
        assert can_transition(source, target), f"{source} -> {target}"


def test_escalated_case_can_be_approved_and_dispatched_again():
    # Regression: the Follow-Up Agent escalates and returns the case to the approval
    # gate. Without ESCALATED -> SENT that escalation could never be acted on.
    assert can_transition(CaseState.ESCALATED, CaseState.SENT)
    assert can_transition(CaseState.SENT, CaseState.AWAITING_RESPONSE)


def test_escalation_loop_runs_for_multiple_cycles():
    state = CaseState.AWAITING_RESPONSE
    for _ in range(3):
        for nxt in (CaseState.ESCALATED, CaseState.SENT, CaseState.AWAITING_RESPONSE):
            assert can_transition(state, nxt), f"stalled at {state} -> {nxt}"
            state = nxt
    assert can_transition(state, CaseState.RESOLVED)


def test_new_cannot_jump_to_resolved():
    assert not can_transition(CaseState.NEW, CaseState.RESOLVED)
    with pytest.raises(InvalidTransition):
        assert_transition(CaseState.NEW, CaseState.RESOLVED)


def test_approval_gate_cannot_be_skipped():
    assert not can_transition(CaseState.VERIFIED, CaseState.SENT)
    assert not can_transition(CaseState.NEW, CaseState.SENT)


@pytest.mark.parametrize("terminal", [CaseState.RESOLVED, CaseState.CLOSED])
def test_terminal_states_accept_nothing(terminal):
    for target in CaseState:
        assert not can_transition(terminal, target)
    assert next_states(terminal) == set()


def test_cases_cannot_move_backwards():
    assert not can_transition(CaseState.SENT, CaseState.PENDING_APPROVAL)
    assert not can_transition(CaseState.AWAITING_RESPONSE, CaseState.SENT)
    assert not can_transition(CaseState.VERIFIED, CaseState.NEW)


def test_rejection_message_lists_legal_alternatives():
    with pytest.raises(InvalidTransition) as exc:
        assert_transition(CaseState.NEW, CaseState.RESOLVED)
    assert "verified" in str(exc.value)


def test_any_open_case_can_be_closed():
    for state in CaseState:
        if not state.is_terminal:
            assert can_transition(state, CaseState.CLOSED)
