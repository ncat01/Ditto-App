package com.ditto.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * On-device store for the demo. Schema mirrors the backend's SQLAlchemy models so the
 * same data model works against SQLite locally and PostgreSQL server-side.
 */
@Database(
    entities = [
        ContentEntity::class,
        ScanJobEntity::class,
        CaseEntity::class,
        CaseHistoryEntity::class,
        ActivityEntity::class
    ],
    version = 2,
    exportSchema = true
)
abstract class DittoDatabase : RoomDatabase() {
    abstract fun scanJobDao(): ScanJobDao
    abstract fun contentDao(): ContentDao
    abstract fun caseDao(): CaseDao
    abstract fun caseHistoryDao(): CaseHistoryDao
    abstract fun activityDao(): ActivityDao

    companion object {
        private val migration = object : androidx.room.migration.Migration(1,2) {
            override fun migrate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE cases ADD COLUMN attributionPresent INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE cases ADD COLUMN permissionGranted INTEGER NOT NULL DEFAULT 0")
                db.execSQL("CREATE TABLE IF NOT EXISTS scan_jobs (id TEXT NOT NULL PRIMARY KEY, contentId TEXT NOT NULL, startedAt INTEGER NOT NULL, stage TEXT NOT NULL, fingerprint TEXT NOT NULL, candidates INTEGER NOT NULL, error TEXT, FOREIGN KEY(contentId) REFERENCES content(id) ON DELETE CASCADE)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_scan_jobs_contentId ON scan_jobs(contentId)")
            }
        }
        private val instances = mutableMapOf<String, DittoDatabase>()
        fun get(context: Context, user: String): DittoDatabase = synchronized(instances) {
            instances.getOrPut(user) {
                Room.databaseBuilder(context.applicationContext, DittoDatabase::class.java,
                    "ditto-${user}.db").addMigrations(migration).build()
            }
        }
    }
}
