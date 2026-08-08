package com.heartbeatcoinscalper.heart_beat_coin_scalper

object RuntimeContract {
    const val METHOD_CHANNEL = "com.heartbeatcoinscalper/runtime"
    const val ACTION_START =
        "com.heartbeatcoinscalper.heart_beat_coin_scalper.action.START"
    const val ACTION_STOP =
        "com.heartbeatcoinscalper.heart_beat_coin_scalper.action.STOP"
    const val ACTION_TEST_LISTING_ALERT =
        "com.heartbeatcoinscalper.heart_beat_coin_scalper.action.TEST_LISTING_ALERT"
    const val PREFERENCES = "monitoring_runtime"

    const val KEY_SESSION_REQUESTED = "session_requested"
    const val KEY_HEARTBEAT_AT = "heartbeat_at"
    const val KEY_WAKE_LOCK_HELD = "wake_lock_held"
    const val KEY_LAST_POLL_AT = "last_poll_at"
    const val KEY_LAST_SUCCESS_AT = "last_success_at"
    const val KEY_LAST_NOTICE_ID = "last_notice_id"
    const val KEY_LAST_NOTICE_TITLE = "last_notice_title"
    const val KEY_MATCHING_NOTICE_COUNT = "matching_notice_count"
    const val KEY_LAST_MATCHED_TICKER = "last_matched_ticker"
    const val KEY_LAST_MATCHED_FIRST_LISTED_AT = "last_matched_first_listed_at"
    const val KEY_CONSECUTIVE_FAILURES = "consecutive_failures"
    const val KEY_LAST_ERROR = "last_error"
}
