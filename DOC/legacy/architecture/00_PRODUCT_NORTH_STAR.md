# Product Constitution

## Core Mission

`heart_beat_coin_scalper`는 Binance 현물 시장의 짧은 가격 박동을 관찰하고, 닫힌 캔들 기반 시장 구조 판단을 통해 손실을 제한하면서 반복 가능한 진입/청산을 실험·운영하기 위한 Python 코인 스캘핑 런타임이다.

이 프로젝트의 핵심은 “많이 매매하는 봇”이 아니라, 가격 이벤트를 캔들로 정리하고, 구조 점수와 금지 조건을 통과한 경우에만 제한된 주문 의도를 만들며, 모든 판단과 결과를 장부·상태·로그로 남기는 것이다.

## Purpose Function

수익은 최대, 손실은 최소를 목표로 하되, 실주문보다 생존성·검증성·재현성을 우선한다.

```text
시장 가격 이벤트
-> 닫힌 캔들
-> 시장 구조 분류
-> 진입/청산 판단
-> 주문 의도
-> 실행/스킵
-> 장부/상태/로그
-> 피드백
```

이 목적 함수는 빠른 구현, 높은 거래 빈도, 감정적 추격매수, 단기 수익률 과장, 자동화 편의성보다 우선한다.

## Current Active Scope

현재 활성 범위는 Binance spot 기반 Python 런타임이다.

현재 README 기준 실행 경로는 다음을 중심으로 본다.

- `run.py`
- `run.bat`
- `config.yaml`
- `core/candle_aggregator.py`
- `core/market_structure.py`
- `core/heartbeat.py`
- `core/state.py`
- `paper/ledger.py`
- `paper/report.py`
- `exchanges/binance/ws.py`
- `exchanges/binance/rest.py`
- `tests/`

`crypto_scalper_app_legacy`는 현재 Python 런타임과 별도 경로의 레거시 앱이며, 현행 하네스의 기준 실행 단위로 보지 않는다.

## Strategy Identity

프로젝트 이름에는 `heartbeat`가 들어가지만, 현재 전략은 단순한 “저점 대비 N% 반등 매수”가 아니다.

현재 전략 정체성은 다음에 가깝다.

```text
닫힌 캔들 누적
-> 저점/고점 구조 확인
-> 이동평균 회복/이탈 확인
-> 매수/매도 거래량 흐름 확인
-> 지지/저항 반응 확인
-> 과열/붕괴/거절 차단
-> HEARTBEAT 또는 STRONG_HEARTBEAT일 때 제한 진입
```

따라서 새 문서나 코드 작업에서 과거 percentage heartbeat 아이디어를 현재 진입 로직으로 오해하면 안 된다.

## Strategy Archetype: Tracking, Not Box-First

현재 코드는 **박스형(box-first)** 이 아니라 **추적형(tracking-first)** 으로 분류한다.

박스형 전략은 먼저 고정 또는 준고정 가격 구간을 정의한다.

```text
box low
-> box high
-> lower band entry
-> upper band exit
-> range invalidation
```

추적형 전략은 가격 이벤트가 닫힌 캔들로 확정된 뒤, 새로 형성되는 저점·고점·거래량·이동평균·지지/저항 반응을 계속 따라가며 현재 구조가 살아 있는지 판단한다.

```text
price event
-> closed candle
-> rolling structure memory
-> market_state update
-> entry block / exit reason
-> state transition
```

현재 `core.market_structure`는 지지/저항과 최근 저점/고점을 사용하므로 박스 정보를 전혀 쓰지 않는 것은 아니다. 하지만 박스를 먼저 고정하고 그 안에서만 매수·매도하는 구조가 아니라, 닫힌 캔들마다 시장 구조를 갱신하고 `HEARTBEAT`, `STRONG_HEARTBEAT`, `FALLING`, `DEAD`, `ACCUMULATION` 같은 상태로 추적한다.

따라서 현행 전략 정체성은 다음처럼 표현한다.

```text
tracking-first heartbeat scalper
with structural box reference
```

문서, 코드, 테스트, 리포트는 이 분류를 유지해야 한다. 향후 박스형 전략을 추가하려면 `BOX_RANGE_STRATEGY` 또는 별도 module/AREA로 분리하고, 현재 `MARKET_STRUCTURE_STRATEGY`를 박스형으로 재해석하면 안 된다.

## Trading Constitution

이 프로젝트의 모든 판단은 다음 순서를 따른다.

1. 생존 가능한가
2. 손실 제한 조건이 명확한가
3. 진입 이유와 무효화 조건이 로그로 남는가
4. 동일 입력에서 재현 가능한가
5. 실주문으로 넘어가도 되는 모드인가
6. 기대 수익이 비용, 슬리피지, 오류 위험보다 큰가

수익률을 높이는 변경이라도 손실 제한, 실주문 경계, 복구 가능성, 검증 가능성을 약화하면 우선 차단한다.

## Target Operator

주요 사용자는 이 프로젝트를 직접 운영·개선하는 개인 오퍼레이터다.

오퍼레이터는 다음을 원한다.

- 실시간 가격 흐름을 자동으로 캔들화
- 구조적 반등과 죽은 흐름 구분
- 진입/청산 이유 확인
- demo/paper/live 경계 분리
- 장부와 상태 복구
- 실주문 사고 방지
- 반복 가능한 실험과 테스트
- 장기적으로 Binance 외 거래소 확장 가능성

## Classification Principle

거래 신호는 다음을 만족할 때만 의미가 있다.

- 닫힌 캔들 기준으로 판단된다
- 시장 구조가 `HEARTBEAT` 또는 `STRONG_HEARTBEAT`에 가깝다
- 확인 신호가 충분하다
- 금지 조건이 없다
- 손절 또는 구조 붕괴 청산 기준이 있다
- 주문 모드가 안전하게 확인된다
- 장부·로그·상태에 결과가 남는다

단순 상승, 커뮤니티 내러티브, 신규 상장 흥분, 급등 추격, 감정적 복구매매는 신호가 아니다.

## What This Project Must Not Become

이 프로젝트는 다음이 되면 안 된다.

- API key가 들어간 무방비 실주문 스크립트
- 기본값으로 실계좌를 건드리는 봇
- 손절 없는 물타기 봇
- 급등 코인 추격 봇
- 뉴스/내러티브만 보고 매수하는 봇
- 로그 없이 결과만 남기는 블랙박스
- 백테스트 없이 파라미터만 바꾸는 실험장
- `demo`, `paper`, `live`가 뒤섞인 런타임
- 손실을 숨기고 수익만 강조하는 리포트
- 거래소 장애나 WebSocket 중복 이벤트를 무시하는 자동화

## Automation Constitution

자동화가 도와도 되는 영역:

- 가격 이벤트 수신
- 캔들 집계
- 시장 구조 분류
- 진입/청산 후보 계산
- 주문 의도 생성
- 최소 주문 금액 가드
- 장부 반영
- 상태 저장/복구
- 로그/리포트 작성
- 테스트와 회귀 검증

자동화가 단독으로 결정하면 안 되는 영역:

- 실주문 활성화
- API key/secret 처리
- 기본 실행 모드를 위험하게 변경
- 거래소 주문 필터를 무시한 주문
- 손실 제한 없는 전략 변경
- 미검증 파라미터 실계좌 반영
- 레거시 앱과 현행 런타임을 임의로 병합
- Binance 외 거래소 확장 시 인증/주문 규격 추정

## Exchange Expansion Rule

현재 기준 거래소는 Binance spot이다.

향후 Coinone/KRW 경로를 붙일 경우 Coinone 최신 API 기준은 `2.1`로 보고, Binance 어댑터와 분리된 새 거래소 어댑터로 설계한다.

거래소별 차이는 전략 목적을 바꾸지 않는다.

```text
전략 목적
-> 거래소 어댑터
-> 주문 규격
-> 수량/호가/최소 주문 필터
-> 실행 결과
```

거래소 확장은 보호영역이며, 주문·인증·수량 포맷·최소 주문금액 검증 없이 live 경로로 연결하면 안 된다.

## Success Criteria

프로젝트가 정상 방향이면 다음이 가능해야 한다.

- 기본 실행이 실주문 사고를 일으키지 않는다
- `demo`, `paper`, `live` 모드가 명확히 구분된다
- 닫힌 캔들 기준 전략 판단이 유지된다
- 진입/청산 이유가 로그로 남는다
- 최소 주문금액과 live order guard가 작동한다
- `state.json` 복구가 실행 모드와 충돌하지 않는다
- 실주문은 명시적 승인과 설정이 있을 때만 가능하다
- API key/secret이 문서, 테스트, 로그, 커밋에 노출되지 않는다
- 전략 변경은 테스트 또는 재현 가능한 리포트와 함께 이루어진다
- 손실과 스킵 이벤트가 수익 이벤트만큼 정직하게 기록된다
