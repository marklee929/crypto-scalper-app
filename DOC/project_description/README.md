# Heart Beat Coin Scalper 프로젝트 설명

작성일: 2026-06-22

## 1. 프로젝트 개요

`heart_beat_coin_scalper`는 Binance 현물 시장을 대상으로 하는 Python 기반 코인 스캘핑 런타임이다. 현재 구현의 중심은 짧은 주기의 가격 이벤트를 캔들로 집계하고, 닫힌 캔들을 시장 구조 분석에 넣어 진입/청산 여부를 판단한 뒤, 장부와 로그에 실행 결과를 남기는 구조다.

프로젝트 이름에는 `heartbeat`가 들어가지만, 현재 코드의 실제 진입 로직은 단순한 가격 퍼센트 반등 감지가 아니라 `core.market_structure`의 구조 점수와 금지 조건을 중심으로 동작한다. 즉, "저점 대비 몇 퍼센트 상승"만으로 매수하는 전략이 아니라, 저점/고점 구조, 이동평균 회복, 매수/매도 거래량 흐름, 지지/저항 반응, 과열 여부를 함께 보는 형태다.

현재 런타임은 두 가지 모드를 가진다.

- `demo`: 의사 난수 기반 가격 스트림을 생성해 전략, 장부, 상태 저장, 로그 흐름을 검증한다.
- `live`: Binance WebSocket으로 가격 이벤트를 받고, 설정에 따라 Binance REST 시장가 주문까지 보낼 수 있다.

주의할 점은 기본 실행 모드가 `live`라는 점이다. `run.py`와 `run.bat` 모두 별도 인자가 없으면 실시간 Binance 경로로 들어간다. 또한 현재 `config.yaml`에는 라이브 주문 관련 설정과 민감정보 필드가 존재하므로, 새 하네스 작업에서는 설정 파일을 보호 대상으로 취급해야 한다. 문서나 테스트 산출물에 실제 키 값을 복사하지 않는다.

## 2. 현재 코드 기준 시스템 흐름

```text
config.yaml / CLI 인자
-> run.py
-> demo 가격 스트림 또는 Binance WebSocket 가격 이벤트
-> CandleAggregator
-> HeartbeatStrategy.on_candle()
-> market_structure 분류/진입/청산 판단
-> Ledger 매수/매도 반영
-> BinanceRestClient 주문 전송(라이브 주문 활성화 시)
-> trades.log / strategy.log / hourly_report.log / state.json
```

핵심 특징은 닫힌 캔들 기준 의사결정이다. `CandleAggregator.update()`는 현재 버킷 안에서는 진행 중 캔들만 갱신하고, 새 시간 버킷이 시작될 때 이전 캔들을 `closed`로 반환한다. `run._process_tick()`은 이 닫힌 캔들이 있을 때만 전략 판단을 실행한다.

## 3. 디렉터리와 구성요소

### 루트 실행 파일

- `run.py`: 전체 런타임 진입점이다. 설정 로드, demo/live 모드 분기, 틱 처리, 주문 가드, 상태 저장, 로그 기록을 연결한다.
- `run.bat`: Windows 실행 편의 스크립트다. 인자가 없으면 `--mode live`로 실행한다.
- `config.yaml`: 거래소, 심볼, 수수료/슬리피지, 주문 크기, 캔들 주기, Binance 연결, 로그/상태 파일 경로를 담는다.

### `core`

- `config.py`: 기본 설정값과 YAML 로더를 제공한다. PyYAML이 없으면 단순 YAML 파서를 fallback으로 사용한다. `trade_size`는 `trade_size_cash` 별칭으로 매핑된다.
- `candle_aggregator.py`: 틱 가격을 OHLCV 캔들로 묶는다. 현재 전략 경로의 첫 번째 핵심 모듈이다.
- `market_structure.py`: 시장 상태 분류, 진입 허용 여부, 청산 여부를 계산한다. 현재 전략 판단의 중심이다.
- `heartbeat.py`: `IDLE`, `IN_POSITION`, `COOLDOWN` 상태를 가진 전략 상태 머신이다. 실제 진입/청산 판단은 `market_structure`의 결과를 사용한다.
- `state.py`: `state.json`에 장부와 전략 상태를 원자적으로 저장/복구한다.
- `volatility.py`: 단순 변동성 필터 골격이다. 현재 `run.py`의 주 경로에는 연결되어 있지 않다.
- `timeframe_guard.py`: 멀티 타임프레임 가드 골격이다. 현재는 내부 차단 플래그만 가진 stub 성격이다.
- `oracle.py`: Oracle 신호 골격이다. 현재는 항상 `ENTER`를 반환하는 stub 성격이다.

### `paper`

- `ledger.py`: 현금, 포지션 수량, 평균단가, 실현손익, 수수료, 슬리피지, 거래 이벤트를 관리한다.
- `report.py`: 거래 로그와 시간별 리포트를 텍스트 파일에 append한다.

### `exchanges/binance`

- `ws.py`: Binance WebSocket 연결, 구독, 재접속, 무데이터 감시, 상태 출력, 가격 메시지 파싱을 담당한다. trade, ticker, kline 이벤트에서 가격을 추출한다.
- `rest.py`: Binance 서명 REST 요청과 시장가 주문 전송을 담당한다. 심볼 정규화와 수량 포맷팅도 포함한다.

### `services`

- `logger.py`: 회전 파일 로거를 생성한다.
- `notifier.py`: 로거가 있으면 로거로, 없으면 콘솔로 메시지를 보낸다.

현재 주 실행 경로에서는 `services` 계층이 강하게 연결되어 있지 않다. 향후 하네스에서는 관찰성/알림 계층으로 분리해 붙일 수 있는 후보로 보면 된다.

### `tests`

- `test_candle_aggregator.py`: 캔들 버킷 생성, OHLCV 갱신, 새 구간에서 닫힌 캔들 반환, 잘못된 가격/구간 검증을 다룬다.
- `test_market_structure.py`: 하락 횡보 차단, 매집 횡보 관찰, heartbeat 진입, 구조 붕괴 청산, 과열 구간 진입 차단/익절 등을 다룬다.
- `test_binance_exchange.py`: Binance 메시지 파싱, 심볼 정규화, 주문 수량 포맷팅을 검증한다.
- `test_run_guards.py`: 최소 주문금액 가드, CLI 옵션, 기본 모드, live 설정 검증, live 주문 client 가드를 다룬다.

### `crypto_scalper_app_legacy`

Flutter/Dart 기반의 이전 앱 구현이 들어 있다. 현재 Python 런타임과는 별도 경로다. 새 하네스 작업에서 현재 동작을 기준으로 삼을 때는 루트 Python 코드와 `tests`를 우선해야 하며, 레거시 앱은 참고 자료로만 취급하는 편이 안전하다.

### `DOC`

기존 `architect.md`, `operation_guide.md`, `development_roadmap.md`는 코인 스캘퍼 초기 설계 의도를 담고 있으나 일부 파일은 인코딩이 깨져 있다. `DOC/architecture` 아래 일부 문서는 현재 코드의 코인 스캘퍼 문맥이 아니라 다른 WorkConnect 문맥을 담고 있으므로, 이 프로젝트의 실행 하네스 기준 문서로 직접 사용하면 혼선이 생길 수 있다.

## 4. 전략 구현 분석

### 상태 머신

`HeartbeatStrategy`는 다음 상태를 가진다.

- `IDLE`: 포지션이 없는 대기 상태다. 닫힌 캔들을 누적하고 `can_enter()`가 허용하면 `BUY`를 반환한다.
- `IN_POSITION`: 포지션 보유 상태다. `should_exit()`가 청산을 지시하면 `SELL`을 반환한다.
- `COOLDOWN`: 청산 뒤 일정 시간 동안 재진입을 막는다. 시간이 지나면 `IDLE`로 복귀한다.

전략은 스냅샷과 복구를 지원한다. 저장 대상에는 상태, 최근 저점, 진입가, 진입 당시 구조 저점/고점, peak, cooldown 시각, 최근 캔들 목록, 마지막 판단 로그가 포함된다.

### 시장 구조 분류

`market_structure.classify_market()`은 다음 요소를 합산해 시장 상태를 만든다.

- 구조 점수: higher low, strong low hold, higher high, lower high, previous low 이탈
- 거래량 점수: 매수 거래량 증가, 매도 거래량 감소, 매도 거래량 급증, 거래량 고갈
- 이동평균 점수: 단기 MA 회복/유지, 단기 MA 하회, dead cross
- 지지/저항 점수: 저항 돌파 후 유지, 저항 터치 후 유지, 저항 부근 강한 거절, 직전 저점 이탈

분류 결과는 `NO_TRADE`, `DEAD`, `FALLING`, `ACCUMULATION`, `HEARTBEAT`, `STRONG_HEARTBEAT` 중 하나다. 진입은 `HEARTBEAT` 또는 `STRONG_HEARTBEAT` 상태에서 확인 신호가 최소 3개 이상일 때 허용된다.

### 진입 차단 조건

다음 조건은 진입 차단 사유로 기록된다.

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

현재 `run.py`는 별도 BTC 상태를 연결하지 않으므로, BTC dumping 같은 컨텍스트 기반 차단은 외부 하네스나 상위 런타임에서 값을 넣을 때 의미가 커진다.

### 청산 조건

청산은 크게 hard exit와 take profit으로 나뉜다.

- hard exit: BTC dumping, 진입 구조 붕괴, 직전 저점 이탈, 단기 MA 이탈, 매도 거래량 급증, 새 고점 실패, 저항 거절
- take profit: 저항 터치, 단기 과열, 윗꼬리 증가, 매수 거래량 감소, 새 고점 실패 중 2개 이상

청산 이후에는 `cooldown_sec` 동안 `COOLDOWN`에 머문다.

## 5. 주문, 장부, 로그

`run._process_tick()`은 전략이 `BUY`를 반환하면 `trade_size_cash`와 현재 현금 중 작은 값을 주문 금액으로 사용한다. 이 값이 `min_trade_cash`보다 작으면 실제 매수하지 않고 `BUY_SKIPPED` 이벤트를 전략 로그에 남긴다.

라이브 주문은 `live_order_enabled`가 true일 때만 REST client를 통해 전송된다. 이때 client가 없으면 런타임 오류를 발생시킨다. REST 주문이 성공한 뒤 장부에 반영되는 구조이므로, 주문 실패와 장부 반영의 순서가 명확하다.

주요 산출물은 다음과 같다.

- `state.json`: 장부와 전략 상태 복구용 상태 파일
- `strategy.log`: 각 닫힌 캔들에서의 전략 판단 로그
- `trades.log`: 매수/매도 체결 이벤트 로그
- `hourly_report.log`: 주기적 장부 요약 로그

## 6. 설정과 운영상 주의점

현재 기본 설정은 Binance spot, `ROBOUSDT`, 60초 캔들, demo tick 5초, 초기 현금 1,000,000, 최소 주문 금액 100, 주문 크기 100,000을 기준으로 한다.

운영상 특히 중요한 점은 다음과 같다.

- `run.py`의 기본 모드는 `live`다.
- `run.bat`도 인자가 없으면 live 모드로 실행한다.
- `live_order_enabled`가 true이고 API key/secret이 있으면 실제 주문 경로가 열릴 수 있다.
- API key/secret은 문서, 테스트 fixture, 로그, 커밋 산출물에 복사하지 않는다.
- 새 하네스에서는 dry-run 또는 명시적 paper/live 분리를 가장 먼저 보장해야 한다.

## 7. 현재 테스트가 보장하는 것

테스트는 다음 영역의 회귀를 막는다.

- 캔들 집계가 시간 버킷 경계를 기준으로 닫힌 캔들을 반환하는지
- 시장 구조 분류가 하락 횡보, 매집, heartbeat, 과열, 구조 붕괴를 구분하는지
- Binance trade/ticker/kline 메시지에서 가격을 안정적으로 파싱하는지
- 기본 실행 모드가 live인지
- demo 모드가 기본적으로 유한 실행인지
- 최소 주문 금액 미만이면 매수를 건너뛰는지
- live 주문 활성화 시 REST client가 필요한지

새 하네스 작업에서는 이 테스트들이 현재 동작의 최소 기준선이다. 하네스가 런타임을 감싸거나 실행 모드를 바꾸더라도 이 기준선은 먼저 유지되어야 한다.

## 8. 새 하네스 작업을 위한 분석 메모

새 하네스의 1차 목표는 코드 변경보다 실행 경계와 안전장치를 명확하게 만드는 것이다. 현재 코드에서 하네스가 가장 먼저 다뤄야 할 경계는 다음이다.

- 실행 모드 경계: demo, paper, live를 명시적으로 분리한다.
- 주문 경계: 실제 REST 주문은 명시적 승인/설정이 있을 때만 허용한다.
- 설정 경계: 민감정보와 일반 전략 파라미터를 분리한다.
- 데이터 경계: raw tick, current candle, closed candle, strategy decision, order event, ledger event를 구분한다.
- 복구 경계: `state.json`이 어느 실행 모드의 상태인지 표시할 수 있어야 한다.
- 관찰성 경계: strategy/trade/report 로그의 포맷과 보존 정책을 하네스가 알고 있어야 한다.
- 레거시 경계: Flutter 레거시 앱과 현재 Python 런타임을 같은 실행 단위로 취급하지 않는다.
- 문서 경계: `DOC/architecture` 일부 문서는 현재 프로젝트 문맥과 다르므로, 새 하네스의 기준 문서는 실제 코드 분석 문서와 테스트를 우선한다.

하네스가 입력으로 삼기 좋은 최소 이벤트 모델은 다음과 같다.

```text
PriceEvent(symbol, price, volume, timestamp, source)
-> CandleUpdate(current, closed)
-> StrategyDecision(event, market_state, reasons, score, current_price)
-> OrderIntent(side, symbol, qty, cash_budget, mode)
-> ExecutionResult(side, qty, price, fee, slippage, external_order_id?)
-> LedgerSnapshot(cash, position_qty, avg_price, realized_pnl, equity)
```

현재 코드는 이 모델을 명시적 타입으로 모두 갖고 있지는 않지만, 각 값은 이미 `run.py`, `CandleAggregator`, `HeartbeatStrategy.last_decision`, `Ledger`, `TradeEvent`에 흩어져 있다. 새 하네스는 이 흐름을 감싸서 모드 안전성, 재현성, 테스트 가능성을 높이는 방향이 적합하다.

## 9. 코드상 미완성 또는 주의 대상

- `volatility.py`, `timeframe_guard.py`, `oracle.py`는 설계상 존재하지만 현재 메인 런타임에 깊게 연결되어 있지 않다.
- `HeartbeatStrategy`의 docstring은 "이전 퍼센트 trigger는 사용하지 않는다"고 명시한다. 따라서 문서나 하네스에서 과거 percentage heartbeat 설계를 현재 진입 로직으로 오해하면 안 된다.
- `config.yaml`과 `DEFAULT_CONFIG`의 live 주문 기본값이 다르다. 코드 기본값은 false지만 현재 로컬 설정 파일은 true일 수 있다.
- 로그 파일과 상태 파일이 루트에 직접 쌓인다. 하네스에서 실행별 산출물 디렉터리를 분리하면 재현성과 안전성이 좋아진다.
- Binance REST 주문 수량은 단순 소수점 문자열 포맷만 적용한다. 거래소의 step size, min notional, precision 필터 검증은 별도 보강 대상이다.
- WebSocket은 trade, ticker, kline을 함께 구독하지만 `run.py`의 캔들 집계는 들어오는 가격 이벤트를 동일 입력처럼 처리한다. 중복 또는 혼합 이벤트에 대한 정책은 하네스에서 명확히 할 필요가 있다.

## 10. 하네스 기준 우선순위 제안

1. 기본 실행을 안전한 paper/demo로 고정하고, live 주문은 별도 명시 옵션으로만 열기
2. 민감정보를 환경변수 또는 별도 비추적 설정으로 분리
3. 실행별 산출물 디렉터리 생성: state, strategy log, trades log, report log 분리
4. PriceEvent부터 LedgerSnapshot까지 이벤트 흐름을 기록하는 얇은 하네스 계층 추가
5. Binance 실시간 입력과 demo 입력을 같은 인터페이스로 맞추기
6. 현재 테스트를 유지한 상태에서 하네스 단위 테스트 추가
7. 거래소 주문 필터, 중복 이벤트 정책, 장애 복구 정책을 별도 문서와 테스트로 고정
