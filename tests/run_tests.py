#!/usr/bin/env python3
"""Offline regression tests for the public skill (no network, standard library only).

Every test builds deterministic synthetic data in a temporary folder, runs a script the way the skill
does, and checks the output contract. Run: python tests/run_tests.py
"""

import csv
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "yigit-investment-copilot"
M = SKILL / "modules"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
RESULTS = []


def run(script, *args, expect=0):
    res = subprocess.run([sys.executable, str(script), *[str(a) for a in args]], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300)
    if res.returncode != expect:
        raise AssertionError(f"{Path(script).name} exit {res.returncode}: {(res.stderr or res.stdout)[-600:]}")
    return res.stdout


def test(fn):
    try:
        fn()
        RESULTS.append((fn.__name__, "PASS", ""))
    except Exception as exc:  # report and continue
        RESULTS.append((fn.__name__, "FAIL", f"{type(exc).__name__}: {exc}"))
    return fn


def trading_days(n, start=date(2022, 1, 3)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def write_history(path, closes, days, volume=1_000_000):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["date", "open", "high", "low", "close", "adj_close", "volume", "complete"])
        prev = closes[0]
        for d, c in zip(days, closes):
            hi, lo = max(prev, c) * 1.01, min(prev, c) * 0.99
            w.writerow([d.isoformat(), round(prev, 4), round(hi, 4), round(lo, 4), round(c, 4), round(c, 4), volume, 1])
            prev = c


def random_walk(n, seed, drift=0.0004, vol=0.02, start=100.0):
    rng = random.Random(seed)
    out, p = [], start
    for _ in range(n):
        p *= math.exp(drift + vol * rng.gauss(0, 1))
        out.append(p)
    return out


TMP = Path(tempfile.mkdtemp(prefix="iy-tests-"))
DAYS = trading_days(600)
HIST = TMP / "hist"
HIST.mkdir()
CODES = [f"T{i:02d}" for i in range(40)]
for i, code in enumerate(CODES):
    write_history(HIST / f"{code}.csv", random_walk(len(DAYS), i, drift=0.0002 + 0.00005 * (i % 7)), DAYS)
write_history(HIST / "XU100.csv", random_walk(len(DAYS), 999, drift=0.0003, vol=0.012, start=10000), DAYS)


@test
def valuation_known_answers():
    v = M / "public-equity-research" / "scripts" / "valuation_models.py"
    pb = json.loads(run(v, "pb-roe", "--roe", 28, "--coe", 34, "--growth", 22, "--bvps", 40, "--price", 52))
    assert abs(pb["justified_pb"] - 0.5) < 1e-9, pb
    assert abs(pb["implied_sustainable_roe_pct"] - 37.6) < 1e-6, pb
    dcf = json.loads(run(v, "dcf", "--cash0", 100, "--growth", "20,20,20,20,20", "--terminal-growth", 10, "--rate", 25,
                         "--shares", 10, "--net-debt", 0))
    price = dcf["scenarios"][0]["per_share"]
    rev = json.loads(run(v, "reverse-dcf", "--price", price, "--shares", 10, "--cash0", 100, "--rate", 25,
                         "--terminal-growth", 10, "--years", 5))
    assert abs(rev["implied_growth_pct"] - 20) < 0.01, rev
    coe = json.loads(run(v, "coe", "--rf-usd", 4, "--erp", 5, "--crp", 3, "--beta", 1, "--infl-try", 25, "--infl-usd", 2.5))
    assert abs(coe["coe_usd_pct"] - 12) < 1e-9 and coe["coe_try_nominal_pct"] > 30, coe
    run(v, "dcf", "--cash0", 100, "--growth", "5", "--terminal-growth", 30, "--rate", 25, expect=1)  # g >= rate must fail


@test
def forecast_ledger_roundtrip():
    f = M / "probabilistic-market-forecast" / "scripts" / "forecast_ledger.py"
    ledger = TMP / "ledger.jsonl"
    rec = json.loads(run(f, "--ledger", ledger, "add", "--ticker", "T01", "--horizon-days", 30, "--price", 100,
                         "--p10", 90, "--p50", 101, "--p90", 112, "--thesis", "test", "--kill", "kill", "--benchmark-price", 1000))
    res = json.loads(run(f, "--ledger", ledger, "resolve", "--id", rec["id"], "--price", 105, "--benchmark-price", 1010,
                         "--lesson", "lesson one"))
    assert abs(res["excess_return_vs_benchmark"] - 0.04) < 1e-9 and res["inside_p10_p90"] is True, res
    run(f, "--ledger", ledger, "note", "--id", rec["id"], "--text", "note one")
    hist = run(f, "--ledger", ledger, "history", "--ticker", "T01")
    assert "lesson one" in hist and "note one" in hist, hist
    assert "chain intact: 3 records" in run(f, "--ledger", ledger, "verify")
    lines = ledger.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["p90"] = 999
    ledger.write_text("\n".join([json.dumps(tampered, ensure_ascii=False)] + lines[1:]) + "\n", encoding="utf-8")
    run(f, "--ledger", ledger, "verify", expect=1)


@test
def base_rates_contract():
    out = TMP / "br"
    run(M / "probabilistic-market-forecast" / "scripts" / "base_rates.py", "--history-dir", HIST, "--horizon-days", 30,
        "--benchmark", HIST / "XU100.csv", "--out", out)
    data = json.loads((out / "base_rates.json").read_text(encoding="utf-8"))
    assert data["results"]["baseline"]["n"] > 1000, data["results"]["baseline"]
    assert data["meta"]["stocks"] == 40, data["meta"]
    assert set(data["current_matches"]) >= {"trend_template", "mom_top_decile", "drop_1m"}
    assert (out / "base_rates.md").exists()


@test
def portfolio_builder_contract():
    out = TMP / "pf"
    hold = TMP / "holdings.csv"
    hold.write_text("code,quantity,avg_cost,stop\nT01,100,100,80\n", encoding="utf-8")
    run(M / "portfolio-risk-and-sizing" / "scripts" / "portfolio_builder.py", "--history-dir", HIST, "--holdings", hold,
        "--candidates", "T02", "T03", "T04", "T05", "--budget", 100000, "--max-weight", 0.4, "--benchmark", HIST / "XU100.csv",
        "--out", out)
    rep = json.loads((out / "portfolio.json").read_text(encoding="utf-8"))
    assert rep["spent"] <= 100000 and rep["cash_left"] >= 0, rep
    assert abs(sum(p["risk_contribution_pct"] for p in rep["positions"]) - 100) < 1e-6
    assert all(float(p["new_shares"]).is_integer() for p in rep["positions"])
    assert rep["heat_total"] > 0 and rep["beta_to_benchmark"] is not None


def synthetic_snapshot(folder, market="turkey"):
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    rows = []
    for i, code in enumerate(CODES):
        close = 10 + i
        rows.append({"symbol": f"BIST:{code}", "ticker": code, "name": f"Test {code}", "sector": ["Finans", "Sanayi", "Enerji"][i % 3],
                     "sector_en": ["Finance", "Producer Manufacturing", "Energy Minerals"][i % 3], "close": close,
                     "change_pct": rng.uniform(-3, 3), "avg_volume_30d": 2_000_000, "market_cap_try": 1e9 * (1 + i),
                     "ev_try": 1.2e9 * (1 + i), "pe_ttm": rng.uniform(3, 30), "pb": rng.uniform(0.5, 4), "ev_ebitda": rng.uniform(3, 15),
                     "ev_sales": rng.uniform(0.5, 4), "p_cfo": rng.uniform(2, 20), "peg": rng.uniform(0.3, 3),
                     "div_yield_pct": rng.uniform(0, 6), "roe_pct": rng.uniform(-5, 40), "roic_pct": rng.uniform(0, 30),
                     "op_margin_pct": rng.uniform(0, 30), "net_margin_pct": rng.uniform(-5, 25), "debt_to_equity": rng.uniform(0, 2),
                     "net_income_ttm_try": 1e8 * rng.uniform(-1, 5), "ebitda_ttm_try": 1e8 * rng.uniform(0.5, 5), "fcf_try": 1e8 * rng.uniform(-1, 3),
                     "rev_growth_yoy_pct": rng.uniform(-10, 80), "ni_growth_yoy_pct": rng.uniform(-50, 120),
                     "perf_1m_pct": rng.uniform(-20, 20), "perf_3m_pct": rng.uniform(-30, 40), "perf_6m_pct": rng.uniform(-30, 60),
                     "perf_1y_pct": rng.uniform(-40, 120), "high_52w": close * 1.3, "low_52w": close * 0.7, "high_3m": close * 1.1,
                     "sma20": close * 0.98, "sma50": close * 0.95, "sma150": close * 0.9, "sma200": close * 0.88,
                     "rsi14": rng.uniform(25, 75), "adx14": rng.uniform(10, 40), "macd": 0.1, "macd_signal": 0.05,
                     "volatility_w_pct": 2, "volatility_m_pct": 3, "beta_1y": rng.uniform(0.5, 1.5), "float_pct": 30,
                     "piotroski": rng.randint(2, 9), "altman_z": rng.uniform(1, 5),
                     "target_median": close * 1.2 if i % 4 == 0 else "", "rec_total": 5 if i % 4 == 0 else "",
                     "rec_mark": 1.4 if i % 4 == 0 else "", "earnings_next": (date.today() + timedelta(days=5 + i)).isoformat(),
                     "in_xu100": 1 if i < 30 else 0, "avg_turnover_30d_try": 2_000_000 * close})
    cols = list(rows[0].keys())
    with open(folder / "snapshot.csv", "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    (folder / "snapshot.meta.json").write_text(json.dumps({"market": market, "currency": "TRY" if market == "turkey" else "USD",
                                                           "source": "synthetic", "fetched_at": "2026-09-28T10:00:00+03:00"}),
                                               encoding="utf-8")
    return folder / "snapshot.csv"


@test
def scan_contract_and_html():
    snap = synthetic_snapshot(TMP / "run" / "snapshot")
    out = TMP / "run" / "scan"
    run(M / "market-data-engine" / "scripts" / "bist_scan.py", "--snapshot", snap, "--history-dir", HIST,
        "--benchmark", HIST / "XU100.csv", "--horizon", "3m", "--min-turnover", 1_000_000, "--out", out)
    ranked = list(csv.DictReader(open(out / "scan_ranked.csv", encoding="utf-8")))
    assert len(ranked) == 40 and ranked[0]["rank"] == "1", len(ranked)
    assert "lane_expectations" in ranked[0] and "analyst_upside" in ranked[0]
    seed = json.loads((out / "funnel_seed.json").read_text(encoding="utf-8"))
    assert seed["universe"]["total_count"] == 40 and seed["shortlisted"], seed["universe"]
    assert "BILANCO_YAKIN" in (out / "scan_summary.md").read_text(encoding="utf-8")
    run(SKILL / "scripts" / "report_html.py", "--run-dir", TMP / "run", "--history-dir", HIST)
    html = (TMP / "run" / "REPORT.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and "<svg" in html and "<script" not in html


@test
def scan_us_market_labels():
    snap = synthetic_snapshot(TMP / "us" / "snapshot", market="america")
    out = TMP / "us" / "scan"
    run(M / "market-data-engine" / "scripts" / "bist_scan.py", "--snapshot", snap, "--horizon", "1y",
        "--min-turnover", 1_000_000, "--out", out)
    text = (out / "scan_summary.md").read_text(encoding="utf-8")
    assert text.startswith("# ABD tarama") and "USD/gün" in text, text[:200]


@test
def tefas_metrics_function():
    sys.path.insert(0, str(M / "market-data-engine" / "scripts"))
    import tefas_funds  # noqa: E402
    series = [(d, 100 * (1.001 ** k)) for k, d in enumerate(DAYS[:300])]
    m = tefas_funds.metrics(series, rf_annual=0.0)
    expected = (1.001 ** 299 - 1) * 100
    assert abs(m["total_return_pct"] - expected) < 1e-6 and m["max_drawdown_pct"] == 0, m
    assert abs(tefas_funds.real_return(50, 25) - 20.0) < 1e-9
    assert tefas_funds.peer_group({"category": "Hisse", "risk_value": 6}).endswith("yüksek")


@test
def common_helpers():
    sys.path.insert(0, str(M / "market-data-engine" / "scripts"))
    import common  # noqa: E402
    assert common.yahoo_symbol("THYAO") == "THYAO.IS"
    assert common.yahoo_symbol("BRK.B", "america") == "BRK-B"
    assert common.yahoo_symbol("USDTRY") == "TRY=X"
    assert common.round_tick(123.456, "down") == 123.4 and common.round_tick(15.456, "down") == 15.45
    assert common.pct_ranks([3, 1, 2]) == [1.0, 0.0, 0.5]
    import macro_snapshot  # noqa: E402
    assert str(macro_snapshot._tcmb_date("23.01.26")) == "2026-01-23"
    assert macro_snapshot._num("37,50") == 37.5


@test
def technical_and_trade_plan():
    ta = run(M / "technical-quant-analysis" / "scripts" / "technical_indicators.py", HIST / "T05.csv",
             "--benchmark", HIST / "XU100.csv", "--horizon-days", 30)
    data = json.loads(ta)
    assert "trend_template" in data["setups"] and data["indicators"]["close"] > 0
    plan = run(M / "trade-management-exits" / "scripts" / "trade_plan.py", "--entry", data["indicators"]["close"],
               "--history", HIST / "T05.csv", "--capital", 100000, "--risk-pct", 1)
    assert "stop" in plan.lower()


@test
def watchlist_offline():
    snap = TMP / "run" / "snapshot" / "snapshot.csv"
    wl = TMP / "watch.csv"
    wl.write_text("code,entry,stop,target1,target2,quantity,review_date,thesis\nT01,13,12,20,30,100,2020-01-01,x\nT02,,,,,,,\n",
                  encoding="utf-8")
    run(M / "trade-management-exits" / "scripts" / "watchlist_monitor.py", "--watchlist", wl, "--snapshot", snap,
        "--out", TMP / "watch")
    rep = json.loads((TMP / "watch" / "watch_report.json").read_text(encoding="utf-8"))
    first = rep["items"][0]
    assert first["code"] == "T01" and "STOP_ALTINDA" in first["alerts"] and "GOZDEN_GECIR" in first["alerts"], first


@test
def skill_contract_files():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "name: yigit-investment-copilot" in text
    golden = json.loads((SKILL / "evals" / "golden-prompts.json").read_text(encoding="utf-8"))
    assert len(golden["cases"]) >= 10 and all(c["must"] and "must_not" in c for c in golden["cases"])
    yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "interface:" in yaml and "display_name:" in yaml and "./assets/icon.svg" in yaml
    assert (SKILL / "assets" / "icon.svg").exists()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    width = max(len(n) for n, _, _ in RESULTS)
    for name, status, detail in RESULTS:
        print(f"{status}  {name:<{width}}  {detail}")
    failed = [r for r in RESULTS if r[1] != "PASS"]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed · data in {TMP}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
