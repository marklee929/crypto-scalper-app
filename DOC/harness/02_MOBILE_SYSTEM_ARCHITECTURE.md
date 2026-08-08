# Mobile System Architecture

## 시스템 경계

신규 시스템의 production runtime은 S23 한 대다.

```text
                       Samsung Galaxy S23
┌────────────────────────────────────────────────────────────┐
│ Flutter UI                                                 │
│  - 자동매매 세션/상태/주문/오류/내보내기                  │
│                 │ platform boundary                        │
│ Android monitoring service                                 │
│  - lifecycle / foreground notification / wake recovery     │
│                 │                                          │
│ Dart domain runtime                                        │
│  ├─ NoticeSource adapter                                   │
│  ├─ Notice classifier / symbol resolver                    │
│  ├─ MarketData adapter                                     │
│  ├─ Entry guard / trade rule engine                        │
│  ├─ Account & Execution adapter                            │
│  ├─ Event state machine                                    │
│  ├─ Local repository                                       │
│  └─ Health monitor                                         │
└───────────────┬──────────────────────┬─────────────────────┘
                │ HTTPS polling        │ WebSocket / REST
                ▼                      ▼
        Upbit public notice       Binance market/account/order
```

PC는 위 경로에 존재하지 않는다. 개발 중 ADB, 빌드, 로그 확인에만 사용한다.

## 계층별 책임

### Flutter UI

- 감시 시작/중지와 현재 상태 표시
- LIVE_GUARDED 세션 시작/중지, 1회 주문 예산과 위험 한도 설정
- 마지막 공지 확인, 마지막 시장 데이터, 마지막 저장 시각 표시
- 보유 position, 매수 체결가, 고정 목표 매도가, open order 표시
- 오류와 재연결 횟수 표시
- 이벤트 상세와 데이터 내보내기
- 세션 시작 후 조건을 통과한 공지는 추가 확인 없이 자동 주문한다.

### Android monitoring service

- 사용자가 앱 화면에서 자동매매 세션을 명시적으로 시작한다.
- 지속 알림을 표시하고 runtime 생명주기를 관리한다.
- Android 정책상 허용되는 foreground service 유형을 사용한다.
- 서비스 종료와 timeout을 Dart 계층에 상태 이벤트로 전달한다.
- 화면이 꺼진 수면 상태에서도 polling, WebSocket, 저장, 주문 상태 관리가 계속되어야 한다.
- process/기기 재시작 후에는 감시를 복구할 수 있지만, exchange reconciliation 완료 전 신규 매수를 금지한다.

### UpbitPublicNoticeSource

- 기준 URL: `https://pub-info.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all`
- token 없이 공개 공지 목록을 polling하고 raw response 수신 시각을 기록
- `data.notices[]`에서 `id`, `uuid`, `title`, `category`, `listed_at`, `first_listed_at` 수집
- source별 cursor/identifier 관리
- rate limit, timeout, retry/backoff 적용
- 파서와 HTTP 수집을 분리해 저장된 fixture로 재현 가능하게 한다.
- 응답의 `first_listed_at`을 원천이 제공한 최초 게시 시각으로 저장하고, 단말의 `notice_first_seen_at`도 별도로 저장한다.
- 2026-08-08 직접 호출에서 KMNO 공지 `id=6450`의 `first_listed_at`이 `2026-08-07T11:09:45+09:00`으로 확인됐다.
- 공개 endpoint라도 schema, 장애, 차단 가능성이 있으므로 fixture와 contract failure 처리를 둔다.

### Notice classifier and symbol resolver

- 신규 거래지원 공지만 분류
- 한글명, 영문명, ticker 후보를 분리 저장
- `KRW-ABC`와 `ABCUSDT` 같은 거래소별 표기를 canonical asset으로 매핑
- 동명이인, 토큰 migration, ticker collision은 자동 확정하지 않고 `AMBIGUOUS`로 기록

### MarketData adapter

- Binance 공개 market metadata를 캐시하고 주기적으로 갱신
- 이벤트 발생 시 대상 symbol의 실시간 trade stream을 연결
- 필요한 경우 공식 REST 데이터로 T0 이전 구간을 backfill
- 연결 단절, sequence gap, stale stream을 건강 상태로 보고
- 24시간 연결 수명, ping/pong, reconnect를 명시적으로 처리

### Entry guard and trade rule engine

신규 공지라고 해서 무조건 매수하지 않는다. 최소 조건:

```text
자동매매 세션 ACTIVE
공지 category/title이 신규 거래지원 규칙과 일치
first_listed_at 및 단말 수신 시각이 유효
이벤트 age가 최대 허용시간 이내
symbol이 하나로 확정되고 target market이 TRADING
market stream과 orderbook이 fresh
가격 상승률, spread, 예상 slippage가 한도 이내
주문 예산과 일일 risk 한도 이내
기존 position/open order 없음
DB와 exchange 상태 reconciliation 완료
```

하나라도 실패하면 주문 없이 `SKIPPED`와 reason code를 저장한다.

### Account and Execution adapter

- API key는 거래와 조회에 필요한 최소권한만 사용하며 출금 기능은 구현하지 않는다.
- 주문 전 balance, symbol filter, 최소 주문금액, tick/step size를 확인한다.
- 매수는 `MARKET`으로 제출한다.
- 매수 응답만 믿지 않고 최종 주문 상태와 실제 fills를 조회해 평균 체결가와 체결 수량을 확정한다.
- 매도가는 실제 평균 체결가, fee, 설정된 목표 수익률을 사용해 계산하고 exchange tick size로 보정한다.
- 계산이 끝난 하나의 고정 가격으로 전 체결 가능 수량을 `LIMIT SELL` 주문한다.
- 부분 체결, 거부, timeout, unknown execution status는 reconciliation 대상으로 전환한다.

### Event state machine

허용 상태는 다음과 같다.

```text
WATCHING
  -> NOTICE_SEEN
  -> PARSED
  -> SYMBOL_MATCHED | SKIPPED | AMBIGUOUS
  -> ENTRY_VALIDATING
  -> BUY_INTENT_SAVED
  -> BUY_SUBMITTED
  -> BUY_FILLED
  -> SELL_PRICE_FIXED
  -> SELL_INTENT_SAVED
  -> SELL_SUBMITTED
  -> EXITED
  -> COOLDOWN
  -> ARCHIVED

주문 상태 -> RECONCILIATION_REQUIRED
모든 상태 -> FAILED
```

상태 전이는 저장 성공 후 확정한다. 앱 화면 상태만 바꾸고 저장하지 않는 전이는 금지한다.

### Local repository

- 단말 로컬 데이터베이스를 production 기준 저장소로 사용한다.
- 구체 라이브러리(SQLite/Drift 등)는 기술 spike 후 결정한다.
- raw payload, normalized notice, market sample, lifecycle event, health sample을 분리한다.
- order intent, exchange order, fill, position, reconciliation event를 분리한다.
- 데이터는 JSONL/CSV로 내보낼 수 있어야 한다.
- DB가 기록 불가능하면 감시는 `DEGRADED` 또는 `FAILED`로 전환한다.

## 데이터 흐름

```text
poll response received
  -> raw payload append
  -> notice dedupe
  -> classification
  -> symbol resolution
  -> event T0 확정
  -> market live subscription + pre-event backfill
  -> entry guard
  -> market buy + fill confirmation
  -> fixed sell price calculation
  -> limit sell + order monitoring
  -> scheduled snapshots / derived metrics / reconciliation
  -> cooldown
  -> archive + export
```

## 네트워크 원칙

- 공지: 검증된 최소 주기의 HTTP polling
- 가격: 이벤트 대상 WebSocket 우선, REST는 metadata/backfill/fallback
- retry는 지수 backoff와 jitter를 사용하되 공지 polling SLA와 분리
- 무한 즉시 재시도 금지
- HTTP 성공과 유효 데이터 성공을 별도 지표로 기록

## 공식 근거와 확인 상태

확인일: 2026-08-08

- [Upbit 공개 공지 endpoint](https://pub-info.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all)를 공지 감지 기준 입력으로 사용한다.
- [Binance Spot WebSocket 문서](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)는 실시간 trade stream의 기준 문서다.
- API 세부 규칙은 구현 시작 시 다시 확인하고 확인일을 갱신한다.
