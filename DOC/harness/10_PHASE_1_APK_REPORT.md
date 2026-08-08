# Phase 1 APK Implementation Report

## 결과

신규 Flutter 앱 `SRC/heart_beat_coin_scalper`의 Android release APK 생성에 성공했다.

```text
version       : 0.1.0+1
applicationId : com.heartbeatcoinscalper.heart_beat_coin_scalper
minSdk        : 21
targetSdk     : 35
APK           : SRC/heart_beat_coin_scalper/build/app/outputs/flutter-apk/app-release.apk
APK SHA-256   : D63B86D2E321AF6344C2E1ABE72B4AAF0BB93D74738C2F58BBDDB7A3C899A1C2
signing       : Android debug certificate (internal test only)
```

## 구현된 vertical slice

```text
Flutter dashboard
-> MethodChannel
-> Android NoticeMonitoringService
-> foreground notification
-> partial wake lock
-> 3초 Upbit public announcements polling
-> JSON contract 검증
-> latest notice baseline/dedupe
-> 신규 거래지원 분류
-> ticker 추출
-> alert notification
-> SharedPreferences runtime status
-> Flutter dashboard refresh
```

## 공지 원천

```text
https://pub-info.upbit.com/api/v1/announcements
  ?os=web&page=1&per_page=20&category=all
```

필수 contract:

```text
success == true
data.notices[]
id
uuid
title
category
listed_at
first_listed_at
```

첫 실행은 가장 높은 `id`를 baseline으로 저장하고 과거 공지를 신규 신호로 발생시키지 않는다. 이후 더 높은 `id`만 순서대로 처리한다.

신규 거래지원 1차 분류:

```text
category == 거래
AND title contains 신규 거래지원 OR 디지털 자산 추가
AND NOT title contains 거래지원 종료 OR 유의 종목
```

## Android runtime

- 사용자 조작으로 service 시작
- `foregroundServiceType=specialUse`
- 지속 foreground 알림
- `PARTIAL_WAKE_LOCK` 획득
- `START_STICKY` process restart 요청
- 명시적 중지 시 scheduler와 wake lock 해제
- 알림 권한과 battery optimization 상태를 Flutter UI에 표시
- battery optimization 제외 요청은 사용자 조작으로만 실행

## 앱 화면에서 확인 가능한 값

- service requested/running
- charging/battery level
- wake lock 상태
- polling interval
- 마지막 polling 성공 시각
- 연속 오류 횟수와 마지막 오류
- 최신 공지 id/title
- 신규 거래지원 누적 감지 수
- 최근 ticker와 `first_listed_at`

## 검증 결과

```text
flutter analyze                         PASS
dart test test/monitoring_status_test  PASS (2 tests)
flutter build apk --debug              PASS
flutter build apk --release            PASS
APK signature v1/v2 verification       PASS
Upbit live endpoint HTTP/contract       PASS
```

Windows 환경의 `flutter test`는 test suite가 시작되기 전에 `flutter_tester.exe`가 native exit code `0xC0000409`로 종료됐다. 테스트 대상이 순수 Dart model이므로 `package:test` runner로 분리해 통과시켰다. 앱 분석과 Android APK 컴파일에는 영향이 없었다.

## 아직 검증하지 못한 항목

현재 `adb devices -l`에 Android 기기가 표시되지 않아 다음은 미검증이다.

- S23 설치와 화면 렌더링
- notification permission 흐름
- foreground service 실제 시작
- wake lock 실제 유지
- 공지 endpoint의 S23 네트워크 접근
- screen off/Doze 15분·1시간·24시간·72시간 soak
- swipe-away/process kill 복구

## 현재 자동매매 경계

제품은 자동매매 앱이지만 이 APK는 runtime 1차 테스트다.

```text
Upbit notice monitoring : IMPLEMENTED
listing alert            : IMPLEMENTED
Binance market stream    : NOT IMPLEMENTED
MARKET BUY               : NOT IMPLEMENTED
fixed LIMIT SELL         : NOT IMPLEMENTED
```

실주문 API나 거래 secret은 포함하지 않았다.

## 다음 구현 단계

S23 15분/1시간 runtime smoke가 통과하면 다음 vertical slice로 진행한다.

1. 구조화된 event DB
2. Binance public symbol metadata와 WebSocket
3. Upbit ticker -> Binance symbol resolver
4. 공지 수신 시 T0 market capture
5. Android Keystore secret boundary
6. fake exchange의 `MARKET BUY -> fixed LIMIT SELL`
