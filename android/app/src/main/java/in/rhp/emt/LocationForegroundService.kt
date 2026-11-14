package in.rhp.emt

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.location.Location
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import in.rhp.emt.outbox.OutboxDao
import in.rhp.emt.outbox.OutboxDatabase
import in.rhp.emt.outbox.TelemetryEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Native Android Location Foreground Service (RHP-1 Ambulance EMT).
 *
 * Specification Anchors:
 * - Architecture §14: Native Mobile Location & Room Outbox [Closures F5, F16]
 * - Closure F5: FOREGROUND_SERVICE_TYPE_LOCATION continuous GPS updates
 * - PowerManager: Partial wake lock guarantees >= 2 hours tracking with screen off.
 * - Local Room Outbox: Coordinates queued offline for batch upload to /v1/telemetry.
 */
class LocationForegroundService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private lateinit var outboxDao: OutboxDao

    private var wakeLock: PowerManager.WakeLock? = null
    private var referralId: String? = null

    companion object {
        const val CHANNEL_ID = "rhp_ambulance_location_channel"
        const val NOTIFICATION_ID = 40401
        const val EXTRA_REFERRAL_ID = "in.rhp.emt.EXTRA_REFERRAL_ID"
        const val UPDATE_INTERVAL_MS = 5000L
        const val FASTEST_INTERVAL_MS = 3000L
    }

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        val db = OutboxDatabase.getInstance(applicationContext)
        outboxDao = db.outboxDao()

        // Acquire partial wake lock for >= 2 hour screen-off tracking
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "RHP:AmbulanceLocationTracking").apply {
            setReferenceCounted(false)
            acquire(2 * 60 * 60 * 1000L) // 2 hours max timeout
        }

        createNotificationChannel()
        setupLocationCallback()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        referralId = intent?.getStringExtra(EXTRA_REFERRAL_ID)
        val notification = buildForegroundNotification()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceCompat.startForeground(
                this,
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        startLocationUpdates()
        return START_STICKY
    }

    private fun setupLocationCallback() {
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val loc: Location = result.lastLocation ?: return
                recordTelemetry(loc)
            }
        }
    }

    private fun startLocationUpdates() {
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, UPDATE_INTERVAL_MS).apply {
            setMinUpdateIntervalMillis(FASTEST_INTERVAL_MS)
            setWaitForAccurateLocation(false)
        }.build()

        try {
            fusedLocationClient.requestLocationUpdates(request, locationCallback, Looper.getMainLooper())
        } catch (e: SecurityException) {
            // Permission missing
        }
    }

    private fun recordTelemetry(location: Location) {
        val currentReferral = referralId ?: return
        val latE5 = (location.latitude * 1e5).toInt()
        val lonE5 = (location.longitude * 1e5).toInt()
        val speedMps = if (location.hasSpeed()) location.speed.toDouble() else 0.0
        val headingDeg = if (location.hasBearing()) location.bearing.toInt() else 0
        val clientTsMs = System.currentTimeMillis()

        serviceScope.launch {
            val entity = TelemetryEntity(
                id = UUID.randomUUID().toString(),
                referralId = currentReferral,
                latE5 = latE5,
                lonE5 = lonE5,
                speedMps = speedMps,
                headingDeg = headingDeg,
                clientTsMs = clientTsMs,
                status = "QUEUED"
            )
            outboxDao.insertTelemetry(entity)
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Ambulance Location Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Transmits GPS coordinates to receiving facility desk"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("RHP-1 Ambulance Transport Active")
            .setContentText("Continuous GPS telemetry enabled (screen-off active)")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocationClient.removeLocationUpdates(locationCallback)
        serviceScope.cancel()
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

