from __future__ import annotations

import datetime as dt
import math
import unittest

from data import Bar
from validate import validate_bars, validate_signals


def make_bars() -> list[Bar]:
    return [
        Bar(
            date=dt.date(2024, 1, 1) + dt.timedelta(days=index),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1_000_000,
        )
        for index in range(3)
    ]


class ValidationTests(unittest.TestCase):
    def test_rejects_non_chronological_bars(self) -> None:
        bars = make_bars()
        invalid = [bars[1], bars[0], bars[2]]

        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            validate_bars(invalid)

    def test_rejects_nan_signal(self) -> None:
        bars = make_bars()

        with self.assertRaisesRegex(ValueError, "not finite"):
            validate_signals([0.0, math.nan, 1.0], bars)

    def test_rejects_excessive_leverage(self) -> None:
        bars = make_bars()

        with self.assertRaisesRegex(ValueError, "outside"):
            validate_signals([0.0, 1.25, 1.0], bars, max_leverage=1.0)

    def test_rejects_signal_length_mismatch(self) -> None:
        bars = make_bars()

        with self.assertRaisesRegex(ValueError, "signal count"):
            validate_signals([0.0, 1.0], bars)


if __name__ == "__main__":
    unittest.main()
