/// Simple EMA and cross-detection helpers.

enum CrossSignal { none, golden, death }

List<double> ema(List<double> prices, int period) {
  final k = 2 / (period + 1);
  final result = <double>[];
  double? prev;
  for (final p in prices) {
    prev = prev == null ? p : prev + (p - prev) * k;
    result.add(prev);
  }
  return result;
}

CrossSignal detectEmaCross(List<double> prices,
    {int shortPeriod = 9, int longPeriod = 21}) {
  if (prices.length < 2) return CrossSignal.none;
  final short = ema(prices, shortPeriod);
  final long = ema(prices, longPeriod);
  if (short.length < 2 || long.length < 2) return CrossSignal.none;
  final prevShort = short[short.length - 2];
  final prevLong = long[long.length - 2];
  final currShort = short.last;
  final currLong = long.last;
  if (prevShort <= prevLong && currShort > currLong) {
    return CrossSignal.golden;
  }
  if (prevShort >= prevLong && currShort < currLong) {
    return CrossSignal.death;
  }
  return CrossSignal.none;
}
