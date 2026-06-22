# Market Data Quality and Decision Classification Worldview

## Purpose

이 문서는 `heart_beat_coin_scalper`가 시장 데이터와 전략 판단을 어떻게 검증하고 분류해야 하는지 정의한다.

핵심 분리는 다음이다.

```text
validation = 데이터와 실행 조건이 사용 가능한가
classification = 이 시장 상태가 거래할 만한 구조인가
```

유효한 가격 데이터가 들어왔다고 해서 거래해야 하는 것은 아니다.

## Market Evidence Rule

첫 입력 데이터는 판단 근거를 잃지 않아야 한다.

`PriceEvent` 또는 그에 준하는 입력은 최소한 다음 정보를 보존해야 한다.

- symbol
- price
- volume when available
- timestamp
- exchange
- source mode: demo / paper / live
- stream type: trade / ticker / kline / synthetic
- raw payload when useful
- receive time
- normalized time bucket
- validation status

가격 데이터 필드에는 생성된 요약, 내부 오류 메시지, fallback 문구가 시장 사실처럼 들어가면 안 된다.

## Data Trust Levels

### Exchange Live Stream

Binance WebSocket 등 거래소에서 직접 받은 실시간 데이터다.

신뢰도는 높지만 다음 위험이 있다.

- stream reconnect
- stale data
- duplicate event
- trade/ticker/kline 혼합
- timestamp drift
- symbol mismatch
- exchange outage

### Exchange REST / Account Data

주문 결과, 잔고, 체결 내역처럼 REST 응답으로 확인되는 데이터다.

실행·장부 정합성 판단에는 중요하지만, API key/secret 처리와 live order risk 때문에 보호영역이다.

### Paper Runtime Data

실시간 가격을 사용하되 주문은 모의 장부에만 반영하는 데이터다.

전략 검증에 유용하지만 실제 체결, 호가 공백, 주문 실패, partial fill을 완전히 대체하지 못한다.

### Demo Synthetic Data

의사 난수 또는 샘플 기반 가격 스트림이다.

런타임 흐름 검증에는 유용하지만 실제 시장 수익성을 증명하지 않는다.

### Manual or Backfill Data

수동으로 만든 샘플 또는 과거 데이터다.

테스트와 회귀 검증에는 유용하지만, 실시간 장애와 실행 비용을 별도로 고려해야 한다.

## Price and Candle Boundary

시스템은 다음 경계를 구분해야 한다.

```text
raw price event
-> normalized price event
-> current candle
-> closed candle
-> market structure input
```

전략 판단은 닫힌 캔들 기준이어야 한다.

진행 중 캔들을 확정 신호처럼 사용하면 안 된다.

## Data Availability Gate

전략 판단에는 충분한 데이터가 필요하다.

Acceptable:

- 유효한 price
- 정상 timestamp
- symbol 일치
- candle interval 일치
- 닫힌 캔들 존재
- 최소 캔들 개수 충족
- volume 정보 또는 volume 없음에 대한 명시적 처리
- stream type 중복 정책 확인

Not acceptable:

- price <= 0
- timestamp 없음
- symbol mismatch
- stale WebSocket
- 중복 event가 누적 거래량을 왜곡
- 진행 중 캔들만 있음
- 내부 오류 메시지를 price/body처럼 사용
- demo와 live 상태 파일 혼합
- 거래소 주문 필터 미검증 상태의 live order

## Duplicate and Mixed Stream Policy

Binance WebSocket은 trade, ticker, kline 이벤트를 함께 다룰 수 있다.

중복 정책이 없으면 같은 시장 움직임을 여러 번 세거나, 캔들 volume이 왜곡될 수 있다.

Duplicate types:

- same event id
- same timestamp + same price
- same kline close repeated
- trade and ticker duplicate price signal
- reconnect replay
- synthetic demo repeated tick
- same closed candle processed twice

Rule:

```text
same raw event repeat = noise
same closed candle processed twice = bug
same structure confirmed across candles = signal
different streams conflict = review
```

## Classification Principle

시장은 다음처럼 분류한다.

- `NO_TRADE`: 판단할 이유가 약하거나 데이터가 부족한 상태
- `DEAD`: 구조적으로 죽은 흐름
- `FALLING`: 하락 진행 또는 저점 이탈 위험
- `ACCUMULATION`: 매집 가능성은 있으나 진입 확정 전
- `HEARTBEAT`: 제한 진입 검토 가능
- `STRONG_HEARTBEAT`: 더 강한 구조적 박동

거래 가능성은 분류명만으로 결정하지 않는다.

진입은 최소한 다음을 함께 통과해야 한다.

- 확인 신호 수
- 금지 조건 없음
- cooldown 아님
- 주문 가드 통과
- 모드 안전성 확인
- 손실 제한 조건 존재

## Strategy Archetype Classification

전략 판단 데이터는 먼저 전략 타입을 구분해야 한다.

### Tracking-First Signal

현재 코드의 기본 신호다.

조건:

- 닫힌 캔들 기준이다
- 최근 저점/고점 구조가 갱신된다
- 이동평균 회복/이탈이 판단에 들어간다
- 매수/매도 거래량 흐름이 판단에 들어간다
- 지지/저항은 고정 박스가 아니라 구조 반응으로 사용된다
- `market_state`와 `reasons`가 함께 기록된다

결론:

```text
strategy_archetype = tracking-first
```

### Box-First Signal

현재 기본 구현으로 단정하지 않는다.

조건:

- box low/high 또는 range low/high가 명시적으로 계산된다
- 하단권 진입과 상단권 청산이 primary rule이다
- 박스 이탈 또는 박스 붕괴가 핵심 invalidation이다
- 시장 상태 추적보다 range boundary가 우선한다

결론:

```text
strategy_archetype = box-first
```

### Hybrid Caution

현재 전략은 지지/저항과 최근 구조를 사용하므로 박스 참조처럼 보일 수 있다. 하지만 고정 박스를 먼저 깔고 매매하지 않으므로 `box-first`가 아니라 다음으로 기록한다.

```text
strategy_archetype = tracking-first
box_reference = structural_support_resistance
```

하네스와 테스트는 이 구분을 보존해야 한다. 박스형 실험을 추가하려면 기존 추적형 테스트를 기준선으로 유지하고, 별도 테스트 파일 또는 별도 strategy module로 분리한다.

## Entry Block Principle

다음 조건은 진입 차단 사유다.

- 충분한 캔들 데이터 부족
- 직전 저점 이탈
- 고점이 계속 낮아지는 구조
- 단기 이동평균 아래의 좁은 횡보
- 매도 거래량 급증
- 저항 부근 강한 거절
- BTC dumping 컨텍스트
- 스프레드 과다
- 평균 거래량 부족
- 신규 상장/첫 거래일
- 뉴스/내러티브 추격
- 단기 과열
- mode/order guard 불명확
- 거래소 주문 필터 미검증

차단 사유는 숨기지 말고 `strategy.log` 또는 decision record에 남긴다.

## Exit Classification Principle

청산은 hard exit와 take profit을 구분한다.

Hard exit는 생존 조건이다.

- BTC dumping
- 진입 구조 붕괴
- 직전 저점 이탈
- 단기 MA 이탈
- 매도 거래량 급증
- 새 고점 실패
- 저항 거절

Take profit은 수익 보호 조건이다.

- 저항 터치
- 단기 과열
- 윗꼬리 증가
- 매수 거래량 감소
- 새 고점 실패

hard exit를 약화하는 변경은 `GUARDED_FIX` 이상이며, live 영향이 있으면 `PROTECTED_CHANGE`다.

## Quality Trigger Cards

### TRIGGER CARD: Invalid Price Event

Condition: price가 0 이하, NaN, None, symbol mismatch, timestamp missing 또는 stale 상태다.

Action: 해당 event를 전략 입력에서 제외하고 로그에 validation reason을 남긴다.

Do not touch:

- strategy threshold
- live order path
- API key/secret

Verify:

- invalid event가 candle에 들어가지 않는다
- 런타임이 조용히 fake success를 만들지 않는다

### TRIGGER CARD: Closed Candle Boundary Violation

Condition: 진행 중 캔들로 진입/청산 판단을 실행한다.

Action: strategy decision을 막고 `closed candle required`로 기록한다.

Do not touch:

- Binance REST order
- Ledger update

Verify:

- `CandleAggregator.update()`가 closed candle 반환 시에만 strategy를 호출한다

### TRIGGER CARD: Mixed Stream Duplication

Condition: trade/ticker/kline 혼합으로 같은 움직임이 중복 집계될 수 있다.

Action: stream policy를 명시하거나 review 상태로 둔다.

Do not touch:

- strategy thresholds
- order size
- live order config

Verify:

- 같은 closed candle이 두 번 처리되지 않는다

### TRIGGER CARD: Insufficient Candle History

Condition: 시장 구조 분류에 필요한 캔들 수가 부족하다.

Action: `NO_TRADE` 또는 `HOLD`로 유지하고 이유를 기록한다.

Do not touch:

- live order
- ledger

Verify:

- 부족한 데이터로 `BUY`가 나오지 않는다

### TRIGGER CARD: Narrative Chase

Condition: 뉴스, 커뮤니티, 신규 상장, 급등률만으로 진입하려는 변경이다.

Action: 시장 구조 신호와 order guard를 요구한다.

Do not touch:

- market order path
- API credentials

Verify:

- narrative-only input은 `BUY`를 만들지 않는다

### TRIGGER CARD: Live Order Boundary

Condition: `live_order_enabled=true`, API key/secret 존재, REST client 변경, 실제 주문 전송 가능 경로가 보인다.

Action: `PROTECTED_CHANGE`로 격상하고 명시적 승인 없이는 수정·실행하지 않는다.

Do not touch:

- `exchanges/binance/rest.py`
- `config.yaml` secrets
- live order payload

Verify:

- dry-run/paper 경로와 live 경로가 분리되어 있다

### TRIGGER CARD: Secret Contamination

Condition: API key/secret/token이 문서, 로그, 테스트, 커밋 산출물에 들어갈 위험이 있다.

Action: 즉시 중단하고 redaction 또는 env 분리 후보를 보고한다.

Do not touch:

- 외부 API 호출
- live 주문

Verify:

- 산출물에 raw secret이 없다

### TRIGGER CARD: State Mode Mismatch

Condition: `state.json`이 어떤 실행 모드의 상태인지 확인할 수 없거나 demo/live 상태가 섞일 수 있다.

Action: 복구 전 review 또는 모드 태깅 후보를 만든다.

Do not touch:

- live order execution
- destructive state rewrite

Verify:

- 상태 파일을 덮어쓰기 전에 모드/심볼/거래소를 확인한다

## Decision Candidate Readiness

전략 판단이 주문 의도로 올라가려면 다음이 있어야 한다.

- valid symbol
- valid mode
- closed candle
- enough candle history
- market state
- entry/exit decision
- reasons
- score or confirmation count
- block reasons if any
- cooldown state
- cash budget or position qty
- fee/slippage assumptions
- order guard result
- ledger impact preview

## LLM / AI Advisory Policy

LLM은 전략 판단의 최종 권한자가 아니다.

가능한 역할:

- 로그 요약
- 실패 계층 분류 보조
- 문서 정리
- 테스트 후보 생성
- 리포트 해석 보조

금지:

- API key/secret 처리
- 실주문 여부 결정
- 손절 조건 약화 결정
- 공식 거래소 주문 필터 추정
- 수익률 보장
- 백테스트 없이 live 파라미터 추천

## Success Criteria

데이터 품질과 분류 체계가 작동하면 다음이 가능하다.

- 잘못된 가격 이벤트가 캔들에 들어가지 않는다
- 닫힌 캔들 기준 판단이 유지된다
- 같은 캔들이 두 번 처리되지 않는다
- 부족한 데이터로 매수하지 않는다
- 금지 조건은 명시적으로 남는다
- live 주문 경계는 항상 보호된다
- secret이 산출물에 노출되지 않는다
- demo/paper/live 결과가 구분된다
- 손실 이벤트와 차단 이벤트가 수익 이벤트만큼 추적된다
