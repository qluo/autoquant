from __future__ import annotations

import datetime as dt
import unittest

from backtest import BacktestResult, MetricSummary, _daily_strategy_returns, result_to_dict
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
            adjusted_close=close,
            volume=1_000_000,
        )
        for index, close in enumerate(closes)
    ]


class BacktestTests(unittest.TestCase):
    def test_signal_executes_on_next_bar(self) -> None:
        bars = make_bars([100.0, 110.0, 90.0])
        returns, _, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 0.0],
            transaction_cost_bps=0.0,
        )

        self.assertEqual(returns[0], 0.0)
        self.assertAlmostEqual(returns[1], 90.0 / 110.0 - 1.0)

    def test_transaction_costs_penalize_turnover(self) -> None:
        bars = make_bars([100.0, 100.0, 100.0, 100.0])
        no_cost_returns, _, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 1.0, 0.0],
            transaction_cost_bps=0.0,
        )
        cost_returns, _, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 1.0, 0.0],
            transaction_cost_bps=10.0,
        )

        self.assertEqual(sum(no_cost_returns), 0.0)
        self.assertLess(sum(cost_returns), 0.0)

    def test_returns_use_adjusted_close(self) -> None:
        bars = make_bars([100.0, 110.0, 90.0])
        bars[2] = Bar(
            date=bars[2].date,
            open=90.0,
            high=90.0,
            low=90.0,
            close=90.0,
            adjusted_close=121.0,
            volume=bars[2].volume,
        )

        returns, _, _ = _daily_strategy_returns(
            bars=bars,
            signals=[1.0, 0.0, 0.0],
            transaction_cost_bps=0.0,
        )

        self.assertAlmostEqual(returns[1], 121.0 / 110.0 - 1.0)

    def test_result_json_contract(self) -> None:
        summary = MetricSummary(
            total_return=0.1,
            annual_return=0.05,
            annual_volatility=0.2,
            sharpe=0.25,
            sortino=0.3,
            max_drawdown=-0.1,
            annual_turnover=2.0,
            num_trades=4,
            composite_score=0.12,
        )
        result = BacktestResult(
            full=summary,
            development=summary,
            validation=summary,
            benchmark=summary,
            excess_annual_return=0.01,
            tracking_error=0.02,
            information_ratio=0.5,
            beta=0.8,
            correlation=0.9,
            average_exposure=0.7,
            percent_days_invested=0.7,
            annual_metrics={"2021": {"total_return": 0.1}},
            validation_folds={"2020-01-01_2021-12-31": {"sharpe": 0.4}},
            cost_scenarios={"2_bps": {"composite_score": 0.12}},
            start_date="2010-01-04",
            end_date="2021-12-31",
            num_bars=100,
        )

        payload = result_to_dict(result, ticker="QQQ")

        self.assertEqual(payload["ticker"], "QQQ")
        self.assertEqual(payload["evaluation_mode"], "research")
        self.assertEqual(payload["metrics"]["validation"]["composite_score"], 0.12)
        self.assertEqual(payload["metrics"]["validation"]["num_trades"], 4)
        self.assertNotIn("holdout", payload["metrics"])


if __name__ == "__main__":
    unittest.main()
