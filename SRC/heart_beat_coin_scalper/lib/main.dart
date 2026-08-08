import 'dart:async';

import 'package:flutter/material.dart';

import 'runtime/monitoring_bridge.dart';
import 'runtime/monitoring_status.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const HeartBeatCoinScalperApp());
}

class HeartBeatCoinScalperApp extends StatelessWidget {
  const HeartBeatCoinScalperApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF11B981),
      brightness: Brightness.dark,
    );
    return MaterialApp(
      title: 'Heart Beat Coin Scalper',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF08111F),
        cardTheme: const CardThemeData(
          color: Color(0xFF101C2D),
          margin: EdgeInsets.zero,
        ),
      ),
      home: const RuntimeDashboard(),
    );
  }
}

class RuntimeDashboard extends StatefulWidget {
  const RuntimeDashboard({super.key});

  @override
  State<RuntimeDashboard> createState() => _RuntimeDashboardState();
}

class _RuntimeDashboardState extends State<RuntimeDashboard>
    with WidgetsBindingObserver {
  MonitoringStatus _status = MonitoringStatus.empty;
  Timer? _refreshTimer;
  bool _busy = false;
  String? _uiError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_refresh());
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => unawaited(_refresh()),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_refresh());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final next = await MonitoringBridge.getStatus();
      if (!mounted) return;
      setState(() {
        _status = next;
        _uiError = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _uiError = error.toString());
    }
  }

  Future<void> _runAction(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _uiError = null;
    });
    try {
      await action();
      await Future<void>.delayed(const Duration(milliseconds: 500));
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => _uiError = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _status.running
        ? const Color(0xFF34D399)
        : _status.requested
        ? const Color(0xFFFBBF24)
        : const Color(0xFF94A3B8);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Heart Beat Coin Scalper'),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _busy ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            _HeaderCard(status: _status, statusColor: statusColor),
            const SizedBox(height: 12),
            if (_uiError != null) ...[
              _MessageCard(
                icon: Icons.error_outline,
                color: const Color(0xFFF87171),
                message: _uiError!,
              ),
              const SizedBox(height: 12),
            ],
            if (!_status.notificationPermissionGranted) ...[
              _MessageCard(
                icon: Icons.notifications_off_outlined,
                color: const Color(0xFFFBBF24),
                message: '알림 권한이 꺼져 있습니다. 시작할 때 권한 요청 화면이 표시됩니다.',
              ),
              const SizedBox(height: 12),
            ],
            if (!_status.ignoringBatteryOptimizations) ...[
              _MessageCard(
                icon: Icons.battery_alert_outlined,
                color: const Color(0xFFFBBF24),
                message: '수면 상태 장기 실행을 위해 배터리 최적화 제외가 필요합니다.',
                actionLabel: '설정 요청',
                onAction: _busy
                    ? null
                    : () => _runAction(
                        MonitoringBridge.requestBatteryOptimizationExemption,
                      ),
              ),
              const SizedBox(height: 12),
            ],
            _SectionCard(
              title: 'S23 런타임',
              icon: Icons.phone_android,
              children: [
                _StatusRow(
                  label: '서비스',
                  value: _status.running
                      ? 'HEALTHY'
                      : _status.requested
                      ? 'STARTING / STALE'
                      : 'STOPPED',
                ),
                _StatusRow(
                  label: '전원',
                  value: _status.isCharging
                      ? '충전 중 · ${_status.batteryLevel}%'
                      : '배터리 · ${_status.batteryLevel}%',
                ),
                _StatusRow(
                  label: 'Wake lock',
                  value: _status.wakeLockHeld ? 'ACTIVE' : 'INACTIVE',
                ),
                _StatusRow(
                  label: 'Polling',
                  value: '${_status.pollIntervalSeconds}초',
                ),
                _StatusRow(
                  label: '마지막 성공',
                  value: _formatTime(_status.lastSuccessAt),
                ),
                _StatusRow(
                  label: '연속 오류',
                  value: '${_status.consecutiveFailures}회',
                ),
              ],
            ),
            const SizedBox(height: 12),
            _SectionCard(
              title: '업비트 공지',
              icon: Icons.campaign_outlined,
              children: [
                _StatusRow(
                  label: '최신 ID',
                  value: _status.lastNoticeId == 0
                      ? '-'
                      : '${_status.lastNoticeId}',
                ),
                _StatusRow(
                  label: '최신 제목',
                  value: _status.lastNoticeTitle.ifBlank('-'),
                  multiline: true,
                ),
                _StatusRow(
                  label: '신규상장 감지',
                  value: '${_status.matchingNoticeCount}건',
                ),
                _StatusRow(
                  label: '최근 티커',
                  value: _status.lastMatchedTicker.ifBlank('-'),
                ),
                _StatusRow(
                  label: 'first_listed_at',
                  value: _status.lastMatchedFirstListedAt.ifBlank('-'),
                  multiline: true,
                ),
              ],
            ),
            const SizedBox(height: 12),
            _SectionCard(
              title: '자동매매 단계',
              icon: Icons.auto_graph,
              children: const [
                _StatusRow(label: '현재 빌드', value: '1차 런타임 테스트'),
                _StatusRow(label: '공지 감지', value: 'ACTIVE'),
                _StatusRow(label: '시장가 매수', value: 'NOT CONNECTED'),
                _StatusRow(label: '고정가 지정가 매도', value: 'NOT CONNECTED'),
              ],
            ),
            if (_status.lastError.isNotEmpty) ...[
              const SizedBox(height: 12),
              _MessageCard(
                icon: Icons.warning_amber_rounded,
                color: const Color(0xFFF87171),
                message: _status.lastError,
              ),
            ],
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _busy || _status.requested
                  ? null
                  : () => _runAction(() async {
                      await MonitoringBridge.requestNotificationPermission();
                      await MonitoringBridge.startMonitoring();
                    }),
              icon: const Icon(Icons.play_arrow),
              label: const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Text('자동매매 런타임 시작'),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _busy || !_status.requested
                  ? null
                  : () => _runAction(MonitoringBridge.stopMonitoring),
              icon: const Icon(Icons.stop),
              label: const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Text('런타임 중지'),
              ),
            ),
            const SizedBox(height: 10),
            TextButton.icon(
              onPressed: _busy || !_status.running
                  ? null
                  : () => _runAction(MonitoringBridge.sendTestListingAlert),
              icon: const Icon(Icons.notification_add_outlined),
              label: const Padding(
                padding: EdgeInsets.symmetric(vertical: 10),
                child: Text('테스트 신규상장 알림'),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              '1차 APK는 공지 감지와 수면모드 생존성을 검증합니다. 실제 주문 API는 호출하지 않습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(int epochMillis) {
    if (epochMillis <= 0) return '-';
    final value = DateTime.fromMillisecondsSinceEpoch(epochMillis).toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${value.year}-${two(value.month)}-${two(value.day)} '
        '${two(value.hour)}:${two(value.minute)}:${two(value.second)}';
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.status, required this.statusColor});

  final MonitoringStatus status;
  final Color statusColor;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: statusColor, blurRadius: 12)],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    status.running
                        ? 'Monitoring active'
                        : status.requested
                        ? 'Service recovery pending'
                        : 'Runtime stopped',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Upbit announcement · S23 foreground runtime',
                    style: TextStyle(color: Color(0xFF94A3B8)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.children,
  });

  final String title;
  final IconData icon;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const Divider(height: 24),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({
    required this.label,
    required this.value,
    this.multiline = false,
  });

  final String label;
  final String value;
  final bool multiline;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: multiline
            ? CrossAxisAlignment.start
            : CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: 112,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF94A3B8)),
            ),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              maxLines: multiline ? 3 : 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.icon,
    required this.color,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final Color color;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Icon(icon, color: color),
            const SizedBox(width: 12),
            Expanded(child: Text(message)),
            if (actionLabel != null) ...[
              const SizedBox(width: 8),
              TextButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

extension on String {
  String ifBlank(String fallback) => trim().isEmpty ? fallback : this;
}
