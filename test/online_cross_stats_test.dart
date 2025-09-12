import 'package:flutter_test/flutter_test.dart';
import 'package:crypto_scalper_app/utils/online_cross_stats.dart';

void main() {
  test('mean converges to true value', () {
    final stats = OnlineCrossStats();
    for (var i = 0; i < 100; i++) {
      stats.add(5.0);
    }
    expect((stats.mean - 5.0).abs() < 1e-6, isTrue);
    expect(stats.count, 100);
  });

  test('quantile band filtering', () {
    final stats = OnlineCrossStats();
    for (var i = 0; i < 100; i++) {
      stats.add(i.toDouble());
    }
    expect(stats.inQuantileBand(50, 0.1, 0.9), isTrue);
    expect(stats.inQuantileBand(5, 0.1, 0.9), isFalse);
  });
}
