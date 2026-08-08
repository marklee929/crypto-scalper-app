# Scope and Success Gates

## 현재 활성 범위

### 포함

- Android/S23용 신규 Flutter 프로젝트 기반
- Android 장기 실행 서비스와 지속 알림
- 업비트 공지 소스 탐색 및 변경 감지
- 신규 거래지원 공지 분류와 심볼 추출
- Binance 현물 심볼 매핑 및 공개 시장 데이터 수집
- 거래소 계정 조회와 최소권한 주문 adapter
- 조건부 시장가 매수
- 실제 매수 체결가 기반 고정 목표가 계산과 지정가 매도
- 미체결 주문 및 보유 자산 reconciliation
- 로컬 영속 저장, 이벤트 replay, JSONL/CSV 내보내기
- 앱 상태 대시보드와 로컬 알림
- 네트워크/프로세스/재부팅 복구 실험
- APK 빌드 및 S23 직접 설치 검증

### 현재 제외 또는 보류

- 수익 보장 또는 자동 수익 최적화
- iOS, 웹, 데스크톱 제품화
- PC/Python 런타임을 필수 서버로 사용하는 구조
- 기존 Pattern Trading 로직의 신규 앱 이식
- Play Store 배포
- 출금 기능 및 출금 권한
- 공지 조건을 생략한 무조건 주문
- 계산 후 시장을 추종하며 계속 바꾸는 목표 매도가

## 단계와 통과 조건

### Gate 0 — Source Contract

목표: 공지 원천과 가격 원천이 실제로 수집 가능한지 증명한다.

통과 조건:

- 공지 기준 원천은 `https://pub-info.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all`이다.
- 인증 token 없이 접근되는 공개 응답의 요청 형식, 응답 샘플, 확인일을 기록한다.
- `data.notices[]`의 `id`, `uuid`, `title`, `category`, `listed_at`, `first_listed_at`를 contract fixture로 보관한다.
- 이용 조건과 rate limit을 검토한다.
- 동일 공지에 안정적인 식별자 또는 내용 hash를 만들 수 있다.
- 신규 거래지원 공지를 다른 공지와 구별하고 종목을 추출한다.
- Binance 심볼 목록과 매핑 성공/실패를 기록한다.
- 원천이 바뀌었을 때 실패가 명확히 노출된다.

### Gate 1 — S23 Sleep-mode Runtime

목표: 충전 상태 S23에서 장기 수집이 가능한지 측정한다.

통과 조건:

- 1시간 개발 실험과 24시간 soak test를 완료한다.
- 프로세스 종료, 네트워크 전환, 화면 꺼짐, 기기 수면 상태를 각각 시험한다.
- 충전 연결 상태에서 화면이 꺼진 동안에도 polling, WebSocket, DB heartbeat가 요구 주기를 지켜야 한다.
- heartbeat gap, 재연결 횟수, 배터리 사용량, 데이터 사용량을 기록한다.
- Android 버전별 foreground service 제한과 실제 서비스 유형을 문서화한다.
- 중단을 감지하지 못하는 silent failure가 없어야 한다.

24시간 성공 후 72시간 soak test를 다음 기준선으로 삼는다.

### Gate 2 — Auto-trading Core

목표: 저장된 fixture와 fake exchange로 전체 자동매매 계약을 재현한다.

통과 조건:

- 공지 원문에서 이벤트 생성까지 replay 테스트가 가능하다.
- 이벤트마다 raw/normalized/derived 데이터가 구분되어 저장된다.
- T0 전후 가격을 확보하거나, 확보하지 못한 이유가 기록된다.
- 앱 종료 후 재시작해도 중복 이벤트가 생기지 않는다.
- 화면과 내보내기 파일의 값이 저장소와 일치한다.
- 조건 충족 시 `MARKET BUY -> fill 확인 -> target 계산 -> LIMIT SELL` 순서를 지킨다.
- 조건 미충족 시 주문 없이 명확한 skip code로 종료한다.
- 부분 체결, 주문 거부, timeout, 앱 재시작을 fixture로 검증한다.

### Gate 3 — Paper and Evidence Review

목표: 자동화할 가치가 있는지 통계적으로 판단한다.

통과 조건:

- 분석에 사용할 최소 표본 수를 사전에 정한다.
- 성공/실패/무반응 이벤트를 모두 포함한다.
- latency bucket별 수익률, 최대 낙폭, 유동성, 체결 불확실성을 계산한다.
- 공지 감지 지연과 시장 반응 지연을 분리한다.
- 전략 폐기 조건을 충족하는지 검토한다.
- 동일한 rule engine이 fake execution과 live execution에서 다른 판단을 만들지 않는지 확인한다.

기본 최소 표본 수는 확정하지 않는다. 공지 빈도와 데이터 품질을 본 뒤 결정한다.

### Gate 4 — Live Guarded Execution

목표: 사용자가 시작한 활성 자동매매 세션에서 조건 충족 시 실주문을 수행한다.

통과 조건:

- fresh install에서는 사용자가 거래 세션과 1회 주문 예산을 명시적으로 설정한다.
- 세션이 활성화된 뒤에는 공지마다 사용자 확인을 요구하지 않고 조건에 따라 자동 주문한다.
- 매수는 시장가 주문으로 실행한다.
- 매수 주문의 실제 체결 평균가와 실제 체결 수량을 확인한다.
- 수수료, 목표 수익률, tick size를 반영해 단 하나의 고정 매도가를 계산한다.
- 매도는 계산된 가격의 지정가 주문으로 실행한다.
- 최대 1개 active position, 1회 주문 예산, 일일 손실/주문 횟수 한도, kill switch를 둔다.
- API key는 거래 최소권한만 사용하고 출금 권한을 허용하지 않는다.
- 모든 주문은 intent-first로 저장하며 exchange 응답과 local state를 reconciliation한다.

### Gate 5 — Live Recovery and Soak

목표: 화면이 꺼진 S23에서 실주문 상태를 잃지 않고 장기 운영한다.

통과 조건:

- 미체결 지정가 매도가 있는 상태에서 UI 종료와 process restart를 시험한다.
- 재시작 직후 exchange open order와 balance를 조회하기 전 신규 매수를 차단한다.
- 충전 분리, 네트워크 단절, API 오류 시 새 진입을 차단하고 기존 포지션 관리 상태를 유지한다.
- 24시간 및 72시간 soak에서 silent failure가 없다.

## 전략 폐기 또는 전환 조건

다음 중 하나면 해당 공지는 자동 매수하지 않고 `SKIPPED`로 저장한다.

- 시장 반응이 공지 감지보다 일관되게 먼저 발생한다.
- 공지 응답 schema가 검증 contract와 다르거나 `first_listed_at`이 유효하지 않다.
- 유효 구간이 모바일 네트워크와 Android 스케줄링 지연보다 짧다.
- 공지 최초 게시 후 허용 진입 시간이 지났다.
- 가격이 최대 허용 상승률 또는 spread/slippage 한도를 초과했다.
- 주문·계정·DB·시간 상태 중 하나라도 stale 또는 uncertain이다.
- 기존 position/open order/reconciliation 문제가 있다.
