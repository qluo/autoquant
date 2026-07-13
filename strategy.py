from __future__ import annotations

from data import Bar

MOMENTUM_LOOKBACK = 126
MEAN_REVERSION_LOOKBACK = 20
VOLATILITY_LOOKBACK = 20
VOLATILITY_TARGET = 0.10
STRATEGY_FAMILY = "trend"


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


def _generate_trend_signals(bars: list[Bar]) -> list[float]:
    closes = [bar.adjusted_close for bar in bars]
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


def generate_signals(bars: list[Bar]) -> list[float]:
    """Return target exposure for the selected strategy family."""
    if STRATEGY_FAMILY == "trend":
        return _generate_trend_signals(bars)
    if STRATEGY_FAMILY == "momentum":
        return generate_momentum_signals(bars)
    if STRATEGY_FAMILY == "mean_reversion":
        return generate_mean_reversion_signals(bars)
    if STRATEGY_FAMILY == "volatility_targeting":
        return generate_volatility_targeting_signals(bars)
    raise ValueError(f"unknown strategy family: {STRATEGY_FAMILY}")


def generate_momentum_signals(
    bars: list[Bar], lookback: int = MOMENTUM_LOOKBACK
) -> list[float]:
    """Return long exposure when trailing total return is positive."""
    if lookback < 1:
        raise ValueError("lookback must be positive")

    closes = [bar.adjusted_close for bar in bars]
    signals: list[float] = []
    for index, close in enumerate(closes):
        if index < lookback:
            signals.append(0.0)
        else:
            signals.append(float(close > closes[index - lookback]))
    return signals


def generate_mean_reversion_signals(
    bars: list[Bar], lookback: int = MEAN_REVERSION_LOOKBACK
) -> list[float]:
    """Return long exposure when price is below its trailing average."""
    if lookback < 1:
        raise ValueError("lookback must be positive")

    closes = [bar.adjusted_close for bar in bars]
    averages = _simple_moving_average(closes, lookback)
    return [
        0.0 if average is None else float(close < average)
        for close, average in zip(closes, averages, strict=True)
    ]


def generate_volatility_targeting_signals(
    bars: list[Bar],
    lookback: int = VOLATILITY_LOOKBACK,
    target_volatility: float = VOLATILITY_TARGET,
) -> list[float]:
    """Scale long exposure toward a target using trailing realized volatility."""
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    if target_volatility <= 0.0:
        raise ValueError("target volatility must be positive")

    closes = [bar.adjusted_close for bar in bars]
    signals: list[float] = []
    for index in range(len(closes)):
        if index < lookback:
            signals.append(0.0)
            continue
        window_returns = [
            closes[offset] / closes[offset - 1] - 1.0
            for offset in range(index - lookback + 1, index + 1)
        ]
        volatility = _sample_stddev(window_returns) * (252.0**0.5)
        signals.append(
            1.0 if volatility == 0.0 else min(1.0, target_volatility / volatility)
        )
    return signals


def _sample_stddev(values: list[float]) -> float:
    average = sum(values) / len(values)
    return (sum((value - average) ** 2 for value in values) / (len(values) - 1)) ** 0.5
