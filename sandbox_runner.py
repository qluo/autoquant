from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backtest import LATEST_RESULT_JSON, TRUSTED_FILES, changed_files
from config import VALIDATION_END
from data import DEFAULT_CSV, DEFAULT_TICKER, RISK_FREE_CSV


IMAGE = "autoquant-research:latest"
ROOT = Path(__file__).resolve().parent
SANDBOX_RESULT_NAME = "latest_result.json"


def _clear_stale_sandbox_result(output_dir: Path) -> Path:
    """Remove only the replaceable result produced by the sandbox itself."""
    output = output_dir / SANDBOX_RESULT_NAME
    try:
        output.unlink(missing_ok=True)
    except PermissionError as error:
        raise RuntimeError(
            "sandbox output directory is not writable; restore write access to "
            f"{output_dir} through the approved maintenance process"
        ) from error
    return output


def _copy_research_data(destination: Path, data_path: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    target_path = destination / data_path.name
    with data_path.open(newline="") as source, target_path.open(
        "w", newline=""
    ) as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames or [])
        writer.writeheader()
        for row in reader:
            if row["Date"] <= VALIDATION_END.isoformat():
                writer.writerow(row)
    metadata = data_path.with_suffix(".csv.meta.json")
    if metadata.exists():
        shutil.copy2(metadata, destination / metadata.name)
    for path in (RISK_FREE_CSV, RISK_FREE_CSV.with_suffix(".csv.meta.json")):
        if path.exists():
            shutil.copy2(path, destination / path.name)


def _stage_runner(stage: Path, data_path: Path) -> None:
    for relative_name in TRUSTED_FILES:
        source = ROOT / relative_name
        destination = stage / relative_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(ROOT / "strategy.py", stage / "strategy.py")
    _copy_research_data(stage / "data", data_path)


def run_sandboxed_backtest(
    data_path: Path = DEFAULT_CSV, ticker: str = DEFAULT_TICKER
) -> Path:
    trusted_changes = [
        path
        for path in changed_files()
        if path in TRUSTED_FILES or path.startswith("tests/")
    ]
    if trusted_changes:
        raise RuntimeError(
            "sandbox requires a clean trusted worktree; changed files: "
            + ", ".join(trusted_changes)
        )
    output_dir = ROOT / "runs" / "sandbox"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = _clear_stale_sandbox_result(output_dir)
    with tempfile.TemporaryDirectory(prefix="autoquant-stage-") as temp_dir:
        stage = Path(temp_dir)
        _stage_runner(stage, data_path)
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--pids-limit",
            "128",
            "--memory",
            "512m",
            "--cpus",
            "1.0",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,src={stage},dst=/app,readonly",
            "--mount",
            f"type=bind,src={output_dir},dst=/output",
            "--workdir",
            "/app",
            IMAGE,
            "python",
            "backtest.py",
            "--data",
            f"data/{data_path.name}",
            "--ticker",
            ticker,
            "--output",
            "/output/latest_result.json",
        ]
        subprocess.run(command, check=True)
    if not output.exists():
        raise RuntimeError("sandboxed backtest did not write a result")
    shutil.copy2(output, LATEST_RESULT_JSON)
    return LATEST_RESULT_JSON


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    args = parser.parse_args()
    output = run_sandboxed_backtest(args.data, args.ticker)
    print(f"wrote sandboxed result to {output}")


if __name__ == "__main__":
    main()
