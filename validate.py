from __future__ import annotations

import math
from collections.abc import Callable

from data import Bar


def validate_bars(bars: list[Bar]) -> None:
    if len(bars) < 2:
        raise ValueError("backtest requires at least two bars")

    previous_date = bars[0].date
    for index, bar in enumerate(bars):
        values = [bar.open, bar.high, bar.low, bar.close, bar.adjusted_close]
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError(f"bar at index {index} has invalid OHLC values")
        if bar.volume < 0:
            raise ValueError(f"bar at index {index} has negative volume")
        if not (bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high):
            raise ValueError(f"bar at index {index} has inconsistent OHLC prices")
        if index > 0 and bar.date <= previous_date:
            raise ValueError("bars must be strictly increasing by date")
        previous_date = bar.date


def validate_signals(
    signals: list[float],
    bars: list[Bar],
    max_leverage: float = 1.0,
) -> None:
    if len(signals) != len(bars):
        raise ValueError("strategy returned a signal count that does not match bars")

    for index, signal in enumerate(signals):
        if not math.isfinite(signal):
            raise ValueError(f"signal at index {index} is not finite")
        if signal < 0.0 or signal > max_leverage:
            raise ValueError(
                f"signal at index {index} is outside [0.0, {max_leverage}]"
            )


def validate_strategy_causality(
    generate_signals: Callable[[list[Bar]], list[float]],
    bars: list[Bar],
    full_signals: list[float],
    checkpoint_step: int = 64,
) -> None:
    """Reject strategies whose past signals depend on future bars."""
    if checkpoint_step < 1:
        raise ValueError("checkpoint_step must be positive")

    checkpoints = set(range(1, len(bars), checkpoint_step))
    checkpoints.add(len(bars) - 1)
    for prefix_length in sorted(checkpoints):
        prefix_signals = generate_signals(bars[:prefix_length])
        validate_signals(prefix_signals, bars[:prefix_length])
        if prefix_signals != full_signals[:prefix_length]:
            raise ValueError(
                "strategy failed prefix invariance at "
                f"{bars[prefix_length - 1].date}"
            )
