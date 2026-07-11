# autoquant

Constrained offline research harness for single-asset quant experiments.

The ordinary research loop uses QQQ data through 2021 only:

- 2010-2017 development window.
- 2018-2021 validation window.
- 2022 onward locked holdout, evaluated only with explicit human approval.

Returns and signals use adjusted close so splits and distributions are reflected
in the daily total-return series. A signal computed after `close[t]` fills at
`close[t+1]` and begins earning the following close-to-close return.

## Setup

```bash
uv sync
uv run python data.py --download
```

The downloaded CSV is a local, pinned input. Each result records its SHA-256
hash; replacing it starts a different research dataset.

## Run Research Backtest

```bash
uv run python backtest.py
```

The command runs causality and validation checks, then writes
`runs/latest_result.json`. The result includes development and validation
metrics, buy-and-hold comparison, exposure, annual results, cost sensitivity,
and code/data integrity hashes. It deliberately excludes locked-holdout results.

## Record An Attempt

Record every attempt before reverting its strategy patch:

```bash
uv run python record_result.py manual_review "baseline"
uv run python record_result.py discarded "hypothesis and rejection reason"
uv run python record_result.py invalid "validation failure"
uv run python record_result.py crashed "runtime failure"
```

The append-only ledger is `results.tsv`; exact result JSON and strategy patches
are retained under `runs/`.

## Locked Holdout

Only a human should run this for a frozen candidate in a clean worktree:

```bash
uv run python evaluation.py --candidate <run_id> --approve-locked-holdout
```

Locked results are written separately under `runs/locked/` and are not copied
to the agent-visible latest result.

## Tests

```bash
uv run python -m unittest discover -s tests
```

Arbitrary Python strategy code is not an OS security boundary. Run autonomous
experiments in a container or worker with no network and read-only trusted files.
