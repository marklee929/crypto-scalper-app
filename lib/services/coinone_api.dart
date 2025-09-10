import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/config.dart';
import '../utils/log.dart';

class CoinoneAPI {
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
    final url = Uri.parse(
      '${AppConfig.baseUrl}/public/v2/chart/KRW/$symbol?interval=$interval&size=$limit',
    );

    try {

      log.d("📡 [캔들 요청] $url");

      final response = await http.get(url);

      log.d("📥 [응답 상태] ${response.statusCode}");
      log.d("📦 [응답 본문] ${response.body}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        log.i("📦 [응답 본문] ${jsonEncode(data).substring(0, 300)}");

        // ✅ chart 필드가 List<Map>인지 확인하고 반환
        if (data is Map<String, dynamic> && data.containsKey('chart')) {
          final chart = data['chart'];
          if (chart is List) {
            return List<Map<String, dynamic>>.from(chart);
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
