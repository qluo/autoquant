from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from config import MAX_CANDIDATES_ADVANCED, MAX_EFFECTIVE_HYPOTHESES, MAX_EXPERIMENT_ATTEMPTS, MAX_EXPERIMENT_MINUTES
from experiment_manifest import ExperimentManifest
from ledger import read_events, reserve_selection_candidate, reserve_selection_hypothesis
from record_result import append_result
from reviewer_summary import write_summary
from universe_registry import ApprovedUniverse, get_universe


ROOT = Path(__file__).resolve().parent
RISK_FREE_INPUTS = (
    ROOT / "data/risk_free_3m.csv",
    ROOT / "data/risk_free_3m.csv.meta.json",
)


def _require_primary_checkout(root: Path = ROOT) -> None:
    if not (root / ".git").is_dir():
        raise RuntimeError(
            "daily controller must run from the primary repository checkout, "
            "not a linked or temporary Git worktree"
        )


def _validate_inputs(universe: ApprovedUniverse) -> None:
    data_path = ROOT / universe.data_path
    required = (*RISK_FREE_INPUTS, data_path, data_path.with_suffix(".csv.meta.json"))
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing approved inputs: " + ", ".join(missing))


def _remaining_attempts(batch_id: str) -> int:
    used = sum(
        event["event_type"] == "attempt" and event["batch_id"] == batch_id
        for event in read_events()
    )
    return MAX_EXPERIMENT_ATTEMPTS - used


def _set_strategy_family(path: Path, family: str) -> None:
    source = path.read_text()
    supported = set(re.findall(r'STRATEGY_FAMILY == "([a-z_]+)"', source))
    if family not in supported:
        raise ValueError(f"unsupported strategy family: {family}")
    updated, count = re.subn(
        r'STRATEGY_FAMILY = "[a-z_]+"', f'STRATEGY_FAMILY = "{family}"', source, count=1
    )
    if count != 1:
        raise RuntimeError("could not select strategy family")
    path.write_text(updated)


def _reviewed_strategy_source(source: Path) -> Path:
    expected = (ROOT / "strategy.py").resolve()
    if source.resolve() != expected:
        raise ValueError("reviewed strategy source must be the primary checkout's strategy.py")
    if not expected.is_file():
        raise FileNotFoundError(f"missing reviewed strategy source: {expected}")
    return expected


def _workspace_result_path(workspace: Path) -> Path:
    candidates = (
        workspace / "runs/latest_result.json",
        workspace / "runs/sandbox/latest_result.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "sandbox completed without a result; checked: "
        + ", ".join(str(path) for path in candidates)
    )


def _run(command: list[str], cwd: Path, timeout: int) -> None:
    subprocess.run(command, cwd=cwd, check=True, timeout=timeout)


def run_daily_experiment(
    manifest: ExperimentManifest,
    dry_run: bool = False,
    strategy_source: Path | None = None,
) -> Path | None:
    universe = get_universe(manifest.universe_id)
    _validate_inputs(universe)
    if _remaining_attempts(manifest.batch_id) <= 0:
        raise RuntimeError(f"batch {manifest.batch_id} has exhausted its attempt budget")
    if dry_run:
        return None

    reservation_id, created = reserve_selection_hypothesis(
        selection_dataset_id=manifest.selection_dataset_id,
        hypothesis_id=manifest.hypothesis_id,
        fingerprint=manifest.selection_fingerprint(),
        payload={"manifest": manifest.as_payload()},
        max_effective_hypotheses=MAX_EFFECTIVE_HYPOTHESES,
    )

    timeout = MAX_EXPERIMENT_MINUTES * 60
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="autoquant-daily-") as temporary:
        workspace = Path(temporary) / "workspace"
        _run(["git", "worktree", "add", "--detach", str(workspace), "HEAD"], ROOT, timeout)
        try:
            if strategy_source is None:
                _set_strategy_family(workspace / "strategy.py", manifest.strategy_family)
            else:
                shutil.copy2(_reviewed_strategy_source(strategy_source), workspace / "strategy.py")
            _run(["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests"], workspace, timeout)
            _run(["docker", "build", "-t", "autoquant-research:latest", "."], workspace, timeout)
            remaining = timeout - int(time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("daily research budget exhausted before sandbox run")
            _run(
                [
                    "uv", "run", "python", "sandbox_runner.py",
                    "--data", str(universe.data_path), "--ticker", universe.ticker,
                    "--selection-reservation-id", str(reservation_id),
                ],
                workspace,
                remaining,
            )
            strategy_sha256 = hashlib.sha256((workspace / "strategy.py").read_bytes()).hexdigest()
            candidate_id, candidate_created = reserve_selection_candidate(
                selection_dataset_id=manifest.selection_dataset_id,
                candidate_id=strategy_sha256,
                max_candidates_advanced=MAX_CANDIDATES_ADVANCED,
            )
            shutil.copy2(_workspace_result_path(workspace), ROOT / "runs/latest_result.json")
            event_id = append_result(
                "manual_review",
                manifest.hypothesis,
                manifest.batch_id,
                manifest.strategy_family,
                None,
                f"selection reservation {reservation_id} "
                f"({'new' if created else 'existing'}), candidate reservation {candidate_id} "
                f"({'new' if candidate_created else 'existing'}); controller completed fixed research evaluation",
                manifest,
                workspace / "strategy.py",
            )
            output = ROOT / "runs/reports" / f"{manifest.batch_id}-{event_id}.html"
            return write_summary(manifest, ROOT / "runs/latest_result.json", "manual review", output)
        finally:
            _run(["git", "worktree", "remove", "--force", str(workspace)], ROOT, timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one bounded daily research experiment.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--strategy-source",
        type=Path,
        help="use the reviewed primary-checkout strategy.py, including uncommitted ML code",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    _require_primary_checkout()
    os.chdir(ROOT)
    report = run_daily_experiment(
        ExperimentManifest.from_path(manifest_path),
        args.dry_run,
        args.strategy_source.resolve() if args.strategy_source else None,
    )
    if report is None:
        print("daily controller preflight passed")
    else:
        print(f"wrote reviewer summary to {report}")


if __name__ == "__main__":
    main()
