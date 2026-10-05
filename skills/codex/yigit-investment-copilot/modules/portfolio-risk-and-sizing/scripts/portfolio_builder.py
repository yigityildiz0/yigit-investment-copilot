#!/usr/bin/env python3
"""Risk-based portfolio construction and portfolio-level risk report (research tool; never trades).

Allocates a cash budget across candidate stocks with equal-risk-contribution (risk parity),
inverse-volatility or equal weights, applies per-name and per-sector caps, rounds to whole shares
(BIST lot = 1 share), and reports the combined portfolio (existing holdings + new positions):
volatility, risk contributions, correlations, diversification ratio, historical VaR/ES, worst
20-day loss, beta to the benchmark, sector exposure and open "heat" (loss to stops).

Inputs are price_history.py CSVs (date, close, adj_close, ...). Covariance uses daily log returns
over the lookback, shrunk toward a constant-correlation target for stability.

Usage:
  python portfolio_builder.py --history-dir hist --candidates THYAO ASELS BIMAS TUPRS --budget 250000 --out pf
  python portfolio_builder.py --history-dir hist --holdings holdings.csv --candidates EREGL KCHOL \\
      --budget 100000 --method erc --max-weight 0.20 --max-sector 0.35 --snapshot snap/snapshot.csv \\
      --stops THYAO=280,EREGL=24.5 --benchmark hist/XU100.csv --out pf

holdings.csv columns: code,quantity[,avg_cost][,stop]
"""

import argparse
import csv
import json
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRT = timezone(timedelta(hours=3))


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load(path):
    out = []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            if str(r.get("complete", "1")).strip() in {"0", "false", "False"}:
                continue
            try:
                adj = float(r.get("adj_close") or r.get("close"))
                close = float(r.get("close") or adj)
            except (TypeError, ValueError):
                continue
            if adj > 0 and close > 0:
                out.append((r["date"][:10], adj, close))
    out.sort()
    return out


def mat_vec(m, v):
    return [sum(a * b for a, b in zip(row, v)) for row in m]


def port_var(w, cov):
    return sum(wi * x for wi, x in zip(w, mat_vec(cov, w)))


def covariance(returns, shrink):
    n, t = len(returns), len(returns[0])
    means = [sum(r) / t for r in returns]
    cov = [[sum((returns[i][k] - means[i]) * (returns[j][k] - means[j]) for k in range(t)) / (t - 1) for j in range(n)] for i in range(n)]
    sd = [math.sqrt(cov[i][i]) for i in range(n)]
    corrs = [cov[i][j] / (sd[i] * sd[j]) for i in range(n) for j in range(n) if i < j and sd[i] and sd[j]]
    avg_corr = sum(corrs) / len(corrs) if corrs else 0.0
    shrunk = [[cov[i][j] if i == j else (1 - shrink) * cov[i][j] + shrink * avg_corr * sd[i] * sd[j] for j in range(n)] for i in range(n)]
    return shrunk, sd, avg_corr


def erc_weights(cov, iters=2000):
    n = len(cov)
    w = [1 / math.sqrt(cov[i][i]) if cov[i][i] > 0 else 0 for i in range(n)]
    s = sum(w)
    w = [x / s for x in w]
    for _ in range(iters):
        mv = mat_vec(cov, w)
        rc = [w[i] * mv[i] for i in range(n)]
        total = sum(rc)
        if total <= 0:
            break
        target = total / n
        w = [w[i] * math.sqrt(target / rc[i]) if rc[i] > 0 else w[i] for i in range(n)]
        s = sum(w)
        w = [x / s for x in w]
    return w


def apply_caps(w, cap, sectors=None, sector_cap=None, rounds=100):
    """Clip names at `cap` and sectors at `sector_cap`, redistributing to names with room.
    Weight that cannot be placed stays in cash (weights may sum to < 1)."""
    w = list(w)
    for _ in range(rounds):
        changed = False
        if sectors and sector_cap:
            totals = {}
            for i, s in enumerate(sectors):
                totals[s] = totals.get(s, 0.0) + w[i]
            for s, tot in totals.items():
                if tot > sector_cap + 1e-12:
                    scale = sector_cap / tot
                    for i, si in enumerate(sectors):
                        if si == s:
                            w[i] *= scale
                    changed = True
        over = [i for i, x in enumerate(w) if x > cap + 1e-12]
        for i in over:
            w[i] = cap
            changed = True
        free = 1.0 - sum(w)
        if free > 1e-9:
            room = []
            for i, x in enumerate(w):
                r = cap - x
                if sectors and sector_cap:
                    used = sum(w[j] for j, s in enumerate(sectors) if s == sectors[i])
                    r = min(r, sector_cap - used)
                room.append(max(0.0, r))
            total_room = sum(room)
            if total_room > 1e-9:
                base = [w[i] if room[i] > 0 else 0.0 for i in range(len(w))]
                bsum = sum(base) or 1.0
                for i in range(len(w)):
                    if room[i] > 0:
                        w[i] += min(room[i], free * (base[i] / bsum if sum(base) else room[i] / total_room))
                changed = True
        if not changed:
            break
    return w


def quantile(values, q):
    s = sorted(values)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history-dir", type=Path, required=True)
    ap.add_argument("--candidates", nargs="*", default=[])
    ap.add_argument("--holdings", type=Path, help="CSV code,quantity[,avg_cost][,stop]")
    ap.add_argument("--budget", type=float, default=0.0, help="new cash to allocate across candidates")
    ap.add_argument("--method", choices=["erc", "invvol", "equal"], default="erc")
    ap.add_argument("--max-weight", type=float, default=0.20, help="cap per name as a share of the new budget")
    ap.add_argument("--max-sector", type=float, help="cap per sector (needs --snapshot)")
    ap.add_argument("--snapshot", type=Path, help="snapshot.csv for sector labels")
    ap.add_argument("--stops", help="CODE=price,CODE=price for heat (loss to stops)")
    ap.add_argument("--benchmark", type=Path, help="benchmark CSV (e.g. XU100.csv) for beta")
    ap.add_argument("--lookback", type=int, default=252)
    ap.add_argument("--shrink", type=float, default=0.25, help="shrink correlations toward their average (0..1)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    holdings = {}
    if a.holdings and a.holdings.exists():
        with open(a.holdings, encoding="utf-8-sig", newline="") as handle:
            for r in csv.DictReader(handle):
                code = (r.get("code") or r.get("kod") or "").strip().upper()
                if code:
                    holdings[code] = {"quantity": float(r.get("quantity") or r.get("adet") or 0),
                                      "avg_cost": float(r["avg_cost"]) if r.get("avg_cost") else None,
                                      "stop": float(r["stop"]) if r.get("stop") else None}
    stops = {k: v["stop"] for k, v in holdings.items() if v.get("stop")}
    for part in (a.stops or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            stops[k.strip().upper()] = float(v)
    cands = [c.upper() for c in a.candidates if c.upper() not in holdings or a.budget > 0]
    codes = list(dict.fromkeys(list(holdings) + cands))
    series, missing = {}, []
    for c in codes:
        p = a.history_dir / f"{c}.csv"
        if p.exists():
            series[c] = load(p)
        else:
            missing.append(c)
    codes = [c for c in codes if c in series and len(series[c]) > 60]
    if not codes:
        raise SystemExit("no usable price histories; run price_history.py for the codes first")
    common = sorted(set.intersection(*[set(d for d, _, _ in series[c]) for c in codes]))[-(a.lookback + 1):]
    if len(common) < 60:
        raise SystemExit(f"only {len(common)} common dates; use longer or aligned histories")
    maps = {c: {d: (adj, close) for d, adj, close in series[c]} for c in codes}
    rets = [[math.log(maps[c][common[k]][0] / maps[c][common[k - 1]][0]) for k in range(1, len(common))] for c in codes]
    price = {c: series[c][-1][2] for c in codes}
    last_date = {c: series[c][-1][0] for c in codes}
    cov, sd, avg_corr = covariance(rets, a.shrink)
    ann = math.sqrt(252)

    sectors = {}
    if a.snapshot and a.snapshot.exists():
        with open(a.snapshot, encoding="utf-8-sig", newline="") as handle:
            for r in csv.DictReader(handle):
                sectors[(r.get("ticker") or "").upper()] = r.get("sector") or "?"

    # allocate the new budget across candidates
    cand = [c for c in codes if c in cands]
    alloc = {}
    if cand and a.budget > 0:
        idx = [codes.index(c) for c in cand]
        sub = [[cov[i][j] for j in idx] for i in idx]
        if a.method == "equal":
            w = [1 / len(cand)] * len(cand)
        elif a.method == "invvol":
            inv = [1 / math.sqrt(sub[k][k]) for k in range(len(cand))]
            w = [x / sum(inv) for x in inv]
        else:
            w = erc_weights(sub)
        w = apply_caps(w, a.max_weight, [sectors.get(c, "?") for c in cand] if a.max_sector and sectors else None, a.max_sector)
        for c, wi in zip(cand, w):
            qty = math.floor(a.budget * wi / price[c])
            alloc[c] = {"target_weight": wi, "shares": qty, "cost": qty * price[c], "price": price[c]}
    spent = sum(x["cost"] for x in alloc.values())

    # combined portfolio after the new positions
    value = {c: (holdings.get(c, {}).get("quantity", 0) + alloc.get(c, {}).get("shares", 0)) * price[c] for c in codes}
    total = sum(value.values())
    cash_left = a.budget - spent
    if total <= 0:
        raise SystemExit("portfolio value is zero: give --holdings or a --budget with candidates")
    w_all = [value[c] / total for c in codes]
    var = port_var(w_all, cov)
    vol = math.sqrt(var) * ann
    mv = mat_vec(cov, w_all)
    rc = [w_all[i] * mv[i] / var if var else 0 for i in range(len(codes))]
    div_ratio = sum(w_all[i] * sd[i] for i in range(len(codes))) / math.sqrt(var) if var else None
    port_rets = [sum(w_all[i] * rets[i][k] for i in range(len(codes))) for k in range(len(rets[0]))]
    simple = [math.exp(x) - 1 for x in port_rets]
    var95 = -quantile(simple, 0.05)
    tail = [x for x in simple if x <= -var95]
    es95 = -sum(tail) / len(tail) if tail else None
    worst20 = min((math.exp(sum(port_rets[k - 20:k])) - 1 for k in range(20, len(port_rets) + 1)), default=None)
    beta = None
    if a.benchmark and a.benchmark.exists():
        b = {d: adj for d, adj, _ in load(a.benchmark)}
        pairs = [(port_rets[k - 1], math.log(b[common[k]] / b[common[k - 1]])) for k in range(1, len(common))
                 if common[k] in b and common[k - 1] in b]
        if len(pairs) > 30:
            mx, my = sum(p for p, _ in pairs) / len(pairs), sum(q for _, q in pairs) / len(pairs)
            vb = sum((q - my) ** 2 for _, q in pairs)
            beta = sum((p - mx) * (q - my) for p, q in pairs) / vb if vb else None
    pairs_hi = []
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            if sd[i] and sd[j]:
                raw = sum((rets[i][k] - sum(rets[i]) / len(rets[i])) * (rets[j][k] - sum(rets[j]) / len(rets[j])) for k in range(len(rets[i]))) / (len(rets[i]) - 1)
                corr = raw / (sd[i] * sd[j])
                if corr >= 0.7:
                    pairs_hi.append((codes[i], codes[j], corr))
    pairs_hi.sort(key=lambda x: -x[2])
    sector_exp = {}
    for c in codes:
        s = sectors.get(c, "?")
        sector_exp[s] = sector_exp.get(s, 0.0) + value[c] / total
    heat = []
    for c in codes:
        qty = holdings.get(c, {}).get("quantity", 0) + alloc.get(c, {}).get("shares", 0)
        if c in stops and qty:
            heat.append({"code": c, "stop": stops[c], "loss_to_stop": max(0.0, (price[c] - stops[c]) * qty)})
    heat_total = sum(h["loss_to_stop"] for h in heat)

    rows = []
    for i, c in enumerate(codes):
        rows.append({"code": c, "sector": sectors.get(c, "?"), "price": price[c], "price_date": last_date[c],
                     "held_shares": holdings.get(c, {}).get("quantity", 0), "new_shares": alloc.get(c, {}).get("shares", 0),
                     "new_cost": alloc.get(c, {}).get("cost", 0.0), "target_weight_of_budget": alloc.get(c, {}).get("target_weight"),
                     "portfolio_weight": w_all[i], "vol_ann_pct": sd[i] * ann * 100, "risk_contribution_pct": rc[i] * 100})
    report = {"generated_at": datetime.now(TRT).isoformat(timespec="seconds"), "method": a.method, "budget": a.budget,
              "spent": spent, "cash_left": cash_left, "portfolio_value": total, "lookback_days": len(common) - 1,
              "portfolio_vol_ann_pct": vol * 100, "diversification_ratio": div_ratio, "avg_pairwise_corr": avg_corr,
              "var95_1d_pct": var95 * 100 if var95 is not None else None, "es95_1d_pct": es95 * 100 if es95 is not None else None,
              "worst_20d_pct": worst20 * 100 if worst20 is not None else None, "beta_to_benchmark": beta,
              "heat_total": heat_total, "heat_pct_of_portfolio": heat_total / total * 100 if total else None,
              "sector_exposure_pct": {k: v * 100 for k, v in sorted(sector_exp.items(), key=lambda kv: -kv[1])},
              "high_correlation_pairs": [{"a": x, "b": y, "corr": round(r, 3)} for x, y, r in pairs_hi[:15]],
              "positions": rows, "missing_histories": missing,
              "assumptions": [f"daily log returns over {len(common) - 1} common days; correlations shrunk {a.shrink:.0%} toward their average",
                              "prices are the last delayed close in the history files; re-check before any order",
                              "VaR/ES and worst-20-day are historical (this window only) and are not loss caps",
                              "BIST lot = 1 share; fees, taxes and slippage not deducted"]}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "portfolio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    f = lambda x, d=2: "—" if x is None else f"{x:,.{d}f}"
    lines = [f"# Portföy kurulumu — yöntem {a.method.upper()}", "",
             f"- Bütçe {f(a.budget, 0)} · harcanan {f(spent, 0)} · kalan nakit {f(cash_left, 0)} · toplam portföy {f(total, 0)} (son kapanışlar, gecikmeli)",
             f"- Yıllık oynaklık %{f(vol * 100, 1)} · çeşitlendirme oranı {f(div_ratio)} · ort. korelasyon {f(avg_corr)} · beta {f(beta)}",
             f"- 1 günlük tarihsel VaR95 %{f(report['var95_1d_pct'])} · ES95 %{f(report['es95_1d_pct'])} · en kötü 20 gün %{f(report['worst_20d_pct'], 1)}"
             + (f" · stoplara açık risk (heat) {f(heat_total, 0)} = portföyün %{f(report['heat_pct_of_portfolio'], 1)}" if heat else ""),
             "", "| Kod | Sektör | Fiyat | Eldeki | Yeni adet | Yeni tutar | Portföy ağırlığı % | Oynaklık % | Risk payı % |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -r["portfolio_weight"]):
        lines.append(f"| {r['code']} | {r['sector'][:20]} | {f(r['price'])} | {f(r['held_shares'], 0)} | {f(r['new_shares'], 0)} | {f(r['new_cost'], 0)} | "
                     f"{f(r['portfolio_weight'] * 100, 1)} | {f(r['vol_ann_pct'], 1)} | {f(r['risk_contribution_pct'], 1)} |")
    lines += ["", "Sektör dağılımı: " + ", ".join(f"{k} %{v:.1f}" for k, v in report["sector_exposure_pct"].items())]
    if pairs_hi:
        lines.append("Yüksek korelasyon (≥0,70, aynı riski iki kez taşır): " + ", ".join(f"{x}–{y} {r:.2f}" for x, y, r in pairs_hi[:10]))
    if missing:
        lines.append("Geçmişi olmayan (hesaba katılmadı): " + ", ".join(missing))
    lines += ["", "> Bu bir risk dağılımı önerisidir, al emri değildir. Her yeni pozisyon ön işlem kapısından geçmeli; tek hisse ve sektör sınırları kullanıcı profiline göre ayarlanır.",
              "", "Varsayımlar: " + "; ".join(report["assumptions"]) + "."]
    (a.out / "portfolio.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {len(codes)} names, vol {vol * 100:.1f}%/yr, spent {spent:,.0f} of {a.budget:,.0f} -> {a.out}")
    for r in sorted(rows, key=lambda r: -r["portfolio_weight"])[:12]:
        print(f"  {r['code']:<6} w {r['portfolio_weight'] * 100:5.1f}%  new {r['new_shares']:>7.0f}  risk {r['risk_contribution_pct']:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
