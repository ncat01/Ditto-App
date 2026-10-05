package com.ditto.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ContentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: ContentEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(items: List<ContentEntity>)

    @Query("SELECT * FROM content ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<ContentEntity>>

    @Query("SELECT * FROM content WHERE id = :id")
    suspend fun byId(id: String): ContentEntity?

    @Query("SELECT COUNT(*) FROM content")
    suspend fun count(): Int
}

@Dao
interface CaseDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: CaseEntity)

    @Update
    suspend fun update(item: CaseEntity)

    @Query("SELECT * FROM cases ORDER BY updatedAt DESC")
    fun observeAll(): Flow<List<CaseEntity>>

    @Query("SELECT * FROM cases WHERE id = :id")
    fun observeById(id: String): Flow<CaseEntity?>

    @Query("SELECT * FROM cases WHERE id = :id")
    suspend fun byId(id: String): CaseEntity?

    @Query("SELECT * FROM cases WHERE currentState IN (:states) ORDER BY updatedAt DESC")
    suspend fun byStates(states: List<String>): List<CaseEntity>

    @Query("SELECT COUNT(*) FROM cases")
    suspend fun count(): Int

    @Query("SELECT COUNT(*) FROM cases WHERE candidateId = :candidateId")
    suspend fun countByCandidate(candidateId: String): Int

    @Query("DELETE FROM cases")
    suspend fun clear()
}

@Dao
interface CaseHistoryDao {
    @Insert
    suspend fun insert(entry: CaseHistoryEntity)

    @Query("SELECT * FROM case_history WHERE caseId = :caseId ORDER BY timestamp ASC, id ASC")
    fun observeForCase(caseId: String): Flow<List<CaseHistoryEntity>>

    @Query("SELECT * FROM case_history WHERE caseId = :caseId ORDER BY timestamp ASC, id ASC")
    suspend fun forCase(caseId: String): List<CaseHistoryEntity>

    @Query("DELETE FROM case_history")
    suspend fun clear()
}

@Dao
interface ActivityDao {
    @Insert
    suspend fun insert(event: ActivityEntity)

    @Query("SELECT * FROM activity ORDER BY timestamp DESC, id DESC LIMIT :limit")
    fun observeRecent(limit: Int = 100): Flow<List<ActivityEntity>>

    @Query("DELETE FROM activity")
    suspend fun clear()
}
