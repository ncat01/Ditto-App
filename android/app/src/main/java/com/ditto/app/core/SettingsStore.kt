package com.ditto.app.core

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "ditto_settings")

data class DittoSettings(
    val demoMode: Boolean = true,
    val presentationMode: Boolean = false,
    val creatorName: String = "Alex Morgan",
    val creatorHandle: String = "@alexmorgan.shoots",
    val autoApproveNever: Boolean = true,
    val notifyOnEscalation: Boolean = true,
    val notifyOnNewCase: Boolean = true,
    /** Backend URL for Live Mode. Empty means "use the build-time default". */
    val apiBaseUrl: String = ""
)

/**
 * Local preference storage. Note that no API keys are stored here — the Android client
 * never holds provider credentials; those live server-side in the FastAPI backend's
 * environment (report §31).
 */
class SettingsStore(private val context: Context, private val userId: String) {

    private class Keys(user: String) {
        val DEMO_MODE = booleanPreferencesKey("$user:demo_mode")
        val PRESENTATION_MODE = booleanPreferencesKey("$user:presentation_mode")
        val CREATOR_NAME = stringPreferencesKey("$user:creator_name")
        val CREATOR_HANDLE = stringPreferencesKey("$user:creator_handle")
        val NOTIFY_ESCALATION = booleanPreferencesKey("$user:notify_escalation")
        val NOTIFY_NEW_CASE = booleanPreferencesKey("$user:notify_new_case")
        val API_BASE_URL = stringPreferencesKey("$user:api_base_url")
    }

    private val keys = Keys(userId)

    val settings: Flow<DittoSettings> = context.dataStore.data.map { p: Preferences ->
        DittoSettings(
            demoMode = p[keys.DEMO_MODE] ?: true,
            presentationMode = p[keys.PRESENTATION_MODE] ?: false,
            creatorName = p[keys.CREATOR_NAME] ?: "Alex Morgan",
            creatorHandle = p[keys.CREATOR_HANDLE] ?: "@alexmorgan.shoots",
            notifyOnEscalation = p[keys.NOTIFY_ESCALATION] ?: true,
            notifyOnNewCase = p[keys.NOTIFY_NEW_CASE] ?: true,
            apiBaseUrl = p[keys.API_BASE_URL] ?: ""
        )
    }

    suspend fun setDemoMode(enabled: Boolean) =
        context.dataStore.edit { it[keys.DEMO_MODE] = enabled }

    suspend fun setPresentationMode(enabled: Boolean) =
        context.dataStore.edit { it[keys.PRESENTATION_MODE] = enabled }

    suspend fun setCreator(name: String, handle: String) = context.dataStore.edit {
        it[keys.CREATOR_NAME] = name
        it[keys.CREATOR_HANDLE] = handle
    }

    suspend fun setNotifyEscalation(enabled: Boolean) =
        context.dataStore.edit { it[keys.NOTIFY_ESCALATION] = enabled }

    suspend fun setNotifyNewCase(enabled: Boolean) =
        context.dataStore.edit { it[keys.NOTIFY_NEW_CASE] = enabled }

    suspend fun setApiBaseUrl(url: String) =
        context.dataStore.edit { it[keys.API_BASE_URL] = url.trim() }
}
