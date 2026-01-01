heart_beat_coin_scalper 전체 구조 문서

# Heart Beat Coin Scalper – Architecture

## 0. 설계 철학
- 예측 ❌ / 반응 ⭕
- AI는 결정권자가 아닌 **조언자(Oracle)**
- 매매는 항상 **저변동 구간에서 시장가**
- 비용(수수료+슬리피지)을 포함해 **실효 1% 이상 갭 유지**
- 장애/재시작/드리프트에 강한 구조

---

## 1. 전체 구조 개요

[Price Feed]
  └─ (REST / WebSocket)
        ↓
[Volatility Filter]  ← 시장가 허용 여부
        ↓
[Multi-Timeframe Guard]
  - 1m / 5m / 10m / 30m
        ↓
[Heartbeat Strategy Core]
  - IDLE / IN_POSITION / COOLDOWN
        ↓
[Oracle (Optional)]
  - ENTER / CAUTION / EXIT
        ↓
[Paper / Live Executor]
        ↓
[Ledger + Report]

2. 디렉토리 구조
heart_beat_coin_scalper/
├─ core/
│  ├─ state.py            # 상태머신, 상태저장/복구
│  ├─ heartbeat.py        # 심장박동 진입/청산 로직
│  ├─ volatility.py       # 변동성 계산, 시장가 허용
│  ├─ timeframe_guard.py  # 1/5/10/30분봉 권한 구조
│  └─ oracle.py           # 예언자(조언자) 모델
│
├─ exchanges/
│  └─ coinone/
│     ├─ rest.py          # Coinone REST v2.1
│     └─ ws.py            # (선택) WebSocket
│
├─ paper/
│  ├─ ledger.py           # 가상 시트, 손익 계산
│  └─ report.py           # 이벤트/정각 리포트
│
├─ services/
│  ├─ notifier.py         # Telegram / 콘솔 알림
│  └─ logger.py           # 파일 로그/로테이션
│
├─ config.yaml            # 모든 전략 파라미터
├─ run.py                 # 단일 실행 엔트리
└─ README.md

3. 핵심 전략 로직
3.1 심장박동(Heartbeat)

진입: 최근 저점 대비 +1% 회복

청산: peak 대비 -1% (trailing)

단, ARM(무장) 이후에만 trailing 활성화

ARM 조건:
arm_pct = effective_gap + trailing_pct

3.2 시장가 사용 정책

저변동 구간에서만 시장가 허용

급변 감지 시 진입 금지

vol_1m <= VOL_OK → 시장가 허용
vol_10s > vol_60s * 2 → 급변 → 진입 금지

3.3 멀티 타임프레임 권한 구조
타임프레임	역할
1분	진입 트리거
5분	진입 허가
10분	지속성 필터
30분	브레이크(금지)

30분봉은 기다리는 용도 ❌,
매수 금지 조건만 담당 ⭕

3.4 Oracle(예언자)

결정권 ❌

역할:

진입 금지

조건 강화

사이즈 감소

신뢰도는 online scoring으로 갱신

4. 상태머신
IDLE
 └─(진입 조건)→ IN_POSITION
IN_POSITION
 └─(trailing hit)→ COOLDOWN
COOLDOWN
 └─(timeout)→ IDLE

5. 장애 대응

state.json 기반 복구

재시작 시:

포지션 없음 → IDLE

포지션 존재 → IN_POSITION 동기화