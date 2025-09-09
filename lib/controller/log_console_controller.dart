import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../utils/log_manager.dart';

enum LogMode { live, file }

class LogConsoleBoxController extends ChangeNotifier {
  LogConsoleBoxController._(this.mode, {this.filePath});

  factory LogConsoleBoxController.live() =>
      LogConsoleBoxController._(LogMode.live);

  factory LogConsoleBoxController.fromFile(String path) =>
      LogConsoleBoxController._(LogMode.file, filePath: path);

  final LogMode mode;
  final String? filePath;

  final List<String> _lines = [];
  List<String> get logs => List.unmodifiable(_lines);

  StreamSubscription<String>? _sub;

  static const int maxLines = 2000; // 필요 시 조정

  Future<void> attach() async {
    _sub?.cancel();
    if (mode == LogMode.live) {
      _sub = LogManager.instance.stream.listen((line) {
        _lines.add(line);
        // 오래된 로그 제거
        if (_lines.length > maxLines) {
          _lines.removeRange(0, _lines.length - maxLines);
        }
        notifyListeners();
      });
    } else {
      if (filePath == null) {
        _lines.clear();
        notifyListeners();
        return;
      }
      final file = File(filePath!);
      if (await file.exists()) {
        final content = await file.readAsLines();
        _lines
          ..clear()
          ..addAll(content);
      } else {
        _lines.clear();
      }
      // cap 적용
      if (_lines.length > maxLines) {
        _lines.removeRange(0, _lines.length - maxLines);
      }
      notifyListeners();
    }
  }

  Future<void> reloadFile() async {
    if (mode != LogMode.file || filePath == null) return;
    final file = File(filePath!);
    if (await file.exists()) {
      final content = await file.readAsLines();
      _lines
        ..clear()
        ..addAll(content);
      notifyListeners();
    }
  }

  void clear() {
    _lines.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
