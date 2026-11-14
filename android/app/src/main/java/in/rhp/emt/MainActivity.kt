package in.rhp.emt

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/**
 * MainActivity — Hybrid Interactive Screen for EMT & Mobile Hospital Desks.
 *
 * Provides:
 * 1. Base URL configuration (connects to laptop Wi-Fi LAN IP).
 * 2. Toggle button for continuous ambulance LocationForegroundService.
 * 3. Embedded full-screen web environment for immediate offline-capable PWA access.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var urlInput: EditText
    private lateinit var statusText: TextView
    private var isTracking = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Programmatic lightweight UI container without relying on XML layout inflation
        val rootLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        // Top Control Header
        val headerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(16, 16, 16, 16)
        }

        urlInput = EditText(this).apply {
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f)
            hint = "http://192.168.1.100:8080"
            setText("http://10.0.2.2:8080") // Android emulator host loopback
            textSize = 14f
        }

        val connectButton = Button(this).apply {
            text = "Open"
            setOnClickListener {
                val targetUrl = urlInput.text.toString().trim()
                if (targetUrl.isNotEmpty()) {
                    webView.loadUrl(targetUrl)
                }
            }
        }

        val trackButton = Button(this).apply {
            text = "GPS: OFF"
            setOnClickListener {
                toggleTracking(this)
            }
        }

        headerLayout.addView(urlInput)
        headerLayout.addView(connectButton)
        headerLayout.addView(trackButton)

        statusText = TextView(this).apply {
            text = "Protocol RHP-1 EMT Native Service: Ready"
            setPadding(16, 8, 16, 8)
            textSize = 12f
        }

        // Embedded WebView for React PWA views
        webView = WebView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1.0f
            )
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                cacheMode = WebSettings.LOAD_DEFAULT
            }
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(
                    view: WebView?,
                    errorCode: Int,
                    description: String?,
                    failingUrl: String?
                ) {
                    statusText.text = "Error: $description ($failingUrl)"
                }
            }
        }

        rootLayout.addView(headerLayout)
        rootLayout.addView(statusText)
        rootLayout.addView(webView)

        setContentView(rootLayout)

        requestPermissionsIfNeeded()
    }

    private fun toggleTracking(btn: Button) {
        if (!isTracking) {
            val serviceIntent = Intent(this, LocationForegroundService::class.java).apply {
                action = LocationForegroundService.ACTION_START_TRACKING
                putExtra(LocationForegroundService.EXTRA_BASE_URL, urlInput.text.toString())
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
            isTracking = true
            btn.text = "GPS: ON"
            statusText.text = "LocationForegroundService: Active (15s cadence, 200m geofence)"
        } else {
            val serviceIntent = Intent(this, LocationForegroundService::class.java).apply {
                action = LocationForegroundService.ACTION_STOP_TRACKING
            }
            startService(serviceIntent)
            isTracking = false
            btn.text = "GPS: OFF"
            statusText.text = "LocationForegroundService: Stopped"
        }
    }

    private fun requestPermissionsIfNeeded() {
        val permissions = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), 101)
        }
    }
}
