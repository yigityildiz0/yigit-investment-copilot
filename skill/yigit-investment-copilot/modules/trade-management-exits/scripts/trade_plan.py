#!/usr/bin/env python3
"""Build a written long-trade plan for a BIST share: entry, stop, R, targets, size, trailing and
time rules, and gap risk. Standard library only; never places an order.

Stop logic: prefer a structure stop (just below the nearest swing support) when it sits between
1 and 3 ATR from entry; otherwise use an ATR stop. Size is the smaller of the risk-limited and
budget-limited quantity (lot = 1 share on BIST). Prices are rounded to BIST price steps.

Usage:
  python trade_plan.py --entry 290.75 --history THYAO.csv --capital 500000 --risk-pct 1 --horizon-days 30
  python trade_plan.py --entry 46.9 --atr 1.8 --stop 43.5 --targets 52 56 --capital 200000 --max-loss 2000
"""

import argparse
import json
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "technical-quant-analysis" / "scripts"))
sys.path.insert(0, str(HERE.parents[2] / "market-data-engine" / "scripts"))
try:
    from common import round_tick  # noqa: E402
except Exception:
    def round_tick(price, mode="nearest"):
        return round(price, 2)


def ta_levels(history):
    from technical_indicators import indicator_pack, load, pivots  # noqa: E402
    rows, _ = load(history, repair=True)
    pack = indicator_pack(rows)
    return pack, pivots(rows, pack.get("atr14"))



def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--history", type=Path, help="OHLCV CSV to derive ATR and swing levels")
    ap.add_argument("--atr", type=float)
    ap.add_argument("--stop", type=float, help="manual structure stop")
    ap.add_argument("--targets", nargs="*", type=float, default=[])
    ap.add_argument("--capital", type=float, required=True, help="total portfolio value in TL")
    ap.add_argument("--risk-pct", type=float, default=1.0, help="max loss per trade as %% of capital")
    ap.add_argument("--max-loss", type=float, help="override max loss in TL")
    ap.add_argument("--max-position-pct", type=float, default=20.0)
    ap.add_argument("--budget", type=float, help="cash available for this position")
    ap.add_argument("--atr-mult", type=float, default=2.0)
    ap.add_argument("--commission-rate", type=float, default=0.0015)
    ap.add_argument("--bsmv-rate", type=float, default=0.05)
    ap.add_argument("--horizon-days", type=int, default=30)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()

    pack, levels = ({}, [])
    if a.history:
        pack, levels = ta_levels(a.history)
    atr = a.atr or pack.get("atr14")
    if not atr:
        raise SystemExit("give --atr or --history")
    entry = round_tick(a.entry)
    fee = a.commission_rate * (1 + a.bsmv_rate)
    atr_stop = entry - a.atr_mult * atr
    supports = sorted([lv["level"] for lv in levels if lv["level"] < entry * 0.995], reverse=True)
    structure = a.stop if a.stop else (supports[0] - 0.5 * atr if supports else None)
    method = "ATR"
    stop = atr_stop
    if structure and atr <= entry - structure <= 3 * atr:
        stop, method = structure, "yapı (swing destek altı)" if not a.stop else "manuel yapı"
    stop = round_tick(max(stop, 0.01), "down")
    risk_share = entry - stop + fee * (entry + stop)
    warnings = []
    if (entry - stop) / entry > 0.15:
        warnings.append("Stop mesafesi %15'ten geniş: boyutu küçült ya da kurulumu atla.")
    if (entry - stop) < atr:
        warnings.append("Stop 1 ATR'den dar: normal gürültüyle tetiklenebilir.")
    max_loss = a.max_loss if a.max_loss else a.capital * a.risk_pct / 100
    budget = min(a.budget or a.capital, a.capital * a.max_position_pct / 100)
    q_risk = math.floor(max_loss / risk_share) if risk_share > 0 else 0
    q_budget = math.floor(budget / (entry * (1 + fee)))
    qty = max(0, min(q_risk, q_budget))
    R = entry - stop
    resist = sorted({round(x, 4) for x in a.targets} | {round(lv["level"], 4) for lv in levels if lv["level"] > entry * 1.005})
    targets = [{"level": round_tick(entry + m * R), "r_multiple": m, "basis": f"{m}R"} for m in (1.5, 2.0, 3.0)]
    targets += [{"level": round_tick(x), "r_multiple": round((x - entry) / R, 2), "basis": "direnç"} for x in resist[:3]]
    targets.sort(key=lambda t: t["level"])
    first_res = next((t for t in targets if t["basis"] == "direnç"), None)
    if first_res and first_res["r_multiple"] < 1.5:
        warnings.append(f"İlk direnç {first_res['level']} yalnız {first_res['r_multiple']}R uzakta: ödül/risk zayıf.")
    gap_price = round_tick(stop * 0.90, "down")
    time_stop_days = max(5, a.horizon_days // 3)
    first_take = next((t for t in targets if t["r_multiple"] >= 1.5), targets[-1])
    plan = {
        "entry": entry, "stop": stop, "stop_method": method, "atr14": atr, "R_per_share": round(R, 4),
        "risk_per_share_all_in": round(risk_share, 4),
        "quantity": qty, "binding_limit": "risk" if q_risk <= q_budget else "bütçe/konsantrasyon",
        "risk_limited_qty": q_risk, "budget_limited_qty": q_budget,
        "cash_used": round(qty * entry * (1 + fee), 2), "position_pct_of_capital": round(qty * entry / a.capital * 100, 2) if a.capital else None,
        "modeled_loss_at_stop": round(qty * risk_share, 2), "max_loss_budget": round(max_loss, 2),
        "gap_through_stop_loss": round(qty * (entry - gap_price + fee * (entry + gap_price)), 2),
        "gap_note": f"Stop, bir günlük -%10 limit boşlukla {gap_price} seviyesine kadar atlanabilir.",
        "targets": targets,
        "management": [
            f"Kapanış {round_tick(entry + R)} (+1R) üstünde gelirse stop'u başa-baş maliyete ({round_tick(entry * (1 + 2 * fee), 'up')}) çek.",
            f"{first_take['level']} ({first_take['r_multiple']}R) civarında pozisyonun 1/3'ünü, 3R ({round_tick(entry + 3 * R)}) civarında 1/3'ünü azalt; kalanı iz süren stop ile taşı.",
            f"İz süren stop: son 22 günün en yükseği − 3×ATR (chandelier) ya da 20 günlük EMA altında kapanış; hangisi yüksekse.",
            f"Zaman stopu: {time_stop_days} işlem günü içinde +0,5R ({round_tick(entry + 0.5 * R)}) görülmezse tezi yeniden değerlendir ya da çık.",
            "Bilanço/genel kurul/bedelsiz gibi olay öncesi: pozisyon boşluk riskine göre boyutlanmadıysa azalt.",
            "Tez bozulursa (KAP'ta olumsuz olay, sektör/makro kırılma) fiyat stop'u beklemeden çık.",
        ],
        "warnings": warnings,
        "disclaimer": "Plan bir araştırma çıktısıdır; emri kullanıcı kendi aracı kurumunda verir.",
    }
    if a.md:
        lines = [f"# İşlem planı — giriş {entry}", "",
                 f"- Stop {stop} ({method}) · R {plan['R_per_share']} TL/pay · ATR {atr:.2f}",
                 f"- Adet {qty} ({plan['binding_limit']} sınırı) · nakit {plan['cash_used']:,.0f} TL · sermayenin %{plan['position_pct_of_capital']}",
                 f"- Stop'ta modellenen zarar {plan['modeled_loss_at_stop']:,.0f} TL (bütçe {plan['max_loss_budget']:,.0f}) · -%10 boşluk senaryosu {plan['gap_through_stop_loss']:,.0f} TL",
                 "- Hedefler: " + ", ".join("{} ({}R, {})".format(t["level"], t["r_multiple"], t["basis"]) for t in targets), "",
                 "## Yönetim kuralları", "", *[f"- {m}" for m in plan["management"]]]
        if warnings:
            lines += ["", "## Uyarılar", "", *[f"- {w}" for w in warnings]]
        a.md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
