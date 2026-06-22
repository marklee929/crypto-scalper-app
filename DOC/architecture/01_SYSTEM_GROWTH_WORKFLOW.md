# Strategy Growth Workflow and Correction Loop

## Purpose

이 문서는 `heart_beat_coin_scalper`가 아이디어, 시장 데이터, 전략 판단, 주문 실행, 장부 기록, 피드백을 거쳐 어떻게 더 안전하고 반복 가능한 스캘핑 시스템으로 성장해야 하는지 정의한다.

목표는 “더 자주 진입”이 아니라 “잘못된 진입을 줄이고, 유효한 박동을 더 안정적으로 잡는 것”이다.

세부 데이터 품질과 신호 분류 규칙은 `02_DATA_SOURCE_AND_QUALITY.md`가 담당한다.

## Core Lifecycle

현재 프로젝트의 핵심 생명주기는 다음이다.

```text
market hypothesis
-> config / mode selection
-> price event ingestion
-> candle aggregation
-> closed candle confirmation
-> market structure classification
-> strategy decision
-> order intent
-> order guard
-> execution or skip
-> ledger update
-> state snapshot
-> strategy/trade/report logs
-> review
-> strategy improvement
```

수집은 목표가 아니다. 목표는 손실 제한이 가능한 반복 매매 판단을 만들고, 그 판단이 실제로 유효했는지 검증하는 것이다.

## Strategy Archetype Gate

전략 개선이나 버그 수정 전에 먼저 현재 작업이 박스형인지 추적형인지 구분한다.

현재 기본 경로는 추적형이다.

```text
추적형 현재 경로:
raw price event
-> current candle update
-> closed candle confirmation
-> rolling market structure memory
-> strategy decision
-> order intent or block
-> ledger/state/log feedback
```

박스형 작업은 별도 전략으로 다룬다.

```text
박스형 후보 경로:
range discovery
-> box low/high definition
-> box validity score
-> lower-band entry / upper-band exit
-> range break invalidation
```

지지/저항을 본다고 해서 자동으로 박스형이 되는 것은 아니다. 현재 코드는 지지/저항을 구조 추적의 입력으로 쓰는 것이며, 고정 박스 매매 엔진으로 동작한다고 단정하지 않는다.

작업 분류 규칙:

- `market_structure` 상태 갱신, `HeartbeatStrategy` 상태 머신, closed candle 판단은 추적형 작업이다.
- range low/high를 명시적으로 정의하고 그 구간 안에서 진입/청산하는 새 로직은 박스형 작업이다.
- 박스형 후보를 추가할 때는 기존 추적형 로직의 hard exit, confirmation, cooldown을 약화하지 않는다.
- 리포트에는 `strategy_archetype: tracking-first` 또는 `strategy_archetype: box-first`를 남긴다.


## Market Hypothesis Before Code Change

전략이나 파라미터를 바꾸기 전에 먼저 물어야 한다.

- 어떤 시장 구조를 잡으려는가?
- 진입 이유와 무효화 조건은 무엇인가?
- 이 변경이 손실을 줄이는가, 단순히 진입을 늘리는가?
- demo/paper/live 중 어디에서 검증할 것인가?
- 기존 테스트가 보장하던 기준선을 깨지 않는가?
- 수수료, 슬리피지, 최소 주문금액, 거래소 필터를 고려했는가?

답이 없으면 구현이 아니라 `READ_ONLY_AUDIT` 또는 `DOC_ONLY`로 멈춘다.

## Workflow Stages

### 1. Market Hypothesis

시장 아이디어를 정의한다.

예:

- 저점이 유지되면서 매도 거래량이 줄어드는 매집 구간
- 단기 MA 회복 후 저항을 돌파하고 유지하는 heartbeat
- 저항 부근 거절과 매도량 급증으로 인한 청산
- BTC dumping 컨텍스트에서 알트 진입 차단

Output: `hypothesis candidate`.

### 2. Configuration and Mode Selection

실행 모드와 설정을 확정한다.

Output: `runtime context`.

필수 구분:

- `demo`: 가상 가격 스트림
- `paper`: 실시간 또는 저장 데이터 기반 모의 장부
- `live`: 실계좌 주문 가능 경로

현재 코드에는 `demo`와 `live`가 중심이며, 새 하네스에서는 `paper`를 독립 모드로 분리하는 것이 우선 후보다.

### 3. Price Event Ingestion

Binance WebSocket 또는 demo stream에서 가격 이벤트를 받는다.

Output: `PriceEvent`.

필수 보존 정보:

- symbol
- price
- volume when available
- timestamp
- source
- stream type: trade / ticker / kline / demo

### 4. Candle Aggregation

가격 이벤트를 OHLCV 캔들로 묶는다.

Output:

```text
current candle
closed candle?
```

전략 판단은 `closed candle`이 있을 때만 실행한다.

### 5. Market Structure Classification

닫힌 캔들 목록을 시장 구조 분석으로 보낸다.

Output:

- `NO_TRADE`
- `DEAD`
- `FALLING`
- `ACCUMULATION`
- `HEARTBEAT`
- `STRONG_HEARTBEAT`

분류는 구조, 거래량, 이동평균, 지지/저항 반응을 함께 본다.

### 6. Strategy Decision

`HeartbeatStrategy.on_candle()`이 상태 머신 기준으로 판단한다.

상태:

- `IDLE`
- `IN_POSITION`
- `COOLDOWN`

Output:

- `BUY`
- `SELL`
- `HOLD`
- `BUY_SKIPPED`
- decision reasons
- score / flags
- current state

### 7. Order Intent

전략 판단이 실제 주문 가능 후보로 변환된다.

Output:

```text
OrderIntent(side, symbol, qty?, cash_budget, mode)
```

`OrderIntent`는 곧바로 주문이 아니다. 주문 가드를 통과해야 한다.

### 8. Order Guard

주문 전 마지막 방어선이다.

확인:

- 실행 모드
- `live_order_enabled`
- REST client 존재 여부
- API key/secret 처리
- `min_trade_cash`
- 현금 잔고
- 수량 포맷
- 거래소 최소 주문/step size/min notional 후보
- 중복 주문 위험
- cooldown 상태
- 장애/무데이터 상태

Output:

- `allowed`
- `blocked`
- `skipped`
- `requires_review`

### 9. Execution or Skip

`paper` 계층 장부에 반영하거나, live 주문 설정이 명시적으로 열렸을 때만 Binance REST 주문을 보낸다.

Output:

- `ExecutionResult`
- `SkipResult`
- external order id if live
- error details if failed

### 10. Ledger, State, Logs

결과를 장부와 상태 파일, 로그로 남긴다.

Output:

- `LedgerSnapshot`
- `state.json`
- `trades.log`
- `strategy.log`
- `hourly_report.log`

### 11. Review and Improvement

거래 결과를 보고 다음을 판단한다.

- 진입이 너무 많았는가
- 손절이 너무 늦었는가
- 과열 진입이 있었는가
- WebSocket 이벤트 중복이 신호를 왜곡했는가
- 수수료/슬리피지가 기대수익을 먹었는가
- 상태 복구가 올바르게 되었는가
- 테스트가 현재 위험을 충분히 막는가

## Correction Loop Before Patching

잘못된 결과가 나오면 바로 한 줄 패치하지 않는다.

먼저 실패한 생명주기 단계를 분류한다.

```text
config / mode selection
-> price event ingestion
-> candle aggregation
-> market structure classification
-> strategy decision
-> order guard
-> execution
-> ledger update
-> state snapshot
-> logging/reporting
-> tests
```

가장 이른 실패 계층을 고친다.

예:

- live 주문이 원치 않게 열릴 위험이면 `Order Guard`보다 먼저 `config / mode selection`을 본다.
- 캔들이 이상하면 전략 파라미터보다 `Price Event`와 `Candle Aggregation`을 본다.
- 손실 청산이 늦으면 매수 조건보다 `should_exit()`와 hard exit를 먼저 본다.
- 장부가 실제 주문과 다르면 전략이 아니라 `ExecutionResult -> Ledger` 순서를 본다.
- 로그에 이유가 없으면 수익률 계산보다 `StrategyDecision` 기록을 먼저 본다.

## Workflow Trigger Points

다음 조건에서는 stop, downgrade, review, 또는 paper-only로 전환한다.

- 실행 모드가 불명확하다
- 기본 실행이 `live`로 향한다
- `live_order_enabled=true`와 API key/secret이 동시에 존재한다
- API key/secret이 문서, 로그, 테스트에 노출될 위험이 있다
- WebSocket 데이터가 오래되었거나 중복 정책이 없다
- 캔들 수가 부족하다
- 가격/거래량/timestamp가 비정상이다
- 전략 판단이 닫힌 캔들이 아닌 진행 중 캔들에 의존한다
- 최소 주문금액 또는 거래소 주문 필터 검증이 불충분하다
- 상태 복구 파일이 실행 모드와 맞지 않는다
- 실주문 관련 파일이 보호 승인 없이 변경된다

## Representative Signal Rule

같은 가격 이벤트나 같은 캔들이 반복되어도 의미가 다르다.

```text
동일 이벤트 중복 = 보통 noise
같은 구조가 여러 캔들에서 유지 = signal
서로 다른 stream이 같은 가격대를 확인 = possible signal
갑작스러운 stream 불일치 = review
```

중복 데이터는 무조건 삭제하지 말고, 전략 입력에 들어가기 전 중복인지 구조 확인 신호인지 분류한다.

## Feedback and Knowledge Improvement

성장 루프는 점진적으로 다음을 만들어야 한다.

- 안전한 기본 실행 모드
- paper/live 분리
- 실행별 산출물 디렉터리
- 재현 가능한 거래 이벤트 모델
- WebSocket stream 중복 정책
- 거래소 주문 필터 검증
- 상태 복구 모드 태깅
- 손실 이벤트 중심 리포트
- 파라미터 변경 전후 비교 리포트
- Binance 외 거래소 확장 어댑터 규칙

## Success Criteria

워크플로우가 건강하면 다음이 가능하다.

- 잘못된 매매 결과가 나왔을 때 실패 계층을 찾을 수 있다
- 전략 변경이 임의 감이 아니라 가설과 검증으로 남는다
- live 주문은 항상 별도 보호 경계를 통과한다
- demo/paper/live 결과물이 섞이지 않는다
- 로그가 수익뿐 아니라 스킵, 차단, 손실, 오류를 모두 남긴다
- 테스트가 현재 동작의 기준선 역할을 한다
- 반복 개선이 손실 축소와 재현성 강화로 이어진다
