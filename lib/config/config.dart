// filepath: lib/config/config.dart

import 'dart:io';

import 'package:yaml/yaml.dart';

/// AppConfig loads configuration from a `config.yaml` file or
/// environment variables.
///
/// Environment variables take precedence over the YAML file.
class AppConfig {
  AppConfig._internal();

  static final AppConfig _instance = AppConfig._internal();

  /// Returns the singleton instance of [AppConfig].
  factory AppConfig() => _instance;

  late final Map<String, dynamic> _yaml = _loadYaml();

  Map<String, dynamic> _loadYaml() {
    final file = File('config.yaml');
    if (file.existsSync()) {
      final yamlMap = loadYaml(file.readAsStringSync()) as YamlMap;
      return Map<String, dynamic>.from(yamlMap);
    }
    return {};
  }

  String get apiKey => _getString('API_KEY', 'apiKey');

  String get apiSecret => _getString('API_SECRET', 'apiSecret');

  String get baseUrl => _getString('BASE_URL', 'baseUrl');

  String _getString(String envKey, String yamlKey) {
    return Platform.environment[envKey] ?? _yaml[yamlKey] ?? '';
  }
}

