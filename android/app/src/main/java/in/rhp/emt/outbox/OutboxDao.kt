package in.rhp.emt.outbox

import android.content.Context
import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Local Room Entity for Offline Outbox Commands.
 * Guarantees zero loss of transition requests when cell coverage drops.
 */
@Entity(tableName = "outbox_commands")
data class OutboxCommandEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "idempotency_key") val idempotencyKey: String,
    @ColumnInfo(name = "endpoint") val endpoint: String,
    @ColumnInfo(name = "payload_json") val payloadJson: String,
    @ColumnInfo(name = "status") val status: String, // QUEUED, SENT, DEAD
    @ColumnInfo(name = "attempts") val attempts: Int = 0,
    @ColumnInfo(name = "created_at_ms") val createdAtMs: Long = System.currentTimeMillis()
)

/**
 * Local Room Entity for GPS Telemetry Batches.
 */
@Entity(tableName = "telemetry_queue")
data class TelemetryEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "referral_id") val referralId: String,
    @ColumnInfo(name = "lat_e5") val latE5: Int,
    @ColumnInfo(name = "lon_e5") val lonE5: Int,
    @ColumnInfo(name = "speed_mps") val speedMps: Double,
    @ColumnInfo(name = "heading_deg") val headingDeg: Int,
    @ColumnInfo(name = "client_ts_ms") val clientTsMs: Long,
    @ColumnInfo(name = "status") val status: String
)

@Dao
interface OutboxDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCommand(cmd: OutboxCommandEntity)

    @Query("SELECT * FROM outbox_commands WHERE status = 'QUEUED' ORDER BY created_at_ms ASC LIMIT 20")
    suspend fun getPendingCommands(): List<OutboxCommandEntity>

    @Query("UPDATE outbox_commands SET status = 'SENT' WHERE id = :id")
    suspend fun markCommandSent(id: String)

    @Query("UPDATE outbox_commands SET attempts = attempts + 1, status = CASE WHEN attempts >= 8 THEN 'DEAD' ELSE 'QUEUED' END WHERE id = :id")
    suspend fun incrementCommandAttempts(id: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTelemetry(item: TelemetryEntity)

    @Query("SELECT * FROM telemetry_queue WHERE status = 'QUEUED' ORDER BY client_ts_ms ASC LIMIT 50")
    suspend fun getPendingTelemetry(): List<TelemetryEntity>

    @Query("DELETE FROM telemetry_queue WHERE id IN (:ids)")
    suspend fun deleteTelemetry(ids: List<String>)
}

@Database(entities = [OutboxCommandEntity::class, TelemetryEntity::class], version = 1, exportSchema = false)
abstract class OutboxDatabase : RoomDatabase() {
    abstract fun outboxDao(): OutboxDao

    companion object {
        @Volatile
        private var INSTANCE: OutboxDatabase? = null

        fun getInstance(context: Context): OutboxDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    OutboxDatabase::class.java,
                    "rhp_ambulance_outbox.db"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}

