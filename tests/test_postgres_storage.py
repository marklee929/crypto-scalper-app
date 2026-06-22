from __future__ import annotations

import unittest

from storage.postgres import get_database_url_from_env, redact_database_url, connect


class PostgresStorageTest(unittest.TestCase):
    def test_get_database_url_from_env_returns_none_when_missing(self) -> None:
        self.assertIsNone(get_database_url_from_env({}))

    def test_get_database_url_from_env_trims_value(self) -> None:
        env = {"DATABASE_URL": "  postgresql://user:pass@localhost/db  "}

        self.assertEqual(
            get_database_url_from_env(env),
            "postgresql://user:pass@localhost/db",
        )

    def test_redact_database_url_hides_password(self) -> None:
        raw = "postgresql://scalper:s3cret@localhost:5432/heart_beat_coin_scalper"

        redacted = redact_database_url(raw)

        self.assertEqual(
            redacted,
            "postgresql://scalper:***@localhost:5432/heart_beat_coin_scalper",
        )
        self.assertNotIn("s3cret", redacted)

    def test_redact_database_url_hides_sensitive_query_values(self) -> None:
        raw = "postgresql://user:pass@localhost/db?sslmode=require&password=hidden"

        redacted = redact_database_url(raw)

        self.assertIn("sslmode=require", redacted)
        self.assertIn("password=%2A%2A%2A", redacted)
        self.assertNotIn("hidden", redacted)
        self.assertNotIn("pass@localhost", redacted)

    def test_connect_without_database_url_fails_without_driver_import(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL is not configured"):
            connect("")


if __name__ == "__main__":
    unittest.main()

