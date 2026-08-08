PURPOSE FUNCTION:
heart_beat_coin_scalper의 PostgreSQL 기반 기록/복기/asset tracking 레이어를 추가하고, 기존 하네스 문서와 런타임 경계를 PostgreSQL-first 기준으로 동기화한다.

수익은 최대, 손실은 최소를 목표로 하되, 실주문보다 생존성·검증성·재현성·장부 정합성을 우선한다.

이번 작업의 목적은 매매 전략을 공격적으로 바꾸는 것이 아니다.
이번 작업의 목적은 다음이다.

1. PostgreSQL DB 아키텍처를 현행 하네스에 연결한다.
2. 15m / 30m / 1h / 4h candle, strategy decision, order intent, execution result, ledger snapshot, live asset snapshot, demo fake asset snapshot을 저장할 기반을 만든다.
3. demo / paper / live 결과가 섞이지 않게 한다.
4. live order와 local ledger가 어긋나는 경우 RECONCILIATION_REQUIRED로 멈출 수 있는 구조를 만든다.
5. API key / secret / .env 원문은 DB, 문서, 로그, 테스트에 절대 저장하지 않는다.
6. SQLite는 운영 기본 DB로 추가하지 않는다. 현재 운영 기준은 PostgreSQL이다.

AREA:
SYSTEM_ARCHITECTURE_DOCS + CODEX_HARNESS_DOCS + DATABASE_ARCHITECTURE + POSTGRES_STORAGE + RUNTIME_ENTRYPOINT + ORDER_GUARD + PAPER_LEDGER + STATE_RECOVERY + LOGGING_REPORTING + TESTS

MODE:
PHASED_EXECUTION

기본 phase mode:
- Phase 0: READ_ONLY_AUDIT
- Phase 1: DOC_ONLY
- Phase 2: GUARDED_FIX
- Phase 3: GUARDED_FIX
- Phase 4: GUARDED_FIX
- Phase 5: READ_ONLY_AUDIT 또는 GUARDED_FIX, 단 live order에는 연결 금지

FOCUS:
PostgreSQL-first DB 적용, 하네스 문서 동기화, 안전한 기록 레이어 추가, demo fake asset 추적, live asset snapshot 설계, order/ledger reconciliation guard 준비.

TIMEBOX:
각 phase는 독립적으로 45~90분 단위로 제한한다.
한 phase가 끝나면 보고서를 남기고, 다음 phase로 넘어가기 전에 stop condition을 확인한다.
마지막 10분에는 새 구현을 시작하지 않는다.

READ FIRST:
- README.md
- DOC/architecture/00_PRODUCT_NORTH_STAR.md
- DOC/architecture/01_SYSTEM_GROWTH_WORKFLOW.md
- DOC/architecture/02_DATA_SOURCE_AND_QUALITY.md
- DOC/architecture/03_SYSTEM_ARCHITECTURE.md
- DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
- DOC/architecture/05_CODEX_HARNESS_GUIDE.md
- DOC/architecture/06_WORK_AREA_REGISTRY.md
- DOC/architecture/07_HARNESS_RESTRUCTURE_REVIEW.md
- DOC/architecture/08_DATABASE_ARCHITECTURE.md
- run.py
- core/config.py
- core/candle_aggregator.py
- core/heartbeat.py
- core/market_structure.py
- core/state.py
- paper/ledger.py
- paper/report.py
- exchanges/binance/ws.py
- exchanges/binance/rest.py
- tests/test_candle_aggregator.py
- tests/test_market_structure.py
- tests/test_binance_exchange.py
- tests/test_run_guards.py

GLOBAL STOP CONDITIONS:
즉시 중단하고 Stop Report를 작성한다.

- 실제 Binance market order를 전송해야 한다.
- API key / secret / token 원문을 읽거나 출력하거나 문서/로그/테스트/DB에 저장해야 한다.
- config.yaml의 실제 secret 값을 수정해야 한다.
- live_order_enabled 값을 변경해야 한다.
- order size를 실거래 영향이 있게 변경해야 한다.
- Binance REST payload를 변경해야 한다.
- strategy hard exit를 약화해야 한다.
- confirmation count를 완화해야 한다.
- 기존 state.json 또는 거래 로그를 삭제해야 한다.
- DROP TABLE, TRUNCATE, destructive ALTER가 필요하다.
- SQLite를 운영 기본 DB로 추가하려 한다.
- demo fake asset과 live asset을 같은 테이블/상태로 섞어야 한다.
- PostgreSQL 연결 실패를 무시하고 live 주문을 계속 진행해야 한다.
- phase 범위 밖 파일을 수정해야 한다.
- 테스트 실패 원인이 현재 AREA 밖인데 억지로 고치려 한다.
- 구현이 추측에 의존한다.

GLOBAL FORBIDDEN:
- 실제 외부 주문
- 실제 API key/secret 출력
- `.env` dump
- raw secret DB 저장
- SQLite 운영 DB 도입
- live asset을 demo 결과로 갱신
- DB 오류를 fake success로 숨김
- 주문 성공/실패를 generic message로 뭉개기
- 기존 WorkConnect 용어를 이 프로젝트의 실행 규칙으로 되살리기
- Facebook / Telegram / Content Queue 같은 이전 프로젝트 모듈명을 현재 하네스 active AREA로 복구하기

GLOBAL REQUIRED REPORT:
각 phase 종료 시 다음을 보고한다.

- AREA
- MODE
- PURPOSE FUNCTION
- files inspected
- files modified
- tests/checks run
- command run
- DB touched 여부
- external API touched 여부
- actual order sent 여부
- secret exposure risk
- protected areas touched 여부
- state/log impact
- remaining risks
- next CODE_TASK_CANDIDATE

COMMIT RULE:
사용자가 명시적으로 커밋을 허용한 경우에만 phase별 commit을 수행한다.
커밋 전 반드시 diff를 검토하고 다음을 확인한다.

- raw secret 없음
- live order 전송 없음
- protected area 무단 변경 없음
- phase scope 안에 머묾
- 테스트 또는 skip reason 명확

PHASE 0: READ_ONLY_AUDIT — 현행 상태 재확인

AREA:
SYSTEM_ARCHITECTURE_DOCS + DATABASE_ARCHITECTURE + RUNTIME_ENTRYPOINT + ORDER_GUARD + TESTS

MODE:
READ_ONLY_AUDIT

PURPOSE FUNCTION:
현재 코드와 문서가 PostgreSQL-first DB 도입을 받을 준비가 되어 있는지 확인하고, 구현 전에 충돌 지점을 분류한다.

TASK:
1. README.md와 DOC/architecture/08_DATABASE_ARCHITECTURE.md를 읽고 현재 DB 방향이 PostgreSQL-first인지 확인한다.
2. DOC/architecture/03, 04, 05, 06에 08_DATABASE_ARCHITECTURE가 충분히 반영되어 있는지 확인한다.
3. 현재 코드에 DB 관련 모듈, migration runner, dependency 파일이 있는지 확인한다.
4. 현재 run.py 흐름에서 기록을 삽입하기 좋은 위치를 확인한다.
5. 현재 live order 위험 경로를 다시 확인한다.
6. 현재 state.json이 mode/symbol/exchange metadata를 갖는지 확인한다.
7. 현재 tests가 DB 없는 상태를 전제로 하는지 확인한다.

INSPECT:
- DOC/architecture/03_SYSTEM_ARCHITECTURE.md
- DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
- DOC/architecture/05_CODEX_HARNESS_GUIDE.md
- DOC/architecture/06_WORK_AREA_REGISTRY.md
- DOC/architecture/08_DATABASE_ARCHITECTURE.md
- run.py
- core/config.py
- core/state.py
- paper/ledger.py
- paper/report.py
- tests/

DO NOT MODIFY:
아무 파일도 수정하지 않는다.

OUTPUT:
Audit report를 작성한다.

보고서에는 반드시 다음을 포함한다.

1. 현재 DB 상태
2. 08_DATABASE_ARCHITECTURE와 03/04/05/06의 불일치
3. 구현 전 필요한 하네스 수정 목록
4. PostgreSQL dependency 후보
5. migration 위치 후보
6. DB 기록 삽입 위치 후보
7. live order 위험 경계
8. CODE_TASK_CANDIDATE 목록

STOP CONDITIONS:
- raw secret을 봐야 할 것 같으면 중단
- live 실행이 필요하면 중단
- 실제 DB 접속이 필요하면 중단

PHASE 0 COMPLETION REPORT:
- completed_at: 2026-06-22 KST
- AREA: SYSTEM_ARCHITECTURE_DOCS + DATABASE_ARCHITECTURE + RUNTIME_ENTRYPOINT + ORDER_GUARD + TESTS
- MODE: READ_ONLY_AUDIT
- result: completed without file/code/config/runtime changes
- DB touched: NO
- external API touched: NO
- actual order sent: NO
- secret exposure risk: LOW; config.yaml raw secret values were not opened or copied
- next phase: PHASE 1 DOC_ONLY — 하네스 문서 PostgreSQL 동기화

PHASE 1: DOC_ONLY — 하네스 문서 PostgreSQL 동기화

AREA:
SYSTEM_ARCHITECTURE_DOCS + CODEX_HARNESS_DOCS + DATABASE_ARCHITECTURE

MODE:
DOC_ONLY

PURPOSE FUNCTION:
08_DATABASE_ARCHITECTURE.md를 active harness 문서 세트에 연결하고, PostgreSQL-first 기준을 03/04/05/06에 반영한다.

TASK:
다음 문서를 수정한다.

1. DOC/architecture/03_SYSTEM_ARCHITECTURE.md
   - Document-to-Layer Control Map에 `08_DATABASE_ARCHITECTURE.md` 추가
   - PostgreSQL Storage Layer 추가
   - state/log와 PostgreSQL의 관계 명시
   - Data vs Decision vs Execution Boundary에 DB record 계층 추가
   - Target Architecture Direction에 PostgreSQL record/reconciliation 추가

2. DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
   - “현재 README 기준 핵심 DB는 없다” 문구를 현재 기준에 맞게 수정
   - 정확한 표현:
     현재 코드의 핵심 실행 경로는 아직 DB에 의존하지 않지만, 하네스 기준 DB 아키텍처는 PostgreSQL-first다.
   - PostgreSQL local server 사용 기준 추가
   - DATABASE_URL env 보호 규칙 추가
   - DB migration safety 추가
   - DB 연결 실패 시 demo/live 처리 원칙 추가
   - SQLite 운영 기본 DB 추가 금지 명시

3. DOC/architecture/05_CODEX_HARNESS_GUIDE.md
   - Protected examples에 PostgreSQL migration, live asset overwrite, fake/live asset mixing 추가
   - Work Modes에서 DOC_ONLY / GUARDED_FIX DB 작업 경계 추가
   - Trigger examples에 DB migration touched, DATABASE_URL exposure, live asset overwrite 추가
   - Completion Report에 DB touched 여부 추가

4. DOC/architecture/06_WORK_AREA_REGISTRY.md
   - AREA: DATABASE_ARCHITECTURE 추가
   - AREA: POSTGRES_STORAGE 추가
   - AREA: ASSET_TRACKING 추가
   - AREA: DB_MIGRATION 추가
   - 각 AREA에 allowed / forbidden / required checks / risk 추가
   - SQLite 운영 기본 DB 추가 금지
   - secret 원문 DB 저장 금지
   - destructive migration 금지
   - live asset과 demo fake asset 혼합 금지
   - future audit target에 PostgreSQL foundation 추가

5. DOC/architecture/07_HARNESS_RESTRUCTURE_REVIEW.md
   - DB 아키텍처 추가 이후 남은 보강점 업데이트
   - PostgreSQL-first 기준 반영
   - SQLite 일반론이 왜 제외되었는지 기록

ALLOWED FILES:
- DOC/architecture/03_SYSTEM_ARCHITECTURE.md
- DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
- DOC/architecture/05_CODEX_HARNESS_GUIDE.md
- DOC/architecture/06_WORK_AREA_REGISTRY.md
- DOC/architecture/07_HARNESS_RESTRUCTURE_REVIEW.md
- DOC/architecture/08_DATABASE_ARCHITECTURE.md only if typo/sync fix is needed

FORBIDDEN:
- runtime code
- config.yaml
- .env
- DB 접속
- migration 실행
- external API
- live order
- tests 수정

SUCCESS CRITERIA:
- 08_DATABASE_ARCHITECTURE가 03/04/05/06에 연결됨
- PostgreSQL-first 기준이 명확함
- SQLite 운영 기본 DB 금지가 명확함
- secret env only 정책 유지
- DB 작업 AREA가 06에 추가됨
- live order 보호영역이 약화되지 않음
- 기존 tracking-first strategy identity가 유지됨

REPORT:
수정한 문서와 추가한 섹션을 요약한다.

PHASE 1 COMPLETION REPORT:
- completed_at: 2026-06-22 KST
- AREA: SYSTEM_ARCHITECTURE_DOCS + CODEX_HARNESS_DOCS + DATABASE_ARCHITECTURE
- MODE: DOC_ONLY
- result: completed
- files modified:
  - DOC/architecture/03_SYSTEM_ARCHITECTURE.md
  - DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
  - DOC/architecture/05_CODEX_HARNESS_GUIDE.md
  - DOC/architecture/06_WORK_AREA_REGISTRY.md
  - DOC/architecture/07_HARNESS_RESTRUCTURE_REVIEW.md
- summary:
  - `08_DATABASE_ARCHITECTURE.md`를 active architecture map에 연결
  - PostgreSQL Storage Layer와 DB record/reconciliation 경계 추가
  - `DATABASE_URL` env 보호, forward-only migration, SQLite 운영 기본 DB 금지 명시
  - `DATABASE_ARCHITECTURE`, `POSTGRES_STORAGE`, `DB_MIGRATION`, `ASSET_TRACKING` AREA 추가
  - live asset과 demo fake asset 혼합 금지 및 destructive migration 보호영역 추가
- tests/checks run: documentation consistency/search checks only
- command run: read/search/patch/status commands only
- DB touched: NO
- migration touched: NO
- external API touched: NO
- actual order sent: NO
- secret exposure risk: LOW; raw config secrets were not opened or copied
- protected areas touched: documentation only; live order behavior untouched
- state/log impact: none
- stop conditions encountered: none
- next phase: PHASE 2 GUARDED_FIX — PostgreSQL foundation 구현

PHASE 2: GUARDED_FIX — PostgreSQL foundation 구현

AREA:
POSTGRES_STORAGE + DB_MIGRATION + CONFIG_AND_SECRETS + TESTS

MODE:
GUARDED_FIX

PURPOSE FUNCTION:
PostgreSQL 연결과 migration foundation을 추가하되, 전략/주문/live 경로에는 아직 연결하지 않는다.

TASK:
1. PostgreSQL storage package 추가
   후보 경로:
   - storage/__init__.py
   - storage/postgres.py
   - storage/migrations.py
   - storage/schema/
   - storage/schema/001_scalper_core.sql

2. DATABASE_URL env 로딩 추가
   - raw DATABASE_URL을 로그에 출력하지 않는다.
   - 연결 실패 시 password를 포함한 URL을 출력하지 않는다.
   - config.yaml에 DB password를 넣지 않는다.

3. Dependency 처리
   - 현재 dependency 관리 파일이 없으면 requirements.txt 추가를 검토한다.
   - PostgreSQL client는 `psycopg` v3 계열을 우선 검토한다.
   - dependency 추가가 필요하면 최소 의존성만 추가한다.
   - SQLite는 추가하지 않는다.

4. Migration runner 추가
   - forward-only migration
   - scalper schema 생성
   - migration history table 생성
   - 001 migration 적용 가능 구조
   - dry-run 또는 list mode 가능하면 추가
   - destructive migration 금지

5. 001 migration SQL 작성
   DOC/architecture/08_DATABASE_ARCHITECTURE.md 기준으로 최소 foundation을 만든다.

최소 테이블:
- scalper.schema_migration
- scalper.runtime_run
- scalper.runtime_config_snapshot
- scalper.market_candle
- scalper.strategy_decision
- scalper.order_intent
- scalper.execution_result
- scalper.live_asset_snapshot
- scalper.ledger_snapshot
- scalper.demo_fake_account
- scalper.demo_fake_asset_snapshot
- scalper.asset_reconciliation_event

6. Index 생성
   - market_candle(exchange, symbol, timeframe, open_time)
   - strategy_decision(run_id, decided_at)
   - order_intent(run_id, status)
   - execution_result(order_intent_id)
   - live_asset_snapshot(exchange, account_label, asset, is_latest)
   - demo_fake_asset_snapshot(fake_account_id, asset, is_latest)

7. Tests 추가
   - DB 연결이 없는 환경에서도 unit tests가 실패하지 않도록 한다.
   - migration SQL 파일 존재와 forbidden SQL 부재를 검증하는 테스트를 추가한다.
   - raw secret 문자열이 migration/config snapshot helper에 들어가지 않는지 테스트한다.
   - 실제 PostgreSQL 접속 테스트는 기본 unit test에서 제외한다.
   - DB integration test는 DATABASE_URL_TEST가 있을 때만 opt-in으로 실행한다.

ALLOWED FILES:
- storage/
- storage/schema/
- tests/
- requirements.txt 또는 pyproject.toml, 단 현재 프로젝트 구조에 맞출 것
- DOC/architecture/08_DATABASE_ARCHITECTURE.md, 구현 중 발견한 명백한 오타만

FORBIDDEN:
- run.py live order behavior 변경
- exchanges/binance/rest.py 변경
- config.yaml secret 변경
- actual DB migration 실행 without explicit command
- DROP TABLE / TRUNCATE
- SQLite 추가
- API key/secret 출력

REQUIRED CHECKS:
- migration SQL에 DROP TABLE 없음
- migration SQL에 TRUNCATE 없음
- migration SQL에 raw secret 필드 없음
- unit tests pass
- actual order sent: NO
- external API touched: NO

IMPLEMENTATION DETAIL:
storage/postgres.py는 다음 역할만 가진다.

- get_database_url_from_env()
- redact_database_url()
- connect() 또는 connection factory
- execute_migration()
- ensure_schema()
- optional health_check()

DATABASE_URL이 없을 때:
- import 실패하지 않는다.
- demo/test는 DB 없이 동작 가능해야 한다.
- live order 경로에 연결되는 작업은 아직 하지 않는다.

REPORT:
- 추가 파일
- dependency 변경
- migration 테이블 목록
- 테스트 결과
- DB 접속 여부
- secret 노출 여부

PHASE 2 COMPLETION REPORT:
- completed_at: 2026-06-22 KST
- AREA: POSTGRES_STORAGE + DB_MIGRATION + CONFIG_AND_SECRETS + TESTS
- MODE: GUARDED_FIX
- result: completed
- added files:
  - storage/__init__.py
  - storage/postgres.py
  - storage/migrations.py
  - storage/schema/001_scalper_core.sql
  - tests/test_postgres_storage.py
  - tests/test_postgres_migrations.py
  - requirements.txt
- dependency change:
  - added `psycopg[binary]>=3.2,<4`
- migration tables:
  - scalper.schema_migration
  - scalper.runtime_run
  - scalper.runtime_config_snapshot
  - scalper.market_candle
  - scalper.strategy_decision
  - scalper.order_intent
  - scalper.execution_result
  - scalper.live_asset_snapshot
  - scalper.ledger_snapshot
  - scalper.demo_fake_account
  - scalper.demo_fake_asset_snapshot
  - scalper.asset_reconciliation_event
- indexes:
  - idx_market_candle_symbol_tf_time
  - idx_strategy_decision_run_time
  - idx_order_intent_run_status
  - idx_execution_result_order
  - idx_live_asset_latest
  - idx_demo_fake_asset_latest
- tests/checks run:
  - `python -m unittest tests.test_postgres_storage tests.test_postgres_migrations -v`
  - `python -m unittest discover -v`
  - forbidden SQL/search checks on storage/tests
- test result: 39 tests passed
- DB touched: NO
- migration touched: SQL file only; no DB migration executed
- external API touched: NO
- actual order sent: NO
- secret exposure risk: LOW; raw config secrets were not opened or copied
- protected areas touched: no live order, no Binance REST behavior, no config.yaml secret change
- state/log impact: none
- stop conditions encountered: none
- next phase: PHASE 3 GUARDED_FIX — RuntimeRun / ConfigSnapshot 기록 연결

PHASE 3: GUARDED_FIX — RuntimeRun / ConfigSnapshot 기록 연결

AREA:
POSTGRES_STORAGE + RUNTIME_ENTRYPOINT + CONFIG_AND_SECRETS + STATE_RECOVERY + TESTS

MODE:
GUARDED_FIX

PURPOSE FUNCTION:
런타임 시작 시 PostgreSQL에 runtime_run과 secret 제외 config snapshot을 기록할 수 있게 한다. 아직 order execution 기록은 붙이지 않는다.

TASK:
1. Runtime DB recorder 추가
   후보 경로:
   - storage/runtime_repository.py
   - storage/db_recorder.py
   - storage/models.py if needed

2. runtime_run 생성 로직 추가
   - mode
   - exchange
   - market
   - symbol
   - quote_asset / base_asset if derivable
   - strategy_name
   - strategy_version
   - config_hash
   - live_order_enabled
   - status RUNNING

3. runtime_config_snapshot 저장
   - config_json은 secret 제외
   - binance_api_key / binance_api_secret / token / password / secret 류 key는 원문 제거
   - secret_fingerprint_json에는 존재 여부 또는 안전한 fingerprint만 저장
   - raw env dump 금지

4. run.py 연결
   - DB enabled 여부는 env 또는 config non-secret flag로 제어
   - DATABASE_URL 없으면 DB recorder는 disabled 상태로 동작
   - demo 실행은 DB disabled여도 깨지지 않는다.
   - live 실행에서 DB required 정책은 아직 적용하지 않는다. 단 문서에 future guard로 남긴다.

5. state.json metadata 후보
   - run_id
   - mode
   - exchange
   - symbol
   - strategy_version
   이 필드를 state snapshot에 추가할 수 있는지 검토한다.
   단 기존 restore를 깨지 않게 backward compatible하게 처리한다.

6. Tests
   - secret 제외 config snapshot 테스트
   - config_hash 안정성 테스트
   - DATABASE_URL 없을 때 DB disabled 테스트
   - runtime_run payload 생성 테스트
   - state restore backward compatibility 테스트

ALLOWED FILES:
- run.py
- core/config.py if non-secret config helper only
- core/state.py if backward compatible metadata only
- storage/
- tests/

FORBIDDEN:
- live order path 변경
- Binance REST payload 변경
- config.yaml actual secret 변경
- live_order_enabled 변경
- order size 변경
- hard exit 변경
- actual DB write test by default
- SQLite 추가

REQUIRED CHECKS:
- tests/test_run_guards.py
- new DB recorder tests
- no raw secret in test fixtures
- actual order sent: NO
- external API touched: NO

SUCCESS CRITERIA:
- DB recorder disabled mode에서 기존 demo/test 흐름이 유지됨
- DB recorder enabled mode의 payload 생성이 테스트됨
- secret 원문이 snapshot에 들어가지 않음
- state metadata 추가가 기존 state restore를 깨지 않음

STOP CONDITIONS:
- run.py 수정 중 live order behavior를 건드려야 하면 중단
- config.yaml 실제 값을 봐야 하면 중단
- DB 연결 실패를 live 주문 경로에서 무시하는 구조가 되면 중단

PHASE 3 COMPLETION REPORT:
- completed_at: 2026-06-22 KST
- AREA: POSTGRES_STORAGE + RUNTIME_ENTRYPOINT + CONFIG_AND_SECRETS + STATE_RECOVERY + TESTS
- MODE: GUARDED_FIX
- result: completed
- files modified:
  - run.py
  - storage/runtime_repository.py
  - tests/test_runtime_repository.py
- runtime changes:
  - runtime DB recorder factory added
  - DB recorder defaults to disabled unless `SCALPER_DB_ENABLED` or non-secret config flag enables it
  - `DATABASE_URL` absence yields disabled recorder metadata, not an import/runtime failure
  - secret-bearing config keys are excluded from config snapshot payload
  - safe fingerprints are generated without storing raw secret values
  - runtime metadata is saved under `state.json` payload key `runtime`
- tests/checks run:
  - `python -m unittest tests.test_runtime_repository tests.test_run_guards -v`
  - `python -m unittest discover -v`
- test result: 46 tests passed
- DB touched: NO
- migration touched: NO
- external API touched: NO
- actual order sent: NO
- secret exposure risk: LOW; raw config secrets were not opened or copied
- protected areas touched: no live order behavior, no Binance REST payload, no config.yaml change
- state/log impact: future state saves include backward-compatible `runtime` metadata
- stop conditions encountered: none
- next phase: PHASE 4 GUARDED_FIX — Candle / Decision / Ledger 기록 레이어 추가

PHASE 4: GUARDED_FIX — Candle / Decision / Ledger 기록 레이어 추가

AREA:
POSTGRES_STORAGE + CANDLE_AGGREGATOR + MARKET_STRUCTURE_STRATEGY + ORDER_GUARD + PAPER_LEDGER + LOGGING_REPORTING + TESTS

MODE:
GUARDED_FIX

PURPOSE FUNCTION:
전략 판단과 장부 결과를 PostgreSQL에 기록할 수 있게 하되, 전략 판단 자체와 live order behavior는 변경하지 않는다.

TASK:
1. market_candle 저장 함수 추가
   - 15m / 30m / 1h / 4h 저장 대상
   - 1m/raw tick은 기본 저장하지 않는다.
   - 현재 CandleAggregator는 60초 candle 중심일 수 있으므로, 15m 이상 저장은 별도 TimeframeAggregator 또는 exchange kline fetcher 후보로 분리한다.
   - 이 phase에서는 무리하게 실시간 15m aggregation을 완성하지 말고, 구조를 안전하게 만든다.
   - 구현 범위가 커지면 CODE_TASK_CANDIDATE로 분리한다.

2. strategy_decision 저장 함수 추가
   - HeartbeatStrategy.last_decision 구조를 받아 저장 payload 생성
   - event
   - market_state
   - sideways_state
   - score fields
   - reasons
   - confirmations
   - current_price
   - previous_low/high
   - support/resistance
   - raw_decision_json

3. ledger_snapshot 저장 함수 추가
   - Ledger.summary() 결과 기반
   - cash
   - position_qty
   - avg_price
   - realized_pnl
   - unrealized_pnl
   - fees_paid
   - slippage_paid
   - equity

4. run.py 연결
   - DB recorder가 enabled일 때만 append 기록
   - DB 기록 실패 시 demo는 warning + continue 가능
   - live mode에서는 아직 실주문 전 DB required 정책을 적용하지 않되, failure를 명확히 로그로 남긴다.
   - live order behavior는 절대 변경하지 않는다.

5. Tests
   - decision payload mapping test
   - ledger snapshot payload mapping test
   - DB disabled에서도 기존 tests 통과
   - DB recorder mock으로 insert 호출 순서 검증
   - closed candle이 있을 때만 decision 저장 후보가 생기는지 검증

ALLOWED FILES:
- run.py
- storage/
- tests/
- paper/ledger.py only if snapshot method가 backward compatible하게 필요할 때
- core/heartbeat.py only if reason visibility bug가 명확할 때, threshold 변경 금지

FORBIDDEN:
- strategy threshold 변경
- hard exit 변경
- confirmation count 변경
- live order 전송
- Binance REST payload 변경
- API key/secret
- 1m/raw tick 대량 저장 기본 활성화
- SQLite

REQUIRED CHECKS:
- tests/test_market_structure.py
- tests/test_run_guards.py
- new storage mapping tests
- actual order sent: NO
- external API touched: NO

STOP CONDITIONS:
- 15m/30m/1h/4h aggregation 설계가 현재 60초 CandleAggregator와 충돌하면 구현하지 말고 별도 CODE_TASK_CANDIDATE로 분리
- DB insert 실패를 조용히 무시해야만 구현 가능하면 중단

PHASE 4 COMPLETION REPORT:
- completed_at: 2026-06-22 KST
- AREA: POSTGRES_STORAGE + CANDLE_AGGREGATOR + MARKET_STRUCTURE_STRATEGY + ORDER_GUARD + PAPER_LEDGER + LOGGING_REPORTING + TESTS
- MODE: GUARDED_FIX
- result: completed with scoped implementation
- files modified:
  - run.py
  - storage/records.py
  - storage/runtime_repository.py
  - tests/test_storage_records.py
  - tests/test_runtime_repository.py
- implementation summary:
  - strategy_decision payload builder added
  - ledger_snapshot payload builder added
  - market_candle payload builder added for allowed storage timeframes only: 15m, 30m, 1h, 4h
  - run.py records decision and ledger snapshot only when a closed candle decision exists
  - disabled recorder remains no-op
  - DB record failure logs `[DB_RECORD_WARNING]` with error type only, without raw secret output
- scope note:
  - realtime 15m/30m/1h/4h aggregation was not implemented because current CandleAggregator is 60-second runtime focused
  - 1m/raw tick storage was not enabled
- tests/checks run:
  - `python -m unittest tests.test_storage_records tests.test_runtime_repository tests.test_run_guards -v`
  - `python -m unittest discover -v`
- test result: 50 tests passed
- DB touched: NO
- migration touched: NO
- external API touched: NO
- actual order sent: NO
- secret exposure risk: LOW; raw config secrets were not opened or copied
- protected areas touched: no strategy threshold, no hard exit, no confirmation count, no Binance REST payload, no config.yaml change
- state/log impact: future state saves still include runtime metadata; no existing state/log deletion
- stop conditions encountered: none
- next phase: PHASE 5 GUARDED_FIX — Demo Fake Asset Tracking

PHASE 5: GUARDED_FIX — Demo Fake Asset Tracking

AREA:
POSTGRES_STORAGE + PAPER_LEDGER + ORDER_GUARD + TESTS

MODE:
GUARDED_FIX

PURPOSE FUNCTION:
demo/paper 모드에서 실제 계좌를 건드리지 않고 가상 자산의 매수/매도 흐름을 PostgreSQL에 추적한다.

TASK:
1. demo_fake_account helper 추가
   - default fake account 생성 또는 조회
   - base_currency 기본 USDT
   - initial_cash 기록

2. demo_fake_asset_snapshot 저장
   - fake account별 asset latest snapshot
   - cash asset
   - position asset
   - valuation fields
   - is_latest 관리

3. demo order flow 기록
   - order_intent(mode=demo)
   - execution_result(status=FAKE_FILLED)
   - ledger_snapshot(mode=demo)
   - demo_fake_asset_snapshot 갱신

4. live asset과 완전 분리
   - demo는 live_asset_snapshot을 절대 쓰지 않는다.
   - fake asset에는 exchange API 응답을 넣지 않는다.
   - demo 결과를 live restore 기준으로 쓰지 않는다.

5. Tests
   - fake BUY 후 cash 감소, asset 증가
   - fake SELL 후 cash 증가, asset 감소
   - latest snapshot 하나만 유지하는 helper logic
   - live_asset_snapshot 호출 안 됨
   - no external API

ALLOWED FILES:
- storage/
- paper/
- run.py only if safe demo recorder connection needed
- tests/

FORBIDDEN:
- live asset 갱신
- Binance REST
- API key/secret
- live_order_enabled 변경
- actual account balance 조회
- actual order

REQUIRED CHECKS:
- fake asset tests
- tests/test_run_guards.py
- actual order sent: NO
- external API touched: NO

SUCCESS CRITERIA:
- demo fake asset이 live asset과 분리됨
- fake buy/sell 추적 가능
- ledger snapshot과 fake asset snapshot이 같은 run_id로 묶임

PHASE 5 COMPLETION REPORT — 2026-06-22

- mode: GUARDED_FIX
- completed scope:
  - added `storage/fake_assets.py` helper for demo fake cash/position snapshots
  - added latest snapshot tracker logic that marks previous same fake_account/asset snapshots as not latest
  - added demo fake account get/create helper in PostgreSQL runtime recorder
  - added demo-only execution flow recording:
    - `order_intent(status=FAKE_FILLED)`
    - `execution_result(status=FAKE_FILLED, raw_response_json=NULL)`
    - execution-linked `ledger_snapshot`
    - `demo_fake_asset_snapshot` latest update
  - wired demo/paper/backtest runtime flow after paper ledger BUY/SELL events only
  - avoided duplicate ledger snapshots when the demo execution flow already recorded the execution-linked ledger snapshot
  - added tests for fake BUY, fake SELL, latest helper, and demo flow separation from live asset snapshot
- files changed:
  - `storage/fake_assets.py`
  - `storage/runtime_repository.py`
  - `run.py`
  - `tests/test_fake_assets.py`
  - `tests/test_runtime_repository.py`
- tests/checks run:
  - `python -m unittest tests.test_fake_assets tests.test_runtime_repository tests.test_run_guards -v`
  - `python -m unittest discover -v`
- test result: 54 tests passed
- DB touched: NO
- migration touched: NO
- external API touched: NO
- actual order sent: NO
- live asset updated: NO
- Binance REST payload changed: NO
- `live_order_enabled` changed: NO
- config secret touched: NO
- secret exposure risk: LOW; raw config secrets were not opened or copied
- protected areas touched: no strategy threshold, no hard exit, no confirmation count, no Binance account balance lookup, no Binance REST order payload change, no `config.yaml` change
- state/log impact: future demo trade ticks may add PostgreSQL demo fake records only when DB is explicitly enabled; existing state/log files were not deleted
- stop conditions encountered: none
- next phase: PHASE 6 READ_ONLY_AUDIT — Live Asset Snapshot / Reconciliation Guard 설계

PHASE 6: READ_ONLY_AUDIT 먼저 — Live Asset Snapshot / Reconciliation Guard 설계

AREA:
ASSET_TRACKING + ORDER_GUARD + BINANCE_REST_EXECUTION + POSTGRES_STORAGE + STATE_RECOVERY

MODE:
READ_ONLY_AUDIT first

PURPOSE FUNCTION:
실계좌 자산 snapshot과 order/ledger reconciliation guard를 설계하되, 실제 Binance account API 호출 또는 live order 변경은 하지 않는다.

TASK:
1. 현재 BinanceRestClient가 account balance 조회 기능을 갖고 있는지 확인한다.
2. 없다면 추가 구현하지 말고 설계 후보만 작성한다.
3. live order 성공 후 ledger 반영 실패 위험을 다시 확인한다.
4. RECONCILIATION_REQUIRED 상태를 어디에 기록할지 설계한다.
5. 다음 자동 주문을 어떻게 중단할지 설계한다.
6. live_asset_snapshot 갱신을 언제 수행할지 설계한다.
7. account API는 PROTECTED_CHANGE인지 분류한다.

OUTPUT:
CODE_TASK_CANDIDATE report 작성.

보고서 필수 항목:
- 필요한 Binance account endpoint 후보
- secret/API key handling risk
- live asset snapshot write path
- order success + ledger failure scenario
- RECONCILIATION_REQUIRED propagation path
- required tests
- protected approvals needed

DO NOT IMPLEMENT YET:
- Binance account API
- REST client account endpoint
- live order path
- live asset write from actual exchange
- reconciliation stop behavior in live

STOP CONDITIONS:
- account API 호출이 필요하면 중단
- secret이 필요하면 중단
- live order path 수정이 필요하면 중단

PHASE 7: 전체 정리 및 Closeout

AREA:
CODEX_HARNESS_DOCS + TESTS + POSTGRES_STORAGE + LOGGING_REPORTING

MODE:
READ_ONLY_AUDIT + DOC_ONLY if needed

PURPOSE FUNCTION:
DB 적용, 하네스 수정, runtime 변경이 서로 일관되는지 최종 점검한다.

TASK:
1. DOC/architecture/03/04/05/06/08 일관성 확인
2. SQLite 운영 DB 언급이 남아 있는지 검색
3. WorkConnect 잔재 용어가 active rule에 남아 있는지 검색
4. secret 저장 금지 정책이 코드/문서/테스트에 일관되는지 확인
5. PostgreSQL DATABASE_URL redaction 확인
6. run.py live order behavior가 변경되지 않았는지 확인
7. tests 전체 또는 관련 subset 실행
8. final report 작성

REQUIRED SEARCHES:
- SQLite
- WC_EXECUTION_COMPLETE
- WorkConnect
- Facebook
- Telegram
- CONTENT_QUEUE
- raw secret
- BINANCE_API_KEY
- BINANCE_API_SECRET
- DATABASE_URL

주의:
BINANCE_API_KEY / BINANCE_API_SECRET 검색은 key 이름 존재 확인만 한다.
실제 값이 출력될 가능성이 있으면 즉시 중단하고 redaction report만 작성한다.

SUCCESS CRITERIA:
- PostgreSQL-first 기준 확정
- 하네스 문서 동기화
- DB foundation 구현 또는 phase별 구현 완료
- secret 노출 없음
- live order 전송 없음
- tests 통과 또는 skip reason 명확
- 다음 protected task가 명확히 분리됨

FINAL REPORT FORMAT:
# PHASED EXECUTION REPORT

## 1. 결론 요약
## 2. 실행한 Phase
## 3. 수정 파일 목록
## 4. 추가 파일 목록
## 5. DB 변경 요약
## 6. Migration 요약
## 7. Secret 보호 결과
## 8. Live order 영향
## 9. Demo / fake asset 영향
## 10. Tests / Checks
## 11. Stop Conditions Encountered
## 12. Remaining Risks
## 13. Next CODE_TASK_CANDIDATE

[SCALPER_EXECUTION_COMPLETE]
