#!/usr/bin/env python3
"""Compute transparent fund and optional benchmark metrics from dated values."""

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path


def sample_stdev(values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def compound_return(values):
    result = 1.0
    for value in values:
        result *= 1 + value
    return result - 1


def drawdown(values):
    peak_value = values[0][1]
    peak_date = values[0][0]
    worst = 0.0
    worst_peak = peak_date
    trough_date = peak_date
    for current_date, value in values:
        if value > peak_value:
            peak_value = value
            peak_date = current_date
        current = value / peak_value - 1
        if current < worst:
            worst = current
            worst_peak = peak_date
            trough_date = current_date
    recovery = next((current_date for current_date, value in values if current_date > trough_date and value >= dict(values)[worst_peak]), None)
    return worst, worst_peak, trough_date, recovery


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--value-column", default="value")
    parser.add_argument("--benchmark-column")
    parser.add_argument("--periods-per-year", type=float, default=252.0)
    parser.add_argument("--risk-free-annual", type=float, default=0.0)
    args = parser.parse_args()
    if args.periods_per_year <= 0 or args.risk_free_annual <= -1:
        raise SystemExit("periods-per-year must be positive and risk-free-annual greater than -1")

    rows = []
    with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            current = date.fromisoformat(row[args.date_column])
            fund = float(row[args.value_column])
            benchmark = float(row[args.benchmark_column]) if args.benchmark_column and row.get(args.benchmark_column) not in (None, "") else None
            rows.append((current, fund, benchmark))
    rows.sort(key=lambda row: row[0])
    if len(rows) < 3 or len({row[0] for row in rows}) != len(rows):
        raise SystemExit("need at least three unique dated observations")
    if any(row[1] <= 0 or (row[2] is not None and row[2] <= 0) for row in rows):
        raise SystemExit("fund and benchmark values must be positive")
    if args.benchmark_column and any(row[2] is None for row in rows):
        raise SystemExit("benchmark column must be complete when supplied")

    fund_returns = [rows[index][1] / rows[index - 1][1] - 1 for index in range(1, len(rows))]
    days = (rows[-1][0] - rows[0][0]).days
    if days <= 0:
        raise SystemExit("date range must be positive")
    total_return = rows[-1][1] / rows[0][1] - 1
    annualized_return = (1 + total_return) ** (365 / days) - 1
    volatility_period = sample_stdev(fund_returns)
    annualized_volatility = volatility_period * math.sqrt(args.periods_per_year) if volatility_period is not None else None
    risk_free_period = (1 + args.risk_free_annual) ** (1 / args.periods_per_year) - 1
    excess = [value - risk_free_period for value in fund_returns]
    sharpe = (sum(excess) / len(excess)) / volatility_period * math.sqrt(args.periods_per_year) if volatility_period else None
    downside = math.sqrt(sum(min(0.0, value) ** 2 for value in excess) / len(excess))
    sortino = (sum(excess) / len(excess)) / downside * math.sqrt(args.periods_per_year) if downside else None
    maximum_drawdown, peak_date, trough_date, recovery_date = drawdown([(row[0], row[1]) for row in rows])

    result = {
        "observations": len(rows),
        "start": rows[0][0].isoformat(),
        "end": rows[-1][0].isoformat(),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": maximum_drawdown,
        "drawdown_peak_date": peak_date.isoformat(),
        "drawdown_trough_date": trough_date.isoformat(),
        "drawdown_recovery_date": recovery_date.isoformat() if recovery_date else None,
    }

    if args.benchmark_column:
        benchmark_returns = [rows[index][2] / rows[index - 1][2] - 1 for index in range(1, len(rows))]
        active_returns = [fund - benchmark for fund, benchmark in zip(fund_returns, benchmark_returns)]
        tracking_period = sample_stdev(active_returns)
        tracking_error = tracking_period * math.sqrt(args.periods_per_year) if tracking_period is not None else None
        information_ratio = (sum(active_returns) / len(active_returns)) / tracking_period * math.sqrt(args.periods_per_year) if tracking_period else None
        positive_benchmark = [index for index, value in enumerate(benchmark_returns) if value > 0]
        negative_benchmark = [index for index, value in enumerate(benchmark_returns) if value < 0]
        upside_benchmark_return = compound_return([benchmark_returns[index] for index in positive_benchmark]) if positive_benchmark else None
        downside_benchmark_return = compound_return([benchmark_returns[index] for index in negative_benchmark]) if negative_benchmark else None
        upside_capture = compound_return([fund_returns[index] for index in positive_benchmark]) / upside_benchmark_return if upside_benchmark_return not in (None, 0) else None
        downside_capture = compound_return([fund_returns[index] for index in negative_benchmark]) / downside_benchmark_return if downside_benchmark_return not in (None, 0) else None
        result["benchmark"] = {
            "total_return": rows[-1][2] / rows[0][2] - 1,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "upside_capture": upside_capture,
            "downside_capture": downside_capture,
        }

    result["assumptions"] = {
        "periods_per_year": args.periods_per_year,
        "risk_free_annual": args.risk_free_annual,
        "note": "Input observations should be regular, same-currency, distribution-adjusted values. Metrics do not verify mandate changes, fees, tax or benchmark fitness.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
