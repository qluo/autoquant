from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from backtest import (
    RUNS_DIR,
    TRUSTED_FILES,
    _daily_strategy_returns,
    _metric_summary,
    changed_files,
)
from config import DEFAULT_TRANSACTION_COST_BPS, HOLDOUT_START
from data import DEFAULT_CSV, Bar, load_bars, load_risk_free_daily
from strategy import generate_signals
from validate import validate_bars, validate_signals, validate_strategy_causality


LOCKED_RESULTS_DIR = RUNS_DIR / "locked"


def evaluate_locked_holdout(
    bars: list[Bar],
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
) -> dict[str, object]:
    validate_bars(bars)
    signals = generate_signals(bars)
    validate_signals(signals, bars)
    validate_strategy_causality(generate_signals, bars, signals)
    risk_free_daily, risk_free_metadata = load_risk_free_daily(bars)
    returns, turnovers, _ = _daily_strategy_returns(
        bars, signals, transaction_cost_bps, risk_free_daily
    )
    return_dates = [bar.date for bar in bars[1:]]
    holdout_indices = [
        index for index, date in enumerate(return_dates) if date >= HOLDOUT_START
    ]
    if not holdout_indices:
        raise ValueError(f"bars do not cover locked holdout from {HOLDOUT_START}")

    benchmark_returns, benchmark_turnovers, _ = _daily_strategy_returns(
        bars, [1.0] * len(bars), transaction_cost_bps, risk_free_daily
    )
    interval_risk_free = risk_free_daily[1:]
    holdout = _metric_summary(
        [returns[index] for index in holdout_indices],
        [turnovers[index] for index in holdout_indices],
        [interval_risk_free[index] for index in holdout_indices],
    )
    benchmark = _metric_summary(
        [benchmark_returns[index] for index in holdout_indices],
        [benchmark_turnovers[index] for index in holdout_indices],
        [interval_risk_free[index] for index in holdout_indices],
    )
    return {
        "evaluation_mode": "locked_holdout",
        "holdout_start": str(HOLDOUT_START),
        "holdout_end": str(return_dates[holdout_indices[-1]]),
        "metrics": asdict(holdout),
        "benchmark": {"name": "buy_and_hold_QQQ", **asdict(benchmark)},
        "risk_free": risk_free_metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--approve-locked-holdout", action="store_true")
    args = parser.parse_args()

    if not args.approve_locked_holdout:
        parser.error("locked holdout requires --approve-locked-holdout")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.candidate):
        parser.error("candidate must contain only letters, numbers, '_' or '-'")

    trusted_changes = [
        path
        for path in changed_files()
        if path in TRUSTED_FILES or path.startswith("tests/")
    ]
    if trusted_changes:
        raise RuntimeError(
            "locked evaluation requires a clean trusted worktree; changed files: "
            + ", ".join(trusted_changes)
        )

    payload = evaluate_locked_holdout(load_bars(DEFAULT_CSV))
    LOCKED_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = LOCKED_RESULTS_DIR / f"{args.candidate}.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote locked evaluation to {output}")


if __name__ == "__main__":
    main()
