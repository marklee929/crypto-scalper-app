package com.heartbeatcoinscalper.heart_beat_coin_scalper

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            RuntimeContract.METHOD_CHANNEL,
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "getStatus" -> result.success(NoticeMonitoringService.readStatus(this))
                "startMonitoring" -> {
                    val intent = Intent(this, NoticeMonitoringService::class.java)
                        .setAction(RuntimeContract.ACTION_START)
                    ContextCompat.startForegroundService(this, intent)
                    result.success(null)
                }
                "stopMonitoring" -> {
                    val intent = Intent(this, NoticeMonitoringService::class.java)
                        .setAction(RuntimeContract.ACTION_STOP)
                    startService(intent)
                    result.success(null)
                }
                "sendTestListingAlert" -> {
                    val intent = Intent(this, NoticeMonitoringService::class.java)
                        .setAction(RuntimeContract.ACTION_TEST_LISTING_ALERT)
                    startService(intent)
                    result.success(null)
                }
                "requestNotificationPermission" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                        ContextCompat.checkSelfPermission(
                            this,
                            Manifest.permission.POST_NOTIFICATIONS,
                        ) != android.content.pm.PackageManager.PERMISSION_GRANTED
                    ) {
                        ActivityCompat.requestPermissions(
                            this,
                            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                            NOTIFICATION_PERMISSION_REQUEST,
                        )
                    }
                    result.success(null)
                }
                "requestBatteryOptimizationExemption" -> {
                    try {
                        startActivity(
                            Intent(
                                Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                                Uri.parse("package:$packageName"),
                            ),
                        )
                        result.success(null)
                    } catch (error: Exception) {
                        result.error(
                            "BATTERY_SETTINGS_FAILED",
                            error.message,
                            null,
                        )
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 4101
    }
}
