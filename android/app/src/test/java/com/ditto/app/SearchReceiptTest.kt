package com.ditto.app

import com.ditto.app.ui.screens.readSearchReceipt
import com.ditto.app.ui.screens.searchReceiptId
import com.ditto.app.core.BackendRequestException
import com.ditto.app.core.isDefiniteBackendRejection
import org.junit.Assert.*
import org.junit.Test

class SearchReceiptTest {
    @Test
    fun confirmedRejectionsAllowANewSearchButLostResponsesKeepTheirReceipt() {
        listOf(400, 401, 403, 404, 409, 422, 429).forEach { status ->
            assertTrue("Confirmed $status must clear the pending request", isDefiniteBackendRejection(BackendRequestException("Search rejected",status=status)))
        }
        listOf(null, 200, 202, 301, 408, 500, 502, 503, 504).forEach { status ->
            assertFalse("Status $status must retain recovery", isDefiniteBackendRejection(BackendRequestException("Search uncertain",status=status)))
        }
        assertFalse(isDefiniteBackendRejection(java.net.SocketTimeoutException("Response lost")))
    }
    @Test
    fun aLostSubmissionFindsOnlyItsOwnIdempotentReceipt() {
        val id = searchReceiptId("user1", "original1", "request1")
        assertEquals("0a9a66f87f4f8dd8d4d87511387aef0c", id)
        assertEquals(id, searchReceiptId("user1", "original1", "request1"))
        assertNotEquals(id, searchReceiptId("user1", "original1", "olderRequest"))
        assertNotEquals(id, searchReceiptId("otherUser", "original1", "request1"))
        assertNotEquals(id, searchReceiptId("user1", "otherOriginal", "request1"))
    }
    @Test
    fun onlyAnExplicitCompletedEmptyArrayMeansNoIndexedMatches() {
        val receipt = readSearchReceipt("""{"jobId":"job-1","state":"complete","result":{"results":[]}}""")
        assertEquals("complete", receipt.state)
        assertTrue(receipt.leads.isEmpty())
        listOf("""{"jobId":"job-1","state":"complete","result":{}}""",
            """{"jobId":"job-1","state":"complete","result":null}""",
            """{"jobId":"job-1","state":"complete","result":{"results":null}}""").forEach { raw ->
            assertTrue(runCatching { readSearchReceipt(raw) }.isFailure)
        }
    }

    @Test
    fun failedAndInterruptedSearchesRemainFailuresNotZeroMatches() {
        listOf("error", "unknown", "cancelled").forEach { state ->
            val receipt = readSearchReceipt("""{"id":"job-2","state":"$state","error":"Search stopped"}""")
            assertEquals(state, receipt.state)
            assertFalse(receipt.active)
            assertEquals("Search stopped", receipt.error)
            assertNotEquals("complete", receipt.state)
        }
    }

    @Test
    fun queuedAndRunningReceiptsRestoreProgressUsingBothApiIdFields() {
        assertTrue(readSearchReceipt("""{"jobId":"job-3","state":"queued"}""").active)
        assertTrue(readSearchReceipt("""{"id":"job-3","state":"running"}""").active)
        assertNull(readSearchReceipt("""{"jobId":null,"state":null,"result":null}""").id)
        assertTrue(runCatching { readSearchReceipt("""{"jobId":"job-3","state":"mystery"}""") }.isFailure)
    }

    @Test
    fun exactInstagramSourceIsPreservedButUnsafeSourcesAreRejected() {
        val receipt = readSearchReceipt("""{"jobId":"job-4","state":"complete","result":{"results":[{"url":"https://www.instagram.com/reel/example/","title":"A source","matchType":"exact","source":"Instagram"}]}}""")
        assertEquals("https://www.instagram.com/reel/example/", receipt.leads.single().url)
        assertTrue(receipt.leads.single().exact)
        listOf("javascript:alert(1)", "https://user:password@example.com/source").forEach { url ->
            assertTrue(runCatching { readSearchReceipt("""{"jobId":"job-4","state":"complete","result":{"results":[{"url":"$url"}]}}""") }.isFailure)
        }
    }
}
