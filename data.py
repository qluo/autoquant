from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TICKER = "QQQ"
DEFAULT_CSV = DATA_DIR / "qqq.csv"
START_DATE = dt.date(2010, 1, 1)
END_DATE = dt.date(2026, 7, 10)
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


@dataclass(frozen=True)
class Bar:
    """One OHLCV price bar for a single trading date."""

    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: int


def ticker_csv_path(ticker: str) -> Path:
    return DATA_DIR / f"{ticker.lower()}.csv"


def download_bars(
    ticker: str = DEFAULT_TICKER,
    path: Path | None = None,
    start_date: dt.date = START_DATE,
    end_date: dt.date = END_DATE,
) -> Path:
    symbol = ticker.upper()
    output_path = path or ticker_csv_path(symbol)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    period1 = int(time.mktime(start_date.timetuple()))
    period2 = int(time.mktime((end_date + dt.timedelta(days=1)).timetuple()))
    url = (
        f"{YAHOO_CHART_URL}/{symbol}?period1={period1}&period2={period2}"
        "&interval=1d&events=history"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose")

    # Normalize provider-specific JSON into a stable local CSV contract.
    with output_path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"])

        for index, timestamp in enumerate(timestamps):
            values = [
                quote["open"][index],
                quote["high"][index],
                quote["low"][index],
                quote["close"][index],
                quote["volume"][index],
            ]
            if any(value is None for value in values):
                continue

            date = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).date()
            adjusted_close = adjclose[index] if adjclose else quote["close"][index]
            writer.writerow(
                [
                    date.isoformat(),
                    f"{quote['open'][index]:.6f}",
                    f"{quote['high'][index]:.6f}",
                    f"{quote['low'][index]:.6f}",
                    f"{quote['close'][index]:.6f}",
                    f"{adjusted_close:.6f}",
                    int(quote["volume"][index]),
                ]
            )

    return output_path


def download_qqq(path: Path = DEFAULT_CSV) -> Path:
    return download_bars(DEFAULT_TICKER, path)


def load_bars(path: Path = DEFAULT_CSV) -> list[Bar]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run: uv run python data.py --download"
        )

    bars: list[Bar] = []
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")

        for row in reader:
            bars.append(
                Bar(
                    date=dt.date.fromisoformat(row["Date"]),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(float(row["Volume"])),
                )
            )

    if len(bars) < 260:
        raise ValueError(f"{path} has too few rows for the baseline strategy")

    bars.sort(key=lambda bar: bar.date)
    return bars


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.download:
        path = download_bars(args.ticker, args.output)
        print(f"downloaded {path}")
    else:
        path = args.output or ticker_csv_path(args.ticker)
        bars = load_bars(path)
        print(f"loaded {len(bars)} bars from {path}")


if __name__ == "__main__":
    main()
