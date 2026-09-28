#!/usr/bin/env python3
"""Performance statistics for a return series, including the Probabilistic and Deflated Sharpe
Ratio (Bailey & López de Prado) for multiple-testing-aware evaluation. Standard library only.

Input: CSV with a `ret` column (simple period returns, e.g. 0.012) or a JSON list of numbers.
Usage:
  python strategy_stats.py returns.csv --periods-per-year 12 --trials 21 --trial-sr-var 0.0025
"""

import argparse
import csv
import json
import sys
import math
import random
from pathlib import Path
from statistics import NormalDist

EULER = 0.5772156649015329
N01 = NormalDist()


def moments(x):
    n = len(x)
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    if sd == 0:
        return m, 0.0, 0.0, 3.0
    skew = sum(((v - m) / sd) ** 3 for v in x) / n
    kurt = sum(((v - m) / sd) ** 4 for v in x) / n
    return m, sd, skew, kurt


def max_drawdown(returns):
    peak, eq, mdd = 1.0, 1.0, 0.0
    for r in returns:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return mdd


def psr(sr, n, skew, kurt, sr_star=0.0):
    """Probability that the true (per-period) Sharpe exceeds sr_star."""
    if n < 3:
        return None
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    if denom <= 0:
        return None
    return N01.cdf((sr - sr_star) * math.sqrt(n - 1) / math.sqrt(denom))


def expected_max_sr(n_trials, trial_sr_var):
    """Expected maximum per-period Sharpe among n_trials unskilled strategies."""
    if n_trials < 2 or trial_sr_var <= 0:
        return 0.0
    return math.sqrt(trial_sr_var) * ((1 - EULER) * N01.inv_cdf(1 - 1 / n_trials) + EULER * N01.inv_cdf(1 - 1 / (n_trials * math.e)))


def bootstrap_ci(returns, periods_per_year, reps=2000, block=3, seed=7):
    rng = random.Random(seed)
    n = len(returns)
    if n < 8:
        return None
    stats = []
    for _ in range(reps):
        sample = []
        while len(sample) < n:
            start = rng.randrange(n)
            sample.extend(returns[(start + k) % n] for k in range(block))
        m = sum(sample[:n]) / n
        stats.append(m * periods_per_year)
    stats.sort()
    return {"annual_mean_p05": stats[int(0.05 * reps)], "annual_mean_p95": stats[int(0.95 * reps)]}


def summarize(returns, periods_per_year, trials=1, trial_sr_var=0.0, benchmark=None):
    returns = [r for r in returns if r is not None]
    n = len(returns)
    if n < 2:
        return {"periods": n, "error": "need at least two returns"}
    m, sd, skew, kurt = moments(returns)
    growth = 1.0
    for r in returns:
        growth *= 1 + r
    years = n / periods_per_year
    downside = [min(0.0, r) for r in returns]
    dd = math.sqrt(sum(d * d for d in downside) / n)
    sr = m / sd if sd else 0.0
    out = {
        "periods": n, "years": round(years, 2),
        "total_return_pct": (growth - 1) * 100,
        "cagr_pct": (growth ** (1 / years) - 1) * 100 if years > 0 and growth > 0 else None,
        "vol_ann_pct": sd * math.sqrt(periods_per_year) * 100,
        "sharpe_ann": sr * math.sqrt(periods_per_year),
        "sortino_ann": (m / dd) * math.sqrt(periods_per_year) if dd else None,
        "max_drawdown_pct": max_drawdown(returns) * 100,
        "hit_rate": sum(1 for r in returns if r > 0) / n,
        "skew": skew, "kurtosis": kurt,
        "t_stat_mean": m / (sd / math.sqrt(n)) if sd else None,
        "psr_vs_zero": psr(sr, n, skew, kurt, 0.0),
    }
    cagr = out["cagr_pct"]
    out["calmar"] = cagr / abs(out["max_drawdown_pct"]) if cagr is not None and out["max_drawdown_pct"] else None
    sr0 = expected_max_sr(trials, trial_sr_var)
    out["trials"] = trials
    out["expected_max_sr_per_period_under_null"] = sr0
    out["deflated_sharpe_prob"] = psr(sr, n, skew, kurt, sr0) if trials > 1 else out["psr_vs_zero"]
    out["bootstrap"] = bootstrap_ci(returns, periods_per_year)
    if benchmark and len(benchmark) == n:
        active = [a - b for a, b in zip(returns, benchmark)]
        am, asd, _, _ = moments(active)
        out["excess_ann_pct"] = am * periods_per_year * 100
        out["information_ratio"] = am / asd * math.sqrt(periods_per_year) if asd else None
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
    ap.add_argument("returns", type=Path)
    ap.add_argument("--column", default="ret")
    ap.add_argument("--periods-per-year", type=float, default=252)
    ap.add_argument("--trials", type=int, default=1, help="number of strategy variants tried (for DSR)")
    ap.add_argument("--trial-sr-var", type=float, default=0.0, help="variance of per-period Sharpe across trials")
    a = ap.parse_args()
    if a.returns.suffix.lower() == ".json":
        data = json.loads(a.returns.read_text(encoding="utf-8"))
    else:
        with a.returns.open(encoding="utf-8-sig", newline="") as handle:
            data = [float(r[a.column]) for r in csv.DictReader(handle) if r.get(a.column) not in (None, "")]
    print(json.dumps(summarize(data, a.periods_per_year, a.trials, a.trial_sr_var), indent=2))


if __name__ == "__main__":
    main()
