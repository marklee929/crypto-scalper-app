# Android Runtime and Operations

## 운영 목표

충전기에 연결된 S23에서 화면이 꺼지고 기기가 수면 상태에 들어가도 **공지 polling, 시장 WebSocket, 주문 실행·조회, 로컬 저장, 알림**을 지속한다. 이것은 선택 기능이 아니라 production 필수 요구사항이다.

Android는 범용 서버 OS가 아니므로 구현 완료 판정은 코드 존재가 아니라 24시간·72시간 실기기 증거로 한다.

## Android 제약

확인일: 2026-08-08

- foreground service는 지속 알림을 표시해야 하며 서비스 유형과 권한 선언이 필요하다. [Android foreground service 선언](https://developer.android.com/develop/background-work/services/fgs/declare)
- Android 12 이상을 대상으로 하는 앱은 백그라운드에서 foreground service를 시작하는 데 제한이 있다. 감시는 사용자가 앱 화면에서 명시적으로 시작하는 흐름을 기본으로 한다. [백그라운드 시작 제한](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- Android 15 이상 대상 앱의 `dataSync` foreground service는 백그라운드에서 24시간당 총 6시간 제한을 받는다. 따라서 production 장기 실행 service를 단순 `dataSync` 유형으로 설계하지 않는다. [Foreground service timeout](https://developer.android.com/develop/background-work/services/fgs/timeout)
- `specialUse` 같은 다른 유형은 실제 use case와 배포 정책에 맞아야 한다. 직접 설치 APK라도 OS 동작을 실기기에서 검증해야 한다. [Foreground service 유형](https://developer.android.com/develop/background-work/services/fgs/service-types)
- foreground service만으로 화면이 꺼진 동안 CPU 실행이 보장되지는 않는다. active `LIVE_GUARDED` 자동매매 세션은 partial wake lock을 명시적으로 획득하고 세션 종료 시 해제한다. [Android wake lock 설명](https://developer.android.com/reference/android/os/PowerManager.html)
- 전원 연결 시 Android는 App Standby에서 앱을 해제하지만 Doze/제조사 정책과 실제 timer/network 동작은 별도 검증한다. [Doze와 App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)

## 첫 번째 기술 spike

신규 앱 기능보다 먼저 최소 monitoring prototype을 만든다.

prototype 기능:

- 사용자 조작으로 감시 시작/중지
- 지속 알림에 시작 시각, 마지막 heartbeat, 오류 상태 표시
- 정해진 주기의 작은 HTTPS 요청
- WebSocket 연결과 ping/pong
- 로컬 DB heartbeat 기록
- 프로세스와 device boot 식별자 기록
- 서비스 timeout/종료 callback 기록
- screen off 상태의 polling jitter와 WebSocket message gap 측정
- partial wake lock 획득 여부와 실제 보유시간 기록
- battery optimization 제외 여부와 Samsung background 설정 표시

실험 순서:

1. 화면 켠 상태 1시간
2. 화면 끈 상태 1시간 및 강제 Doze 진입
3. Wi-Fi에서 LTE/5G 전환
4. 네트워크 5분 차단 후 복구
5. 앱 UI swipe-away
6. 충전 상태 + 화면 off + LIVE_GUARDED 24시간 soak
7. 미체결 지정가 매도 존재 상태에서 UI 종료/process restart 복구
8. 재부팅 후 open order/balance reconciliation
9. 24시간 통과 후 72시간 soak

## 실기기 설정 기록

테스트 보고서에 다음을 반드시 적는다.

```text
device model
Android version / API level
One UI version
app version / build number
targetSdk / compileSdk
battery optimization state
isIgnoringBatteryOptimizations
partial wake lock state/held duration
background usage setting
network type
charger connected duration
test start/end UTC
```

설정을 바꿔 통과했다면 기본 설정에서도 통과한 것처럼 보고하지 않는다.

## Production 전원·수면 정책

- S23은 production 동안 충전 연결을 기본 조건으로 한다.
- 자동매매 세션 시작 전 battery optimization과 background 제한 상태를 검사한다.
- 필요한 설정이 아니면 신규 매수를 시작하지 않고 사용자에게 정확한 설정 항목을 표시한다.
- 화면이 꺼져도 foreground notification은 유지한다.
- `LIVE_GUARDED` session은 partial wake lock을 사용한다.
- wake lock은 자동매매 세션 중에만 유지하고 명시적 중지 시 즉시 해제한다.
- wake lock 누락·해제·재획득과 단말 온도를 health log에 기록한다.
- 충전이 분리되면 새 매수를 차단하고 경고한다. 기존 position과 open sell order는 reconciliation 및 보호 상태로 계속 관리한다.
- 전원 재연결 후 건강 상태와 reconciliation을 통과해야 신규 매수를 다시 허용한다.

## 건강 상태

```text
STARTING
HEALTHY
DEGRADED
STALE
STOPPING
STOPPED
FAILED
```

- `HEALTHY`: 공지 polling, 시장 연결, DB 기록이 SLA 안에서 성공
- `DEGRADED`: 일부 원천 실패지만 raw 오류와 재시도 진행 중
- `STALE`: 마지막 성공 시각이 SLA 초과
- `FAILED`: 저장 불가, 반복 파서 실패, 복구 불가 종료

SLA 숫자는 실제 polling 주기와 네트워크 실험 후 확정한다.

## 재연결과 복구

- 모든 네트워크 연결에는 connect timeout과 read timeout을 둔다.
- retry 횟수와 마지막 오류를 저장한다.
- WebSocket은 예상 종료 전 proactive reconnect 가능성을 검토한다.
- 재연결 시 gap 구간을 기록하고 가능한 범위에서 REST backfill한다.
- app/process 재시작 시 진행 중 이벤트를 읽고 `RECOVERING` 표시 후 재개한다.
- 복구 여부가 불명확하면 자동으로 `COMPLETE` 처리하지 않는다.
- 계정 balance와 open order 조회가 끝나기 전에는 신규 시장가 매수를 제출하지 않는다.

## APK 빌드 및 설치 완료 기준

개발 단계별 최소 확인:

```text
flutter analyze
flutter test
debug APK build
adb install/update
S23 launch smoke test
foreground notification 확인
화면 off/수면/Doze 확인
polling jitter와 WebSocket gap 확인
market buy/limit sell fake 또는 승인된 live smoke 확인
로그 및 DB 기록 확인
```

release APK는 signing, minify, 권한 목록, versioning을 별도로 검토한다. APK가 생성됐다는 사실만으로 S23 운영 검증이 완료된 것은 아니다.

## 운영 화면 필수 항목

- 서비스 상태
- 감시 시작 후 경과시간
- 마지막 공지 polling 성공/실패 시각
- 마지막 시장 데이터 시각
- 마지막 DB 기록 시각
- 누적 공지/이벤트/오류 수
- 재연결 횟수
- 충전 및 배터리 상태
- 앱 버전과 schema version
- 명시적 감시 중지 버튼
- LIVE_GUARDED 활성 여부와 1회 주문 예산
- 보유 수량, 평균 매수가, 고정 매도가, 주문 상태
- battery optimization/wake lock/충전 상태

## 장애 보고 원칙

장애 보고에는 최소한 다음을 포함한다.

```text
발생 UTC
마지막 정상 heartbeat
현재 service state
Android lifecycle event
network state
원천별 마지막 성공
재시도 횟수
데이터 gap 범위
복구 여부
```
