from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import memory
import ledger
from ledger import append_event


class MemoryTests(unittest.TestCase):
    def test_summary_search_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            append_event(
                "attempt",
                {"status": "discarded", "strategy_family": "trend"},
                candidate_id="parent",
                path=database,
            )
            append_event(
                "attempt",
                {
                    "status": "manual_review",
                    "strategy_family": "trend",
                    "parent_candidate": "parent",
                },
                candidate_id="child",
                path=database,
            )
            with patch(
                "memory.read_events",
                side_effect=lambda **kwargs: ledger.read_events(path=database, **kwargs),
            ):
                self.assertEqual(memory.summary()["attempt_count"], 2)
                self.assertEqual(len(memory.search("trend", None, 10)), 2)
                self.assertEqual(len(memory.candidate_history("parent")), 2)
