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


def sharpe_ratio(returns: list[float]) -> float:
    volatility = annualized_volatility(returns)
    if volatility == 0.0:
        return 0.0
    return annualized_return(returns) / volatility


def sortino_ratio(returns: list[float]) -> float:
    downside = [min(value, 0.0) for value in returns]
    downside_deviation = stddev(downside) * math.sqrt(TRADING_DAYS_PER_YEAR)
    if downside_deviation == 0.0:
        return 0.0
    return annualized_return(returns) / downside_deviation


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
