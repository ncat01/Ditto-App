package com.ditto.app.core

import android.content.Context
import com.ditto.app.data.demo.MockDiscoveryProvider
import com.ditto.app.data.demo.PerceptualHasher
import com.ditto.app.data.local.DittoDatabase
import com.ditto.app.data.repository.DittoRepository
import com.ditto.app.data.repository.LocalDittoRepository
import com.ditto.app.data.repository.RemoteDittoRepository
import com.ditto.app.domain.agents.MockActionPlanningAgent
import com.ditto.app.domain.agents.MockFollowUpAgent
import com.ditto.app.domain.agents.MockVerificationAgent

/**
 * Manual dependency container. Chosen over Hilt deliberately: the graph is small and
 * a compile-time-annotation-free container keeps the build simple and reliable for a
 * capstone deliverable, while still centralising construction in one place.
 */
object ServiceLocator {

    @Volatile var activeUser: String? = null
        private set
    fun activateUser(id: String?) {
        if (activeUser != id) { (repo as? RemoteDittoRepository)?.close();DemoClock.clearDisplay(); activeUser = id; repo = null; settingsStore = null }
    }
    @Volatile private var repo: DittoRepository? = null
    @Volatile private var settingsStore: SettingsStore? = null

    fun settings(context: Context): SettingsStore =
        settingsStore ?: synchronized(this) {
            settingsStore ?: SettingsStore(context.applicationContext,activeUser ?: "anonymous").also { settingsStore = it }
        }

    /**
     * Demo Mode repository. Live Mode swaps in the Retrofit-backed implementation
     * against the FastAPI backend; the UI depends only on [DittoRepository].
     */
    fun repository(context: Context): DittoRepository =
        repo ?: synchronized(this) {
            repo ?: run {
                val connection=BackendConnection(context.applicationContext)
                if(connection.enabled()) RemoteDittoRepository(context.applicationContext, connection.session() ?: error("Sign in to the backend first"))
                else repositoryFor(context.applicationContext, activeUser ?: error("Sign in first"))
            }.also { repo = it }
        }

    private val userRepositories = mutableMapOf<String, DittoRepository>()
    fun repositoryFor(context: Context,user: String): DittoRepository = synchronized(userRepositories) {
        userRepositories.getOrPut(user) { buildLocal(context.applicationContext,user) }
    }
    private fun buildLocal(context: Context,user: String): DittoRepository = LocalDittoRepository(
        clock = { DemoClock.now(context,user) },
        context = context,
        userId = user,
        db = DittoDatabase.get(context, user),
        videoCorpus = com.ditto.app.data.demo.VideoCorpus(context),
        matcher = PerceptualHasher(context),
        discovery = MockDiscoveryProvider(com.ditto.app.data.demo.VideoCorpus(context)),
        verifier = MockVerificationAgent(),
        planner = MockActionPlanningAgent(),
        followUp = MockFollowUpAgent()
    )
}
