# autoquant

Constrained offline backtesting agent for quant research.

Phase 1 provides a minimal single-asset harness:

- Download QQQ historical OHLCV data into `data/qqq.csv`.
- Run a fixed offline backtest.
- Keep strategy logic isolated in `strategy.py`.
- Print deterministic performance, risk, turnover, and composite-score metrics.

## Setup

```bash
uv sync
```

## Download Sample Data

```bash
uv run python data.py --download
```

The first sample dataset is QQQ daily data from 2010-01-01 through 2026-07-10.

To download another ticker:

```bash
uv run python data.py --download --ticker SPY
```

This writes to `data/spy.csv`. You can also pass `--output path/to/file.csv`.

## Run Baseline Backtest

```bash
uv run python backtest.py
```

The baseline strategy is a simple moving-average trend filter. It emits same-day signals, and `backtest.py` shifts positions by one trading day so execution only uses already-observed data.
