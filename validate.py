from __future__ import annotations

import math

from data import Bar


def validate_bars(bars: list[Bar]) -> None:
    if len(bars) < 2:
        raise ValueError("backtest requires at least two bars")

    previous_date = bars[0].date
    for index, bar in enumerate(bars):
        values = [bar.open, bar.high, bar.low, bar.close]
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError(f"bar at index {index} has invalid OHLC values")
        if bar.volume < 0:
            raise ValueError(f"bar at index {index} has negative volume")
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
