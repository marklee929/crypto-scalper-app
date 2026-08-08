from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


SCHEMA_DIR = Path(__file__).with_name("schema")
FORBIDDEN_SQL_PATTERNS = (
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+SCHEMA\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+TABLE\b[\s\S]*\bDROP\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    sql: str

    @property
    def checksum(self) -> str:
        return sha256(self.sql.encode("utf-8")).hexdigest()


def list_migration_files(schema_dir: Path = SCHEMA_DIR) -> list[Path]:
    if not schema_dir.exists():
        return []
    return sorted(schema_dir.glob("[0-9][0-9][0-9]_*.sql"))


def load_migrations(schema_dir: Path = SCHEMA_DIR) -> list[Migration]:
    migrations: list[Migration] = []
    for path in list_migration_files(schema_dir):
        version = _parse_version(path)
        sql = path.read_text(encoding="utf-8")
        validate_migration_sql(sql)
        migrations.append(Migration(version=version, name=path.stem, path=path, sql=sql))
    return migrations


def validate_migration_sql(sql: str) -> None:
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if pattern.search(sql):
            raise ValueError(f"Forbidden migration SQL pattern: {pattern.pattern}")


def apply_migrations(connection, *, dry_run: bool = False) -> list[int]:
    migrations = load_migrations()
    if dry_run:
        return [migration.version for migration in migrations]

    _ensure_migration_table(connection)
    applied = _applied_versions(connection)
    applied_now: list[int] = []
    for migration in migrations:
        if migration.version in applied:
            continue
        with connection.cursor() as cursor:
            cursor.execute(migration.sql)
            cursor.execute(
                """
                INSERT INTO scalper.schema_migration(version, name, checksum)
                VALUES (%s, %s, %s)
                """,
                (migration.version, migration.name, migration.checksum),
            )
        connection.commit()
        applied_now.append(migration.version)
    return applied_now


def _ensure_migration_table(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS scalper;
            CREATE TABLE IF NOT EXISTS scalper.schema_migration (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
    connection.commit()


def _applied_versions(connection) -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version FROM scalper.schema_migration")
        rows = cursor.fetchall()
    return {int(row[0]) for row in rows}


def _parse_version(path: Path) -> int:
    prefix = path.name.split("_", 1)[0]
    return int(prefix)

