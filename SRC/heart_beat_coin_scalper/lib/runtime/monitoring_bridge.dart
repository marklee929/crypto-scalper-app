import 'package:flutter/services.dart';

import 'monitoring_status.dart';

abstract final class MonitoringBridge {
  static const _channel = MethodChannel('com.heartbeatcoinscalper/runtime');

  static Future<MonitoringStatus> getStatus() async {
    final value = await _channel.invokeMapMethod<String, dynamic>('getStatus');
    return MonitoringStatus.fromMap(value ?? const <String, dynamic>{});
  }

  static Future<void> startMonitoring() async {
    await _channel.invokeMethod<void>('startMonitoring');
  }

  static Future<void> stopMonitoring() async {
    await _channel.invokeMethod<void>('stopMonitoring');
  }

  static Future<void> sendTestListingAlert() async {
    await _channel.invokeMethod<void>('sendTestListingAlert');
  }

  static Future<void> requestNotificationPermission() async {
    await _channel.invokeMethod<void>('requestNotificationPermission');
  }

  static Future<void> requestBatteryOptimizationExemption() async {
    await _channel.invokeMethod<void>('requestBatteryOptimizationExemption');
  }
}
