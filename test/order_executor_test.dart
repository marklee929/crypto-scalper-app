import 'package:flutter_test/flutter_test.dart';
import 'package:crypto_scalper_app/trade/order_executor.dart';
import 'package:crypto_scalper_app/services/coinone_private.dart';

void main() {
  tearDown(() {
    // Reset injected functions after each test
    createLimitOrder = CoinonePrivate.createLimitOrder;
    createMarketOrder = CoinonePrivate.createMarketOrder;
    getOrder = CoinonePrivate.getOrder;
    cancelOrder = CoinonePrivate.cancelOrder;
  });

  test('falls back to market when limit fails', () async {
    createLimitOrder = ({symbol, side, qty, price}) async => {'result': 'error'};
    var marketCalled = false;
    createMarketOrder = ({symbol, side, qty}) async {
      marketCalled = true;
      return {'result': 'success'};
    };
    final ok = await OrderExecutor.placeWithFallback('btc', 'buy', 1, 100,
        timeoutSec: 0);
    expect(ok, isTrue);
    expect(marketCalled, isTrue);
  });

  test('cancels and markets remaining on timeout', () async {
    createLimitOrder = ({symbol, side, qty, price}) async =>
        {'result': 'success', 'order_id': '1'};
    cancelOrder = ({orderId, symbol}) async => {'result': 'success'};
    var marketQty = 0.0;
    createMarketOrder = ({symbol, side, qty}) async {
      marketQty = qty;
      return {'result': 'success'};
    };
    final ok = await OrderExecutor.placeWithFallback('btc', 'buy', 1, 100,
        timeoutSec: 0);
    expect(ok, isTrue);
    expect(marketQty, 1);
  });
}
