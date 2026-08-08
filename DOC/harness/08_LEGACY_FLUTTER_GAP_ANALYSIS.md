# Legacy Flutter Gap Analysis

## 목적

이 문서는 `SRC/crypto_scalper_app_legacy`를 정적 검토해, 이전 Flutter 앱에서 해결되지 않은 부분을 신규 앱이 반복하지 않도록 만드는 migration 기준이다.

레거시 코드를 비난하거나 수리하기 위한 문서가 아니다. 레거시는 그대로 보존하고, 필요한 개념만 테스트와 함께 신규 구조로 다시 구현한다.

검토일: 2026-08-08

## 요약

이전 앱은 UI, 거래 루프, 개인 API, 로그, 전략 실험이 한 앱에 빠르게 결합되었다. README에는 background 독립 실행과 장기적인 foreground service 전환이 제안되어 있지만, 실제 Android manifest에는 foreground service가 선언되어 있지 않다.

현재 소스는 일부 구현 세대가 합쳐진 상태라 정적 코드 기준으로도 일관된 build/runtime 계약을 제공하지 못한다. 신규 앱은 이 코드를 기반으로 덧대지 않고 새 skeleton에서 자동매매 vertical slice를 다시 구현한다.

## 확인된 한계

### 1. UI lifecycle과 runtime lifecycle이 분리되지 않음

근거:

- `dashboard_screen.dart`가 `AutoTradeService`를 직접 생성한다.
- dashboard의 `dispose()`가 `autoTrader.dispose()`를 호출한다.
- `AutoTradeService`는 Dart `Timer`와 in-process `StreamController`로만 실행된다.
- Android manifest에는 foreground service 선언과 관련 권한이 없다.

영향:

- 화면 widget이 사라지거나 프로세스가 정리되면 감시 루프의 생존을 보장할 수 없다.
- 앱이 열린 상태의 10분 테스트는 화면 off 24시간 운영의 증거가 아니다.

신규 수용 기준:

- UI는 service 상태를 구독할 뿐 service 수명을 소유하지 않는다.
- Android native service와 Dart domain runtime 사이의 명시적 bridge를 둔다.
- 실제 S23 24h/72h soak test를 통과한다.

### 2. 컴파일 가능한 단일 상태가 아님

`auto_trade_service.dart`와 dashboard에는 서로 다른 구현 세대의 흔적이 함께 존재한다.

정적 검토에서 확인된 예:

- `isRunning` field와 getter가 중복되고 getter는 `_isRunning`을 참조한다.
- `start(String coin)`과 UI의 `autoTrader.start()` 호출 계약이 다르다.
- `_targetCoin`, `top10`, `c1h`, `price`, `trend30`, `trend10`, `_runCycle`, `_telegramService` 등 현재 파일 안에서 정의되지 않은 식별자가 사용된다.
- 거래 후보 선별, 기존 포지션 관리, 새 selector 흐름이 한 method에 혼합되어 있다.

영향:

- 레거시 일부 파일만 복사하면 어떤 동작이 기준인지 판단하기 어렵다.
- 긴급 패치가 다른 세대의 로직을 조용히 활성화할 수 있다.

신규 수용 기준:

- 새 Flutter skeleton은 처음부터 `flutter analyze`와 `flutter test`가 통과해야 한다.
- 하나의 vertical slice를 작게 연결하고 매 단계 build 가능한 상태를 유지한다.
- 상태와 의존성은 constructor/interface로 명시한다.

### 3. WebSocket 복구가 운영 수준이 아님

레거시 `coinone_ws.dart`는 오류나 종료 후 고정 5초 `Timer`로 다시 연결한다.

부족한 부분:

- exponential backoff와 jitter
- 중복 reconnect 방지
- close 이후 reconnect 취소
- 연결/구독 확인 상태
- ping/pong과 stale detection
- gap 기록과 backfill
- 재연결 횟수와 마지막 정상 메시지 영속화

신규 수용 기준:

- 연결 상태와 데이터 freshness를 별도로 관리한다.
- reconnect state machine과 취소 가능한 timer를 둔다.
- gap은 숨기지 않고 이벤트 품질에 반영한다.
- 공식 stream 수명 전에 proactive reconnect를 시험한다.

### 4. 이벤트 데이터 저장과 복구 계약이 없음

레거시는 `SharedPreferences`에 실행 여부와 마지막 코인 같은 UI 상태를 저장하고, 로그 파일을 append하는 수준이다.

부족한 부분:

- raw 공지 및 raw market payload
- stable event id와 dedupe
- state transition transaction
- parser/metric/schema version
- process death 이후 진행 이벤트 복구
- 데이터 gap과 시간 품질
- 구조화된 export

신규 수용 기준:

- `03_EVENT_DATA_CONTRACT.md`의 raw/normalized/derived/health 구조를 사용한다.
- 저장 성공을 상태 전이의 전제조건으로 둔다.
- 앱 update와 process death를 포함한 복구 테스트를 만든다.

### 5. Secret과 주문 경계가 너무 가까움

레거시에는 두 가지 `AppConfig` 접근이 공존한다.

- 소스 상수 placeholder 방식
- 실행 디렉터리의 `config.yaml` 또는 환경 변수 방식

동시에 UI와 자동 루프가 개인 잔액 및 주문 adapter를 직접 호출한다. PC에서는 가능한 설정 방식도 APK 안에서는 같은 의미로 동작하지 않는다.

영향:

- 모바일 secret 보관 정책이 불명확하다.
- 공지 수집과 주문 실행의 경계가 없어 불완전한 데이터가 바로 주문으로 이어질 수 있다.
- UI lifecycle 오류가 주문 경로에 직접 영향을 줄 수 있다.

신규 수용 기준:

- 공개 공지·시장 데이터 계층은 거래 secret을 참조하지 않는다.
- 주문 package는 별도 adapter와 `LIVE_GUARDED` 경계로 구현한다.
- 모바일 거래 secret은 Android Keystore로 보호하고, 조회·현물거래 최소권한만 사용한다.
- 출금 기능과 출금 권한은 추가하지 않는다.

### 6. 관측보다 거래 기능이 먼저 결합됨

레거시 문서와 코드의 중심은 전액/전량 주문, 상승 추종, Top-N selector다. 반면 실패 원인을 설명할 structured telemetry와 replay 계약은 약하다.

신규 수용 기준:

- 첫 화면의 핵심 action은 자동매수가 아니라 감시 시작/중지와 export다.
- 성공·실패·무반응 공지를 모두 저장한다.
- metric은 raw event에서 다시 계산할 수 있어야 한다.

### 7. 초 단위 latency 연구에 맞는 시간 모델이 없음

레거시는 분 단위 Timer와 일반 `DateTime` 중심이며, source event time, device receive time, processing time, monotonic elapsed time을 분리하지 않는다.

신규 수용 기준:

- `03_EVENT_DATA_CONTRACT.md`의 다중 timestamp 계약을 적용한다.
- T0의 의미와 정밀도를 함께 저장한다.
- clock jump, stream gap, parser delay를 event quality에 포함한다.

### 8. 테스트 범위가 모바일 운영 위험을 다루지 않음

레거시 test는 EMA, candle synth, rolling stats, order executor 등 로직 중심이다. Android service lifecycle, network switch, process death, DB migration에 대한 수용 기준은 확인되지 않는다.

신규 수용 기준:

- unit/integration/device test를 분리한다.
- foreground service, screen off, swipe-away, reboot, APK update를 S23에서 검증한다.
- 외부 API live probe는 결정적인 fixture test를 대체하지 않는다.

## 재사용 판단표

| 레거시 요소 | 판단 | 이유 |
|---|---|---|
| UI 색상·카드 아이디어 | 참고 가능 | runtime과 분리 가능 |
| 로그 화면 UX | 개념 재사용 | 구조화 저장소 위에서 다시 구현 필요 |
| 로컬 알림 초기화 | 참고 가능 | foreground 지속 알림과는 별개 |
| EMA/rolling utility | 테스트 후 선별 | Event Trading 핵심 범위는 아님 |
| Coinone private/order 코드 | 재사용 금지 | 신규 주문 계약·거래소·보안 경계와 불일치 |
| `AutoTradeService` | 재사용 금지 | lifecycle, 상태, 컴파일 계약 불명확 |
| `CoinoneWsClient` | 재사용 금지 | 복구·gap·health 계약 부족 |
| SharedPreferences 실행 복원 | 재설계 | boolean은 실제 service 상태가 아님 |
| config.yaml/env secret 방식 | 모바일에 이식 금지 | APK runtime 및 보안 모델과 불일치 |

## 신규 앱의 Definition of Better

신규 앱이 레거시보다 나아졌다고 말하려면 다음이 모두 참이어야 한다.

```text
build 가능한 단일 기준선
UI와 runtime lifecycle 분리
Android 정책에 맞는 foreground 운영
24h/72h 실기기 증거
구조화된 raw event와 replay
재시작 후 idempotent recovery
연결됨과 데이터 최신 상태의 분리
공개 데이터 계층과 주문 권한의 물리적 경계
MARKET BUY -> fill 확인 -> 고정가 LIMIT SELL 불변조건
오류와 데이터 gap의 가시화
```

이 기준 중 하나라도 빠지면 “Flutter로 다시 옮겼다”는 완료 조건을 충족하지 않는다.
