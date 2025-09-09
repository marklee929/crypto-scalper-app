# 🎯 앱 방향성 (Product Direction)

* **목표:** “수익 최대 · 손실 최소” 원칙을 앱 UX/알림/가드에 일관되게 반영. (Coinone API **v2.1** 기준)
* **역할:** 자동매매 엔진(백엔드/루프)은 계속 돌고, **앱은 제어판 + 관제실**. 화면 전환/앱 백그라운드 상태에서도 루프는 지속.
* **핵심 가치:** (1) 즉시성(1초 내 체감 응답), (2) 가시성(상태/로그/포지션 한눈), (3) 안전성(가드/쿨다운/전량정리 버튼 보호장치).

---

# ✅ 현재 구현/상태 요약 (as of 2025-08-13 KST)

* **권한/푸시:** `permission_handler`, `flutter_local_notifications` 초기화 완료. (안드로이드 로컬푸시)
* **대시보드 스캐폴딩:** `DashboardScreen` 존재.
* **자동루프 방향:** 화면과 독립 실행(싱글톤 서비스 + 타이머/스트림 루프).
* **전략/가드(설계 반영):** `sell_memory_guard`, `cooldown_filter`, `reentry_on_dip`, `volume_spike_exit`, `waiting_zone_filter` 노출 예정.
* **로그 콘솔 요구:** tail -f 스타일 실시간 + 과거 검색/스크롤, 상/하단 토스트.
* **입력값:** `targetCoin` 수동 입력 → 자동매매 시작 시 필수. 앱 재시작 시 복원.
* **매매:** `buyAll / sellAll` 전액/전량 고정 (수량 파라미터 제거).

> 주: 백엔드 루프(Python/서버 or Dart 서비스)가 이미 존재/진행 중이라는 전제. 앱은 REST/WS 브릿지로 붙거나, 단일 앱 내 서비스로 붙음.

---

# 🏗 아키텍처 제안 (앱 레이어)

```
lib/
  screens/
    dashboard_screen.dart        # 요약·액션
    log_view_screen.dart         # 실시간/과거 로그
    settings_screen.dart         # API키/전략토글/임계치
  services/
    auto_trade_service.dart      # 루프·상태·액션(싱글톤)
    coinone_api.dart             # v2.1 REST/WS 어댑터
    notification_service.dart    # 로컬푸시/요약전송
    storage_service.dart         # settings.json, 로그 핸들러
  controllers/
    log_console_controller.dart  # tail -f, pagination, 검색
    app_state.dart               # 글로벌 요약(보유/현금/가격/추세)
  utils/
    log.dart                     # 레벨/색상/필터
    format.dart                  # 숫자/시간 포맷
```

* **실행모델:** 앱 내 **싱글톤 서비스 + Timer.periodic(1s)** 또는 **Stream**. 장기적으로 Android Foreground Service 이관 고려.
* **상태관리:** 당장은 `ChangeNotifier` 기반(가볍고 빠름) → 추후 Riverpod 전환 옵션 열어둠.
* **이벤트 버스:** 서비스→UI 브로드캐스트(스트림)로 최소 전달 지연.

---

# 🔌 API 계약 (Coinone v2.1 기준 초안)

* **시세:** `/ticker`, `/candles/{interval}` (1m/30m/1h/1d)
* **계좌/자산:** `/account/balance`
* **주문:** `/order/limit`, `/order/market`, `/order/cancel`, `/order/status`
* **주의:** 호출 제한/에러코드 맵핑 테이블을 `coinone_api.dart`에 캡슐화. 재시도/백오프 포함.

---

# 🧩 핵심 기능 요건 (UI/UX)

## 1) 대시보드

* 현재가·수익률·보유 수량·가용 KRW·추세/상대위치(1h/1m 혼합) 즉시 표시
* 액션: **자동매매 시작/중지**, **전량 매도(Confirm 2-step)**, **전액 매수(임계치 확인)**
* `targetCoin` 입력 + **유효성 검사** + **자동 저장**

## 2) 로그 뷰어 (tail -f + 과거)

* 실시간 스트림 표시(레벨별 색상)
* 첫 로딩 **30줄** → 상/하 이동 시 **+N줄** 증감
* 검색/필터(레벨, 텍스트, 기간)
* 최상/최하 도달 시 토스트: “여기가 처음/마지막입니다.”

## 3) 알림/요약

* 체결/손절/가드 발동/추세 변화 시 **요약 푸시** (중복 전송 방지 키: `trend:pos:price`)
* 에러/재시도/토큰 만료 등 중요 이벤트 푸시

## 4) 설정

* API 키, 슬리피지/임계치, 전략 토글(가드/쿨다운/재진입 허용 등)
* `settings.json` 로컬 저장 + 즉시 반영

---

# 🛡 리스크/가드 노출 정책

* **sell\_memory\_guard:** 동일 고가 재진입 금지(최근 고점/기간 표기)
* **cooldown\_filter:** 체결 후 N분 재진입 제한(남은 시간 표시)
* **reentry\_on\_dip:** 급등 후 눌림 진입 허용(조건식 표시)
* **volume\_spike\_exit:** 거래량 급증시 익절/이탈(스파이크 판단 로그 주석으로)
* **waiting\_zone\_filter:** 변동성 과도 구간 진입 제한

각 가드는 **스위치 + 파라미터** 노출, 대시보드에 현재 활성 상태/사유 표시.

---

# ⚙️ 성능/안정성 가이드

* 로그 뷰: 큰 파일 직접 전체 로딩 금지 → **파일 핸들 유지 + 오프셋 기반 슬라이스**
* I/O는 **Isolate** 또는 비동기 처리. UI 프레임 드랍 방지.
* API 백오프/재시도 + 지수 대기 + 오류 누적시 일시 정지(알림 전송).
* 앱 포그라운드/백그라운드 전환에도 루프 유지(싱글톤/Service).

---

# 🧪 테스트 플랜

* **단위:** 포맷터/계산/가드 조건식/스파이크 판단
* **통합:** 가짜 API로 체결→로그→푸시 파이프라인
* **시뮬:** 과거 캔들로 루프 10분간 재생, 경계 케이스 회귀

---

# 📦 배포/운영 노트

* 당분간 **DEV 빌드** (내부 배포). 릴리즈 전 Foreground Service/WorkManager 검토.
* 비공개 `secrets.json` 분리. 로그에 키/민감값 노출 금지.

---

# 🗺 로드맵 & 백로그 (우선순위)

**P0 (이번 스프린트)**

1. `AutoTradeService` 루프 독립 실행 + 상태 스트림 (1s)
2. 대시보드 MVP(요약·액션·targetCoin 저장/복원)
3. 로그 뷰어 tail -f + 30줄 페이징 + 상/하단 토스트
4. 체결/에러 로컬푸시(중복 방지 키)

**P1**
5\. 가드/전략 토글 UI + 현재 상태 표시
6\. 캔들 뷰(1m/1h) 미니차트 + 상대위치 표시
7\. 설정 화면 전체(임계치/쿨다운/슬리피지)

**P2**
8\. Android Foreground Service 전환(장시간 안정성)
9\. 성능 프로파일링(스크롤/파일 I/O)
10\. 백테스트 리플레이(샌드박스)

---

# 🧱 파일별 작업 가이드 (Copilot 적용용 헤더 포함)

> 아래 블록을 각 파일 상단에 붙이면 Copilot이 정확히 그 파일에 제안/적용하기 쉬워집니다.

```dart
// filepath: lib/services/auto_trade_service.dart
// role: 1초 루프, 상태 스트림, buyAll/sellAll, 가드 적용
```

* \[TODO]

  * 싱글톤 구현, `start() / stop()`
  * `Stream<AppState>` 브로드캐스트
  * 체결 시 `NotificationService.sendTradeSummary()` 호출
  * 중복 전송 방지 키 로직 포함

```dart
// filepath: lib/services/coinone_api.dart
// role: Coinone v2.1 REST/WS 캡슐화, 백오프/재시도
```

* \[TODO]

  * `getTicker(symbol)`, `getCandles(symbol, interval, limit)`
  * `getBalance()`, `orderMarketBuyAll(symbol)`, `orderMarketSellAll(symbol)`
  * 에러코드 맵/재시도 정책

```dart
// filepath: lib/controllers/log_console_controller.dart
// role: tail -f, 페이징(±N줄), 검색, 최상/최하 토스트
```

* \[TODO]

  * 파일 핸들/오프셋 유지, `appendLive(line)`
  * `loadInitial(30)`, `loadMoreTop(N)`, `loadMoreBottom(N)`
  * `isAtTop/Bottom` 판단 → 토스트 트리거

```dart
// filepath: lib/screens/dashboard_screen.dart
// role: 요약 뷰 + 액션 + targetCoin 입력/저장
```

* \[TODO]

  * 현재가/보유/KRW/수익률/추세 표시
  * 시작/중지, 전액 매수, 전량 매도(2-step 확인)
  * `targetCoin` 필수 검사 + 즉시 저장/복원

```dart
// filepath: lib/services/notification_service.dart
// role: 로컬푸시, 요약 템플릿, 중복방지 키
```

* \[TODO]

  * `init()`, `sendTradeSummary(trend, pos, price, krw, qty)`
  * `lastKey` 비교로 스팸 방지

```dart
// filepath: lib/services/storage_service.dart
// role: settings.json, 간단 KV, 로그 경로 유틸
```

* \[TODO]

  * `readSettings()/writeSettings()`
  * `getLogsDir()` 등 경로 관리

````

---

# 🧾 상태 모델 초안
```dart
class AppState {
  final String symbol;          // targetCoin
  final double? currentPrice;   // 실시간
  final double? avgCost;        // 평균단가
  final double qty;             // 보유수량
  final int krw;                // 가용 현금
  final String trend;           // 상승/하락 등
  final double relativePos;     // 0.0~1.0 상대위치(1h/1m 혼합)
  final bool running;           // 루프 실행 여부
  const AppState({
    required this.symbol,
    this.currentPrice,
    this.avgCost,
    required this.qty,
    required this.krw,
    required this.trend,
    required this.relativePos,
    required this.running,
  });
}
````

---

# 🔐 에러/예외 공통 처리

* **인증 만료:** 토큰 리프레시 → 재시도, 실패시 루프 일시정지 + 알림
* **호출 실패 반복:** 지수 백오프 + 회로차단(일정 시간 skip) + 알림
* **체결 지연/거부:** 즉시 알림 + 재시도 정책 명시

---

# 🧰 개발 워크플로 (권장)

1. P0 파일 먼저 생성(상단 Copilot 헤더 추가)
2. `AutoTradeService.start()`로 더미 티커(모의)부터 연결 → 대시보드에 반영
3. 로그 컨트롤러 붙여 tail -f 안정화
4. 체결 이벤트 → 푸시 → 대시보드 지표 동기화

---

# 📎 Copilot 컨텍스트용 요약 프롬프트 (붙여넣기)

> **프로젝트 컨텍스트**: Flutter 앱은 Coinone API v2.1을 사용해 코인 자동매매 엔진을 제어/모니터링한다. 루프는 화면과 독립 실행되며, 대시보드에서 상태·액션을 제공한다. 로그는 tail -f UX, 알림은 체결/오류/추세변화에 한해 발송한다. 매수/매도는 전액/전량 고정이며, 가드(cooldown, sell\_memory\_guard 등)는 UI에서 토글/파라미터로 노출한다.
>
> **우선 작업(P0):**
>
> * `auto_trade_service.dart`에 1초 루프 + 상태 스트림 + 액션 구현
> * `dashboard_screen.dart`에 요약/액션 + targetCoin 저장/복원
> * `log_console_controller.dart`에 tail -f + 30줄 페이징 + 상/하단 토스트
> * `notification_service.dart`에 중복 방지 키 포함 요약 푸시
>
> **파일 헤더 규칙:** 각 파일 상단에 `// filepath: <경로>` 주석을 포함해 제안/적용 정확도를 높인다.

---

# 🧩 열어둔 선택지

* 상태관리 Riverpod 전환, Foreground Service 채택, 백테스트/리플레이 샌드박스 분리, 차트 라이브러리(Recharts/CanvasKit) 비교 검토.

---

# 📌 체크리스트 (P0 완료 정의)

* [ ] 대시보드에서 **시작/중지/전량매도/전액매수** 동작 확인
* [ ] 앱 백그라운드에서도 루프 유지, 10분 스트레스 테스트 통과
* [ ] 로그 뷰어: 초기 30줄, 상/하단 이동, 검색 동작
* [ ] 체결/오류 푸시 중복 차단 정상 동작
* [ ] `targetCoin` 비어있을 때 시작 차단 + 저장/복원 확인
