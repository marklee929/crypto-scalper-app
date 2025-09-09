import 'package:flutter/material.dart';
import 'dart:async';
import '../controller/log_console_controller.dart';
import '../widgets/log_console_box.dart';
import '../utils/log_manager.dart';

class LogViewScreen extends StatefulWidget {
  const LogViewScreen({super.key});

  @override
  State<LogViewScreen> createState() => _LogViewScreenState();
}

class _LogViewScreenState extends State<LogViewScreen> {
  LogConsoleBoxController? _controller;

  @override
  void initState() {
    super.initState();
    _prepare();
  }

  Future<void> _prepare() async {
    final path = await LogManager.instance.todayLogPath();
    final c = LogConsoleBoxController.fromFile(path);
    await c.attach();
    if (!mounted) return;
    setState(() {
      _controller = c;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('로그 파일 보기')),
      body: _controller == null
          ? const Center(child: CircularProgressIndicator())
          : LogConsoleBox(
              isLive: false,
              controller: _controller!,
              onClose: null,
            ),
    );
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }
}
