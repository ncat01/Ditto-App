package com.ditto.app.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ditto.app.core.ServiceLocator
import com.ditto.app.data.repository.DittoRepository
import com.ditto.app.data.repository.DittoResult
import com.ditto.app.domain.model.Case
import com.ditto.app.domain.model.FollowUpOutcome
import com.ditto.app.domain.model.MessageTone
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class CaseDetailUiState(
    val busy: Boolean = false,
    val error: String? = null,
    /** Latest agent decision banner, shown after a follow-up run. */
    val lastDecision: String? = null,
    val lastDecisionDetail: String? = null
)

class CaseDetailViewModel(app: Application, private val caseId: String) : AndroidViewModel(app) {

    private val repo: DittoRepository = ServiceLocator.repository(app)

    val case: StateFlow<Case?> = repo.observeCase(caseId)
        .catch { emit(null) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    private val _ui = MutableStateFlow(CaseDetailUiState())
    val ui: StateFlow<CaseDetailUiState> = _ui.asStateFlow()

    fun dismissError() { _ui.value = _ui.value.copy(error = null) }
    fun dismissDecision() {
        _ui.value = _ui.value.copy(lastDecision = null, lastDecisionDetail = null)
    }

    fun approve(editedBody: String?, tone: MessageTone?) = run {
        _ui.value = _ui.value.copy(busy = true, error = null)
        viewModelScope.launch {
            when (val r = repo.approve(caseId, editedBody, tone)) {
                is DittoResult.Ok -> _ui.value = _ui.value.copy(
                    busy = false,
                    lastDecision = "Action approved.",
                    lastDecisionDetail = "Message prepared and dispatched to the sandboxed " +
                        "outreach queue. The Follow-Up Agent is now tracking this case."
                )
                is DittoResult.Err -> _ui.value =
                    _ui.value.copy(busy = false, error = r.message)
            }
        }
    }

    fun reject(note: String?) {
        _ui.value = _ui.value.copy(busy = true, error = null)
        viewModelScope.launch {
            when (val r = repo.reject(caseId, note)) {
                is DittoResult.Ok -> _ui.value = _ui.value.copy(
                    busy = false,
                    lastDecision = "Action rejected.",
                    lastDecisionDetail = "Nothing was sent. The case is closed."
                )
                is DittoResult.Err -> _ui.value =
                    _ui.value.copy(busy = false, error = r.message)
            }
        }
    }

    fun saveDraft(body: String, tone: MessageTone) {
        _ui.value = _ui.value.copy(busy = true, error = null)
        viewModelScope.launch {
            when (val r = repo.saveDraft(caseId, body, tone)) {
                is DittoResult.Ok -> _ui.value = _ui.value.copy(
                    busy = false,
                    lastDecision = "Draft saved.",
                    lastDecisionDetail = "The edited message will be used when you approve."
                )
                is DittoResult.Err -> _ui.value =
                    _ui.value.copy(busy = false, error = r.message)
            }
        }
    }

    fun runFollowUp(outcome: FollowUpOutcome) {
        _ui.value = _ui.value.copy(busy = true, error = null)
        viewModelScope.launch {
            val before = case.value?.state
            when (val r = repo.runFollowUp(caseId, outcome)) {
                is DittoResult.Ok -> {
                    val after = r.value.state
                    val latest = r.value.history.lastOrNull()
                    _ui.value = _ui.value.copy(
                        busy = false,
                        lastDecision = latest?.action ?: "Follow-up complete.",
                        lastDecisionDetail = buildString {
                            append(latest?.reasoning.orEmpty())
                            if (before != null && before != after) {
                                append("\n\nState: ${before.label} → ${after.label}")
                            }
                        }
                    )
                }
                is DittoResult.Err -> _ui.value =
                    _ui.value.copy(busy = false, error = r.message)
            }
        }
    }

    fun resolve(note: String?) {
        _ui.value = _ui.value.copy(busy = true, error = null)
        viewModelScope.launch {
            when (val r = repo.resolve(caseId, note)) {
                is DittoResult.Ok -> _ui.value = _ui.value.copy(
                    busy = false,
                    lastDecision = "Resolution confirmed.",
                    lastDecisionDetail = "The case is closed and follow-up is cancelled."
                )
                is DittoResult.Err -> _ui.value =
                    _ui.value.copy(busy = false, error = r.message)
            }
        }
    }

    companion object {
        fun factory(caseId: String) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(
                modelClass: Class<T>,
                extras: androidx.lifecycle.viewmodel.CreationExtras
            ): T {
                val app = extras[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY]
                    as Application
                return CaseDetailViewModel(app, caseId) as T
            }
        }
    }
}
