from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict
from pathlib import Path

from backtest import RUNS_DIR, run_backtest
from config import ROBUSTNESS_CORE_TICKERS, ROBUSTNESS_STRESS_TICKERS
from data import load_bars, ticker_csv_path


def evaluate_ticker(ticker: str) -> dict[str, object]:
    path = ticker_csv_path(ticker)
    result = run_backtest(load_bars(path))
    return {
        "ticker": ticker,
        "data_path": str(path),
        "risk_free": result.risk_free,
        "validation": asdict(result.validation),
        "benchmark": asdict(result.benchmark),
        "relative_metrics": {
            "excess_annual_return": result.excess_annual_return,
            "information_ratio": result.information_ratio,
            "beta": result.beta,
            "correlation": result.correlation,
        },
        "validation_folds": result.validation_folds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()

    core_results = [evaluate_ticker(ticker) for ticker in ROBUSTNESS_CORE_TICKERS]
    stress_results = [evaluate_ticker(ticker) for ticker in ROBUSTNESS_STRESS_TICKERS]
    core_excess = [
        result["relative_metrics"]["excess_annual_return"] for result in core_results
    ]
    stress_drawdowns = [result["validation"]["max_drawdown"] for result in stress_results]
    results = {
        "candidate": args.candidate,
        "core_confirmation": core_results,
        "cross_asset_stress": stress_results,
        "summary": {
            "core_median_excess_annual_return": statistics.median(core_excess),
            "core_positive_excess_count": sum(value > 0.0 for value in core_excess),
            "stress_worst_max_drawdown": min(stress_drawdowns),
        },
    }
    output_dir = RUNS_DIR / "robustness"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{args.candidate}.json"
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"wrote robustness report to {output}")


if __name__ == "__main__":
    main()
