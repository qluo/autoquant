# AutoQuant Research Agent Program

You are running a constrained, offline exploratory quant-research loop. You
produce auditable candidates; you do not run the locked holdout or promote code.

## Objective

Develop a simple, causal strategy for its explicitly stated intended universe
that materially improves on the applicable current champion across development,
validation, cost, and robustness evidence. Do not optimize a single score in
isolation. The current QQQ workflow is a sample single-asset implementation,
not the scope of the research objective.

## Setup

1. Read `research_playbook.md` for hypothesis methodology and approved idea
   sources. Select an economic mechanism and intended universe; the current
   single-asset sample is not the default claim of generality.
2. Select `universe_id` only from `universe_registry.py`; the robustness panel
   is confirmation-only and cannot be used for research. If the hypothesis
   requires an unregistered asset or universe, stop and ask for approval of its
   data, benchmark, costs, and evaluation policy before creating a manifest or
   running an experiment.
3. Confirm the approved universe input, FRED DGS3MO, and robustness-panel CSV
   files exist.
4. Run `uv run python -m unittest discover -s tests`.
5. Build the local runner image with `docker build -t autoquant-research:latest .`.
6. Run `uv run python sandbox_runner.py` and record the baseline with a batch ID.
7. Read `uv run python memory.py summary` and avoid already-rejected families.
8. Stop after 20 attempts or 60 minutes, whichever comes first.

## File Boundary

Edit only `strategy.py`. The sandbox stages that file with trusted code and only
development/validation data. It has no network, no holdout/history mount, and
limited CPU, memory, and process count. Do not edit source, data, tests, ledger,
or run artifacts. `runs/sandbox/latest_result.json` is the sole replaceable
sandbox-output exception: if it is stale or unwritable, rerun the approved
`sandbox_runner.py`; do not manually remove it or change its permissions.

After the human approves the specific hypothesis, you may run the reviewed and
tested uncommitted strategy source through the controller with:

```bash
uv run python daily_controller.py --manifest <manifest.json> --strategy-source strategy.py
```

The controller copies only the primary checkout's `strategy.py` into its
temporary workspace and snapshots that exact source in the attempt record.
Without `--strategy-source`, it continues to select a pre-existing family from
`HEAD`. It accepts the sandbox's canonical result or its isolated
`runs/sandbox/latest_result.json` output and records the result and report in
the primary checkout; do not manually move either artifact.

ML strategies are permitted, including small neural models, only if the
approved hypothesis pre-commits the model class, causal feature set, fixed
parameter budget, expected failure regime, and rejection condition. Training
and inference must use only the prefix available at each signal time; use fixed
seeds and only the compute resources approved for the run. The existing
sandbox limits apply. Do not add dependencies, enable a GPU runner, download
data, or run hyperparameter searches unless a human separately approves the
dependency, compute, data, or policy change.

## Experiment Loop

For each attempt:

1. Complete the hypothesis template in `research_playbook.md`: state one
   falsifiable economic hypothesis, intended universe, expected failure regime,
   and rejection condition. Do not hard-code market dates. Check
   `uv run python memory.py search --strategy-family <family>` first.
2. Present that complete hypothesis to the human and wait for explicit approval.
   A general research-run request is not sufficient. Do not create the manifest,
   edit strategy logic, or invoke the controller before approval.
3. Make one focused change to `strategy.py`.
4. Run `uv run python -m unittest discover -s tests`.
5. Run `uv run python sandbox_runner.py`.
6. Inspect development/validation metrics, benchmark comparison, yearly/fold
   stability, 2/5/10 bps scenarios, risk-free provenance, and integrity hashes.
   The final reviewer report must include the buy-and-hold baseline's annual
   return, Sharpe, and maximum drawdown beside the candidate metrics.
7. Record the attempt before reverting or committing, then prepare the final
   reviewer report as HTML:

```bash
uv run python record_result.py manual_review "hypothesis and result" --batch-id <batch_id>
uv run python record_result.py discarded "hypothesis and rejection reason" --batch-id <batch_id>
uv run python record_result.py invalid "hypothesis and validation failure" --batch-id <batch_id>
uv run python record_result.py crashed "hypothesis and crash reason" --batch-id <batch_id>
```

8. Run `uv run python robustness.py --candidate <strategy_sha256>` only for a
   frozen candidate that clears the acceptance criteria. Never tune against its
   robustness result.

## Acceptance Criteria

A candidate may be proposed for human review only when:

- All tests and prefix-invariance checks pass.
- Validation composite score improves by at least 5% and validation Sharpe by at
  least 0.10 versus the champion.
- Validation max drawdown is not worse by more than 0.02.
- Excess return, exposure, turnover, trade count, annual results, and folds do
  not reveal a degenerate or one-period result.
- The improvement persists at 5 bps and remains viable at 10 bps.
- The frozen strategy has credible median behavior on SPY/IWM/EFA/EEM and no
  catastrophic failure on TLT/GLD.

Passing creates a candidate, not a validated strategy. A human alone may run a
locked evaluation, which is limited to one candidate per batch and three looks
over the lifetime of the locked period.

## Guardrails

Do not invoke `evaluation.py`, `promote_candidate.py`, downloads, or any live,
paper, broker, or order-management capability. Do not add dependencies or alter
the policy, data, cost, evaluation windows, ledger, or sandbox configuration.
