import 'package:flutter_test/flutter_test.dart';
import 'package:crypto_scalper_app/utils/ohlcv_synth.dart';

void main() {
  test('synth50mFrom10m aggregates OHLCV correctly', () {
    final ten = [
      {'open': 1, 'high': 2, 'low': 1, 'close': 2, 'volume': 10},
      {'open': 2, 'high': 3, 'low': 2, 'close': 3, 'volume': 20},
      {'open': 3, 'high': 4, 'low': 3, 'close': 4, 'volume': 30},
      {'open': 4, 'high': 5, 'low': 4, 'close': 5, 'volume': 40},
      {'open': 5, 'high': 6, 'low': 5, 'close': 6, 'volume': 50},
    ];
    final result = synth50mFrom10m(ten);
    expect(result.length, 1);
    final c = result.first;
    expect(c['open'], 1);
    expect(c['close'], 6);
    expect(c['high'], 6);
    expect(c['low'], 1);
    expect(c['volume'], 150);
  });
}
