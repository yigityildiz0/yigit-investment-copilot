#!/usr/bin/env python3
"""Compute transparent return and risk metrics from dated fund values."""

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--value-column", default="value")
    parser.add_argument("--risk-free-annual", type=float, default=0.0)
    args = parser.parse_args()

    rows = []
    with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append((date.fromisoformat(row[args.date_column]), float(row[args.value_column])))
    rows.sort()
    if len(rows) < 3 or any(value <= 0 for _, value in rows):
        raise SystemExit("need at least three positive dated values")

    returns = [rows[i][1] / rows[i - 1][1] - 1 for i in range(1, len(rows))]
    days = (rows[-1][0] - rows[0][0]).days
    if days <= 0:
        raise SystemExit("date range must be positive")
    total_return = rows[-1][1] / rows[0][1] - 1
    annualized_return = (rows[-1][1] / rows[0][1]) ** (365 / days) - 1
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(1, len(returns) - 1)
    annualized_vol = math.sqrt(variance) * math.sqrt(252)
    daily_rf = (1 + args.risk_free_annual) ** (1 / 252) - 1
    sharpe = ((mean - daily_rf) / math.sqrt(variance) * math.sqrt(252)) if variance > 0 else None
    downside = [min(0.0, value - daily_rf) for value in returns]
    downside_dev = math.sqrt(sum(value * value for value in downside) / len(downside))
    sortino = ((mean - daily_rf) / downside_dev * math.sqrt(252)) if downside_dev > 0 else None

    peak = rows[0][1]
    max_drawdown = 0.0
    drawdown_start = rows[0][0]
    trough_date = rows[0][0]
    peak_date = rows[0][0]
    for current_date, value in rows:
        if value > peak:
            peak = value
            peak_date = current_date
        drawdown = value / peak - 1
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            drawdown_start = peak_date
            trough_date = current_date

    output = {
        "observations": len(rows),
        "start": rows[0][0].isoformat(),
        "end": rows[-1][0].isoformat(),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "drawdown_peak_date": drawdown_start.isoformat(),
        "drawdown_trough_date": trough_date.isoformat(),
        "assumption": "252 observations/year; input frequency should be regular trading-day NAV data.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
