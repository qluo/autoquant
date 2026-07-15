# AutoQuant Implementation Plan

## Goal

Build a constrained offline backtesting agent for exploratory quant research.

The agent should help generate, run, compare, and remember trading-strategy experiments, but it must not trade live, access brokers, or modify the trusted backtest/evaluation harness.

Core loop:

```text
research idea
-> structured experiment plan
-> human approval
-> edit constrained strategy file
-> run standardized offline backtest
-> evaluate against development and validation evidence
-> promote/discard
-> log experiment memory
```

The agent is a research assistant, not the final judge of a strategy. A strategy
may be promoted only through a separately controlled evaluation process; it may
not be declared robust merely because it maximizes a visible backtest score.

## Design Principles

1. Offline only.
   No live trading, broker APIs, order placement, or capital allocation.

2. Fixed evaluator.
   The agent may edit strategy logic, but not the backtest engine, data splits, cost model, or risk checks.

3. Reproducible experiments.
   Every run should record code version, data version, parameters, metrics, and decision.

4. Bias control first.
   The system should explicitly guard against lookahead bias, survivorship bias, leakage, overfitting, and unrealistic costs.

5. Human approval gates.
   A human approves experiment plans and any expansion of data access, compute budget, or evaluation scope.

6. Selection integrity.
   The agent may iterate on development and validation data, but it must not
   repeatedly select strategies using the locked final holdout. Every attempt,
   including rejected attempts, is retained for audit.

7. Verifiable boundaries.
   Trusted evaluator code, configuration, data, and experiment records are
   protected or verified mechanically; instructions alone are not a boundary.

## Proposed Directory Structure

```text
autoquant/
  README.md
  program.md
  Dockerfile
  pyproject.toml
  data.py
  backtest.py
  strategy.py
  metrics.py
  validate.py
  sandbox_runner.py
  ledger.py
  promote_candidate.py
  robustness.py
  results.tsv
  evaluation.py
  config.py
  tests/
    test_metrics.py
    test_backtest.py
    test_evaluation.py
    test_data.py
    test_no_lookahead.py
  docs/
    data_policy.md
    implementation_plan.md
    research_playbook.md
    project_structure.md
```

Initial file roles:

- `program.md`: instructions for the research agent.
- `research_playbook.md`: universe-agnostic hypothesis and experiment-design
  guidance; QQQ is an initial sample dataset, not the research objective.
- `data.py`: fixed data loading, cleaning, and evaluation-dataset selection.
- `backtest.py`: fixed backtest harness and portfolio simulation.
- `metrics.py`: fixed performance and risk metrics.
- `validate.py`: fixed validation checks for leakage, dates, costs, and outputs.
- `sandbox_runner.py`: trusted Docker staging and execution wrapper.
- `ledger.py`: append-only SQLite event ledger and TSV exporter.
- `promote_candidate.py`: human-only promotion event recorder.
- `robustness.py`: frozen-candidate panel evaluator.
- `evaluation.py`: trusted promotion and locked-holdout workflow.
- `config.py`: trusted evaluation windows, cost scenarios, and policy limits.
- `strategy.py`: the only file the agent edits during experiments.
- `results.tsv`: derived human-readable export of the authoritative SQLite ledger.

## Technical Design

### Runtime Model

AutoQuant is a local, offline-first Python project. The trusted research harness is normal Python code, while the research agent is constrained by process and file boundaries.

Core runtime command:

```bash
uv run python backtest.py
```

The command should:

1. Load local historical data.
2. Validate market data.
3. Call `strategy.generate_signals`.
4. Validate strategy output.
5. Shift signals into next-bar positions.
6. Apply transaction costs.
7. Compute full-period, development, and validation metrics; emit locked-holdout
   metrics only in the separately authorized evaluation mode.
8. Print a human-readable summary.
9. Write machine-readable output for the agent.

### Trust Boundaries

Trusted files:

```text
data.py
backtest.py
metrics.py
validate.py
evaluation.py
config.py
tests/
```

These files define the evaluation contract. During autonomous experiments they
are mounted read-only (or run from a clean, trusted checkout) and their hashes
are recorded with every result. The acceptance command rejects any unexpected
change outside `strategy.py` and approved generated artifacts.

Editable research file:

```text
strategy.py
```

The agent can edit this file to test strategy ideas. It must return one target exposure per input bar.

Generated artifacts:

```text
data/
runs/
results.tsv
run.log
```

`runs/` may contain machine-readable results, logs, and saved candidate patches.
The SQLite event ledger is append-only and must record discarded, invalid, and
crashed attempts as well as promotions and holdout lookups. Generated artifacts
are retained for audit even when a candidate patch is reverted.

### Data Contract

Input data is daily OHLCV:

```text
Date, Open, High, Low, Close, Adj Close, Volume
```

QQQ daily data is the initial sample dataset. Additional single-asset datasets
can use the same schema; strategies requiring cross-sectional ranking or
portfolio construction need an expanded, explicitly approved interface.

`data.Bar` is the in-memory representation of one daily OHLCV row:

```text
date, open, high, low, close, adjusted_close, volume
```

For the initial daily ETF model, portfolio returns and benchmark returns use
`adjusted_close`, which represents a split- and distribution-adjusted
total-return series. Raw OHLC remains available for data quality checks and for
future execution models. A future execution model that uses raw fills must
model distributions and corporate actions explicitly; adjusted close is not a
literal executable fill price.

Every run records the data source, retrieval timestamp, ticker, date range,
calendar, adjustment convention, row count, missing-session policy, and SHA-256
hash of the exact input file.

### Strategy Contract

`strategy.py` exposes:

```python
def generate_signals(bars: list[Bar]) -> list[float]:
    ...
```

Rules:

- Return length must equal input bar count.
- Each signal is target exposure for that date.
- `0.0` means cash.
- `1.0` means fully long.
- Values must be finite.
- Values must stay within the configured leverage bound.
- Same-day signals are executed on the next bar by `backtest.py`.

This contract lets the agent research strategy logic without controlling execution mechanics.
During autonomous runs, `strategy.py` is treated as untrusted code. It runs in
a container without network access, cannot write outside its temporary run
directory, cannot read experiment results or locked data, and is limited to
approved imports and fixed compute limits. A restricted strategy DSL or
approved causal feature library is deferred until the containerized workflow
reveals which primitives are worth supporting.

### Backtest Contract

`backtest.py` owns execution semantics:

- Daily close-to-close returns.
- Next-bar execution.
- Long-only exposure for the initial version.
- Transaction cost charged on absolute position change.
- Fixed development, validation, and locked-holdout policy.
- Standard metric calculation.

The agent should treat this file as read-only during experiments.

The initial daily event timeline is deliberately conservative:

```text
after close[t]:       observe data through adjusted_close[t] and compute signal[t]
before close[t + 1]:  submit the already-computed target order
at close[t + 1]:      apply the position change and transaction cost
close[t + 1]..[t + 2]: the new position earns the next close-to-close return
```

Thus a signal never earns the return whose close was used to calculate it. The
implementation and tests must use this timeline exactly. Any later open-price,
MOC/LOC, or intraday model is a separate, explicitly approved execution model.

### Metric Contract

Development ranking uses a composite score, but promotion is not based on one
number alone. A candidate must first satisfy validation, integrity, robustness,
and benchmark-relative constraints.

Supporting metrics:

- Total return.
- Annualized return.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio.
- Max drawdown.
- Annual turnover.
- Number of trades.
- Development and validation composite scores.
- Development and validation Sharpe and max drawdown.
- Locked-holdout metrics, emitted only by the human-triggered evaluator.
- Buy-and-hold benchmark metrics.
- Excess annual return, tracking error, information ratio, beta, and correlation.
- Average exposure, percent of days invested, and annual/subperiod metrics.

Metric conventions:

- Use 252 trading days per year.
- Compute Sharpe from the arithmetic mean of daily excess returns divided by
  their sample standard deviation, annualized by `sqrt(252)`.
- Compute Sortino from the arithmetic mean of daily excess returns divided by
  downside deviation, annualized by `sqrt(252)`.
- Use a zero risk-free rate for the current development/validation harness and
  label that assumption in every result.
- If volatility or downside deviation is zero, report the corresponding ratio
  as `0.0` and emit a diagnostic flag; never emit NaN or infinity into ranking.
- Before the first locked-holdout evaluation, add a pinned daily three-month
  Treasury-bill proxy, accrue it to cash exposure, and use the same series for
  excess-return metrics. Adding this series requires human data-source approval.

The composite score is intentionally simple at first. It is a development
ranking aid, not evidence of a deployable edge. Its inputs and components must
be emitted separately, and ranking sensitivity to reasonable weight changes
must be checked before a promotion decision.

### Agent Loop Design

The exploratory research loop should work like this:

```text
1. Read program.md, research_playbook.md, and the append-only experiment
   ledger. State the intended universe before proposing a hypothesis.
2. Inspect development/validation baselines and the current champion.
3. Propose one falsifiable strategy hypothesis.
4. Edit only strategy.py in the research worktree.
5. Run the development/validation backtest in the restricted runner.
6. The trusted runner checks hashes, changed-file allowlist, causal behavior,
   validation rules, benchmarks, and required cost scenarios.
7. The trusted recorder saves metrics and the candidate patch, then appends the
   attempt to results.tsv before any revert decision.
8. Promote only candidates that meet the stated challenger criteria; otherwise
   discard the working-tree change while retaining the audit artifact.
9. Request a human-triggered locked-holdout evaluation only for a candidate
   that already passed development and validation gates.
```

The agent is allowed to continue iterating only inside this loop and only up to
the configured attempt and wall-clock budget. It receives no locked-holdout
metrics during ordinary iteration.

### Output Design

Human output:

```text
stdout summary from backtest.py
```

Agent output:

```text
runs/latest_result.json
```

Experiment memory:

```text
results.tsv
```

Expected JSON shape:

```json
{
  "ticker": "QQQ",
  "start_date": "2010-01-04",
  "end_date": "2021-12-31",
  "evaluation_mode": "research",
  "windows": {
    "development_end": "2017-12-31",
    "validation_end": "2021-12-31"
  },
  "data": {
    "sha256": "...",
    "adjustment": "adjusted_close_total_return"
  },
  "integrity": {
    "strategy_sha256": "...",
    "harness_sha256": "...",
    "changed_files": ["strategy.py"],
    "trusted_files_clean": true,
    "prefix_invariance_passed": true
  },
  "metrics": {
    "development": {"composite_score": 0.0, "sharpe": 0.0},
    "validation": {
      "annual_return": 0.0,
      "sharpe": 0.0,
      "max_drawdown": 0.0,
      "annual_turnover": 0.0,
      "num_trades": 0,
      "composite_score": 0.0
    },
    "average_exposure": 0.0,
    "annual": {},
    "validation_folds": {}
  },
  "benchmark": {
    "name": "buy_and_hold_QQQ",
    "annual_return": 0.0,
    "sharpe": 0.0,
    "max_drawdown": 0.0
  },
  "relative_metrics": {
    "excess_annual_return": 0.0,
    "information_ratio": 0.0,
    "beta": 0.0,
    "correlation": 0.0
  },
  "cost_scenarios": {
    "2_bps": {"composite_score": 0.0},
    "5_bps": {"composite_score": 0.0},
    "10_bps": {"composite_score": 0.0}
  }
}
```

### Safety Model

The system has two distinct safety goals:

1. Operational safety: it cannot trade, access a broker, or alter the trusted
   evaluation environment while experimenting.
2. Research safety: it cannot silently use future data, repeatedly optimize on
   a final holdout, or hide failed attempts.

Safety controls:

- Run trusted evaluation from a clean checkout or read-only mount; hash trusted
  files, configuration, dependencies, and data before each run.
- Reject an experiment if its changed-file list is not an allowlist containing
  only `strategy.py` and approved generated artifacts.
- Execute strategy code in a container with no network, fixed CPU/memory/time
  limits, read-only trusted code and development/validation data, a temporary
  writable run directory, and no mount containing `results.tsv`, prior runs, or
  holdout data. A separate human-controlled container performs locked evaluation.
- Save every candidate patch and append its result before a revert or promotion.
- Reject invalid bars and strategy outputs.
- Test prefix invariance: changing or appending future bars must not change any
  signal produced for an earlier prefix.
- Use next-bar execution.
- Use visible development/validation windows and a separate locked holdout.
- Apply transaction costs and rerun promotion candidates under cost stress.
- Require the full trusted test suite to pass before accepting a promotion.
- Require human approval for new data sources, dependencies, or live-trading capabilities.

### Extension Points

Future extensions should be added behind explicit contracts:

- Multi-ticker data loader.
- Short exposure support.
- Volatility targeting.
- Portfolio construction.
- SQLite experiment memory.
- Paper-trading proposal generator.

Live trading is out of scope unless explicitly approved in a future design phase.

## Phase 1: Minimal Offline Harness

Status: complete. The local harness uses adjusted-close total returns, the
conservative execution timeline, benchmark reporting, pinned FRED DGS3MO cash
rates, and data hashing/provenance.

Build a small, deterministic local backtesting harness.

Scope:

- Download QQQ historical OHLCV data and save it as a bundled sample CSV.
- Support a single-asset strategy workflow first.
- Implement a baseline strategy in `strategy.py` and a buy-and-hold benchmark.
- Run one backtest from the command line.
- Print standardized metrics.

Required design choices:

- QQQ sample date range: 2010-01-01 through 2026-07-10.
- Market data source: Yahoo Finance chart API, normalized into pinned local CSVs.
- Cash-rate source: FRED DGS3MO daily three-month Treasury constant-maturity yield.
- Baseline strategy: 50-day and 200-day moving-average trend filter.
- Return model: adjusted-close total return for the initial daily ETF model.
- Execution model: close[t] observation, close[t+1] fill, then next interval P&L.
- Default transaction cost: 2 bps per unit of turnover.
- Composite score:
  `0.45 * sharpe + 0.25 * sortino + annual_return - 1.25 * abs(max_drawdown) - 0.03 * min(annual_turnover, 10)`.

Example command:

```bash
uv run python backtest.py
```

Initial output:

```text
---
total_return:       0.1234
annual_return:      0.0612
annual_volatility:  0.1420
sharpe:             0.4310
sortino:            0.5120
max_drawdown:      -0.1830
turnover:           1.7420
num_trades:         128
```

Success criteria:

- Backtest runs locally without network access.
- Metrics are deterministic across repeated runs.
- Strategy logic is isolated in `strategy.py`.
- The evaluator can run a baseline strategy end to end.
- Buy-and-hold QQQ is reported on the same return series and costs convention.

## Phase 2: Evaluation Guardrails

Status: complete. Application-level checks and Docker-enforced isolation are
implemented and verified.

Add checks that make invalid experiments fail loudly.

Required checks:

- Signal timestamps must not use future prices or returns.
- Prefix-invariance checks must fail a strategy whose earlier signals change
  when future observations are perturbed or appended.
- Positions must be shifted so trades occur after signal observation.
- Missing data behavior must be explicit.
- Transaction costs and slippage must be applied.
- Strategy output must satisfy position and leverage limits.
- Evaluation must separate development, validation, and locked holdout periods.

Existing checks:

- Bars must be strictly increasing by date.
- OHLC values must be finite and positive.
- Volume must be non-negative.
- Strategy signals must match the bar count.
- Strategy signals must be finite.
- Strategy signals must stay within `[0.0, 1.0]`.
- Signals are delayed through the documented next-close fill before returns are earned.
- Transaction costs are charged on turnover.
- Development, validation, annual, rolling-fold, benchmark-relative, exposure,
  and cost-scenario results are reported.
- The ordinary backtest truncates input at validation end and emits no holdout metrics.
- Trusted code and data hashes plus the changed-file set are emitted with each run.
- Prefix invariance is checked during every backtest.

Deferred extension:

- Revisit an approved causal feature library or DSL only after the containerized
  workflow provides evidence that the additional restriction is worth its cost.

Evaluation policy:

```text
development:       2010-01-01 through 2017-12-31; visible to the agent
validation:        2018-01-01 through 2021-12-31; visible only as standard metrics
locked holdout:    2022-01-01 onward; inaccessible to the ordinary agent loop

rolling validation: additional fixed historical folds are used for promotion.
```

The precise windows live in trusted `config.py`. They may change only with
human approval and only before an experiment batch begins. A strategy running
in ordinary agent mode receives no locked-holdout bars or outputs. Locked
evaluation is human-triggered and writes to a separate result path. Automated
enforcement allows at most one candidate per 20-attempt batch and three total
looks at the same locked period. A candidate may not be modified and rerun in
response to its holdout result. Detailed results remain human-only; the research
process receives at most a pass/fail decision. After three looks, retire that
period as a final holdout and rely on newly accumulated forward data.

Success criteria:

- Tests catch intentional lookahead examples and prefix-invariance violations.
- Backtest fails if strategy output has invalid dates, NaNs, or excessive leverage.
- Costs materially affect turnover-heavy strategies.
- All-cash, buy-and-hold, zero-volatility, duplicate-date, short-window, and
  missing-session edge cases have deterministic, documented behavior.

## Phase 3: Agent Experiment Loop

Status: complete. The supervised loop uses fixed attempt/time budgets, Docker
isolation, material challenger thresholds, frozen robustness reports, an
append-only SQLite ledger, and budgeted human-triggered holdout evaluation.

Create `program.md` for an autonomous-but-constrained research loop.

The agent may:

- Edit `strategy.py`.
- Run the fixed backtest command.
- Read standardized metrics from structured output.
- Propose a promotion after a candidate meets every required gate.

The agent may not:

- Edit `data.py`, `backtest.py`, `metrics.py`, or `validate.py`.
- Change date splits after seeing results.
- Disable costs, slippage, or risk checks.
- Add broker, exchange, or live-trading integrations.
- Install new dependencies without human approval.
- Read locked-holdout data or results during ordinary iteration.
- Modify, delete, or backfill `results.tsv`, run artifacts, or candidate patches.

Primary objective:

```text
produce a candidate that passes development and validation constraints, then
improves the current champion by a material margin on a transparent ranking:
- benchmark-relative risk-adjusted return
- controlled drawdown and exposure
- reasonable turnover after costs
- stable performance across validation folds and subperiods
- an economically plausible, causal rule

subject to:
- leverage within configured limit
- all validation checks passing
```

Success criteria:

- First run records cash, buy-and-hold QQQ, and the baseline strategy.
- Each experiment records attempt number, strategy hash, candidate patch,
  metrics, costs, configuration/data/harness hashes, status, and hypothesis.
- Each backtest writes `runs/latest_result.json` for agent parsing.
- Human-readable stdout remains available for quick inspection.
- Failed, worse, invalid, and crashed experiments remain auditable after the
  working-tree strategy is discarded.
- Improved candidates remain on a research branch only after passing the
  challenger criteria; a human reviews promotion to main.

Structured output:

```text
runs/latest_result.json
```

Purpose:

- Stable machine-readable output for the agent.
- Exact numeric values without parsing formatted stdout.
- Complete metric set for the latest backtest run.

Experiment ledger export:

```text
results.tsv
```

Purpose:

- Human-readable local summary of attempted experiments.
- Includes attempt number, before/after commit, strategy and harness hashes,
  status, hypothesis, full-metrics artifact path, and short decision reason.
- Remains separate from `latest_result.json`, which is overwritten each run.

Implemented commands:

```bash
docker build -t autoquant-research:latest .
uv run python sandbox_runner.py
uv run python record_result.py manual_review "hypothesis and result" --batch-id <batch_id>
uv run python robustness.py --candidate <candidate_id>
uv run python evaluation.py --candidate <candidate_id> --batch-id <batch_id> --approval-id <approval_id> --approve-locked-holdout
uv run python promote_candidate.py <candidate_id> --approval-id <approval_id> --reason "review outcome"
```

The agent may invoke the attempt recorder but may not edit the ledger or
artifacts. SQLite triggers reject event updates and deletes. A locked-holdout
command requires an explicit approval ID, a clean trusted worktree, one lookup
per batch, and three lifetime looks; it writes separately under `runs/locked/`
and never to the ordinary agent-visible result file.

Implemented agent instruction file:

```text
program.md
```

## Phase 4: Research Memory

Status: complete. SQLite events record attempts, promotions, and holdout
lookups; `memory.py` provides read-only summaries, strategy-family searches,
and candidate/descendant history.

Track:

- Monotonic attempt number and timestamp.
- Hypothesis.
- Strategy family.
- Universe.
- Data, configuration, strategy, and trusted-harness hashes.
- Development, validation, and locked-holdout policy identifiers.
- Cost scenarios, benchmark metrics, exposure diagnostics, and subperiod metrics.
- Git commit before/after, changed-file list, and saved candidate patch path.
- Full metric set.
- Status: promoted, discarded, invalid, crashed, or manual review.
- Reason the idea likely worked or failed.
- Human approval identifier for a locked evaluation or promotion.
- Parent candidate, strategy family, and rejection/promotion reason.

Possible storage:

- SQLite is the append-only authoritative event ledger.
- Immutable result JSON and patch artifacts remain files addressed by path and hash.
- `results.tsv` is a human-readable export.

Success criteria:

- The agent can avoid repeating previously failed ideas.
- The human can inspect experiment history quickly.
- Results are reproducible from logged metadata.
- Failed attempts and the number of trials before selection are auditable.
- Candidate ancestry and related promotion/holdout events are queryable.

## Phase 5: Strategy Research Expansion

Status: complete for the current single-asset scope. Controlled causal
momentum, mean-reversion, volatility-targeting, factor-combination,
regime-filter, and risk-constrained families are available while the trend
baseline remains the default research strategy.
`STRATEGY_FAMILY` selects the family for a frozen candidate run.

After the promotion pipeline is reliable, add controlled strategy families.

Candidate research areas:

- Momentum.
- Mean reversion.
- Volatility targeting.
- Cross-sectional ranking.
- Simple factor combinations.
- Regime filters.
- Portfolio construction and risk constraints.

Each expansion should add tests and validation before giving the agent access to it.
Cross-sectional ranking remains deferred until the strategy contract is expanded
to accept a multi-asset universe; implementing it against one asset would not be
a meaningful ranking strategy.
Before claiming robustness, evaluate the exact frozen strategy and parameters
on an out-of-universe panel that was never used for tuning:

- Core confirmation panel: SPY, IWM, EFA, and EEM.
- Cross-asset stress panel: TLT and GLD.

The candidate need not outperform on every instrument. Promotion requires
credible median behavior across the comparable equity panel, no catastrophic
failure, no dependence on QQQ alone, and an economic explanation for where the
strategy should or should not transfer. TLT and GLD are stress tests unless the
strategy hypothesis explicitly claims cross-asset applicability. Adding and
pinning these datasets requires human approval.

## Human Approval Gates

Require approval before:

- Adding new data sources.
- Changing the evaluation objective.
- Changing transaction cost or slippage assumptions.
- Changing development, validation, rolling-fold, or locked-holdout policy.
- Resetting the lifetime holdout-look counter or reusing a retired holdout.
- Increasing compute budget.
- Adding dependencies.
- Loosening strategy sandbox, import, filesystem, or network restrictions.
- Changing the risk-free series or metric annualization convention.
- Changing the core or stress robustness panel after seeing its results.
- Running a locked-holdout evaluation or promoting a research-branch candidate.
- Introducing any live-trading, broker, or order-management feature.

## Phase 1-3 Completion

1. Pinned QQQ and robustness-panel market data, FRED DGS3MO cash rates, and provenance hashes are implemented.
2. Docker research execution stages only trusted code, the candidate strategy, and development/validation data with no network, read-only inputs, temporary writable space, and fixed resource limits.
3. SQLite events are append-only; TSV is an export; promotions and holdout lookups are distinct events.
4. Locked evaluation enforces one lookup per batch, three lifetime looks, clean trusted code, and human approval IDs.
5. Frozen candidates can run against SPY/IWM/EFA/EEM confirmation and TLT/GLD stress panels.
6. Tests cover causality, invalid data/signals, cost effects, cash accrual, provider-session gaps, short windows, ledger immutability, holdout budgets, and locked-evaluation separation.

## Decisions

Resolved decisions:

- Market data source: Yahoo Finance chart API for QQQ and the fixed ETF panel.
- Cash-rate source: FRED DGS3MO daily three-month Treasury constant-maturity yield.
- Project setup: use `uv` to stay consistent with `autoresearch`.
- Strategy scope: start with single-asset strategies.
- Return convention: adjusted-close total return for the initial daily ETF model.
- Research protocol: visible development/validation, human-triggered locked holdout, and fixed rolling-validation folds.
- Objective: satisfy hard validity and robustness constraints, then use a transparent composite ranking rather than a single-score promotion rule.
- Autonomous budget: at most 20 attempts or 60 minutes per batch.
- Challenger threshold: at least 5% validation-score improvement and 0.10 Sharpe improvement, subject to drawdown, cost, annual-stability, and benchmark-relative guardrails.
- Cost scenarios: 2, 5, and 10 bps.
- Rolling folds: fixed two-year windows from 2014 through 2021.
- Metric convention: 252-day annualization using arithmetic daily excess
  returns; zero risk-free rate during development, followed by a pinned daily
  three-month Treasury-bill proxy before locked evaluation; zero denominators
  report `0.0` plus a diagnostic flag.
- Strategy isolation: use a resource-limited, network-disabled container with
  read-only trusted and development/validation mounts; keep holdout data and
  experiment history outside the container. Docker is the selected runtime;
  defer a strategy DSL.
- Holdout budget: at most one candidate per 20-attempt batch and three lifetime
  evaluations of the same locked period, with no result-driven rerun.
- Robustness panel: SPY/IWM/EFA/EEM for confirmation and TLT/GLD for stress,
  always using frozen strategy code and parameters.
- Experiment storage: append-only SQLite is authoritative; immutable JSON/patch
  artifacts remain files addressed by path and hash; TSV is an export.
- Human holdout thresholds: positive annual excess return, no more than 0.02
  additional maximum drawdown versus the benchmark, and valid risk ratios.

## What is missing

### 1. Summary of expectation of this auto agent

AutoQuant should be runnable as a daily, autonomous research agent. For each
authorized research run, it should read prior experiments and the research
playbook, propose a bounded and falsifiable hypothesis, implement the focused
strategy change in an isolated workspace, conduct the fixed experiments, retain
the full audit trail, and prepare a concise finding for human reviewers.

The agent should generate ideas from the recorded research history and from
approved, versioned market inputs. QQQ is an initial sample dataset, not the
scope of the research objective; every hypothesis must name its intended
universe. The agent must remain unable to trade, access a broker, alter trusted
evaluation code, or access the locked holdout during routine research.

Preparing a reviewer-ready report is in scope. Delivering that report through
email, Slack, a dashboard, or another notification system is intentionally out
of scope for this project.

### 2. Daily controller workflow

```text
scheduled daily trigger
-> verify approved, versioned data is available
-> read experiment ledger, current champion, and research playbook
-> generate one bounded economic hypothesis and pre-committed rejection rule
-> create an isolated strategy workspace
-> implement one focused strategy change
-> run tests and the fixed sandboxed backtest
-> record immutable result, source snapshot, and decision in the ledger
-> discard/revert or freeze a candidate using fixed acceptance gates
-> generate a concise reviewer-ready research summary
```

The controller must not run locked evaluation or promotion. It must not use
locked-holdout outputs to generate, select, or refine ideas. Research on a day
without a newly approved data version remains subject to the cumulative
experiment budget; repeated tuning on the same visible period is not new
evidence.

### 3. Missing capabilities

Implemented: `daily_controller.py` is a cron-compatible daily entry point. It
validates approved local inputs and a structured manifest, enforces the per-batch
attempt and wall-clock budgets, selects one existing vetted family in an
isolated Git worktree, runs tests and the sandbox, records immutable source and
result artifacts, and writes a reviewer summary. `data_policy.md` defines the
approval requirements for input refreshes; `experiment_manifest.py` retains the
intended universe, mechanism, causal inputs, parameter budget, expected failure
regime, and rejection condition with each attempt.

Two activation items remain intentionally external to the repository:

- An operator must install the daily trigger (for example, a cron or CI
  schedule) and supply a reviewed manifest. The controller deliberately does
  not install or modify host scheduling.
- Cross-sectional and portfolio strategies require an approved synchronized
  multi-asset data, benchmark, cost, and portfolio-construction contract. The
  current QQQ single-asset interface cannot honestly implement them.
