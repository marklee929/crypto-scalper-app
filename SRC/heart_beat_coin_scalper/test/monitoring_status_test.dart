import 'package:heart_beat_coin_scalper/runtime/monitoring_status.dart';
import 'package:test/test.dart';

void main() {
  test('native status map is converted without losing numeric values', () {
    final status = MonitoringStatus.fromMap(const {
      'requested': true,
      'running': true,
      'wakeLockHeld': true,
      'isCharging': true,
      'batteryLevel': 87,
      'ignoringBatteryOptimizations': true,
      'notificationPermissionGranted': true,
      'pollIntervalSeconds': 3,
      'lastPollAt': 1786146000123,
      'lastSuccessAt': 1786146000456,
      'lastNoticeId': 6457,
      'lastNoticeTitle': '공지 제목',
      'matchingNoticeCount': 2,
      'lastMatchedTicker': 'KMNO',
      'lastMatchedFirstListedAt': '2026-08-07T11:09:45+09:00',
      'consecutiveFailures': 0,
      'lastError': '',
    });

    expect(status.running, isTrue);
    expect(status.wakeLockHeld, isTrue);
    expect(status.batteryLevel, 87);
    expect(status.lastNoticeId, 6457);
    expect(status.lastMatchedTicker, 'KMNO');
    expect(status.lastSuccessAt, 1786146000456);
  });

  test('missing platform fields use safe defaults', () {
    final status = MonitoringStatus.fromMap(const {});

    expect(status.running, isFalse);
    expect(status.lastNoticeId, 0);
    expect(status.lastError, isEmpty);
  });
}
