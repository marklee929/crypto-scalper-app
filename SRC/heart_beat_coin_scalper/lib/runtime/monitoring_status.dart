class MonitoringStatus {
  const MonitoringStatus({
    required this.requested,
    required this.running,
    required this.wakeLockHeld,
    required this.isCharging,
    required this.batteryLevel,
    required this.ignoringBatteryOptimizations,
    required this.notificationPermissionGranted,
    required this.pollIntervalSeconds,
    required this.lastPollAt,
    required this.lastSuccessAt,
    required this.lastNoticeId,
    required this.lastNoticeTitle,
    required this.matchingNoticeCount,
    required this.lastMatchedTicker,
    required this.lastMatchedFirstListedAt,
    required this.consecutiveFailures,
    required this.lastError,
  });

  static const empty = MonitoringStatus(
    requested: false,
    running: false,
    wakeLockHeld: false,
    isCharging: false,
    batteryLevel: 0,
    ignoringBatteryOptimizations: false,
    notificationPermissionGranted: false,
    pollIntervalSeconds: 3,
    lastPollAt: 0,
    lastSuccessAt: 0,
    lastNoticeId: 0,
    lastNoticeTitle: '',
    matchingNoticeCount: 0,
    lastMatchedTicker: '',
    lastMatchedFirstListedAt: '',
    consecutiveFailures: 0,
    lastError: '',
  );

  factory MonitoringStatus.fromMap(Map<String, dynamic> map) {
    int integer(String key) => (map[key] as num?)?.toInt() ?? 0;
    bool boolean(String key) => map[key] as bool? ?? false;
    String text(String key) => map[key]?.toString() ?? '';

    return MonitoringStatus(
      requested: boolean('requested'),
      running: boolean('running'),
      wakeLockHeld: boolean('wakeLockHeld'),
      isCharging: boolean('isCharging'),
      batteryLevel: integer('batteryLevel'),
      ignoringBatteryOptimizations: boolean('ignoringBatteryOptimizations'),
      notificationPermissionGranted: boolean('notificationPermissionGranted'),
      pollIntervalSeconds: integer('pollIntervalSeconds'),
      lastPollAt: integer('lastPollAt'),
      lastSuccessAt: integer('lastSuccessAt'),
      lastNoticeId: integer('lastNoticeId'),
      lastNoticeTitle: text('lastNoticeTitle'),
      matchingNoticeCount: integer('matchingNoticeCount'),
      lastMatchedTicker: text('lastMatchedTicker'),
      lastMatchedFirstListedAt: text('lastMatchedFirstListedAt'),
      consecutiveFailures: integer('consecutiveFailures'),
      lastError: text('lastError'),
    );
  }

  final bool requested;
  final bool running;
  final bool wakeLockHeld;
  final bool isCharging;
  final int batteryLevel;
  final bool ignoringBatteryOptimizations;
  final bool notificationPermissionGranted;
  final int pollIntervalSeconds;
  final int lastPollAt;
  final int lastSuccessAt;
  final int lastNoticeId;
  final String lastNoticeTitle;
  final int matchingNoticeCount;
  final String lastMatchedTicker;
  final String lastMatchedFirstListedAt;
  final int consecutiveFailures;
  final String lastError;
}
