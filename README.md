# autoquant

Offline, constrained research harness for daily ETF strategies.

Start strategy research with [the research playbook](research_playbook.md).
QQQ is the initial sample dataset, not a claim that every hypothesis or result
applies only to QQQ.

The included QQQ sample workflow uses data through 2021 only: 2010-2017
development and 2018-2021 validation. The 2022+ period is locked and available
only to a human-controlled evaluator. Signals use adjusted close, fill on the
following close, and earn returns only after that fill. New universes require
their own approved data, benchmarks, cost assumptions, and evaluation policy.

## Pinned Inputs

```bash
uv sync
uv run python data.py --download
uv run python data.py --download-risk-free
uv run python data.py --download-robustness-panel
```

QQQ and the fixed SPY/IWM/EFA/EEM/TLT/GLD panel come from the project’s Yahoo
Finance downloader. Cash accrual uses FRED `DGS3MO`, the daily three-month
Treasury constant-maturity yield. Each local CSV is hashed and accompanied by
provenance metadata.

## Sandboxed Research Run

```bash
docker build -t autoquant-research:latest .
uv run python sandbox_runner.py
```

The container has no network, a read-only staged filesystem, only research
period QQQ data, and fixed resource limits. It writes the agent-visible result
to `runs/latest_result.json`.

## Ledger and Robustness

```bash
uv run python record_result.py manual_review "baseline" --batch-id initial
uv run python robustness.py --candidate <strategy_sha256>
```

SQLite at `runs/experiments.sqlite` is the append-only event ledger. `results.tsv`
is a derived export; candidate patches and result JSON are immutable artifacts.

```bash
uv run python memory.py summary
uv run python memory.py search --strategy-family trend
uv run python memory.py candidate <strategy_sha256>
```

## Locked Evaluation and Promotion

These commands are human-only and require a clean trusted worktree:

```bash
uv run python evaluation.py --candidate <candidate_id> --batch-id <batch_id> --approval-id <approval_id> --approve-locked-holdout
uv run python promote_candidate.py <candidate_id> --approval-id <approval_id> --reason "review outcome"
```

The evaluator enforces one lookup per batch and three lifetime looks for the
locked period. Detailed holdout results remain outside the agent loop.

## Tests

```bash
uv run python -m unittest discover -s tests
```
