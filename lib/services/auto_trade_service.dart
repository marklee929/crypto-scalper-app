import 'dart:async';
import '../services/coinone_api.dart';
import '../strategy/rebound_detector.dart';
import '../strategy/trend_guard.dart';
import '../strategy/trade_executor.dart';
import '../strategy/market_analysis.dart';
import '../utils/log.dart';
import '../utils/log_manager.dart';
// import '../../main.dart'; // 제거: 불필요 의존
import 'notification_service.dart'; // sendNotification 전역 함수 사용

class AutoTradeService {
  Timer? _timer;
  bool isRunning = false;
  final int _topK = 5;

  String? _targetCoin;
  double? latestPrice;
  double? latestProfitRate;

  final _marketAnalysis = MarketAnalysis();
  final _reboundDetector = ReboundDetector();
  final _trendGuard = TrendGuard();
  final _executor = TradeExecutor();

  String? currentTrend;

  DateTime _lastSummaryTime = DateTime.now().subtract(const Duration(hours: 1));

  void Function(String level, String message)? logHandler;

  void _log(String level, String message) {
    logHandler?.call(level, message);
    switch (level) {
      case "info":
        log.i(message);
        break;
      case "warn":
        log.w(message);
        break;
      case "error":
        log.e(message);
        break;
      default:
        log.d(message);
    }
  }

  void _emitInfo(String msg) {
    LogManager.instance.log('[INFO] $msg');
  }

  void _emitError(String msg) {
    LogManager.instance.log('[ERROR] $msg');
  }

  void start(String coin) {
    if (isRunning) return;
    isRunning = true;
    _targetCoin = coin;
    _executor.setTargetCoin(coin);
    _trendGuard.reset();

    _log("info", "✅ 자동매매 시작됨: $_targetCoin");

    _timer =
        Timer.periodic(const Duration(minutes: 1), (_) => _loop());
    _loop();
  }

  void stop() {
    if (!isRunning) return;
    _timer?.cancel();
    isRunning = false;
    _log("warn", "🛑 자동매매 중지됨");
  }

  void setCurrentTrend(String trend) {
    currentTrend = trend;
    _log("info", "현재 트렌드 업데이트: $trend");
  }

  String getCurrentTrend() {
    return currentTrend ?? "알 수 없음";
  }

  Future<void> _loop() async {
    try {
      final tickers = await CoinoneAPI.getAllTickers();
      if (tickers == null || tickers.isEmpty) return;

      final sorted = tickers.entries
          .map((e) => MapEntry(
              e.key, double.tryParse(e.value['volume']?.toString() ?? '0') ?? 0))
          .toList()
        ..sort((a, b) => b.value.compareTo(a.value));
      final candidates = sorted.take(_topK).map((e) => e.key).toList();

      if (candidates.isEmpty) return;
      _log('info', 'Top $_topK candidates: ${candidates.join(', ')}');

      _targetCoin = candidates.first;
      _executor.setTargetCoin(_targetCoin!);
      await _tick();
    } catch (e) {
      _log('error', '티커 조회 오류: $e');
    }
  }

  Future<void> _tick() async {
    if (_targetCoin == null) return;

    try {
      final price = await CoinoneAPI.getCurrentPrice(_targetCoin!);
      if (price == null) return;
      latestPrice = price;

      final balances = await CoinoneAPI.getBalanceMap();
      final coinData = balances?[_targetCoin!.toLowerCase()];
      final qty = double.tryParse(coinData?["avail"] ?? "0") ?? 0;
      final avg = double.tryParse(coinData?["avg"] ?? "0") ?? 0;
      final krw = double.tryParse(balances?["krw"]?["avail"] ?? "0") ?? 0;

      final c1h = await CoinoneAPI.getCandles(
        _targetCoin!,
        interval: '1h',
        limit: 12,
      );
      final m1 = await CoinoneAPI.getCandles(
        _targetCoin!,
        interval: '1m',
        limit: 50,
      );
      if (c1h == null || m1 == null || c1h.length < 6 || m1.length < 30) return;

      final trend30 = _marketAnalysis.getTrendState(m1.sublist(m1.length - 30));
      final trend10 = _marketAnalysis.getTrendState(m1.sublist(m1.length - 10));
      final relativePos = _marketAnalysis.getRelativePosition(c1h, price);

      final bottom = _marketAnalysis.getBottom(c1h.sublist(c1h.length - 6));
      final peak = _marketAnalysis.getPeak(c1h.sublist(c1h.length - 6));

      latestProfitRate = (avg > 0) ? ((price - avg) / avg * 100.0) : 0.0;

      if (qty > 0) {
        // 익절 조건
        final profitRatio = price / avg;
        _trendGuard.recordHigh(price); // 최고가 기록

        final shouldTakeProfit =
            profitRatio > 1.03 &&
            price < _trendGuard.highestPrice * 0.98 &&
            (trend30 == "down" || (trend30 == "side" && trend10 == "down"));

        final shouldCutLoss = false;
        // profitRatio < 0.97 &&
        // (trend30 == "down" || (trend30 == "side" && trend10 == "down"));

        if (shouldTakeProfit || shouldCutLoss) {
          _log("info", "📤 매도 조건 감지 (${shouldTakeProfit ? "익절" : "손절"})");
          await _executor.sellAll(qty);
          _trendGuard.reset();
        }
      } else {
        // 매수 조건
        final shouldBuy =
            price > bottom * 1.005 &&
            (trend30 == "up" || (trend30 == "side" && trend10 == "up")) &&
            krw >= 5000;

        if (shouldBuy) {
          _log("info", "📥 재매수 조건 충족 → 매수 시도");
          await _executor.buyAll(krw, price);
        }
      }

      // 🕒 1시간마다 요약 푸시 전송
      if (DateTime.now().difference(_lastSummaryTime).inMinutes >= 60) {
        _lastSummaryTime = DateTime.now();

        final trendStr = "30분: $trend30 / 10분: $trend10";
        setCurrentTrend(trendStr);

        final summary =
            """
      📊 [코인 요약 보고서]
          코인: $_targetCoin
          현재가: ${price.toStringAsFixed(0)} KRW
          보유량: ${qty.toStringAsFixed(4)} 개
          수익률: ${latestProfitRate!.toStringAsFixed(2)}%
          트렌드: $trendStr
        """;

        // 로그 대신 푸시 전송
        await sendNotification("📊 $_targetCoin 요약 보고서", summary);
      }
    } catch (e) {
      _log("error", "❌ 자동매매 오류: $e");
    }
  }
}
