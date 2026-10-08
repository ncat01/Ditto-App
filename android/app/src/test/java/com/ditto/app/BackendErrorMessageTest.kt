package com.ditto.app

import com.ditto.app.core.backendErrorMessage
import com.ditto.app.core.backendFailureMessage
import com.ditto.app.core.canRetryBackendRequest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLHandshakeException

class BackendErrorMessageTest {
    @Test
    fun validationArraysBecomeReadableMessages() {
        val body = """{"detail":[{"msg":"String should have at least 10 characters"}]}"""
        assertEquals(
            "Password must be at least 10 characters.",
            backendErrorMessage("api/auth/signup", 422, body)
        )
    }

    @Test
    fun loginDoesNotExposeServerDetails() {
        assertEquals(
            "Email or password is incorrect.",
            backendErrorMessage("api/auth/login", 401, "not-json")
        )
    }

    @Test
    fun malformedErrorsStayFriendly() {
        assertEquals(
            "Request could not be completed. Try again.",
            backendErrorMessage("api/example", 400, "{broken")
        )
    }

    @Test
    fun dnsFailuresNeverExposeTheBackendHostname() {
        val failure=UnknownHostException("Unable to resolve host ditto-api-production-7e7f.up.railway.app: No address associated with hostname")
        val message=backendFailureMessage("api/dashboard",failure)
        assertEquals("Cannot reach Ditto. Check your internet connection; we will reconnect automatically.",message)
        assertFalse(message.contains("railway"))
        assertFalse(message.contains("resolve host"))
        assertEquals("Cannot reach Ditto to sign in. Check your connection and try again.",
            backendFailureMessage("api/auth/login",IllegalStateException("raw network detail",failure),true))
    }

    @Test
    fun anUncertainSearchSubmissionDoesNotClaimThatItFailed() {
        assertEquals("Search status could not be confirmed. Reopen your original to check before searching again.",
            backendFailureMessage("api/discovery/original/web-search-job",SocketTimeoutException("Read timed out"),true))
    }

    @Test
    fun onlyReadRequestsMayRetryConnectionFailures() {
        val failure=UnknownHostException("private hostname")
        assertTrue(canRetryBackendRequest("GET",failure))
        assertFalse(canRetryBackendRequest("POST",failure))
        assertFalse(canRetryBackendRequest("POST",SocketTimeoutException("timeout")))
        assertFalse(canRetryBackendRequest("GET",SSLHandshakeException("certificate details")))
    }

    @Test
    fun secureConnectionErrorsStayReadable() {
        val message=backendFailureMessage("api/content",SSLHandshakeException("secret certificate and hostname"))
        assertEquals("Ditto could not establish a secure connection. Try again shortly or contact support.",message)
    }
}
