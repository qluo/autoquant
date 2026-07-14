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

## First-time setup

From `autoquant/`:

```bash
uv sync
docker build -t autoquant-research:latest .
uv run python -m unittest discover -s tests
```

The repository must be a Git checkout with Docker available. Research uses only
approved local inputs; see [data_policy.md](data_policy.md).

## Agent workflow

The detailed research protocol is in [program.md](program.md), and hypothesis
design is in [research_playbook.md](research_playbook.md). The bounded
execution component is `daily_controller.py`: after the agent creates a
manifest, it validates inputs and budget, runs the selected vetted family in an
isolated Git worktree, records immutable artifacts, and writes the report.

```bash
uv run python daily_controller.py --manifest <manifest.json> --dry-run
uv run python daily_controller.py --manifest <manifest.json>
```

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

New data, universes, cost assumptions, evaluation policies, and multi-asset
strategies require human approval before research begins.
