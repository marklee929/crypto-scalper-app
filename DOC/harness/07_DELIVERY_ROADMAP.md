# Delivery Roadmap

## 원칙

구현 순서는 화면 완성도가 아니라 가장 큰 불확실성을 먼저 제거하는 순서다.

## Phase 0 — Repository Baseline

목표:

- 신규 Flutter 앱의 디렉터리명과 package id 결정
- 레거시와 신규 코드 경계 확정
- Flutter/Android SDK 및 S23 연결 상태 확인
- debug APK 설치 경로 확보

산출물:

- 신규 앱 skeleton
- 환경 확인 보고서
- `flutter analyze`, 기본 test, debug APK 성공
- `08_LEGACY_FLUTTER_GAP_ANALYSIS.md`의 재사용 금지선 확인

## Phase 1 — S23 Runtime Spike

목표:

- 최소 foreground monitoring service
- heartbeat DB와 지속 알림
- 화면 off/network switch/process death 실험
- 24시간 및 72시간 soak 데이터 확보

이 단계에서 비즈니스 공지 파서를 만들지 않아도 된다.

중단 기준:

- 정책에 맞는 service 유형으로 목표 지속시간을 달성할 수 없음
- silent failure를 탐지할 수 없음
- 허용할 수 없는 배터리/데이터 사용량

## Phase 2 — Upbit Notice Integration

목표:

- 업비트 공개 announcements endpoint 연결
- raw response append 저장
- dedupe와 revision
- 신규 거래지원 fixture 수집

산출물:

- `first_listed_at`을 포함한 source contract와 확인일
- parser fixtures
- 원천 장애/구조 변경 테스트

## Phase 3 — Market and Account Integration

목표:

- Binance public symbol metadata
- symbol resolver
- 대상 trade WebSocket과 reconnect
- T0 이전 REST backfill 가능성 검증
- 최소권한 account/order adapter
- balance, open order, symbol filter, fill 조회

산출물:

- match/no-match/ambiguous 사례
- gap과 stale detection
- sample event capture

## Phase 4 — Auto-trading Vertical Slice

목표:

```text
공지 raw 수신
  -> 신규상장 분류
  -> symbol 매핑
  -> T0 확정
  -> 진입 조건 검증
  -> BUY intent
  -> MARKET BUY
  -> 실제 fill 확인
  -> 고정 목표 매도가 계산
  -> LIMIT SELL
  -> 주문 추적/metric/export
```

fake exchange에서 단일 이벤트를 end-to-end로 replay하고, 앱 재시작 후 같은 주문·복구 결과를 얻어야 한다.

## Phase 5 — S23 Guarded Live MVP

목표:

- S23 수면 상태 상시 자동매매
- 조건 충족 시 시장가 매수
- 실제 fill 기준 고정가 지정가 매도
- 최소 주문 예산, 단일 position, 일일 risk 한도
- 미체결 매도 주문과 재시작 reconciliation
- 모든 실행/skip/error 데이터 축적

이 단계의 산출물은 **조건부 자동매매가 가능한 APK와 감사 가능한 주문 dataset**이다.

## Phase 6 — Live Soak and Evidence Analysis

목표:

- latency bucket
- baseline별 수익률
- 최대 낙폭과 peak timing
- 거래량/유동성
- 감지 지연과 시장 선행 반응

결과:

```text
KEEP_RULES
TIGHTEN_GUARDS
PAUSE_NEW_ENTRIES
REJECT_STRATEGY
```

## Phase 7 — Strategy Improvement

- 원시 데이터 기반 replay와 paper 비교
- 현실적 지연, 수수료, 슬리피지 반영
- signal expiry와 진입 guard 조정
- 목표 매도가 변경은 새 strategy version으로 분리
- 변경 전후 live 결과 비교

## 현재 미결정 사항

| 항목 | 상태 | 결정 시점 |
|---|---|---|
| 신규 Flutter 앱 폴더명/package id | OPEN | Phase 0 |
| S23 Android/One UI 실제 버전 | MEASURE | Phase 0 |
| foreground service type | VALIDATE | Phase 1 |
| partial wake lock | REQUIRED | LIVE_GUARDED 세션, Phase 1 실기기 검증 |
| 부팅 후 자동 재개 | DEFER | Phase 1 결과 후 |
| 업비트 공지 원천 | CONFIRMED | 공개 announcements endpoint |
| polling 주기 | MEASURE | Phase 2 |
| local DB 라이브러리 | SPIKE | Phase 1~2 |
| 고빈도 데이터 보존기간 | MEASURE | Phase 5 |
| baseline price 정의 | DEFER | Phase 6 |
| 자동주문 | ACTIVE SCOPE | LIVE_GUARDED |
| 1회 시장가 매수 예산 | OPEN | Phase 4 이전 |
| 고정 목표 매도가 계산식 | OPEN | Phase 4 이전 |
| 지정가 장기 미체결 처리 | OPEN | Phase 4 이전 |
| 손절/비상청산 규칙 | OPEN | Phase 4 이전 |

## 다음 실행 작업

하네스 승인 후 첫 작업은 다음 하나다.

> **Phase 0: 로컬 Flutter/Android 개발환경과 연결된 S23 상태를 읽기 전용으로 점검하고, 신규 앱 skeleton의 이름·package id 후보와 생성 계획을 보고한다.**

이 작업에서는 아직 레거시 코드를 이식하거나 실주문을 보내지 않는다.
