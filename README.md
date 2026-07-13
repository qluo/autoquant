# autoquant

Offline, constrained research harness for daily ETF strategies.

Start strategy research with [the research playbook](research_playbook.md).
QQQ is the initial sample dataset, not a claim that every hypothesis or result
applies only to QQQ.

## Daily autonomous research workflow

AutoQuant is a constrained research agent, not a signal scheduler or trading
system. For each authorized daily run, the agent must:

1. Read [research_playbook.md](research_playbook.md), `program.md`, and the
   experiment ledger; use prior failures to avoid repeating ideas.
2. Propose one bounded, falsifiable economic hypothesis, including its intended
   universe and pre-committed rejection condition.
3. Make one focused strategy change in an isolated workspace.
4. Run the fixed tests and sandboxed research backtest.
5. Retain the manifest, source snapshot, result, decision, and a concise
   reviewer-ready report.

It must never trade, access a broker, change trusted evaluation code, download
unapproved data, run a locked evaluation, or promote a candidate.

### Authorize a run

From `autoquant/`, first confirm the local research environment is healthy:

```bash
uv sync
docker build -t autoquant-research:latest .
uv run python -m unittest discover -s tests
uv run python memory.py summary
```

Then authorize an AutoQuant agent session with this scope:

```text
Read program.md, research_playbook.md, and the experiment ledger. Propose one
causal, falsifiable hypothesis for an explicitly named intended universe. Do
not use locked-holdout information. Create a complete experiment manifest, run
one fixed research evaluation in an isolated workspace, record the outcome,
and return the reviewer summary. Do not promote a candidate or access brokers.
```

The agent creates the manifest before it changes strategy logic. A manifest
must state the hypothesis, family, intended universe, mechanism, causal inputs,
parameter budget, expected failure regime, and rejection condition.

### Controller handoff

`daily_controller.py` is the bounded execution component used after the agent
has proposed its manifest. It currently selects one existing vetted family
(`trend`, `momentum`, `mean_reversion`, `volatility_targeting`, `factor_combo`,
`regime_filter`, or `risk_constrained`), runs it in an isolated Git worktree,
records the result, and writes a report under `runs/reports/`.

```bash
uv run python daily_controller.py --manifest <approved-manifest.json> --dry-run
uv run python daily_controller.py --manifest <approved-manifest.json>
```

The controller enforces the per-batch 20-attempt limit and 60-minute wall-clock
budget. It does not itself generate hypotheses or synthesize arbitrary strategy
code; that is the autonomous-agent layer described above. Data refreshes remain
human-approved under [data_policy.md](data_policy.md).

### Review

Open the report path printed by the controller and inspect experiment history:

```bash
uv run python memory.py summary
uv run python memory.py search --strategy-family <family>
```

A reviewer report is evidence for human review, not a promotion or a
locked-holdout evaluation.

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
