#!/usr/bin/env python3
"""Reconcile same-asset quotes across crypto venues."""

import argparse
import datetime as dt
import json
import statistics
from pathlib import Path


def parse_time(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("quotes", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--max-age-seconds", type=int, default=300)
    args = parser.parse_args()
    rows = json.loads(args.quotes.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) < 2:
        raise SystemExit("need at least two quote records")
    identity = {(row["network"], row["contract"].lower(), row["pair"], row["quote_currency"]) for row in rows}
    if len(identity) != 1:
        raise SystemExit("quotes do not share network, contract, pair and quote currency")
    as_of = parse_time(args.as_of) if args.as_of else dt.datetime.now(dt.timezone.utc)
    prices = [float(row["price"]) for row in rows]
    if any(price <= 0 for price in prices):
        raise SystemExit("prices must be positive")
    median = statistics.median(prices)
    output_rows = []
    stale = False
    for row, price in zip(rows, prices):
        age = (as_of - parse_time(row["timestamp"])).total_seconds()
        stale = stale or age > args.max_age_seconds
        output_rows.append({
            "venue": row["venue"],
            "price": price,
            "age_seconds": age,
            "deviation_from_median_bps": (price / median - 1) * 10000,
        })
    max_dispersion = (max(prices) / min(prices) - 1) * 10000
    status = "CONDITIONAL" if stale or max_dispersion > 100 else "PASS"
    print(json.dumps({
        "status": status,
        "identity": list(identity)[0],
        "median_price": median,
        "max_venue_dispersion_bps": max_dispersion,
        "quotes": output_rows,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
