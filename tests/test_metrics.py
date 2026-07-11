from __future__ import annotations

import unittest

from metrics import compound_return, max_drawdown, sharpe_ratio, sortino_ratio


class MetricsTests(unittest.TestCase):
    def test_compound_return(self) -> None:
        self.assertAlmostEqual(compound_return([0.10, -0.10]), -0.01)

    def test_max_drawdown(self) -> None:
        self.assertAlmostEqual(max_drawdown([0.10, -0.20, 0.05]), -0.20)

    def test_zero_volatility_ratios_are_zero(self) -> None:
        self.assertEqual(sharpe_ratio([0.0, 0.0]), 0.0)
        self.assertEqual(sortino_ratio([0.0, 0.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
