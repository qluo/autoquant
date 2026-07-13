from __future__ import annotations

import unittest

from metrics import (
    annualized_excess_return,
    compound_return,
    downside_deviation,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    information_ratio,
)


class MetricsTests(unittest.TestCase):
    def test_compound_return(self) -> None:
        self.assertAlmostEqual(compound_return([0.10, -0.10]), -0.01)

    def test_max_drawdown(self) -> None:
        self.assertAlmostEqual(max_drawdown([0.10, -0.20, 0.05]), -0.20)

    def test_zero_volatility_ratios_are_zero(self) -> None:
        self.assertEqual(sharpe_ratio([0.0, 0.0]), 0.0)
        self.assertEqual(sortino_ratio([0.0, 0.0]), 0.0)

    def test_ratios_use_arithmetic_daily_excess_returns(self) -> None:
        returns = [0.01, 0.03]
        self.assertAlmostEqual(annualized_excess_return(returns), 5.04)
        self.assertGreater(sharpe_ratio(returns), 0.0)
        self.assertAlmostEqual(
            downside_deviation(returns), 0.0
        )
        self.assertEqual(sortino_ratio(returns), 0.0)

    def test_risk_free_rate_is_subtracted_before_ratios(self) -> None:
        returns = [0.01, 0.03]
        self.assertAlmostEqual(
            annualized_excess_return(returns, risk_free_daily=0.01), 2.52
        )

    def test_sharpe_volatility_uses_excess_returns(self) -> None:
        returns = [0.01, 0.03]
        risk_free = [0.01, 0.01]

        expected = 2.52 / (0.01 * (2 ** 0.5) * (252 ** 0.5))
        self.assertAlmostEqual(sharpe_ratio(returns, risk_free), expected)

    def test_information_ratio_uses_arithmetic_active_return(self) -> None:
        self.assertAlmostEqual(
            information_ratio([0.10, -0.10], [0.0, 0.0]), 0.0
        )


if __name__ == "__main__":
    unittest.main()
