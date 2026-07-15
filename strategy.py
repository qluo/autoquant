from __future__ import annotations

import math

from data import Bar

MOMENTUM_LOOKBACK = 126
MEAN_REVERSION_LOOKBACK = 20
VOLATILITY_LOOKBACK = 20
VOLATILITY_TARGET = 0.10
REGIME_VOLATILITY_LIMIT = 0.20
STRATEGY_FAMILY = "deep_neural_trend_classifier"
NEURAL_FEATURE_LOOKBACK = 200
NEURAL_TARGET_HORIZON = 21
NEURAL_REFIT_INTERVAL = 21
NEURAL_HIDDEN_UNITS = 8
NEURAL_EPOCHS = 12
NEURAL_LEARNING_RATE = 0.03
NEURAL_PROBABILITY_THRESHOLD = 0.55
NEURAL_SEED = 7


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
    if STRATEGY_FAMILY == "factor_combo":
        return generate_factor_combo_signals(bars)
    if STRATEGY_FAMILY == "regime_filter":
        return generate_regime_filter_signals(bars)
    if STRATEGY_FAMILY == "risk_constrained":
        return generate_risk_constrained_signals(bars)
    if STRATEGY_FAMILY == "neural_trend_classifier":
        return generate_neural_trend_signals(bars)
    if STRATEGY_FAMILY == "deep_neural_trend_classifier":
        return generate_deep_neural_trend_signals(bars)
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


def generate_factor_combo_signals(bars: list[Bar]) -> list[float]:
    """Combine trend and momentum confirmations without adding leverage."""
    trend = _generate_trend_signals(bars)
    momentum = generate_momentum_signals(bars)
    return [float(trend_value and momentum_value) for trend_value, momentum_value in zip(trend, momentum, strict=True)]


def generate_regime_filter_signals(
    bars: list[Bar], volatility_limit: float = REGIME_VOLATILITY_LIMIT
) -> list[float]:
    """Use the trend signal only in a lower-volatility trailing regime."""
    if volatility_limit <= 0.0:
        raise ValueError("volatility limit must be positive")
    trend = _generate_trend_signals(bars)
    closes = [bar.adjusted_close for bar in bars]
    signals: list[float] = []
    for index, trend_signal in enumerate(trend):
        if index < VOLATILITY_LOOKBACK:
            signals.append(0.0)
            continue
        returns = [
            closes[offset] / closes[offset - 1] - 1.0
            for offset in range(index - VOLATILITY_LOOKBACK + 1, index + 1)
        ]
        realized = _sample_stddev(returns) * (252.0**0.5)
        signals.append(trend_signal if realized <= volatility_limit else 0.0)
    return signals


def generate_risk_constrained_signals(bars: list[Bar]) -> list[float]:
    """Apply volatility targeting as an exposure cap to the trend signal."""
    trend = _generate_trend_signals(bars)
    risk_cap = generate_volatility_targeting_signals(bars)
    return [min(trend_value, cap) for trend_value, cap in zip(trend, risk_cap, strict=True)]


def _neural_features(closes: list[float], index: int) -> list[float]:
    returns = [
        closes[index] / closes[index - lookback] - 1.0
        for lookback in (5, 21, 63, 126)
    ]
    volatility_returns = [
        closes[offset] / closes[offset - 1] - 1.0
        for offset in range(index - 20, index + 1)
    ]
    volatility = _sample_stddev(volatility_returns) * (252.0**0.5)
    sma_50 = sum(closes[index - 49 : index + 1]) / 50
    sma_200 = sum(closes[index - 199 : index + 1]) / 200
    return returns + [volatility, closes[index] / sma_50 - 1.0, sma_50 / sma_200 - 1.0]


def _sigmoid(value: float) -> float:
    bounded = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + math.exp(-bounded))


def _initial_weight(position: int) -> float:
    return (((position + 1) * 1103515245 + NEURAL_SEED) % 65_536) / 65_536.0 - 0.5


def _fit_neural_classifier(
    features: list[list[float]], labels: list[float]
) -> tuple[list[float], list[float], list[list[float]], list[float], list[float], float]:
    means = [sum(row[column] for row in features) / len(features) for column in range(7)]
    scales = [
        max(
            1e-6,
            (sum((row[column] - means[column]) ** 2 for row in features) / len(features))
            ** 0.5,
        )
        for column in range(7)
    ]
    normalized = [
        [(value - means[column]) / scales[column] for column, value in enumerate(row)]
        for row in features
    ]
    hidden_weights = [
        [_initial_weight(unit * 7 + column) for column in range(7)]
        for unit in range(NEURAL_HIDDEN_UNITS)
    ]
    hidden_biases = [_initial_weight(56 + unit) for unit in range(NEURAL_HIDDEN_UNITS)]
    output_weights = [_initial_weight(64 + unit) for unit in range(NEURAL_HIDDEN_UNITS)]
    output_bias = _initial_weight(72)

    for _ in range(NEURAL_EPOCHS):
        for row, label in zip(normalized, labels, strict=True):
            hidden = [
                max(0.0, sum(weight * value for weight, value in zip(weights, row, strict=True)) + bias)
                for weights, bias in zip(hidden_weights, hidden_biases, strict=True)
            ]
            probability = _sigmoid(sum(weight * value for weight, value in zip(output_weights, hidden, strict=True)) + output_bias)
            error = probability - label
            previous_output_weights = output_weights[:]
            for unit, value in enumerate(hidden):
                output_weights[unit] -= NEURAL_LEARNING_RATE * error * value
            output_bias -= NEURAL_LEARNING_RATE * error
            for unit, value in enumerate(hidden):
                if value == 0.0:
                    continue
                gradient = error * previous_output_weights[unit]
                for column, feature in enumerate(row):
                    hidden_weights[unit][column] -= NEURAL_LEARNING_RATE * gradient * feature
                hidden_biases[unit] -= NEURAL_LEARNING_RATE * gradient
    return means, scales, hidden_weights, hidden_biases, output_weights, output_bias


def _neural_probability(
    features: list[float], model: tuple[list[float], list[float], list[list[float]], list[float], list[float], float]
) -> float:
    means, scales, hidden_weights, hidden_biases, output_weights, output_bias = model
    normalized = [(value - mean) / scale for value, mean, scale in zip(features, means, scales, strict=True)]
    hidden = [
        max(0.0, sum(weight * value for weight, value in zip(weights, normalized, strict=True)) + bias)
        for weights, bias in zip(hidden_weights, hidden_biases, strict=True)
    ]
    return _sigmoid(sum(weight * value for weight, value in zip(output_weights, hidden, strict=True)) + output_bias)


def generate_neural_trend_signals(bars: list[Bar]) -> list[float]:
    """Fit a causal, deterministic MLP to matured 21-session trend labels."""
    closes = [bar.adjusted_close for bar in bars]
    signals: list[float] = []
    model: tuple[list[float], list[float], list[list[float]], list[float], list[float], float] | None = None
    for index in range(len(closes)):
        if index < NEURAL_FEATURE_LOOKBACK + NEURAL_TARGET_HORIZON:
            signals.append(0.0)
            continue
        if model is None or (index - (NEURAL_FEATURE_LOOKBACK + NEURAL_TARGET_HORIZON)) % NEURAL_REFIT_INTERVAL == 0:
            feature_rows = [_neural_features(closes, row) for row in range(NEURAL_FEATURE_LOOKBACK - 1, index - NEURAL_TARGET_HORIZON + 1)]
            labels = [
                float(closes[row + NEURAL_TARGET_HORIZON] > closes[row])
                for row in range(NEURAL_FEATURE_LOOKBACK - 1, index - NEURAL_TARGET_HORIZON + 1)
            ]
            model = _fit_neural_classifier(feature_rows, labels)
        signals.append(float(_neural_probability(_neural_features(closes, index), model) >= NEURAL_PROBABILITY_THRESHOLD))
    return signals


def _fit_deep_neural_classifier(
    features: list[list[float]], labels: list[float]
) -> tuple[
    list[float],
    list[float],
    list[list[float]],
    list[float],
    list[list[float]],
    list[float],
    list[float],
    float,
]:
    means = [sum(row[column] for row in features) / len(features) for column in range(7)]
    scales = [
        max(
            1e-6,
            (sum((row[column] - means[column]) ** 2 for row in features) / len(features))
            ** 0.5,
        )
        for column in range(7)
    ]
    normalized = [
        [(value - means[column]) / scales[column] for column, value in enumerate(row)]
        for row in features
    ]
    first_weights = [[_initial_weight(unit * 7 + column) for column in range(7)] for unit in range(6)]
    first_biases = [_initial_weight(42 + unit) for unit in range(6)]
    second_weights = [[_initial_weight(48 + unit * 6 + column) for column in range(6)] for unit in range(3)]
    second_biases = [_initial_weight(66 + unit) for unit in range(3)]
    output_weights = [_initial_weight(69 + unit) for unit in range(3)]
    output_bias = _initial_weight(72)

    for _ in range(NEURAL_EPOCHS):
        for row, label in zip(normalized, labels, strict=True):
            first_hidden = [
                max(0.0, sum(weight * value for weight, value in zip(weights, row, strict=True)) + bias)
                for weights, bias in zip(first_weights, first_biases, strict=True)
            ]
            second_hidden = [
                max(0.0, sum(weight * value for weight, value in zip(weights, first_hidden, strict=True)) + bias)
                for weights, bias in zip(second_weights, second_biases, strict=True)
            ]
            probability = _sigmoid(sum(weight * value for weight, value in zip(output_weights, second_hidden, strict=True)) + output_bias)
            error = probability - label
            previous_output_weights = output_weights[:]
            previous_second_weights = [weights[:] for weights in second_weights]
            second_gradients = [
                error * previous_output_weights[unit] * float(value > 0.0)
                for unit, value in enumerate(second_hidden)
            ]
            first_gradients = [
                float(value > 0.0)
                * sum(
                    gradient * weights[unit]
                    for gradient, weights in zip(second_gradients, previous_second_weights, strict=True)
                )
                for unit, value in enumerate(first_hidden)
            ]
            for unit, value in enumerate(second_hidden):
                output_weights[unit] -= NEURAL_LEARNING_RATE * error * value
            output_bias -= NEURAL_LEARNING_RATE * error
            for unit, gradient in enumerate(second_gradients):
                for column, value in enumerate(first_hidden):
                    second_weights[unit][column] -= NEURAL_LEARNING_RATE * gradient * value
                second_biases[unit] -= NEURAL_LEARNING_RATE * gradient
            for unit, gradient in enumerate(first_gradients):
                for column, value in enumerate(row):
                    first_weights[unit][column] -= NEURAL_LEARNING_RATE * gradient * value
                first_biases[unit] -= NEURAL_LEARNING_RATE * gradient
    return means, scales, first_weights, first_biases, second_weights, second_biases, output_weights, output_bias


def _deep_neural_probability(
    features: list[float],
    model: tuple[
        list[float], list[float], list[list[float]], list[float], list[list[float]], list[float], list[float], float
    ],
) -> float:
    means, scales, first_weights, first_biases, second_weights, second_biases, output_weights, output_bias = model
    normalized = [(value - mean) / scale for value, mean, scale in zip(features, means, scales, strict=True)]
    first_hidden = [
        max(0.0, sum(weight * value for weight, value in zip(weights, normalized, strict=True)) + bias)
        for weights, bias in zip(first_weights, first_biases, strict=True)
    ]
    second_hidden = [
        max(0.0, sum(weight * value for weight, value in zip(weights, first_hidden, strict=True)) + bias)
        for weights, bias in zip(second_weights, second_biases, strict=True)
    ]
    return _sigmoid(sum(weight * value for weight, value in zip(output_weights, second_hidden, strict=True)) + output_bias)


def generate_deep_neural_trend_signals(bars: list[Bar]) -> list[float]:
    """Fit a causal, deterministic two-hidden-layer MLP to matured trend labels."""
    closes = [bar.adjusted_close for bar in bars]
    signals: list[float] = []
    model = None
    for index in range(len(closes)):
        if index < NEURAL_FEATURE_LOOKBACK + NEURAL_TARGET_HORIZON:
            signals.append(0.0)
            continue
        if model is None or (index - (NEURAL_FEATURE_LOOKBACK + NEURAL_TARGET_HORIZON)) % NEURAL_REFIT_INTERVAL == 0:
            feature_rows = [_neural_features(closes, row) for row in range(NEURAL_FEATURE_LOOKBACK - 1, index - NEURAL_TARGET_HORIZON + 1)]
            labels = [
                float(closes[row + NEURAL_TARGET_HORIZON] > closes[row])
                for row in range(NEURAL_FEATURE_LOOKBACK - 1, index - NEURAL_TARGET_HORIZON + 1)
            ]
            model = _fit_deep_neural_classifier(feature_rows, labels)
        signals.append(float(_deep_neural_probability(_neural_features(closes, index), model) >= NEURAL_PROBABILITY_THRESHOLD))
    return signals
