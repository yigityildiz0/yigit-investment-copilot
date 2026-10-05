#!/usr/bin/env python3
"""Size an ordinary long cash position from budget and loss limits."""

import argparse
import json
from decimal import Decimal, ROUND_FLOOR, InvalidOperation


def dec(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"invalid decimal: {value}") from exc


def floor_lot(value: Decimal, lot: Decimal) -> Decimal:
    return (value / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=dec, required=True)
    parser.add_argument("--entry", type=dec, required=True)
    parser.add_argument("--stop", type=dec, required=True)
    parser.add_argument("--max-loss", type=dec, required=True)
    parser.add_argument("--lot-size", type=dec, default=Decimal("1"))
    parser.add_argument("--buy-fee-rate", type=dec, default=Decimal("0"), help="decimal rate, e.g. 0.001")
    parser.add_argument("--sell-fee-rate", type=dec, default=Decimal("0"))
    parser.add_argument("--fixed-buy-fee", type=dec, default=Decimal("0"))
    parser.add_argument("--fixed-roundtrip-fee", type=dec, default=Decimal("0"))
    parser.add_argument("--scenarios", default="-30,-10,10,30", help="comma-separated percentage moves")
    args = parser.parse_args()

    if min(args.budget, args.entry, args.max_loss, args.lot_size) <= 0:
        raise SystemExit("budget, entry, max-loss and lot-size must be positive")
    if args.stop < 0 or args.stop >= args.entry:
        raise SystemExit("stop must be non-negative and below entry for a long cash position")

    unit_cash = args.entry * (Decimal("1") + args.buy_fee_rate)
    budget_room = args.budget - args.fixed_buy_fee
    q_budget = floor_lot(max(Decimal("0"), budget_room / unit_cash), args.lot_size)

    unit_loss = (args.entry - args.stop) + args.entry * args.buy_fee_rate + args.stop * args.sell_fee_rate
    loss_room = args.max_loss - args.fixed_roundtrip_fee
    q_risk = floor_lot(max(Decimal("0"), loss_room / unit_loss), args.lot_size)
    quantity = min(q_budget, q_risk)

    cash_used = quantity * unit_cash + (args.fixed_buy_fee if quantity else Decimal("0"))
    modeled_stop_loss = quantity * unit_loss + (args.fixed_roundtrip_fee if quantity else Decimal("0"))
    scenario_rows = []
    for raw in args.scenarios.split(","):
        pct = dec(raw.strip())
        exit_price = args.entry * (Decimal("1") + pct / Decimal("100"))
        pnl = quantity * (exit_price - args.entry)
        pnl -= quantity * (args.entry * args.buy_fee_rate + exit_price * args.sell_fee_rate)
        if quantity:
            pnl -= args.fixed_roundtrip_fee
        scenario_rows.append({"move_pct": str(pct), "exit_price": str(exit_price), "pnl_after_fees": str(pnl)})

    result = {
        "quantity": str(quantity),
        "budget_limited_quantity": str(q_budget),
        "risk_limited_quantity": str(q_risk),
        "cash_used": str(cash_used),
        "cash_remaining": str(args.budget - cash_used),
        "modeled_loss_at_stop": str(modeled_stop_loss),
        "risk_per_unit": str(unit_loss),
        "scenarios": scenario_rows,
        "warning": "Gap, liquidity and execution risk can make realized loss exceed the modeled stop loss.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
