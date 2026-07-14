from __future__ import annotations

import hashlib
import json
import argparse
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from config import (
    DEFAULT_TRANSACTION_COST_BPS,
    DEVELOPMENT_END,
    PROMOTION_COST_SCENARIOS_BPS,
    VALIDATION_END,
    VALIDATION_FOLDS,
)
from data import (
    DEFAULT_CSV,
    DEFAULT_TICKER,
    RISK_FREE_CSV,
    Bar,
    load_bars,
    load_risk_free_daily,
    metadata_path,
)
from metrics import (
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    annualized_volatility,
    beta,
    composite_score,
    compound_return,
    correlation,
    downside_deviation,
    information_ratio,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    tracking_error,
)
from strategy import generate_signals
from validate import validate_bars, validate_signals, validate_strategy_causality


RUNS_DIR = Path(__file__).resolve().parent / "runs"
LATEST_RESULT_JSON = RUNS_DIR / "latest_result.json"
TRUSTED_FILES = (
    "Dockerfile",
    "backtest.py",
    "config.py",
    "data.py",
    "experiment_manifest.py",
    "evaluation.py",
    "ledger.py",
    "memory.py",
    "metrics.py",
    "promote_candidate.py",
    "program.md",
    "record_result.py",
    "robustness.py",
    "sandbox_runner.py",
    "universe_registry.py",
    "validate.py",
    "pyproject.toml",
    "tests/test_backtest.py",
    "tests/test_evaluation.py",
    "tests/test_daily_controller.py",
    "tests/test_data.py",
    "tests/test_ledger.py",
    "tests/test_memory.py",
    "tests/test_metrics.py",
    "tests/test_no_lookahead.py",
    "tests/test_strategy.py",
    "tests/test_universe_registry.py",
    "uv.lock",
)


@dataclass(frozen=True)
class MetricSummary:
    total_return: float
    annual_return: float
    annual_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    annual_turnover: float
    num_trades: int
    composite_score: float
    sharpe_valid: bool
    sortino_valid: bool


@dataclass(frozen=True)
class BacktestResult:
    full: MetricSummary
    development: MetricSummary
    validation: MetricSummary
    benchmark: MetricSummary
    excess_annual_return: float
    tracking_error: float
    information_ratio: float
    beta: float
    correlation: float
    average_exposure: float
    percent_days_invested: float
    annual_metrics: dict[str, dict[str, float]]
    validation_folds: dict[str, dict[str, float]]
    cost_scenarios: dict[str, dict[str, float]]
    risk_free: dict[str, object]
    start_date: str
    end_date: str
    num_bars: int


def _daily_strategy_returns(
    bars: list[Bar],
    signals: list[float],
    transaction_cost_bps: float,
    risk_free_daily: list[float] | None = None,
) -> tuple[list[float], list[float], list[float]]:
    # signal[t] fills at close[t+1] and starts earning after that close.
    positions = [0.0, 0.0] + signals[:-2]
    if risk_free_daily is None:
        risk_free_daily = [0.0] * len(bars)
    if len(risk_free_daily) != len(bars):
        raise ValueError("risk-free and bar series must have the same length")
    returns: list[float] = []
    turnovers: list[float] = []
    effective_positions: list[float] = []
    previous_position = 0.0

    for index in range(1, len(bars)):
        adjusted_return = (
            bars[index].adjusted_close / bars[index - 1].adjusted_close - 1.0
        )
        cash_return = risk_free_daily[index]
        position = positions[index]
        turnover = abs(position - previous_position)
        cost = turnover * transaction_cost_bps / 10_000.0
        returns.append(position * adjusted_return + (1.0 - position) * cash_return - cost)
        turnovers.append(turnover)
        effective_positions.append(position)
        previous_position = position

    return returns, turnovers, effective_positions


def _metric_summary(
    returns: list[float],
    turnovers: list[float],
    risk_free_returns: list[float] | None = None,
) -> MetricSummary:
    if risk_free_returns is None:
        risk_free_returns = [0.0] * len(returns)
    if len(risk_free_returns) != len(returns):
        raise ValueError("risk-free and return series must have the same length")
    annual_return = annualized_return(returns)
    sharpe = sharpe_ratio(returns, risk_free_returns)
    sortino = sortino_ratio(returns, risk_free_returns)
    volatility = annualized_volatility(returns)
    downside = downside_deviation(returns, risk_free_returns)
    drawdown = max_drawdown(returns)
    annual_turnover = (
        sum(turnovers) / len(turnovers) * TRADING_DAYS_PER_YEAR if turnovers else 0.0
    )
    return MetricSummary(
        total_return=compound_return(returns),
        annual_return=annual_return,
        annual_volatility=volatility,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=drawdown,
        annual_turnover=annual_turnover,
        num_trades=sum(turnover > 0.0 for turnover in turnovers),
        composite_score=composite_score(
            annual_return=annual_return,
            sharpe=sharpe,
            sortino=sortino,
            max_drawdown_value=drawdown,
            annual_turnover=annual_turnover,
        ),
        sharpe_valid=volatility > 0.0,
        sortino_valid=downside > 0.0,
    )


def _select(values: list[float], indices: list[int]) -> list[float]:
    return [values[index] for index in indices]


def run_backtest(
    bars: list[Bar],
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
) -> BacktestResult:
    validate_bars(bars)
    research_bars = [bar for bar in bars if bar.date <= VALIDATION_END]
    if len(research_bars) < 2:
        raise ValueError("bars do not cover the research evaluation windows")

    signals = generate_signals(research_bars)
    validate_signals(signals, research_bars)
    validate_strategy_causality(generate_signals, research_bars, signals)
    risk_free_daily, risk_free_metadata = load_risk_free_daily(research_bars)
    returns, turnovers, positions = _daily_strategy_returns(
        research_bars, signals, transaction_cost_bps, risk_free_daily
    )

    return_dates = [bar.date for bar in research_bars[1:]]
    development_indices = [
        index for index, date in enumerate(return_dates) if date <= DEVELOPMENT_END
    ]
    validation_indices = [
        index
        for index, date in enumerate(return_dates)
        if DEVELOPMENT_END < date <= VALIDATION_END
    ]
    if not development_indices or not validation_indices:
        raise ValueError("bars must cover both development and validation windows")

    validation_returns = _select(returns, validation_indices)
    validation_turnovers = _select(turnovers, validation_indices)
    interval_risk_free = risk_free_daily[1:]
    benchmark_signals = [1.0] * len(research_bars)
    benchmark_returns, benchmark_turnovers, _ = _daily_strategy_returns(
        research_bars, benchmark_signals, transaction_cost_bps, risk_free_daily
    )
    validation_benchmark_returns = _select(benchmark_returns, validation_indices)
    validation_benchmark_turnovers = _select(benchmark_turnovers, validation_indices)

    cost_scenarios: dict[str, dict[str, float]] = {}
    for cost_bps in PROMOTION_COST_SCENARIOS_BPS:
        scenario_returns, scenario_turnovers, _ = _daily_strategy_returns(
            research_bars, signals, cost_bps, risk_free_daily
        )
        scenario = _metric_summary(
            _select(scenario_returns, validation_indices),
            _select(scenario_turnovers, validation_indices),
            _select(interval_risk_free, validation_indices),
        )
        cost_scenarios[f"{cost_bps:g}_bps"] = {
            "annual_return": scenario.annual_return,
            "sharpe": scenario.sharpe,
            "composite_score": scenario.composite_score,
        }

    validation_positions = _select(positions, validation_indices)
    annual_metrics: dict[str, dict[str, float]] = {}
    for year in sorted({return_dates[index].year for index in validation_indices}):
        year_indices = [
            index for index in validation_indices if return_dates[index].year == year
        ]
        year_summary = _metric_summary(
            _select(returns, year_indices),
            _select(turnovers, year_indices),
            _select(interval_risk_free, year_indices),
        )
        year_positions = _select(positions, year_indices)
        annual_metrics[str(year)] = {
            "total_return": year_summary.total_return,
            "sharpe": year_summary.sharpe,
            "max_drawdown": year_summary.max_drawdown,
            "annual_turnover": year_summary.annual_turnover,
            "average_exposure": sum(year_positions) / len(year_positions),
        }

    validation_folds: dict[str, dict[str, float]] = {}
    for fold_start, fold_end in VALIDATION_FOLDS:
        fold_indices = [
            index
            for index, date in enumerate(return_dates)
            if fold_start <= date <= fold_end
        ]
        if not fold_indices:
            continue
        fold_summary = _metric_summary(
            _select(returns, fold_indices),
            _select(turnovers, fold_indices),
            _select(interval_risk_free, fold_indices),
        )
        validation_folds[f"{fold_start}_{fold_end}"] = {
            "annual_return": fold_summary.annual_return,
            "sharpe": fold_summary.sharpe,
            "max_drawdown": fold_summary.max_drawdown,
            "composite_score": fold_summary.composite_score,
        }

    return BacktestResult(
        full=_metric_summary(returns, turnovers, interval_risk_free),
        development=_metric_summary(
            _select(returns, development_indices),
            _select(turnovers, development_indices),
            _select(interval_risk_free, development_indices),
        ),
        validation=_metric_summary(
            validation_returns,
            validation_turnovers,
            _select(interval_risk_free, validation_indices),
        ),
        benchmark=_metric_summary(
            validation_benchmark_returns,
            validation_benchmark_turnovers,
            _select(interval_risk_free, validation_indices),
        ),
        excess_annual_return=(
            annualized_return(validation_returns)
            - annualized_return(validation_benchmark_returns)
        ),
        tracking_error=tracking_error(
            validation_returns, validation_benchmark_returns
        ),
        information_ratio=information_ratio(
            validation_returns, validation_benchmark_returns
        ),
        beta=beta(validation_returns, validation_benchmark_returns),
        correlation=correlation(validation_returns, validation_benchmark_returns),
        average_exposure=(
            sum(validation_positions) / len(validation_positions)
            if validation_positions
            else 0.0
        ),
        percent_days_invested=(
            sum(position > 0.0 for position in validation_positions)
            / len(validation_positions)
            if validation_positions
            else 0.0
        ),
        annual_metrics=annual_metrics,
        validation_folds=validation_folds,
        cost_scenarios=cost_scenarios,
        risk_free=risk_free_metadata,
        start_date=str(research_bars[0].date),
        end_date=str(research_bars[-1].date),
        num_bars=len(research_bars),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open() as file:
        return max(sum(1 for _ in file) - 1, 0)


def trusted_harness_sha256(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in TRUSTED_FILES:
        path = root / name
        digest.update(name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def changed_files(root: Path | None = None) -> list[str]:
    root = root or Path(__file__).resolve().parent
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    return sorted(line[3:] for line in result.stdout.splitlines() if line)


def result_to_dict(
    result: BacktestResult,
    ticker: str = DEFAULT_TICKER,
    data_path: Path = DEFAULT_CSV,
) -> dict[str, object]:
    changes = changed_files()
    trusted_changes = sorted(
        path for path in changes if path in TRUSTED_FILES or path.startswith("tests/")
    )
    sidecar = metadata_path(data_path)
    provenance = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    return {
        "ticker": ticker,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "evaluation_mode": "research",
        "metric_conventions": {
            "trading_days_per_year": TRADING_DAYS_PER_YEAR,
            "risk_free_return": "pinned_daily_series_or_zero_rate_fallback",
            "ratio_return": "arithmetic_daily_excess",
            "zero_denominator": "ratio_zero_with_validity_flag_false",
        },
        "windows": {
            "development_end": str(DEVELOPMENT_END),
            "validation_end": str(VALIDATION_END),
        },
        "data": {
            "path": str(data_path),
            "sha256": _sha256(data_path) if data_path.exists() else None,
            "adjustment": "adjusted_close_total_return",
            "source": provenance.get("source", "Yahoo Finance chart API"),
            "retrieved_at_utc": provenance.get("retrieved_at_utc"),
            "calendar": provenance.get("calendar", "provider_trading_sessions"),
            "row_count": _csv_row_count(data_path),
            "missing_session_policy": "accept provider trading sessions; reject duplicate dates",
        },
        "integrity": {
            "strategy_sha256": _sha256(Path(__file__).resolve().parent / "strategy.py"),
            "harness_sha256": trusted_harness_sha256(),
            "changed_files": changes,
            "trusted_files_clean": not trusted_changes,
            "trusted_file_changes": trusted_changes,
            "prefix_invariance_passed": True,
        },
        "metrics": {
            "full": asdict(result.full),
            "development": asdict(result.development),
            "validation": asdict(result.validation),
            "average_exposure": result.average_exposure,
            "percent_days_invested": result.percent_days_invested,
            "annual": result.annual_metrics,
            "validation_folds": result.validation_folds,
        },
        "benchmark": {"name": f"buy_and_hold_{ticker}", **asdict(result.benchmark)},
        "relative_metrics": {
            "excess_annual_return": result.excess_annual_return,
            "tracking_error": result.tracking_error,
            "information_ratio": result.information_ratio,
            "beta": result.beta,
            "correlation": result.correlation,
        },
        "cost_scenarios": result.cost_scenarios,
        "risk_free": result.risk_free,
    }


def write_latest_result(
    result: BacktestResult,
    path: Path = LATEST_RESULT_JSON,
    ticker: str = DEFAULT_TICKER,
    data_path: Path = DEFAULT_CSV,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = result_to_dict(result, ticker, data_path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def print_result(result: BacktestResult) -> None:
    print("---")
    print(f"start_date:             {result.start_date}")
    print(f"end_date:               {result.end_date}")
    print(f"num_bars:               {result.num_bars}")
    print(f"validation_return:      {result.validation.annual_return:.6f}")
    print(f"validation_sharpe:      {result.validation.sharpe:.6f}")
    print(f"validation_drawdown:    {result.validation.max_drawdown:.6f}")
    print(f"validation_score:       {result.validation.composite_score:.6f}")
    print(f"benchmark_return:       {result.benchmark.annual_return:.6f}")
    print(f"excess_annual_return:   {result.excess_annual_return:.6f}")
    print(f"annual_turnover:        {result.validation.annual_turnover:.6f}")
    print(f"average_exposure:       {result.average_exposure:.6f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=LATEST_RESULT_JSON)
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    args = parser.parse_args()

    bars = load_bars(args.data)
    result = run_backtest(bars)
    print_result(result)
    write_latest_result(result, args.output, args.ticker, args.data)


if __name__ == "__main__":
    main()
