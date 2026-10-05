package com.ditto.app.domain.agents

import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.FollowUpDecision
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.statemachine.CaseStateMachine

/**
 * The persistence layer that makes Ditto agentic (report §6, layer 6).
 *
 * Given a case and an observed outcome from the weekly re-check, the agent decides
 * whether to wait, nudge, escalate, or resolve — then requests a state transition.
 * The transition is validated by [CaseStateMachine]; the agent cannot force an
 * illegal state.
 */
class MockFollowUpAgent : FollowUpAgent {

    override val displayName: String = "Demo Follow-Up Agent (weekly re-evaluation)"

    override suspend fun evaluate(case: Case, observed: FollowUpOutcome): FollowUpDecision {
        val current = case.state
        val currentTier = case.plan?.action?.tier ?: 0
        val rounds = case.followUpCount + 1

        val decision = when (observed) {
            FollowUpOutcome.CONTENT_REMOVED -> FollowUpDecision(
                outcome = observed,
                nextState = CaseState.RESOLVED,
                escalateTo = null,
                headline = "Resolution confirmed.",
                reasoning = "The reported content is no longer reachable at the recorded " +
                    "URL. The objective of this case has been met, so no further outreach " +
                    "is scheduled and the case is closed as resolved."
            )

            FollowUpOutcome.ATTRIBUTION_ADDED -> FollowUpDecision(
                outcome = observed,
                nextState = CaseState.RESOLVED,
                escalateTo = null,
                headline = "Attribution confirmed.",
                reasoning = "The caption on the reported post now credits the original " +
                    "creator. The requested remedy was granted in full, so the case is " +
                    "resolved without escalating to a formal notice."
            )

            FollowUpOutcome.PARTIAL_RESPONSE -> FollowUpDecision(
                outcome = observed,
                nextState = CaseState.AWAITING_RESPONSE,
                escalateTo = null,
                headline = "Partial response — holding at current tier.",
                reasoning = "The account acknowledged the request but has not yet added " +
                    "attribution. Good-faith engagement is present, so escalating now would " +
                    "be disproportionate. The case stays at its current tier and will be " +
                    "re-checked at the next weekly interval."
            )

            FollowUpOutcome.HOSTILE_RESPONSE -> {
                // A hostile reply removes the case for a voluntary remedy: skip the
                // intermediate nudge and go straight to the highest tier.
                val next = CaseStateMachine.transition(current, CaseState.ESCALATED)
                val target = ActionType.FORMAL_TAKEDOWN
                FollowUpDecision(
                    outcome = observed,
                    nextState = if (next is CaseStateMachine.TransitionResult.Success)
                        CaseState.ESCALATED else current,
                    escalateTo = target,
                    headline = "Case escalated — voluntary resolution declined.",
                    reasoning = "The account explicitly refused to add attribution. A " +
                        "further request at the same tier has no realistic prospect of " +
                        "success, so the case escalates directly to ${target.label} rather " +
                        "than spending another weekly cycle at the current tier."
                )
            }

            FollowUpOutcome.NO_RESPONSE -> {
                val nextTier = (currentTier + 1).coerceAtMost(ActionType.FORMAL_TAKEDOWN.tier)
                val target = ActionType.entries.first { it.tier == nextTier }
                val atCeiling = currentTier >= ActionType.FORMAL_TAKEDOWN.tier

                if (atCeiling) {
                    FollowUpDecision(
                        outcome = observed,
                        nextState = CaseState.ESCALATED,
                        escalateTo = null,
                        headline = "No response — escalation ceiling reached.",
                        reasoning = "A formal notice has already been issued and $rounds " +
                            "follow-up cycle${if (rounds == 1) "" else "s"} " +
                            "${if (rounds == 1) "has" else "have"} passed with no " +
                            "response. No higher " +
                            "automated tier exists; the case remains escalated and is " +
                            "flagged for the creator to pursue a platform-level claim."
                    )
                } else {
                    FollowUpDecision(
                        outcome = observed,
                        nextState = CaseState.ESCALATED,
                        escalateTo = target,
                        headline = "No response — escalating.",
                        reasoning = "No reply was detected after the configured interval " +
                            "(follow-up cycle $rounds). Increasing escalation level from " +
                            "${case.plan?.action?.label ?: "the previous action"} to " +
                            "${target.label}. The escalation is proposed, not sent — it " +
                            "returns to the approval gate before any outbound action."
                    )
                }
            }
        }

        // Guard: never return a state the machine would refuse.
        val validated = if (decision.nextState == current ||
            CaseStateMachine.canTransition(current, decision.nextState)
        ) {
            decision
        } else {
            decision.copy(
                nextState = current,
                headline = "No state change.",
                reasoning = decision.reasoning +
                    " (State held at ${current.label}: the proposed transition is not " +
                    "legal from this state.)"
            )
        }
        return validated
    }
}
