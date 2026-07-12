from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ledger import append_event, export_attempts_tsv


LATEST_RESULT_JSON = Path("runs/latest_result.json")
ATTEMPTS_DIR = Path("runs/attempts")
PATCHES_DIR = Path("runs/patches")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    )
    return result.stdout


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_stem(strategy_sha256: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{strategy_sha256[:12]}"


def append_result(
    status: str,
    hypothesis: str,
    batch_id: str,
    strategy_family: str,
    parent_candidate: str | None,
    reason: str,
) -> int:
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

    stem = _artifact_stem(strategy_sha256)
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    patch_path = PATCHES_DIR / f"{stem}.diff"
    patch_path.write_text(_git("diff", "--", "strategy.py"))
    result_path: Path | None = None
    validation: dict[str, object] = {}
    row: dict[str, object] = {
        "status": status,
        "hypothesis": hypothesis,
        "strategy_sha256": strategy_sha256,
        "commit": _git("rev-parse", "--short", "HEAD").strip(),
        "strategy_family": strategy_family,
        "universe": "QQQ",
        "parent_candidate": parent_candidate,
        "reason": reason,
        "config_sha256": _sha256(Path("config.py")),
        "patch_path": str(patch_path),
    }
    if payload:
        ATTEMPTS_DIR.mkdir(parents=True, exist_ok=True)
        result_path = ATTEMPTS_DIR / f"{stem}.json"
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        validation = payload["metrics"]["validation"]
        row.update(
            {
                "ticker": payload["ticker"],
                "harness_sha256": payload["integrity"]["harness_sha256"],
                "data_sha256": payload["data"]["sha256"],
                "validation_score": validation["composite_score"],
                "validation_sharpe": validation["sharpe"],
                "validation_max_drawdown": validation["max_drawdown"],
                "result_path": str(result_path),
            }
        )

    event_id = append_event(
        "attempt", row, batch_id=batch_id, candidate_id=strategy_sha256
    )
    export_attempts_tsv()
    return event_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "status", choices=["discarded", "invalid", "crashed", "manual_review"]
    )
    parser.add_argument("hypothesis")
    parser.add_argument("--batch-id", default="default")
    parser.add_argument("--strategy-family", default="unspecified")
    parser.add_argument("--parent-candidate")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    event_id = append_result(
        args.status,
        args.hypothesis,
        args.batch_id,
        args.strategy_family,
        args.parent_candidate,
        args.reason,
    )
    print(f"recorded attempt event {event_id}")


if __name__ == "__main__":
    main()
