# AutoQuant Research Agent Program

You are running a constrained, offline exploratory quant-research loop. You
produce auditable candidates; you do not run the locked holdout or promote code.

## Objective

Develop a simple, causal strategy for its explicitly stated intended universe
that materially improves on the applicable current champion across development,
selection, cost, and robustness evidence. Do not optimize a single score in
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
6. Use direct sandbox runs only for development checks; do not treat their
   visible metrics as selection evidence or record an attempt from them.
7. Read `uv run python memory.py summary`. Avoid only substantially equivalent
   rejected hypotheses—not entire strategy families. Compare the universe,
   mechanism, causal inputs, implementation fingerprint, complexity card, and
   expected failure regime before retrying a related idea.
8. Stop after 20 attempts or 60 minutes, whichever comes first.

## File Boundary

Edit only `strategy.py`. The sandbox stages that file with trusted code and only
development/selection data. It has no network, no holdout/history mount, and
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
sandbox limits apply. Do not add dependencies, enable a GPU runner other than
the approved Colab workflow below, download data, or run hyperparameter
searches unless a human separately approves the
dependency, compute, data, or policy change.

For the current single-asset daily dataset, neural models are not permitted
without explicit human approval and a sample-size/complexity justification.
Approved ML must use walk-forward retraining, purge/embargo for overlapping
labels, training-prefix-only scaling and imputation, declared feature timestamps
and missing-data behavior, fixed multiple seeds, and linear/logistic comparison.
Report median and worst seed, calibration when outputs are probabilities, and
rolling drift evidence; never select the best seed or model variant.

## Colab GPU workflow

For an approved deep-learning hypothesis that needs an accelerator, use the
installed `colab` CLI and the `colab-operator` skill. Use an ephemeral job, for
example:

```bash
colab run --gpu T4 <approved-training-job>.py
```

The job must use only the reviewed strategy, a minimal training/evaluation
script, and the approved development/validation inputs. Do not upload the Git
history, `runs/`, SQLite ledger, holdout data, credentials, or use Drive/GCP
mounts. Do not use the GPU to expand the parameter-search budget. Stop any
kept session after use.

Colab is an approved accelerator for training and exploratory computation; it
does not replace the trusted local evaluator. Before an attempt is recorded,
the exact strategy and any fixed model artifact must be evaluated by the local
controller so the result, source snapshot, and report remain auditable.

## Experiment Loop

For each attempt:

1. Complete the hypothesis template in `research_playbook.md`: state one
   falsifiable economic hypothesis, intended universe, expected failure regime,
   and rejection condition. Do not hard-code market dates. Check
   `uv run python memory.py search --strategy-family <family>` first.
2. Present that complete hypothesis to the human and wait for explicit approval.
   A general research-run request is not sufficient. Do not create the manifest,
   edit strategy logic, or invoke the controller before approval.
3. Create a manifest with a stable `hypothesis_id` and
   `selection_dataset_id: qqq_selection_v1`. Its fingerprint must cover the
   universe, mechanism, causal inputs, model family, and parameter budget.
   Related variants must retain their parent/relationship in the hypothesis
   text; they do not reset the global selection budget.
   Include the structured complexity card from `research_playbook.md`; a broad
   label such as “regime classifier” is not a single focused change unless its
   features, branches, and free parameters are predeclared.
4. Make one focused change to `strategy.py`.
5. Run `uv run python -m unittest discover -s tests`.
6. Run the controller, which reserves selection budget before exposing
   selection evidence. Do not call `sandbox_runner.py` for selection.
7. Inspect development/selection metrics, benchmark comparison, yearly/fold
   stability, 2/5/10 bps scenarios, risk-free provenance, and integrity hashes.
   The final reviewer report must include the buy-and-hold baseline's annual
   return, Sharpe, and maximum drawdown beside the candidate metrics.
8. The controller records the attempt and prepares the final reviewer report.
   Do not invoke `record_result.py` directly for a selection run.

```bash
uv run python record_result.py manual_review "hypothesis and result" --batch-id <batch_id>
uv run python record_result.py discarded "hypothesis and rejection reason" --batch-id <batch_id>
uv run python record_result.py invalid "hypothesis and validation failure" --batch-id <batch_id>
uv run python record_result.py crashed "hypothesis and crash reason" --batch-id <batch_id>
```

9. Run `uv run python robustness.py --candidate <strategy_sha256>` only for a
   frozen candidate that clears the acceptance criteria. Never tune against its
   robustness result.

## Acceptance Criteria

A candidate may be proposed for human review only when:

- All tests and prefix-invariance checks pass.
- Positive selection excess annual return is the primary objective; its
  deterministic block-bootstrap 95% interval, fold distribution, and benchmark
  comparison must be reported rather than treated as a single decisive estimate.
- Drawdown deterioration remains within 0.02, turnover and exposure are
  credible, and trade count is non-degenerate.
- A majority of selection folds have positive excess return; reviewers inspect
  the worst and median fold rather than relying on the aggregate alone.
- The strategy remains viable at 5 and 10 bps costs.
- It remains directionally viable under both fixed execution conventions:
  next-close-delayed and next-open. Market-on-close and VWAP are not claimed
  with daily bars and require approved intraday data.
- Composite score is a legacy descriptive field only. It is not an acceptance,
  ranking, promotion, or optimization objective.
- If evidence is materially equivalent, prefer the lower declared complexity,
  then lower turnover and clearer mechanism.
- The frozen strategy has credible median behavior on SPY/IWM/EFA/EEM and no
  catastrophic failure on TLT/GLD.

Passing creates a candidate, not a validated strategy. A human alone may run
one full locked evaluation for a holdout version. After any lookup—pass or
fail—that holdout is retired for final claims; further final evaluation needs a
new human-approved untouched period.

Before opening the holdout, predeclare one complete final report: candidate
versus buy-and-hold, frozen champion, and baseline ladder; fixed cost stress;
turnover, trade count, exposure, beta, and drawdown checks; fixed subperiod and
execution-convention checks; uncertainty; mechanism consistency; and an
operational-readiness checklist. All diagnostics are disclosed together in the
single lookup. The outcome may support promotion, rejection, or `inconclusive`,
but never redesign or a follow-up probe on the retired holdout.

## Research layers and selection retirement

Development data is reusable for construction and debugging. Selection data is
visible only through the controller and is globally budgeted by its pinned
`selection_dataset_id`, independent of session or batch. For
`qqq_selection_v1`, the limits are 50 effective hypothesis fingerprints and 3
candidates advanced for formal review. A reservation is append-only and occurs
before execution, so failed jobs and repeated related attempts remain auditable.
After either limit is reached, retire the selection version permanently. A human
may approve a new version only with a new pinned data hash and predeclared
period; it must not reopen the retired period. The final holdout remains
untouched until promotion.

## Guardrails

Do not invoke `evaluation.py`, `promote_candidate.py`, downloads, or any live,
paper, broker, or order-management capability. Do not add dependencies or alter
the policy, data, cost, evaluation windows, ledger, or sandbox configuration.
