import 'dart:async';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class LogManager {
  LogManager._();
  static final instance = LogManager._();

  final _controller = StreamController<String>.broadcast();
  Stream<String> get stream => _controller.stream;

  String? _todayPathCache;

  Future<String> _todayPath() async {
    if (_todayPathCache != null) return _todayPathCache!;
    final dir = await getApplicationDocumentsDirectory();
    final now = DateTime.now();
    final name =
        'trade_${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}.log';
    final path = '${dir.path}/$name';
    _todayPathCache = path;
    final file = File(path);
    if (!await file.exists()) {
      await file.create(recursive: true);
    }
    return path;
  }

  Future<void> log(String line) async {
    // 1) 실시간 브로드캐스트
    _controller.add(line);
    // 2) 파일에 안전하게 Append (IOSink 사용 안 함)
    final path = await _todayPath();
    final file = File(path);
    await file.writeAsString('$line\n', mode: FileMode.append, flush: false);
  }

  Future<String> todayLogPath() => _todayPath();

  Future<void> dispose() async {
    // _controller는 앱 라이프사이클 동안 유지. 필요 시 close 추가.
    // await _controller.close();
  }
}
