from __future__ import annotations

import datetime as dt
import unittest

from backtest import _daily_strategy_returns
from data import Bar


def make_bars(closes: list[float]) -> list[Bar]:
    start = dt.date(2024, 1, 1)
    return [
        Bar(
            date=start + dt.timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000_000,
        )
        for index, close in enumerate(closes)
    ]


class BacktestTests(unittest.TestCase):
    def test_signal_executes_on_next_bar(self) -> None:
        bars = make_bars([100.0, 110.0, 90.0])
        returns, _ = _daily_strategy_returns(
            bars=bars,
            signals=[0.0, 1.0, 0.0],
            transaction_cost_bps=0.0,
        )

        self.assertEqual(returns[0], 0.0)
        self.assertAlmostEqual(returns[1], 90.0 / 110.0 - 1.0)

    def test_transaction_costs_penalize_turnover(self) -> None:
        bars = make_bars([100.0, 100.0, 100.0, 100.0])
        no_cost_returns, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 1.0, 0.0],
            transaction_cost_bps=0.0,
        )
        cost_returns, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 1.0, 0.0],
            transaction_cost_bps=10.0,
        )

        self.assertEqual(sum(no_cost_returns), 0.0)
        self.assertLess(sum(cost_returns), 0.0)


if __name__ == "__main__":
    unittest.main()
