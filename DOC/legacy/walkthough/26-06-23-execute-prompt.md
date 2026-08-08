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

PURPOSE FUNCTION:
heart_beat_coin_scalper의 safe demo 실행에서 config.yaml의 live_order_enabled=True 때문에 BinanceRestClient가 없다는 RuntimeError가 발생하는 문제를 수정한다.

수익은 최대, 손실은 최소를 목표로 하되, 실주문보다 생존성·검증성·모드 안전성을 우선한다.

이번 수정의 핵심 목적:
- demo / paper / backtest 모드에서는 live_order_enabled=True가 config.yaml에 있어도 절대 실주문 경로를 타지 않는다.
- live 주문은 반드시 --live 명시 + runtime mode live + live_order_enabled=True + BinanceRestClient 존재 조건을 모두 만족해야만 가능하다.
- run.bat 기본 실행은 계속 안전한 demo pump 로그 확인용이어야 한다.
- API key / secret 원문은 출력하거나 문서/로그/테스트에 저장하지 않는다.

AREA:
RUNTIME_ENTRYPOINT + ORDER_GUARD + CONFIG_AND_SECRETS + TESTS

MODE:
GUARDED_FIX

FOCUS:
demo mode에서 live_order_enabled=True 설정값이 실주문 가드를 통과하지 못하게 runtime mode 기반 order guard를 추가한다.

READ FIRST:
- DOC/architecture/00_PRODUCT_NORTH_STAR.md
- DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
- DOC/architecture/05_CODEX_HARNESS_GUIDE.md
- DOC/architecture/06_WORK_AREA_REGISTRY.md
- run.py
- run.bat
- core/config.py
- tests/test_run_guards.py

BUG CONTEXT:
현재 run.bat 기본 실행은 다음처럼 safe demo pump로 들어간다.

```bat
--mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump
```

GUARDED_FIX COMPLETION REPORT — 2026-06-23

- AREA: RUNTIME_ENTRYPOINT + ORDER_GUARD + CONFIG_AND_SECRETS + TESTS
- MODE: GUARDED_FIX
- PURPOSE FUNCTION: safe demo 실행에서 `live_order_enabled=True` 설정값이 실주문 가드를 통과하지 못하게 runtime mode 기반 order guard를 추가한다.
- files inspected:
  - `DOC/architecture/00_PRODUCT_NORTH_STAR.md`
  - `DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md`
  - `DOC/architecture/05_CODEX_HARNESS_GUIDE.md`
  - `DOC/architecture/06_WORK_AREA_REGISTRY.md`
  - `DOC/walkthough/26-06-23-execute-prompt.md`
  - `run.py`
  - `run.bat`
  - `core/config.py`
  - `tests/test_run_guards.py`
- files modified:
  - `run.py`
  - `tests/test_run_guards.py`
  - `DOC/walkthough/26-06-23-execute-prompt.md`
- implementation summary:
  - `_place_live_order_if_enabled()`에 `runtime_mode` 조건을 추가했다.
  - runtime mode가 `live`가 아니면 `live_order_enabled=True`여도 실주문 client를 요구하거나 호출하지 않는다.
  - `_process_tick()`은 `runtime_metadata.mode`를 기준으로 BUY/SELL 실주문 guard를 호출한다.
  - runtime metadata가 없으면 안전 기본값 `demo`로 처리한다.
  - direct live guard 호출은 기존처럼 `runtime_mode=live` 기본값을 유지해 `live_order_enabled=True`와 client 없음이면 RuntimeError를 발생시킨다.
  - live runner test에서 실제 coroutine warning이 생기지 않도록 `run_live`를 일반 mock으로 고정했다.
- tests/checks run:
  - `python -m unittest tests.test_run_guards -v`
  - `python -m unittest discover -v`
  - `git diff -- run.py tests\test_run_guards.py --check`
- test result:
  - `tests.test_run_guards`: 16 tests passed
  - full unittest discover: 60 tests passed
- DB touched: NO
- external API touched: NO
- actual order sent: NO
- Binance REST payload changed: NO
- `live_order_enabled` config value changed: NO
- config.yaml touched: NO
- API key/secret exposure risk: LOW; raw secret values were not opened or copied
- protected areas touched:
  - ORDER_GUARD changed only to add runtime-mode narrowing
  - BINANCE_REST_EXECUTION request payload and client code were not changed
- state/log impact:
  - no existing state/log deletion
  - safe demo path can continue writing demo runtime state/logs under configured output paths
- remaining risks:
  - `config.yaml` may still contain `live_order_enabled=True`, but demo runtime now ignores it for actual order execution.
  - live mode still intentionally requires `--live`, runtime mode `live`, `live_order_enabled=True`, and a configured BinanceRestClient/API credentials.
- stop conditions encountered: none
- next CODE_TASK_CANDIDATE:
  - READ_ONLY_AUDIT for live asset snapshot / reconciliation guard can continue separately after this order guard fix.

PURPOSE FUNCTION:
heart_beat_coin_scalper의 run.bat safe demo pump 실행이 Windows 환경에서 state 저장 PermissionError 없이 완료되도록 수정하고, demo mode에서는 config.yaml의 live_order_enabled=True가 실주문 경로로 절대 전달되지 않도록 검증한다.

수익은 최대, 손실은 최소를 목표로 하되, 이번 작업에서는 실주문보다 demo 안전 실행, 상태 저장 안정성, 검증 가능성을 우선한다.

AREA:
STATE_RECOVERY + RUNTIME_ENTRYPOINT + ORDER_GUARD + CONFIG_AND_SECRETS + TESTS

MODE:
GUARDED_FIX

FOCUS:
Windows에서 `.runtime\demo-pump\state.tmp -> state.json` replace 중 PermissionError가 발생하는 문제를 해결한다.
동시에 demo mode에서 live_order_enabled=True가 출력/전달되는 문제를 정리한다.

BUG CONTEXT:
run.bat 기본 실행:

```bat
python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump

현재 출력:

[RUNTIME_CONFIG] mode=demo ... live_order_enabled=True state_path=.runtime\demo-pump\state.json
[RUN] mode=demo profile=pump ...
PermissionError: [WinError 5] 액세스가 거부되었습니다: '.runtime\\demo-pump\\state.tmp' -> '.runtime\\demo-pump\\state.json'

현재 core/state.py:

def save(self, state):
    self.path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = self.path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp_path.replace(self.path)

문제:

fixed temp path state.tmp 사용
Windows에서 target state.json 잠금 시 replace 실패
PermissionError retry 없음
fallback snapshot 없음
demo 실행 중 상태 저장 실패가 전체 런타임을 죽임
demo mode인데 live_order_enabled=True가 그대로 남아 있음

READ FIRST:

DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
DOC/architecture/05_CODEX_HARNESS_GUIDE.md
DOC/architecture/06_WORK_AREA_REGISTRY.md
run.py
run.bat
core/state.py
tests/test_run_guards.py
tests/test_candle_aggregator.py

REQUIRED FIX 1: StateStore.save Windows-safe 처리

core/state.py를 수정한다.

요구사항:

fixed state.tmp 대신 unique temp file을 사용한다.
예:
state.<pid>.<timestamp>.tmp
또는 tempfile.NamedTemporaryFile(delete=False, dir=parent)
replace() 실패 시 짧은 retry를 한다.
예:
5회
0.05s / 0.1s / 0.2s 정도
PermissionError만 retry
retry 후에도 실패하면 runtime을 바로 죽이지 말고 recovery snapshot을 남긴다.
예:
state.recovery.<timestamp>.json
또는 state.failed.<timestamp>.json
save 실패가 발생해도 적어도 demo mode에서는 전체 실행을 죽이지 않게 한다.
단, live mode에서 state 저장 실패를 무시하고 계속 주문하는 구조는 금지한다.
live mode 정책은 별도 guard로 남긴다.
JSON write는 UTF-8 유지.
partial write 방지.
temp 파일 cleanup 시도.
load()는 기존 state.json이 깨졌을 때 {} 반환하는 현재 동작을 유지하되, PermissionError도 안전하게 처리할지 검토한다.

권장 구현 형태:

class StateStore:
    def save(self, state, *, strict: bool = False) -> bool:
        ...
        try:
            atomic replace with retries
            return True
        except PermissionError:
            write recovery snapshot
            if strict:
                raise
            return False

또는 기존 호출부 호환을 위해 save()는 예외를 삼키고 bool을 반환해도 된다.
단, tests로 보장할 것.

REQUIRED FIX 2: demo mode에서 live_order_enabled 무력화

run.py에 runtime mode safety helper를 추가한다.

권장:

def _apply_runtime_mode_safety(config: dict, mode: str) -> None:
    if mode != "live" and bool(config.get("live_order_enabled", False)):
        print("[SAFE_MODE] live_order_enabled=true ignored outside live runtime.", flush=True)
        config["live_order_enabled"] = False

main()에서 config load 후, run_demo/run_live 전에 호출한다.

순서 후보:

mode = _resolve_runtime_mode(args)
config = load_config(args.config)
config["demo_profile"] = args.demo_profile
_apply_output_dir(config, args.output_dir)
_apply_runtime_mode_safety(config, mode)

결과:

run.bat demo 실행 로그에서 live_order_enabled=False가 찍혀야 한다.
demo mode에서 config.yaml의 live_order_enabled=True가 있어도 _place_live_order_if_enabled()가 live 주문을 시도하면 안 된다.

REQUIRED FIX 3: _place_live_order_if_enabled mode-aware guard

현재 함수가 config만 보고 판단하면 위험하다.

권장:

def _place_live_order_if_enabled(config, order_client, side, qty, *, mode="demo"):
    if mode != "live":
        return
    if not bool(config.get("live_order_enabled", False)):
        return
    if order_client is None:
        raise RuntimeError(...)
    order_client.place_market_order(...)

그리고 _process_tick()에서 runtime_metadata의 mode를 넘긴다.

mode = str((runtime_metadata or {}).get("mode") or "demo")
_place_live_order_if_enabled(config, order_client, "BUY", qty, mode=mode)

SELL도 동일.

REQUIRED FIX 4: run.bat safe demo 유지

run.bat 기본값 유지:

--mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump

추가로 시작 전에 출력 폴더를 만들 필요가 있으면 안전하게 생성해도 된다.

예:

if not exist ".runtime\demo-pump" mkdir ".runtime\demo-pump"

단, 기존 state/log 삭제는 금지.

TESTS TO ADD OR UPDATE:

StateStore save basic
def test_state_store_save_creates_state_json(self):
    ...
StateStore replace PermissionError fallback
mock Path.replace 또는 os.replace가 PermissionError를 내게 하고:
save가 demo/non-strict에서 예외를 던지지 않는지
recovery snapshot이 생기는지
False를 반환하는지, 또는 warning 처리되는지 확인
StateStore unique temp
save를 여러 번 호출해도 fixed state.tmp 충돌이 없는지 확인
demo mode forces live_order_enabled false
def test_demo_mode_overrides_live_order_enabled_true(self):
    config = {"live_order_enabled": True}
    _apply_runtime_mode_safety(config, "demo")
    self.assertFalse(config["live_order_enabled"])
live mode preserves live_order_enabled
def test_live_mode_preserves_live_order_enabled(self):
    config = {"live_order_enabled": True}
    _apply_runtime_mode_safety(config, "live")
    self.assertTrue(config["live_order_enabled"])
_place_live_order_if_enabled ignores demo
def test_place_live_order_ignored_outside_live_even_if_enabled(self):
    _place_live_order_if_enabled({"live_order_enabled": True, "symbol": "ROBOUSDT"}, None, "BUY", 1.0, mode="demo")
live still requires client
def test_live_order_guard_requires_client_in_live_mode(self):
    with self.assertRaises(RuntimeError):
        _place_live_order_if_enabled({"live_order_enabled": True, "symbol": "ROBOUSDT"}, None, "BUY", 1.0, mode="live")
main demo log config safety
load_config returns live_order_enabled=True
argv demo
run_demo receives config live_order_enabled=False

VALIDATION COMMANDS:
실제 외부 주문 없이 아래만 실행한다.

python -m unittest tests.test_run_guards
python -m unittest discover tests
python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump

검증 기대:

demo 실행 완료
[RUNTIME_CONFIG] ... mode=demo ... live_order_enabled=False
[RUN] mode=demo profile=pump ...
[DONE] mode=demo ...
.runtime\demo-pump\state.json 생성 또는 갱신
.runtime\demo-pump\strategy.log 생성 또는 갱신
actual order sent: NO
external API touched: NO

FORBIDDEN:

실제 Binance REST order 전송
API key / secret 출력
config.yaml 실제 secret 수정
live_order_enabled를 config.yaml에서 직접 false로 커밋
order size 변경
Binance REST payload 변경
strategy threshold 변경
hard exit 변경
기존 state/log 삭제
SQLite 추가
.runtime 산출물 커밋

SUCCESS CRITERIA:

run.bat 기본 실행이 PermissionError 없이 완료된다.
demo mode에서 live_order_enabled=True config가 안전하게 false로 무력화된다.
demo mode에서는 BinanceRestClient가 필요하지 않다.
--mode live 단독은 계속 차단된다.
--live 명시 시 live runtime으로만 간다.
live mode + live_order_enabled=True + client None은 여전히 RuntimeError다.
StateStore.save는 Windows 파일 잠금/replace 실패에 대해 retry 또는 recovery snapshot을 남긴다.
테스트가 통과한다.
actual order sent: NO
raw secret exposure: NO

REPORT:
수정 후 다음을 보고한다.

수정 파일
PermissionError 원인
StateStore save 변경 내용
demo mode live_order_enabled 무력화 방식
mode-aware order guard 적용 여부
run.bat demo pump 검증 결과
tests 결과
actual order sent 여부
external API touched 여부
secret 노출 여부
남은 위험
```

GUARDED_FIX COMPLETION REPORT — 2026-06-23

- AREA: STATE_RECOVERY + RUNTIME_ENTRYPOINT + ORDER_GUARD + CONFIG_AND_SECRETS + TESTS
- MODE: GUARDED_FIX
- PURPOSE FUNCTION: run.bat safe demo pump 실행이 Windows state replace PermissionError 없이 완료되도록 하고, demo mode에서는 `live_order_enabled=True`가 실주문 경로로 전달되지 않도록 검증한다.
- files inspected:
  - `DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md`
  - `DOC/architecture/05_CODEX_HARNESS_GUIDE.md`
  - `DOC/architecture/06_WORK_AREA_REGISTRY.md`
  - `DOC/walkthough/26-06-23-execute-prompt.md`
  - `run.py`
  - `run.bat`
  - `core/config.py`
  - `core/state.py`
  - `tests/test_run_guards.py`
  - `tests/test_candle_aggregator.py`
- files modified:
  - `core/state.py`
  - `run.py`
  - `tests/test_run_guards.py`
  - `tests/test_state_store.py`
  - `DOC/walkthough/26-06-23-execute-prompt.md`
- PermissionError cause:
  - 기존 `StateStore.save()`는 고정 temp path `state.tmp`를 사용하고, Windows에서 target `state.json`이 잠긴 상태의 `replace()` 실패를 retry/recovery 없이 그대로 올렸다.
  - demo 실행 중 state 저장 실패가 전체 runtime 실패로 이어질 수 있었다.
- StateStore save changes:
  - fixed `state.tmp` 대신 `state.<pid>.<timestamp>.tmp` unique temp file을 사용한다.
  - JSON은 UTF-8로 temp file에 먼저 쓰고, `Path.replace()`로 atomic replace를 시도한다.
  - `PermissionError`에 대해서만 짧은 retry를 수행한다.
  - retry 후에도 실패하면 `state.recovery.<timestamp>.json` recovery snapshot을 남긴다.
  - non-strict save는 warning 후 `False`를 반환하고 demo runtime을 죽이지 않는다.
  - strict save는 recovery snapshot을 남긴 뒤 `PermissionError`를 다시 올린다.
  - `load()`는 JSON decode failure와 PermissionError에서 기존처럼 `{}`를 반환한다.
- demo mode live_order_enabled safety:
  - `_apply_runtime_mode_safety(config, mode)`를 추가했다.
  - runtime mode가 `live`가 아니면 `live_order_enabled=True`를 로그 warning 후 `False`로 무력화한다.
  - `main()`에서 config load/output-dir 적용 뒤 runtime recorder/runner 생성 전에 적용한다.
  - demo runtime log에는 `live_order_enabled=False`가 출력된다.
- mode-aware order guard:
  - `_place_live_order_if_enabled()`가 `mode` 또는 기존 호환용 `runtime_mode`를 받는다.
  - mode가 `live`가 아니면 `live_order_enabled=True`여도 order client를 요구하거나 호출하지 않는다.
  - `_process_tick()` BUY/SELL 경로는 `runtime_metadata.mode`를 넘긴다.
  - live mode + `live_order_enabled=True` + client 없음은 여전히 `RuntimeError`다.
- run.bat safe demo pump validation:
  - command: `python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump`
  - result: completed successfully
  - observed:
    - `[SAFE_MODE] live_order_enabled=true ignored outside live runtime.`
    - `[RUNTIME_CONFIG] ... mode=demo ... live_order_enabled=False ...`
    - `[RUN] mode=demo profile=pump ...`
    - `[DONE] mode=demo processed_ticks=240 closed_candles=20 new_trades=3 ...`
  - files verified:
    - `.runtime\demo-pump\state.json`: exists
    - `.runtime\demo-pump\strategy.log`: exists
    - `.runtime\demo-pump\trades.log`: exists
- tests/checks run:
  - `python -m unittest tests.test_state_store tests.test_run_guards -v`
  - `python -m unittest discover tests -v`
  - `git diff -- core\state.py run.py tests\test_state_store.py tests\test_run_guards.py --check`
  - `python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump`
- test result:
  - focused tests: 24 tests passed
  - full discover: 68 tests passed
- actual order sent: NO
- external API touched: NO
- Binance REST payload changed: NO
- config.yaml touched: NO
- live_order_enabled config file value changed: NO
- raw secret exposure: NO
- state/log impact:
  - `.runtime\demo-pump` local runtime artifacts were created/updated by the required demo validation.
  - existing state/log files were not deleted.
  - `.runtime` artifacts remain runtime output and must not be committed.
- remaining risks:
  - If another process keeps `state.json` locked longer than the retry window, demo will continue with a recovery snapshot and warning; operator should inspect the recovery file.
  - live mode intentionally remains strict for state save failure to avoid continuing automated orders with uncertain local state.
- stop conditions encountered: none
- next CODE_TASK_CANDIDATE:
  - READ_ONLY_AUDIT for live asset snapshot / reconciliation guard remains the next protected design task.

[SCALPER_EXECUTION_COMPLETE]

PURPOSE FUNCTION:
heart_beat_coin_scalper의 PostgreSQL DB 테이블이 실제로 생성되지 않고 데이터가 쌓이지 않는 원인을 검토하고, 필요한 경우 안전한 migration 실행 경로와 runtime data recording을 추가한다.

수익은 최대, 손실은 최소를 목표로 하되, 이번 작업에서는 실주문보다 DB 기록 안정성, migration 안전성, demo/fake asset 추적, secret 보호를 우선한다.

AREA:
POSTGRES_STORAGE + DB_MIGRATION + RUNTIME_ENTRYPOINT + ORDER_GUARD + ASSET_TRACKING + LOGGING_REPORTING + TESTS

MODE:
READ_ONLY_AUDIT first, then GUARDED_FIX if confirmed

FOCUS:
현재 `storage/schema/001_scalper_core.sql`에는 테이블 생성 SQL이 존재하지만, 실제 local PostgreSQL에 테이블이 생성되지 않는 원인을 확인한다.
원인이 migration 미실행 또는 DB recorder disabled라면, 안전한 방식으로 테이블 생성과 demo pump 데이터 적재를 추가한다.

READ FIRST:
- DOC/architecture/08_DATABASE_ARCHITECTURE.md
- DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
- DOC/architecture/05_CODEX_HARNESS_GUIDE.md
- DOC/architecture/06_WORK_AREA_REGISTRY.md
- run.py
- run.bat
- storage/postgres.py
- storage/migrations.py
- storage/runtime_repository.py
- storage/records.py
- storage/fake_assets.py
- storage/schema/001_scalper_core.sql
- tests/

KNOWN CURRENT OBSERVATION:
- `storage/schema/001_scalper_core.sql` defines tables.
- `storage/migrations.py` has `apply_migrations()`.
- `storage/postgres.py` has `ensure_schema()`.
- `storage/runtime_repository.py` creates DB recorder only when DB is enabled.
- run.bat safe demo currently completes, but DB tables appear not created.
- run.py may create recorder, but migration may not be invoked automatically.
- If SCALPER_DB_ENABLED or DATABASE_URL is missing, DisabledRuntimeRecorder is used and no DB data is written.

PHASE 0: READ_ONLY_AUDIT

TASK:
1. Confirm whether migration SQL exists.
2. Confirm whether migration runner exists.
3. Confirm whether run.py or create_runtime_recorder calls `ensure_schema()` or `apply_migrations()`.
4. Confirm whether DB is disabled unless `SCALPER_DB_ENABLED` or config db flag is set.
5. Confirm whether run.bat sets any DB env variable.
6. Confirm whether missing tables would cause recorder.start() to fail.
7. Confirm whether demo data recording only happens if db_recorder is enabled.
8. Report exact cause:
   - DB disabled
   - DATABASE_URL missing
   - migration not executed
   - schema missing
   - recorder insert failure
   - PostgreSQL dependency missing
   - other

DO NOT MODIFY in PHASE 0.

PHASE 0 REPORT:
- tables SQL present: YES/NO
- migration runner present: YES/NO
- migration auto-run present: YES/NO
- DB enable condition
- likely reason tables not created
- recommended fix
- protected risk

PHASE 1: GUARDED_FIX — explicit migration command

If PHASE 0 confirms migration is not actually executed, add a safe explicit migration command.

REQUIRED:
1. Add CLI option to run.py:

```text
--migrate-db

Behavior:

Requires DATABASE_URL.
Runs safe migration via storage.postgres.ensure_schema(connection) or apply_migrations(connection).
Prints applied migration versions.
Does not start demo/live trading loop.
Does not call Binance WebSocket.
Does not call Binance REST.
Does not require API key/secret.
Does not print DATABASE_URL raw value.
Redacts DATABASE_URL in logs.

Expected command:

python run.py --migrate-db

Expected output:

[DB_MIGRATION] database=postgresql://user:***@localhost:5432/heart_beat_coin_scalper
[DB_MIGRATION] applied=[1]
[DB_MIGRATION] done
If tables already exist, it should safely return:
[DB_MIGRATION] applied=[]
[DB_MIGRATION] done
Migration SQL safety:
Keep forbidden SQL validation.
Do not allow DROP TABLE.
Do not allow TRUNCATE.
Do not allow DROP SCHEMA.
Do not allow destructive ALTER DROP.

PHASE 2: GUARDED_FIX — optional DB auto-migration for demo

Add optional auto-migrate, but do not force it silently.

Preferred env/config:

SCALPER_DB_ENABLED=1
SCALPER_DB_AUTO_MIGRATE=1
DATABASE_URL=...

Behavior:

If DB enabled and auto migrate enabled, run migration before recorder.start().
If DB enabled but auto migrate disabled and tables missing, fail with clear message recommending python run.py --migrate-db.
For demo mode, if DB disabled, continue without DB and print:
[DB] disabled reason=...
For live mode, do not silently ignore DB errors if live-order reconciliation later depends on DB. For now report warning/stop according to current policy.

PHASE 3: GUARDED_FIX — run.bat DB setup helper

Do not put password in run.bat.

Add a separate safe helper bat if useful:

migrate_db.bat

or add commented instructions in run.bat output.

Recommended new file:

@echo off
setlocal
cd /d "%~dp0"

echo [DB] Running PostgreSQL migration.
echo [DB] Requires DATABASE_URL env var.
python "%~dp0run.py" --migrate-db

Do not include actual DATABASE_URL.

PHASE 4: GUARDED_FIX — demo data accumulation path

Ensure that when DB is enabled and schema exists, safe demo pump records data.

Expected command:

set SCALPER_DB_ENABLED=1
set SCALPER_DB_AUTO_MIGRATE=1
set DATABASE_URL=postgresql://...
python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump

Expected DB writes:

scalper.runtime_run: 1 row
scalper.runtime_config_snapshot: 1 row
scalper.strategy_decision: rows for closed candles
scalper.ledger_snapshot: rows for closed candles
scalper.order_intent / execution_result / demo_fake_asset_snapshot: rows if fake buy/sell occurs
No live_asset_snapshot writes in demo

Important:

15m/30m/1h/4h market_candle may not yet be populated unless a timeframe aggregator exists.
If market_candle is not yet wired, report as CODE_TASK_CANDIDATE rather than faking data.
Do not store 1m/raw tick by default.
Do not fake 15m/30m/1h/4h rows unless actual aggregation logic exists.

PHASE 5: TESTS

Add or update tests:

migration dry-run/list test
def test_migration_files_load_and_validate():
    ...
forbidden SQL test
def test_forbidden_migration_sql_rejected():
    ...
migrate-db CLI test with mocked connection
def test_migrate_db_command_runs_migration_without_runtime_loop():
    ...
DB disabled by default test
def test_db_disabled_without_env():
    ...
DB auto migrate calls ensure_schema when enabled
def test_db_auto_migrate_when_enabled():
    ...
recorder disabled does not break demo
def test_demo_runs_with_disabled_recorder():
    ...
no raw DATABASE_URL output test
def test_database_url_redacted_in_migration_output():
    ...
demo does not write live asset snapshot
def test_demo_fake_execution_does_not_write_live_asset():
    ...

VALIDATION COMMANDS:
Run without external order:

python -m unittest tests.test_run_guards
python -m unittest discover tests

Manual DB validation, only after user has local PostgreSQL ready:

set SCALPER_DB_ENABLED=1
set SCALPER_DB_AUTO_MIGRATE=1
set DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/heart_beat_coin_scalper
python run.py --migrate-db
python run.py --mode demo --demo-profile pump --ticks 240 --output-dir .runtime\demo-pump

Then verify in PostgreSQL:

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'scalper'
ORDER BY table_name;

SELECT count(*) FROM scalper.runtime_run;
SELECT count(*) FROM scalper.runtime_config_snapshot;
SELECT count(*) FROM scalper.strategy_decision;
SELECT count(*) FROM scalper.ledger_snapshot;
SELECT count(*) FROM scalper.demo_fake_asset_snapshot;

FORBIDDEN:

Actual Binance REST order
API key / secret output
DATABASE_URL raw output
config.yaml secret edit
live_order_enabled config edit
order size change
Binance REST payload change
strategy threshold change
hard exit change
DROP TABLE
TRUNCATE
SQLite operating DB
fake live_asset_snapshot from demo
.runtime output commit
DB password in run.bat

SUCCESS CRITERIA:

python run.py --migrate-db creates scalper schema and tables.
Running migration twice is safe.
DB disabled mode still runs demo without DB.
DB enabled + DATABASE_URL + auto migrate creates tables if missing.
demo pump writes runtime/config/decision/ledger/fake asset rows when DB enabled.
demo does not touch live_asset_snapshot.
no raw secret or DATABASE_URL is printed.
actual order sent: NO.
external Binance API touched: NO.

REPORT:
After completion, report:

root cause of missing tables
files modified
migration command added
DB enable env vars
tables created
which tables receive data in demo
which tables are still not populated and why
tests run
manual validation commands
actual order sent 여부
secret exposure 여부
remaining CODE_TASK_CANDIDATE