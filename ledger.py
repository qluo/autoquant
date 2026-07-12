from __future__ import annotations

import csv
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any


RUNS_DIR = Path("runs")
LEDGER_DB = RUNS_DIR / "experiments.sqlite"
RESULTS_TSV = Path("results.tsv")


def _connection(path: Path = LEDGER_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            batch_id TEXT,
            candidate_id TEXT,
            holdout_id TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS events_holdout_idx "
        "ON events (event_type, holdout_id, batch_id)"
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS events_no_update
        BEFORE UPDATE ON events
        BEGIN SELECT RAISE(ABORT, 'events are append-only'); END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS events_no_delete
        BEFORE DELETE ON events
        BEGIN SELECT RAISE(ABORT, 'events are append-only'); END
        """
    )
    return connection


def append_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    batch_id: str | None = None,
    candidate_id: str | None = None,
    holdout_id: str | None = None,
    path: Path = LEDGER_DB,
) -> int:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    with _connection(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (
                created_at_utc, event_type, batch_id, candidate_id, holdout_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                event_type,
                batch_id,
                candidate_id,
                holdout_id,
                json.dumps(payload, sort_keys=True),
            ),
        )
    return int(cursor.lastrowid)


def count_events(
    event_type: str,
    *,
    holdout_id: str | None = None,
    batch_id: str | None = None,
    path: Path = LEDGER_DB,
) -> int:
    query = "SELECT COUNT(*) FROM events WHERE event_type = ?"
    values: list[str] = [event_type]
    if holdout_id is not None:
        query += " AND holdout_id = ?"
        values.append(holdout_id)
    if batch_id is not None:
        query += " AND batch_id = ?"
        values.append(batch_id)
    with _connection(path) as connection:
        return int(connection.execute(query, values).fetchone()[0])


def reserve_holdout_lookup(
    *,
    holdout_id: str,
    batch_id: str,
    candidate_id: str,
    payload: dict[str, Any],
    max_total: int,
    max_per_batch: int,
    path: Path = LEDGER_DB,
) -> int:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    with _connection(path) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'holdout' AND holdout_id = ?",
            (holdout_id,),
        ).fetchone()[0]
        batch_total = connection.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE event_type = 'holdout' AND holdout_id = ? AND batch_id = ?
            """,
            (holdout_id, batch_id),
        ).fetchone()[0]
        if total >= max_total:
            raise RuntimeError(f"locked holdout {holdout_id} has reached its lifetime limit")
        if batch_total >= max_per_batch:
            raise RuntimeError(f"batch {batch_id} has already used its locked holdout lookup")
        cursor = connection.execute(
            """
            INSERT INTO events (
                created_at_utc, event_type, batch_id, candidate_id, holdout_id, payload_json
            ) VALUES (?, 'holdout', ?, ?, ?, ?)
            """,
            (
                timestamp,
                batch_id,
                candidate_id,
                holdout_id,
                json.dumps(payload, sort_keys=True),
            ),
        )
    return int(cursor.lastrowid)


def export_attempts_tsv(path: Path = LEDGER_DB, output: Path = RESULTS_TSV) -> Path:
    fieldnames = [
        "event_id",
        "created_at_utc",
        "batch_id",
        "candidate_id",
        "status",
        "hypothesis",
        "validation_score",
        "validation_sharpe",
        "validation_max_drawdown",
        "result_path",
        "patch_path",
    ]
    with _connection(path) as connection:
        rows = connection.execute(
            """
            SELECT id, created_at_utc, batch_id, candidate_id, payload_json
            FROM events WHERE event_type = 'attempt' ORDER BY id
            """
        ).fetchall()

    with output.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for event_id, created_at, batch_id, candidate_id, payload_json in rows:
            payload = json.loads(payload_json)
            writer.writerow(
                {
                    "event_id": event_id,
                    "created_at_utc": created_at,
                    "batch_id": batch_id or "",
                    "candidate_id": candidate_id or "",
                    "status": payload.get("status", ""),
                    "hypothesis": payload.get("hypothesis", ""),
                    "validation_score": payload.get("validation_score", ""),
                    "validation_sharpe": payload.get("validation_sharpe", ""),
                    "validation_max_drawdown": payload.get(
                        "validation_max_drawdown", ""
                    ),
                    "result_path": payload.get("result_path", ""),
                    "patch_path": payload.get("patch_path", ""),
                }
            )
    return output
