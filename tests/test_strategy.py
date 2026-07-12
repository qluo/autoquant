from __future__ import annotations

import datetime as dt
import unittest

from data import Bar
from strategy import generate_mean_reversion_signals, generate_momentum_signals, generate_signals


def make_bars(values: list[float]) -> list[Bar]:
    return [
        Bar(
            date=dt.date(2024, 1, 1) + dt.timedelta(days=index),
            open=value,
            high=value,
            low=value,
            close=value,
            adjusted_close=value,
            volume=1_000_000,
        )
        for index, value in enumerate(values)
    ]


class MomentumStrategyTests(unittest.TestCase):
    def test_waits_for_lookback_and_uses_trailing_return(self) -> None:
        signals = generate_momentum_signals(make_bars([100.0, 101.0, 99.0, 102.0]), 2)

        self.assertEqual(signals, [0.0, 0.0, 0.0, 1.0])

    def test_rejects_non_positive_lookback(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            generate_momentum_signals(make_bars([100.0]), 0)

    def test_default_strategy_remains_trend(self) -> None:
        self.assertEqual(generate_signals(make_bars([100.0, 101.0])), [0.0, 0.0])

    def test_mean_reversion_uses_trailing_average(self) -> None:
        signals = generate_mean_reversion_signals(make_bars([100.0, 110.0, 90.0]), 2)

        self.assertEqual(signals, [0.0, 0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
