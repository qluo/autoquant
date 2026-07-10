from __future__ import annotations

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


# BPS means basis points. 1 basis point is 0.01%, so 2 bps is 0.02%.
# TRANSACTION_COST_BPS is the one-way trading cost charged per unit of turnover.
TRANSACTION_COST_BPS = 2.0


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
    # First data date used in the backtest.
    start_date: str
    # Last data date used in the backtest.
    end_date: str
    # Number of daily bars loaded.
    num_bars: int


def _validate_signals(signals: list[float], bars: list[Bar]) -> None:
    if len(signals) != len(bars):
        raise ValueError("strategy returned a signal count that does not match bars")
    for index, signal in enumerate(signals):
        if signal < 0.0 or signal > 1.0:
            raise ValueError(f"signal at index {index} is outside [0.0, 1.0]")


def run_backtest(bars: list[Bar]) -> BacktestResult:
    signals = generate_signals(bars)
    _validate_signals(signals, bars)

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
        cost = turnover * TRANSACTION_COST_BPS / 10_000.0
        returns.append(position * close_return - cost)
        turnovers.append(turnover)
        previous_position = position

    total = compound_return(returns)
    annual_return = annualized_return(returns)
    annual_volatility = annualized_volatility(returns)
    sharpe = sharpe_ratio(returns)
    sortino = sortino_ratio(returns)
    drawdown = max_drawdown(returns)
    annual_turnover = sum(turnovers) / len(turnovers) * TRADING_DAYS_PER_YEAR
    num_trades = sum(1 for value in turnovers if value > 0.0)
    score = composite_score(
        annual_return=annual_return,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_value=drawdown,
        annual_turnover=annual_turnover,
    )

    return BacktestResult(
        total_return=total,
        annual_return=annual_return,
        annual_volatility=annual_volatility,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=drawdown,
        annual_turnover=annual_turnover,
        num_trades=num_trades,
        composite_score=score,
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


def main() -> None:
    bars = load_bars()
    result = run_backtest(bars)
    print_result(result)


if __name__ == "__main__":
    main()
