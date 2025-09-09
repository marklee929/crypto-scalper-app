import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import '../services/coinone_api.dart';
import '../services/auto_trade_service.dart';
import '../widgets/log_console_box.dart';
import 'dart:async';
import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';

import 'log_view_screen.dart';
import '../controller/log_console_controller.dart';
import '../utils/log_manager.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool isAutoTrading = false;
  double? currentPrice;
  double? holdingQty;
  String strategy = "상승 추종";
  double? profitRate;
  bool isLoading = true;

  final TextEditingController _coinController = TextEditingController();
  final autoTrader = AutoTradeService();

  bool _canStart = false;
  late final Timer _dashboardUpdater;

  final _logController = LogConsoleBoxController.live(); // 라이브 전용
  Directory? _logDir;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
    _initLogDir();
    _logController.attach(); // 라이브 스트림 구독 시작
    // 가시성 테스트 로그
    LogManager.instance.log('📲 대시보드 초기화 완료');

    _coinController.addListener(() {
      setState(() {
        _canStart = _coinController.text.trim().isNotEmpty;
      });
    });

    _dashboardUpdater = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted) return;
      if (autoTrader.latestPrice != null) {
        setState(() {
          currentPrice = autoTrader.latestPrice;
          profitRate = autoTrader.latestProfitRate;
        });
      }
    });
  }

  void _initLogDir() async {
    final dir = await getApplicationDocumentsDirectory();
    if (!mounted) return;
    setState(() {
      _logDir = dir;
    });
  }

  String _todayLogPath() {
    if (_logDir == null) return '';
    final now = DateTime.now();
    final filename =
        'trade_${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}.log';
    return '${_logDir!.path}/$filename';
  }

  void _startAutoTrading() async {
    final coin = _coinController.text.trim().toLowerCase();
    if (coin.isEmpty || autoTrader.isRunning) return;
    autoTrader.start(coin);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lastCoin', coin);
    if (!mounted) return;
    setState(() => isAutoTrading = true);
  }

  void _stopAutoTrading() {
    if (!autoTrader.isRunning) return;
    autoTrader.stop();
    setState(() => isAutoTrading = false);
  }

  Future<void> _loadInitialData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final coin = prefs.getString('lastCoin') ?? '';
      if (coin.isEmpty) {
        if (!mounted) return;
        setState(() => isLoading = false);
        return;
      }
      _coinController.text = coin;
      _canStart = true;

      final price = await CoinoneAPI.getCurrentPrice(coin);
      final balances = await CoinoneAPI.getBalanceMap();

      final qty =
          double.tryParse(balances?[coin.toLowerCase()]?['avail'] ?? '0') ?? 0;
      final avgPrice =
          double.tryParse(balances?[coin.toLowerCase()]?['avg'] ?? '0') ?? 0;
      final profit = (price != null && avgPrice > 0)
          ? ((price - avgPrice) / avgPrice * 100)
          : 0.0;

      if (!mounted) return;
      setState(() {
        currentPrice = price;
        holdingQty = qty;
        profitRate = profit;
        isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('초기 데이터 로드 실패: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('📡 코인 자동매매 대시보드'),
        actions: [
          IconButton(
            icon: const Icon(Icons.article),
            tooltip: '로그 보기',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const LogViewScreen()),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          if (isLoading) const LinearProgressIndicator(), // 로딩 표시
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  infoCard(
                    "현재가",
                    currentPrice != null
                        ? "${currentPrice!.toStringAsFixed(0)} KRW"
                        : "로딩 중...",
                  ),
                  infoCard(
                    "보유량",
                    holdingQty != null
                        ? "${holdingQty!.toStringAsFixed(2)} 개"
                        : "로딩 중...",
                  ),
                  infoCard("전략", strategy),
                  infoCard(
                    "수익률/트렌드",
                    profitRate != null
                        ? "${profitRate! >= 0 ? '+' : ''}${profitRate!.toStringAsFixed(2)}%/ ${autoTrader.getCurrentTrend()}"
                        : "로딩 중...",
                  ),
                  TextField(
                    controller: _coinController,
                    decoration: const InputDecoration(
                      labelText: "거래할 코인명 (예: trump)",
                      border: OutlineInputBorder(),
                    ),
                  ),
                  infoCard("상태", isAutoTrading ? "자동매매 중 ✅" : "정지 ⏹️"),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      ElevatedButton.icon(
                        icon: const Icon(Icons.play_arrow),
                        label: const Text("자동매매 시작"),
                        onPressed: _canStart && !isAutoTrading
                            ? _startAutoTrading
                            : null,
                      ),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.stop),
                        label: const Text("정지"),
                        onPressed: isAutoTrading ? _stopAutoTrading : null,
                      ),
                      const SizedBox(width: 12),
                      IconButton(
                        icon: const Icon(Icons.article),
                        tooltip: "📂 로그 파일 보기",
                        onPressed: () {
                          final path = _todayLogPath();
                          if (path.isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('로그 경로 초기화 중입니다. 잠시 후 다시 시도하세요.'),
                              ),
                            );
                            return;
                          }
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const LogViewScreen(), // 파라미터 제거
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          // 로그 콘솔
          SizedBox(
            height: 240,
            child: LogConsoleBox(
              isLive: true,
              controller: _logController,
              onClose: null,
            ),
          ),
        ],
      ),
    );
  }

  Widget infoCard(String title, String value) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: ListTile(
        leading: const Icon(Icons.trending_up),
        title: Text(title),
        trailing: Text(
          value,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _logController.dispose();
    _dashboardUpdater.cancel();
    _coinController.dispose();
    super.dispose();
  }
}
