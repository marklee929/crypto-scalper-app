# Heart Beat Coin Scalper — Active Harness

## 문서의 역할

이 폴더는 앞으로 개발할 **S23 독립 실행형 Flutter 공지 반응 자동매매 앱**의 기준 문서다.

프로젝트 이력은 다음과 같이 구분한다.

```text
초기 Flutter 앱
  -> PC 기반 Python heart_beat_coin_scalper
  -> 현재: S23에서 독립 실행하는 신규 Flutter 앱
```

- `SRC/*_legacy`: 과거 구현을 참고하기 위한 읽기 전용 레거시 코드다.
- `DOC/legacy`: 과거 PC/Python 하네스와 작업 기록이다.
- `DOC/harness`: 현재 및 앞으로의 제품·아키텍처·개발 규칙이다.
- `production_demo.md`: 신규 아이디어가 출발한 관찰과 가설 원문이다. 확정 사양이 아니다.

현재 구현과 문서가 충돌하면 이 폴더의 번호가 붙은 문서를 우선한다. 번호 문서끼리 충돌하면 더 구체적인 문서를 우선하고, 해결되지 않으면 구현을 멈추고 결정 기록을 남긴다.

## 핵심 방향

1. 앱은 PC나 로컬 서버가 꺼져 있어도 S23에서 감시·기록·알림이 동작해야 한다.
2. 1차 제품은 업비트 신규 거래지원 공지를 감지해 조건부로 실주문하는 **자동매매 앱**이다.
3. 자동매매와 동시에 공지 및 해외 거래소 가격 반응 데이터를 반드시 수집한다.
4. Pattern Trading과 Event Trading은 데이터, 상태, 전략, 성과를 섞지 않는다.
5. 실주문은 활성 세션 안에서 모든 안전·신선도·가격 조건을 통과할 때만 자동 실행한다.
6. 주문 계약은 **시장가 매수 후 실제 체결 평균가로 목표 매도가를 계산하고, 해당 고정 가격으로 지정가 매도**하는 방식이다.

## 문서 지도

| 문서 | 통제 대상 |
|---|---|
| [production_demo.md](production_demo.md) | KMNO/BSB 관찰과 최초 가설 |
| [00_PRODUCT_NORTH_STAR.md](00_PRODUCT_NORTH_STAR.md) | 제품 정체성, 금지선, 성공 기준 |
| [01_SCOPE_AND_SUCCESS_GATES.md](01_SCOPE_AND_SUCCESS_GATES.md) | 현재 범위와 단계별 통과 조건 |
| [02_MOBILE_SYSTEM_ARCHITECTURE.md](02_MOBILE_SYSTEM_ARCHITECTURE.md) | Flutter/Android 구성과 시스템 경계 |
| [03_EVENT_DATA_CONTRACT.md](03_EVENT_DATA_CONTRACT.md) | 이벤트 상태, 시간, 저장 데이터 계약 |
| [04_ANDROID_RUNTIME_OPERATIONS.md](04_ANDROID_RUNTIME_OPERATIONS.md) | S23 장기 실행, APK 및 장애 운영 규칙 |
| [05_DEVELOPMENT_RULES.md](05_DEVELOPMENT_RULES.md) | 코드 변경·보안·테스트·완료 규칙 |
| [06_WORK_AREA_REGISTRY.md](06_WORK_AREA_REGISTRY.md) | 작업 영역과 위험도 |
| [07_DELIVERY_ROADMAP.md](07_DELIVERY_ROADMAP.md) | 구현 순서와 보류 결정 |
| [08_LEGACY_FLUTTER_GAP_ANALYSIS.md](08_LEGACY_FLUTTER_GAP_ANALYSIS.md) | 이전 Flutter의 한계와 신규 수용 기준 |
| [09_ORDER_EXECUTION_CONTRACT.md](09_ORDER_EXECUTION_CONTRACT.md) | 조건부 시장가 매수와 고정가 지정가 매도 계약 |
| [10_PHASE_1_APK_REPORT.md](10_PHASE_1_APK_REPORT.md) | 최초 Android runtime APK 구현·검증 보고 |

## 현재 기준선

```text
제품 단계        : 자동매매 설계 및 S23 실행 타당성 검증
대상 단말        : Samsung Galaxy S23, 충전 상태 상시 운용
배포 방식        : 로컬 빌드 APK 직접 설치 우선
운영 의존성      : S23 + 인터넷만 필수
주문 기능        : LIVE_GUARDED 조건부 실주문
매수/매도 계약   : MARKET BUY -> 계산된 고정가 LIMIT SELL
공지 원천        : pub-info.upbit.com 공개 announcements endpoint
시간 기준        : first_listed_at + 단말 최초 수신 시각 동시 저장
```

## 문서 변경 규칙

- 시장 관찰은 `production_demo.md` 또는 별도 실험 기록에 추가한다.
- 확정된 제품 규칙만 번호 문서에 반영한다.
- API endpoint, Android 정책, rate limit 같은 외부 사실에는 확인일과 공식 출처를 남긴다.
- 가설은 사실처럼 쓰지 않고 `가설`, `검증 필요`, `결정` 중 하나로 표시한다.
- 레거시 문서를 수정해 신규 정책처럼 사용하지 않는다.
