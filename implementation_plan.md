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

Add checks that make invalid experiments fail loudly.

Required checks:

- Signal timestamps must not use future prices or returns.
- Positions must be shifted so trades occur after signal observation.
- Missing data behavior must be explicit.
- Transaction costs and slippage must be applied.
- Strategy output must satisfy position and leverage limits.
- Evaluation must separate in-sample and out-of-sample periods.

Success criteria:

- Tests catch at least one intentional lookahead example.
- Backtest fails if strategy output has invalid dates, NaNs, or excessive leverage.
- Costs materially affect turnover-heavy strategies.

## Phase 3: Agent Experiment Loop

Create `program.md` for an autonomous-but-constrained research loop.

The agent may:

- Edit `strategy.py`.
- Run the fixed backtest command.
- Read standardized metrics.
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
- Failed or worse experiments are discarded.
- Improved experiments remain on the branch.

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
