#!/usr/bin/env python3
"""Walk-forward, cost-aware test of simple cross-sectional BIST ranking signals.

For each fold the script picks the best (signal, top-k) combination on the preceding training
window (net Sharpe), then applies it unchanged to the next test window. Only the out-of-sample
test periods are stitched into the reported track record. It also reports what a naive full-sample
optimisation would have shown, so the overfitting gap is visible, plus the Deflated Sharpe
probability for the number of combinations tried.

Built-in signals (higher = better): mom_12_1, mom_6_1, mom_3_0, rev_1m (short-term reversal),
prox_52w (52-week-high proximity), lowvol_60, trend_200, combo_mom_prox.

Known biases you must disclose with any result:
- survivorship: the universe is today's listed stocks (delisted names are missing);
- no historical liquidity filter when histories are close-only (spark mode);
- corporate-action repairs are approximate; costs are assumptions.

Usage:
  python walkforward_backtest.py --history-dir hist5y --benchmark hist5y/XU100.csv --out wf \
      --rebalance 21 --train 504 --test 126 --top-k 5 10 20 --cost-bps 25
"""

import argparse
import csv
import json
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strategy_stats import moments, summarize  # noqa: E402

SIGNALS = ["mom_12_1", "mom_6_1", "mom_3_0", "rev_1m", "prox_52w", "lowvol_60", "trend_200", "combo_mom_prox"]
LOOKBACK = {"mom_12_1": 253, "mom_6_1": 127, "mom_3_0": 64, "rev_1m": 22, "prox_52w": 252, "lowvol_60": 61,
            "trend_200": 200, "combo_mom_prox": 252}


def load_prices(path):
    out = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            if str(r.get("complete", "1")).strip() in ("0", "false"):
                continue
            try:
                v = float(r.get("adj_close") or r["close"])
            except (TypeError, ValueError, KeyError):
                continue
            if v > 0:
                out[r["date"]] = v
    return out


def pct_rank(scores):
    items = sorted(scores.items(), key=lambda kv: kv[1])
    n = len(items)
    return {t: (i / (n - 1) if n > 1 else 0.5) for i, (t, _) in enumerate(items)}


class Panel:
    def __init__(self, history_dir, benchmark, universe=None, start=None, end=None):
        bench = load_prices(benchmark)
        self.dates = [d for d in sorted(bench) if (not start or d >= start) and (not end or d <= end)]
        self.bench = [bench[d] for d in self.dates]
        index = {d: i for i, d in enumerate(self.dates)}
        self.prices, self.last_obs = {}, {}
        files = sorted(history_dir.glob("*.csv"))
        wanted = {u.upper() for u in universe} if universe else None
        bench_name = Path(benchmark).stem.upper()
        for f in files:
            t = f.stem.upper()
            if t == bench_name or (wanted and t not in wanted) or t in ("USDTRY", "EURTRY", "GOLD", "BRENT"):
                continue
            raw = load_prices(f)
            arr, obs, last, last_i = [None] * len(self.dates), [None] * len(self.dates), None, None
            for i, d in enumerate(self.dates):
                if d in raw:
                    last, last_i = raw[d], i
                arr[i] = last
                obs[i] = last_i
            if sum(1 for v in arr if v is not None) > 150:
                self.prices[t] = arr
                self.last_obs[t] = obs
        self.logret = {}
        self.cum_p = {}
        for t, arr in self.prices.items():
            lr, cp, run, run_p = [0.0] * len(arr), [0.0] * (len(arr) + 1), 0.0, 0.0
            sq = [0.0] * (len(arr) + 1)
            for i in range(len(arr)):
                if i > 0 and arr[i] and arr[i - 1]:
                    lr[i] = math.log(arr[i] / arr[i - 1])
                cp[i + 1] = cp[i] + (arr[i] or 0.0)
                sq[i + 1] = sq[i] + lr[i] * lr[i]
            self.logret[t] = (lr, self._prefix(lr), sq)
            self.cum_p[t] = cp
        self.cache = {}

    @staticmethod
    def _prefix(values):
        out = [0.0] * (len(values) + 1)
        for i, v in enumerate(values):
            out[i + 1] = out[i] + v
        return out

    def eligible(self, t, i, need):
        arr, obs = self.prices[t], self.last_obs[t]
        return (i - need >= 0 and arr[i - need] is not None and arr[i] is not None and obs[i] is not None and i - obs[i] <= 5)

    def raw_signal(self, name, t, i):
        p = self.prices[t]
        if name == "mom_12_1":
            return p[i - 21] / p[i - 252] - 1
        if name == "mom_6_1":
            return p[i - 21] / p[i - 126] - 1
        if name == "mom_3_0":
            return p[i] / p[i - 63] - 1
        if name == "rev_1m":
            return -(p[i] / p[i - 21] - 1)
        if name == "prox_52w":
            return p[i] / max(v for v in p[i - 251:i + 1] if v is not None)
        if name == "lowvol_60":
            _, pre, sq = self.logret[t]
            s1, s2, n = pre[i + 1] - pre[i - 59], sq[i + 1] - sq[i - 59], 60
            var = max(0.0, (s2 - s1 * s1 / n) / (n - 1))
            return -math.sqrt(var)
        if name == "trend_200":
            cp = self.cum_p[t]
            return p[i] / ((cp[i + 1] - cp[i - 199]) / 200) - 1
        raise KeyError(name)

    def scores(self, name, i):
        key = (name, i)
        if key in self.cache:
            return self.cache[key]
        if name == "combo_mom_prox":
            a, b = self.scores("mom_6_1", i), self.scores("prox_52w", i)
            ra, rb = pct_rank(a), pct_rank(b)
            out = {t: (ra[t] + rb[t]) / 2 for t in ra if t in rb}
        else:
            need = LOOKBACK[name]
            out = {}
            for t in self.prices:
                if self.eligible(t, i, need):
                    try:
                        out[t] = self.raw_signal(name, t, i)
                    except (TypeError, ZeroDivisionError, ValueError):
                        pass
        self.cache[key] = out
        return out


def run_strategy(panel, signal, k, start, end, rebalance, delay, cost):
    periods, prev = [], {}
    i = start
    while i + delay + 1 < end:
        entry = i + delay
        exit_ = min(entry + rebalance, end - 1)
        if exit_ <= entry:
            break
        sc = panel.scores(signal, i)
        picks = [t for t, _ in sorted(sc.items(), key=lambda kv: -kv[1])[:k]]
        if not picks:
            i += rebalance
            continue
        rets = [panel.prices[t][exit_] / panel.prices[t][entry] - 1 for t in picks if panel.prices[t][entry] and panel.prices[t][exit_]]
        gross = sum(rets) / len(rets) if rets else 0.0
        w = {t: 1 / len(picks) for t in picks}
        turnover = sum(abs(w.get(t, 0) - prev.get(t, 0)) for t in set(w) | set(prev))
        net = gross - turnover * cost
        bench = panel.bench[exit_] / panel.bench[entry] - 1
        universe = [panel.prices[t][exit_] / panel.prices[t][entry] - 1 for t in sc if panel.prices[t][entry] and panel.prices[t][exit_]]
        periods.append({"date": panel.dates[entry], "exit": panel.dates[exit_], "signal": signal, "k": k,
                        "gross": gross, "net": net, "turnover": turnover, "bench": bench,
                        "ew_universe": sum(universe) / len(universe) if universe else None, "picks": picks})
        prev = w
        i += rebalance
    return periods


def sharpe(periods):
    x = [p["net"] for p in periods]
    if len(x) < 3:
        return -9e9
    m, sd, _, _ = moments(x)
    return m / sd if sd else -9e9



def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    _utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history-dir", type=Path, required=True)
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--universe-file", type=Path)
    ap.add_argument("--signals", nargs="*", default=SIGNALS, choices=SIGNALS)
    ap.add_argument("--top-k", nargs="*", type=int, default=[5, 10, 20])
    ap.add_argument("--rebalance", type=int, default=21)
    ap.add_argument("--delay", type=int, default=1, help="bars between signal close and entry close")
    ap.add_argument("--train", type=int, default=504)
    ap.add_argument("--test", type=int, default=126)
    ap.add_argument("--cost-bps", type=float, default=25, help="all-in cost per side in basis points")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    universe = [l.strip() for l in a.universe_file.read_text(encoding="utf-8").splitlines() if l.strip()] if a.universe_file else None
    panel = Panel(a.history_dir, a.benchmark, universe, a.start, a.end)
    n = len(panel.dates)
    cost = a.cost_bps / 10000
    combos = [(s, k) for s in a.signals for k in a.top_k]
    first = max(LOOKBACK[s] for s in a.signals) + 1
    if n < first + a.train + a.test // 2:
        raise SystemExit(f"not enough history: {n} bars, need ~{first + a.train + a.test // 2}; fetch a longer range (e.g. --range 5y)")

    oos, folds = [], []
    f = first + a.train
    while f < n - a.rebalance:
        train_start, test_end = f - a.train, min(f + a.test, n)
        scored = [(sharpe(run_strategy(panel, s, k, train_start, f, a.rebalance, a.delay, cost)), s, k) for s, k in combos]
        best = max(scored)
        test = run_strategy(panel, best[1], best[2], f, test_end, a.rebalance, a.delay, cost)
        folds.append({"train": [panel.dates[train_start], panel.dates[f - 1]], "test": [panel.dates[f], panel.dates[test_end - 1]],
                      "chosen": f"{best[1]}/top{best[2]}", "train_sharpe_per_period": round(best[0], 3), "test_periods": len(test)})
        oos.extend(test)
        f += a.test

    ppy = 252 / a.rebalance
    full = {f"{s}/top{k}": run_strategy(panel, s, k, first, n, a.rebalance, a.delay, cost) for s, k in combos}
    trial_sr = [sharpe(v) for v in full.values() if len(v) >= 3]
    sr_var = moments(trial_sr)[1] ** 2 if len(trial_sr) > 1 else 0.0
    is_best = max(full, key=lambda name: sharpe(full[name]))
    report = {
        "universe_size": len(panel.prices), "bars": n, "period": [panel.dates[0], panel.dates[-1]],
        "settings": {"rebalance": a.rebalance, "delay": a.delay, "train": a.train, "test": a.test, "cost_bps_per_side": a.cost_bps,
                     "combos": len(combos)},
        "walk_forward_oos": summarize([p["net"] for p in oos], ppy, len(combos), sr_var, [p["bench"] for p in oos]),
        "benchmark_same_periods": summarize([p["bench"] for p in oos], ppy),
        "equal_weight_universe_same_periods": summarize([p["ew_universe"] for p in oos if p["ew_universe"] is not None], ppy),
        "naive_in_sample_best": {"combo": is_best, **summarize([p["net"] for p in full[is_best]], ppy)},
        "folds": folds,
        "biases": ["Returns are nominal TL: compare with inflation, deposit rates and USD-based results before calling them profitable.",
                   "Survivorship: only currently listed stocks are in the universe; delisted losers are missing (index members today = past winners).",
                   "Close-only histories cannot apply a historical liquidity filter; results may include untradeable micro-caps.",
                   "Corporate-action repairs are approximate; verify outliers against KAP.",
                   "Costs are assumptions; slippage in thin BIST names can be far larger."],
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "walkforward.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    with (a.out / "walkforward_oos.csv").open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["date", "exit", "signal", "k", "gross", "net", "turnover", "bench", "ew_universe", "picks"])
        for p in oos:
            w.writerow([p["date"], p["exit"], p["signal"], p["k"], round(p["gross"], 6), round(p["net"], 6), round(p["turnover"], 3),
                        round(p["bench"], 6), None if p["ew_universe"] is None else round(p["ew_universe"], 6), ";".join(p["picks"])])
    wf, bm, ew, nb = report["walk_forward_oos"], report["benchmark_same_periods"], report["equal_weight_universe_same_periods"], report["naive_in_sample_best"]
    g = lambda d, k: "—" if d.get(k) is None else f"{d[k]:.2f}"
    lines = [f"# Walk-forward test — {report['period'][0]} → {report['period'][1]}", "",
             f"Evren {report['universe_size']} hisse · yeniden dengeleme {a.rebalance} gün · maliyet {a.cost_bps} bp/taraf · {len(combos)} kombinasyon · {len(folds)} kat",
             "", "| Seri | CAGR % | Sharpe | Maks. düşüş % | İsabet | DSR olasılığı |", "|---|---|---|---|---|---|",
             f"| Walk-forward (OOS) | {g(wf, 'cagr_pct')} | {g(wf, 'sharpe_ann')} | {g(wf, 'max_drawdown_pct')} | {g(wf, 'hit_rate')} | {g(wf, 'deflated_sharpe_prob')} |",
             f"| Endeks (aynı dönemler) | {g(bm, 'cagr_pct')} | {g(bm, 'sharpe_ann')} | {g(bm, 'max_drawdown_pct')} | {g(bm, 'hit_rate')} | — |",
             f"| Eşit ağırlık evren | {g(ew, 'cagr_pct')} | {g(ew, 'sharpe_ann')} | {g(ew, 'max_drawdown_pct')} | {g(ew, 'hit_rate')} | — |",
             f"| Naif tüm-dönem en iyisi ({nb['combo']}) | {g(nb, 'cagr_pct')} | {g(nb, 'sharpe_ann')} | {g(nb, 'max_drawdown_pct')} | {g(nb, 'hit_rate')} | — |",
             "", "Katlarda seçilen kombinasyonlar: " + ", ".join(fd["chosen"] for fd in folds), "",
             "**Yanlılıklar:** " + " ".join(report["biases"]), "",
             "Yorum kuralı: OOS sonuç endeksi ve eşit ağırlıklı evreni maliyet sonrası geçmiyorsa veya DSR olasılığı < 0,95 ise sinyal 'kanıtlanmış' sayılmaz."]
    (a.out / "walkforward.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main()
