from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApprovedUniverse:
    identifier: str
    ticker: str
    data_path: Path
    benchmark_name: str


APPROVED_UNIVERSES = {
    "qqq": ApprovedUniverse(
        identifier="qqq",
        ticker="QQQ",
        data_path=Path("data/qqq.csv"),
        benchmark_name="buy_and_hold_QQQ",
    ),
}


def get_universe(identifier: str) -> ApprovedUniverse:
    try:
        return APPROVED_UNIVERSES[identifier]
    except KeyError as error:
        raise ValueError(f"unapproved research universe: {identifier}") from error
