class TrendGuard {
  double? _peakPrice;
  double highestPrice = 0.0;

  bool shouldSell(double current, double latestBuy) {
    if (_peakPrice == null || current > _peakPrice!) {
      _peakPrice = current;
    }

    final profitRate = ((current - latestBuy) / latestBuy) * 100;
    final drawdownRate = ((_peakPrice! - current) / _peakPrice!) * 100;

    return profitRate >= 3 && drawdownRate >= 2;
  }

  void recordHigh(double price) {
    if (price > highestPrice) highestPrice = price;
  }

  void reset() {
    highestPrice = 0.0;
    _peakPrice = null;
  }
}
