import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import '../controller/log_console_controller.dart';
import '../utils/log.dart';

class LogConsoleBox extends StatefulWidget {
  final bool isLive;
  final VoidCallback? onClose;
  final LogConsoleBoxController controller;

  const LogConsoleBox({
    super.key,
    required this.isLive,
    this.onClose,
    required this.controller,
  });

  @override
  State<LogConsoleBox> createState() => _LogConsoleBoxState();
}

class _LogConsoleBoxState extends State<LogConsoleBox> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  List<String> _visibleLogs = [];
  List<int> _searchMatches = [];
  int _highlightIndex = 0;
  bool _searchMode = false;

  // 추가: 바닥 부착 상태
  bool _stickToBottom = true;
  static const _stickThreshold = 24.0;

  void _onLogUpdated() {
    if (!mounted) return;
    setState(() {
      _visibleLogs = List.from(widget.controller.logs);
      if (_searchMode) {
        _applySearchFilter();
      }
    });
    // 새 로그가 왔고 바닥에 붙어있으면 자동으로 맨 아래로
    if (_stickToBottom) {
      _scrollToBottom();
    }
  }

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onLogUpdated);
    _visibleLogs = List.from(widget.controller.logs);

    // 스크롤 위치에 따라 바닥 부착 여부 갱신
    _scrollController.addListener(() {
      if (!_scrollController.hasClients) return;
      final pos = _scrollController.position;
      final atBottom =
          (pos.maxScrollExtent - pos.pixels).abs() <= _stickThreshold;
      _stickToBottom = atBottom && !_searchMode;
    });
  }

  @override
  void didUpdateWidget(covariant LogConsoleBox oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_onLogUpdated);
      widget.controller.addListener(_onLogUpdated);
      _visibleLogs = List.from(widget.controller.logs);
      // 컨트롤러 교체 시 초기엔 바닥에 붙도록
      _stickToBottom = true;
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _onSearch(String keyword) {
    _searchMatches.clear();
    _highlightIndex = 0;

    if (keyword.trim().isEmpty) {
      setState(() {
        _searchMode = false;
        _visibleLogs = List.from(widget.controller.logs);
        _stickToBottom = true; // 검색 종료 시 다시 바닥 부착
      });
      _scrollToBottom();
      return;
    }

    for (int i = 0; i < widget.controller.logs.length; i++) {
      if (widget.controller.logs[i].toLowerCase().contains(
        keyword.toLowerCase(),
      )) {
        _searchMatches.add(i);
      }
    }

    if (_searchMatches.isNotEmpty) _jumpToSearchIndex(0);

    setState(() {
      _searchMode = true;
      _stickToBottom = false; // 검색 모드에선 부착 해제
    });
  }

  void _jumpToSearchIndex(int index) {
    _highlightIndex = index.clamp(0, _searchMatches.length - 1);
    final line = widget.controller.logs[_searchMatches[_highlightIndex]];
    setState(() {
      _visibleLogs = [line];
    });
  }

  void _nextMatch() {
    if (_searchMatches.isEmpty) return;
    _highlightIndex = (_highlightIndex + 1) % _searchMatches.length;
    _jumpToSearchIndex(_highlightIndex);
  }

  void _prevMatch() {
    if (_searchMatches.isEmpty) return;
    _highlightIndex =
        (_highlightIndex - 1 + _searchMatches.length) % _searchMatches.length;
    _jumpToSearchIndex(_highlightIndex);
  }

  // 검색 기능이 아직 없을 때를 위한 안전한 no-op
  void _applySearchFilter() {
    // intentionally no-op
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onLogUpdated);
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black,
      padding: const EdgeInsets.all(8),
      child: Column(
        children: [
          Row(
            children: [
              if (widget.onClose != null)
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white),
                  tooltip: "닫기",
                  onPressed: widget.onClose,
                ),
              Expanded(
                child: TextField(
                  controller: _searchController,
                  onChanged: _onSearch,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: "로그 검색...",
                    hintStyle: const TextStyle(color: Colors.white54),
                    filled: true,
                    fillColor: Colors.black26,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.white),
                tooltip: "이전 검색",
                onPressed: _prevMatch,
              ),
              IconButton(
                icon: const Icon(Icons.arrow_forward, color: Colors.white),
                tooltip: "다음 검색",
                onPressed: _nextMatch,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: _visibleLogs.length,
              itemBuilder: (_, index) => Text(
                _visibleLogs[index],
                style: const TextStyle(
                  fontFamily: 'Courier',
                  fontSize: 12,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
