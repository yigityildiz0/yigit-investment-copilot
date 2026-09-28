#!/usr/bin/env python3
"""BIST market regime dashboard: breadth, sector rotation, index trend, distribution and
follow-through days, USD-based trend and a heuristic exposure band.

Inputs (from market-data-engine):
  --snapshot  snapshot.csv (all stocks)            required
  --index     XU100.csv OHLCV history (chart mode)  recommended
  --usdtry    TRY=X / USDTRY.csv history            optional (USD-based index trend)
  --history-dir  per-stock CSVs                     optional (adjusted 52-week highs/lows)

The regime label and exposure band are transparent heuristics adapted from O'Neil-style
distribution/follow-through logic and breadth practice; they are context, not a trade signal.

Usage:
  python bist_breadth.py --snapshot snap/snapshot.csv --index hist/XU100.csv --usdtry hist/USDTRY.csv --out regime
"""

import argparse
import csv
import json
import sys
import math
from pathlib import Path


def fnum(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_series(path):
    out = []
    for r in read_rows(path):
        c = fnum(r.get("adj_close")) or fnum(r.get("close"))
        if c:
            out.append({"date": r["date"], "close": c, "volume": fnum(r.get("volume")) or 0.0,
                        "complete": str(r.get("complete", "1")) not in ("0", "false")})
    return [x for x in out if x["complete"]]


def median(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def share(flags):
    flags = [f for f in flags if f is not None]
    return round(100 * sum(flags) / len(flags), 1) if flags else None


def sma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def index_features(series, dd_threshold=0.08, ftd_gain=0.015):
    closes = [x["close"] for x in series]
    vols = [x["volume"] for x in series]
    n = len(closes)
    out = {"last_date": series[-1]["date"], "close": closes[-1], "sma50": sma(closes, 50), "sma200": sma(closes, 200)}
    if n > 220:
        out["sma200_slope_20d_pct"] = (sma(closes, 200) / (sum(closes[-220:-20]) / 200) - 1) * 100
    hi = max(closes[-252:])
    out["from_52w_high_pct"] = (closes[-1] / hi - 1) * 100
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, n)]
    if len(rets) > 260:
        vol20 = [math.sqrt(sum(r * r for r in rets[i - 20:i]) / 20) * math.sqrt(252) for i in range(len(rets) - 252, len(rets) + 1)]
        out["realized_vol_20d_pct"] = vol20[-1] * 100
        out["vol_percentile_1y"] = round(100 * sum(v <= vol20[-1] for v in vol20) / len(vol20), 1)
    have_volume = sum(1 for v in vols[-30:] if v) >= 25
    dist = []
    if have_volume:
        for i in range(max(1, n - 25), n):
            if closes[i] / closes[i - 1] - 1 <= -0.002 and vols[i] > vols[i - 1]:
                dist.append(series[i]["date"])
    out["distribution_days_25"] = len(dist) if have_volume else None
    out["distribution_dates"] = dist
    # follow-through day after a correction low within the last 60 sessions
    window = closes[-60:]
    low_i = min(range(len(window)), key=lambda k: window[k])
    low_abs = n - 60 + low_i
    prior_high = max(closes[max(0, low_abs - 120):low_abs + 1])
    out["correction_depth_pct"] = (window[low_i] / prior_high - 1) * 100
    ftd = None
    if window[low_i] / prior_high - 1 <= -dd_threshold:
        for i in range(low_abs + 4, n):
            if min(closes[low_abs + 1:i + 1]) < closes[low_abs]:
                break  # low undercut: rally attempt failed
            if closes[i] / closes[i - 1] - 1 >= ftd_gain and (not have_volume or vols[i] > vols[i - 1]):
                ftd = series[i]["date"]
                break
    out["correction_low_date"] = series[low_abs]["date"]
    out["follow_through_day"] = ftd
    return out



def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--index", type=Path)
    ap.add_argument("--usdtry", type=Path)
    ap.add_argument("--history-dir", type=Path)
    ap.add_argument("--universe", default="ALL", help="ALL or XU100 / XU030 membership column")
    ap.add_argument("--market-label", default="BIST", help="title label, e.g. ABD for a US snapshot")
    ap.add_argument("--index-name", default="XU100", help="index label used in the report")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    rows = read_rows(a.snapshot)
    if a.universe.upper() != "ALL":
        rows = [r for r in rows if r.get(f"in_{a.universe.lower()}") == "1"]
    rows = [r for r in rows if fnum(r.get("close"))]
    near_hi, near_lo = [], []
    for r in rows:
        c = fnum(r["close"])
        hi, lo = fnum(r.get("high_52w")), fnum(r.get("low_52w"))
        if a.history_dir and (a.history_dir / f"{r['ticker']}.csv").exists():
            s = load_series(a.history_dir / f"{r['ticker']}.csv")[-252:]
            if len(s) > 100:
                hi, lo = max(x["close"] for x in s), min(x["close"] for x in s)
        near_hi.append(c >= 0.95 * hi if hi else None)
        near_lo.append(c <= 1.05 * lo if lo else None)
    breadth = {
        "stocks": len(rows),
        "pct_above_sma50": share([fnum(r["close"]) > fnum(r["sma50"]) if fnum(r.get("sma50")) else None for r in rows]),
        "pct_above_sma200": share([fnum(r["close"]) > fnum(r["sma200"]) if fnum(r.get("sma200")) else None for r in rows]),
        "pct_sma50_above_sma200": share([fnum(r["sma50"]) > fnum(r["sma200"]) if fnum(r.get("sma50")) and fnum(r.get("sma200")) else None for r in rows]),
        "advancers": sum(1 for r in rows if (fnum(r.get("change_pct")) or 0) > 0),
        "decliners": sum(1 for r in rows if (fnum(r.get("change_pct")) or 0) < 0),
        "pct_near_52w_high": share(near_hi), "pct_near_52w_low": share(near_lo),
        "median_perf_1m_pct": median([fnum(r.get("perf_1m_pct")) for r in rows]),
        "median_perf_3m_pct": median([fnum(r.get("perf_3m_pct")) for r in rows]),
        "pct_positive_1m": share([fnum(r["perf_1m_pct"]) > 0 if fnum(r.get("perf_1m_pct")) is not None else None for r in rows]),
        "basis_52w": "adjusted history" if a.history_dir else "snapshot (vendor 52w fields may miss bonus-issue adjustments)",
    }
    sectors = {}
    for r in rows:
        sectors.setdefault(r.get("sector") or "?", []).append(r)
    sector_table = []
    for name, items in sectors.items():
        if len(items) < 4:
            continue
        sector_table.append({
            "sector": name, "n": len(items),
            "pct_above_sma50": share([fnum(r["close"]) > fnum(r["sma50"]) if fnum(r.get("sma50")) else None for r in items]),
            "median_1m_pct": median([fnum(r.get("perf_1m_pct")) for r in items]),
            "median_3m_pct": median([fnum(r.get("perf_3m_pct")) for r in items]),
            "median_6m_pct": median([fnum(r.get("perf_6m_pct")) for r in items]),
        })
    sector_table.sort(key=lambda s: -(s["median_3m_pct"] if s["median_3m_pct"] is not None else -999))

    idx = index_features(load_series(a.index)) if a.index and a.index.exists() else {}
    usd = {}
    if a.index and a.usdtry and a.index.exists() and a.usdtry.exists():
        fx = {x["date"]: x["close"] for x in load_series(a.usdtry)}
        ser = [x["close"] / fx[x["date"]] for x in load_series(a.index) if x["date"] in fx]
        if len(ser) > 200:
            usd = {"index_usd": ser[-1], "above_sma50": ser[-1] > sma(ser, 50), "above_sma200": ser[-1] > sma(ser, 200),
                   "from_52w_high_pct": (ser[-1] / max(ser[-252:]) - 1) * 100}

    label, band, risk = "BELİRSİZ (endeks verisi yok)", None, None
    if idx.get("sma200"):
        c, s50, s200 = idx["close"], idx["sma50"], idx["sma200"]
        b50 = breadth["pct_above_sma50"] or 0
        dd = idx.get("distribution_days_25") or 0
        if c > s50 > s200 and b50 >= 60 and dd <= 4:
            label, band, risk = "GÜÇLÜ YÜKSELİŞ", "%80–100", "%1,0"
        elif c > s200 and (dd >= 5 or b50 < 50 or c < s50):
            label, band, risk = ("DÜZELTME (uzun trend yukarı)", "%30–60", "%0,5") if c < s50 else ("YÜKSELİŞ — BASKI ALTINDA", "%50–80", "%0,75")
        elif c > s200:
            label, band, risk = "YÜKSELİŞ", "%70–90", "%0,75–1,0"
        elif idx.get("follow_through_day") or b50 >= 50:
            label, band, risk = "DİP ARAYIŞI / TOPARLANMA DENEMESİ", "%20–40 (pilot)", "%0,5"
        else:
            label, band, risk = "DÜŞÜŞ TRENDİ", "%0–30 (yalnız göreli güçlü/savunmacı)", "%0,25–0,5"
    result = {"regime_label": label, "equity_exposure_band_of_plan": band, "risk_per_trade_hint": risk,
              "breadth": breadth, "index": idx, "usd_based": usd, "sectors": sector_table,
              "method_note": "Heuristic regime from index trend (SMA50/200), breadth (% > SMA50), distribution days "
                             "(down ≥0.2% on higher volume, last 25 sessions) and follow-through day (≥1.5% gain on higher "
                             "volume, day 4+ after an ≥8% correction low). Not validated alpha; use as context."}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "regime.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    f = lambda x, d=1: "—" if x is None else (f"{x:,.{d}f}" if isinstance(x, (int, float)) else str(x))
    lines = [f"# {a.market_label} piyasa rejimi — {idx.get('last_date', '?')}", "",
             f"**Rejim:** {label} · **Plan içi hisse maruziyeti:** {band or '—'} · **İşlem başı risk ipucu:** {risk or '—'}", "",
             "## Endeks", "",
             f"- {a.index_name} {f(idx.get('close'))} · SMA50 {f(idx.get('sma50'))} · SMA200 {f(idx.get('sma200'))} · 52h zirveden {f(idx.get('from_52w_high_pct'))}%",
             f"- Dağıtım günü (25 seans): {f(idx.get('distribution_days_25'), 0)} · düzeltme derinliği {f(idx.get('correction_depth_pct'))}% (dip {idx.get('correction_low_date', '—')}) · takip günü: {idx.get('follow_through_day') or 'yok'}",
             f"- Gerçekleşen oynaklık 20g {f(idx.get('realized_vol_20d_pct'))}% (1y yüzdelik {f(idx.get('vol_percentile_1y'))})",
             f"- USD bazlı {a.index_name}: {f(usd.get('index_usd'), 2)} · SMA50 üstü {usd.get('above_sma50', '—')} · SMA200 üstü {usd.get('above_sma200', '—')} · 52h zirveden {f(usd.get('from_52w_high_pct'))}%",
             "", "## Genişlik", "",
             f"- {breadth['stocks']} hisse · SMA50 üstü %{f(breadth['pct_above_sma50'])} · SMA200 üstü %{f(breadth['pct_above_sma200'])} · SMA50>SMA200 %{f(breadth['pct_sma50_above_sma200'])}",
             f"- Bugün yükselen/düşen {breadth['advancers']}/{breadth['decliners']} · 52h zirveye %5 yakın %{f(breadth['pct_near_52w_high'])} · dibe yakın %{f(breadth['pct_near_52w_low'])}",
             f"- Medyan getiri 1A {f(breadth['median_perf_1m_pct'])}% · 3A {f(breadth['median_perf_3m_pct'])}% · 1A pozitif hisse %{f(breadth['pct_positive_1m'])}",
             "", "## Sektör rotasyonu (3A medyan getiriye göre)", "",
             "| Sektör | n | SMA50 üstü % | 1A % | 3A % | 6A % |", "|---|---|---|---|---|---|"]
    for s in sector_table:
        lines.append(f"| {s['sector']} | {s['n']} | {f(s['pct_above_sma50'])} | {f(s['median_1m_pct'])} | {f(s['median_3m_pct'])} | {f(s['median_6m_pct'])} |")
    lines += ["", f"_Yöntem: {result['method_note']}_"]
    (a.out / "regime.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK regime={label} exposure={band} breadth50={breadth['pct_above_sma50']} dist={idx.get('distribution_days_25')} ftd={idx.get('follow_through_day')} -> {a.out}")


if __name__ == "__main__":
    main()
