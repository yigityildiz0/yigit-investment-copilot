#!/usr/bin/env python3
"""Transparent scenario math for futures and warrant expiry payoffs."""

import argparse
import json
from decimal import Decimal


def d(value: str) -> Decimal:
    return Decimal(value)


def scenarios(raw: str):
    return [d(item.strip()) for item in raw.split(",")]


def futures(args):
    sign = Decimal("1") if args.direction == "long" else Decimal("-1")
    rows = []
    for exit_price in scenarios(args.exit_prices):
        gross = sign * (exit_price - args.entry) * args.multiplier * args.contracts
        net = gross - args.roundtrip_fees
        rows.append({
            "exit_price": str(exit_price),
            "gross_pnl": str(gross),
            "net_pnl": str(net),
            "return_on_initial_margin_pct": str(net / args.initial_margin * Decimal("100")),
        })
    return {
        "mode": "futures",
        "notional_at_entry": str(args.entry * args.multiplier * args.contracts),
        "initial_margin": str(args.initial_margin),
        "scenarios": rows,
        "warning": "Daily mark-to-market, margin changes, gaps and forced liquidation can make realized outcomes differ and losses can exceed initial margin.",
    }


def warrant(args):
    rows = []
    cost = args.warrant_price * args.warrants + args.roundtrip_fees
    for underlying in scenarios(args.underlying_prices):
        intrinsic_underlying = max(Decimal("0"), underlying - args.strike) if args.option_type == "call" else max(Decimal("0"), args.strike - underlying)
        expiry_value = intrinsic_underlying * args.ratio * args.warrants
        pnl = expiry_value - cost
        rows.append({
            "underlying_at_expiry": str(underlying),
            "warrant_expiry_value": str(expiry_value),
            "net_pnl": str(pnl),
            "return_on_cost_pct": str(pnl / cost * Decimal("100")) if cost else None,
        })
    return {
        "mode": "warrant_expiry_intrinsic_only",
        "total_cost": str(cost),
        "scenarios": rows,
        "warning": "This is expiry intrinsic value only. Pre-expiry price also depends on time, implied volatility, rates, dividends, spread, liquidity, ratio and issuer quotes.",
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    fut = sub.add_parser("futures")
    fut.add_argument("--direction", choices=["long", "short"], required=True)
    fut.add_argument("--entry", type=d, required=True)
    fut.add_argument("--exit-prices", required=True)
    fut.add_argument("--multiplier", type=d, required=True)
    fut.add_argument("--contracts", type=d, required=True)
    fut.add_argument("--initial-margin", type=d, required=True)
    fut.add_argument("--roundtrip-fees", type=d, default=Decimal("0"))

    war = sub.add_parser("warrant")
    war.add_argument("--option-type", choices=["call", "put"], required=True)
    war.add_argument("--strike", type=d, required=True)
    war.add_argument("--ratio", type=d, required=True, help="warrant value per one unit of underlying intrinsic")
    war.add_argument("--warrant-price", type=d, required=True)
    war.add_argument("--warrants", type=d, required=True)
    war.add_argument("--underlying-prices", required=True)
    war.add_argument("--roundtrip-fees", type=d, default=Decimal("0"))

    args = parser.parse_args()
    if args.mode == "futures":
        if min(args.entry, args.multiplier, args.contracts, args.initial_margin) <= 0:
            raise SystemExit("positive futures inputs required")
        result = futures(args)
    else:
        if min(args.strike, args.ratio, args.warrant_price, args.warrants) <= 0:
            raise SystemExit("positive warrant inputs required")
        result = warrant(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
