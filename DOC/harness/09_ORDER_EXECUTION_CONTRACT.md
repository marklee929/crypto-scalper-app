# Order Execution Contract

## 목적

공지 감지 후 주문이 실행되는 정상 경로와 실패·복구 경로를 고정한다.

정상 주문 계약:

```text
조건부 진입
-> MARKET BUY
-> 실제 fills 확정
-> 목표 매도가 1회 계산
-> 고정 가격 LIMIT SELL
```

## 자동 진입 전제조건

다음 조건을 모두 만족해야 `BUY_INTENT_SAVED`로 이동한다.

```text
trading_session == LIVE_GUARDED
runtime_health == HEALTHY
power_state == CHARGING
notice_contract == VALID
notice_type == NEW_MARKET_SUPPORT
event_age <= configured_max_entry_age
symbol_resolution == MATCHED
market_status == TRADING
market_data == FRESH
price_move <= configured_max_pre_entry_move
spread <= configured_max_spread
estimated_slippage <= configured_max_slippage
position_count == 0
open_order_count == 0
reconciliation == CLEAN
daily_risk_limit == AVAILABLE
order_budget <= configured_order_budget
```

조건이 하나라도 `false` 또는 `unknown`이면 주문을 보내지 않고 `SKIPPED`와 reason code를 저장한다.

## 1. 시장가 매수

- 매수 side는 `BUY`, order type은 `MARKET`으로 고정한다.
- 주문 금액은 세션에 설정된 1회 quote 예산을 넘지 않는다.
- exchange filter와 최소 주문금액을 주문 직전에 확인한다.
- `client_order_id`는 event와 intent에서 결정적으로 생성해 재시도 시 중복 매수를 막는다.
- API timeout은 실패 확정이 아니다. client order id로 주문 상태를 조회한 뒤 판단한다.
- 주문 상태가 불명확하면 신규 주문을 만들지 않고 `RECONCILIATION_REQUIRED`로 전환한다.

## 2. 실제 체결 확정

목표 매도가는 예상 매수가나 공지 감지 시세로 계산하지 않는다.

필수 계산 입력:

```text
executed quote amount
executed base quantity
fill별 price와 quantity
buy commission과 commission asset
실제 sellable base quantity
예상 sell fee rate
exchange price tick size
exchange quantity step size
configured net target rate
```

부분 체결이면 exchange의 최종 주문 상태를 먼저 확인한다. 취소 후 체결분만 보유하게 된 경우에도 실제 보유량으로 매도 계약을 생성한다.

## 3. 고정 목표 매도가 계산

목표는 설정된 순수익률을 수수료 이후에 만족시키는 가격이다.

개념식:

```text
acquisition_cost_quote
  = 실제 매수 체결 quote 금액 + quote 환산 매수 수수료

raw_target_price
  = acquisition_cost_quote * (1 + configured_net_target_rate)
    / (sellable_quantity * (1 - estimated_sell_fee_rate))

fixed_target_sell_price
  = raw_target_price를 exchange tick size에 맞게 올림 보정

fixed_sell_quantity
  = sellable_quantity를 exchange step size에 맞게 내림 보정
```

수수료가 별도 자산으로 결제되어 정확한 quote 환산이 불가능하면 해당 환산 방식과 가격 원천을 기록한다. 입력 하나라도 불명확하면 지정가 주문 전에 reconciliation한다.

## 4. 지정가 매도

- 매도 side는 `SELL`, order type은 `LIMIT`으로 고정한다.
- 정상 경로의 time-in-force는 `GTC`를 기본 후보로 두되 exchange adapter 구현 시 확인한다.
- `SELL_INTENT`를 저장한 후 주문 API를 호출한다.
- 계산된 `fixed_target_sell_price`는 주문 제출 후 가격 추종 목적으로 변경하지 않는다.
- reject가 tick/step 형식 문제라면 같은 raw target에서 형식만 다시 보정할 수 있다.
- 전략 목표가 변경이나 trailing 전환은 같은 주문의 수정이 아니라 새 strategy version이다.

## 5. 주문 상태

```text
BUY_INTENT_SAVED
BUY_SUBMITTED
BUY_PARTIALLY_FILLED
BUY_FILLED
BUY_REJECTED
BUY_STATUS_UNKNOWN

SELL_PRICE_FIXED
SELL_INTENT_SAVED
SELL_SUBMITTED
SELL_PARTIALLY_FILLED
SELL_FILLED
SELL_REJECTED
SELL_STATUS_UNKNOWN

RECONCILIATION_REQUIRED
EXITED
```

`*_STATUS_UNKNOWN`과 `RECONCILIATION_REQUIRED`에서는 신규 매수를 금지한다.

## 6. 재시작과 중복 방지

앱/process/service 재시작 시 로컬 상태만 믿지 않는다.

```text
local active intent/order 읽기
-> exchange open order 조회
-> client order id로 주문 상태 조회
-> account balance 조회
-> fills 조회
-> local position 재구성
-> 일치하면 CLEAN
-> 불일치하면 RECONCILIATION_REQUIRED
```

reconciliation이 끝나기 전에는 공지 감지는 계속할 수 있지만 신규 매수는 실행하지 않는다.

## 7. 지정가 미체결과 비상청산

정상 청산은 고정 목표가 지정가 매도다.

다음 정책 숫자는 아직 `OPEN`이며 구현 전에 확정해야 한다.

```text
지정가 최대 대기시간
부분 체결 후 잔량 처리
손절 가격 또는 손실률
공지 오탐 발견 시 처리
거래소 장애 시 처리
충전 분리 장기화 시 처리
비상 시장가 매도 허용 여부
```

비상청산은 정상 고정가 매도와 분리된 보호 정책이다. 값이 정해지지 않은 상태에서 임의로 시장가 청산하거나 무기한 방치하지 않는다.

## 8. 알림과 감사 로그

다음 이벤트는 로컬 알림과 영속 로그를 남긴다.

```text
진입 조건 통과/skip
시장가 매수 제출/체결/거부/불명확
고정 목표 매도가와 계산 입력
지정가 매도 제출/부분 체결/완전 체결/거부
reconciliation 시작/성공/실패
runtime stale 또는 power 상태 변화
```

로그에는 API key, signature, Authorization header를 넣지 않는다.

