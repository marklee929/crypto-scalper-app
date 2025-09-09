import '../services/coinone_api.dart';
import 'dart:math';

class MarketAnalysis {
  /// 최근 N개 종가 기준 이동평균 반환
  Future<double?> getMovingAverage(
    String symbol, {
    String interval = "30m",
    int count = 10,
  }) async {
    final candles = await CoinoneAPI.getCandles(
      symbol,
      interval: interval,
      limit: count,
    );
    if (candles == null || candles.isEmpty) return null;

    final closes = candles
        .map((c) => double.tryParse(c['close'] ?? '0') ?? 0)
        .toList();

    final avg = closes.reduce((a, b) => a + b) / closes.length;
    return avg;
  }

  /// 현재가의 상대 위치 (%): (현재가 - 평균) / 평균
  double getRelativePosition(List<Map<String, dynamic>> candles, double price) {
    final lows = candles.map(
      (e) => double.tryParse(e['low'].toString()) ?? price,
    );
    final highs = candles.map(
      (e) => double.tryParse(e['high'].toString()) ?? price,
    );

    final min = lows.reduce((a, b) => a < b ? a : b);
    final max = highs.reduce((a, b) => a > b ? a : b);

    return max == min ? 0.5 : (price - min) / (max - min);
  }

  /// 최근 N봉의 고가/저가 기준 변동성 (%)
  Future<double?> getVolatility(
    String symbol, {
    String interval = "30m",
    int count = 10,
  }) async {
    final candles = await CoinoneAPI.getCandles(
      symbol,
      interval: interval,
      limit: count,
    );
    if (candles == null || candles.isEmpty) return null;

    final highs = candles
        .map((c) => double.tryParse(c['high'] ?? '0') ?? 0)
        .toList();
    final lows = candles
        .map((c) => double.tryParse(c['low'] ?? '0') ?? 0)
        .toList();

    final maxHigh = highs.reduce(max);
    final minLow = lows.reduce(min);

    if (minLow == 0) return null;

    return ((maxHigh - minLow) / minLow) * 100;
  }

  String getTrendState(List<Map<String, dynamic>> candles) {
    final closes = candles
        .map((e) => double.tryParse(e['close'].toString()) ?? 0)
        .toList();
    if (closes.length < 2) return "side";
    final first = closes.first;
    final last = closes.last;
    final change = (last - first) / first;

    if (change > 0.01) return "up";
    if (change < -0.01) return "down";
    return "side";
  }

  double getBottom(List<Map<String, dynamic>> candles) => candles
      .map((e) => double.tryParse(e['low'].toString()) ?? 0)
      .reduce((a, b) => a < b ? a : b);

  double getPeak(List<Map<String, dynamic>> candles) => candles
      .map((e) => double.tryParse(e['high'].toString()) ?? 0)
      .reduce((a, b) => a > b ? a : b);
}
