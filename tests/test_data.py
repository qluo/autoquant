from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from data import Bar, load_risk_free_daily


class RiskFreeDataTests(unittest.TestCase):
    def test_loads_and_forward_fills_pinned_rates(self) -> None:
        bars = [
            Bar(dt.date(2024, 1, 1), 100, 100, 100, 100, 100, 1),
            Bar(dt.date(2024, 1, 3), 100, 100, 100, 100, 100, 1),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk_free_3m.csv"
            path.write_text(
                "Date,AnnualizedRatePercent\n"
                "2024-01-01,5.0\n"
            )

            rates, metadata = load_risk_free_daily(bars, path)

        self.assertGreater(rates[0], 0.0)
        self.assertEqual(rates[0], rates[1])
        self.assertEqual(metadata["source"], "pinned_local_treasury_bill_csv")

    def test_missing_series_is_explicit_zero_fallback(self) -> None:
        bars = [Bar(dt.date(2024, 1, 1), 100, 100, 100, 100, 100, 1)]
        with tempfile.TemporaryDirectory() as directory:
            rates, metadata = load_risk_free_daily(
                bars, Path(directory) / "missing.csv"
            )

        self.assertEqual(rates, [0.0])
        self.assertEqual(metadata["source"], "zero_rate_fallback")
