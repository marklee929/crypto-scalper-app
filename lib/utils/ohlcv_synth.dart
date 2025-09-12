import 'dart:math';

double _toDouble(dynamic v) =>
    v is num ? v.toDouble() : double.parse(v.toString());

/// Aggregate 10-minute OHLCV candles into 50-minute candles.
///
/// Expects [tenMinute] ordered from oldest to newest.
/// Returns a list of aggregated candles as maps with
/// open/high/low/close/volume fields.
List<Map<String, double>> synth50mFrom10m(List<Map<String, dynamic>> tenMinute) {
  final result = <Map<String, double>>[];
  for (var i = 0; i + 4 < tenMinute.length; i += 5) {
    final chunk = tenMinute.sublist(i, i + 5);
    final open = _toDouble(chunk.first['open']);
    final close = _toDouble(chunk.last['close']);
    final high = chunk.map((c) => _toDouble(c['high'])).reduce(max);
    final low = chunk.map((c) => _toDouble(c['low'])).reduce(min);
    final volume =
        chunk.map((c) => _toDouble(c['volume'])).reduce((a, b) => a + b);
    result.add({
      'open': open,
      'high': high,
      'low': low,
      'close': close,
      'volume': volume,
    });
  }
  return result;
}
