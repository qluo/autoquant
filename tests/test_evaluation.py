from __future__ import annotations

import datetime as dt
import unittest

from data import Bar
from evaluation import evaluate_locked_holdout


def make_bars(start: dt.date, count: int) -> list[Bar]:
    bars: list[Bar] = []
    for index in range(count):
        price = 100.0 + index * 0.1
        bars.append(
            Bar(
                date=start + dt.timedelta(days=index),
                open=price,
                high=price,
                low=price,
                close=price,
                adjusted_close=price,
                volume=1_000_000,
            )
        )
    return bars


class LockedEvaluationTests(unittest.TestCase):
    def test_locked_evaluation_is_separate_from_research_result(self) -> None:
        payload = evaluate_locked_holdout(make_bars(dt.date(2021, 1, 1), 600))

        self.assertEqual(payload["evaluation_mode"], "locked_holdout")
        self.assertEqual(payload["holdout_start"], "2022-01-01")
        self.assertIn("metrics", payload)
        self.assertIn("benchmark", payload)

    def test_locked_evaluation_requires_holdout_bars(self) -> None:
        with self.assertRaisesRegex(ValueError, "do not cover locked holdout"):
            evaluate_locked_holdout(make_bars(dt.date(2020, 1, 1), 300))


if __name__ == "__main__":
    unittest.main()
