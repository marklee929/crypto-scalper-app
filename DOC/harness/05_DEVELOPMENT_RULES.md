# Development Rules

## 적용 범위

이 규칙은 신규 Flutter/Android 코드, 테스트, 스크립트, APK 설정, `DOC/harness` 변경에 적용한다. `SRC/*_legacy`와 `DOC/legacy`는 명시적인 이식 작업이 아니면 수정하지 않는다.

## 작업 시작 규칙

모든 변경은 먼저 다음을 선언한다.

```text
목적
활성 work area
변경 파일
위험도
외부 영향
완료 조건
```

요구사항이 불명확해도 안전한 조사·문서·테스트 범위는 진행할 수 있다. 주문 방식·금액·손실 제한 변경, secret, Android 핵심 권한, 데이터 삭제가 걸리면 영향과 검증 범위를 먼저 명시한다.

## 작업 모드

| 모드 | 허용 범위 |
|---|---|
| `READ_ONLY_AUDIT` | 파일·로그·설정 확인, 변경 없음 |
| `DOC_ONLY` | `DOC/harness` 문서만 변경 |
| `AUTOTRADE_BUILD` | 공지 감지부터 매수·매도까지 자동매매 구현 |
| `RUNTIME_GUARDED` | foreground service, boot, 권한, 배터리 관련 변경 |
| `DATA_MIGRATION` | 로컬 schema와 migration 변경 |
| `LIVE_GUARDED` | 조건부 실주문과 reconciliation 구현·검증 |

## 기본 안전 정책

- 공지 수집·분류와 주문 실행은 별도 package/boundary에 둔다.
- 실주문은 사용자가 시작한 `LIVE_GUARDED` 세션과 runtime guard를 모두 통과해야 한다.
- 화면 off 상태에서는 자동주문을 계속 허용하되 service health가 stale이면 새 매수를 금지한다.
- 앱 시작, 부팅, 복구 직후에는 reconciliation 완료 전 신규 자동주문을 금지한다.
- 실제 외부 주문을 발생시키는 테스트를 자동 실행하지 않는다.
- 공지 수집 실패 시 이전 결과를 새 공지처럼 재사용하지 않는다.
- DB 기록 실패 상태에서 정상 수집으로 표시하지 않는다.

## 주문 불변조건

```text
공지 조건 통과
-> BUY intent 저장
-> MARKET BUY 제출
-> exchange 최종 상태와 fills 확인
-> 실제 평균 체결가/실제 수량 확정
-> 고정 목표 매도가 계산 및 tick size 보정
-> SELL intent 저장
-> LIMIT SELL 제출
-> fill 또는 open order 상태 지속 추적
```

- `BUY intent` 저장 실패 시 매수 API를 호출하지 않는다.
- 시장가 매수의 예상 가격을 고정 매도가 계산에 사용하지 않는다.
- 매수 체결이 불확실하면 두 번째 매수를 시도하지 않고 `RECONCILIATION_REQUIRED`로 전환한다.
- 매도가는 계산 후 고정한다. trailing 또는 임의 재가격은 별도 전략 version 없이는 금지한다.
- 지정가 매도 미체결, 부분 체결, 취소, 거부에 대한 명시적 상태가 필요하다.
- position 또는 open order가 하나라도 불명확하면 신규 매수를 금지한다.
- 출금 기능과 출금 권한은 금지한다.

## Secret 규칙

- secret을 Git, 문서, 로그, fixture, screenshot, export에 넣지 않는다.
- `.env`, Android keystore, local properties의 실제 값은 커밋하지 않는다.
- 업비트 공개 공지와 공개 시세에는 인증정보를 보내지 않는다.
- 거래 API secret은 Android Keystore로 보호되는 저장 경계를 사용하며 일반 설정, DB, SharedPreferences에 평문 저장하지 않는다.
- 거래 key는 조회·현물거래 최소권한만 허용하고 출금 권한은 허용하지 않는다.
- 로그에는 token, Authorization header, 서명 원문을 기록하지 않는다.

## 데이터 규칙

- 저장 timestamp는 UTC epoch 기반으로 통일한다.
- 외부 원천 시각, 단말 수신 시각, 처리 완료 시각을 분리한다.
- raw -> normalized -> derived 순서를 지키며 raw 데이터를 덮어쓰지 않는다.
- parser와 metric에는 version을 둔다.
- 모든 이벤트 생성은 idempotent해야 한다.
- 데이터 gap과 불확실성을 0이나 정상값으로 채우지 않는다.
- schema 변경에는 forward migration과 이전 데이터 fixture 테스트가 필요하다.

## 네트워크 규칙

- endpoint, timeout, rate limit, retry 정책을 코드 상수로 흩뿌리지 않는다.
- HTTP status와 parsing 결과를 별도로 다룬다.
- exponential backoff, jitter, 최대 대기시간을 둔다.
- WebSocket 연결 상태와 데이터 freshness를 분리한다.
- endpoint/JSON schema 변경을 정상적인 실패 유형으로 취급한다.
- 외부 API integration test는 명시적으로 분리하고 unit test 기본 실행에 포함하지 않는다.

## Android 규칙

- foreground service 유형은 편의로 선택하지 않고 실제 use case와 공식 정책으로 정한다.
- 새 권한을 추가하면 목적, 화면 노출, 거부 시 동작, 제거 조건을 문서화한다.
- 서비스가 종료될 수 있다는 전제로 복구와 gap 기록을 구현한다.
- active 자동매매 세션은 화면 off/수면 상태에서도 실행되어야 한다.
- `LIVE_GUARDED` 세션은 partial wake lock을 사용하고 보유 시간과 해제 여부를 계측한다.
- 배터리 최적화 해제를 몰래 유도하거나 자동 변경하지 않는다.
- emulator 통과를 실기기 통과로 간주하지 않는다.

## 레거시 재사용 규칙

레거시는 아이디어와 테스트 케이스의 참고자료다. 파일 복사를 기본 전략으로 삼지 않는다.

재사용 전 확인:

```text
현재 제품 범위와 일치하는가
mobile lifecycle에서 안전한가
secret/live 기본값이 섞여 있지 않은가
동기 I/O나 무한 loop가 UI/service를 막지 않는가
테스트로 동작을 설명할 수 있는가
```

이식한 코드는 신규 namespace와 테스트 아래로 옮기며 레거시 파일을 직접 import하지 않는다.

## 테스트 계층

### Unit

- 공지 fixture parsing
- 공지 분류와 ticker 추출
- symbol collision/alias
- dedupe와 revision
- 상태 전이
- 시간 정규화와 metric

### Integration

- HTTP/WebSocket fake server
- DB insert/restart/migration
- reconnect와 gap/backfill
- export round-trip

### Device

- foreground service 시작/중지
- 화면 off, swipe-away, network switch
- 기기 수면/Doze 중 polling, WebSocket, 주문 조회
- process death와 recovery
- 24h/72h soak
- APK update 후 DB 보존
- fake exchange의 MARKET BUY 후 고정가 LIMIT SELL 순서
- 승인된 live smoke의 최소 주문 예산과 단일 position

외부 사이트의 현재 응답에 의존하는 테스트는 `live probe`로 분리한다.

## 완료 조건

코드 작업은 최소한 다음을 보고해야 완료다.

```text
변경 요약
변경 파일
실행한 analyze/test/build 명령
S23 검증 여부
외부 API 영향
secret/live order 영향
남은 위험과 다음 단계
```

테스트하지 않은 항목은 `미검증`으로 명시한다. 성공으로 추정하지 않는다.

## 중지 조건

다음 상황에서는 구현을 확대하지 않고 조사 결과와 결정 필요사항을 보고한다.

- 업비트 공개 공지 응답이 contract와 달라짐
- Android 서비스 유형이 use case와 맞지 않음
- 주문 금액·매도 계산식·손실 제한이 합의된 contract와 달라짐
- secret 노출 가능성이 있음
- schema 변경이 기존 데이터를 잃을 수 있음
- 레거시 이동 중인 사용자 변경과 충돌함
- 시간 품질이 latency 결론을 지지하지 못함
