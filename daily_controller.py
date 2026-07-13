from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from config import MAX_EXPERIMENT_ATTEMPTS, MAX_EXPERIMENT_MINUTES
from experiment_manifest import ExperimentManifest
from ledger import read_events
from record_result import append_result
from reviewer_summary import write_summary


ROOT = Path(__file__).resolve().parent
REQUIRED_INPUTS = (
    ROOT / "data/qqq.csv",
    ROOT / "data/qqq.csv.meta.json",
    ROOT / "data/risk_free_3m.csv",
    ROOT / "data/risk_free_3m.csv.meta.json",
)


def _validate_inputs() -> None:
    missing = [str(path) for path in REQUIRED_INPUTS if not path.exists()]
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


def _run(command: list[str], cwd: Path, timeout: int) -> None:
    subprocess.run(command, cwd=cwd, check=True, timeout=timeout)


def run_daily_experiment(manifest: ExperimentManifest, dry_run: bool = False) -> Path | None:
    _validate_inputs()
    if _remaining_attempts(manifest.batch_id) <= 0:
        raise RuntimeError(f"batch {manifest.batch_id} has exhausted its attempt budget")
    if dry_run:
        return None

    timeout = MAX_EXPERIMENT_MINUTES * 60
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="autoquant-daily-") as temporary:
        workspace = Path(temporary) / "workspace"
        _run(["git", "worktree", "add", "--detach", str(workspace), "HEAD"], ROOT, timeout)
        try:
            _set_strategy_family(workspace / "strategy.py", manifest.strategy_family)
            _run(["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests"], workspace, timeout)
            _run(["docker", "build", "-t", "autoquant-research:latest", "."], workspace, timeout)
            remaining = timeout - int(time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("daily research budget exhausted before sandbox run")
            _run(["uv", "run", "python", "sandbox_runner.py"], workspace, remaining)
            shutil.copy2(workspace / "runs/latest_result.json", ROOT / "runs/latest_result.json")
            event_id = append_result(
                "manual_review",
                manifest.hypothesis,
                manifest.batch_id,
                manifest.strategy_family,
                None,
                "daily controller completed fixed research evaluation",
                manifest,
                workspace / "strategy.py",
            )
            output = ROOT / "runs/reports" / f"{manifest.batch_id}-{event_id}.md"
            return write_summary(manifest, ROOT / "runs/latest_result.json", "manual review", output)
        finally:
            _run(["git", "worktree", "remove", "--force", str(workspace)], ROOT, timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one bounded daily research experiment.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_daily_experiment(ExperimentManifest.from_path(args.manifest), args.dry_run)
    if report is None:
        print("daily controller preflight passed")
    else:
        print(f"wrote reviewer summary to {report}")


if __name__ == "__main__":
    main()
