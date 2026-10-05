package com.ditto.app.core

import android.content.Context
import androidx.work.*
import com.ditto.app.domain.model.CaseState
import com.ditto.app.domain.model.FollowUpOutcome
import java.util.concurrent.TimeUnit

object DemoClock {
    @Volatile private var displayOffset: Long = 0
    fun displayNow(): Long = System.currentTimeMillis()+displayOffset
    fun clearDisplay() { displayOffset=0 }
    fun now(context: Context,user: String): Long {
        val offset=context.getSharedPreferences("clock_$user",0).getLong("offset",0)
        if(ServiceLocator.activeUser==user)displayOffset=offset
        return System.currentTimeMillis()+offset
    }
    fun reset(context: Context,user: String) { context.getSharedPreferences("clock_$user",0).edit().putLong("offset",0).commit();if(ServiceLocator.activeUser==user)displayOffset=0 }
    fun advance(context: Context,user: String) {
        val prefs=context.getSharedPreferences("clock_$user",0)
        prefs.edit().putLong("offset",prefs.getLong("offset",0)+TimeUnit.DAYS.toMillis(7)).commit()
        now(context,user)
    }
}

class FollowUpWorker(context: Context,params: WorkerParameters): CoroutineWorker(context,params) {
    override suspend fun doWork(): Result {
        val user=inputData.getString("user") ?: return Result.failure()
        return try { checkDue(applicationContext,user);Result.success() } catch(_:Exception) { Result.retry() }
    }
    companion object {
        suspend fun checkDue(context: Context,user: String): Int {
            val repository=ServiceLocator.repositoryFor(context,user)
            val now=DemoClock.now(context,user)
            val due=repository.casesAwaitingFollowUp().filter { it.state==CaseState.AWAITING_RESPONSE && (it.nextFollowUpAt ?: Long.MAX_VALUE)<=now }
            for(case in due) repository.runFollowUp(case.id,FollowUpOutcome.NO_RESPONSE)
            return due.size
        }
        fun schedule(context: Context,user: String) {
            val work=PeriodicWorkRequestBuilder<FollowUpWorker>(15,TimeUnit.MINUTES).setInputData(workDataOf("user" to user)).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("ditto-followup-$user",ExistingPeriodicWorkPolicy.KEEP,work)
        }
    }
}
