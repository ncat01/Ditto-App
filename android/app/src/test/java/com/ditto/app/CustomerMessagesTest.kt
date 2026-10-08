package com.ditto.app

import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.AgentKind
import com.ditto.app.ui.screens.customerActivityText
import com.ditto.app.ui.screens.customerServiceStatus
import com.ditto.app.ui.screens.safeCustomerMessage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CustomerMessagesTest {
    @Test
    fun dnsErrorsDoNotExposeHostingAddresses() {
        val raw = "Unable to resolve host ditto-api-production-7e7f.up.railway.app: No address associated with hostname"
        val display = customerServiceStatus(raw)
        assertTrue(display.contains("internet connection"))
        assertFalse(display.contains("railway"))
        assertFalse(display.contains("hostname"))
    }

    @Test
    fun legacyPreparationEventsDoNotExposeFingerprintsOrLibraries() {
        val event = ActivityEvent(1, 0, AgentKind.INGESTION, "Original fingerprinted",
            "pHash 64-bit (ImageHash/Pillow): 0123456789abcdef", null)
        val display = customerActivityText(event)
        assertEquals("Original ready", display.title)
        assertEquals("Your original is ready for search and comparison.", display.detail)
        assertFalse(display.toString().contains("pHash"))
        assertFalse(display.toString().contains("0123456789abcdef"))
    }

    @Test
    fun failedActionsRemainFailuresAfterTechnicalDetailsAreRemoved() {
        val event = ActivityEvent(2, 0, AgentKind.DISCOVERY, "Search failed",
            "Backend HTTP 503: provider exception", "case")
        val display = customerActivityText(event)
        assertEquals("Search failed", display.title)
        assertTrue(display.detail.contains("did not finish"))
    }

    @Test
    fun legacyFailureInDetailsDoesNotBecomeASuccess() {
        val event = ActivityEvent(3, 0, AgentKind.INGESTION, "Original fingerprint update",
            "Pillow exception: fingerprint generation failed", null)
        val display = customerActivityText(event)
        assertEquals("Your originals couldn't finish", display.title)
        assertTrue(display.detail.contains("did not finish"))
    }

    @Test
    fun usefulLoginValidationIsPreserved() {
        assertEquals("Password must be at least 10 characters.", safeCustomerMessage(
            "Password must be at least 10 characters.", "Couldn't sign in."))
    }
}
