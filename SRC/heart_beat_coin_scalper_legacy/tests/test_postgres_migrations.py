from __future__ import annotations

import unittest

from storage.migrations import load_migrations, validate_migration_sql


REQUIRED_TABLES = (
    "scalper.schema_migration",
    "scalper.runtime_run",
    "scalper.runtime_config_snapshot",
    "scalper.market_candle",
    "scalper.strategy_decision",
    "scalper.order_intent",
    "scalper.execution_result",
    "scalper.live_asset_snapshot",
    "scalper.ledger_snapshot",
    "scalper.demo_fake_account",
    "scalper.demo_fake_asset_snapshot",
    "scalper.asset_reconciliation_event",
)

REQUIRED_INDEXES = (
    "idx_market_candle_symbol_tf_time",
    "idx_strategy_decision_run_time",
    "idx_order_intent_run_status",
    "idx_execution_result_order",
    "idx_live_asset_latest",
    "idx_demo_fake_asset_latest",
)

RAW_SECRET_FIELD_NAMES = (
    "api_key",
    "api_secret",
    "password ",
    "password\n",
    "token ",
    "token\n",
    "private_key",
)


class PostgresMigrationTest(unittest.TestCase):
    def test_loads_initial_migration(self) -> None:
        migrations = load_migrations()

        self.assertEqual([migration.version for migration in migrations], [1])
        self.assertEqual(migrations[0].name, "001_scalper_core")

    def test_initial_migration_contains_required_tables_and_indexes(self) -> None:
        sql = load_migrations()[0].sql

        for table in REQUIRED_TABLES:
            self.assertIn(table, sql)
        for index in REQUIRED_INDEXES:
            self.assertIn(index, sql)

    def test_initial_migration_has_no_forbidden_sql(self) -> None:
        sql = load_migrations()[0].sql

        validate_migration_sql(sql)

    def test_forbidden_sql_is_rejected(self) -> None:
        for sql in (
            "DROP TABLE scalper.runtime_run;",
            "TRUNCATE scalper.runtime_run;",
            "ALTER TABLE scalper.runtime_run DROP COLUMN status;",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):
                    validate_migration_sql(sql)

    def test_initial_migration_does_not_define_raw_secret_fields(self) -> None:
        lowered_sql = load_migrations()[0].sql.lower()

        for field_name in RAW_SECRET_FIELD_NAMES:
            self.assertNotIn(field_name, lowered_sql)


if __name__ == "__main__":
    unittest.main()

