# Work Area Registry

## 위험도

| 등급 | 의미 |
|---|---|
| LOW | 문서, 순수 모델, fixture 중심 |
| MEDIUM | 네트워크, 저장소, lifecycle에 영향 |
| HIGH | Android 장기 실행, 데이터 migration, 배포 설정 |
| PROTECTED | secret, 계정, 실제 주문, 데이터 삭제 |

## 활성 작업 영역

### `PRODUCT_HARNESS` — LOW

- 소유: `DOC/harness`
- 역할: 제품 방향, 범위, 규칙, 로드맵
- 완료: 문서 링크와 충돌 여부 확인

### `FLUTTER_APP_SHELL` — MEDIUM

- 소유 예정: 신규 Flutter 앱의 `lib/app`, 화면, navigation
- 역할: 상태 대시보드, 이벤트 목록, 설정, export
- 제한: domain/network 로직을 widget 안에 구현하지 않음

### `ANDROID_MONITORING_SERVICE` — HIGH

- 소유 예정: 신규 Flutter 앱의 `android` native service와 platform bridge
- 역할: foreground notification, lifecycle, 종료/복구 신호
- 필수 검증: 실제 S23 24h/72h soak

### `NOTICE_SOURCE_UPBIT` — MEDIUM-HIGH

- 역할: `pub-info.upbit.com/api/v1/announcements` polling, raw 저장, cursor
- 계약: `id`, `uuid`, `title`, `category`, `listed_at`, `first_listed_at`
- 위험: 공개 JSON schema 변경, rate limit, 일시 차단
- 제한: contract mismatch 시 신규 매수 차단

### `NOTICE_CLASSIFIER` — MEDIUM

- 역할: 신규 거래지원 공지 분류, asset 추출
- 필수 검증: 저장된 실제/변형 fixture, false positive/negative

### `SYMBOL_RESOLVER` — MEDIUM

- 역할: canonical asset과 Binance symbol 매핑
- 필수 검증: alias, migration, ticker collision, no-match

### `BINANCE_MARKET_DATA` — MEDIUM-HIGH

- 역할: public metadata, WebSocket trade, REST backfill
- 위험: reconnect gap, stream stale, server timestamp 차이
- 제한: 시장 데이터 adapter에서 주문을 직접 실행하지 않음

### `ACCOUNT_AND_EXECUTION` — PROTECTED

- 역할: balance/open order 조회, MARKET BUY, LIMIT SELL, fill 확인
- 위험: 실제 자산, unknown execution status, 부분 체결
- 불변조건: intent-first, fill-based target, fixed sell price, reconciliation
- 금지: 출금 API, 출금 권한, 중복 매수

### `ENTRY_GUARD` — HIGH

- 역할: 공지·시간·가격·spread·slippage·risk·position 조건 판정
- 완료: 모든 skip에 안정적인 reason code 기록
- 제한: 데이터가 stale/unknown이면 fail-closed

### `EVENT_ENGINE` — MEDIUM

- 역할: 상태 머신, T0, capture schedule, cooldown
- 필수 검증: 결정적 clock을 사용하는 replay test

### `LOCAL_STORAGE` — HIGH

- 역할: raw/normalized/derived/health 영속 저장
- 위험: migration, 용량, flash write, 부분 기록
- 제한: 삭제 migration은 PROTECTED로 승격

### `DATA_EXPORT` — MEDIUM

- 역할: JSONL/CSV export와 schema metadata
- 위험: secret 또는 개인정보 포함

### `RUNTIME_HEALTH` — HIGH

- 역할: freshness, heartbeat, reconnect, battery/network 상태
- 완료: silent failure를 화면·알림·저장으로 드러냄

### `APK_DELIVERY` — HIGH

- 역할: build variant, signing, version, adb install, S23 smoke
- 제한: release key를 저장소에 추가하지 않음

### `PAPER_EXECUTION` — HIGH

- live와 같은 rule engine을 fake exchange로 검증
- 실제 주문 없음

### `LIVE_GUARDED_EXECUTION` — PROTECTED / ACTIVE SCOPE

- 첫 제품의 핵심 범위
- 사용자가 시작한 세션 안에서 조건 충족 시 추가 확인 없이 자동 주문
- 시장가 매수 후 실제 fill 기준 고정가 지정가 매도
- 주문 금액, 계산식, 손실 제한 변경은 영향과 검증 결과를 보고

### `LEGACY_REFERENCE` — READ_ONLY

- 소유: `SRC/*_legacy`, `DOC/legacy`
- 역할: 과거 아이디어, 테스트, 실패 사례 참고
- 제한: 신규 runtime dependency로 연결하지 않음

## 다중 영역 변경 규칙

한 작업이 세 영역 이상을 동시에 변경하면 먼저 경계를 나누거나 execution card를 작성한다.

```text
Task
Areas
Reason for cross-area change
Risk
Rollback
Verification per area
```

`NOTICE_SOURCE_UPBIT + EVENT_ENGINE + LOCAL_STORAGE + ANDROID_MONITORING_SERVICE`를 한 번에 구현하지 않는다. 작은 vertical slice로 연결한다.

## 우선 감사 대상

1. S23의 실제 Android/One UI 버전과 foreground service 제한
2. 업비트 공개 공지 endpoint의 polling 주기와 schema 변화 감지
3. Binance에서 T0 이전 초단위 trade backfill 가능 범위
4. 모바일 장기 기록의 DB 용량과 write 빈도
5. ticker collision과 토큰 migration 사례
6. 지정가 매도 미체결·부분 체결·재시작 reconciliation
