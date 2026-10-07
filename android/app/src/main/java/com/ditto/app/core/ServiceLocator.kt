package com.ditto.app.core

import android.content.Context
import com.ditto.app.data.repository.DittoRepository
import com.ditto.app.data.repository.RemoteDittoRepository

/**
 * Manual dependency container. Chosen over Hilt deliberately: the graph is small and
 * a compile-time-annotation-free container keeps the build simple and reliable for a
 * capstone deliverable, while still centralising construction in one place.
 */
object ServiceLocator {

    @Volatile var activeUser: String? = null
        private set
    fun activateUser(id: String?) {
        if (activeUser != id) { (repo as? RemoteDittoRepository)?.close(); activeUser = id; repo = null; settingsStore = null }
    }
    @Volatile private var repo: DittoRepository? = null
    @Volatile private var settingsStore: SettingsStore? = null

    fun settings(context: Context): SettingsStore =
        settingsStore ?: synchronized(this) {
            settingsStore ?: SettingsStore(context.applicationContext,activeUser ?: "anonymous").also { settingsStore = it }
        }

    /**
     * API repository. All account data comes from the hosted backend.
     * against the FastAPI backend; the UI depends only on [DittoRepository].
     */
    fun repository(context: Context): DittoRepository =
        repo ?: synchronized(this) {
            repo ?: run {
                val connection=BackendConnection(context.applicationContext)
                if(connection.enabled()) RemoteDittoRepository(context.applicationContext, connection.session() ?: error("Sign in to the backend first"))
                else error("Sign in to your Ditto account first")
            }.also { repo = it }
        }

}
