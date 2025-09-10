import 'dart:convert';

import 'package:convert/convert.dart';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';

import '../config/config.dart';
import '../utils/log.dart';

/// Wrapper for Coinone's private REST endpoints (v2.1).
///
/// Provides helpers to create signed requests and expose
/// convenient methods for common account and order actions.
class CoinonePrivate {
  // ----------------------
  // Endpoint definitions
  // ----------------------
  static const _base = '/v2.1';
  static const _marketOrder = '$_base/order/market';
  static const _limitOrder = '$_base/order/limit';
  static const _cancelOrder = '$_base/order/cancel';
  static const _orderInfo = '$_base/order/status';
  static const _balanceAll = '$_base/account/balance/all';

  // ----------------------
  // Signature helpers
  // ----------------------
  static String _nonce() => const Uuid().v4();

  static Map<String, dynamic> _authBody(Map<String, dynamic> body) => {
        'access_token': AppConfig.apiKey,
        'nonce': _nonce(),
        ...body,
      };

  static Map<String, String> _headers(String jsonStr) {
    final base64Payload = base64.encode(utf8.encode(jsonStr));
    final hmac = Hmac(sha512, utf8.encode(AppConfig.apiSecret));
    final signature =
        hex.encode(hmac.convert(utf8.encode(base64Payload)).bytes);
    return {
      'Content-Type': 'application/json',
      'X-COINONE-PAYLOAD': base64Payload,
      'X-COINONE-SIGNATURE': signature,
    };
  }

  static Future<Map<String, dynamic>?> _post(
      String endpoint, Map<String, dynamic> body) async {
    final payload = _authBody(body);
    final jsonStr = jsonEncode(payload);
    final headers = _headers(jsonStr);
    final url = Uri.parse('${AppConfig.baseUrl}$endpoint');

    try {
      log.d("📡 [POST] $url");
      final res = await http.post(url, headers: headers, body: jsonStr);
      log.d("📥 [응답 상태] ${res.statusCode}");
      log.d("📦 [응답 본문] ${res.body}");

      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      log.e("❌ API 요청 오류: $e");
    }
    return null;
  }

  // ----------------------
  // API methods
  // ----------------------

  /// Create a market order.
  static Future<Map<String, dynamic>?> createMarketOrder({
    required String symbol,
    required String side,
    required double qty,
  }) async {
    return _post(_marketOrder, {
      'symbol': symbol.toLowerCase(),
      'side': side,
      'qty': qty.toString(),
    });
  }

  /// Create a limit order.
  static Future<Map<String, dynamic>?> createLimitOrder({
    required String symbol,
    required String side,
    required double qty,
    required double price,
  }) async {
    return _post(_limitOrder, {
      'symbol': symbol.toLowerCase(),
      'side': side,
      'qty': qty.toString(),
      'price': price.toString(),
    });
  }

  /// Cancel an order by [orderId].
  static Future<Map<String, dynamic>?> cancelOrder({
    required String orderId,
    required String symbol,
  }) async {
    return _post(_cancelOrder, {
      'order_id': orderId,
      'symbol': symbol.toLowerCase(),
    });
  }

  /// Retrieve details for a specific order.
  static Future<Map<String, dynamic>?> getOrder({
    required String orderId,
    required String symbol,
  }) async {
    return _post(_orderInfo, {
      'order_id': orderId,
      'symbol': symbol.toLowerCase(),
    });
  }

  /// Fetch raw balance list.
  static Future<List?> getBalances() async {
    final res = await _post(_balanceAll, {});
    return res?['balances'] as List?;
  }

  /// Convenience map of balances keyed by currency.
  static Future<Map<String, Map<String, String>>> getBalanceMap() async {
    final raw = await getBalances();
    if (raw == null) return {};

    final Map<String, Map<String, String>> result = {};
    for (final item in raw) {
      final currency = item['currency']?.toString().toLowerCase();
      if (currency != null) {
        result[currency] = {
          'avail': item['available'] ?? '0',
          'limit': item['limit'] ?? '0',
          'avg': item['average_price'] ?? '0',
        };
      }
    }
    return result;
  }
}

