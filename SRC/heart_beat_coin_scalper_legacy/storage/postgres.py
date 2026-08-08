from __future__ import annotations

import os
from typing import Mapping, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DATABASE_URL_ENV = "DATABASE_URL"
_SENSITIVE_QUERY_KEYS = {"password", "pass", "token", "secret", "api_key", "apikey"}


def get_database_url_from_env(
    env: Mapping[str, str] | None = None,
    *,
    name: str = DATABASE_URL_ENV,
) -> Optional[str]:
    source = env if env is not None else os.environ
    value = str(source.get(name, "")).strip()
    return value or None


def redact_database_url(database_url: str | None) -> str:
    if not database_url:
        return ""
    try:
        parts = urlsplit(str(database_url))
    except ValueError:
        return "<redacted>"
    if not parts.scheme or not parts.netloc:
        return "<redacted>"

    hostname = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    if parts.username:
        auth = f"{parts.username}:***@"
    elif parts.password:
        auth = "***@"
    else:
        auth = ""
    netloc = f"{auth}{hostname}{port}"

    safe_query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, value))
    return urlunsplit(
        (parts.scheme, netloc, parts.path, urlencode(safe_query), "")
    )


def connect(database_url: str | None = None):
    resolved_url = database_url or get_database_url_from_env()
    if not resolved_url:
        raise RuntimeError(f"{DATABASE_URL_ENV} is not configured.")

    import psycopg  # type: ignore

    return psycopg.connect(resolved_url)


def execute_migration(connection, sql: str) -> None:
    from storage.migrations import validate_migration_sql

    validate_migration_sql(sql)
    with connection.cursor() as cursor:
        cursor.execute(sql)
    connection.commit()


def ensure_schema(connection) -> list[int]:
    from storage.migrations import apply_migrations

    return apply_migrations(connection)


def health_check(connection) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
    return bool(row and row[0] == 1)

