import '../services/coinone_private.dart';
import '../utils/log.dart';

class TradeExecutor {
  String? _targetCoin;

  void setTargetCoin(String coin) {
    _targetCoin = coin;
  }

  /// 전량 매도 시도
  Future<bool> sellAll(double qty) async {
    if (_targetCoin == null) {
      log.e("❌ 코인이 설정되지 않았습니다 (sellAll)");
      return false;
    }
    if (qty <= 0) return false;

    log.i("🔻 매도 조건 충족 → 전량 매도 시도");
    final result = await CoinonePrivate.createMarketOrder(
      symbol: _targetCoin ?? '',
      side: 'sell',
      qty: qty,
    );

    final success = result != null && result['result'] == 'success';

    if (success) {
      log.i("✅ 전량 매도 완료: $qty $_targetCoin");
    } else {
      log.w("❌ 매도 실패");
    }

    return success;
  }

  /// 전액 매수 시도
  Future<bool> buyAll(double krwBalance, double price) async {
    if (_targetCoin == null) {
      log.e("❌ 코인이 설정되지 않았습니다 (buyAll)");
      return false;
    }

    if (krwBalance <= 1000 || price <= 0) return false;

    final qty = krwBalance / price;

    log.i("🟢 매수 조건 충족 → 전액 매수 시도");
    final result = await CoinonePrivate.createMarketOrder(
      symbol: _targetCoin ?? '',
      side: 'buy',
      qty: qty,
    );

    final success = result != null && result['result'] == 'success';

    if (success) {
      log.i("✅ 매수 성공: $qty $_targetCoin");
    } else {
      log.w("❌ 매수 실패");
    }

    return success;
  }
}
