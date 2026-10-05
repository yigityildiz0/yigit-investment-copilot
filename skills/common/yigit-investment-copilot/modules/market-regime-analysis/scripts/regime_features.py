#!/usr/bin/env python3
"""Measure transparent trend, volatility, drawdown and optional breadth features."""

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path


def mean(values):
    return sum(values) / len(values) if values else None


def sample_stdev(values):
    if len(values) < 2:
        return None
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def rolling_volatility(returns, window, periods):
    if len(returns) < window:
        return None, []
    series = [sample_stdev(returns[index - window:index]) * math.sqrt(periods) for index in range(window, len(returns) + 1)]
    return series[-1], series


def percentile_rank(series, value):
    if not series:
        return None
    return sum(item <= value for item in series) / len(series)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--periods-per-year", type=float, default=252.0)
    args = parser.parse_args()
    if args.periods_per_year <= 0:
        raise SystemExit("periods-per-year must be positive")
    rows = []
    with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = {"date": date.fromisoformat(raw["date"]), "close": float(raw["close"])}
            for field in ("volume", "advances", "declines"):
                row[field] = float(raw[field]) if raw.get(field) not in (None, "") else None
            rows.append(row)
    if len(rows) < 21 or any(row["close"] <= 0 for row in rows):
        raise SystemExit("need at least 21 positive closes")
    dates = [row["date"] for row in rows]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise SystemExit("dates must be unique ascending ISO strings")
    closes = [row["close"] for row in rows]
    returns = [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes))]
    vol20, vol_series = rolling_volatility(returns, 20, args.periods_per_year)
    vol60, _ = rolling_volatility(returns, 60, args.periods_per_year)
    peak = max(closes)
    result = {
        "as_of": dates[-1].isoformat(),
        "observations": len(rows),
        "close": closes[-1],
        "return_20": closes[-1] / closes[-21] - 1,
        "sma20": mean(closes[-20:]),
        "sma60": mean(closes[-60:]) if len(closes) >= 60 else None,
        "sma200": mean(closes[-200:]) if len(closes) >= 200 else None,
        "annualized_volatility_20": vol20,
        "annualized_volatility_60": vol60,
        "volatility_20_percentile_in_sample": percentile_rank(vol_series, vol20),
        "drawdown_from_sample_peak": closes[-1] / peak - 1,
    }
    last = rows[-1]
    if last["advances"] is not None or last["declines"] is not None:
        if last["advances"] is None or last["declines"] is None or min(last["advances"], last["declines"]) < 0 or last["advances"] + last["declines"] == 0:
            raise SystemExit("advances and declines must be supplied together and non-negative")
        result["advance_share"] = last["advances"] / (last["advances"] + last["declines"])
    if any(row["volume"] is not None for row in rows):
        if any(row["volume"] is None or row["volume"] < 0 for row in rows):
            raise SystemExit("volume must be complete and non-negative when supplied")
        result["volume_vs_20_period_average"] = rows[-1]["volume"] / mean([row["volume"] for row in rows[-20:]]) if mean([row["volume"] for row in rows[-20:]]) else None
    result["boundary"] = "Measurements only. Macro, liquidity, revisions, events and cross-asset evidence must be analyzed separately before assigning a regime."
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
