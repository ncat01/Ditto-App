package com.ditto.app.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ditto.app.core.DittoSettings
import com.ditto.app.core.ServiceLocator
import com.ditto.app.core.SettingsStore
import com.ditto.app.data.repository.DittoRepository
import com.ditto.app.data.repository.DittoResult
import com.ditto.app.domain.model.ActivityEvent
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.DashboardStats
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * App-wide state: cases, stats, activity feed and settings. Everything is driven from
 * Room Flows, so any state transition immediately refreshes the dashboard counters,
 * case list and activity feed without a manual reload (report §40).
 */
class DittoViewModel(app: Application) : AndroidViewModel(app) {

    private val repo: DittoRepository = ServiceLocator.repository(app)
    private val settingsStore: SettingsStore = ServiceLocator.settings(app)

    val engineNames = EngineNames(
        verification = repo.verificationEngineName,
        discovery = repo.discoveryProviderName,
        matcher = repo.matcherName
    )

    val cases: StateFlow<List<Case>> = repo.observeCases()
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val stats: StateFlow<DashboardStats> = repo.observeStats()
        .catch { emit(emptyStats()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyStats())

    val activity: StateFlow<List<ActivityEvent>> = repo.observeActivity()
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val content: StateFlow<List<ContentItem>> = repo.observeContent()
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val settings: StateFlow<DittoSettings> = settingsStore.settings
        .catch { emit(DittoSettings()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), DittoSettings())

    private val _toast = MutableStateFlow<String?>(null)
    val toast: StateFlow<String?> = _toast.asStateFlow()

    fun clearToast() { _toast.value = null }
    fun showMessage(text: String) { _toast.value = text }

    // ---- settings ----
    fun setDemoMode(enabled: Boolean) = viewModelScope.launch {
        settingsStore.setDemoMode(enabled)
        _toast.value = if (enabled) "Demo Mode on — synthetic corpus, nothing is sent."
        else "Demo Mode off. Live providers are not configured, so scans still use the demo corpus."
    }

    fun setPresentationMode(enabled: Boolean) = viewModelScope.launch {
        settingsStore.setPresentationMode(enabled)
        _toast.value = if (enabled) "Presentation Mode on — faster scans, deterministic results."
        else "Presentation Mode off."
    }

    fun setNotifyEscalation(v: Boolean) = viewModelScope.launch {
        settingsStore.setNotifyEscalation(v)
    }

    fun setNotifyNewCase(v: Boolean) = viewModelScope.launch {
        settingsStore.setNotifyNewCase(v)
    }

    fun setApiBaseUrl(url: String) = viewModelScope.launch {
        settingsStore.setApiBaseUrl(url)
        _toast.value = "Backend URL saved."
    }

    fun resetDemoData() = viewModelScope.launch {
        when (val r = repo.resetDemoData()) {
            is DittoResult.Ok -> _toast.value = "Demo data reset — ${r.value} cases seeded."
            is DittoResult.Err -> _toast.value = r.message
        }
    }

    companion object Selectors {
        /**
         * Pure selectors over an already-collected list.
         *
         * These deliberately take the list as a parameter rather than reading
         * `cases.value` internally: a composable calling a function that reads a
         * StateFlow's value directly does not register a snapshot read, so the
         * result would never invalidate and the UI would render stale data.
         */
        fun needingAttention(cases: List<Case>): List<Case> = cases
            .filter {
                it.state == CaseState.PENDING_APPROVAL || it.state == CaseState.ESCALATED
            }
            .sortedByDescending { it.verification?.confidence ?: 0.0 }

        fun awaitingResponse(cases: List<Case>): List<Case> = cases
            .filter {
                it.state == CaseState.AWAITING_RESPONSE || it.state == CaseState.SENT
            }
            .sortedBy { it.nextFollowUpAt ?: Long.MAX_VALUE }
    }

    private fun emptyStats() = DashboardStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0)

    data class EngineNames(
        val verification: String,
        val discovery: String,
        val matcher: String
    )

    object Factory : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(
            modelClass: Class<T>,
            extras: androidx.lifecycle.viewmodel.CreationExtras
        ): T {
            val app = extras[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY]
                as Application
            return DittoViewModel(app) as T
        }
    }
}
