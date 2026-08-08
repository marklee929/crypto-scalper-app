# Heart Beat Coin Scalper — Android Runtime Test

S23에서 독립 실행하는 업비트 공지 반응 자동매매 앱의 1차 runtime prototype이다.

이번 버전 `0.1.0+1`은 실제 주문을 보내지 않는다. 자동매매의 필수 기반인 화면 off/수면 상태 공지 감시와 알림을 검증한다.

## 구현 범위

- Flutter 상태 대시보드
- Android native foreground service (`specialUse`)
- active session partial wake lock
- 업비트 공개 공지 endpoint 3초 polling
- 첫 실행 최신 공지 baseline 처리
- 신규 거래지원 공지 분류 및 ticker 추출
- foreground 상태 알림과 신규상장 고우선순위 알림
- process restart용 `START_STICKY`와 최소 상태 보존
- 배터리 최적화 제외 요청 화면
- 테스트 신규상장 알림

## 아직 미구현

- Binance WebSocket 및 symbol resolver
- Android Keystore 기반 거래 key 저장
- 시장가 매수와 고정가 지정가 매도
- 구조화된 로컬 DB와 주문 reconciliation
- 재부팅 후 자동 복구

## 빌드

```powershell
flutter pub get
flutter analyze
dart test
flutter build apk --release
```

APK:

```text
build/app/outputs/flutter-apk/app-release.apk
```

현재 release variant는 내부 테스트를 위해 Android debug key로 서명된다.

## S23 설치

S23에서 개발자 옵션과 USB 디버깅을 켜고 PC를 허용한 뒤:

```powershell
adb devices -l
adb install -r build/app/outputs/flutter-apk/app-release.apk
adb shell am start -n com.heartbeatcoinscalper.heart_beat_coin_scalper/.MainActivity
```

## 1차 실기기 확인

1. 알림 권한을 허용한다.
2. 배터리 최적화 제외를 허용한다.
3. `자동매매 런타임 시작`을 누른다.
4. `HEALTHY`, `Wake lock ACTIVE`, 최신 공지 ID와 제목을 확인한다.
5. `테스트 신규상장 알림`을 눌러 고우선순위 알림을 확인한다.
6. 화면을 끄고 15분 후 다시 열어 마지막 성공 시각과 오류 횟수를 확인한다.
7. 이후 1시간, 24시간, 72시간 순서로 soak test를 늘린다.
