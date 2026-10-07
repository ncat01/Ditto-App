package com.ditto.app

import com.ditto.app.core.backendErrorMessage
import org.junit.Assert.assertEquals
import org.junit.Test

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
}
