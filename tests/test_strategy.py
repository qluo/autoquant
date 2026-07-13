from __future__ import annotations

import datetime as dt
import unittest

from data import Bar
from strategy import (
    generate_mean_reversion_signals,
    generate_momentum_signals,
    generate_factor_combo_signals,
    generate_regime_filter_signals,
    generate_risk_constrained_signals,
    generate_signals,
    generate_volatility_targeting_signals,
)


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

    def test_volatility_targeting_waits_for_lookback(self) -> None:
        signals = generate_volatility_targeting_signals(
            make_bars([100.0, 101.0, 100.0, 101.0]), lookback=2
        )

        self.assertEqual(signals[:2], [0.0, 0.0])
        self.assertGreater(signals[2], 0.0)
        self.assertLessEqual(signals[2], 1.0)

    def test_volatility_targeting_rejects_invalid_parameters(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2"):
            generate_volatility_targeting_signals(make_bars([100.0, 101.0]), 1)
        with self.assertRaisesRegex(ValueError, "positive"):
            generate_volatility_targeting_signals(make_bars([100.0, 101.0]), 2, 0.0)

    def test_factor_combo_never_exceeds_component_exposure(self) -> None:
        signals = generate_factor_combo_signals(make_bars([100.0] * 210))

        self.assertTrue(all(signal in (0.0, 1.0) for signal in signals))

    def test_regime_filter_rejects_invalid_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            generate_regime_filter_signals(make_bars([100.0] * 25), 0.0)

    def test_risk_constrained_exposure_is_bounded(self) -> None:
        signals = generate_risk_constrained_signals(make_bars([100.0 + index for index in range(220)]))

        self.assertTrue(all(0.0 <= signal <= 1.0 for signal in signals))


if __name__ == "__main__":
    unittest.main()
