from __future__ import annotations

import math


TRADING_DAYS_PER_YEAR = 252


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def compound_return(returns: list[float]) -> float:
    equity = 1.0
    for value in returns:
        equity *= 1.0 + value
    return equity - 1.0


def annualized_return(returns: list[float]) -> float:
    if not returns:
        return 0.0
    total = compound_return(returns)
    years = len(returns) / TRADING_DAYS_PER_YEAR
    if years <= 0 or total <= -1.0:
        return 0.0
    return (1.0 + total) ** (1.0 / years) - 1.0


def annualized_volatility(returns: list[float]) -> float:
    return stddev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR)


def annualized_excess_return(
    returns: list[float], risk_free_daily: float = 0.0
) -> float:
    if not returns:
        return 0.0
    return mean([value - risk_free_daily for value in returns]) * TRADING_DAYS_PER_YEAR


def downside_deviation(
    returns: list[float], risk_free_daily: float = 0.0
) -> float:
    if not returns:
        return 0.0
    downside_squared = [
        min(value - risk_free_daily, 0.0) ** 2 for value in returns
    ]
    return math.sqrt(mean(downside_squared)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(returns: list[float], risk_free_daily: float = 0.0) -> float:
    volatility = annualized_volatility(returns)
    if volatility == 0.0:
        return 0.0
    return annualized_excess_return(returns, risk_free_daily) / volatility


def sortino_ratio(returns: list[float], risk_free_daily: float = 0.0) -> float:
    deviation = downside_deviation(returns, risk_free_daily)
    if deviation == 0.0:
        return 0.0
    return annualized_excess_return(returns, risk_free_daily) / deviation


def correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("return series must have the same length")
    if len(left) < 2:
        return 0.0
    left_std = stddev(left)
    right_std = stddev(right)
    if left_std == 0.0 or right_std == 0.0:
        return 0.0
    covariance = sum(
        (left_value - mean(left)) * (right_value - mean(right))
        for left_value, right_value in zip(left, right, strict=True)
    ) / (len(left) - 1)
    return covariance / (left_std * right_std)


def beta(strategy_returns: list[float], benchmark_returns: list[float]) -> float:
    if len(strategy_returns) != len(benchmark_returns):
        raise ValueError("return series must have the same length")
    benchmark_variance = stddev(benchmark_returns) ** 2
    if len(strategy_returns) < 2 or benchmark_variance == 0.0:
        return 0.0
    strategy_mean = mean(strategy_returns)
    benchmark_mean = mean(benchmark_returns)
    covariance = sum(
        (strategy - strategy_mean) * (benchmark - benchmark_mean)
        for strategy, benchmark in zip(
            strategy_returns, benchmark_returns, strict=True
        )
    ) / (len(strategy_returns) - 1)
    return covariance / benchmark_variance


def tracking_error(strategy_returns: list[float], benchmark_returns: list[float]) -> float:
    if len(strategy_returns) != len(benchmark_returns):
        raise ValueError("return series must have the same length")
    active_returns = [
        strategy - benchmark
        for strategy, benchmark in zip(
            strategy_returns, benchmark_returns, strict=True
        )
    ]
    return annualized_volatility(active_returns)


def information_ratio(
    strategy_returns: list[float], benchmark_returns: list[float]
) -> float:
    error = tracking_error(strategy_returns, benchmark_returns)
    if error == 0.0:
        return 0.0
    active_returns = [
        strategy - benchmark
        for strategy, benchmark in zip(
            strategy_returns, benchmark_returns, strict=True
        )
    ]
    return annualized_return(active_returns) / error


def max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    worst = 0.0

    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = equity / peak - 1.0
        worst = min(worst, drawdown)

    return worst


def composite_score(
    annual_return: float,
    sharpe: float,
    sortino: float,
    max_drawdown_value: float,
    annual_turnover: float,
) -> float:
    # Reward return quality, then penalize drawdown and excessive trading.
    drawdown_penalty = abs(max_drawdown_value)
    turnover_penalty = min(annual_turnover, 10.0) * 0.03
    return (
        0.45 * sharpe
        + 0.25 * sortino
        + 1.00 * annual_return
        - 1.25 * drawdown_penalty
        - turnover_penalty
    )
