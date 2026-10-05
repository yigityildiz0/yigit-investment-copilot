#!/usr/bin/env python3
"""Indicative Black-Scholes metrics for a verified plain European warrant."""

import argparse
import json
import math


SQRT_TWO_PI = math.sqrt(2 * math.pi)


def normal_cdf(value):
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def normal_pdf(value):
    return math.exp(-0.5 * value * value) / SQRT_TWO_PI


def vanilla(option_type, spot, strike, years, rate, dividend, volatility):
    if years == 0:
        intrinsic = max(0.0, spot - strike) if option_type == "call" else max(0.0, strike - spot)
        delta = 1.0 if option_type == "call" and spot > strike else -1.0 if option_type == "put" and spot < strike else 0.0
        return {"value": intrinsic, "delta": delta, "gamma": None, "theta_per_day": None, "vega_per_vol_point": None}
    root_time = math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * volatility * volatility) * years) / (volatility * root_time)
    d2 = d1 - volatility * root_time
    discounted_spot = spot * math.exp(-dividend * years)
    discounted_strike = strike * math.exp(-rate * years)
    if option_type == "call":
        value = discounted_spot * normal_cdf(d1) - discounted_strike * normal_cdf(d2)
        delta = math.exp(-dividend * years) * normal_cdf(d1)
        theta_year = -(discounted_spot * normal_pdf(d1) * volatility) / (2 * root_time) - rate * discounted_strike * normal_cdf(d2) + dividend * discounted_spot * normal_cdf(d1)
    else:
        value = discounted_strike * normal_cdf(-d2) - discounted_spot * normal_cdf(-d1)
        delta = math.exp(-dividend * years) * (normal_cdf(d1) - 1)
        theta_year = -(discounted_spot * normal_pdf(d1) * volatility) / (2 * root_time) + rate * discounted_strike * normal_cdf(-d2) - dividend * discounted_spot * normal_cdf(-d1)
    gamma = math.exp(-dividend * years) * normal_pdf(d1) / (spot * volatility * root_time)
    vega_point = discounted_spot * normal_pdf(d1) * root_time * 0.01
    return {"value": value, "delta": delta, "gamma": gamma, "theta_per_day": theta_year / 365, "vega_per_vol_point": vega_point}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--option-type", choices=["call", "put"], required=True)
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument("--strike", type=float, required=True)
    parser.add_argument("--days-to-expiry", type=float, required=True)
    parser.add_argument("--volatility", type=float, required=True, help="annual decimal, e.g. 0.40")
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--dividend-yield", type=float, default=0.0)
    parser.add_argument("--underlying-units-per-warrant", type=float, required=True)
    parser.add_argument("--quoted-warrant-price", type=float)
    parser.add_argument("--scenario-spots", help="comma-separated underlying prices")
    parser.add_argument("--scenario-days-elapsed", type=float, default=0.0)
    args = parser.parse_args()
    if min(args.spot, args.strike, args.volatility, args.underlying_units_per_warrant) <= 0 or args.days_to_expiry < 0:
        raise SystemExit("spot, strike, volatility and units must be positive; days cannot be negative")
    if args.quoted_warrant_price is not None and args.quoted_warrant_price <= 0:
        raise SystemExit("quoted-warrant-price must be positive")
    if not 0 <= args.scenario_days_elapsed <= args.days_to_expiry:
        raise SystemExit("scenario-days-elapsed must be between zero and days-to-expiry")

    years = args.days_to_expiry / 365
    raw = vanilla(args.option_type, args.spot, args.strike, years, args.risk_free_rate, args.dividend_yield, args.volatility)
    ratio = args.underlying_units_per_warrant
    modeled = {key: value * ratio if value is not None else None for key, value in raw.items()}
    intrinsic_underlying = max(0.0, args.spot - args.strike) if args.option_type == "call" else max(0.0, args.strike - args.spot)
    intrinsic_warrant = intrinsic_underlying * ratio
    break_even = args.strike + args.quoted_warrant_price / ratio if args.option_type == "call" and args.quoted_warrant_price else args.strike - args.quoted_warrant_price / ratio if args.quoted_warrant_price else None
    effective_gearing = None
    if args.quoted_warrant_price:
        effective_gearing = modeled["delta"] * args.spot / args.quoted_warrant_price

    spots = [args.spot]
    if args.scenario_spots:
        spots = [float(value.strip()) for value in args.scenario_spots.split(",")]
        if any(value <= 0 for value in spots):
            raise SystemExit("scenario spots must be positive")
    scenario_years = (args.days_to_expiry - args.scenario_days_elapsed) / 365
    scenarios = []
    for spot in spots:
        current = vanilla(args.option_type, spot, args.strike, scenario_years, args.risk_free_rate, args.dividend_yield, args.volatility)
        expiry_intrinsic = (max(0.0, spot - args.strike) if args.option_type == "call" else max(0.0, args.strike - spot)) * ratio
        scenarios.append({
            "underlying": spot,
            "remaining_days": args.days_to_expiry - args.scenario_days_elapsed,
            "indicative_warrant_value": current["value"] * ratio,
            "expiry_intrinsic_if_underlying_unchanged": expiry_intrinsic,
        })

    result = {
        "model": "black_scholes_plain_european_indicative",
        "inputs": vars(args),
        "modeled_warrant_value": modeled["value"],
        "intrinsic_value_now": intrinsic_warrant,
        "time_value_using_quote": args.quoted_warrant_price - intrinsic_warrant if args.quoted_warrant_price else None,
        "expiry_break_even_underlying_using_quote": break_even,
        "delta_per_warrant": modeled["delta"],
        "gamma_per_warrant": modeled["gamma"],
        "theta_per_calendar_day_per_warrant": modeled["theta_per_day"],
        "vega_per_one_volatility_point_per_warrant": modeled["vega_per_vol_point"],
        "effective_gearing_using_quote": effective_gearing,
        "scenario_grid": scenarios,
        "warnings": [
            "Indicative vanilla model only; it is not an issuer quote or fair-value guarantee.",
            "Do not use for barriers, turbos, quanto, baskets, caps, calls, early exercise or another non-vanilla payoff.",
            "Verify the product document's conversion convention, dividends, rates, volatility, settlement, corporate actions, spread and market-maker terms.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
