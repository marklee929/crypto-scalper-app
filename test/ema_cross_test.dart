import 'package:flutter_test/flutter_test.dart';
import 'package:crypto_scalper_app/utils/ema_utils.dart';

void main() {
  test('detects golden cross', () {
    final prices = [
      ...List<double>.filled(20, 10),
      12,
      14,
      16,
      18,
      20,
    ];
    expect(detectEmaCross(prices), CrossSignal.golden);
  });

  test('detects death cross', () {
    final prices = [
      ...List<double>.filled(20, 20),
      18,
      16,
      14,
      12,
      10,
    ];
    expect(detectEmaCross(prices), CrossSignal.death);
  });

  test('no cross when EMAs equal', () {
    final prices = List<double>.filled(30, 10);
    expect(detectEmaCross(prices), CrossSignal.none);
  });
}
