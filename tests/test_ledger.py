from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sqlite3

from ledger import append_event, count_events, export_attempts_tsv, read_events, reserve_holdout_lookup


class LedgerTests(unittest.TestCase):
    def test_holdout_budget_is_enforced_by_batch_and_lifetime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            reserve_holdout_lookup(
                holdout_id="holdout",
                batch_id="batch-1",
                candidate_id="candidate-1",
                payload={},
                max_total=2,
                max_per_batch=1,
                path=database,
            )
            with self.assertRaisesRegex(RuntimeError, "batch-1"):
                reserve_holdout_lookup(
                    holdout_id="holdout",
                    batch_id="batch-1",
                    candidate_id="candidate-2",
                    payload={},
                    max_total=2,
                    max_per_batch=1,
                    path=database,
                )
            reserve_holdout_lookup(
                holdout_id="holdout",
                batch_id="batch-2",
                candidate_id="candidate-2",
                payload={},
                max_total=2,
                max_per_batch=1,
                path=database,
            )
            self.assertEqual(count_events("holdout", holdout_id="holdout", path=database), 2)
            with self.assertRaisesRegex(RuntimeError, "lifetime"):
                reserve_holdout_lookup(
                    holdout_id="holdout",
                    batch_id="batch-3",
                    candidate_id="candidate-3",
                    payload={},
                    max_total=2,
                    max_per_batch=1,
                    path=database,
                )

    def test_tsv_is_a_derived_attempt_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            output = Path(directory) / "results.tsv"
            from ledger import append_event

            append_event(
                "attempt",
                {"status": "discarded", "hypothesis": "test"},
                batch_id="batch-1",
                candidate_id="candidate-1",
                path=database,
            )
            export_attempts_tsv(database, output)
            self.assertIn("candidate-1", output.read_text())

    def test_events_cannot_be_updated_or_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            from ledger import append_event

            event_id = append_event("attempt", {}, path=database)
            with sqlite3.connect(database) as connection:
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    connection.execute("DELETE FROM events WHERE id = ?", (event_id,))

    def test_read_events_returns_decoded_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            append_event(
                "attempt", {"strategy_family": "trend"}, candidate_id="candidate", path=database
            )

            events = read_events(candidate_id="candidate", path=database)

        self.assertEqual(events[0]["payload"]["strategy_family"], "trend")
