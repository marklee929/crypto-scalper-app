import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/config.dart';
import '../utils/log.dart';
import 'package:uuid/uuid.dart';
import '../utils/rate_limiter.dart';

class CoinoneAPI {
  // Simple in-memory cache for candle data
  static final Map<String, _CandleCache> _candleCache = {};

  static Future<Map<String, dynamic>?> getAllTickers() async {
    final url = Uri.parse("https://api.coinone.co.kr/ticker?currency=all");
    try {
      final response = await RateLimiter.run(() => http.get(url));
      if (response.statusCode != 200) return null;
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      final result = <String, Map<String, dynamic>>{};
      data.forEach((key, value) {
        if (value is Map<String, dynamic> && value.containsKey('volume')) {
          result[key] = value;
        }
      });
      return result;
    } catch (e) {
      log.e("❌ 전체 티커 조회 오류: $e");
      return null;
    }
  }
  static Future<double?> getCurrentPrice(String coin) async {
    final url = Uri.parse("https://api.coinone.co.kr/ticker?currency=$coin");

    try {
      log.d("📡 [현재가 요청] $url");

      final response = await http.get(url);

      log.d("📥 [응답 상태] ${response.statusCode}");
      log.d("📦 [응답 본문] ${response.body}");

      if (response.statusCode != 200) {
        log.w("❗ 현재가 조회 실패 ($coin) → ${response.statusCode}");
        return null;
      }

      final data = jsonDecode(response.body);
      final priceStr = data['last'];
      if (priceStr == null) {
        log.w("❗ 현재가 데이터 없음 ($coin)");
        return null;
      }

      return double.tryParse(priceStr);
    } catch (e) {
      log.e("❌ 현재가 API 오류 ($coin): $e");
      return null;
    }
  }

  static Future<List<Map<String, dynamic>>?> getCandles(
    String symbol, {
    required String interval,
    int limit = 10,
  }) async {
    final cacheKey = '$symbol:$interval:$limit';
    final now = DateTime.now();
    final cached = _candleCache[cacheKey];
    if (cached != null && now.difference(cached.fetchedAt).inSeconds < 60) {
      return cached.data;
    }

    final url = Uri.parse(
      '${AppConfig.baseUrl}/public/v2/chart/KRW/$symbol?interval=$interval&size=$limit',
    );

    try {
      log.d("📡 [캔들 요청] $url");

      final response = await RateLimiter.run(() => http.get(url));

      log.d("📥 [응답 상태] ${response.statusCode}");
      log.d("📦 [응답 본문] ${response.body}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        log.i("📦 [응답 본문] ${jsonEncode(data).substring(0, 300)}");

        // ✅ chart 필드가 List<Map>인지 확인하고 반환
        if (data is Map<String, dynamic> && data.containsKey('chart')) {
          final chart = data['chart'];
          if (chart is List) {
            final list = List<Map<String, dynamic>>.from(chart);
            _candleCache[cacheKey] = _CandleCache(now, list);
            return list;
          } else {
            log.w("❗ 'chart' 필드는 리스트가 아님");
          }
        } else {
          log.w("❗ 'chart' 필드 없음 또는 JSON 구조 이상");
        }
      } else {
        log.w("❌ 응답 오류: ${response.statusCode}");
      }
    } catch (e) {
      log.e("⛔ ❌ 캔들 조회 오류: $e");
    }
    return null;
  }

}

class _CandleCache {
  final DateTime fetchedAt;
  final List<Map<String, dynamic>> data;
  _CandleCache(this.fetchedAt, this.data);
}
