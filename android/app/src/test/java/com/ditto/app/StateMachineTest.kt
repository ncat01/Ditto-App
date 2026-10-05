package com.ditto.app

import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.statemachine.CaseStateMachine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StateMachineTest {

    @Test
    fun `valid happy path transitions are accepted`() {
        val path = listOf(
            CaseState.NEW to CaseState.VERIFIED,
            CaseState.VERIFIED to CaseState.PENDING_APPROVAL,
            CaseState.PENDING_APPROVAL to CaseState.SENT,
            CaseState.SENT to CaseState.AWAITING_RESPONSE,
            CaseState.AWAITING_RESPONSE to CaseState.ESCALATED,
            CaseState.ESCALATED to CaseState.RESOLVED
        )
        path.forEach { (from, to) ->
            assertTrue(
                "$from -> $to should be allowed",
                CaseStateMachine.canTransition(from, to)
            )
        }
    }

    @Test
    fun `awaiting response can resolve directly without escalating`() {
        assertTrue(CaseStateMachine.canTransition(CaseState.AWAITING_RESPONSE, CaseState.RESOLVED))
    }

    @Test
    fun `escalated can return to awaiting response for a further cycle`() {
        assertTrue(
            CaseStateMachine.canTransition(CaseState.ESCALATED, CaseState.AWAITING_RESPONSE)
        )
    }

    @Test
    fun `an escalated case can be approved and dispatched again`() {
        // Regression: the Follow-Up Agent escalates to a higher action tier and returns
        // the case to the approval gate. If ESCALATED -> SENT were illegal, that
        // escalation could never be acted on and the loop would dead-end.
        assertTrue(CaseStateMachine.canTransition(CaseState.ESCALATED, CaseState.SENT))
        assertTrue(CaseStateMachine.canTransition(CaseState.SENT, CaseState.AWAITING_RESPONSE))
    }

    @Test
    fun `escalation loop can run for multiple cycles`() {
        var state = CaseState.AWAITING_RESPONSE
        repeat(3) {
            listOf(CaseState.ESCALATED, CaseState.SENT, CaseState.AWAITING_RESPONSE)
                .forEach { next ->
                    assertTrue(
                        "cycle stalled at $state -> $next",
                        CaseStateMachine.canTransition(state, next)
                    )
                    state = next
                }
        }
        assertTrue(CaseStateMachine.canTransition(state, CaseState.RESOLVED))
    }

    @Test
    fun `new cannot jump straight to resolved`() {
        assertFalse(CaseStateMachine.canTransition(CaseState.NEW, CaseState.RESOLVED))
        val result = CaseStateMachine.transition(CaseState.NEW, CaseState.RESOLVED)
        assertTrue(result is CaseStateMachine.TransitionResult.Rejected)
    }

    @Test
    fun `cannot skip the approval gate`() {
        // VERIFIED must pass through PENDING_APPROVAL before anything is sent.
        assertFalse(CaseStateMachine.canTransition(CaseState.VERIFIED, CaseState.SENT))
        assertFalse(CaseStateMachine.canTransition(CaseState.NEW, CaseState.SENT))
    }

    @Test
    fun `terminal states accept no transitions`() {
        CaseState.entries.forEach { target ->
            assertFalse(
                "RESOLVED -> $target must be rejected",
                CaseStateMachine.canTransition(CaseState.RESOLVED, target)
            )
            assertFalse(
                "CLOSED -> $target must be rejected",
                CaseStateMachine.canTransition(CaseState.CLOSED, target)
            )
        }
    }

    @Test
    fun `a case cannot move backwards`() {
        assertFalse(CaseStateMachine.canTransition(CaseState.SENT, CaseState.PENDING_APPROVAL))
        assertFalse(CaseStateMachine.canTransition(CaseState.AWAITING_RESPONSE, CaseState.SENT))
        assertFalse(CaseStateMachine.canTransition(CaseState.VERIFIED, CaseState.NEW))
    }

    @Test
    fun `rejection message names the legal alternatives`() {
        val result = CaseStateMachine.transition(CaseState.NEW, CaseState.RESOLVED)
        val reason = (result as CaseStateMachine.TransitionResult.Rejected).reason
        assertTrue(reason.contains("verified"))
        assertTrue(reason.contains("new -> resolved"))
    }

    @Test
    fun `success result carries the new state`() {
        val result = CaseStateMachine.transition(CaseState.NEW, CaseState.VERIFIED)
        assertEquals(
            CaseState.VERIFIED,
            (result as CaseStateMachine.TransitionResult.Success).state
        )
    }

    @Test
    fun `every case can always be closed except from a terminal state`() {
        CaseState.entries.filter { !it.isTerminal }.forEach { state ->
            assertTrue(
                "$state should be closable",
                CaseStateMachine.canTransition(state, CaseState.CLOSED)
            )
        }
    }

    @Test
    fun `open and terminal flags agree with the transition table`() {
        assertTrue(CaseState.RESOLVED.isTerminal)
        assertTrue(CaseState.CLOSED.isTerminal)
        assertTrue(CaseState.AWAITING_RESPONSE.isOpen)
        assertTrue(CaseStateMachine.nextStates(CaseState.RESOLVED).isEmpty())
    }
}
