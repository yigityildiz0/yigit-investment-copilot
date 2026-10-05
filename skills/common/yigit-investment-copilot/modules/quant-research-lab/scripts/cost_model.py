#!/usr/bin/env python3
"""Round-trip trading cost and capacity estimate for a BIST equity order (standard library only).

Components per side: broker commission, BSMV on commission, optional exchange/clearing fee,
half the bid-ask spread and square-root market impact:  impact = k * sigma_daily * sqrt(Q / ADV).
Rates change and differ by broker: pass your own. Defaults are placeholders, not current tariffs.

Usage:
  python cost_model.py --price 290.75 --order-try 250000 --adv-try 6.7e9 --daily-vol-pct 2.0 --commission-rate 0.0015
  python cost_model.py --price 12.4 --order-try 100000 --adv-try 1.5e7 --daily-vol-pct 4.5 --bid 12.38 --ask 12.42 --capacity
"""

import argparse
import json
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "market-data-engine" / "scripts"))
try:
    from common import bist_tick  # noqa: E402
except Exception:  # standalone copy without the engine
    def bist_tick(price):
        for upper, tick in ((20, 0.01), (50, 0.02), (100, 0.05), (250, 0.10), (500, 0.25), (1000, 0.50), (2500, 1.0)):
            if price < upper:
                return tick
        return 2.5


def side_cost(order, price, adv, sigma, a):
    commission = order * a.commission_rate
    bsmv = commission * a.bsmv_rate
    exchange = order * a.exchange_fee_rate
    if a.bid and a.ask and a.ask > a.bid:
        spread_pct = (a.ask - a.bid) / ((a.ask + a.bid) / 2)
    else:
        spread_pct = a.spread_ticks * bist_tick(price) / price
    half_spread = order * spread_pct / 2
    participation = order / adv if adv else None
    impact = order * a.impact_k * sigma * math.sqrt(participation) if participation else 0.0
    total = commission + bsmv + exchange + half_spread + impact
    return {"commission": commission, "bsmv": bsmv, "exchange_fee": exchange, "half_spread": half_spread,
            "impact": impact, "total_try": total, "total_pct": total / order * 100,
            "participation_of_adv_pct": participation * 100 if participation else None, "spread_pct": spread_pct * 100}



def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--order-try", type=float, required=True, help="order value in TL (one side)")
    ap.add_argument("--adv-try", type=float, help="average daily value traded in TL")
    ap.add_argument("--daily-vol-pct", type=float, default=2.5, help="daily volatility in percent")
    ap.add_argument("--commission-rate", type=float, default=0.0015, help="broker rate per side (placeholder)")
    ap.add_argument("--bsmv-rate", type=float, default=0.05, help="BSMV as a share of commission (verify)")
    ap.add_argument("--exchange-fee-rate", type=float, default=0.0, help="exchange/clearing pass-through if known")
    ap.add_argument("--bid", type=float)
    ap.add_argument("--ask", type=float)
    ap.add_argument("--spread-ticks", type=float, default=1.0, help="assumed spread in ticks when bid/ask unknown")
    ap.add_argument("--impact-k", type=float, default=0.7, help="square-root impact coefficient (0.5-1.0 typical)")
    ap.add_argument("--capacity", action="store_true", help="also print a cost table for larger order sizes")
    a = ap.parse_args()
    if a.price <= 0 or a.order_try <= 0:
        raise SystemExit("price and order must be positive")
    sigma = a.daily_vol_pct / 100
    one = side_cost(a.order_try, a.price, a.adv_try, sigma, a)
    result = {
        "inputs": {k: v for k, v in vars(a).items() if k != "capacity"},
        "per_side": one,
        "round_trip_pct": one["total_pct"] * 2,
        "round_trip_try": one["total_try"] * 2,
        "break_even_move_pct": one["total_pct"] * 2,
        "notes": ["BIST hisse alım-satım kazancında yerleşik gerçek kişi için stopaj oranı güncel mevzuattan doğrulanmalı (2026-09 itibarıyla %0).",
                  "Temettü stopajı ayrı konudur (22.12.2024'ten beri %15; doğrula).",
                  "Etki modeli kaba bir tahmindir; ince tahtada gerçek kayma çok daha büyük olabilir."],
    }
    if a.capacity and a.adv_try:
        table = []
        for mult in (0.1, 0.25, 0.5, 1, 2, 5, 10, 20):
            order = a.order_try * mult
            c = side_cost(order, a.price, a.adv_try, sigma, a)
            table.append({"order_try": order, "adv_pct": c["participation_of_adv_pct"], "round_trip_pct": c["total_pct"] * 2})
        result["capacity"] = table
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
