#!/usr/bin/env python3
"""Transparent personal-finance calculations using explicit assumptions."""

import argparse
import json


def compound(args):
    periods = int(round(args.years * args.periods_per_year))
    if periods < 0:
        raise SystemExit("years cannot be negative")
    rate = (1 + args.annual_return) ** (1 / args.periods_per_year) - 1
    balance = args.principal
    contributions = 0.0
    for _ in range(periods):
        balance *= 1 + rate
        balance += args.contribution_per_period
        contributions += args.contribution_per_period
    return {"future_value": balance, "principal": args.principal, "contributions": contributions, "investment_gain": balance - args.principal - contributions}


def real_return(args):
    return {"real_return": (1 + args.nominal_return) / (1 + args.inflation) - 1}


def fee_drag(args):
    gross = args.principal * (1 + args.gross_annual_return) ** args.years
    net_rate = (1 + args.gross_annual_return) * (1 - args.annual_fee) - 1
    net = args.principal * (1 + net_rate) ** args.years
    return {"gross_value": gross, "net_value_after_annual_fee": net, "fee_drag_value": gross - net, "modeled_net_annual_rate": net_rate}


def loan(args):
    monthly_rate = args.annual_rate / 12
    if args.months <= 0:
        raise SystemExit("months must be positive")
    payment = args.principal / args.months if monthly_rate == 0 else args.principal * monthly_rate / (1 - (1 + monthly_rate) ** -args.months)
    total = payment * args.months + args.upfront_fees
    return {"monthly_payment": payment, "total_payments_and_fees": total, "total_financing_cost": total - args.principal, "rate_assumption": "annual_rate is a nominal annual rate divided by 12; this is not an APR/EIR calculation"}


def required_return(args):
    if min(args.start, args.target, args.years) <= 0:
        raise SystemExit("start, target and years must be positive")
    return {"required_annual_return": (args.target / args.start) ** (1 / args.years) - 1}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    comp = sub.add_parser("compound")
    comp.add_argument("--principal", type=float, required=True)
    comp.add_argument("--annual-return", type=float, required=True)
    comp.add_argument("--years", type=float, required=True)
    comp.add_argument("--contribution-per-period", type=float, default=0.0)
    comp.add_argument("--periods-per-year", type=int, default=12)
    real = sub.add_parser("real-return")
    real.add_argument("--nominal-return", type=float, required=True)
    real.add_argument("--inflation", type=float, required=True)
    fee = sub.add_parser("fee-drag")
    fee.add_argument("--principal", type=float, required=True)
    fee.add_argument("--gross-annual-return", type=float, required=True)
    fee.add_argument("--annual-fee", type=float, required=True)
    fee.add_argument("--years", type=float, required=True)
    credit = sub.add_parser("loan")
    credit.add_argument("--principal", type=float, required=True)
    credit.add_argument("--annual-rate", type=float, required=True)
    credit.add_argument("--months", type=int, required=True)
    credit.add_argument("--upfront-fees", type=float, default=0.0)
    required = sub.add_parser("required-return")
    required.add_argument("--start", type=float, required=True)
    required.add_argument("--target", type=float, required=True)
    required.add_argument("--years", type=float, required=True)
    args = parser.parse_args()

    if args.mode == "compound":
        if min(args.principal, args.years, args.contribution_per_period) < 0 or args.periods_per_year <= 0 or args.annual_return <= -1:
            raise SystemExit("compound inputs must be non-negative, periods positive, and annual return greater than -100%")
    elif args.mode == "real-return":
        if args.nominal_return <= -1 or args.inflation <= -1:
            raise SystemExit("nominal return and inflation must be greater than -100%")
    elif args.mode == "fee-drag":
        if min(args.principal, args.years, args.annual_fee) < 0 or args.annual_fee >= 1 or args.gross_annual_return <= -1:
            raise SystemExit("fee-drag inputs must be valid and annual fee below 100%")
    elif args.mode == "loan":
        if min(args.principal, args.annual_rate, args.upfront_fees) < 0:
            raise SystemExit("loan principal, rate and fees cannot be negative")

    functions = {"compound": compound, "real-return": real_return, "fee-drag": fee_drag, "loan": loan, "required-return": required_return}
    result = {"mode": args.mode, "inputs": vars(args), "result": functions[args.mode](args), "assumptions": "Contributions occur at period end; returns are constant; tax, spread, timing variation and product rules are excluded unless explicitly supplied.", "boundary": "Deterministic math only; verify tax, fees, timing, rates and product rules separately."}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
