# 2026-05-05 작업 기록

## Binance Exchange 전환

- 기존 Python runtime의 Coinone live 연결 경로를 제거하고 Binance 기준 exchange layer로 전환했다.
- `exchanges/binance/ws.py`를 추가해 `wss://stream.binance.com:9443/ws`에 연결하고 `{symbol}@trade`, `{symbol}@ticker`를 구독한다.
- Binance trade payload의 `p`, `q`, `T`를 각각 `price`, `volume`, `timestamp`로 변환한다.
- `exchanges/binance/rest.py`를 추가해 `POST /api/v3/order` MARKET 주문 서명 흐름을 구현했다.
- `run.py` live 경로를 Binance WebSocket + optional Binance REST order client로 변경했다.
- 전략 판단 로직은 그대로 유지하고, 입력 데이터와 주문 adapter만 Binance 형식으로 바꿨다.
- `exchange=binance`, `symbol=ROBOUSDT`, `market=spot`, `trade_size` config를 반영했다.
- 실제 REST 주문은 안전상 `live_order_enabled: false`가 기본이며, 명시적으로 켜고 API key/secret이 있을 때만 실행된다.
- Coinone runtime package 파일은 제거했고, architecture/roadmap의 exchange 표기도 Binance 기준으로 갱신했다.

## 검증

- `python -m compileall core exchanges run.py tests`
- `python -m unittest discover -v`
- `python run.py --mode demo --ticks 120 --min-trade-cash 100`

## Binance WebSocket 안정화 보완

- ROBOUSDT는 5초 이상 거래 이벤트가 비는 구간이 있어 `ws_no_data_timeout_sec: 5`가 정상 연결을 반복적으로 끊었다.
- `ws_no_data_timeout_sec` 기본값과 config 값을 `60`초로 완화했다.
- Binance stream 기본 구독에 `{symbol}@kline_1m`을 추가해 저유동성 구간에서도 연결 상태 확인용 메시지를 받을 수 있게 했다.
- `trade` 이벤트의 `q`만 실제 tick volume으로 사용하고, `ticker`/`kline`의 누적 volume은 candle volume 왜곡을 막기 위해 `0.0`으로 처리했다.
- 25초 WebSocket 유지 테스트에서 `disconnected=False` 확인.

## Live Runtime Visibility 추가

- Binance WebSocket에 `ws_status_interval_sec` 설정을 추가했다.
- 기본값은 30초이며, 연결 중이면 `[WS_STATUS]` 로그로 메시지 수, 가격 이벤트 수, 마지막 가격, 마지막 메시지 경과 시간을 출력한다.
- closed candle이 생성되어 전략 판단이 갱신될 때마다 `[LIVE_DECISION]` 로그를 출력한다.
- 운영자는 터미널에서 `[WS_STATUS]`로 연결 생존 여부를, `[LIVE_DECISION]`으로 전략 판단 진행 여부를 확인할 수 있다.
