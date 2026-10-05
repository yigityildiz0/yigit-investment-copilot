#!/usr/bin/env python3
"""Historical base rates: what happened after a setup, compared with what happened on average.

For every stock history in a folder (price_history.py CSVs) the script samples dates point-in-time,
checks which setups were true using only data up to that date, and measures the forward return over
the horizon. It reports each setup against the unconditional baseline of the same universe and
period, by year, and the stocks that match each setup today.

Setups (close-only, so spark histories work):
  trend_template     price > SMA50 > SMA150 > SMA200, SMA200 rising 20 bars, >=30% above 52w low, within 25% of 52w high
  near_52w_high      close >= 95% of the 252-bar high
  breakout_55        close above the previous 55-bar closing high
  mom_top_decile     12-1 month momentum in the top decile of that date's cross-section
  oversold_uptrend   RSI14 < 30 while close > SMA200
  drop_1m            21-bar return <= -15% (mean-reversion test)
  limit_up_streak    >=3 daily gains >= 9.5% in the last 20 bars (BIST tavan serisi)

Usage:
  python base_rates.py --history-dir ~/.cache/yigit-investment-copilot/spark2y --horizon-days 90 --out br
  python base_rates.py --history-dir hist5y --benchmark hist5y/XU100.csv --horizon-days 30 --step 5 --out br

Caveats printed with every run: survivorship (only today's listed names), overlapping windows
(neighbouring samples share most of their future), regime dependence, costs not deducted.
"""

import argparse
import csv
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SETUPS = ["trend_template", "near_52w_high", "breakout_55", "mom_top_decile", "oversold_uptrend", "drop_1m", "limit_up_streak"]
SKIP = {"XU100", "XU030", "XU050", "XUTUM", "USDTRY", "EURTRY", "GOLD", "BRENT", "SPX", "NDX", "VIX", "DXY", "US10Y"}
TRT = timezone(timedelta(hours=3))


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            if str(r.get("complete", "1")).strip() in {"0", "false", "False"}:
                continue
            try:
                v = float(r.get("adj_close") or r.get("close"))
            except (TypeError, ValueError):
                continue
            if v > 0:
                rows.append((r["date"][:10], v))
    rows.sort()
    return rows


def rolling_mean(values, n):
    out, total = [None] * len(values), 0.0
    for i, v in enumerate(values):
        total += v
        if i >= n:
            total -= values[i - n]
        if i >= n - 1:
            out[i] = total / n
    return out


def rolling_extreme(values, n, use_max=True):
    out, dq = [None] * len(values), deque()
    better = (lambda a, b: a >= b) if use_max else (lambda a, b: a <= b)
    for i, v in enumerate(values):
        while dq and better(v, values[dq[-1]]):
            dq.pop()
        dq.append(i)
        if dq[0] <= i - n:
            dq.popleft()
        if i >= n - 1:
            out[i] = values[dq[0]]
    return out


def rsi(values, n=14):
    out = [None] * len(values)
    if len(values) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / n, losses / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(values)):
        d = values[i] - values[i - 1]
        ag = (ag * (n - 1) + max(d, 0.0)) / n
        al = (al * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def features(series, bars, step, warmup=260, calendar=None):
    """Point-in-time setup flags and forward returns for sampled indices of one stock. With a shared
    calendar (date -> global index) every stock is sampled on the same dates, so cross-sections line up."""
    dates = [d for d, _ in series]
    v = [x for _, x in series]
    n = len(v)
    s50, s150, s200 = rolling_mean(v, 50), rolling_mean(v, 150), rolling_mean(v, 200)
    hi252, lo252 = rolling_extreme(v, 252, True), rolling_extreme(v, 252, False)
    hi55 = rolling_extreme(v, 55, True)
    r14 = rsi(v)
    out = []
    for i in range(warmup, n):
        if calendar is not None and calendar.get(dates[i], 1) % step:
            continue
        if calendar is None and (i - warmup) % step:
            continue
        fwd = v[i + bars] / v[i] - 1 if i + bars < n else None
        f = {"date": dates[i], "i": i, "fwd": fwd, "end_date": dates[i + bars] if i + bars < n else None}
        c = v[i]
        f["trend_template"] = bool(s50[i] and s150[i] and s200[i] and s200[i - 20] and hi252[i] and lo252[i]
                                   and c > s50[i] > s150[i] > s200[i] and s200[i] > s200[i - 20]
                                   and c >= 1.3 * lo252[i] and c >= 0.75 * hi252[i])
        f["near_52w_high"] = bool(hi252[i] and c >= 0.95 * hi252[i])
        f["breakout_55"] = bool(hi55[i - 1] and c > hi55[i - 1])
        f["oversold_uptrend"] = bool(r14[i] is not None and r14[i] < 30 and s200[i] and c > s200[i])
        f["drop_1m"] = c / v[i - 21] - 1 <= -0.15
        ups = sum(1 for k in range(i - 19, i + 1) if v[k] / v[k - 1] - 1 >= 0.095)
        f["limit_up_streak"] = ups >= 3
        f["mom_12_1"] = v[i - 21] / v[i - 252] - 1 if i >= 252 else None
        out.append(f)
    return out


def quantile(sorted_values, q):
    if not sorted_values:
        return None
    pos = (len(sorted_values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def summarize(samples, baseline_by_date, bars, step):
    rets = sorted(s["fwd"] for s in samples)
    if not rets:
        return {"n": 0}
    by_date = {}
    for s in samples:
        by_date.setdefault(s["date"], []).append(s["fwd"])
    # same-date excess over the baseline removes market-wide moves; overlap inflates t, so deflate it
    diffs = [sum(v) / len(v) - baseline_by_date[d] for d, v in by_date.items() if d in baseline_by_date]
    mean_diff = sum(diffs) / len(diffs) if diffs else None
    t = None
    if len(diffs) > 2:
        m = mean_diff
        sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / (len(diffs) - 1))
        if sd > 0:
            t = m / (sd / math.sqrt(len(diffs))) / math.sqrt(max(1.0, bars / step))
    years = {}
    for s in samples:
        years.setdefault(s["date"][:4], []).append(s["fwd"])
    return {"n": len(rets), "stocks": len({s["code"] for s in samples}), "signal_dates": len(by_date),
            "mean_pct": sum(rets) / len(rets) * 100, "median_pct": quantile(rets, 0.5) * 100,
            "hit_rate_pct": sum(1 for r in rets if r > 0) / len(rets) * 100,
            "p10_pct": quantile(rets, 0.1) * 100, "p90_pct": quantile(rets, 0.9) * 100,
            "loss_beyond_10_pct": sum(1 for r in rets if r <= -0.10) / len(rets) * 100,
            "same_date_excess_vs_baseline_pct": mean_diff * 100 if mean_diff is not None else None,
            "overlap_adjusted_t": t,
            "by_year_mean_pct": {y: sum(v) / len(v) * 100 for y, v in sorted(years.items())},
            "by_year_n": {y: len(v) for y, v in sorted(years.items())}}


def fmt(x, d=1):
    return "—" if x is None else f"{x:,.{d}f}"


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history-dir", type=Path, required=True)
    ap.add_argument("--horizon-days", type=int, default=90, help="calendar days; converted to trading bars (x252/365)")
    ap.add_argument("--step", type=int, default=5, help="sample every N bars (5 = weekly)")
    ap.add_argument("--benchmark", type=Path, help="benchmark CSV (e.g. XU100.csv): adds benchmark forward return")
    ap.add_argument("--tickers", nargs="*", help="limit to these codes")
    ap.add_argument("--min-bars", type=int, default=300)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    bars = max(1, round(a.horizon_days * 252 / 365))
    files = sorted(p for p in a.history_dir.glob("*.csv") if not p.name.startswith("_"))
    if a.tickers:
        wanted = {t.upper() for t in a.tickers}
        files = [p for p in files if p.stem.upper() in wanted]
    all_samples, current, skipped = [], {k: [] for k in SETUPS}, 0
    first_date, last_date = None, None
    loaded = []
    for p in files:
        code = p.stem.upper()
        if code in SKIP:
            continue
        series = load(p)
        if len(series) < max(a.min_bars, 260 + bars):
            skipped += 1
            continue
        loaded.append((code, series))
    calendar = {d: i for i, d in enumerate(sorted({d for _, series in loaded for d, _ in series}))}
    for code, series in loaded:
        feats = features(series, bars, a.step, calendar=calendar)
        last = features(series, bars, 1, warmup=len(series) - 1)
        for f in feats:
            f["code"] = code
        all_samples.extend(f for f in feats if f["fwd"] is not None)
        if last:
            for k in SETUPS:
                if k != "mom_top_decile" and last[-1].get(k):
                    current[k].append(code)
            last[-1]["code"] = code
            all_samples_last = last[-1]
            all_samples_last["_current"] = True
            current.setdefault("_mom_now", []).append((code, all_samples_last.get("mom_12_1")))
        first_date = min(first_date or series[0][0], series[0][0])
        last_date = max(last_date or series[-1][0], series[-1][0])
    if not all_samples:
        raise SystemExit("no usable histories: need at least min-bars + horizon bars per stock (use a 2y+ range)")
    # cross-sectional momentum decile per date (needs >=30 names that date)
    by_date = {}
    for s in all_samples:
        if s.get("mom_12_1") is not None:
            by_date.setdefault(s["date"], []).append(s["mom_12_1"])
    cut = {d: sorted(v)[int(0.9 * len(v))] for d, v in by_date.items() if len(v) >= 30}
    for s in all_samples:
        s["mom_top_decile"] = bool(s.get("mom_12_1") is not None and s["date"] in cut and s["mom_12_1"] >= cut[s["date"]])
    now_mom = [(c, m) for c, m in current.pop("_mom_now", []) if m is not None]
    if len(now_mom) >= 30:
        threshold = sorted(m for _, m in now_mom)[int(0.9 * len(now_mom))]
        current["mom_top_decile"] = sorted(c for c, m in now_mom if m >= threshold)
    bench_fwd = {}
    if a.benchmark and a.benchmark.exists():
        b = load(a.benchmark)
        idx = {d: i for i, (d, _) in enumerate(b)}
        for s in all_samples:
            i = idx.get(s["date"])
            if i is not None and i + bars < len(b):
                bench_fwd[s["date"]] = b[i + bars][1] / b[i][1] - 1
    baseline_by_date = {}
    for s in all_samples:
        baseline_by_date.setdefault(s["date"], []).append(s["fwd"])
    baseline_by_date = {d: sum(v) / len(v) for d, v in baseline_by_date.items()}
    results = {"baseline": summarize(all_samples, baseline_by_date, bars, a.step)}
    for k in SETUPS:
        results[k] = summarize([s for s in all_samples if s.get(k)], baseline_by_date, bars, a.step)
    if bench_fwd:
        bm = [bench_fwd[d] for d in sorted(bench_fwd)]
        results["benchmark_same_dates_mean_pct"] = sum(bm) / len(bm) * 100
    meta = {"generated_at": datetime.now(TRT).isoformat(timespec="seconds"), "history_dir": str(a.history_dir),
            "stocks": len({s["code"] for s in all_samples}), "skipped_short_histories": skipped,
            "period": f"{first_date} → {last_date}", "horizon_days": a.horizon_days, "horizon_bars": bars, "step_bars": a.step,
            "caveats": ["survivorship: only currently listed names are in the folder, delisted losers are missing",
                        "overlapping windows: neighbouring samples share most of their future; t is deflated by sqrt(horizon/step) and is still rough",
                        "regime dependence: a 2-year window is one or two regimes; check by-year stability",
                        "costs, slippage, taxes and limit-day execution are not deducted",
                        "close-only setups; volume, fundamentals and news are ignored"]}
    a.out.mkdir(parents=True, exist_ok=True)
    import json
    (a.out / "base_rates.json").write_text(json.dumps({"meta": meta, "results": results, "current_matches": current},
                                                     ensure_ascii=False, indent=2), encoding="utf-8")
    base = results["baseline"]
    lines = [f"# Taban oranları — {a.horizon_days} gün ({bars} işlem günü) sonrası getiri", "",
             f"- Veri: {meta['stocks']} hisse, {meta['period']}, her {a.step} işlem gününde bir örnek · üretim {meta['generated_at']}",
             f"- Taban (koşulsuz): ortalama %{fmt(base['mean_pct'])} · medyan %{fmt(base['median_pct'])} · pozitif oran %{fmt(base['hit_rate_pct'], 0)} · "
             f"P10 %{fmt(base['p10_pct'])} / P90 %{fmt(base['p90_pct'])} · n={base['n']}"
             + (f" · endeks aynı tarihlerde %{fmt(results['benchmark_same_dates_mean_pct'])}" if "benchmark_same_dates_mean_pct" in results else ""),
             "", "| Kurulum | n | hisse | ort.% | medyan% | pozitif% | P10% | P90% | ≤−10% olasılık | aynı gün tabana göre fark% | kaba t | şu an eşleşen |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in SETUPS:
        r = results[k]
        if not r.get("n"):
            lines.append(f"| {k} | 0 | | | | | | | | | | {len(current.get(k, []))} |")
            continue
        lines.append(f"| {k} | {r['n']} | {r['stocks']} | {fmt(r['mean_pct'])} | {fmt(r['median_pct'])} | {fmt(r['hit_rate_pct'], 0)} | "
                     f"{fmt(r['p10_pct'])} | {fmt(r['p90_pct'])} | {fmt(r['loss_beyond_10_pct'], 0)} | "
                     f"{fmt(r['same_date_excess_vs_baseline_pct'])} | {fmt(r['overlap_adjusted_t'], 2)} | {len(current.get(k, []))} |")
    lines += ["", "## Yıllara göre ortalama (%; istikrar kontrolü)", ""]
    years = sorted({y for r in results.values() if isinstance(r, dict) for y in r.get("by_year_mean_pct", {})})
    lines.append("| Kurulum | " + " | ".join(years) + " |")
    lines.append("|---|" + "|".join("---" for _ in years) + "|")
    for k in ["baseline"] + SETUPS:
        r = results[k]
        lines.append(f"| {k} | " + " | ".join(fmt(r.get('by_year_mean_pct', {}).get(y)) for y in years) + " |")
    lines += ["", "## Bugün eşleşen hisseler", ""]
    for k in SETUPS:
        names = current.get(k, [])
        lines.append(f"- **{k}** ({len(names)}): {', '.join(names[:40])}{' …' if len(names) > 40 else ''}")
    lines += ["", "## Nasıl okunur", "",
              "- Bir kurulum ancak **aynı gün tabana göre farkı** pozitif, **kaba t ≥ 2** ve **yıllara göre işareti tutarlı** ise tarihsel bir üstünlük adayıdır; yine de maliyet ve hayatta kalma yanlılığı düşülmemiştir.",
              "- Taban oranı bir tahmin başlangıcıdır (dış görünüm): hisseye özel hikâyeden önce bu dağılımı yaz, sonra kanıtla ayarla.",
              "- Uyarılar: " + "; ".join(meta["caveats"]) + "."]
    (a.out / "base_rates.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {meta['stocks']} stocks, {base['n']} samples, horizon {bars} bars -> {a.out}")
    for k in SETUPS:
        r = results[k]
        if r.get("n"):
            print(f"  {k:<17} n={r['n']:>6} mean {r['mean_pct']:+6.1f}% vs same-day base {r['same_date_excess_vs_baseline_pct'] or 0:+5.1f}% t≈{r['overlap_adjusted_t'] or 0:+.2f} now {len(current.get(k, []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
