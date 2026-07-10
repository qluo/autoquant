from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from data import Bar, load_bars
from metrics import (
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    annualized_volatility,
    composite_score,
    compound_return,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
)
from strategy import generate_signals
from validate import validate_bars, validate_signals


# BPS means basis points. 1 basis point is 0.01%, so 2 bps is 0.02%.
# TRANSACTION_COST_BPS is the one-way trading cost charged per unit of turnover.
TRANSACTION_COST_BPS = 2.0
SPLIT_DATE = dt.date(2020, 1, 1)


@dataclass(frozen=True)
class BacktestResult:
    """Standard metrics emitted by the offline backtest."""

    # Total compounded return over the full backtest period.
    total_return: float
    # Annualized compounded return, assuming 252 trading days per year.
    annual_return: float
    # Annualized standard deviation of daily strategy returns.
    annual_volatility: float
    # Return per unit of total volatility. Higher is better.
    sharpe: float
    # Return per unit of downside volatility. Higher is better.
    sortino: float
    # Worst peak-to-trough equity decline. This is usually negative.
    max_drawdown: float
    # Annualized sum of absolute position changes.
    annual_turnover: float
    # Number of days where exposure changed.
    num_trades: int
    # Weighted score combining return, risk, drawdown, and turnover.
    composite_score: float
    # First date assigned to the out-of-sample evaluation window.
    split_date: str
    # Composite score before split_date. Useful for detecting overfit ideas.
    in_sample_composite_score: float
    # Composite score on and after split_date. This is the primary research score.
    out_of_sample_composite_score: float
    # Out-of-sample Sharpe ratio.
    out_of_sample_sharpe: float
    # Out-of-sample worst peak-to-trough equity decline.
    out_of_sample_max_drawdown: float
    # First data date used in the backtest.
    start_date: str
    # Last data date used in the backtest.
    end_date: str
    # Number of daily bars loaded.
    num_bars: int


def _daily_strategy_returns(
    bars: list[Bar],
    signals: list[float],
    transaction_cost_bps: float,
) -> tuple[list[float], list[float]]:
    # Execute today's signal on the next bar to avoid same-close lookahead.
    positions = [0.0] + signals[:-1]
    returns: list[float] = []
    turnovers: list[float] = []
    previous_position = 0.0

    for index in range(1, len(bars)):
        close_return = bars[index].close / bars[index - 1].close - 1.0
        position = positions[index]
        turnover = abs(position - previous_position)
        # Cost is charged on absolute exposure change, e.g. 0->1 or 1->0.
        cost = turnover * transaction_cost_bps / 10_000.0
        returns.append(position * close_return - cost)
        turnovers.append(turnover)
        previous_position = position

    return returns, turnovers


def _metric_summary(returns: list[float], turnovers: list[float]) -> dict[str, float]:
    annual_return = annualized_return(returns)
    sharpe = sharpe_ratio(returns)
    sortino = sortino_ratio(returns)
    drawdown = max_drawdown(returns)
    annual_turnover = (
        sum(turnovers) / len(turnovers) * TRADING_DAYS_PER_YEAR if turnovers else 0.0
    )
    score = composite_score(
        annual_return=annual_return,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_value=drawdown,
        annual_turnover=annual_turnover,
    )
    return {
        "annual_return": annual_return,
        "annual_volatility": annualized_volatility(returns),
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": drawdown,
        "annual_turnover": annual_turnover,
        "composite_score": score,
    }


def run_backtest(
    bars: list[Bar],
    transaction_cost_bps: float = TRANSACTION_COST_BPS,
) -> BacktestResult:
    validate_bars(bars)
    signals = generate_signals(bars)
    validate_signals(signals, bars)
    returns, turnovers = _daily_strategy_returns(bars, signals, transaction_cost_bps)

    total = compound_return(returns)
    full_metrics = _metric_summary(returns, turnovers)
    num_trades = sum(1 for value in turnovers if value > 0.0)

    # Return index 0 corresponds to bars[1], so use bars[1:] for split labels.
    return_dates = [bar.date for bar in bars[1:]]
    in_sample_indices = [
        index for index, return_date in enumerate(return_dates) if return_date < SPLIT_DATE
    ]
    out_of_sample_indices = [
        index for index, return_date in enumerate(return_dates) if return_date >= SPLIT_DATE
    ]
    if not in_sample_indices or not out_of_sample_indices:
        raise ValueError(f"bars must cover both sides of split date {SPLIT_DATE}")

    in_sample_metrics = _metric_summary(
        [returns[index] for index in in_sample_indices],
        [turnovers[index] for index in in_sample_indices],
    )
    out_of_sample_metrics = _metric_summary(
        [returns[index] for index in out_of_sample_indices],
        [turnovers[index] for index in out_of_sample_indices],
    )

    return BacktestResult(
        total_return=total,
        annual_return=full_metrics["annual_return"],
        annual_volatility=full_metrics["annual_volatility"],
        sharpe=full_metrics["sharpe"],
        sortino=full_metrics["sortino"],
        max_drawdown=full_metrics["max_drawdown"],
        annual_turnover=full_metrics["annual_turnover"],
        num_trades=num_trades,
        composite_score=full_metrics["composite_score"],
        split_date=str(SPLIT_DATE),
        in_sample_composite_score=in_sample_metrics["composite_score"],
        out_of_sample_composite_score=out_of_sample_metrics["composite_score"],
        out_of_sample_sharpe=out_of_sample_metrics["sharpe"],
        out_of_sample_max_drawdown=out_of_sample_metrics["max_drawdown"],
        start_date=str(bars[0].date),
        end_date=str(bars[-1].date),
        num_bars=len(bars),
    )


def print_result(result: BacktestResult) -> None:
    print("---")
    print(f"start_date:         {result.start_date}")
    print(f"end_date:           {result.end_date}")
    print(f"num_bars:           {result.num_bars}")
    print(f"total_return:       {result.total_return:.6f}")
    print(f"annual_return:      {result.annual_return:.6f}")
    print(f"annual_volatility:  {result.annual_volatility:.6f}")
    print(f"sharpe:             {result.sharpe:.6f}")
    print(f"sortino:            {result.sortino:.6f}")
    print(f"max_drawdown:       {result.max_drawdown:.6f}")
    print(f"annual_turnover:    {result.annual_turnover:.6f}")
    print(f"num_trades:         {result.num_trades}")
    print(f"composite_score:    {result.composite_score:.6f}")
    print(f"split_date:         {result.split_date}")
    print(f"is_score:           {result.in_sample_composite_score:.6f}")
    print(f"oos_score:          {result.out_of_sample_composite_score:.6f}")
    print(f"oos_sharpe:         {result.out_of_sample_sharpe:.6f}")
    print(f"oos_max_drawdown:   {result.out_of_sample_max_drawdown:.6f}")


def main() -> None:
    bars = load_bars()
    result = run_backtest(bars)
    print_result(result)


if __name__ == "__main__":
    main()
