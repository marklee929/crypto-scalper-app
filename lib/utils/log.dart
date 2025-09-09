export 'package:logger/logger.dart' show Level;

import 'package:logger/logger.dart';
import 'log_manager.dart';

class _LogToManagerOutput extends LogOutput {
  @override
  void output(OutputEvent event) {
    for (final line in event.lines) {
      // 파일/브로드캐스트로 전달 (UI에서 다시 로깅 금지)
      LogManager.instance.log(line);
    }
  }
}

final LogOutput fileLogOutput = _LogToManagerOutput();

final Logger log = Logger(
  filter: ProductionFilter(),
  printer: PrettyPrinter(
    methodCount: 0,
    errorMethodCount: 5,
    lineLength: 120,
    colors: false, // 파일 저장 시 ANSI 색 제거
    printTime: true,
    noBoxingByDefault: true, // ┌/└ 박스 라인 제거
  ),
  output: MultiOutput([
    ConsoleOutput(), // IDE/Logcat
    fileLogOutput, // 파일/브로드캐스트(LogManager)
  ]),
);
