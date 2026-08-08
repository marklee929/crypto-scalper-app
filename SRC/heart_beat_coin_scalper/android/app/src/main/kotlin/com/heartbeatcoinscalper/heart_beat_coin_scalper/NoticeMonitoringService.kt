package com.heartbeatcoinscalper.heart_beat_coin_scalper

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.BatteryManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class NoticeMonitoringService : Service() {
    private var scheduler: ScheduledExecutorService? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private val polling = AtomicBoolean(false)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == RuntimeContract.ACTION_STOP) {
            stopMonitoring()
            return START_NOT_STICKY
        }

        val preferences = preferences(this)
        val explicitlyStarted = intent?.action == RuntimeContract.ACTION_START
        val shouldResume = preferences.getBoolean(
            RuntimeContract.KEY_SESSION_REQUESTED,
            false,
        )
        if (!explicitlyStarted && !shouldResume) {
            stopSelf()
            return START_NOT_STICKY
        }

        preferences.edit()
            .putBoolean(RuntimeContract.KEY_SESSION_REQUESTED, true)
            .putLong(RuntimeContract.KEY_HEARTBEAT_AT, System.currentTimeMillis())
            .apply()

        startAsForeground()
        acquireWakeLock()
        startPollingIfNeeded()
        if (intent?.action == RuntimeContract.ACTION_TEST_LISTING_ALERT) {
            showListingAlert(
                UpbitNotice(
                    id = TEST_NOTICE_ID,
                    uuid = "diagnostic",
                    title = "테스트코인(TEST) 신규 거래지원 안내 (KRW 마켓)",
                    category = "거래",
                    listedAt = "diagnostic",
                    firstListedAt = "diagnostic-now",
                ),
                "TEST",
            )
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scheduler?.shutdownNow()
        scheduler = null
        releaseWakeLock()
        preferences(this).edit()
            .putLong(RuntimeContract.KEY_HEARTBEAT_AT, 0L)
            .putBoolean(RuntimeContract.KEY_WAKE_LOCK_HELD, false)
            .apply()
        super.onDestroy()
    }

    private fun startAsForeground() {
        val notification = buildOngoingNotification("서비스 시작 중 · 공지 기준점 확인")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val serviceType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            } else {
                0
            }
            if (serviceType != 0) {
                startForeground(ONGOING_NOTIFICATION_ID, notification, serviceType)
            } else {
                startForeground(ONGOING_NOTIFICATION_ID, notification)
            }
        } else {
            startForeground(ONGOING_NOTIFICATION_ID, notification)
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "$packageName:notice-monitor",
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
        preferences(this).edit()
            .putBoolean(RuntimeContract.KEY_WAKE_LOCK_HELD, true)
            .apply()
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        preferences(this).edit()
            .putBoolean(RuntimeContract.KEY_WAKE_LOCK_HELD, false)
            .apply()
    }

    private fun startPollingIfNeeded() {
        if (scheduler != null) return
        scheduler = Executors.newSingleThreadScheduledExecutor().also { executor ->
            executor.scheduleWithFixedDelay(
                { pollSafely() },
                0L,
                POLL_INTERVAL_SECONDS.toLong(),
                TimeUnit.SECONDS,
            )
        }
    }

    private fun pollSafely() {
        if (!polling.compareAndSet(false, true)) return
        val now = System.currentTimeMillis()
        preferences(this).edit()
            .putLong(RuntimeContract.KEY_HEARTBEAT_AT, now)
            .putLong(RuntimeContract.KEY_LAST_POLL_AT, now)
            .apply()
        try {
            pollAnnouncements()
        } catch (error: Exception) {
            recordFailure(error)
        } finally {
            preferences(this).edit()
                .putLong(RuntimeContract.KEY_HEARTBEAT_AT, System.currentTimeMillis())
                .putBoolean(
                    RuntimeContract.KEY_WAKE_LOCK_HELD,
                    wakeLock?.isHeld == true,
                )
                .apply()
            polling.set(false)
        }
    }

    private fun pollAnnouncements() {
        val connection = URL(ANNOUNCEMENT_URL).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", USER_AGENT)
            connection.useCaches = false

            val statusCode = connection.responseCode
            if (statusCode != HttpURLConnection.HTTP_OK) {
                throw IllegalStateException("Upbit HTTP $statusCode")
            }
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            processResponse(body)
        } finally {
            connection.disconnect()
        }
    }

    private fun processResponse(body: String) {
        val root = JSONObject(body)
        check(root.optBoolean("success")) { "Upbit success=false" }
        val notices = root.getJSONObject("data").getJSONArray("notices")
        check(notices.length() > 0) { "Upbit notices is empty" }

        val parsed = parseNotices(notices)
        check(parsed.isNotEmpty()) { "No valid notice contract" }
        val newest = parsed.maxBy { it.id }
        val prefs = preferences(this)
        val previousId = prefs.getLong(RuntimeContract.KEY_LAST_NOTICE_ID, 0L)

        val editor = prefs.edit()
            .putLong(RuntimeContract.KEY_LAST_SUCCESS_AT, System.currentTimeMillis())
            .putLong(RuntimeContract.KEY_LAST_NOTICE_ID, newest.id)
            .putString(RuntimeContract.KEY_LAST_NOTICE_TITLE, newest.title)
            .putInt(RuntimeContract.KEY_CONSECUTIVE_FAILURES, 0)
            .putString(RuntimeContract.KEY_LAST_ERROR, "")

        if (previousId > 0L) {
            var matchingCount = prefs.getInt(
                RuntimeContract.KEY_MATCHING_NOTICE_COUNT,
                0,
            )
            parsed
                .filter { it.id > previousId }
                .sortedBy { it.id }
                .forEach { notice ->
                    if (notice.isNewMarketSupport()) {
                        val ticker = extractTicker(notice.title)
                        matchingCount += 1
                        editor
                            .putInt(
                                RuntimeContract.KEY_MATCHING_NOTICE_COUNT,
                                matchingCount,
                            )
                            .putString(RuntimeContract.KEY_LAST_MATCHED_TICKER, ticker)
                            .putString(
                                RuntimeContract.KEY_LAST_MATCHED_FIRST_LISTED_AT,
                                notice.firstListedAt,
                            )
                        showListingAlert(notice, ticker)
                    }
                }
        }

        editor.apply()
        updateOngoingNotification(
            "정상 · 최신 #${newest.id} · " +
                newest.title.take(32),
        )
    }

    private fun parseNotices(notices: JSONArray): List<UpbitNotice> {
        val result = mutableListOf<UpbitNotice>()
        for (index in 0 until notices.length()) {
            val value = notices.optJSONObject(index) ?: continue
            if (!value.has("id") ||
                !value.has("title") ||
                !value.has("category") ||
                !value.has("listed_at") ||
                !value.has("first_listed_at")
            ) {
                continue
            }
            result += UpbitNotice(
                id = value.getLong("id"),
                uuid = value.optString("uuid"),
                title = value.getString("title"),
                category = value.getString("category"),
                listedAt = value.getString("listed_at"),
                firstListedAt = value.getString("first_listed_at"),
            )
        }
        return result
    }

    private fun extractTicker(title: String): String {
        val candidates = TICKER_PATTERN.findAll(title).map { it.groupValues[1] }
        return candidates.firstOrNull { it !in MARKET_CODES } ?: "UNKNOWN"
    }

    private fun recordFailure(error: Exception) {
        val prefs = preferences(this)
        val failures = prefs.getInt(RuntimeContract.KEY_CONSECUTIVE_FAILURES, 0) + 1
        val message = "${error.javaClass.simpleName}: ${error.message ?: "unknown"}".take(300)
        prefs.edit()
            .putInt(RuntimeContract.KEY_CONSECUTIVE_FAILURES, failures)
            .putString(RuntimeContract.KEY_LAST_ERROR, message)
            .apply()
        updateOngoingNotification("오류 ${failures}회 · $message")
    }

    private fun stopMonitoring() {
        preferences(this).edit()
            .putBoolean(RuntimeContract.KEY_SESSION_REQUESTED, false)
            .putLong(RuntimeContract.KEY_HEARTBEAT_AT, 0L)
            .apply()
        scheduler?.shutdownNow()
        scheduler = null
        releaseWakeLock()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun buildOngoingNotification(content: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, NoticeMonitoringService::class.java)
                .setAction(RuntimeContract.ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, MONITORING_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("Heart Beat monitoring active")
            .setContentText(content)
            .setStyle(NotificationCompat.BigTextStyle().bigText(content))
            .setContentIntent(openIntent)
            .addAction(android.R.drawable.ic_media_pause, "중지", stopIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun updateOngoingNotification(content: String) {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(ONGOING_NOTIFICATION_ID, buildOngoingNotification(content))
    }

    private fun showListingAlert(notice: UpbitNotice, ticker: String) {
        val openIntent = PendingIntent.getActivity(
            this,
            notice.id.toInt(),
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, LISTING_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_warning)
            .setContentTitle("신규 거래지원 감지 · $ticker")
            .setContentText(notice.title)
            .setStyle(
                NotificationCompat.BigTextStyle().bigText(
                    "${notice.title}\nfirst_listed_at: ${notice.firstListedAt}",
                ),
            )
            .setContentIntent(openIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(LISTING_NOTIFICATION_BASE_ID + notice.id.toInt(), notification)
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(
                MONITORING_CHANNEL_ID,
                "자동매매 런타임",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "S23 공지 감시 foreground service 상태"
                setShowBadge(false)
            },
        )
        manager.createNotificationChannel(
            NotificationChannel(
                LISTING_CHANNEL_ID,
                "신규 거래지원 감지",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "업비트 신규 거래지원 공지 알림"
            },
        )
    }

    private data class UpbitNotice(
        val id: Long,
        val uuid: String,
        val title: String,
        val category: String,
        val listedAt: String,
        val firstListedAt: String,
    ) {
        fun isNewMarketSupport(): Boolean {
            if (category != "거래") return false
            if (title.contains("거래지원 종료") || title.contains("유의 종목")) return false
            return title.contains("신규 거래지원") || title.contains("디지털 자산 추가")
        }
    }

    companion object {
        private const val ANNOUNCEMENT_URL =
            "https://pub-info.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all"
        private const val USER_AGENT = "HeartBeatCoinScalper/0.1 Android"
        private const val POLL_INTERVAL_SECONDS = 3
        private const val CONNECT_TIMEOUT_MS = 5_000
        private const val READ_TIMEOUT_MS = 5_000
        private const val ACTIVE_HEARTBEAT_WINDOW_MS = 20_000L
        private const val MONITORING_CHANNEL_ID = "monitoring_runtime"
        private const val LISTING_CHANNEL_ID = "listing_alerts"
        private const val ONGOING_NOTIFICATION_ID = 1101
        private const val LISTING_NOTIFICATION_BASE_ID = 20_000
        private const val TEST_NOTICE_ID = 900_001L
        private val TICKER_PATTERN = Regex("\\(([A-Z0-9]{2,15})\\)")
        private val MARKET_CODES = setOf("KRW", "BTC", "USDT")

        private fun preferences(context: Context) = context.getSharedPreferences(
            RuntimeContract.PREFERENCES,
            Context.MODE_PRIVATE,
        )

        fun readStatus(context: Context): Map<String, Any> {
            val prefs = preferences(context)
            val now = System.currentTimeMillis()
            val requested = prefs.getBoolean(
                RuntimeContract.KEY_SESSION_REQUESTED,
                false,
            )
            val heartbeatAt = prefs.getLong(RuntimeContract.KEY_HEARTBEAT_AT, 0L)
            val running = requested && heartbeatAt > 0L &&
                now - heartbeatAt <= ACTIVE_HEARTBEAT_WINDOW_MS
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
            val batteryLevel = batteryManager.getIntProperty(
                BatteryManager.BATTERY_PROPERTY_CAPACITY,
            ).coerceAtLeast(0)
            val batteryStatus = context.registerReceiver(
                null,
                android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED),
            )?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
            val charging = batteryStatus == BatteryManager.BATTERY_STATUS_CHARGING ||
                batteryStatus == BatteryManager.BATTERY_STATUS_FULL
            val notificationsGranted = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS,
                ) == PackageManager.PERMISSION_GRANTED

            return mapOf(
                "requested" to requested,
                "running" to running,
                "wakeLockHeld" to (
                    running && prefs.getBoolean(
                        RuntimeContract.KEY_WAKE_LOCK_HELD,
                        false,
                    )
                    ),
                "isCharging" to charging,
                "batteryLevel" to batteryLevel,
                "ignoringBatteryOptimizations" to
                    powerManager.isIgnoringBatteryOptimizations(context.packageName),
                "notificationPermissionGranted" to notificationsGranted,
                "pollIntervalSeconds" to POLL_INTERVAL_SECONDS,
                "lastPollAt" to prefs.getLong(RuntimeContract.KEY_LAST_POLL_AT, 0L),
                "lastSuccessAt" to prefs.getLong(
                    RuntimeContract.KEY_LAST_SUCCESS_AT,
                    0L,
                ),
                "lastNoticeId" to prefs.getLong(
                    RuntimeContract.KEY_LAST_NOTICE_ID,
                    0L,
                ),
                "lastNoticeTitle" to (
                    prefs.getString(RuntimeContract.KEY_LAST_NOTICE_TITLE, "") ?: ""
                    ),
                "matchingNoticeCount" to prefs.getInt(
                    RuntimeContract.KEY_MATCHING_NOTICE_COUNT,
                    0,
                ),
                "lastMatchedTicker" to (
                    prefs.getString(RuntimeContract.KEY_LAST_MATCHED_TICKER, "") ?: ""
                    ),
                "lastMatchedFirstListedAt" to (
                    prefs.getString(
                        RuntimeContract.KEY_LAST_MATCHED_FIRST_LISTED_AT,
                        "",
                    ) ?: ""
                    ),
                "consecutiveFailures" to prefs.getInt(
                    RuntimeContract.KEY_CONSECUTIVE_FAILURES,
                    0,
                ),
                "lastError" to (
                    prefs.getString(RuntimeContract.KEY_LAST_ERROR, "") ?: ""
                    ),
            )
        }
    }
}
