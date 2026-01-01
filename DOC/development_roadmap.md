개발 순서/마일스톤

# Development Roadmap

## Phase 0 – 정리
- Repo 초기화
- 레거시 코드 분리/동결
- SSH / Git 환경 안정화

---

## Phase 1 – Paper Engine (Week 1)
- ledger.py
- report.py
- state persistence
- 정각 리포트

---

## Phase 2 – Heartbeat Core (Week 2)
- IDLE/IN_POSITION/COOLDOWN
- ARM + trailing
- sell memory guard

---

## Phase 3 – Multi Timeframe Guard (Week 2)
- 1/5/10/30 분봉
- EMA slope / 구조적 하락 감지

---

## Phase 4 – Oracle (Optional) (Week 3)
- Risk scoring
- 신뢰도 업데이트
- 진입 제어만 담당

---

## Phase 5 – Exchange Integration (Week 3)
- Coinone REST v2.1
- 실데이터 paper trading

---

## Phase 6 – Small Live (Week 4)
- 소액 실주문
- 손실 제한
- 자동 정지 조건

---

## Phase 7 – 안정화
- 파라미터 튜닝
- 로그 분석
- 전략 고정

++ 추가로 남겨둘 포인트 (아직 미구현)
++ 시장가 대신 "유사 시장가(IOC/최소 슬리피지)" 전략
++ 장중/장외 시간대별 파라미터 분리
++ 변동성 regime 자동 분류
++ 다중 코인 확장 여부
++ 리포트 시각화(주간/월간)
++ 전략 버전 태깅 및 성과 비교