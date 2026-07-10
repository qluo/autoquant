# AutoQuant Implementation Plan

## Goal

Build a constrained offline backtesting agent for quant research.

The agent should help generate, run, compare, and remember trading-strategy experiments, but it must not trade live, access brokers, or modify the trusted backtest/evaluation harness.

Core loop:

```text
research idea
-> structured experiment plan
-> human approval
-> edit constrained strategy file
-> run standardized offline backtest
-> compare against baseline
-> keep/discard
-> log experiment memory
```

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

## Proposed Directory Structure

```text
autoquant/
  README.md
  implementation_plan.md
  program.md
  pyproject.toml
  data.py
  backtest.py
  strategy.py
  metrics.py
  validate.py
  results.tsv
  tests/
    test_metrics.py
    test_backtest.py
    test_no_lookahead.py
```

Initial file roles:

- `program.md`: instructions for the research agent.
- `data.py`: fixed data loading, cleaning, and train/test split logic.
- `backtest.py`: fixed backtest harness and portfolio simulation.
- `metrics.py`: fixed performance and risk metrics.
- `validate.py`: fixed validation checks for leakage, dates, costs, and outputs.
- `strategy.py`: the only file the agent edits during experiments.
- `results.tsv`: local experiment log, likely untracked by git.

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
7. Compute full-period and out-of-sample metrics.
8. Print a human-readable summary.
9. Write machine-readable output for the agent.

### Trust Boundaries

Trusted files:

```text
data.py
backtest.py
metrics.py
validate.py
tests/
```

These files define the evaluation contract. The research agent should not edit them during autonomous experiments.

Editable research file:

```text
strategy.py
```

The agent can edit this file to test strategy ideas. It must return one target exposure per input bar.

Local generated files:

```text
data/
runs/
results.tsv
run.log
```

These files are local artifacts and should not be required for source-code review.

### Data Contract

Input data is daily OHLCV:

```text
Date, Open, High, Low, Close, Adj Close, Volume
```

The initial dataset is QQQ daily data. Additional tickers can be downloaded with the same schema.

`data.Bar` is the in-memory representation of one daily OHLCV row:

```text
date, open, high, low, close, volume
```

The backtest currently uses `close` for daily close-to-close returns. `Adj Close` is retained in CSV for future use but is not part of the Phase 1/2 `Bar` object.

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

### Backtest Contract

`backtest.py` owns execution semantics:

- Daily close-to-close returns.
- Next-bar execution.
- Long-only exposure for the initial version.
- Transaction cost charged on absolute position change.
- Fixed in-sample/out-of-sample split.
- Standard metric calculation.

The agent should treat this file as read-only during experiments.

### Metric Contract

Primary evaluation is based on out-of-sample composite score.

Supporting metrics:

- Total return.
- Annualized return.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio.
- Max drawdown.
- Annual turnover.
- Number of trades.
- In-sample composite score.
- Out-of-sample composite score.
- Out-of-sample Sharpe.
- Out-of-sample max drawdown.

The composite score is intentionally simple at first. It rewards risk-adjusted return and penalizes drawdown and excessive turnover.

### Agent Loop Design

The Phase 3 research loop should work like this:

```text
1. Read program.md and latest experiment memory.
2. Inspect current baseline metrics.
3. Propose one strategy hypothesis.
4. Edit only strategy.py.
5. Run uv run python backtest.py.
6. Read runs/latest_result.json.
7. Compare primary score and guardrail metrics to baseline.
8. Commit successful changes.
9. Revert unsuccessful changes.
10. Append attempt to results.tsv.
```

The agent is allowed to continue iterating only inside this loop.

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
  "end_date": "2026-07-10",
  "split_date": "2020-01-01",
  "metrics": {
    "total_return": 0.0,
    "annual_return": 0.0,
    "annual_volatility": 0.0,
    "sharpe": 0.0,
    "sortino": 0.0,
    "max_drawdown": 0.0,
    "annual_turnover": 0.0,
    "num_trades": 0,
    "composite_score": 0.0,
    "is_score": 0.0,
    "oos_score": 0.0,
    "oos_sharpe": 0.0,
    "oos_max_drawdown": 0.0
  }
}
```

### Safety Model

The system is safe by construction only if the agent cannot change the evaluator while experimenting.

Safety controls:

- Keep evaluator files read-only by instruction and review.
- Reject invalid bars and strategy outputs.
- Use next-bar execution.
- Use fixed split dates.
- Apply transaction costs.
- Require tests to pass before accepting harness changes.
- Require human approval for new data sources, dependencies, or live-trading capabilities.

### Extension Points

Future extensions should be added behind explicit contracts:

- Multi-ticker data loader.
- Adjusted-close return mode.
- Short exposure support.
- Volatility targeting.
- Portfolio construction.
- SQLite experiment memory.
- Paper-trading proposal generator.

Live trading is out of scope unless explicitly approved in a future design phase.

## Phase 1: Minimal Offline Harness

Status: complete.

Build a small, deterministic local backtesting harness.

Scope:

- Download QQQ historical OHLCV data and save it as a bundled sample CSV.
- Support a single-asset strategy workflow first.
- Implement a baseline strategy in `strategy.py`.
- Run one backtest from the command line.
- Print standardized metrics.

Implemented choices:

- QQQ sample date range: 2010-01-01 through 2026-07-10.
- Data source: Yahoo Finance chart API, normalized into `data/qqq.csv`.
- Baseline strategy: 50-day and 200-day moving-average trend filter.
- Execution model: same-day signal, next-day position.
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

## Phase 2: Evaluation Guardrails

Status: complete.

Add checks that make invalid experiments fail loudly.

Required checks:

- Signal timestamps must not use future prices or returns.
- Positions must be shifted so trades occur after signal observation.
- Missing data behavior must be explicit.
- Transaction costs and slippage must be applied.
- Strategy output must satisfy position and leverage limits.
- Evaluation must separate in-sample and out-of-sample periods.

Implemented checks:

- Bars must be strictly increasing by date.
- OHLC values must be finite and positive.
- Volume must be non-negative.
- Strategy signals must match the bar count.
- Strategy signals must be finite.
- Strategy signals must stay within `[0.0, 1.0]`.
- Positions are shifted by one bar before returns are calculated.
- Transaction costs are charged on turnover.
- Full-period, in-sample, and out-of-sample composite scores are reported.

Fixed evaluation split:

```text
in-sample:     dates before 2020-01-01
out-of-sample: dates on or after 2020-01-01
```

Success criteria:

- Tests catch at least one intentional lookahead example.
- Backtest fails if strategy output has invalid dates, NaNs, or excessive leverage.
- Costs materially affect turnover-heavy strategies.

## Phase 3: Agent Experiment Loop

Create `program.md` for an autonomous-but-constrained research loop.

The agent may:

- Edit `strategy.py`.
- Run the fixed backtest command.
- Read standardized metrics from structured output.
- Commit candidate changes.
- Record results in `results.tsv`.
- Keep changes only when they improve the selected objective without violating guardrails.

The agent may not:

- Edit `data.py`, `backtest.py`, `metrics.py`, or `validate.py`.
- Change date splits after seeing results.
- Disable costs, slippage, or risk checks.
- Add broker, exchange, or live-trading integrations.
- Install new dependencies without human approval.

Primary objective:

```text
maximize a composite out-of-sample score that rewards:
- risk-adjusted return
- controlled drawdown
- reasonable turnover
- positive absolute return
- stable behavior across evaluation windows

subject to:
- leverage within configured limit
- all validation checks passing
```

Success criteria:

- First run records the baseline.
- Each experiment records commit, metrics, status, and short description.
- Each backtest writes `runs/latest_result.json` for agent parsing.
- Human-readable stdout remains available for quick inspection.
- Failed or worse experiments are discarded.
- Improved experiments remain on the branch.

Structured output:

```text
runs/latest_result.json
```

Purpose:

- Stable machine-readable output for the agent.
- Exact numeric values without parsing formatted stdout.
- Complete metric set for the latest backtest run.

Experiment ledger:

```text
results.tsv
```

Purpose:

- Append-only local summary of attempted experiments.
- Includes commit, primary score, status, and short description.
- Remains separate from `latest_result.json`, which is overwritten each run.

## Phase 4: Research Memory

Move beyond `results.tsv` once the loop is useful.

Track:

- Hypothesis.
- Strategy family.
- Universe.
- Data version.
- Train/test dates.
- Costs model.
- Code commit.
- Full metric set.
- Keep/discard decision.
- Reason the idea likely worked or failed.

Possible storage:

- Start with `results.tsv`.
- Move to SQLite when structured querying becomes useful.

Success criteria:

- The agent can avoid repeating previously failed ideas.
- The human can inspect experiment history quickly.
- Results are reproducible from logged metadata.

## Phase 5: Strategy Research Expansion

After the basic loop is reliable, add controlled strategy families.

Candidate research areas:

- Momentum.
- Mean reversion.
- Volatility targeting.
- Cross-sectional ranking.
- Simple factor combinations.
- Regime filters.
- Portfolio construction and risk constraints.

Each expansion should add tests and validation before giving the agent access to it.

## Human Approval Gates

Require approval before:

- Adding new data sources.
- Changing the evaluation objective.
- Changing transaction cost or slippage assumptions.
- Changing train/test date splits.
- Increasing compute budget.
- Adding dependencies.
- Introducing any live-trading, broker, or order-management feature.

## Initial Build Order

1. Create minimal package files and CLI entry point.
2. Implement deterministic sample data generation.
3. Implement baseline strategy.
4. Implement backtest engine with shifted execution.
5. Implement metrics.
6. Add validation checks.
7. Add focused tests.
8. Write `program.md` for the constrained agent loop.
9. Run baseline and record first result.

## Open Decisions

Resolved initial decisions:

- Data source: download QQQ historical data as the first bundled sample CSV.
- Project setup: use `uv` to stay consistent with `autoresearch`.
- Strategy scope: start with single-asset strategies.
- Objective: use a composite score across sensible performance, risk, turnover, and stability metrics.

Remaining implementation details:

- Choose the historical QQQ date range.
- Choose the data source for the initial CSV download.
- Define the exact composite score formula.
- Define default transaction cost and slippage assumptions.
