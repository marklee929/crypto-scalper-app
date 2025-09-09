import 'market_analysis.dart';
import '../services/coinone_api.dart';
import '../utils/log.dart';

class ReboundDetector {
  final _marketAnalysis = MarketAnalysis();

  /// 반등 시작 여부 판단 (30분봉 + 일봉 조합)
  Future<bool> shouldRebound(String symbol) async {
    try {
      final candles30m = await CoinoneAPI.getCandles(
        symbol,
        interval: "30m",
        limit: 10,
      );
      final candles1d = await CoinoneAPI.getCandles(
        symbol,
        interval: "1d",
        limit: 5,
      );

      if (candles30m == null || candles1d == null) {
        log.w("❗ 캔들 데이터 불러오기 실패");
        return false;
      }

      final isShortRebound = _analyzeCandleRebound(candles30m);
      final isLongRebound = _analyzeCandleRebound(candles1d);

      if (isShortRebound && isLongRebound) {
        log.i("📈 [반등 시그널 감지] 30분봉 + 일봉 모두 조건 만족");
        return true;
      } else {
        log.i("⚠️ 반등 조건 미충족 (30m: $isShortRebound, 1d: $isLongRebound)");
        return false;
      }
    } catch (e) {
      log.e("❌ 반등 판단 중 오류: $e");
      return false;
    }
  }

  bool _analyzeCandleRebound(List<Map<String, dynamic>> candles) {
    if (candles.length < 4) return false;

    final prev = candles.sublist(1, 4);
    final is3Down = prev.every((c) => _isBearish(c));
    final last = candles[0];

    final isLastBullish = _isBullish(last);
    final lastVolume = double.tryParse(last['volume'] ?? '0') ?? 0;
    final prevVolume = double.tryParse(prev[0]['volume'] ?? '0') ?? 0;

    return is3Down && isLastBullish && lastVolume > prevVolume;
  }

  bool _isBullish(Map<String, dynamic> candle) {
    final open = double.tryParse(candle['open'] ?? '0') ?? 0;
    final close = double.tryParse(candle['close'] ?? '0') ?? 0;
    return close > open;
  }

  bool _isBearish(Map<String, dynamic> candle) {
    final open = double.tryParse(candle['open'] ?? '0') ?? 0;
    final close = double.tryParse(candle['close'] ?? '0') ?? 0;
    return close < open;
  }

  Future<bool> shouldBuy(String coin) async {
    final candles1h = await CoinoneAPI.getCandles(
      coin,
      interval: "1h",
      limit: 12,
    );
    final price = await CoinoneAPI.getCurrentPrice(coin);

    if (candles1h == null || price == null) {
      log.w("📉 상대위치 계산 불가 → 데이터 부족");
      return false;
    }

    final relative =
        _marketAnalysis.getRelativePosition(candles1h, price) *
        100; // 0~1 → 0~100%

    if (relative != null && relative > 10.0) {
      log.w("⚠️ 현재가가 평균보다 너무 높음 (${relative.toStringAsFixed(2)}%) → 진입 보류");
      return false;
    }

    // 2. 최근 추세 비교 (예시: 30분 전보다 가격이 1% 이상 상승했으면 반등으로 간주)
    final candles = await CoinoneAPI.getCandles(
      coin,
      interval: "30m",
      limit: 2,
    );
    if (candles == null || candles.length < 2) {
      log.w("📉 캔들 데이터 부족 → 반등 판단 불가");
      return false;
    }

    final prevClose = double.tryParse(candles[0]['close']?.toString() ?? '');
    final current = double.tryParse(candles[1]['close']?.toString() ?? '');
    if (prevClose == null || current == null) {
      log.w("❗ 캔들 데이터 오류 → 매수 판단 불가");
      return false;
    }

    final changeRate = (current - prevClose) / prevClose * 100;
    final result = changeRate > 1.0;

    log.i(
      "📈 반등 감지 → 이전: $prevClose, 현재: $current, 변동률: ${changeRate.toStringAsFixed(2)}% → 매수 판단: $result",
    );
    return result;
  }
}
