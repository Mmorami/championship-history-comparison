from __future__ import annotations

from pathlib import Path
import sqlite3


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> None:
    _ensure_migrations_table(conn)
    applied = {
        row["version"] for row in conn.execute("SELECT version FROM schema_migrations;").fetchall()
    }
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        version = sql_file.stem
        if version in applied:
            continue
        script = sql_file.read_text(encoding="utf-8")
        conn.executescript(script)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?);", (version,))
        conn.commit()

