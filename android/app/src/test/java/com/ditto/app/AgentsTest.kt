package com.ditto.app

import com.ditto.app.data.demo.DemoCorpus
import com.ditto.app.domain.agents.MockActionPlanningAgent
import com.ditto.app.domain.agents.MockFollowUpAgent
import com.ditto.app.domain.agents.MockVerificationAgent
import com.ditto.app.domain.model.ActionType
import com.ditto.app.domain.model.CandidateMatch
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.Classification
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.Severity
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AgentsTest {

    private val verifier = MockVerificationAgent()
    private val planner = MockActionPlanningAgent()
    private val followUp = MockFollowUpAgent()

    private fun content(id: String) = DemoCorpus.content.first { it.id == id }
    private fun candidate(id: String) =
        DemoCorpus.candidates.first { it.match.id == id }.match

    // ---------------------------------------------------------------- verification

    @Test
    fun `verification classifies seeded corpus in line with ground truth`() = runTest {
        for (seeded in DemoCorpus.candidates) {
            val c = content(seeded.match.contentId)
            val result = verifier.verify(c, seeded.match)
            assertEquals(
                "Candidate ${seeded.match.id} misclassified",
                seeded.groundTruth,
                result.classification.wire
            )
        }
    }

    @Test
    fun `high similarity repost gets high confidence`() = runTest {
        val result = verifier.verify(content("content_003"), candidate("cand_002"))
        assertEquals(Classification.GENUINE_REPOST, result.classification)
        assertTrue("confidence was ${result.confidence}", result.confidence >= 0.80)
    }

    @Test
    fun `monetized high-reach repost is high severity`() = runTest {
        val result = verifier.verify(content("content_003"), candidate("cand_002"))
        assertEquals(Severity.HIGH, result.severity)
    }

    @Test
    fun `content predating the original is not a repost`() = runTest {
        // cand_003 was posted before the original and has weak hash agreement.
        val result = verifier.verify(content("content_002"), candidate("cand_003"))
        assertEquals(Classification.FALSE_POSITIVE, result.classification)
    }

    @Test
    fun `high face similarity with low hash similarity reads as likeness misuse`() = runTest {
        val result = verifier.verify(content("content_005"), candidate("cand_005"))
        assertEquals(Classification.GENUINE_LIKENESS_MISUSE, result.classification)
        assertEquals(Severity.HIGH, result.severity)
    }

    @Test
    fun `verification is deterministic across runs`() = runTest {
        val a = verifier.verify(content("content_001"), candidate("cand_001"))
        val b = verifier.verify(content("content_001"), candidate("cand_001"))
        assertEquals(a.classification, b.classification)
        assertEquals(a.confidence, b.confidence, 0.0)
        assertEquals(a.severity, b.severity)
    }

    @Test
    fun `every verification exposes signals and a summary`() = runTest {
        val result = verifier.verify(content("content_001"), candidate("cand_001"))
        assertTrue(result.signals.isNotEmpty())
        assertTrue(result.summary.isNotBlank())
        assertTrue(result.evidenceSummary.isNotBlank())
    }

    // ---------------------------------------------------------------- action planning

    @Test
    fun `false positive never produces outbound action`() = runTest {
        val c = content("content_002")
        val cand = candidate("cand_003")
        val v = verifier.verify(c, cand)
        val plan = planner.plan(c, cand, v, 0)
        assertEquals(ActionType.LOG_ONLY, plan.action)
        assertTrue("draft must be empty", plan.draftBody.isBlank())
    }

    @Test
    fun `first-time non-monetized repost gets an attribution request`() = runTest {
        val c = content("content_001")
        val cand = candidate("cand_001")
        val v = verifier.verify(c, cand)
        val plan = planner.plan(c, cand, v, 0)
        assertEquals(ActionType.ATTRIBUTION_REQUEST, plan.action)
        assertTrue(plan.draftBody.isNotBlank())
    }

    @Test
    fun `monetized high-reach repost escalates to a formal takedown`() = runTest {
        val c = content("content_003")
        val cand = candidate("cand_002")
        val v = verifier.verify(c, cand)
        val plan = planner.plan(c, cand, v, 0)
        assertEquals(ActionType.FORMAL_TAKEDOWN, plan.action)
    }

    @Test
    fun `confirmed match on a small account still gets an attribution request`() = runTest {
        // Regression: a confident repost must never be silently logged just because
        // the infringing account is small and non-monetized.
        val c = content("content_001")
        val cand = candidate("cand_001").copy(followerCount = 400, monetized = false)
        val v = com.ditto.app.domain.model.VerificationResult(
            classification = Classification.GENUINE_REPOST,
            confidence = 0.95, severity = Severity.LOW,
            summary = "", signals = emptyList(), evidenceSummary = "", engine = "test"
        )
        val plan = planner.plan(c, cand, v, 0)
        assertEquals(ActionType.ATTRIBUTION_REQUEST, plan.action)
        assertTrue(plan.factors.any { it.contains("confirmed-match floor") })
    }

    @Test
    fun `low confidence match requires human review`() = runTest {
        val c = content("content_001")
        val cand = candidate("cand_001").copy(followerCount = 400, monetized = false)
        val v = com.ditto.app.domain.model.VerificationResult(
            classification = Classification.GENUINE_REPOST,
            confidence = 0.62, severity = Severity.LOW,
            summary = "", signals = emptyList(), evidenceSummary = "", engine = "test"
        )
        assertEquals(ActionType.REVIEW_REQUEST, planner.plan(c, cand, v, 0).action)
    }

    @Test
    fun `escalation never proposes a weaker action than already attempted`() = runTest {
        val c = content("content_001")
        val cand = candidate("cand_001")
        val v = verifier.verify(c, cand)
        val plan = planner.plan(c, cand, v, priorEscalationLevel = 2)
        assertTrue(plan.action.tier >= 2)
    }

    @Test
    fun `policy exposes the factors behind its decision`() = runTest {
        val c = content("content_001")
        val cand = candidate("cand_001")
        val v = verifier.verify(c, cand)
        val plan = planner.plan(c, cand, v, 0)
        assertTrue(plan.factors.isNotEmpty())
        assertTrue(plan.factors.any { it.contains("escalation score", ignoreCase = true) })
        assertTrue(plan.reasoning.isNotBlank())
    }

    @Test
    fun `tone selection changes the drafted message`() = runTest {
        val c = content("content_001")
        val cand = candidate("cand_001")
        val v = verifier.verify(c, cand)
        val professional = planner.plan(
            c, cand, v, 0, com.ditto.app.domain.model.MessageTone.PROFESSIONAL
        )
        val firm = planner.plan(c, cand, v, 0, com.ditto.app.domain.model.MessageTone.FIRM)
        assertTrue(professional.draftBody != firm.draftBody)
    }

    // ---------------------------------------------------------------- follow-up

    private fun caseIn(state: CaseState, tier: Int, cycles: Int = 0): Case {
        val cand = candidate("cand_001")
        return Case(
            id = "DIT-TEST",
            contentId = cand.contentId,
            contentTitle = "Test",
            contentPaletteSeed = 1,
            candidate = cand,
            verification = null,
            plan = com.ditto.app.domain.model.ActionPlan(
                action = ActionType.entries.first { it.tier == tier },
                priority = Severity.MEDIUM,
                reasoning = "",
                factors = emptyList(),
                draftSubject = "",
                draftBody = "",
                tone = com.ditto.app.domain.model.MessageTone.PROFESSIONAL,
                engine = "test"
            ),
            state = state,
            escalationLevel = tier,
            followUpCount = cycles,
            createdAt = 0, updatedAt = 0, nextFollowUpAt = null, lastActionAt = null
        )
    }

    @Test
    fun `no response escalates and raises the action tier`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 1)
        val d = followUp.evaluate(case, FollowUpOutcome.NO_RESPONSE)
        assertEquals(CaseState.ESCALATED, d.nextState)
        assertEquals(ActionType.FORMAL_TAKEDOWN, d.escalateTo)
        assertTrue(d.reasoning.isNotBlank())
    }

    @Test
    fun `content removed resolves the case`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 1)
        val d = followUp.evaluate(case, FollowUpOutcome.CONTENT_REMOVED)
        assertEquals(CaseState.RESOLVED, d.nextState)
        assertNull(d.escalateTo)
    }

    @Test
    fun `attribution added resolves without escalating`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 1)
        val d = followUp.evaluate(case, FollowUpOutcome.ATTRIBUTION_ADDED)
        assertEquals(CaseState.RESOLVED, d.nextState)
        assertNull(d.escalateTo)
    }

    @Test
    fun `partial response holds the case at its current tier`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 1)
        val d = followUp.evaluate(case, FollowUpOutcome.PARTIAL_RESPONSE)
        assertEquals(CaseState.AWAITING_RESPONSE, d.nextState)
        assertNull(d.escalateTo)
    }

    @Test
    fun `hostile response escalates straight to a formal notice`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 0)
        val d = followUp.evaluate(case, FollowUpOutcome.HOSTILE_RESPONSE)
        assertEquals(CaseState.ESCALATED, d.nextState)
        assertEquals(ActionType.FORMAL_TAKEDOWN, d.escalateTo)
    }

    @Test
    fun `escalation stops at the ceiling instead of inventing a higher tier`() = runTest {
        val case = caseIn(CaseState.ESCALATED, tier = 2, cycles = 3)
        val d = followUp.evaluate(case, FollowUpOutcome.NO_RESPONSE)
        assertNull("no tier above formal takedown exists", d.escalateTo)
        assertEquals(CaseState.ESCALATED, d.nextState)
    }

    @Test
    fun `follow-up never returns a state the machine would refuse`() = runTest {
        // A resolved case is terminal; the agent must not force it elsewhere.
        val case = caseIn(CaseState.RESOLVED, tier = 1)
        FollowUpOutcome.entries.forEach { outcome ->
            val d = followUp.evaluate(case, outcome)
            assertTrue(
                "outcome $outcome produced illegal ${d.nextState}",
                d.nextState == CaseState.RESOLVED ||
                    com.ditto.app.domain.statemachine.CaseStateMachine
                        .canTransition(CaseState.RESOLVED, d.nextState)
            )
        }
    }

    @Test
    fun `every follow-up decision carries a headline and reasoning`() = runTest {
        val case = caseIn(CaseState.AWAITING_RESPONSE, tier = 1)
        FollowUpOutcome.entries.forEach { outcome ->
            val d = followUp.evaluate(case, outcome)
            assertTrue(d.headline.isNotBlank())
            assertTrue(d.reasoning.isNotBlank())
        }
    }

    // ---------------------------------------------------------------- corpus

    @Test
    fun `every seeded candidate maps to real content`() {
        DemoCorpus.candidates.forEach { seeded ->
            assertNotNull(
                "orphan candidate ${seeded.match.id}",
                DemoCorpus.content.firstOrNull { it.id == seeded.match.contentId }
            )
        }
    }

    @Test
    fun `corpus contains both positive and negative examples`() {
        val truths = DemoCorpus.candidates.map { it.groundTruth }.toSet()
        assertTrue(truths.contains("genuine_repost"))
        assertTrue(truths.contains("false_positive"))
        assertTrue(truths.contains("genuine_likeness_misuse"))
    }
}
