# autoquant

Offline, constrained research harness for daily ETF strategies.

Start strategy research with [the research playbook](research_playbook.md).
QQQ is the initial sample dataset, not a claim that every hypothesis or result
applies only to QQQ.

## Run one daily experiment manually

The daily controller evaluates one predeclared, vetted strategy family in an
isolated Git worktree. It records the experiment and writes a reviewer report;
it never downloads data, promotes a candidate, or accesses the locked holdout.

### First-time setup

From `autoquant/`:

```bash
uv sync
docker build -t autoquant-research:latest .
uv run python -m unittest discover -s tests
```

The repository must be a Git checkout and Docker must be available. Local
market inputs must already be approved and pinned; see [data_policy.md](data_policy.md).

### 1. Create a manifest

Create a new JSON file each day—for example, `manifests/2026-07-13-trend.json`:

```json
{
  "batch_id": "2026-07-13-trend",
  "hypothesis": "A trend-following rule can provide useful risk-adjusted exposure for liquid broad equity ETFs.",
  "strategy_family": "trend",
  "intended_universe": "liquid broad equity ETFs",
  "economic_mechanism": "persistent information diffusion and institutional flows",
  "causal_inputs": "daily adjusted closes known at the signal timestamp",
  "parameter_budget": "one existing vetted family; no parameter changes",
  "expected_failure_regime": "sideways markets and abrupt reversals",
  "rejection_condition": "no improvement over the current baseline after costs"
}
```

Supported families are `trend`, `momentum`, `mean_reversion`,
`volatility_targeting`, `factor_combo`, `regime_filter`, and
`risk_constrained`. Choose one bounded hypothesis; do not tune parameters in
the manifest after seeing results.

### 2. Preflight, then run

```bash
uv run python daily_controller.py --manifest manifests/2026-07-13-trend.json --dry-run
uv run python daily_controller.py --manifest manifests/2026-07-13-trend.json
```

The controller verifies the pinned QQQ and risk-free inputs, checks the
per-batch attempt limit, runs tests and the sandboxed backtest, records the
result with an immutable strategy snapshot, and reverts the temporary
workspace. The batch is limited to 20 attempts and 60 minutes.

### 3. Review the outcome

```bash
uv run python memory.py summary
uv run python memory.py search --strategy-family trend
```

Open the report path printed by the controller under `runs/reports/`. It
contains the hypothesis, source/data hashes, validation metrics, costs, and
the manual-review decision. A result is not a promotion or a locked-holdout
evaluation.

Use a new `batch_id` for a new authorized batch. Re-running the same visible
data is not new evidence; keep the hypothesis and rejection rule fixed before
running it.

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
