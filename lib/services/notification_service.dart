// role: 로컬푸시, 요약 템플릿, 중복방지 키
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  NotificationService._();
  static final instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  String? _lastKey;

  Future<void> init() async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);
    await _plugin.initialize(initSettings);
  }

  Future<void> send({
    required String title,
    required String body,
    String? key,
  }) async {
    if (key != null && _lastKey == key) return; // 중복 방지
    _lastKey = key ?? '${title}_${body.hashCode}';

    const androidDetails = AndroidNotificationDetails(
      'trade',
      'Trade',
      importance: Importance.high,
      priority: Priority.high,
    );
    const details = NotificationDetails(android: androidDetails);
    await _plugin.show(0, title, body, details);
  }
}

// AutoTradeService에서 바로 쓸 수 있는 전역 함수(2개 인자)
Future<void> sendNotification(String title, String body, {String? key}) {
  return NotificationService.instance.send(title: title, body: body, key: key);
}
