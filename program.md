# AutoQuant Research Agent Program

You are running a constrained, offline exploratory quant-research loop. You
produce auditable candidates; you do not decide that a strategy is robust or
run the locked holdout.

## Objective

Develop a causal single-asset QQQ strategy that improves materially on the
current champion across development and validation evidence. Do not optimize a
single score in isolation.

Read these fields from `runs/latest_result.json`:

```text
metrics.development
metrics.validation
metrics.annual
benchmark
relative_metrics
cost_scenarios
integrity
```

The ordinary result contains no 2022+ locked-holdout metrics.

## Setup

1. Confirm you are in the `autoquant` repository.
2. Confirm `data/qqq.csv` exists. Ask the human before downloading or replacing data.
3. Run `uv run python -m unittest discover -s tests`.
4. Run `uv run python backtest.py` and record the baseline before editing.
5. Stop after 20 attempts or 60 minutes, whichever comes first.

## File Boundary

During experiments, edit only `strategy.py`. Treat all other source, test,
configuration, data, ledger, and run-artifact files as read-only. You may invoke
`backtest.py` and `record_result.py`, but may not edit them.

## Experiment Loop

For each attempt:

1. State one falsifiable hypothesis and why it could work economically.
2. Make one focused change to `strategy.py`; do not hard-code market dates.
3. Run `uv run python -m unittest discover -s tests`.
4. Run `uv run python backtest.py`.
5. Inspect the full metric vector, benchmark comparison, annual results, cost scenarios, and integrity block.
6. Record the attempt before reverting or committing it:

```bash
uv run python record_result.py manual_review "hypothesis and result"
uv run python record_result.py discarded "hypothesis and rejection reason"
uv run python record_result.py invalid "hypothesis and validation failure"
uv run python record_result.py crashed "hypothesis and crash reason"
```

7. Keep a candidate on the research branch only when it clears every acceptance criterion. Otherwise restore the previous champion without deleting its ledger row or saved patch.

## Acceptance Criteria

A candidate may be proposed for human review only when:

- All tests and prefix-invariance checks pass.
- `integrity.trusted_files_clean` is true in a clean experiment checkout.
- Validation composite score improves by at least 5% and validation Sharpe by at least 0.10 versus the current champion.
- Validation max drawdown is not worse by more than 0.02.
- Excess annual return, exposure, turnover, and trade count do not reveal an obvious regression or degenerate strategy.
- The improvement persists at 5 bps and remains viable at 10 bps.
- Performance is not explained by one validation year.
- The rule remains simple, causal, and economically defensible.

Passing these checks creates a candidate, not a validated strategy. A human
decides whether to run the locked holdout and whether to promote the candidate.

## Guardrails

Do not modify evaluator files, tests, data, costs, evaluation windows, or prior
records. Do not read or invoke locked-holdout evaluation, add dependencies or
data sources, access a network, or add live/paper trading and broker features.
