import 'dart:async';

class RateLimiter {
  const RateLimiter._();

  /// Runs [action] with simple exponential backoff.
  /// Retries up to [maxAttempts] times when an exception is thrown.
  static Future<T> run<T>(Future<T> Function() action,
      {int maxAttempts = 3, Duration initialDelay = const Duration(milliseconds: 500)}) async {
    var attempt = 0;
    var delay = initialDelay;
    while (true) {
      try {
        return await action();
      } catch (e) {
        attempt++;
        if (attempt >= maxAttempts) rethrow;
        await Future.delayed(delay);
        delay *= 2;
      }
    }
  }
}
