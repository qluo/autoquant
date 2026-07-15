# AutoQuant

AutoQuant is an offline, constrained research agent for daily ETF strategies.
It proposes one bounded hypothesis, tests it in an isolated workspace, records
the full audit trail, and prepares a finding for human review. It does not
trade, access brokers, promote candidates, or access the locked holdout during
routine research.

## Daily use

1. Open this repository in Codex. [`AGENTS.md`](AGENTS.md) supplies the
   persistent operating rules for every agent run.
2. Authorize one research run. The agent reads the playbook and experiment
   memory, then explores approved idea sources: SSRN/NBER for asset pricing,
   FRED/ALFRED for macro themes, SEC EDGAR for fundamentals, and Google News
   for qualitative market context.

   Start an interactive agent session with the research assignment:

   ```bash
   codex --search -C . "Start an authorized AutoQuant research run. Follow AGENTS.md: read the playbook and experiment memory, explore approved idea sources, then propose one bounded falsifiable hypothesis and wait for my approval before running it."
   ```

   The agent will propose the hypothesis first. After you approve that specific
   proposal, it may create the manifest and run the bounded controller.
3. The agent proposes one falsifiable hypothesis with a cited economic
   mechanism, intended universe, and rejection condition. News and external
   sources are hypothesis context only—not strategy data. If the idea requires
   an unregistered asset, universe, or dataset, the agent pauses for human
   approval before creating a manifest or running an experiment.
4. After approval, the agent evaluates the focused change in an isolated
   workspace, records immutable artifacts, and writes an HTML report under
   `runs/reports/`.
5. Review that report. It compares the
   candidate with the fixed buy-and-hold baseline using annual return, Sharpe,
   and maximum drawdown. Inspect experiment history with:

   ```bash
   uv run python memory.py summary
   uv run python memory.py search --strategy-family <family>
   ```

Each run is limited to 20 attempts or 60 minutes. A report is evidence for
human review—not a promotion or locked-holdout evaluation.

## Research-data layers

Development data is reusable. Visible selection data is finite: the controller
globally reserves each declared hypothesis fingerprint against
`qqq_selection_v1` before it runs, including failures. That version allows 50
effective hypotheses and 3 candidates advanced for review; it retires when a
limit is reached. Do not use direct sandbox or manual runs to inspect selection
metrics. The final holdout remains untouched until human promotion.

If a baseline reports a stale or unwritable `runs/sandbox/latest_result.json`,
rerun the approved sandbox command. That file is ephemeral output and the
runner replaces it before each run; agents must not use `rm`, `chmod`, or
`chown` on experiment artifacts.

## First-time setup

From `autoquant/`:

```bash
uv sync
docker build -t autoquant-research:latest .
uv run python -m unittest discover -s tests
```

The repository must be a Git checkout with Docker available. Research uses only
approved local inputs; see [the data policy](docs/data_policy.md).

### Authorize Colab GPU access

Deep-learning experiments also need a one-time Colab authorization. Install the
CLI, then create a short-lived GPU session; the CLI opens the OAuth flow if
needed. Confirm it is available, then release it immediately:

```bash
uv tool install google-colab-cli
colab --auth oauth2 new -s autoquant-setup --gpu T4
colab status -s autoquant-setup
colab stop -s autoquant-setup
```

This authorizes the local CLI account and verifies GPU access without retaining
a runtime. Do not mount Google Drive or authenticate the runtime for GCP
services.

## Agent workflow

The agent instructions are deliberately split by purpose:

- [AGENTS.md](AGENTS.md): short, non-negotiable guardrails.
- [research_playbook.md](research_playbook.md): hypothesis methodology and
  approved idea sources.
- [policy.toml](policy.toml): versioned budgets, windows, dataset IDs, and
  lifecycle settings.

For a map of the runtime modules, operating documents, and generated artifacts,
see [the project structure guide](docs/project_structure.md).

The bounded execution component is `daily_controller.py`: after the agent
creates a manifest, it validates inputs and budget, runs the selected vetted
family in an isolated Git worktree, records immutable artifacts, and writes the
report. Run it only from the primary repository checkout; it creates its own
temporary worktree and refuses to run from a linked or temporary worktree.

```bash
uv run python daily_controller.py --manifest <manifest.json> --dry-run
uv run python daily_controller.py --manifest <manifest.json>
```

After the human approves its hypothesis, run an uncommitted, tested strategy
implementation—including a bounded ML model—with:

```bash
uv run python daily_controller.py --manifest <manifest.json> --strategy-source strategy.py
```

The controller snapshots that exact source. ML must be deterministic and
causal, use only approved local data, dependencies, and compute resources, and
remain within the run's resource budget. New packages, a GPU-enabled runner
other than the Colab workflow below, datasets, or hyperparameter searches need
separate human approval.

### Colab GPU training

Deep-learning training may use the installed Google Colab CLI after the
hypothesis is approved:

```bash
colab version
colab run --gpu T4 <approved-training-job>.py
```

Use the `colab-operator` skill in a new agent session. Keep the job ephemeral;
upload only the reviewed strategy, minimal job code, and approved
development/validation inputs. Never upload the repository history, `runs/`,
ledger, holdout data, or credentials, and do not mount Drive or GCP services.
The Colab result is exploratory compute: run the exact strategy and fixed model
artifact through the local controller before it can be recorded or reported.

The controller supports the currently vetted single-asset families: `trend`,
`momentum`, `mean_reversion`, `volatility_targeting`, `factor_combo`,
`regime_filter`, and `risk_constrained`.

## Approved research universes

The manifest selects an approved single-asset universe with `universe_id`.
The registry currently contains only `qqq`; it maps the run to its pinned data,
ticker, and matching buy-and-hold benchmark. The robustness-panel assets remain
confirmation-only and must not be selected for research or tuning.

Adding another universe requires human approval and a registry entry with its
own pinned data, benchmark, cost, and evaluation policy. This is not yet a
multi-asset or cross-sectional strategy system.

If an agent's idea requires an unregistered asset or universe, it must pause
and request that approval before creating a manifest, downloading data, or
running an experiment.

## Recover an experiment's source

Every recorded attempt stores an immutable `strategy.py` snapshot named by its
SHA-256 hash. To recover the exact source reviewed for a candidate:

```bash
uv run python memory.py candidate <strategy_sha256>
less runs/strategies/<strategy_sha256>.py
sha256sum runs/strategies/<strategy_sha256>.py
```

The ledger event returned by the first command includes
`strategy_snapshot_path`. The final checksum must match the event's
`strategy_sha256` before relying on the snapshot.

## Safety boundary

Each approved research universe has fixed development and validation periods,
plus a separate locked holdout defined by its evaluation policy. Only a human
may run locked evaluation or promotion, and no agent may use locked results to
generate or tune ideas.

Each locked-holdout version allows one full evaluation only. It is retired after
that lookup regardless of outcome; another final claim needs a new approved
untouched period.

New data, universes, cost assumptions, evaluation policies, and multi-asset
strategies require human approval before research begins.
