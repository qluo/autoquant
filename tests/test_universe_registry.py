from __future__ import annotations

import unittest

from universe_registry import get_universe


class UniverseRegistryTests(unittest.TestCase):
    def test_qqq_is_an_approved_research_universe(self) -> None:
        universe = get_universe("qqq")

        self.assertEqual(universe.ticker, "QQQ")
        self.assertEqual(str(universe.data_path), "data/qqq.csv")

    def test_rejects_unapproved_universe(self) -> None:
        with self.assertRaisesRegex(ValueError, "unapproved"):
            get_universe("spy")


if __name__ == "__main__":
    unittest.main()
