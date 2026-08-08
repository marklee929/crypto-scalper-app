# Local Runtime Safety

## Purpose

이 문서는 `heart_beat_coin_scalper`를 로컬 PC에서 개발·실행할 때의 안전 규칙을 정의한다.

현재 프로젝트는 로컬 개발 환경에서 Binance WebSocket과 Binance REST 주문 경로까지 연결될 수 있다. 따라서 로컬 실행은 단순 테스트가 아니라 실제 외부 주문 위험을 가질 수 있다.

## Current Runtime Assumption

현재 런타임 가정:

```text
local PC
-> Python runtime
-> local config.yaml
-> local state/log files
-> optional PostgreSQL blackbox records
-> optional demo stream
-> Binance WebSocket
-> optional Binance REST market order
```

로컬에서 실행해도 외부 Binance 계정에 영향을 줄 수 있다.

현재 코드의 핵심 실행 경로는 아직 DB에 의존하지 않지만, 하네스 기준 DB 아키텍처는 PostgreSQL-first다.

PostgreSQL은 로컬 실행의 판단 엔진이 아니라 기록, 복기, asset tracking, reconciliation 계층이다. `DATABASE_URL`이 없더라도 demo와 기본 단위 테스트는 깨지지 않아야 한다. 반대로 live order 경로에서 DB 기록 실패를 조용히 성공처럼 숨기면 안 된다.

## Core Runtime Rule

문법이 맞다고 안전한 것이 아니다.

런타임 변경은 다음이 확인되어야 완료다.

- 실행 모드가 명확하다
- live 주문 가능성이 확인되었다
- API key/secret이 노출되지 않았다
- closed candle 기준 판단이 유지된다
- order guard가 유지된다
- state/log 경로가 의도한 곳이다
- 테스트 또는 smoke check가 실행되었다
- 보호영역이 우발적으로 변경되지 않았다

## Safe Execution Defaults

가능한 기본 실행은 다음 순서를 따른다.

```text
demo
-> paper
-> live data without order
-> live order with explicit approval
```

현재 코드 기본값이 `live`일 수 있으므로, 작업자는 실행 전에 항상 mode와 `live_order_enabled`를 확인한다.

## Local Server / Process Safety

이 프로젝트는 일반 웹 서버가 아니라 Python runtime 중심이다.

확인:

- `python run.py --mode demo` 또는 동등한 안전 명령이 동작하는가
- demo 모드가 유한 실행 또는 중단 가능한 형태인가
- live 모드가 실주문 없이 실행되는 경로가 있는가
- `KeyboardInterrupt` 또는 오류 종료 시 상태 저장이 일관적인가
- 로그 파일이 예상 경로에 생성되는가
- 같은 state/log 파일을 여러 모드가 공유하지 않는가

## Configuration Safety

`config.yaml`은 보호 대상이다.

DB 연결 정보도 보호 대상이다. `DATABASE_URL`은 env에 두고, 원문을 문서, 로그, 테스트 출력, config snapshot에 남기지 않는다. DB password를 `config.yaml`에 넣지 않는다.

확인:

- API key/secret 존재 여부
- `live_order_enabled`
- symbol
- trade size
- min trade cash
- fee/slippage
- state/log paths
- exchange

금지:

- 실제 key를 문서에 복사
- 실제 key를 테스트 fixture에 넣기
- 실제 key를 로그에 출력
- live order 설정을 무심코 true로 변경
- 주문 크기를 보호 승인 없이 키우기

## Runtime Trigger Cards

### TRIGGER CARD: Default Live Mode

Condition: 인자 없이 실행하면 live 경로로 들어간다.

Action: 작업 전 mode를 명시하고, 하네스 문서나 실행 스크립트에서 safe command를 우선 안내한다.

Do not touch:

- live order payload
- API key/secret

Verify:

- 실행 보고서에 사용한 mode를 남긴다

### TRIGGER CARD: Live Order Risk

Condition: `live_order_enabled=true`, REST client 생성, API key/secret 존재, market order call 가능성이 보인다.

Action: 명시적 승인 없이는 실행·수정하지 않는다. 필요하면 dry-run/paper로 전환한다.

Do not touch:

- `exchanges/binance/rest.py`
- live order quantity
- `config.yaml` secret fields

Verify:

- 실제 주문을 보내지 않았음을 보고한다

### TRIGGER CARD: Secret Exposure

Condition: API key/secret이 화면, 로그, 문서, diff, 테스트 결과에 나타날 수 있다.

Action: 즉시 중단하고 redaction 또는 env 분리 후보를 보고한다.

Do not touch:

- external API
- live order

Verify:

- 산출물에 raw secret이 없다

### TRIGGER CARD: External API Test

Condition: 테스트나 smoke run이 Binance REST 주문 또는 계정 조회를 보낼 수 있다.

Action: mock, dry-run, paper mode, 또는 명시적 승인 없이는 실행하지 않는다.

Do not touch:

- actual order endpoint

Verify:

- 네트워크 호출 범위가 보고된다

### TRIGGER CARD: State File Collision

Condition: demo/live/paper가 같은 `state.json` 또는 log 파일을 공유한다.

Action: 실행별 산출물 분리 후보를 만들고, destructive overwrite를 하지 않는다.

Do not touch:

- existing state deletion
- bulk log deletion

Verify:

- mode, symbol, exchange별 output path가 확인된다

### TRIGGER CARD: Strategy Threshold Change

Condition: 진입/청산 threshold, confirmation count, hard exit 조건을 바꾼다.

Action: `GUARDED_FIX` 이상으로 격상하고 테스트/리포트를 요구한다.

Do not touch:

- live order enablement
- API key/secret

Verify:

- `tests/test_market_structure.py` 또는 신규 테스트가 통과한다

### TRIGGER CARD: Order Size Change

Condition: `trade_size_cash`, `min_trade_cash`, 수량 포맷, 수수료/슬리피지를 변경한다.

Action: live 영향 가능성이 있으므로 최소 `GUARDED_FIX`, live 주문과 연결되면 `PROTECTED_CHANGE`.

Do not touch:

- Binance REST order execution without approval

Verify:

- BUY_SKIPPED, min notional, ledger impact를 확인한다

### TRIGGER CARD: Exchange Adapter Change

Condition: Binance REST/WS 또는 Coinone 등 새 거래소 어댑터를 변경한다.

Action: 인증/주문/필터/응답 형식이 포함되면 보호영역으로 본다.

Do not touch:

- live order execution
- secrets

Verify:

- parser tests, symbol normalization tests, order formatting tests를 분리한다

## Runtime Execution Card

실행 전:

```text
identify AREA and MODE
-> check config.yaml risk
-> check live_order_enabled
-> check secrets exposure
-> choose safe command
-> define expected output files
-> run only safe verification
-> inspect logs/state
-> report protected areas touched or not touched
```

실행 중:

- 이상한 주문 가능성이 보이면 즉시 중단
- stale WebSocket이나 reconnect loop는 전략 문제가 아니라 stream 문제로 분류
- 오류를 fake success로 숨기지 않는다

실행 후:

- mode
- command
- files touched
- external API touched 여부
- actual order sent 여부
- logs generated
- tests run
- remaining risk

를 보고한다.

## DB Safety Rule

현재 코드의 핵심 실행 경로는 아직 DB에 의존하지 않지만, 하네스 기준 DB 아키텍처는 PostgreSQL-first다.

`state.json`은 빠른 복구용 hot state이고, PostgreSQL은 실행 이력, 판단 근거, 주문/체결/자산 추적, reconciliation 기록용 blackbox다.

로컬 DB 기준:

- local PostgreSQL server를 1차 기준으로 한다.
- 연결 정보는 `DATABASE_URL` env에 둔다.
- `DATABASE_URL` 원문과 password는 로그, 문서, 테스트, config snapshot에 출력하지 않는다.
- DB 연결 실패는 demo에서는 명확한 warning/degraded mode로 처리할 수 있다.
- live order 경로에서는 DB 실패를 fake success로 숨기지 않는다.
- SQLite는 운영 기본 DB로 추가하지 않는다.

금지:

- `state.json` 무단 삭제
- 기존 거래 로그 삭제
- demo/live 로그 섞기
- 실거래 로그를 테스트 로그로 덮어쓰기
- `DROP TABLE`, `TRUNCATE`, destructive migration
- raw secret 또는 raw `DATABASE_URL` 저장
- SQLite를 운영 기본 DB로 추가
- live asset snapshot을 demo fake asset 결과로 갱신
- demo fake asset과 live asset을 같은 복구 기준으로 섞기
- PostgreSQL 연결 실패를 무시하고 live 주문을 계속 성공처럼 처리

선호:

- 실행별 output directory
- timestamped backup
- mode/symbol/exchange suffix
- read-only inspection first
- forward-only migration
- migration SQL forbidden pattern 검사
- DB disabled mode에서도 demo/test가 깨지지 않는 구조
- live 주문 전 DB/ledger 불일치가 보이면 `RECONCILIATION_REQUIRED`로 멈추는 구조

## Scheduler and Loop Safety

현재 별도 scheduler보다 runtime loop가 중요하다.

주의:

- WebSocket reconnect 무한 루프
- no-data watch
- demo tick interval
- candle interval
- hourly report interval
- cooldown state

loop 관련 변경은 중복 주문, 중복 캔들 처리, 과도한 로그를 만들 수 있으므로 검증이 필요하다.

## Binance External Impact Rule

Binance REST market order는 실제 외부 영향이다.

명시적 승인 없이 금지:

- market buy/sell 전송
- live order 기본값 true 변경
- 주문 크기 증가
- API key/secret 사용 경로 변경
- 주문 실패를 성공처럼 처리
- partial fill/failed order를 장부 성공으로 반영

주문 실패는 오류 세부 정보를 보존해야 하며, generic failure로 뭉개면 안 된다.

## Completion Report Requirement

런타임 작업 보고서는 최소 다음을 포함한다.

- AREA
- MODE
- PURPOSE FUNCTION
- files inspected
- files modified
- command run
- tests/checks run
- DB touched 여부
- migration touched 여부
- external API touched 여부
- actual order sent 여부
- protected areas touched 여부
- state/log impact
- remaining risks
- next CODE_TASK_CANDIDATE if any

## Stop Rule

다음이면 멈추고 보고한다.

- live order 가능성이 있는데 승인 없음
- API key/secret 노출 위험
- `config.yaml` 수정이 필요하지만 범위가 불명확
- Binance REST 주문 경로를 건드려야 함
- state/log 삭제가 필요함
- destructive migration이 필요함
- SQLite를 운영 기본 DB로 추가해야 함
- raw `DATABASE_URL`, API key, API secret 출력이 필요함
- live asset과 demo fake asset을 섞어야만 구현 가능함
- DB 오류를 무시해야만 live 주문 흐름이 진행됨
- 전략 threshold 변경의 손실 영향이 검증되지 않음
- 테스트가 실패했는데 원인이 다른 AREA임
- 레거시 앱과 현재 Python 런타임 경계가 불명확
- fix가 추측에 의존함

명확한 stop report가 위험한 완료보다 낫다.
