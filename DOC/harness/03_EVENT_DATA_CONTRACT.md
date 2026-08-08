# Event Data Contract

## 목적

이 문서는 서로 다른 공지 이벤트를 같은 시간축에서 비교하고, 나중에 원시 데이터로 결과를 재계산하기 위한 최소 계약을 정의한다.

## 시간 정의

### 필수 시각

| 필드 | 의미 |
|---|---|
| `source_first_listed_at` | 업비트 공지 응답의 `first_listed_at` |
| `source_listed_at` | 수정 반영을 포함한 공지 응답의 현재 `listed_at` |
| `response_received_at` | S23이 HTTP 응답 body를 받은 UTC 시각 |
| `notice_first_seen_at` | dedupe 결과 이 공지를 최초로 새 항목으로 확정한 UTC 시각 |
| `notice_processed_at` | 분류와 symbol 추출이 끝난 UTC 시각 |
| `market_event_time` | 거래소가 제공한 체결 event 시각 |
| `market_received_at` | S23이 체결 메시지를 받은 UTC 시각 |
| `monotonic_elapsed_ns` | 같은 프로세스 안의 순서·구간 계산용 monotonic 시각 |

두 개의 기준축을 모두 유지한다.

```text
T0_SOURCE   = source_first_listed_at
T0_OBSERVED = notice_first_seen_at
```

시장 반응 분석은 두 축을 모두 산출한다. 자동 진입의 event age guard는 더 보수적인 값이 되도록 source 시각과 단말 수신 시각을 함께 확인한다.

### 시간 품질

각 timestamp에는 다음 품질 중 하나를 붙인다.

```text
SOURCE_EXACT
SOURCE_ROUNDED
DEVICE_RECEIVED
DERIVED
UNKNOWN
```

기기의 UTC wall clock은 표시와 외부 데이터 조인에 사용하고, 프로세스 내부 latency는 monotonic clock으로 계산한다. 기기 시간 동기화 상태와 clock jump도 health event로 남긴다.

## 최소 엔터티

### `raw_notice_observation`

```text
id
source
request_started_at
response_received_at
http_status
source_cursor
payload_hash
raw_payload
parser_version
```

### `notice`

```text
notice_id
source
source_notice_id
source_uuid
title
url
category
source_first_listed_at
source_listed_at
source_time_precision
notice_first_seen_at
notice_processed_at
category
raw_asset_text
canonical_assets[]
classification_confidence
parser_version
payload_hash
```

### `symbol_resolution`

```text
notice_id
canonical_asset
target_exchange
candidate_symbols[]
selected_symbol
status = MATCHED | NO_MATCH | AMBIGUOUS
reason
market_metadata_version
resolved_at
```

### `event_session`

```text
event_id
notice_id
exchange
symbol
t0
state
capture_started_at
capture_ended_at
pre_event_data_status
live_stream_status
failure_reason
app_version
device_boot_id
```

### `market_sample`

```text
event_id
exchange
symbol
source_type = WS_TRADE | REST_BACKFILL | SNAPSHOT
market_event_time
market_received_at
price
quantity
trade_id
side_if_available
raw_payload_hash
```

### `event_metric`

```text
event_id
baseline_price
baseline_method
price_t_1s
price_t_2s
price_t_3s
price_t_5s
price_t_10s
price_t_30s
price_t_1m
price_t_3m
price_t_5m
price_t_10m
price_t_30m
first_abnormal_trade_offset_ms
first_abnormal_volume_offset_ms
peak_price
peak_offset_ms
max_drawdown
volume_multiplier
metric_version
```

metric 값은 원시 관측값이 아니라 계산 결과다. 계산식이나 version이 바뀌면 원시 데이터를 덮어쓰지 않고 새 version으로 다시 생성한다.

### `order_intent`

```text
intent_id
event_id
created_at
side = BUY | SELL
order_type = MARKET | LIMIT
symbol
quote_budget
requested_quantity
requested_price
rule_version
risk_snapshot_json
status
skip_or_failure_reason
```

주문 API를 호출하기 전에 반드시 저장한다.

### `exchange_order`

```text
intent_id
exchange_order_id
submitted_at
last_checked_at
side
order_type
price
original_quantity
executed_quantity
status
raw_response_hash
```

### `execution_fill`

```text
exchange_order_id
trade_id
executed_at
price
quantity
commission
commission_asset
raw_response_hash
```

### `position_state`

```text
event_id
symbol
buy_order_id
filled_quantity
average_buy_price
sellable_quantity
fixed_target_sell_price
sell_order_id
status
last_reconciled_at
```

`fixed_target_sell_price`는 매수 실제 fill을 모두 반영한 뒤 한 번 계산한다.

```text
raw target = average_buy_price * (1 + configured gross target rate)
fixed target = exchange tick size 규칙으로 보정한 raw target
```

fee를 목표 수익률 안팎 중 어디에 포함할지는 설정과 strategy version에 명시한다. 계산 후에는 동일 주문의 가격을 추적식으로 계속 변경하지 않는다.

### `reconciliation_event`

```text
detected_at
event_id
local_position_json
exchange_balance_json
exchange_open_orders_json
severity
resolution
resolved_at
```

### `runtime_health`

```text
captured_at
service_state
trading_session_state
notice_last_success_at
market_last_message_at
db_last_write_at
network_type
battery_level
is_charging
reconnect_count
consecutive_failure_count
open_position_count
open_order_count
is_reconciled
app_version
device_boot_id
```

## 식별과 중복 제거

우선순위:

```text
source + source_notice_id
  -> source + canonical URL
  -> normalized title + published time
  -> normalized content hash
```

- 같은 공지의 수정본은 새 이벤트가 아니라 revision으로 저장한다.
- 앱 재시작 뒤에도 같은 dedupe key를 사용한다.
- 파서 오류 때문에 식별자가 없으면 raw observation은 보관하되 자동 이벤트를 생성하지 않는다.
- `first_listed_at`이 같은 공지의 `listed_at` 변경만으로 두 번째 매수를 만들지 않는다.

## 기준 가격

`baseline_price`는 하나의 고정 의미로 사용하지 않고 `baseline_method`를 필수로 저장한다.

후보:

- T0 직전 마지막 체결가
- T0 이전 1초 VWAP
- T0 이전 5초 VWAP

초기 분석에서는 모두 계산할 수 있도록 원시 trade를 보존한다. 어떤 방법을 전략 기준으로 쓸지는 Evidence Review에서 결정한다.

## 데이터 완전성 상태

이벤트별로 다음을 평가한다.

```text
COMPLETE
MISSING_PRE_EVENT
STREAM_GAP
CLOCK_UNCERTAIN
PARSER_UNCERTAIN
SYMBOL_AMBIGUOUS
SOURCE_UNAVAILABLE
```

불완전한 이벤트를 삭제하지 않는다. 분석에서 포함·제외한 이유를 남긴다.

## 보존과 내보내기

- 원시 공지와 이벤트 핵심 데이터는 기본적으로 보존한다.
- 주문 intent, exchange order, fill, reconciliation 기록은 삭제하지 않는다.
- 고빈도 market sample의 보존 기간은 실제 용량 측정 후 결정한다.
- 내보내기는 schema version, app version, timezone=`UTC` 메타데이터를 포함한다.
- secret, device identifier, 인증 header는 export에 포함하지 않는다.
