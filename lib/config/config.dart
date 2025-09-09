class AppConfig {
  // 🟣 API 키 (테스트용 - 실제 배포 시 분리 필수)
  static const String apiKey = 'd3236c11-82d1-4ca8-9a16-a87a402fa90c';
  static const String apiSecret = 'd402b85f-3a28-4193-b382-0a30e97e1fda';

  // 🟢 코인원 REST API URL
  static const String baseUrl = 'https://api.coinone.co.kr';

  // 🟡 기본 설정
  static const String defaultCoin = 'XRP';
  static const String quoteCurrency = 'KRW';

  // 🔵 자동매매 기본 전략
  static const String defaultStrategy = '상승 추종';
}
