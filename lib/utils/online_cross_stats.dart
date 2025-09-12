import 'dart:math';

/// Maintains running statistics for cross values.
class OnlineCrossStats {
  double _mean = 0;
  int _count = 0;
  final List<double> _values = [];

  void add(double value) {
    _count++;
    _mean += (value - _mean) / _count;
    _values.add(value);
  }

  double get mean => _mean;
  int get count => _count;

  double quantile(double q) {
    if (_values.isEmpty) return double.nan;
    final sorted = List<double>.from(_values)..sort();
    final pos = (sorted.length - 1) * q;
    final lower = sorted[pos.floor()];
    final upper = sorted[pos.ceil()];
    return lower + (upper - lower) * (pos - pos.floor());
  }

  bool inQuantileBand(double value, double lowerQ, double upperQ) {
    final lower = quantile(lowerQ);
    final upper = quantile(upperQ);
    return value >= lower && value <= upper;
  }
}
