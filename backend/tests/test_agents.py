"""Agent behaviour against the labelled synthetic corpus."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.agents.action_planning import MockActionPlanningAgent
from app.agents.follow_up import MockFollowUpAgent
from app.agents.verification import MockVerificationAgent
from app.discovery import corpus
from app.models.enums import (
    ActionType,
    CaseState,
    Classification,
    FollowUpOutcome,
    MessageTone,
    Severity,
)

verifier = MockVerificationAgent()
planner = MockActionPlanningAgent()
follow_up = MockFollowUpAgent()


@dataclass
class FakeContent:
    id: str
    title: str
    perceptual_hash: str
    published_at: datetime


@dataclass
class FakeCandidate:
    id: str
    platform: str
    account_name: str
    account_handle: str
    source_url: str
    caption: str
    follower_count: int
    monetized: bool
    hash_similarity: float
    visual_similarity: float
    caption_similarity: float
    face_similarity: float
    posted_at: datetime
    transform_note: str


def _content(cid: str) -> FakeContent:
    item = next(c for c in corpus.CONTENT if c.id == cid)
    return FakeContent(
        item.id, item.title, item.perceptual_hash, corpus.content_published_at(item)
    )


def _candidate(cand_id: str) -> FakeCandidate:
    s = next(c for c in corpus.CANDIDATES if c.id == cand_id)
    return FakeCandidate(
        s.id, s.platform, s.account_name, s.account_handle, s.source_url, s.caption,
        s.follower_count, s.monetized, s.hash_similarity, s.visual_similarity,
        s.caption_similarity, s.face_similarity, corpus.candidate_posted_at(s),
        s.transform_note,
    )


# ---------------------------------------------------------------- verification


@pytest.mark.parametrize("seeded", corpus.CANDIDATES, ids=lambda s: s.id)
def test_verification_matches_ground_truth(seeded):
    result = verifier.verify(_content(seeded.content_id), _candidate(seeded.id))
    assert result.classification.value == seeded.ground_truth


def test_monetized_high_reach_repost_is_high_severity():
    r = verifier.verify(_content("content_003"), _candidate("cand_002"))
    assert r.severity is Severity.HIGH
    assert r.confidence >= 0.80


def test_likeness_signature_is_face_match_without_hash_match():
    r = verifier.verify(_content("content_005"), _candidate("cand_005"))
    assert r.classification is Classification.GENUINE_LIKENESS_MISUSE
    assert r.severity is Severity.HIGH


def test_verification_is_deterministic():
    a = verifier.verify(_content("content_001"), _candidate("cand_001"))
    b = verifier.verify(_content("content_001"), _candidate("cand_001"))
    assert (a.classification, a.confidence, a.severity) == (
        b.classification, b.confidence, b.severity
    )


def test_verification_always_explains_itself():
    r = verifier.verify(_content("content_001"), _candidate("cand_001"))
    assert r.summary and r.evidence_summary and r.signals


# ---------------------------------------------------------------- action planning


def test_false_positive_produces_no_outbound_action():
    c, cand = _content("content_002"), _candidate("cand_003")
    plan = planner.plan(c, cand, verifier.verify(c, cand), 0)
    assert plan.action is ActionType.LOG_ONLY
    assert plan.draft_body == ""


def test_first_incident_non_monetized_gets_attribution_request():
    c, cand = _content("content_001"), _candidate("cand_001")
    plan = planner.plan(c, cand, verifier.verify(c, cand), 0)
    assert plan.action is ActionType.ATTRIBUTION_REQUEST
    assert plan.draft_body


def test_monetized_high_reach_escalates_to_takedown():
    c, cand = _content("content_003"), _candidate("cand_002")
    plan = planner.plan(c, cand, verifier.verify(c, cand), 0)
    assert plan.action is ActionType.FORMAL_TAKEDOWN


def test_confirmed_match_on_a_small_account_still_gets_attribution():
    """Regression: a confident repost must never be silently logged just because the
    infringing account is small and non-monetized."""
    from app.agents.action_planning import CONFIRMED_MATCH_CONFIDENCE, T_ATTRIBUTION
    from app.agents.base import Signal, VerificationResult

    c, cand = _content("content_001"), _candidate("cand_001")
    cand.follower_count = 400      # tiny reach
    cand.monetized = False
    v = VerificationResult(
        classification=Classification.GENUINE_REPOST,
        confidence=0.95, severity=Severity.LOW, summary="", signals=[],
    )
    plan = planner.plan(c, cand, v, 0)
    assert v.confidence >= CONFIRMED_MATCH_CONFIDENCE
    assert plan.action is ActionType.ATTRIBUTION_REQUEST
    assert any("confirmed-match floor" in f for f in plan.factors)


def test_low_confidence_match_requires_human_review():
    """The floor must not swallow genuinely weak matches."""
    from app.agents.base import VerificationResult

    c, cand = _content("content_001"), _candidate("cand_001")
    cand.follower_count = 400
    cand.monetized = False
    v = VerificationResult(
        classification=Classification.GENUINE_REPOST,
        confidence=0.62, severity=Severity.LOW, summary="", signals=[],
    )
    assert planner.plan(c, cand, v, 0).action is ActionType.REVIEW_REQUEST


def test_ratchet_never_proposes_a_weaker_tier():
    c, cand = _content("content_001"), _candidate("cand_001")
    plan = planner.plan(c, cand, verifier.verify(c, cand), prior_escalation_level=2)
    assert plan.action.tier >= 2


def test_policy_exposes_its_factors():
    c, cand = _content("content_001"), _candidate("cand_001")
    plan = planner.plan(c, cand, verifier.verify(c, cand), 0)
    assert any("escalation score" in f.lower() for f in plan.factors)


def test_tone_changes_the_draft():
    c, cand = _content("content_001"), _candidate("cand_001")
    v = verifier.verify(c, cand)
    assert (
        planner.plan(c, cand, v, 0, MessageTone.PROFESSIONAL).draft_body
        != planner.plan(c, cand, v, 0, MessageTone.FIRM).draft_body
    )


# ---------------------------------------------------------------- follow-up


@dataclass
class FakeCase:
    current_state: str
    recommended_action: str
    follow_up_count: int = 0


def _case(state: CaseState, action: ActionType, cycles: int = 0) -> FakeCase:
    return FakeCase(state.value, action.value, cycles)


def test_no_response_escalates_a_tier():
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.ATTRIBUTION_REQUEST),
        FollowUpOutcome.NO_RESPONSE,
    )
    assert d.next_state is CaseState.ESCALATED
    assert d.escalate_to is ActionType.FORMAL_TAKEDOWN


def test_content_removed_resolves():
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.ATTRIBUTION_REQUEST),
        FollowUpOutcome.CONTENT_REMOVED,
    )
    assert d.next_state is CaseState.RESOLVED
    assert d.escalate_to is None


def test_attribution_added_resolves_without_escalating():
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.ATTRIBUTION_REQUEST),
        FollowUpOutcome.ATTRIBUTION_ADDED,
    )
    assert d.next_state is CaseState.RESOLVED
    assert d.escalate_to is None


def test_partial_response_holds_tier():
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.ATTRIBUTION_REQUEST),
        FollowUpOutcome.PARTIAL_RESPONSE,
    )
    assert d.next_state is CaseState.AWAITING_RESPONSE
    assert d.escalate_to is None


def test_hostile_response_jumps_to_formal_notice():
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.LOG_ONLY),
        FollowUpOutcome.HOSTILE_RESPONSE,
    )
    assert d.escalate_to is ActionType.FORMAL_TAKEDOWN


def test_escalation_stops_at_the_ceiling():
    d = follow_up.evaluate(
        _case(CaseState.ESCALATED, ActionType.FORMAL_TAKEDOWN, cycles=3),
        FollowUpOutcome.NO_RESPONSE,
    )
    assert d.escalate_to is None
    assert d.next_state is CaseState.ESCALATED


@pytest.mark.parametrize("outcome", list(FollowUpOutcome))
def test_follow_up_never_forces_an_illegal_state(outcome):
    from app.services.state_machine import can_transition

    case = _case(CaseState.RESOLVED, ActionType.ATTRIBUTION_REQUEST)
    d = follow_up.evaluate(case, outcome)
    assert d.next_state is CaseState.RESOLVED or can_transition(
        CaseState.RESOLVED, d.next_state
    )


@pytest.mark.parametrize("outcome", list(FollowUpOutcome))
def test_every_decision_is_explained(outcome):
    d = follow_up.evaluate(
        _case(CaseState.AWAITING_RESPONSE, ActionType.ATTRIBUTION_REQUEST), outcome
    )
    assert d.headline and d.reasoning
