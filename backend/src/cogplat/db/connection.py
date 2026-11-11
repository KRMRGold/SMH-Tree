"""SQLite connection setup and numbered SQL migration runner."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d+)_.*\.sql$")


def connect_db(path: str | Path) -> sqlite3.Connection:
    """Open SQLite with the required per-connection pragmas enabled."""

    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _migration_files(migrations_dir: Path) -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    seen_versions: set[int] = set()

    for path in sorted(migrations_dir.glob("*.sql")):
        match = _MIGRATION_NAME.match(path.name)
        if match is None:
            raise ValueError(f"Invalid migration filename: {path.name}")
        version = int(match.group(1))
        if version in seen_versions:
            raise ValueError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        migrations.append((version, path))

    return sorted(migrations, key=lambda item: item[0])


def apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: str | Path = DEFAULT_MIGRATIONS_DIR,
) -> int:
    """Apply each unapplied migration atomically and return the schema version."""

    directory = Path(migrations_dir)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )

    applied = {
        int(row[0])
        for row in connection.execute("SELECT version FROM schema_migrations")
    }

    for version, path in _migration_files(directory):
        if version in applied:
            continue

        sql = path.read_text(encoding="utf-8")
        applied_at = (
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        )
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{sql}\n"
            "INSERT INTO schema_migrations(version, applied_at) VALUES "
            f"({version}, '{applied_at}');\n"
            "COMMIT;"
        )
        try:
            connection.executescript(script)
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

    row = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()
    return int(row[0])
