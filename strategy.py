from __future__ import annotations

from data import Bar


def _simple_moving_average(values: list[float], window: int) -> list[float | None]:
    averages: list[float | None] = []
    running_sum = 0.0

    for index, value in enumerate(values):
        running_sum += value
        if index >= window:
            running_sum -= values[index - window]

        if index + 1 < window:
            averages.append(None)
        else:
            averages.append(running_sum / window)

    return averages


def generate_signals(bars: list[Bar]) -> list[float]:
    """Return target exposure for each bar, from 0.0 cash to 1.0 long."""
    closes = [bar.close for bar in bars]
    sma_50 = _simple_moving_average(closes, 50)
    sma_200 = _simple_moving_average(closes, 200)

    signals: list[float] = []
    for close, fast, slow in zip(closes, sma_50, sma_200, strict=True):
        if fast is None or slow is None:
            signals.append(0.0)
        elif close > slow and fast > slow:
            signals.append(1.0)
        else:
            signals.append(0.0)

    return signals
