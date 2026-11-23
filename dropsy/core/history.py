"""Local, explicit storage of validated audit snapshots."""
from contextlib import closing, contextmanager
import os
from datetime import UTC
from pathlib import Path
import sqlite3

from .audit import Snapshot, validate_snapshot


@contextmanager
def _database():
    setting = os.environ.get("DROPSY_HISTORY_DB")
    path = Path(setting).expanduser() if setting else Path.home() / ".dropsy" / "history.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(path, timeout=5)) as connection:
        with connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    fingerprint TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    partial INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS timeline
                ON snapshots (scope, mode, captured_at DESC, fingerprint DESC)
            """)
            yield connection


def save_snapshot(snapshot):
    with _database() as connection:
        return store_snapshot(connection, snapshot)


def store_snapshot(connection, snapshot):
    validate_snapshot(snapshot)
    if snapshot.source != "observed":
        raise ValueError("Учебные снимки доступны в примере и не добавляются в историю актива.")
    captured_at = snapshot.captured_at
    if captured_at.utcoffset() is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    cursor = connection.execute("""
        INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fingerprint) DO NOTHING
    """, (
        snapshot.fingerprint, snapshot.scope, snapshot.mode,
        captured_at.astimezone(UTC).isoformat(timespec="microseconds"), len(snapshot.records), snapshot.partial,
        snapshot.model_dump_json(),
    ))
    return cursor.rowcount == 1


def list_snapshots(scope, mode, offset=0):
    with _database() as connection:
        rows = connection.execute("""
            SELECT fingerprint, scope, mode, captured_at, record_count, partial
            FROM snapshots
            WHERE scope = ? AND mode = ?
            ORDER BY captured_at DESC, fingerprint DESC LIMIT 51 OFFSET ?
        """, (scope, mode, offset)).fetchall()
    return {"snapshots": [dict(row) for row in rows[:50]], "next_offset": offset + 50 if len(rows) > 50 else None}


def list_assets():
    with _database() as connection:
        rows = connection.execute("""
            SELECT scope, mode, MAX(captured_at) AS latest, COUNT(*) AS snapshot_count
            FROM snapshots GROUP BY scope, mode
            ORDER BY latest DESC, scope LIMIT 150
        """).fetchall()
    return [dict(row) for row in rows]


def read_snapshot(fingerprint):
    with _database() as connection:
        row = connection.execute("SELECT payload FROM snapshots WHERE fingerprint = ?", (fingerprint,)).fetchone()
    return Snapshot.model_validate_json(row["payload"]) if row else None
