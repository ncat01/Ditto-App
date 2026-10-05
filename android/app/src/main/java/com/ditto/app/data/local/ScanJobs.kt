package com.ditto.app.data.local

import androidx.room.*

@Entity(tableName="scan_jobs",foreignKeys=[ForeignKey(entity=ContentEntity::class,parentColumns=["id"],childColumns=["contentId"],onDelete=ForeignKey.CASCADE)],indices=[Index("contentId")])
data class ScanJobEntity(@PrimaryKey val id: String,val contentId: String,val startedAt: Long,val stage: String,val fingerprint: String,val candidates: Int=0,val error: String?=null)
@Dao
interface ScanJobDao {
    @Insert(onConflict=OnConflictStrategy.REPLACE) suspend fun save(job: ScanJobEntity)
    @Query("SELECT * FROM scan_jobs WHERE contentId=:id ORDER BY startedAt DESC") fun observe(id: String): kotlinx.coroutines.flow.Flow<List<ScanJobEntity>>
}
