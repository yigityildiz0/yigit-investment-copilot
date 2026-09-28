#!/usr/bin/env python3
"""Technical state, setups and scenario levels from a validated OHLCV CSV (standard library only).

Input CSV columns: date, open, high, low, close, volume (+ optional adj_close, complete).
If adj_close exists, OHLC are rescaled by adj_close/close so splits, bonus issues and dividends do
not create fake gaps. Incomplete candles (complete=0/false) are excluded.

Outputs indicators (trend, momentum, volatility, volume), swing support/resistance clusters,
relative strength vs an optional benchmark, weekly-timeframe agreement, rule-based setup checks
and ATR/volatility scenario levels. These are measurements and conditional levels, not signals.

Usage:
  python technical_indicators.py THYAO.csv
  python technical_indicators.py THYAO.csv --benchmark XU100.csv --horizon-days 30 --repair --md THYAO_ta.md
"""

import argparse
import csv
import json
import sys
import math
from datetime import date
from pathlib import Path


# ------------------------------------------------------------------ primitives
def sma_series(values, window):
    out, total = [None] * len(values), 0.0
    for i, v in enumerate(values):
        total += v
        if i >= window:
            total -= values[i - window]
        if i >= window - 1:
            out[i] = total / window
    return out


def ema_series(values, window):
    out = [None] * len(values)
    if len(values) < window:
        return out
    alpha = 2 / (window + 1)
    out[window - 1] = sum(values[:window]) / window
    for i in range(window, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def wilder(values, window):
    out = [None] * len(values)
    if len(values) < window:
        return out
    out[window - 1] = sum(values[:window]) / window
    for i in range(window, len(values)):
        out[i] = (out[i - 1] * (window - 1) + values[i]) / window
    return out


def last(series):
    for v in reversed(series):
        if v is not None:
            return v
    return None


def stdev(values):
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def pct(a, b):
    return (a / b - 1) * 100 if a is not None and b not in (None, 0) else None


# ------------------------------------------------------------------ loading
def load(path, complete_column="complete", repair=False):
    rows, repaired = [], 0
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if complete_column in row and str(row[complete_column]).strip().lower() in {"0", "false", "no"}:
                continue
            try:
                o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
                v = float(row.get("volume") or 0)
            except (TypeError, ValueError, KeyError):
                continue
            adj = row.get("adj_close")
            factor = float(adj) / c if adj not in (None, "") and c else 1.0
            o, h, l, c = o * factor, h * factor, l * factor, c * factor
            v = v / factor if factor else v
            if min(o, h, l, c) <= 0 or v < 0:
                if repair:
                    repaired += 1
                    continue
                raise SystemExit(f"non-positive price or negative volume: {row['date']}")
            if h < max(o, c, l) or l > min(o, c, h):
                if not repair:
                    raise SystemExit(f"invalid OHLC row: {row['date']} (use --repair to clip)")
                h, l = max(o, h, l, c), min(o, h, l, c)
                repaired += 1
            rows.append({"date": row["date"], "open": o, "high": h, "low": l, "close": c, "volume": v})
    dates = [r["date"] for r in rows]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise SystemExit("dates must be unique and ascending ISO strings")
    return rows, repaired


def weekly(rows):
    out = {}
    for r in rows:
        y, w, _ = date.fromisoformat(r["date"]).isocalendar()
        key = (y, w)
        if key not in out:
            out[key] = dict(r)
        else:
            b = out[key]
            b["high"], b["low"] = max(b["high"], r["high"]), min(b["low"], r["low"])
            b["close"], b["volume"], b["date"] = r["close"], b["volume"] + r["volume"], r["date"]
    return [out[k] for k in sorted(out)]


# ------------------------------------------------------------------ indicators
def indicator_pack(rows):
    c = [r["close"] for r in rows]
    h = [r["high"] for r in rows]
    l = [r["low"] for r in rows]
    v = [r["volume"] for r in rows]
    n = len(rows)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    atr14 = wilder(tr, 14)
    gains = [0.0] + [max(0.0, c[i] - c[i - 1]) for i in range(1, n)]
    losses = [0.0] + [max(0.0, c[i - 1] - c[i]) for i in range(1, n)]
    ag, al = wilder(gains[1:], 14), wilder(losses[1:], 14)
    rsi = [None] + [None if a is None else (100.0 if b == 0 else 100 - 100 / (1 + a / b)) for a, b in zip(ag, al)]
    e12, e26 = ema_series(c, 12), ema_series(c, 26)
    macd = [a - b if a is not None and b is not None else None for a, b in zip(e12, e26)]
    valid = [m for m in macd if m is not None]
    sig_part = ema_series(valid, 9)
    signal = [None] * (n - len(valid)) + sig_part
    # ADX / DMI
    plus_dm = [0.0] + [max(h[i] - h[i - 1], 0.0) if (h[i] - h[i - 1]) > (l[i - 1] - l[i]) else 0.0 for i in range(1, n)]
    minus_dm = [0.0] + [max(l[i - 1] - l[i], 0.0) if (l[i - 1] - l[i]) > (h[i] - h[i - 1]) else 0.0 for i in range(1, n)]
    atr_w, pdm_w, mdm_w = wilder(tr[1:], 14), wilder(plus_dm[1:], 14), wilder(minus_dm[1:], 14)
    pdi = [100 * p / a if a else None for p, a in zip(pdm_w, atr_w)]
    mdi = [100 * m / a if a else None for m, a in zip(mdm_w, atr_w)]
    dx = [100 * abs(p - m) / (p + m) if p is not None and m is not None and (p + m) else None for p, m in zip(pdi, mdi)]
    dx_valid = [d for d in dx if d is not None]
    adx_part = wilder(dx_valid, 14)
    adx = last(adx_part)
    # Bollinger / Donchian / volume
    bb_mid = sma_series(c, 20)
    bb_sd = stdev(c[-20:]) if n >= 20 else None
    obv = [0.0]
    for i in range(1, n):
        obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0.0))
    mfi = None
    if n > 15 and any(v[-15:]):
        tp = [(h[i] + l[i] + c[i]) / 3 for i in range(n)]
        pos = sum(tp[i] * v[i] for i in range(n - 14, n) if tp[i] > tp[i - 1])
        neg = sum(tp[i] * v[i] for i in range(n - 14, n) if tp[i] < tp[i - 1])
        mfi = 100.0 if neg == 0 else 100 - 100 / (1 + pos / neg)
    k_raw = [(c[i] - min(l[i - 13:i + 1])) / (max(h[i - 13:i + 1]) - min(l[i - 13:i + 1])) * 100
             if i >= 13 and max(h[i - 13:i + 1]) > min(l[i - 13:i + 1]) else None for i in range(n)]
    k_valid = [k for k in k_raw if k is not None]
    stoch_k = sum(k_valid[-3:]) / 3 if len(k_valid) >= 3 else None
    stoch_d = (sum(k_valid[-3:]) + sum(k_valid[-4:-1]) + sum(k_valid[-5:-2])) / 9 if len(k_valid) >= 5 else None
    logret = [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    window = c[-252:]
    peak, maxdd = window[0], 0.0
    for x in window:
        peak = max(peak, x)
        maxdd = min(maxdd, x / peak - 1)
    s = {w: sma_series(c, w) for w in (20, 50, 100, 150, 200)}
    e = {w: ema_series(c, w) for w in (20, 50, 200)}
    a10 = sum(tr[-10:]) / 10 if n >= 10 else None
    a50 = sum(tr[-50:]) / 50 if n >= 50 else None
    vol20 = sum(v[-20:]) / 20 if n >= 20 else None
    out = {
        "close": c[-1], "open": rows[-1]["open"], "high": h[-1], "low": l[-1], "volume": v[-1],
        "sma20": last(s[20]), "sma50": last(s[50]), "sma100": last(s[100]), "sma150": last(s[150]), "sma200": last(s[200]),
        "ema20": last(e[20]), "ema50": last(e[50]), "ema200": last(e[200]),
        "sma50_slope_20d_pct": pct(s[50][-1], s[50][-21]) if n > 70 and s[50][-21] else None,
        "sma150_slope_20d_pct": pct(s[150][-1], s[150][-21]) if n > 170 and s[150][-21] else None,
        "sma200_slope_20d_pct": pct(s[200][-1], s[200][-21]) if n > 220 and s[200][-21] else None,
        "rsi14": last(rsi), "macd": last(macd), "macd_signal": last(signal),
        "macd_hist": (last(macd) - last(signal)) if last(macd) is not None and last(signal) is not None else None,
        "adx14": adx, "plus_di": last(pdi), "minus_di": last(mdi),
        "atr14": last(atr14), "atr_pct": last(atr14) / c[-1] * 100 if last(atr14) else None,
        "atr_contraction_10_50": a10 / a50 if a10 and a50 else None,
        "bb_upper": bb_mid[-1] + 2 * bb_sd if bb_sd else None, "bb_lower": bb_mid[-1] - 2 * bb_sd if bb_sd else None,
        "bb_width_pct": 4 * bb_sd / bb_mid[-1] * 100 if bb_sd and bb_mid[-1] else None,
        "bb_percent_b": (c[-1] - (bb_mid[-1] - 2 * bb_sd)) / (4 * bb_sd) if bb_sd else None,
        "stoch_k": stoch_k, "stoch_d": stoch_d, "mfi14": mfi,
        "obv_slope_20d": (obv[-1] - obv[-21]) / (sum(v[-20:]) or 1) if n > 21 else None,
        "donchian20_high": max(h[-21:-1]) if n > 21 else None, "donchian20_low": min(l[-21:-1]) if n > 21 else None,
        "donchian55_high": max(h[-56:-1]) if n > 56 else None, "donchian55_low": min(l[-56:-1]) if n > 56 else None,
        "high_52w": max(h[-252:]), "low_52w": min(l[-252:]),
        "dist_52w_high_pct": pct(c[-1], max(h[-252:])), "dist_52w_low_pct": pct(c[-1], min(l[-252:])),
        "volume_ratio_20d": v[-1] / vol20 if vol20 else None,
        "volume_dryup_10_50": (sum(v[-10:]) / 10) / (sum(v[-50:]) / 50) if n >= 50 and sum(v[-50:]) else None,
        "realized_vol_20d_ann_pct": stdev(logret[-20:]) * math.sqrt(252) * 100 if len(logret) >= 20 else None,
        "realized_vol_60d_ann_pct": stdev(logret[-60:]) * math.sqrt(252) * 100 if len(logret) >= 60 else None,
        "max_drawdown_1y_pct": maxdd * 100,
        "ret_1w_pct": pct(c[-1], c[-6]) if n > 6 else None, "ret_1m_pct": pct(c[-1], c[-22]) if n > 22 else None,
        "ret_3m_pct": pct(c[-1], c[-64]) if n > 64 else None, "ret_6m_pct": pct(c[-1], c[-127]) if n > 127 else None,
        "ret_1y_pct": pct(c[-1], c[-253]) if n > 253 else None,
        "limit_up_days_20": sum(1 for i in range(max(1, n - 20), n) if c[i] / c[i - 1] - 1 >= 0.095),
        "limit_down_days_20": sum(1 for i in range(max(1, n - 20), n) if c[i] / c[i - 1] - 1 <= -0.095),
        "chandelier_stop_3atr": max(h[-22:]) - 3 * last(atr14) if last(atr14) else None,
    }
    return out


def pivots(rows, atr, lookback=250, width=5):
    """Swing-high/low fractals clustered within one ATR: (price, touches, last_date)."""
    rows = rows[-lookback:]
    points = []
    for i in range(width, len(rows) - width):
        hi, lo = rows[i]["high"], rows[i]["low"]
        if hi == max(r["high"] for r in rows[i - width:i + width + 1]):
            points.append((hi, rows[i]["date"]))
        if lo == min(r["low"] for r in rows[i - width:i + width + 1]):
            points.append((lo, rows[i]["date"]))
    points.sort()
    clusters, tol = [], (atr or 0) or (rows[-1]["close"] * 0.02)
    for price, day in points:
        if clusters and price - clusters[-1]["prices"][0] <= tol:  # cluster span capped at one ATR
            clusters[-1]["prices"].append(price)
            clusters[-1]["last"] = max(clusters[-1]["last"], day)
        else:
            clusters.append({"prices": [price], "last": day})
    return [{"level": sum(cl["prices"]) / len(cl["prices"]), "touches": len(cl["prices"]), "last_touch": cl["last"]} for cl in clusters]


def relative_strength(rows, bench_path):
    bench = {}
    with Path(bench_path).open(encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            try:
                bench[r["date"]] = float(r.get("adj_close") or r["close"])
            except (TypeError, ValueError):
                pass
    common = [(r["date"], r["close"], bench[r["date"]]) for r in rows if r["date"] in bench]
    if len(common) < 70:
        return {}
    ratio = [a / b for _, a, b in common]
    out = {}
    for label, k in (("rs_1m_pct", 21), ("rs_3m_pct", 63), ("rs_6m_pct", 126), ("rs_1y_pct", 252)):
        if len(ratio) > k:
            out[label] = pct(ratio[-1], ratio[-1 - k])
    out["rs_line_at_52w_high"] = ratio[-1] >= max(ratio[-252:]) * 0.995
    rs = [ratio[i] / ratio[i - 1] - 1 for i in range(1, len(ratio))]
    br = [common[i][2] / common[i - 1][2] - 1 for i in range(1, len(common))]
    sr = [common[i][1] / common[i - 1][1] - 1 for i in range(1, len(common))]
    br, sr = br[-252:], sr[-252:]
    mb, ms = sum(br) / len(br), sum(sr) / len(sr)
    var_b = sum((x - mb) ** 2 for x in br)
    if var_b:
        out["beta_1y"] = sum((x - ms) * (y - mb) for x, y in zip(sr, br)) / var_b
    return out


def setups(p, rs, weekly_state):
    c = p["close"]
    s50, s150, s200 = p.get("sma50"), p.get("sma150"), p.get("sma200")
    tt = {}
    if s150 and s200:
        tt["fiyat>SMA150&SMA200"] = c > s150 and c > s200
        tt["SMA150>SMA200"] = s150 > s200
    if p.get("sma200_slope_20d_pct") is not None:
        tt["SMA200_yukseliyor"] = p["sma200_slope_20d_pct"] > 0
    if s50 and s150 and s200:
        tt["SMA50>SMA150&SMA200"] = s50 > s150 and s50 > s200
    if s50:
        tt["fiyat>SMA50"] = c > s50
    tt["52h_dipten>%30"] = p["dist_52w_low_pct"] >= 30
    tt["52h_zirveye<%25"] = p["dist_52w_high_pct"] >= -25
    if rs.get("rs_6m_pct") is not None:
        tt["endeksi_6ayda_gecti"] = rs["rs_6m_pct"] > 0
    slope150 = p.get("sma150_slope_20d_pct")
    stage = None
    if s150 and slope150 is not None:
        if c > s150 and slope150 > 0.5:
            stage = "Evre 2 (yükseliş)"
        elif c < s150 and slope150 < -0.5:
            stage = "Evre 4 (düşüş)"
        elif abs(slope150) <= 0.5:
            stage = "Evre 1/3 (yatay: dip oluşumu ya da tepe dağıtımı)"
        else:
            stage = "Geçiş"
    up = bool(s50 and s200 and c > s50 > s200)
    checks = {
        "trend_template": {"passed": sum(tt.values()), "checked": len(tt), "failed": [k for k, v in tt.items() if not v]},
        "weinstein_stage": stage,
        "breakout_ready": bool(p.get("donchian55_high") and c >= 0.97 * p["donchian55_high"]
                              and (p.get("atr_contraction_10_50") or 9) < 0.85 and (p.get("volume_dryup_10_50") or 9) < 1.0),
        "breakout_today": bool(p.get("donchian20_high") and c > p["donchian20_high"] and (p.get("volume_ratio_20d") or 0) >= 1.5),
        "pullback_in_uptrend": bool(up and p.get("ema20") and abs(c / p["ema20"] - 1) <= 0.02 and 38 <= (p.get("rsi14") or 0) <= 55),
        "oversold_in_uptrend": bool(s200 and c > s200 and (p.get("rsi14") or 50) < 35),
        "momentum_burst": bool(p.get("ret_1w_pct") is not None and p["high"] > p["low"]
                               and (p["close"] - p["low"]) / (p["high"] - p["low"]) >= 0.75 and (p.get("volume_ratio_20d") or 0) >= 1.5
                               and p["close"] / p["open"] - 1 >= 0.04),
        "vcp_like": bool((p.get("atr_contraction_10_50") or 9) < 0.7 and p["dist_52w_high_pct"] >= -10 and s50 and c > s50),
        "extended": bool((s50 and c > 1.25 * s50) or (p.get("rsi14") or 0) > 78),
        "downtrend": bool(s50 and s200 and c < s200 and s50 < s200),
        "weekly_trend_up": weekly_state.get("trend_up"),
    }
    return checks


def scenario_levels(p, levels, horizon_days):
    c, atr = p["close"], p.get("atr14") or 0
    supports = sorted([lv for lv in levels if lv["level"] < c * 0.995], key=lambda lv: -lv["level"])[:3]
    resists = sorted([lv for lv in levels if lv["level"] > c * 1.005], key=lambda lv: lv["level"])[:3]
    sigma = (p.get("realized_vol_60d_ann_pct") or p.get("realized_vol_20d_ann_pct") or 0) / 100
    t = max(1, horizon_days) / 365
    band = {f"p{int(q * 100)}": c * math.exp(z * sigma * math.sqrt(t)) for q, z in ((0.16, -1.0), (0.5, 0.0), (0.84, 1.0))} if sigma else {}
    return {
        "supports": supports, "resistances": resists,
        "bull_trigger": resists[0]["level"] if resists else p.get("donchian20_high"),
        "bear_trigger": supports[0]["level"] if supports else p.get("donchian20_low"),
        "atr_stop_2x": c - 2 * atr if atr else None, "atr_stop_3x": c - 3 * atr if atr else None,
        "chandelier_stop": p.get("chandelier_stop_3atr"),
        "one_sigma_band_horizon": band,
        "note": "Seviyeler koşullu senaryodur; boşluk (gap) ve ±%10 günlük limit stop'u atlayabilir.",
    }


def to_md(result):
    p, st, lv = result["indicators"], result["setups"], result["levels"]
    f = lambda x, d=2: "—" if x is None else (f"{x:,.{d}f}" if isinstance(x, (int, float)) else str(x))
    lines = [f"# Teknik görünüm — {result['as_of']} ({result['candles']} mum)", "",
             f"- Kapanış {f(p['close'])} · SMA50 {f(p['sma50'])} · SMA200 {f(p['sma200'])} · RSI {f(p['rsi14'], 1)} · ADX {f(p['adx14'], 1)} · ATR% {f(p['atr_pct'])}",
             f"- Getiri 1A {f(p['ret_1m_pct'], 1)}% · 3A {f(p['ret_3m_pct'], 1)}% · 1Y {f(p['ret_1y_pct'], 1)}% · 52h zirveye {f(p['dist_52w_high_pct'], 1)}% · 1y maks. düşüş {f(p['max_drawdown_1y_pct'], 1)}%",
             f"- Trend şablonu {st['trend_template']['passed']}/{st['trend_template']['checked']} · {st['weinstein_stage']} · haftalık trend {'yukarı' if st['weekly_trend_up'] else 'yukarı değil'}",
             "- Kurulumlar: " + (", ".join(k for k, v in st.items() if v is True) or "belirgin kurulum yok"),
             f"- Göreli güç (endekse göre) 3A {f(result['relative_strength'].get('rs_3m_pct'), 1)}% · 6A {f(result['relative_strength'].get('rs_6m_pct'), 1)}%",
             "- Destekler: " + (", ".join("{} ({})".format(f(s["level"]), s["touches"]) for s in lv["supports"]) or "—")
             + " · Dirençler: " + (", ".join("{} ({})".format(f(r["level"]), r["touches"]) for r in lv["resistances"]) or "—"),
             f"- Boğa tetik {f(lv['bull_trigger'])} · ayı tetik {f(lv['bear_trigger'])} · ATR stop 2x {f(lv['atr_stop_2x'])} / 3x {f(lv['atr_stop_3x'])} · chandelier {f(lv['chandelier_stop'])}",
             f"- {lv['note']}"]
    return "\n".join(lines) + "\n"



def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--complete-column", default="complete")
    parser.add_argument("--benchmark", type=Path, help="benchmark OHLCV CSV for relative strength and beta")
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--repair", action="store_true", help="clip inconsistent OHLC rows instead of failing")
    parser.add_argument("--md", type=Path, help="also write a Turkish Markdown summary")
    args = parser.parse_args()
    rows, repaired = load(args.csv_file, args.complete_column, args.repair)
    if len(rows) < 60:
        raise SystemExit("need at least 60 complete candles")
    p = indicator_pack(rows)
    levels = pivots(rows, p.get("atr14"))
    rs = relative_strength(rows, args.benchmark) if args.benchmark else {}
    wk = weekly(rows)
    weekly_state = {}
    if len(wk) >= 35:
        wc = [b["close"] for b in wk]
        w10, w30 = sum(wc[-10:]) / 10, sum(wc[-30:]) / 30
        weekly_state = {"close": wc[-1], "sma10w": w10, "sma30w": w30, "trend_up": wc[-1] > w30 and w10 > w30}
    result = {
        "as_of": rows[-1]["date"], "candles": len(rows), "repaired_rows": repaired,
        "price_basis": "adjusted (adj_close/close factor)" if "adj_close" in args.csv_file.read_text(encoding="utf-8-sig").split("\n", 1)[0] else "as provided",
        "indicators": p, "relative_strength": rs, "weekly": weekly_state,
        "setups": setups(p, rs, weekly_state), "levels": scenario_levels(p, levels, args.horizon_days),
        "warning": "Indicators describe the past; combine with fundamentals, events, liquidity and a written invalidation.",
    }
    # backward-compatible top-level keys used by earlier versions
    for key in ("close", "sma20", "sma50", "sma200", "rsi14", "atr14", "atr_pct", "macd", "macd_signal"):
        result[key] = p.get(key)
    if args.md:
        args.md.write_text(to_md(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
