from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


LATEST_RESULT_JSON = Path("runs/latest_result.json")
RESULTS_TSV = Path("results.tsv")
PATCHES_DIR = Path("runs/patches")
FIELDNAMES = [
    "attempt",
    "commit",
    "ticker",
    "strategy_sha256",
    "harness_sha256",
    "data_sha256",
    "validation_score",
    "validation_sharpe",
    "validation_max_drawdown",
    "excess_annual_return",
    "annual_turnover",
    "num_trades",
    "status",
    "hypothesis",
    "result_path",
    "patch_path",
]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    )
    return result.stdout


def current_commit() -> str:
    return _git("rev-parse", "--short", "HEAD").strip()


def next_attempt() -> int:
    if not RESULTS_TSV.exists():
        return 1
    with RESULTS_TSV.open(newline="") as file:
        return sum(1 for _ in csv.DictReader(file, delimiter="\t")) + 1


def _save_strategy_patch(attempt: int) -> Path:
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    path = PATCHES_DIR / f"{attempt:04d}-strategy.diff"
    path.write_text(_git("diff", "--", "strategy.py"))
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_result(status: str, hypothesis: str) -> Path:
    strategy_sha256 = _sha256(Path("strategy.py"))
    payload = (
        json.loads(LATEST_RESULT_JSON.read_text())
        if LATEST_RESULT_JSON.exists()
        else None
    )
    if payload and payload["integrity"]["strategy_sha256"] != strategy_sha256:
        payload = None
    if payload is None and status not in {"invalid", "crashed"}:
        raise FileNotFoundError(
            "no result exists for the current strategy; record it as invalid or crashed"
        )

    validation = payload["metrics"]["validation"] if payload else {}
    integrity = payload["integrity"] if payload else {}
    attempt = next_attempt()
    patch_path = _save_strategy_patch(attempt)
    result_path = Path("runs") / f"{attempt:04d}-result.json"
    if payload:
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    row = {
        "attempt": str(attempt),
        "commit": current_commit(),
        "ticker": payload["ticker"] if payload else "QQQ",
        "strategy_sha256": strategy_sha256,
        "harness_sha256": integrity.get("harness_sha256", ""),
        "data_sha256": payload["data"]["sha256"] if payload else "",
        "validation_score": (
            f"{validation['composite_score']:.6f}" if payload else ""
        ),
        "validation_sharpe": f"{validation['sharpe']:.6f}" if payload else "",
        "validation_max_drawdown": (
            f"{validation['max_drawdown']:.6f}" if payload else ""
        ),
        "excess_annual_return": (
            f"{payload['relative_metrics']['excess_annual_return']:.6f}"
            if payload
            else ""
        ),
        "annual_turnover": (
            f"{validation['annual_turnover']:.6f}" if payload else ""
        ),
        "num_trades": str(validation["num_trades"]) if payload else "",
        "status": status,
        "hypothesis": hypothesis,
        "result_path": str(result_path) if payload else "",
        "patch_path": str(patch_path),
    }

    write_header = not RESULTS_TSV.exists()
    with RESULTS_TSV.open("a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, delimiter="\t")
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return RESULTS_TSV


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "status",
        choices=["discarded", "invalid", "crashed", "manual_review"],
    )
    parser.add_argument("hypothesis")
    args = parser.parse_args()

    path = append_result(args.status, args.hypothesis)
    print(f"recorded attempt as {args.status} in {path}")


if __name__ == "__main__":
    main()
