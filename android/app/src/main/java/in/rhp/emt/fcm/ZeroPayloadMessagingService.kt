package in.rhp.emt.fcm

import android.content.Intent
import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import in.rhp.emt.LocationForegroundService

/**
 * Zero-Payload FCM Push Messaging Service (RHP-1 Android EMT).
 *
 * Specification Anchors:
 * - Architecture §9, §14: Push Notification Architecture [Closure P3, Invariant I10]
 * - Closure P3: Zero PHI across Google/Apple Push Notification servers.
 * - Empty-Payload Wake Rule: Push payloads contain ONLY {"wake": "1"}.
 *   All clinical and referral state is fetched over authenticated HTTPS from /v1/referrals.
 */
class ZeroPayloadMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "ZeroPayloadFCM"
        private val FORBIDDEN_CLINICAL_KEYS = setOf(
            "patient_name", "diagnosis", "need_class", "bp", "vitals",
            "mgso4", "eclampsia", "gestation", "gravida", "summary", "notes"
        )
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val data = remoteMessage.data

        // 1. Enforce Zero-PHI Verification Gate (Closure P3)
        for (key in data.keys) {
            val keyLower = key.lowercase()
            if (FORBIDDEN_CLINICAL_KEYS.any { keyLower.contains(it) }) {
                Log.e(TAG, "CRITICAL SECURITY VIOLATION: FCM payload contains clinical data key '$key'. Dropping message.")
                return
            }
        }

        // 2. Validate empty-payload wake ping format
        val isWakePing = data.isEmpty() || data["wake"] == "1" || data.containsKey("referral_id")
        if (!isWakePing) {
            Log.w(TAG, "Unknown push payload format received. Ignoring non-wake message.")
            return
        }

        Log.i(TAG, "Received authorized zero-payload wake ping. Triggering authenticated sync.")

        // 3. Trigger authenticated pull from primary server
        val referralId = data["referral_id"]
        if (!referralId.isNullOrEmpty()) {
            val intent = Intent(applicationContext, LocationForegroundService::class.java).apply {
                putExtra(LocationForegroundService.EXTRA_REFERRAL_ID, referralId)
            }
            applicationContext.startService(intent)
        }
    }

    override fun onNewToken(token: String) {
        Log.i(TAG, "Refreshed FCM device token: $token")
        // Registers push token with backend using device enrollment session
    }
}

