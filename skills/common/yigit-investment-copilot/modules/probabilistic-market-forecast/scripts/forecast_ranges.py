#!/usr/bin/env python3
"""Produce transparent lognormal and optional empirical forecast ranges."""

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import NormalDist


QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)


def percentile(values, probability):
    ordered = sorted(values)
    if not ordered:
        return None
    index = (len(ordered) - 1) * probability
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def empirical(csv_path, horizon_bars, current_price, target_price, loss_threshold):
    closes = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            closes.append(float(row["close"]))
    if len(closes) <= horizon_bars or any(value <= 0 for value in closes):
        raise SystemExit("history needs more positive closes than horizon-bars")
    returns = [closes[i] / closes[i - horizon_bars] - 1 for i in range(horizon_bars, len(closes))]
    target_return = target_price / current_price - 1 if target_price else None
    return {
        "samples": len(returns),
        "return_quantiles": {f"p{int(q*100)}": percentile(returns, q) for q in QUANTILES},
        "price_quantiles": {f"p{int(q*100)}": current_price * (1 + percentile(returns, q)) for q in QUANTILES},
        "probability_reach_target": sum(value >= target_return for value in returns) / len(returns) if target_return is not None else None,
        "probability_loss_beyond_threshold": sum(value <= -loss_threshold for value in returns) / len(returns),
        "warning": "Rolling samples overlap and may span different regimes; treat this as a base rate, not an independent forecast.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-price", type=float, required=True)
    parser.add_argument("--annualized-vol", type=float, required=True, help="decimal, e.g. 0.40")
    parser.add_argument("--horizon-days", type=float, required=True)
    parser.add_argument("--annualized-drift", type=float, default=0.0, help="conservative decimal expected return")
    parser.add_argument("--target-price", type=float)
    parser.add_argument("--loss-threshold", type=float, default=0.20, help="decimal loss threshold")
    parser.add_argument("--history-csv", type=Path)
    parser.add_argument("--horizon-bars", type=int)
    args = parser.parse_args()
    if args.current_price <= 0 or args.annualized_vol < 0 or args.horizon_days <= 0:
        raise SystemExit("current-price and horizon-days must be positive; volatility non-negative")
    if not 0 < args.loss_threshold < 1:
        raise SystemExit("loss-threshold must be between 0 and 1")

    t = args.horizon_days / 365.0
    mean = (args.annualized_drift - 0.5 * args.annualized_vol ** 2) * t
    stdev = args.annualized_vol * math.sqrt(t)
    normal = NormalDist()
    prices = {}
    for q in QUANTILES:
        log_return = mean + stdev * normal.inv_cdf(q) if stdev else mean
        prices[f"p{int(q*100)}"] = args.current_price * math.exp(log_return)

    probability_target = None
    if args.target_price:
        if args.target_price <= 0:
            raise SystemExit("target-price must be positive")
        threshold = math.log(args.target_price / args.current_price)
        probability_target = 1 - normal.cdf((threshold - mean) / stdev) if stdev else float(mean >= threshold)
    loss_log = math.log(1 - args.loss_threshold)
    probability_loss = normal.cdf((loss_log - mean) / stdev) if stdev else float(mean <= loss_log)

    result = {
        "model": "geometric_brownian_range",
        "inputs": {
            "current_price": args.current_price,
            "annualized_vol": args.annualized_vol,
            "annualized_drift": args.annualized_drift,
            "horizon_days": args.horizon_days,
        },
        "price_quantiles": prices,
        "probability_reach_target": probability_target,
        "probability_loss_beyond_threshold": probability_loss,
        "warning": "This smooth model can understate jumps, gaps, liquidity, leverage and event tails.",
    }
    if args.history_csv:
        if not args.horizon_bars:
            raise SystemExit("--horizon-bars is required with --history-csv")
        result["empirical"] = empirical(args.history_csv, args.horizon_bars, args.current_price, args.target_price, args.loss_threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
