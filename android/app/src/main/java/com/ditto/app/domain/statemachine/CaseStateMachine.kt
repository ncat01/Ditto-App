package com.ditto.app.domain.statemachine

import com.ditto.app.domain.model.CaseState

/**
 * Authoritative case lifecycle. The UI never sets a state directly; it requests a
 * transition and this object decides whether the transition is legal.
 *
 * Report §39: "Do NOT allow arbitrary status changes from the UI. The backend/domain
 * layer must enforce valid transitions."
 */
object CaseStateMachine {

    private val allowed: Map<CaseState, Set<CaseState>> = mapOf(
        CaseState.NEW to setOf(CaseState.VERIFIED, CaseState.CLOSED),
        CaseState.VERIFIED to setOf(CaseState.PENDING_APPROVAL, CaseState.CLOSED),
        CaseState.PENDING_APPROVAL to setOf(CaseState.SENT, CaseState.CLOSED),
        CaseState.SENT to setOf(CaseState.AWAITING_RESPONSE, CaseState.RESOLVED, CaseState.CLOSED),
        CaseState.AWAITING_RESPONSE to setOf(
            CaseState.ESCALATED, CaseState.RESOLVED, CaseState.CLOSED
        ),
        // An escalated case returns to the approval gate at a higher action tier;
        // approving it dispatches again, hence ESCALATED -> SENT.
        CaseState.ESCALATED to setOf(
            CaseState.SENT, CaseState.AWAITING_RESPONSE,
            CaseState.RESOLVED, CaseState.CLOSED
        ),
        // Terminal states accept no further transitions.
        CaseState.RESOLVED to emptySet(),
        CaseState.CLOSED to emptySet()
    )

    fun canTransition(from: CaseState, to: CaseState): Boolean =
        allowed[from]?.contains(to) == true

    fun nextStates(from: CaseState): Set<CaseState> = allowed[from].orEmpty()

    /**
     * @return the new state, or a [TransitionError] describing why it was refused.
     */
    fun transition(from: CaseState, to: CaseState): TransitionResult =
        if (canTransition(from, to)) {
            TransitionResult.Success(to)
        } else {
            TransitionResult.Rejected(
                "Illegal transition ${from.wire} -> ${to.wire}. " +
                    "Allowed from ${from.wire}: " +
                    (nextStates(from).joinToString(", ") { it.wire }.ifEmpty { "none (terminal)" })
            )
        }

    sealed interface TransitionResult {
        data class Success(val state: CaseState) : TransitionResult
        data class Rejected(val reason: String) : TransitionResult
    }
}

class TransitionError(message: String) : IllegalStateException(message)
