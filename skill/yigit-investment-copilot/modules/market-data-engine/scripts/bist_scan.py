#!/usr/bin/env python3
"""Multi-lane, horizon-aware screen of a stock snapshot (research priority, never a buy signal).

Built for Borsa İstanbul; also runs on a US snapshot (bist_snapshot.py --market america): the market,
currency and index-membership columns are read from snapshot.meta.json.

Inputs
  --snapshot    snapshot.csv from bist_snapshot.py (or a mapped CSV with the same column names)
  --history-dir optional folder of price_history.py CSVs; enables precise momentum, volatility,
                contraction, limit-up streak, beta and relative strength features
  --benchmark   optional benchmark CSV (e.g. XU100.csv) for relative strength and beta
  --kap         optional kap_feed.py JSON (market-wide) for catalyst and risk flags (BIST only)

Lanes (each a 0..1 percentile-style score; sector-relative where accounting differs):
  liquidity, momentum, short_momentum, trend, setup, reversal, value, quality, growth,
  low_risk, catalyst, expectations (analyst target upside, consensus rating, fresh earnings surprise)
Profiles weight the lanes for a research-priority composite. Weights are transparent priors, not
validated alpha; test them with quant-research-lab before trusting them.

Usage:
  python bist_scan.py --snapshot snap/snapshot.csv --horizon 3m --out scan
  python bist_scan.py --snapshot snap/snapshot.csv --history-dir hist --benchmark hist/XU100.csv \
      --kap kap/kap_all.json --horizon 2w --universe XU100 --top 20 --out scan
"""

import argparse
import json
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (fnum, iso, md_table, mean, median, now_trt, pct_ranks, read_csv, read_json,  # noqa: E402
                    safe_name, setup_stdout, sha256_file, stdev, write_csv, write_json, yahoo_symbol)

PROFILES = {
    "kisa": {"trend": 0.20, "setup": 0.20, "short_momentum": 0.15, "catalyst": 0.10, "reversal": 0.05,
             "liquidity": 0.10, "low_risk": 0.10, "quality": 0.05, "expectations": 0.05},
    "orta": {"momentum": 0.15, "growth": 0.15, "value": 0.15, "quality": 0.15, "trend": 0.10, "setup": 0.05,
             "catalyst": 0.05, "low_risk": 0.05, "liquidity": 0.05, "expectations": 0.10},
    "uzun": {"quality": 0.30, "value": 0.25, "growth": 0.15, "low_risk": 0.10, "momentum": 0.10,
             "liquidity": 0.05, "expectations": 0.05},
}
HORIZON_DAYS = {"1w": 7, "2w": 14, "1m": 30, "2m": 60, "3m": 90, "6m": 180, "9m": 270, "1y": 365, "2y": 730, "3y": 1095}
LANES = ["liquidity", "momentum", "short_momentum", "trend", "setup", "reversal", "value", "quality",
         "growth", "low_risk", "catalyst", "expectations"]
# lane-specific score for "no data": analyst coverage is thin (~75 BIST names), so an uncovered
# stock is neutral on expectations instead of penalised like other missing lanes
MISSING_OVERRIDE = {"expectations": 0.5}
STRING_COLUMNS = {"symbol", "ticker", "name", "sector", "industry", "sector_en", "update_mode", "typespecs",
                  "earnings_next", "earnings_last", "exchange", "currency", "exdiv_next", "exdiv_last"}
POSITIVE_KAP = {"BUYBACK": 0.2, "CONTRACT_ORDER": 0.3, "BONUS_ISSUE": 0.3, "DIVIDEND": 0.2, "TENDER_OFFER": 0.2}
RISK_KAP = {"SPK_TRADING_BAN": "SPK_YASAK_LISTESI", "VBTS_MEASURE": "VBTS_TEDBIR", "RIGHTS_ISSUE": "BEDELLI_SULANMA",
            "SUPPLY_OVERHANG": "TIPE_DONUSUM", "DISTRESS": "FINANSAL_SIKINTI", "LEGAL": "HUKUKI_RISK"}


def days_until(text, today):
    if not text:
        return None
    try:
        return (date.fromisoformat(str(text)[:10]) - today).days
    except ValueError:
        return None


def history_path(folder, ticker, market):
    """price_history.py names files after the code, or the Yahoo symbol for dotted share classes."""
    for name in (ticker, safe_name(yahoo_symbol(ticker, market))):
        path = folder / f"{name}.csv"
        if path.exists():
            return path
    return None


def horizon_to_days(text, days):
    if days:
        return int(days)
    key = (text or "3m").lower().strip()
    if key in HORIZON_DAYS:
        return HORIZON_DAYS[key]
    if key.endswith("d") and key[:-1].isdigit():
        return int(key[:-1])
    raise SystemExit(f"unknown horizon {text}; use 1w,2w,1m,3m,6m,1y,2y,3y or --days")


def profile_for(days):
    return "kisa" if days <= 30 else "orta" if days <= 180 else "uzun"


def load_history(path):
    rows = read_csv(path)
    out = []
    for row in rows:
        if str(row.get("complete", "1")).strip() in {"0", "false", "False"}:
            continue
        c, a = fnum(row.get("close")), fnum(row.get("adj_close"))
        if not c or c <= 0:
            continue
        a = a if a and a > 0 else c
        factor = a / c
        out.append({"date": row["date"], "close": c, "adj": a,
                    "high": (fnum(row.get("high")) or c) * factor, "low": (fnum(row.get("low")) or c) * factor,
                    "open": (fnum(row.get("open")) or c) * factor, "volume": fnum(row.get("volume")) or 0.0})
    return out


def atr(bars, window):
    if len(bars) <= window:
        return None
    trs = []
    for i in range(len(bars) - window, len(bars)):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["adj"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / window


def history_features(bars, bench=None):
    n = len(bars)
    if n < 30:
        return {}
    adj = [b["adj"] for b in bars]
    f = {"hist_bars": n, "hist_last_date": bars[-1]["date"]}
    rets = [math.log(adj[i] / adj[i - 1]) for i in range(1, n)]
    if n > 253:
        f["mom_12_1"] = adj[-22] / adj[-253] - 1
    if n > 127:
        f["mom_6_1"] = adj[-22] / adj[-127] - 1
    f["ret_1m"] = adj[-1] / adj[-22] - 1 if n > 22 else None
    f["ret_3m"] = adj[-1] / adj[-64] - 1 if n > 64 else None
    window = adj[-252:]
    f["prox_52w_high"] = adj[-1] / max(window)
    f["dist_52w_low"] = adj[-1] / min(window) - 1
    if len(rets) >= 60:
        f["vol_60d_ann"] = stdev(rets[-60:]) * math.sqrt(252)
    peak, maxdd = window[0], 0.0
    for value in window:
        peak = max(peak, value)
        maxdd = min(maxdd, value / peak - 1)
    f["maxdd_1y"] = maxdd
    # pump-and-dump signature: >=2.5x run-up from a 6-month base, then back below half of the peak
    peak_i = max(range(len(window)), key=lambda k: window[k])
    base = min(window[max(0, peak_i - 120):peak_i + 1])
    f["spike_multiple"] = window[peak_i] / base if base else None
    f["spike_crash"] = int(bool(f["spike_multiple"] and f["spike_multiple"] >= 2.5 and window[-1] / window[peak_i] <= 0.5))
    a10, a50 = atr(bars, 10), atr(bars, 50)
    if a10 and a50:
        f["atr_contraction"] = a10 / a50
        f["atr_pct"] = atr(bars, 14) / adj[-1] * 100
    turnover = [b["close"] * b["volume"] for b in bars[-60:] if b["volume"]]
    f["median_turnover_60d_try"] = median(turnover) if turnover else None
    daily = [adj[i] / adj[i - 1] - 1 for i in range(max(1, n - 20), n)]
    f["limit_up_20d"] = sum(1 for r in daily if r >= 0.095)
    f["limit_down_20d"] = sum(1 for r in daily if r <= -0.095)
    if n >= 221:
        sma_now = sum(adj[-200:]) / 200
        sma_prev = sum(adj[-220:-20]) / 200
        f["sma200_slope_20d"] = sma_now / sma_prev - 1
    ups = sum(b["volume"] for i, b in enumerate(bars[-50:], start=n - 50) if i > 0 and bars[i]["adj"] > bars[i - 1]["adj"])
    downs = sum(b["volume"] for i, b in enumerate(bars[-50:], start=n - 50) if i > 0 and bars[i]["adj"] < bars[i - 1]["adj"])
    f["updown_volume_50d"] = ups / downs if downs else None
    if bench:
        common_dates = [b["date"] for b in bars if b["date"] in bench]
        if len(common_dates) > 70:
            mine = {b["date"]: b["adj"] for b in bars}
            seq = common_dates[-253:]
            r_s = [mine[seq[i]] / mine[seq[i - 1]] - 1 for i in range(1, len(seq))]
            r_b = [bench[seq[i]] / bench[seq[i - 1]] - 1 for i in range(1, len(seq))]
            mb = sum(r_b) / len(r_b)
            ms = sum(r_s) / len(r_s)
            var_b = sum((x - mb) ** 2 for x in r_b)
            if var_b > 0:
                f["beta_hist"] = sum((x - ms) * (y - mb) for x, y in zip(r_s, r_b)) / var_b
            for label, k in (("rs_1m", 21), ("rs_3m", 63), ("rs_6m", 126)):
                if len(seq) > k:
                    f[label] = (mine[seq[-1]] / mine[seq[-1 - k]]) - (bench[seq[-1]] / bench[seq[-1 - k]])
    return f


def is_financial(row):
    return (row.get("sector_en") or "").strip().lower() == "finance"


def ranks_by_group(rows, key_fn, higher=True, group_fn=None, min_group=6):
    values = [key_fn(r) for r in rows]
    overall = pct_ranks(values, higher)
    if not group_fn:
        return overall
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(group_fn(r), []).append(i)
    result = list(overall)
    for idx in groups.values():
        observed = [values[i] for i in idx if values[i] is not None]
        if len(observed) >= min_group:
            sub = pct_ranks([values[i] for i in idx], higher)
            for j, i in enumerate(idx):
                result[i] = sub[j]
    return result


def ratio(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def pos_inverse(x):
    return 1 / x if x is not None and x > 0 else None


def avg(values):
    values = [v for v in values if v is not None]
    return (sum(values) / len(values), len(values)) if values else (None, 0)


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--history-dir", type=Path)
    ap.add_argument("--benchmark", type=Path)
    ap.add_argument("--kap", type=Path, help="kap_feed.py JSON for catalyst/risk flags")
    ap.add_argument("--horizon", default="3m")
    ap.add_argument("--days", type=int)
    ap.add_argument("--profile", choices=sorted(PROFILES), help="override the profile chosen from the horizon")
    ap.add_argument("--weights", type=Path, help="JSON {lane: weight} to override profile weights")
    ap.add_argument("--universe", default="ALL", help="ALL, XUTUM, XU100, XU050, XU030 (turkey) or SPX, NDX, DJI (america)")
    ap.add_argument("--market", help="turkey or america (default: from snapshot.meta.json)")
    ap.add_argument("--min-turnover", type=float, default=10_000_000, help="daily value-traded floor in the snapshot currency (default 10M)")
    ap.add_argument("--exclude-flags", default="", help="comma list of risk flags that exclude a name")
    ap.add_argument("--exclude-file", type=Path, help="lines: TICKER,reason")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--missing-lane-score", type=float, default=0.4,
                    help="score used for a lane with no data (below neutral: unknown is a risk, not a strength)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    horizon_days = horizon_to_days(args.horizon, args.days)
    profile = args.profile or profile_for(horizon_days)
    weights = dict(PROFILES[profile])
    if args.weights:
        weights = {k: float(v) for k, v in read_json(args.weights).items() if k in LANES}
    snapshot_meta = {}
    meta_path = args.snapshot.with_name("snapshot.meta.json")
    if meta_path.exists():
        snapshot_meta = read_json(meta_path)
    market = args.market or snapshot_meta.get("market") or "turkey"
    currency = snapshot_meta.get("currency") if isinstance(snapshot_meta.get("currency"), str) else None
    currency = currency or ("TL" if market == "turkey" else "USD")
    currency = "TL" if currency == "TRY" else currency
    market_label = "BIST" if market == "turkey" else {"america": "ABD"}.get(market, market.upper())

    raw_rows = read_csv(args.snapshot)
    rows = []
    for r in raw_rows:
        row = {k: (fnum(v) if k not in STRING_COLUMNS else v) for k, v in r.items()}
        rows.append(row)
    uni = args.universe.upper()
    if uni != "ALL":
        col = f"in_{uni.lower()}"
        if col not in raw_rows[0]:
            raise SystemExit(f"snapshot has no {col} column; fetch it with --universe ALL or {uni}")
        rows = [r for r in rows if r.get(col) == 1]
    membership = [r["ticker"] for r in rows]

    bench = None
    if args.benchmark and args.benchmark.exists():
        bench = {b["date"]: b["adj"] for b in load_history(args.benchmark)}

    kap_by_ticker, kap_loaded = {}, False
    if args.kap and args.kap.exists():
        kap = read_json(args.kap)
        kap_loaded = True
        for item in kap.get("items", []):
            tickers = item.get("tickers", [])
            # a long SPK list names stocks held by sanctioned persons: too broad to flag each stock
            if item.get("event_class") == "SPK_TRADING_BAN" and len(tickers) > 15:
                continue
            for t in tickers:
                kap_by_ticker.setdefault(t, []).append(item)

    cb_counts = {t: sum(1 for e in ev if e.get("event_class") == "CIRCUIT_BREAKER") for t, ev in kap_by_ticker.items()}
    cb_values = sorted(v for v in cb_counts.values() if v)
    cb_cut = max(5, cb_values[int(0.9 * len(cb_values)) - 1]) if cb_values else 10 ** 9

    exclusions = {}
    if args.exclude_file and args.exclude_file.exists():
        for line in args.exclude_file.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                t, _, reason = line.partition(",")
                exclusions[t.strip().upper()] = reason.strip() or "kullanıcı dışlaması"
    exclude_flags = {f.strip() for f in args.exclude_flags.split(",") if f.strip()}

    today = now_trt().date()
    for r in rows:
        if args.history_dir:
            p = history_path(args.history_dir, r["ticker"], market)
            if p:
                r.update({f"h_{k}" if not k.startswith("hist_") else k: v
                          for k, v in history_features(load_history(p), bench).items()})
        c = r.get("close")
        p1m, p6m, p1y = (r.get("perf_1m_pct"), r.get("perf_6m_pct"), r.get("perf_1y_pct"))
        # snapshot-based features exist for every row and keep cross-sectional ranks consistent
        r["s_mom_12_1"] = (1 + p1y / 100) / (1 + p1m / 100) - 1 if p1y is not None and p1m is not None else None
        r["s_mom_6_1"] = (1 + p6m / 100) / (1 + p1m / 100) - 1 if p6m is not None and p1m is not None else None
        r["s_ret_1m"] = p1m / 100 if p1m is not None else None
        r["s_prox_52w_high"] = ratio(c, r.get("high_52w"))
        r["s_contraction"] = ratio(r.get("volatility_w_pct"), r.get("volatility_m_pct"))
        r["prox_3m_high"] = ratio(c, r.get("high_3m"))
        r["dist_sma20"] = ratio(c, r.get("sma20")) - 1 if ratio(c, r.get("sma20")) else None
        r["ep"] = ratio(r.get("net_income_ttm_try"), r.get("market_cap_try"))
        r["bp"] = pos_inverse(r.get("pb"))
        r["ebitda_ev"] = None if is_financial(r) else ratio(r.get("ebitda_ttm_try"), r.get("ev_try"))
        r["fcf_yield"] = None if is_financial(r) else ratio(r.get("fcf_try"), r.get("market_cap_try"))
        r["sales_ev"] = None if is_financial(r) else pos_inverse(r.get("ev_sales"))
        r["cfo_yield"] = None if is_financial(r) else pos_inverse(r.get("p_cfo"))
        r["peg_inv"] = None if is_financial(r) else pos_inverse(r.get("peg"))
        r["days_to_earnings"] = days_until(r.get("earnings_next"), today)
        r["days_to_exdiv"] = days_until(r.get("exdiv_next"), today)
        since = days_until(r.get("earnings_last"), today)
        r["days_since_earnings"] = -since if since is not None else None
        # consensus fields: need at least two analysts; surprises only while post-earnings drift is plausible
        n_analysts = r.get("rec_total") or 0
        target = r.get("target_median") or r.get("target_avg")
        r["analyst_upside"] = ratio(target, c) - 1 if n_analysts >= 2 and target and c else None
        r["consensus_mark"] = r.get("rec_mark") if n_analysts >= 2 else None
        fresh = r["days_since_earnings"] is not None and 0 <= r["days_since_earnings"] <= 75
        r["eps_surprise_fresh"] = r.get("eps_surprise_pct") if fresh else None
        r["rev_surprise_fresh"] = r.get("rev_surprise_pct") if fresh else None

    # --- eligibility (absolute liquidity floor may use the better history-based turnover)
    covered, excluded = [], []
    for r in rows:
        if r.get("close") is None:
            excluded.append({"ticker": r["ticker"], "reason": "fiyat verisi yok"})
            continue
        covered.append(r)
    eligible = []
    for r in covered:
        reason = exclusions.get(r["ticker"])
        tr = r.get("h_median_turnover_60d_try") or r.get("avg_turnover_30d_try")
        r["turnover_ref_try"] = tr
        if not reason and (tr is None or tr < args.min_turnover):
            reason = f"düşük likidite (< {args.min_turnover/1e6:.0f} mn {currency}/gün)" if tr is not None else "likidite verisi yok"
        if reason:
            excluded.append({"ticker": r["ticker"], "reason": reason})
        else:
            eligible.append(r)
    covered_tickers = [r["ticker"] for r in covered]

    # --- one consistent feature source per rank: history only when it covers >=90% of eligible names
    with_hist = sum(1 for r in eligible if (r.get("hist_bars") or 0) >= 130)
    use_hist = bool(eligible) and with_hist / len(eligible) >= 0.9
    for r in eligible:
        h = (lambda key: r.get(f"h_{key}")) if use_hist else (lambda key: None)
        pick = lambda hv, sv: hv if hv is not None else sv
        r["mom_12_1"] = pick(h("mom_12_1"), r["s_mom_12_1"])
        r["mom_6_1"] = pick(h("mom_6_1"), r["s_mom_6_1"])
        r["ret_1m"] = pick(h("ret_1m"), r["s_ret_1m"])
        r["prox_52w_high"] = pick(h("prox_52w_high"), r["s_prox_52w_high"])
        r["contraction"] = pick(h("atr_contraction"), r["s_contraction"])
        r["vol_rank_basis"] = pick(h("vol_60d_ann"), r.get("volatility_m_pct"))
        r["beta_used"] = pick(h("beta_hist"), r.get("beta_1y"))
        r["rs_1m"], r["rs_3m"], r["rs_6m"] = h("rs_1m"), h("rs_3m"), h("rs_6m")
        r["sma200_slope_20d"] = h("sma200_slope_20d")
        r["liq_rank_basis"] = r.get("h_median_turnover_60d_try") if use_hist else r.get("avg_turnover_30d_try")

    # --- lane scores on the eligible set
    E = eligible
    sector = lambda r: r.get("sector") or "?"
    nonfin = lambda f: (lambda r: None if is_financial(r) else f(r))
    L = {name: [None] * len(E) for name in LANES}
    rk = lambda key, higher=True, group=None: ranks_by_group(E, key, higher, group)

    liq = rk(lambda r: math.log(r["liq_rank_basis"]) if r.get("liq_rank_basis") else None)
    mom_parts = [rk(lambda r: r.get("mom_12_1")), rk(lambda r: r.get("mom_6_1")), rk(lambda r: r.get("perf_3m_pct")),
                 rk(lambda r: r.get("prox_52w_high")), rk(lambda r: r.get("rs_6m"))]
    smom_parts = [rk(lambda r: r.get("ret_1m")), rk(lambda r: r.get("perf_3m_pct")), rk(lambda r: r.get("rs_1m")),
                  rk(lambda r: r.get("prox_3m_high"))]
    rs_rank = rk(lambda r: r.get("mom_6_1"))
    val_parts = [rk(lambda r: r.get("ep"), True, sector), rk(lambda r: r.get("bp"), True, sector),
                 rk(lambda r: r.get("ebitda_ev"), True, sector), rk(lambda r: r.get("fcf_yield"), True, sector),
                 rk(lambda r: r.get("sales_ev"), True, sector), rk(lambda r: r.get("cfo_yield"), True, sector),
                 rk(lambda r: r.get("peg_inv")), rk(lambda r: r.get("div_yield_pct"))]
    exp_parts = [rk(lambda r: r.get("analyst_upside")), rk(lambda r: r.get("consensus_mark"), False),
                 rk(lambda r: r.get("eps_surprise_fresh")), rk(lambda r: r.get("rev_surprise_fresh"))]
    q_parts = [rk(lambda r: r.get("roe_pct")), rk(nonfin(lambda r: r.get("roic_pct"))),
               rk(nonfin(lambda r: r.get("op_margin_pct")), True, sector), rk(lambda r: r.get("net_margin_pct"), True, sector),
               rk(nonfin(lambda r: r.get("debt_to_equity")), False)]
    g_parts = [rk(lambda r: r.get("rev_growth_yoy_pct")), rk(lambda r: r.get("ni_growth_yoy_pct")),
               rk(lambda r: r.get("eps_growth_yoy_pct")), rk(lambda r: r.get("rev_growth_qoq_pct")),
               rk(lambda r: r.get("ni_growth_qoq_pct"))]
    lr_parts = [rk(lambda r: r.get("beta_used"), False), rk(lambda r: r.get("vol_rank_basis"), False),
                rk(lambda r: r.get("prox_52w_high"))]
    contraction = rk(lambda r: r.get("contraction"), False)
    breakout = rk(lambda r: r.get("prox_3m_high"))
    drop_1m = rk(lambda r: -r["ret_1m"] if r.get("ret_1m") is not None else None)
    low_rsi = rk(lambda r: r.get("rsi14"), False)

    for i, r in enumerate(E):
        L["liquidity"][i] = liq[i]
        L["momentum"][i] = avg([p[i] for p in mom_parts])[0]
        L["short_momentum"][i] = avg([p[i] for p in smom_parts])[0]
        L["value"][i] = avg([p[i] for p in val_parts])[0]
        qv = [p[i] for p in q_parts]
        if r.get("piotroski") is not None:
            qv.append(r["piotroski"] / 9)
        if not is_financial(r) and r.get("altman_z") is not None:
            z = r["altman_z"]
            qv.append(1.0 if z >= 3 else 0.5 if z >= 1.8 else 0.0)
        if not is_financial(r) and r.get("fcf_try") is not None:
            qv.append(1.0 if r["fcf_try"] > 0 else 0.0)
        L["quality"][i] = avg(qv)[0]
        L["growth"][i] = avg([p[i] for p in g_parts])[0]
        L["low_risk"][i] = avg([p[i] for p in lr_parts])[0]
        L["expectations"][i] = avg([p[i] for p in exp_parts])[0]

        # trend template (Minervini-style, paraphrased); count only evaluable criteria
        c, s50, s150, s200 = r.get("close"), r.get("sma50"), r.get("sma150"), r.get("sma200")
        crit = {}
        if c and s150 and s200:
            crit["fiyat>SMA150&SMA200"] = c > s150 and c > s200
        if s150 and s200:
            crit["SMA150>SMA200"] = s150 > s200
        if r.get("sma200_slope_20d") is not None:
            crit["SMA200_yukseliyor"] = r["sma200_slope_20d"] > 0
        if s50 and s150 and s200:
            crit["SMA50>SMA150&SMA200"] = s50 > s150 and s50 > s200
        if c and s50:
            crit["fiyat>SMA50"] = c > s50
        if c and r.get("low_52w"):
            crit["52h_dipten>%30"] = c >= 1.30 * r["low_52w"]
        if r.get("prox_52w_high") is not None:
            crit["52h_zirveye<%25"] = r["prox_52w_high"] >= 0.75
        if rs_rank[i] is not None:
            crit["RS_yuzdelik>=70"] = rs_rank[i] >= 0.70
        r["trend_passed"] = sum(1 for v in crit.values() if v)
        r["trend_checked"] = len(crit)
        r["trend_failed"] = [k for k, v in crit.items() if not v]
        L["trend"][i] = r["trend_passed"] / len(crit) if crit else None

        setup = [breakout[i], contraction[i]]
        if r.get("macd") is not None and r.get("macd_signal") is not None:
            setup.append(1.0 if r["macd"] > r["macd_signal"] else 0.0)
        if r.get("adx14") is not None:
            setup.append(min(r["adx14"] / 25, 1.0))
        if r.get("rsi14") is not None:
            setup.append(max(0.0, 1 - abs(r["rsi14"] - 60) / 25))
        if r.get("dist_sma20") is not None:
            d = r["dist_sma20"]
            setup.append(1.0 if d <= 0.05 else max(0.0, 1 - (d - 0.05) / 0.10))
        if r.get("rel_volume_10d") is not None:
            setup.append(min(r["rel_volume_10d"] / 1.5, 1.0))
        L["setup"][i] = avg(setup)[0]

        rev, _ = avg([drop_1m[i], low_rsi[i]])
        if rev is not None:
            gate = (L["quality"][i] is None or L["quality"][i] >= 0.4) and (not s200 or not c or c >= 0.85 * s200)
            L["reversal"][i] = rev if gate else rev * 0.3

        cat, cat_known = 0.0, False
        dte = r.get("days_to_earnings")
        if dte is not None:
            cat_known = True
            if 0 <= dte <= horizon_days:
                cat += 0.4
        events = kap_by_ticker.get(r["ticker"], [])
        if kap_loaded:
            cat_known = True
            for cls, w in POSITIVE_KAP.items():
                hits = sum(1 for e in events if e.get("event_class") == cls)
                cat += min(2, hits) * w
        L["catalyst"][i] = min(1.0, cat) if cat_known else None

        # risk flags
        flags = []
        if r.get("float_pct") is not None and r["float_pct"] < 15:
            flags.append("DUSUK_HALKA_ACIKLIK")
        p3, p1 = r.get("perf_3m_pct"), r.get("perf_1m_pct")
        if (p3 is not None and p3 > 100) or (p1 is not None and p1 > 50):
            flags.append("PARABOLIK")
        if (r.get("h_limit_up_20d") or 0) >= 3:
            flags.append("TAVAN_SERISI")
        if r.get("h_spike_crash"):
            flags.append("POMPA_COKUS")
        elif r.get("h_spike_crash") is None and r.get("high_52w") and r.get("sma200") and c:
            if r["high_52w"] > 2.5 * r["sma200"] and c < 0.5 * r["high_52w"]:
                flags.append("POMPA_COKUS_SUPHESI")
        if (not use_hist and r.get("s_prox_52w_high") is not None and r["s_prox_52w_high"] < 0.35
                and (r.get("perf_1y_pct") or 0) > 50):
            flags.append("VERI_UYUMSUZ")
        if r.get("prox_52w_high") is not None and r["prox_52w_high"] < 0.5:
            flags.append("DERIN_DUSUS")
        if r.get("pb") is not None and r["pb"] < 0:
            flags.append("NEGATIF_OZKAYNAK")
        if r.get("net_income_ttm_try") is not None and r["net_income_ttm_try"] < 0:
            flags.append("ZARAR")
        if not is_financial(r) and r.get("altman_z") is not None and r["altman_z"] < 1.8:
            flags.append("ALTMAN_RISK")
        if not is_financial(r) and r.get("debt_to_equity") is not None and r["debt_to_equity"] > 2:
            flags.append("YUKSEK_KALDIRAC")
        if dte is not None and 0 <= dte <= 7:
            flags.append("BILANCO_YAKIN")
        if r.get("days_to_exdiv") is not None and 0 <= r["days_to_exdiv"] <= 10:
            flags.append("TEMETTU_YAKIN")
        if (r.get("rec_total") or 0) >= 3 and r.get("target_avg") and c and c > 1.05 * r["target_avg"]:
            flags.append("HEDEF_USTU")
        if (r.get("rec_total") or 0) >= 3 and r.get("rec_mark") is not None and r["rec_mark"] >= 2.25:
            flags.append("ANALIST_ZAYIF")
        if r.get("pe_ttm") is None and r.get("pb") is None and r.get("roe_pct") is None:
            flags.append("TEMEL_VERI_YOK")
        for e in events:
            flag = RISK_KAP.get(e.get("event_class"))
            if flag and flag not in flags:
                flags.append(flag)
        if cb_counts.get(r["ticker"], 0) >= cb_cut:
            flags.append("DEVRE_KESICI_SIK")
        r["flags"] = flags

    vol_values = [r.get("vol_rank_basis") for r in E]
    vol_cut = sorted(v for v in vol_values if v)[int(0.9 * len([v for v in vol_values if v])) - 1] if any(vol_values) else None
    total_w = sum(weights.values())
    final_rows = []
    for i, r in enumerate(E):
        if vol_cut and vol_values[i] and vol_values[i] >= vol_cut:
            r["flags"].append("YUKSEK_VOLATILITE")
        for lane in LANES:
            r[f"lane_{lane}"] = L[lane][i]
        known = sum(w for lane, w in weights.items() if L[lane][i] is not None)
        num = sum(w * (L[lane][i] if L[lane][i] is not None else MISSING_OVERRIDE.get(lane, args.missing_lane_score))
                  for lane, w in weights.items())
        r["coverage"] = known / total_w if total_w else 0
        r["composite"] = num / total_w if total_w and known else None
        if exclude_flags and set(r["flags"]) & exclude_flags:
            excluded.append({"ticker": r["ticker"], "reason": "risk bayrağı: " + ",".join(sorted(set(r["flags"]) & exclude_flags))})
            continue
        final_rows.append(r)
    final_rows.sort(key=lambda r: (r["composite"] is None, -(r["composite"] or 0)))
    for pos, r in enumerate(final_rows, 1):
        r["rank"] = pos

    # --- shortlist: composite leaders + lane specialists (multi-lane, not one blended score)
    shortlist, why = [], {}
    for r in final_rows[: max(8, args.top // 2)]:
        shortlist.append(r["ticker"]); why.setdefault(r["ticker"], []).append("bileşik")
    lane_leaders = {}
    for lane in [l for l in LANES if l != "liquidity" and (weights.get(l) or l in ("reversal", "value", "quality", "trend"))]:
        ordered = sorted([r for r in final_rows if r.get(f"lane_{lane}") is not None], key=lambda r: -r[f"lane_{lane}"])
        lane_leaders[lane] = [r["ticker"] for r in ordered[:5]]
        for r in ordered[:3]:
            if r["ticker"] not in shortlist:
                shortlist.append(r["ticker"])
            why.setdefault(r["ticker"], []).append(lane)
    shortlist = shortlist[: max(args.top, 12)]

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    index_cols = [k for k in (raw_rows[0].keys() if raw_rows else []) if k.startswith("in_")]
    cols = ["rank", "ticker", "name", "sector", "close", "composite", "coverage"] + [f"lane_{l}" for l in LANES] + [
        "flags", "turnover_ref_try", "market_cap_try", "pe_ttm", "pb", "ev_ebitda", "ev_sales", "p_cfo", "peg", "div_yield_pct",
        "roe_pct", "roic_pct", "net_margin_pct",
        "rev_growth_yoy_pct", "ni_growth_yoy_pct", "piotroski", "altman_z", "debt_to_equity", "perf_1m_pct", "perf_3m_pct",
        "perf_6m_pct", "perf_1y_pct", "mom_12_1", "mom_6_1", "prox_52w_high", "rs_3m", "rs_6m", "rsi14", "adx14",
        "contraction", "vol_rank_basis", "beta_used", "h_atr_pct", "h_maxdd_1y", "h_limit_up_20d", "h_updown_volume_50d", "trend_passed",
        "trend_checked", "trend_failed", "analyst_upside", "target_median", "target_avg", "rec_mark", "rec_total",
        "eps_surprise_pct", "rev_surprise_pct", "days_since_earnings", "days_to_earnings", "earnings_next", "exdiv_next",
        "days_to_exdiv", "float_pct"] + index_cols + ["hist_bars"]
    ranked_path = write_csv(out / "scan_ranked.csv", final_rows, cols)
    write_csv(out / "scan_excluded.csv", excluded, ["ticker", "reason"])
    excluded_covered = [e for e in excluded if e["ticker"] in set(covered_tickers)]
    total = len(membership)
    ledger = {
        "name": f"{market_label} {uni if uni != 'ALL' else f'ALL (TradingView {market} stocks)'}",
        "mandate": f"horizon {horizon_days} days, profile {profile}, liquidity floor {args.min_turnover:,.0f} {currency}/day",
        "membership_source": snapshot_meta.get("source", "snapshot.csv"),
        "membership_rows": membership,
        "membership_artifact_sha256": sha256_file(args.snapshot),
        "source_timestamp": snapshot_meta.get("fetched_at", "unknown"),
        "data_cutoff": snapshot_meta.get("fetched_at", iso(now_trt())),
        "total_count": total,
        "covered_count": len(covered_tickers),
        "covered_tickers": covered_tickers,
        "eligible_count": len(final_rows),
        "excluded_count": len(excluded_covered),
        "coverage_ratio": round(len(covered_tickers) / total, 4) if total else 0,
        "broad_request": uni in ("ALL", "XUTUM"),
        "selection_claim": "best_within_covered_universe",
        "screen_method": f"bist_scan.py multi-lane percentile screen; profile {profile}; weights {weights}",
        "screen_artifact": ranked_path.name,
        "screen_artifact_sha256": sha256_file(ranked_path),
        "exclusions": excluded_covered,
    }
    seed = {"universe": ledger,
            "screened": [{"ticker": r["ticker"], "composite": r["composite"], "flags": r["flags"]} for r in final_rows],
            "shortlisted": [{"ticker": t, "why": why.get(t, [])} for t in shortlist],
            "finalists": [], "final_recommendations": [], "graveyard": [],
            "note": "Seed for validate_funnel.py. Fill finalists/final_recommendations only after full diligence."}
    write_json(out / "funnel_seed.json", seed)

    top = final_rows[: args.top]
    lines = [f"# {market_label} tarama — {profile.upper()} vade ({horizon_days} gün)", "",
             f"- Veri zamanı: {ledger['data_cutoff']} · kaynak: {ledger['membership_source']}",
             f"- Evren: {total} → kapsanan {len(covered_tickers)} → uygun {len(final_rows)} · dışlanan {len(excluded_covered)} (likidite tabanı {args.min_turnover/1e6:.0f} mn {currency}/gün)",
             f"- Fiyat geçmişi: {with_hist}/{len(eligible)} hissede · sıralamada {'geçmiş verisi' if use_hist else 'anlık görünüm verisi (tutarlılık için)'} · KAP akışı: {'var' if kap_loaded else 'yok'} · Endeks karşılaştırması: {'var' if bench and use_hist else 'yok'}",
             f"- Ağırlıklar (araştırma önceliği, doğrulanmış alfa değil): {', '.join(f'{k} {v:.2f}' for k, v in weights.items())}",
             "", "> Bu liste **ADAY** listesidir, al tavsiyesi değildir. Her aday temel + teknik + haber + risk incelemesinden ve kırmızı takım denetiminden geçmeden işlem planına dönüşmez.",
             "", "## Bileşik sıralama (ilk %d)" % len(top), ""]
    view = [{"#": r["rank"], "Kod": r["ticker"], "Sektör": (r.get("sector") or "")[:22], "Fiyat": r.get("close"),
             "Skor": r.get("composite"), "Trend": f"{r.get('trend_passed')}/{r.get('trend_checked')}",
             "1A%": r.get("perf_1m_pct"), "3A%": r.get("perf_3m_pct"), "F/K": r.get("pe_ttm"), "PD/DD": r.get("pb"),
             "ROE%": r.get("roe_pct"),
             "Hedef↑%": r["analyst_upside"] * 100 if r.get("analyst_upside") is not None else None,
             "Anl.": int(r["rec_total"]) if r.get("rec_total") else None,
             "Bayraklar": ",".join(r.get("flags") or [])} for r in top]
    lines.append(md_table(view, list(view[0].keys()) if view else ["#"]))
    lines += ["", "## Şerit liderleri", ""]
    for lane, tickers in lane_leaders.items():
        lines.append(f"- **{lane}**: {', '.join(tickers)}")
    lines += ["", "## Orta derinlik inceleme listesi (ADAY)", "",
              ", ".join(f"{t} ({'/'.join(why.get(t, []))})" for t in shortlist),
              "", "## Bayrak sözlüğü", "",
              "PARABOLIK: 3 ayda >%100 veya 1 ayda >%50 · TAVAN_SERISI: 20 günde ≥3 tavan · DUSUK_HALKA_ACIKLIK: <%15 · "
              "BILANCO_YAKIN: ≤7 gün · TEMETTU_YAKIN: hak kullanımı ≤10 gün (fiyat temettü kadar düşer) · HEDEF_USTU: fiyat ortalama analist hedefinin %5+ üstünde (≥3 analist) · "
              "ANALIST_ZAYIF: konsensüs 'tut'tan zayıf (≥3 analist) · YUKSEK_VOLATILITE: evrenin üst %10'u · KAP akışından: SPK_YASAK_LISTESI (≤15 hisselik hedefli liste), VBTS_TEDBIR, DEVRE_KESICI_SIK (evrenin en sık %10'u, ≥5 kez), TIPE_DONUSUM (arz baskısı), BEDELLI_SULANMA, FINANSAL_SIKINTI, HUKUKI_RISK · "
              "ZARAR / NEGATIF_OZKAYNAK / ALTMAN_RISK / YUKSEK_KALDIRAC: temel risk · POMPA_COKUS: 6 ayda ≥2,5 kat yükselip zirvenin yarısının altına inme (manipülasyon izi) · VERI_UYUMSUZ: 52h zirve ile 1y getiri çelişiyor (düzeltilmemiş bedelsiz şüphesi; geçmiş veriyle doğrula).",
              "", "Beklenti şeridi: analist medyan hedef getirisi (≥2 analist), konsensüs notu, son 75 günde açıklanan bilanço sürprizi. Analist kapsamı dar; kapsanmayan hisse bu şeritte nötr (0,5) sayılır. Hedef fiyatlar görüştür, kanıt değildir.",
              "", "Dosyalar: scan_ranked.csv (tüm uygun hisseler ve şerit puanları), scan_excluded.csv, funnel_seed.json (validate_funnel.py için evren defteri)."]
    (out / "scan_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK market={market} profile={profile} horizon={horizon_days}d universe={total} covered={len(covered_tickers)} eligible={len(final_rows)} excluded={len(excluded_covered)}")
    print(f"top: {', '.join(r['ticker'] for r in top[:10])}")
    print(f"shortlist ({len(shortlist)}): {', '.join(shortlist)}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
