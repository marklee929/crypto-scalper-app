import '../services/coinone_private.dart';
import '../utils/log.dart';

class OrderExecutor {
  /// Place a limit order and fall back to market if not fully filled.
  ///
  /// [symbol] trading pair (e.g. BTC)
  /// [side] 'buy' or 'sell'
  /// [qty] quantity to trade
  /// [limitPrice] baseline price for the limit order
  /// [timeoutSec] how many seconds to wait before cancelling
  /// [slipBps] price adjustment in basis points to increase fill probability
  static Future<bool> placeWithFallback(
    String symbol,
    String side,
    double qty,
    double limitPrice, {
    int timeoutSec = 3,
    double slipBps = 10,
  }) async {
    if (qty <= 0) return false;

    // Adjust limit price slightly to improve the chance of immediate fill.
    final adjPrice = side == 'buy'
        ? limitPrice * (1 + slipBps / 10000)
        : limitPrice * (1 - slipBps / 10000);

    log.i(
        '📦 Placing $side order for $qty $symbol (limit $adjPrice, timeout ${timeoutSec}s)');

    final limitRes = await CoinonePrivate.createLimitOrder(
      symbol: symbol,
      side: side,
      qty: qty,
      price: adjPrice,
    );

    if (limitRes == null || limitRes['result'] != 'success') {
      log.w('❌ Limit order failed, using market order.');
      final marketRes = await CoinonePrivate.createMarketOrder(
        symbol: symbol,
        side: side,
        qty: qty,
      );
      return marketRes != null && marketRes['result'] == 'success';
    }

    final orderId =
        limitRes['order_id']?.toString() ?? limitRes['orderId']?.toString();
    if (orderId == null) {
      log.w('⚠️ No order id returned, fallback to market.');
      final marketRes = await CoinonePrivate.createMarketOrder(
        symbol: symbol,
        side: side,
        qty: qty,
      );
      return marketRes != null && marketRes['result'] == 'success';
    }

    double remaining = qty;
    final start = DateTime.now();

    while (DateTime.now().difference(start).inSeconds < timeoutSec) {
      await Future.delayed(const Duration(milliseconds: 500));
      final info =
          await CoinonePrivate.getOrder(orderId: orderId, symbol: symbol);

      final remainStr = info?['remaining_qty'] ??
          info?['remainingQty'] ??
          info?['remain_qty'] ??
          info?['remainQty'] ??
          info?['remain'];

      if (remainStr != null) {
        remaining = double.tryParse(remainStr.toString()) ?? remaining;
      } else {
        final filledStr = info?['filled_qty'] ?? info?['filledQty'];
        if (filledStr != null) {
          final filled = double.tryParse(filledStr.toString()) ?? 0;
          remaining = (qty - filled).clamp(0, qty);
        }
      }

      if (remaining <= 0) {
        log.i('✅ Limit order filled.');
        return true;
      }
    }

    // Timeout reached - cancel and fallback
    await CoinonePrivate.cancelOrder(orderId: orderId, symbol: symbol);

    if (remaining > 0) {
      log.w('⌛ Timeout, placing market order for remaining $remaining.');
      final marketRes = await CoinonePrivate.createMarketOrder(
        symbol: symbol,
        side: side,
        qty: remaining,
      );
      return marketRes != null && marketRes['result'] == 'success';
    }

    return true;
  }
}
