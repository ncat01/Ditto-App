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
import com.ditto.app.domain.model.ContentItem
import com.ditto.app.domain.model.ScanStage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class ScanUiState(
    val selectedContent: ContentItem? = null,
    val stage: ScanStage = ScanStage.IDLE,
    val stageMessage: String = "",
    val completedStages: List<ScanStage> = emptyList(),
    val candidatesFound: Int = 0,
    val resultCaseIds: List<String> = emptyList(),
    val results: List<Case> = emptyList(),
    val error: String? = null,
    val isScanning: Boolean = false,
    val isIngesting: Boolean = false
)

class ScanViewModel(app: Application) : AndroidViewModel(app) {

    private val repo: DittoRepository = ServiceLocator.repository(app)

    private val _state = MutableStateFlow(ScanUiState())
    val state: StateFlow<ScanUiState> = _state.asStateFlow()

    val discoveryName: String get() = repo.discoveryProviderName
    val matcherName: String get() = repo.matcherName

    fun selectContent(item: ContentItem) {
        _state.value = ScanUiState(selectedContent = item)
    }

    fun clear() {
        _state.value = ScanUiState()
    }

    /** Ingest a picked file, then select it as the scan target. */
    fun ingest(title: String, uri: String?, isVideo: Boolean, source: String = "Local upload") = viewModelScope.launch {
        _state.value = _state.value.copy(isIngesting = true, error = null)
        when (val r = repo.ingest(title, uri, isVideo, source)) {
            is DittoResult.Ok -> _state.value = ScanUiState(selectedContent = r.value)
            is DittoResult.Err -> _state.value =
                _state.value.copy(isIngesting = false, error = r.message)
        }
    }

    fun startScan() {
        val content = _state.value.selectedContent ?: return
        _state.value = _state.value.copy(
            isScanning = true,
            error = null,
            completedStages = emptyList(),
            resultCaseIds = emptyList(),
            results = emptyList(),
            candidatesFound = 0
        )
        viewModelScope.launch {
            repo.scan(content.id).collect { result ->
                when (result) {
                    is DittoResult.Err -> _state.value = _state.value.copy(
                        isScanning = false,
                        error = result.message,
                        stage = ScanStage.IDLE
                    )

                    is DittoResult.Ok -> {
                        val p = result.value
                        val done = _state.value.completedStages.toMutableList()
                        if (_state.value.stage != ScanStage.IDLE &&
                            _state.value.stage !in done
                        ) {
                            done += _state.value.stage
                        }
                        _state.value = _state.value.copy(
                            stage = p.stage,
                            stageMessage = p.message,
                            completedStages = done,
                            candidatesFound = p.candidatesFound,
                            resultCaseIds = p.casesCreated.ifEmpty {
                                _state.value.resultCaseIds
                            },
                            isScanning = p.stage != ScanStage.DONE
                        )
                        if (p.stage == ScanStage.DONE) loadResults()
                    }
                }
            }
        }
    }

    /** Pull the freshly created cases so the results list can render them. */
    private suspend fun loadResults() {
        val ids = _state.value.resultCaseIds.toSet()
        val contentId = _state.value.selectedContent?.id
        val all = repo.observeCases().first()
        val results = all.filter { it.id in ids || (ids.isEmpty() && it.contentId == contentId) }
            .sortedByDescending { it.candidate.overallSimilarity }
        _state.value = _state.value.copy(results = results, isScanning = false)
    }

    companion object {
        val Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(
                modelClass: Class<T>,
                extras: androidx.lifecycle.viewmodel.CreationExtras
            ): T {
                val app = extras[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY]
                    as Application
                return ScanViewModel(app) as T
            }
        }
    }
}
