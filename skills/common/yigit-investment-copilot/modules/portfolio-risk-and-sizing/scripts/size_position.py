#!/usr/bin/env python3
"""Calculate budget-, loss-, and concentration-limited position size."""

import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_FLOOR


def decimal_value(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"invalid decimal: {value}") from exc


def floor_lot(value: Decimal, lot: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")
    return (value / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--available-cash", type=decimal_value, required=True)
    parser.add_argument(
        "--unit-cash-cost",
        type=decimal_value,
        required=True,
        help="all-in variable cash used per unit at entry",
    )
    parser.add_argument(
        "--unit-loss-at-invalidation",
        type=decimal_value,
        required=True,
        help="all-in variable modeled loss per unit",
    )
    parser.add_argument("--max-loss", type=decimal_value, required=True)
    parser.add_argument("--lot-size", type=decimal_value, default=Decimal("1"))
    parser.add_argument("--fixed-entry-cost", type=decimal_value, default=Decimal("0"))
    parser.add_argument("--fixed-roundtrip-cost", type=decimal_value, default=Decimal("0"))
    parser.add_argument("--portfolio-value", type=decimal_value)
    parser.add_argument("--max-position-pct", type=decimal_value, help="decimal, e.g. 0.10")
    parser.add_argument("--existing-position-value", type=decimal_value, default=Decimal("0"))
    parser.add_argument("--unit-position-value", type=decimal_value)
    parser.add_argument("--unit-gross-notional", type=decimal_value)
    parser.add_argument("--unit-worst-case-loss", type=decimal_value)
    parser.add_argument(
        "--product-type",
        choices=["cash-long", "fund", "long-premium", "futures", "short", "written-option", "other"],
        default="other",
    )
    parser.add_argument("--currency", default="TRY")
    args = parser.parse_args()

    positive = [args.available_cash, args.unit_cash_cost, args.unit_loss_at_invalidation, args.max_loss, args.lot_size]
    if min(positive) <= 0:
        raise SystemExit("cash, unit costs, max-loss and lot-size must be positive")
    if min(args.fixed_entry_cost, args.fixed_roundtrip_cost, args.existing_position_value) < 0:
        raise SystemExit("fixed costs and existing position value cannot be negative")
    if (args.portfolio_value is None) != (args.max_position_pct is None):
        raise SystemExit("portfolio-value and max-position-pct must be provided together")
    if args.max_position_pct is not None and not Decimal("0") < args.max_position_pct <= Decimal("1"):
        raise SystemExit("max-position-pct must be in (0, 1]")

    budget_room = max(Decimal("0"), args.available_cash - args.fixed_entry_cost)
    loss_room = max(Decimal("0"), args.max_loss - args.fixed_roundtrip_cost)
    limits = {
        "budget": floor_lot(budget_room / args.unit_cash_cost, args.lot_size),
        "loss": floor_lot(loss_room / args.unit_loss_at_invalidation, args.lot_size),
    }

    unit_position_value = args.unit_position_value or args.unit_cash_cost
    if unit_position_value <= 0:
        raise SystemExit("unit-position-value must be positive")
    if args.portfolio_value is not None:
        if args.portfolio_value <= 0:
            raise SystemExit("portfolio-value must be positive")
        cap_value = args.portfolio_value * args.max_position_pct
        cap_room = max(Decimal("0"), cap_value - args.existing_position_value)
        limits["concentration"] = floor_lot(cap_room / unit_position_value, args.lot_size)

    quantity = min(limits.values())
    binding = sorted(name for name, value in limits.items() if value == quantity)
    entry_fixed = args.fixed_entry_cost if quantity > 0 else Decimal("0")
    roundtrip_fixed = args.fixed_roundtrip_cost if quantity > 0 else Decimal("0")
    cash_used = quantity * args.unit_cash_cost + entry_fixed
    modeled_loss = quantity * args.unit_loss_at_invalidation + roundtrip_fixed
    position_value = args.existing_position_value + quantity * unit_position_value

    warnings = [
        "The invalidation loss is modeled, not guaranteed; gaps, liquidity and execution can increase realized loss."
    ]
    if args.product_type in {"futures", "short", "written-option"}:
        warnings.append("Margin or collateral is not maximum loss; loss may exceed entry cash and stated margin.")
    if args.product_type == "long-premium":
        warnings.append("Use the full all-in premium as unit loss when a stop cannot reliably cap loss.")
    if args.unit_worst_case_loss is None:
        warnings.append("Credible worst-case loss was not supplied and remains unresolved.")

    result = {
        "currency": args.currency,
        "product_type": args.product_type,
        "quantity": str(quantity),
        "binding_constraints": binding,
        "quantity_limits": {name: str(value) for name, value in limits.items()},
        "cash_used": str(cash_used),
        "cash_remaining": str(args.available_cash - cash_used),
        "modeled_loss_at_invalidation": str(modeled_loss),
        "credible_worst_case_loss": (
            str(quantity * args.unit_worst_case_loss + roundtrip_fixed)
            if args.unit_worst_case_loss is not None
            else None
        ),
        "post_trade_position_value": str(position_value),
        "post_trade_position_pct": (
            str(position_value / args.portfolio_value) if args.portfolio_value else None
        ),
        "gross_notional_added": (
            str(quantity * args.unit_gross_notional) if args.unit_gross_notional is not None else None
        ),
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
