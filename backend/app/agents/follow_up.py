"""Follow-Up / Persistence Agent — the component that makes Ditto agentic.

Given a case and an observed outcome from the weekly re-check, decides whether to
wait, nudge, escalate or resolve, then requests a transition. The state machine
validates it; the agent cannot force an illegal state.
"""
from __future__ import annotations

from app.agents.base import FollowUpDecision
from app.models.enums import ActionType, CaseState, FollowUpOutcome
from app.services.state_machine import can_transition


class MockFollowUpAgent:
    display_name = "Demo Follow-Up Agent (weekly re-evaluation)"

    def evaluate(self, case, observed: FollowUpOutcome) -> FollowUpDecision:
        current = CaseState(case.current_state)
        current_tier = (
            ActionType(case.recommended_action).tier if case.recommended_action else 0
        )
        rounds = case.follow_up_count + 1

        if observed is FollowUpOutcome.CONTENT_REMOVED:
            decision = FollowUpDecision(
                observed, CaseState.RESOLVED, None,
                "Resolution confirmed.",
                "The reported content is no longer reachable at the recorded URL. The "
                "objective of this case has been met, so no further outreach is scheduled.",
            )
        elif observed is FollowUpOutcome.ATTRIBUTION_ADDED:
            decision = FollowUpDecision(
                observed, CaseState.RESOLVED, None,
                "Attribution confirmed.",
                "The caption on the reported post now credits the original creator. The "
                "requested remedy was granted in full, so the case resolves without "
                "escalating to a formal notice.",
            )
        elif observed is FollowUpOutcome.PARTIAL_RESPONSE:
            decision = FollowUpDecision(
                observed, CaseState.AWAITING_RESPONSE, None,
                "Partial response — holding at current tier.",
                "The account acknowledged the request but has not yet added attribution. "
                "Good-faith engagement is present, so escalating now would be "
                "disproportionate. The case will be re-checked next interval.",
            )
        elif observed is FollowUpOutcome.HOSTILE_RESPONSE:
            decision = FollowUpDecision(
                observed, CaseState.ESCALATED, ActionType.FORMAL_TAKEDOWN,
                "Case escalated — voluntary resolution declined.",
                "The account explicitly refused to add attribution. A further request at "
                "the same tier has no realistic prospect of success, so the case escalates "
                "directly to a formal takedown notice.",
            )
        else:  # NO_RESPONSE
            at_ceiling = current_tier >= ActionType.FORMAL_TAKEDOWN.tier
            if at_ceiling:
                decision = FollowUpDecision(
                    observed, CaseState.ESCALATED, None,
                    "No response — escalation ceiling reached.",
                    f"A formal notice has already been issued and {rounds} follow-up "
                    f"cycle{'' if rounds == 1 else 's'} "
                    f"{'has' if rounds == 1 else 'have'} passed with no response. "
                    "No higher automated tier exists; "
                    "the case is flagged for a platform-level claim.",
                )
            else:
                target = next(
                    a for a in ActionType if a.tier == min(current_tier + 1, 2)
                )
                decision = FollowUpDecision(
                    observed, CaseState.ESCALATED, target,
                    "No response — escalating.",
                    "No reply was detected after the configured interval (follow-up cycle "
                    f"{rounds}). Increasing escalation level to {target.label}. The "
                    "escalation is proposed, not sent — it returns to the approval gate.",
                )

        # Guard: never return a state the machine would refuse.
        if decision.next_state != current and not can_transition(current, decision.next_state):
            decision = FollowUpDecision(
                decision.outcome, current, None,
                "No state change.",
                decision.reasoning
                + f" (State held at {current.value}: the proposed transition is not legal.)",
            )
        return decision
