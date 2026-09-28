#!/usr/bin/env python3
"""Transparent valuation models for equity research (Python 3.9+, standard library only).

Subcommands (rates and growth in percent, money in any single currency and unit):
  coe          cost of equity: USD CAPM + country risk, converted to TRY with the Fisher relation
  dcf          FCFF/FCFE discounted cash flow with named scenarios and a WACC x terminal-growth grid
  reverse-dcf  growth the current price implies over N years ("what is priced in?")
  pb-roe       justified P/B = (ROE - g) / (COE - g) and the ROE the market price implies
  rim          residual-income value (book value + PV of ROE - COE spread): banks and insurers
  ddm          one- or two-stage dividend discount model

Currency and inflation discipline: discount nominal TRY flows with a nominal TRY rate, real flows
with a real rate. Companies reporting under TMS 29 publish inflation-adjusted equity, so pair their
ROE with a REAL cost of equity; banks (no TMS 29) pair nominal ROE with a nominal rate.

Examples:
  python valuation_models.py coe --rf-usd 4.2 --erp 5.0 --crp 3.5 --beta 1.1 --infl-try 25 --infl-usd 2.5
  python valuation_models.py dcf --cash0 1200 --growth 35,30,25,20,18 --terminal-growth 15 --rate 32 \\
      --net-debt 800 --shares 250 --scenario bear:20,15,12,10,10:0.25 --scenario bull:45,40,30,25,20:0.25 --grid
  python valuation_models.py reverse-dcf --price 48 --shares 250 --net-debt 800 --cash0 1200 --rate 32 --terminal-growth 15
  python valuation_models.py pb-roe --roe 28 --coe 34 --growth 22 --bvps 40 --price 52
  python valuation_models.py rim --bvps 40 --roe 32,30,28,26,24 --coe 34 --terminal-growth 20 --price 52
  python valuation_models.py ddm --dps 3.2 --coe 34 --growth 30 --years 5 --terminal-growth 20 --price 70
"""

import argparse
import json
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from pathlib import Path


def pct(x):
    return x / 100.0


def fisher(rate_a, infl_a, infl_b):
    """Convert a nominal rate from currency A to currency B: (1+r_a)(1+pi_b)/(1+pi_a) - 1."""
    return (1 + rate_a) * (1 + infl_b) / (1 + infl_a) - 1


def check_spread(rate, growth, label):
    if growth >= rate:
        raise SystemExit(f"{label}: terminal growth ({growth*100:.2f}%) must be below the discount rate ({rate*100:.2f}%)")


def dcf_value(cash0, growth_path, terminal_growth, rate, net_debt=0.0, shares=1.0, mid_year=False):
    flows, pv, cash = [], 0.0, cash0
    for t, g in enumerate(growth_path, start=1):
        cash *= 1 + g
        factor = (1 + rate) ** (t - 0.5 if mid_year else t)
        flows.append({"year": t, "growth_pct": g * 100, "cash": cash, "pv": cash / factor})
        pv += cash / factor
    check_spread(rate, terminal_growth, "dcf")
    n = len(growth_path)
    tv = cash * (1 + terminal_growth) / (rate - terminal_growth)
    pv_tv = tv / (1 + rate) ** (n - 0.5 if mid_year else n)
    ev = pv + pv_tv
    equity = ev - net_debt
    return {"enterprise_value": ev, "equity_value": equity, "per_share": equity / shares if shares else None,
            "pv_explicit": pv, "pv_terminal": pv_tv, "terminal_share_pct": pv_tv / ev * 100 if ev else None,
            "flows": flows}


def parse_path(text):
    return [pct(float(x)) for x in text.split(",") if x.strip()]


def cmd_coe(a):
    ke_usd = pct(a.rf_usd) + a.beta * pct(a.erp) + a.crp_lambda * pct(a.crp)
    out = {"model": "CAPM + country risk premium (USD), Fisher-converted to TRY",
           "inputs": vars(a), "coe_usd_pct": ke_usd * 100}
    if a.infl_try is not None:
        ke_try = fisher(ke_usd, pct(a.infl_usd), pct(a.infl_try))
        out["coe_try_nominal_pct"] = ke_try * 100
        out["coe_real_pct"] = ((1 + ke_usd) / (1 + pct(a.infl_usd)) - 1) * 100
        out["note"] = ("TRY nominal = (1+Ke_USD)(1+pi_TRY)/(1+pi_USD)-1. Use expected (forward) inflation, not the "
                       "trailing print; cross-check with the TRY government bond curve plus an equity premium.")
    if a.local_rf is not None:
        out["cross_check_try_bond_plus_erp_pct"] = (pct(a.local_rf) + a.beta * pct(a.erp)) * 100
    return out


def cmd_dcf(a):
    base = {"name": "base", "path": parse_path(a.growth), "prob": None}
    scenarios = [base]
    for spec in a.scenario or []:
        parts = spec.split(":")
        if len(parts) < 2:
            raise SystemExit("--scenario name:g1,g2,...[:probability]")
        scenarios.append({"name": parts[0], "path": parse_path(parts[1]), "prob": float(parts[2]) if len(parts) > 2 else None})
    given = sum(s["prob"] or 0 for s in scenarios)
    missing = [s for s in scenarios if s["prob"] is None]
    for s in missing:
        s["prob"] = max(0.0, 1 - given) / len(missing) if missing else 0
    rate, tg = pct(a.rate), pct(a.terminal_growth)
    results = []
    for s in scenarios:
        v = dcf_value(a.cash0, s["path"], tg, rate, a.net_debt, a.shares, a.mid_year)
        results.append({"scenario": s["name"], "probability": s["prob"], **{k: v[k] for k in v if k != "flows"},
                        "flows": v["flows"]})
    weighted = sum(r["per_share"] * r["probability"] for r in results if r["per_share"] is not None)
    out = {"model": f"DCF ({a.kind}), {'mid-year' if a.mid_year else 'end-year'} discounting",
           "rate_pct": a.rate, "terminal_growth_pct": a.terminal_growth, "scenarios": results,
           "probability_weighted_per_share": weighted}
    if a.price:
        out["price"] = a.price
        out["upside_to_weighted_pct"] = (weighted / a.price - 1) * 100
    if a.grid:
        rates = [a.rate + d for d in (-4, -2, 0, 2, 4)]
        growths = [a.terminal_growth + d for d in (-3, -1.5, 0, 1.5, 3)]
        grid = []
        for r in rates:
            row = {"rate_pct": r}
            for g in growths:
                row[f"g={g:g}"] = (dcf_value(a.cash0, base["path"], pct(g), pct(r), a.net_debt, a.shares, a.mid_year)["per_share"]
                                   if g < r else None)
            grid.append(row)
        out["sensitivity_per_share"] = grid
    return out


def cmd_reverse(a):
    target_ev = a.price * a.shares + a.net_debt
    rate, tg = pct(a.rate), pct(a.terminal_growth)
    check_spread(rate, tg, "reverse-dcf")

    def ev_at(g):
        return dcf_value(a.cash0, [g] * a.years, tg, rate, 0.0, 1.0, a.mid_year)["enterprise_value"]

    lo, hi = -0.9, 5.0
    if a.cash0 <= 0:
        raise SystemExit("reverse-dcf needs a positive starting cash flow; use pb-roe or rim for loss-makers and banks")
    if ev_at(lo) > target_ev:
        implied = None
        note = "even a -90%/yr path is worth more than the price: price implies collapse or the cash flow base is wrong"
    elif ev_at(hi) < target_ev:
        implied = None
        note = "no growth below 500%/yr justifies the price with these inputs"
    else:
        for _ in range(200):
            mid = (lo + hi) / 2
            if ev_at(mid) < target_ev:
                lo = mid
            else:
                hi = mid
        implied = (lo + hi) / 2
        note = "constant annual growth over the explicit years that makes the DCF equal to today's price"
    out = {"model": "reverse DCF", "price": a.price, "enterprise_value_at_price": target_ev,
           "years": a.years, "rate_pct": a.rate, "terminal_growth_pct": a.terminal_growth,
           "implied_growth_pct": implied * 100 if implied is not None else None, "note": note}
    if implied is not None and a.infl is not None:
        out["implied_real_growth_pct"] = ((1 + implied) / (1 + pct(a.infl)) - 1) * 100
    no_growth = dcf_value(a.cash0, [0.0] * a.years, tg, rate, a.net_debt, a.shares, a.mid_year)["per_share"]
    out["value_per_share_with_zero_explicit_growth"] = no_growth
    return out


def cmd_pbroe(a):
    roe, coe, g = pct(a.roe), pct(a.coe), pct(a.growth)
    check_spread(coe, g, "pb-roe")
    justified = (roe - g) / (coe - g)
    out = {"model": "justified P/B = (ROE - g) / (COE - g)", "roe_pct": a.roe, "coe_pct": a.coe, "growth_pct": a.growth,
           "justified_pb": justified}
    if a.bvps:
        out["justified_price"] = justified * a.bvps
        if a.price:
            market_pb = a.price / a.bvps
            out["market_pb"] = market_pb
            out["implied_sustainable_roe_pct"] = (g + market_pb * (coe - g)) * 100
            out["upside_pct"] = (out["justified_price"] / a.price - 1) * 100
    out["note"] = "ROE must be sustainable and on the same (real or nominal) basis as COE and g."
    return out


def cmd_rim(a):
    roes, coe, tg = parse_path(a.roe), pct(a.coe), pct(a.terminal_growth)
    check_spread(coe, tg, "rim")
    bv, pv, rows = a.bvps, 0.0, []
    for t, roe in enumerate(roes, start=1):
        ri = (roe - coe) * bv
        pv += ri / (1 + coe) ** t
        rows.append({"year": t, "book_start": bv, "roe_pct": roe * 100, "residual_income": ri, "pv": ri / (1 + coe) ** t})
        bv *= 1 + roe * (1 - a.payout / 100)
    last_ri = (roes[-1] - coe) * bv
    pv_tv = last_ri * (1 + tg) / (coe - tg) / (1 + coe) ** len(roes) if a.persist else 0.0
    value = a.bvps + pv + pv_tv
    out = {"model": "residual income", "value_per_share": value, "book_value": a.bvps, "pv_residual_income": pv,
           "pv_terminal": pv_tv, "terminal": "persisting spread" if a.persist else "spread fades to zero after the explicit years",
           "rows": rows}
    if a.price:
        out["upside_pct"] = (value / a.price - 1) * 100
    return out


def cmd_ddm(a):
    coe, g, tg = pct(a.coe), pct(a.growth), pct(a.terminal_growth if a.terminal_growth is not None else a.growth)
    check_spread(coe, tg, "ddm")
    pv, d, rows = 0.0, a.dps, []
    years = a.years if a.terminal_growth is not None else 0
    for t in range(1, years + 1):
        d *= 1 + g
        pv += d / (1 + coe) ** t
        rows.append({"year": t, "dividend": d})
    tv = d * (1 + tg) / (coe - tg) / (1 + coe) ** years
    value = pv + tv
    out = {"model": "two-stage DDM" if years else "Gordon growth DDM", "value_per_share": value, "pv_stage1": pv,
           "pv_terminal": tv, "rows": rows, "note": "Dividends in Türkiye carry 15% withholding for individuals since 22.12.2024; value is pre-tax."}
    if a.price:
        out["upside_pct"] = (value / a.price - 1) * 100
        out["implied_growth_single_stage_pct"] = ((a.price * coe - a.dps) / (a.price + a.dps)) * 100
    return out


def to_md(res):
    lines = [f"# Değerleme — {res.get('model')}", ""]
    for k, v in res.items():
        if k in ("model", "flows", "rows", "scenarios", "sensitivity_per_share", "inputs"):
            continue
        lines.append(f"- {k}: {v:,.4g}" if isinstance(v, float) else f"- {k}: {v}")
    if res.get("scenarios"):
        lines += ["", "| Senaryo | Olasılık | Hisse başı değer | Terminal payı % |", "|---|---|---|---|"]
        for s in res["scenarios"]:
            lines.append(f"| {s['scenario']} | {s['probability']:.2f} | {s['per_share']:,.2f} | {s['terminal_share_pct']:.0f} |")
    if res.get("sensitivity_per_share"):
        keys = [k for k in res["sensitivity_per_share"][0] if k != "rate_pct"]
        lines += ["", "Duyarlılık (satır: iskonto %, sütun: uç büyüme %)", "", "| iskonto | " + " | ".join(keys) + " |",
                  "|---|" + "|".join("---" for _ in keys) + "|"]
        for row in res["sensitivity_per_share"]:
            lines.append(f"| {row['rate_pct']:g} | " + " | ".join("—" if row[k] is None else f"{row[k]:,.2f}" for k in keys) + " |")
    lines += ["", "> Model çıktısıdır (etiket: MODEL ÇIKTISI). Girdiler varsayımdır; değer aralığını ve varsayımı değiştiren kanıtı yaz."]
    return "\n".join(lines)


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", type=Path, help="also write a Turkish Markdown summary")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coe")
    c.add_argument("--rf-usd", type=float, required=True, help="US 10y yield %%")
    c.add_argument("--erp", type=float, default=5.0, help="mature-market equity risk premium %%")
    c.add_argument("--crp", type=float, default=0.0, help="country risk premium %% (e.g. CDS spread x equity/bond vol ratio)")
    c.add_argument("--crp-lambda", type=float, default=1.0, help="company exposure to country risk (1 = average)")
    c.add_argument("--beta", type=float, default=1.0)
    c.add_argument("--infl-try", type=float, help="expected TRY inflation %%")
    c.add_argument("--infl-usd", type=float, default=2.5, help="expected USD inflation %%")
    c.add_argument("--local-rf", type=float, help="TRY government bond yield %% for a cross-check")
    d = sub.add_parser("dcf")
    d.add_argument("--cash0", type=float, required=True, help="last 12-month free cash flow (FCFF with --net-debt, or FCFE with --net-debt 0)")
    d.add_argument("--growth", required=True, help="comma list of yearly growth %% for the base path")
    d.add_argument("--terminal-growth", type=float, required=True)
    d.add_argument("--rate", type=float, required=True, help="WACC (FCFF) or cost of equity (FCFE) %%")
    d.add_argument("--net-debt", type=float, default=0.0)
    d.add_argument("--shares", type=float, default=1.0)
    d.add_argument("--price", type=float)
    d.add_argument("--kind", default="FCFF", choices=["FCFF", "FCFE"])
    d.add_argument("--mid-year", action="store_true")
    d.add_argument("--scenario", action="append", help="name:g1,g2,...:probability (repeatable)")
    d.add_argument("--grid", action="store_true")
    r = sub.add_parser("reverse-dcf")
    for name in ("price", "shares", "cash0", "rate", "terminal-growth"):
        r.add_argument(f"--{name}", type=float, required=True)
    r.add_argument("--net-debt", type=float, default=0.0)
    r.add_argument("--years", type=int, default=10)
    r.add_argument("--infl", type=float, help="expected inflation %% to express the implied growth in real terms")
    r.add_argument("--mid-year", action="store_true")
    p = sub.add_parser("pb-roe")
    p.add_argument("--roe", type=float, required=True)
    p.add_argument("--coe", type=float, required=True)
    p.add_argument("--growth", type=float, required=True)
    p.add_argument("--bvps", type=float)
    p.add_argument("--price", type=float)
    m = sub.add_parser("rim")
    m.add_argument("--bvps", type=float, required=True)
    m.add_argument("--roe", required=True, help="comma list of yearly ROE %%")
    m.add_argument("--coe", type=float, required=True)
    m.add_argument("--terminal-growth", type=float, default=0.0)
    m.add_argument("--payout", type=float, default=30.0, help="dividend payout %% (book grows by retained earnings)")
    m.add_argument("--persist", action="store_true", help="keep the last ROE-COE spread forever (default: fade to zero)")
    m.add_argument("--price", type=float)
    g = sub.add_parser("ddm")
    g.add_argument("--dps", type=float, required=True, help="last annual dividend per share")
    g.add_argument("--coe", type=float, required=True)
    g.add_argument("--growth", type=float, required=True, help="stage-1 growth %% (or perpetual growth without --terminal-growth)")
    g.add_argument("--years", type=int, default=5)
    g.add_argument("--terminal-growth", type=float)
    g.add_argument("--price", type=float)
    a = ap.parse_args()
    handler = {"coe": cmd_coe, "dcf": cmd_dcf, "reverse-dcf": cmd_reverse, "pb-roe": cmd_pbroe, "rim": cmd_rim, "ddm": cmd_ddm}[a.cmd]
    result = handler(a)
    result.pop("inputs", None) if a.cmd != "coe" else None
    if a.cmd == "coe":
        result["inputs"] = {k: v for k, v in result["inputs"].items() if k not in ("cmd", "md")}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if a.md:
        a.md.write_text(to_md(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
