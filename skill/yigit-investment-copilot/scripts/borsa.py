#!/usr/bin/env python3
"""One-command data runs for the investment copilot (Python 3.9+, standard library only).

  python scripts/borsa.py pipeline --horizon 3m            # whole-BIST scan -> regime -> KAP -> finalists -> REPORT.md
  python scripts/borsa.py ticker THYAO --horizon 1m        # single-stock evidence pack
  python scripts/borsa.py regime                           # market regime + macro
  python scripts/borsa.py kap --days 3                     # market-wide KAP digest (or --ticker CODE ...)
  python scripts/borsa.py macro                            # TCMB + cross-asset snapshot

Everything is read-only research data from public endpoints (TradingView screener, Yahoo Finance,
KAP, İş Yatırım, TCMB). Nothing here places orders. Outputs go to ./borsa-out/<time>-<command>/ and a
reusable price cache in ~/.cache/yigit-investment-copilot (override with --cache).
"""

import argparse
import csv
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENG = ROOT / "modules" / "market-data-engine" / "scripts"
TA = ROOT / "modules" / "technical-quant-analysis" / "scripts" / "technical_indicators.py"
FC = ROOT / "modules" / "probabilistic-market-forecast" / "scripts" / "forecast_ranges.py"
REG = ROOT / "modules" / "market-regime-analysis" / "scripts" / "bist_breadth.py"
TRT = timezone(timedelta(hours=3))
HORIZONS = {"1w": 7, "2w": 14, "1m": 30, "2m": 60, "3m": 90, "6m": 180, "9m": 270, "1y": 365, "2y": 730, "3y": 1095}


def say(msg):
    print(f"[{datetime.now(TRT).strftime('%H:%M:%S')}] {msg}", flush=True)


def run(script, *args, timeout=900, capture=False):
    cmd = [sys.executable, str(script), *[str(a) for a in args]]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        say(f"  zaman aşımı: {Path(script).name}")
        return None
    if res.returncode not in (0, 2):
        tail = (res.stderr or res.stdout or "").strip().splitlines()[-3:]
        say(f"  HATA {Path(script).name}: {' | '.join(tail)}")
        return None
    return res.stdout if capture else True


def days_of(h):
    h = h.lower()
    if h in HORIZONS:
        return HORIZONS[h]
    if h.endswith("d") and h[:-1].isdigit():
        return int(h[:-1])
    raise SystemExit(f"bilinmeyen vade {h}")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fetch_history(codes, out, rng, mode, cache_hours, timeout):
    lst = out / "_list.txt"
    out.mkdir(parents=True, exist_ok=True)
    lst.write_text("\n".join(codes), encoding="utf-8")
    return run(ENG / "price_history.py", "--tickers-file", lst, "--range", rng, "--mode", mode, "--max-age-hours", cache_hours,
               "--out", out, timeout=timeout)


def ta_and_forecast(code, hist, bench, horizon_days, out):
    out.mkdir(parents=True, exist_ok=True)
    raw = run(TA, hist, "--benchmark", bench, "--horizon-days", horizon_days, "--repair", "--md", out / "teknik.md", capture=True, timeout=120)
    if not raw:
        return None
    ta = json.loads(raw)
    (out / "teknik.json").write_text(raw, encoding="utf-8")
    p = ta["indicators"]
    vol = (p.get("realized_vol_60d_ann_pct") or p.get("realized_vol_20d_ann_pct") or 40) / 100
    target = (ta["levels"].get("bull_trigger") or p["close"] * 1.1)
    bars = max(1, round(horizon_days * 252 / 365))
    fc = run(FC, "--current-price", p["close"], "--annualized-vol", round(vol, 4), "--horizon-days", horizon_days,
             "--target-price", round(target, 4), "--loss-threshold", 0.10, "--history-csv", hist, "--horizon-bars", bars,
             capture=True, timeout=60)
    if fc:
        (out / "tahmin.json").write_text(fc, encoding="utf-8")
        ta["forecast"] = json.loads(fc)
    return ta


def fmt(x, d=2):
    if x is None:
        return "—"
    if isinstance(x, (int, float)):
        return f"{x:,.{d}f}"
    return str(x)


def num(row, key):
    try:
        return float(row.get(key)) if row.get(key) not in (None, "") else None
    except (TypeError, ValueError):
        return None


def finalist_block(code, row, ta, kap, fin):
    lines = [f"### {code} — {(row.get('name') or '')[:60]}", ""]
    lines.append(f"- Sektör {row.get('sector') or '—'} · fiyat {fmt(num(row, 'close'))} · bileşik skor {fmt(num(row, 'composite'), 3)} · bayraklar: {row.get('flags') or 'yok'}")
    lines.append(f"- F/K {fmt(num(row, 'pe_ttm'))} · PD/DD {fmt(num(row, 'pb'))} · ROE% {fmt(num(row, 'roe_pct'), 1)} · net marj% {fmt(num(row, 'net_margin_pct'), 1)} · Piotroski {fmt(num(row, 'piotroski'), 0)}")
    if ta:
        p, st, lv = ta["indicators"], ta["setups"], ta["levels"]
        lines.append(f"- Teknik: trend şablonu {st['trend_template']['passed']}/{st['trend_template']['checked']} · {st['weinstein_stage']} · RSI {fmt(p.get('rsi14'), 1)} · ATR% {fmt(p.get('atr_pct'))} · göreli güç 3A {fmt(ta['relative_strength'].get('rs_3m_pct'), 1)}%")
        lines.append("- Kurulumlar: " + (", ".join(k for k, v in st.items() if v is True) or "yok")
                     + f" · destek {fmt(lv.get('bear_trigger'))} · direnç {fmt(lv.get('bull_trigger'))} · ATR stop 2x {fmt(lv.get('atr_stop_2x'))}")
        f = ta.get("forecast")
        if f:
            q = f.get("price_quantiles", {})
            emp = (f.get("empirical") or {}).get("price_quantiles", {})
            lines.append(f"- Olasılık aralığı (log-normal, sıfır sürüklenme): P10 {fmt(q.get('p10'))} · P50 {fmt(q.get('p50'))} · P90 {fmt(q.get('p90'))} · "
                         f"dirence ulaşma {fmt((f.get('probability_reach_target') or 0) * 100, 0)}% · -%10 kayıp {fmt((f.get('probability_loss_beyond_threshold') or 0) * 100, 0)}%")
            if emp:
                lines.append(f"- Geçmiş taban oranı (aynı vade): P10 {fmt(emp.get('p10'))} · P50 {fmt(emp.get('p50'))} · P90 {fmt(emp.get('p90'))}")
    if fin:
        m = fin.get("metrics", {})
        lines.append(f"- Bilanço ({fin.get('group')}, {m.get('latest_period')}): gelir TTM {fmt((m.get('revenue_ttm') or 0) / 1e9, 1)} mr TL · net kâr TTM {fmt((m.get('net_income_ttm') or 0) / 1e9, 1)} mr TL · "
                     f"ROE {fmt(m.get('roe_ttm_pct'), 1)}% · faaliyet marjı {fmt(m.get('operating_margin_pct'), 1)}% · net borç/FAVÖK {fmt(m.get('net_debt_to_ebitda'))}"
                     + (f" · veri anomalisi: {len(m['data_anomalies'])}" if m.get("data_anomalies") else ""))
    if kap:
        hi = [i for i in kap.get("items", []) if i["importance"] == "HIGH" and i["event_class"] not in ("SETTLEMENT_DEFAULT",)][:4]
        if hi:
            lines.append("- KAP (önemli): " + " | ".join(f"{i['published'][:10]} {i['event_class']}: {(i['summary'] or i['subject'])[:90]}" for i in hi))
    return "\n".join(lines) + "\n"


def cmd_pipeline(a):
    days = days_of(a.horizon)
    out = a.out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-pipeline-{a.horizon}"
    cache = a.cache
    out.mkdir(parents=True, exist_ok=True)
    say(f"1/7 BIST anlık görünüm ({a.universe}) → {out}")
    if not run(ENG / "bist_snapshot.py", "--universe", "ALL", "--out", out / "snapshot", timeout=120):
        raise SystemExit("Anlık görünüm alınamadı (internet yok mu?). ChatGPT/claude.ai'de web taraması ya da CSV yükleme yolunu kullan.")
    snap = read_csv(out / "snapshot" / "snapshot.csv")
    say("2/7 Endeks ve kur geçmişi (XU100, USDTRY)")
    fetch_history(["XU100", "USDTRY"], cache / "chart", "5y", "chart", 20, 300)
    bench = cache / "chart" / "XU100.csv"
    hist_dir = None
    if not a.skip_history:
        universe = [r["ticker"] for r in snap if a.universe.upper() == "ALL" or r.get(f"in_{a.universe.lower()}") == "1"]
        say(f"3/7 {len(universe)} hisse için 2 yıllık kapanış geçmişi (toplu mod, önbellek 20 saat, süre bütçesi {a.history_budget} sn)")
        t0 = time.time()
        fetch_history(universe, cache / "spark2y", "2y", "spark", 20, a.history_budget)
        have = sum(1 for t in universe if (cache / "spark2y" / f"{t}.csv").exists())
        say(f"   {have}/{len(universe)} hisse geçmişi hazır ({time.time() - t0:.0f} sn)")
        hist_dir = cache / "spark2y"
    say(f"4/7 KAP akışı (son {a.kap_days} gün)")
    run(ENG / "kap_feed.py", "--all", "--days", a.kap_days, "--out", out / "kap", timeout=600)
    kap_all = out / "kap" / "kap_all.json"
    say("5/7 Piyasa rejimi ve genişlik")
    reg_args = ["--snapshot", out / "snapshot" / "snapshot.csv", "--out", out / "regime"]
    if bench.exists():
        reg_args += ["--index", bench]
    if (cache / "chart" / "USDTRY.csv").exists():
        reg_args += ["--usdtry", cache / "chart" / "USDTRY.csv"]
    if hist_dir:
        reg_args += ["--history-dir", hist_dir]
    run(REG, *reg_args, timeout=180)
    say(f"6/7 Çok şeritli tarama (vade {days} gün)")
    scan_args = ["--snapshot", out / "snapshot" / "snapshot.csv", "--horizon", a.horizon, "--universe", a.universe,
                 "--min-turnover", a.min_turnover, "--top", a.top, "--out", out / "scan"]
    if hist_dir:
        scan_args += ["--history-dir", hist_dir]
    if bench.exists():
        scan_args += ["--benchmark", bench]
    if kap_all.exists():
        scan_args += ["--kap", kap_all]
    if not run(ENG / "bist_scan.py", *scan_args, timeout=300):
        raise SystemExit("tarama başarısız")
    seed = json.loads((out / "scan" / "funnel_seed.json").read_text(encoding="utf-8"))
    ranked = {r["ticker"]: r for r in read_csv(out / "scan" / "scan_ranked.csv")}
    finalists = [s["ticker"] for s in seed["shortlisted"]][: a.finalists]
    say(f"7/7 Finalist kanıt paketleri: {', '.join(finalists)}")
    fetch_history(finalists, cache / "chart", "2y", "chart", 20, 600)
    blocks = []
    for code in finalists:
        fdir = out / "finalists" / code
        hist = cache / "chart" / f"{code}.csv"
        ta = ta_and_forecast(code, hist, bench, days, fdir) if hist.exists() and bench.exists() else None
        run(ENG / "kap_feed.py", "--ticker", code, "--days", 90, "--details", 3, "--out", fdir, timeout=180)
        kap = json.loads((fdir / f"kap_{code}.json").read_text(encoding="utf-8")) if (fdir / f"kap_{code}.json").exists() else None
        run(ENG / "financials_isy.py", code, "--quarters", 8, "--out", fdir, timeout=120)
        fin = json.loads((fdir / f"{code}_financials.json").read_text(encoding="utf-8")) if (fdir / f"{code}_financials.json").exists() else None
        blocks.append(finalist_block(code, ranked.get(code, {}), ta, kap, fin))
    run(ENG / "macro_snapshot.py", "--out", out / "macro", timeout=120)
    write_report(out, a, days, seed, blocks)
    say(f"BİTTİ → {out / 'REPORT.md'}")


def write_report(out, a, days, seed, blocks):
    regime = json.loads((out / "regime" / "regime.json").read_text(encoding="utf-8")) if (out / "regime" / "regime.json").exists() else {}
    uni = seed["universe"]
    lines = [f"# Borsa pipeline raporu — vade {a.horizon} ({days} gün)", "",
             f"Veri kesimi {uni['data_cutoff']} · evren {uni['total_count']} → uygun {uni['eligible_count']} · dışlanan {uni['excluded_count']} · "
             f"kaynaklar: TradingView tarayıcı (gecikmeli), Yahoo, KAP, İş Yatırım, TCMB. Hepsi araştırma verisi; karar öncesi birincil kaynakla doğrula.", "",
             "> Bu rapor **ADAY** üretir, al/sat kararı değildir. Sıradaki adımlar SKILL.md'deki tam analiz hattına göre yapılır: temel derin analiz, "
             "yatırım komitesi (boğa-ayı), kırmızı takım, ön işlem kapısı, işlem planı, tahmin defterine kayıt.", ""]
    if regime:
        b, idx = regime.get("breadth", {}), regime.get("index", {})
        lines += ["## Piyasa rejimi", "",
                  f"**{regime.get('regime_label')}** · plan içi hisse maruziyeti {regime.get('equity_exposure_band_of_plan')} · işlem başı risk {regime.get('risk_per_trade_hint')}",
                  f"- XU100 {fmt(idx.get('close'))} (52h zirveden {fmt(idx.get('from_52w_high_pct'), 1)}%) · SMA50 üstü hisse %{fmt(b.get('pct_above_sma50'), 1)} · dağıtım günü {idx.get('distribution_days_25')} · takip günü {idx.get('follow_through_day') or 'yok'}",
                  "- Ayrıntı: regime/regime.md · makro: macro/macro.md", ""]
    summary = (out / "scan" / "scan_summary.md").read_text(encoding="utf-8") if (out / "scan" / "scan_summary.md").exists() else ""
    if summary:
        part = summary.split("## Bileşik sıralama", 1)
        lines += ["## Tarama", "", "## Bileşik sıralama" + part[1].split("## Bayrak sözlüğü")[0] if len(part) > 1 else summary, ""]
    lines += ["## Finalist kanıt paketleri", ""] + blocks
    lines += ["## Yapay zekânın tamamlaması gerekenler", "",
              "1. Her finalist için KAP finansal raporu + özel durumları oku (finalists/<KOD>/kap_*.md), TMS 29 ve tek seferlikleri ayıkla.",
              "2. Değerleme: sektör çarpanları + ters DCF / kalıntı gelir; fiyatın ne fiyatladığını yaz.",
              "3. investment-committee modülü: boğa-ayı tartışması, yatırımcı lensleri, risk komitesi.",
              "4. investment-red-team + pre-trade-investment-gate; yalnız geçenler için trade-management-exits ile plan ve adet.",
              "5. Kararı forecast_ledger.py ile deftere yaz; vadesinde puanla.",
              "6. Rejim 'DÜŞÜŞ TRENDİ' ise maruziyet bandına uy: nakit/mevduat/para piyasası fonu gerçek bir alternatiftir."]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_ticker(a):
    code = a.code.upper()
    days = days_of(a.horizon)
    out = a.out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-{code}"
    out.mkdir(parents=True, exist_ok=True)
    say(f"{code}: anlık görünüm, 5y geçmiş, teknik, olasılık, KAP, bilanço → {out}")
    run(ENG / "bist_snapshot.py", "--tickers", code, "--out", out / "snapshot", timeout=120)
    fetch_history([code, "XU100"], a.cache / "chart", "5y", "chart", 20, 300)
    hist, bench = a.cache / "chart" / f"{code}.csv", a.cache / "chart" / "XU100.csv"
    ta = ta_and_forecast(code, hist, bench, days, out) if hist.exists() and bench.exists() else None
    run(ENG / "kap_feed.py", "--ticker", code, "--days", 120, "--details", 5, "--out", out, timeout=300)
    run(ENG / "financials_isy.py", code, "--quarters", 12, "--out", out, timeout=120)
    snap = read_csv(out / "snapshot" / "snapshot.csv") if (out / "snapshot" / "snapshot.csv").exists() else []
    row = snap[0] if snap else {"close": ta["indicators"]["close"] if ta else None}
    kap = json.loads((out / f"kap_{code}.json").read_text(encoding="utf-8")) if (out / f"kap_{code}.json").exists() else None
    fin = json.loads((out / f"{code}_financials.json").read_text(encoding="utf-8")) if (out / f"{code}_financials.json").exists() else None
    block = finalist_block(code, row, ta, kap, fin)
    (out / "REPORT.md").write_text(f"# {code} kanıt paketi — vade {a.horizon}\n\n{block}\nDosyalar: teknik.md, tahmin.json, kap_{code}.md, {code}_financials.md, snapshot/\n", encoding="utf-8")
    say(f"BİTTİ → {out / 'REPORT.md'}")


def cmd_regime(a):
    out = a.out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-regime"
    run(ENG / "bist_snapshot.py", "--out", out / "snapshot", timeout=120)
    fetch_history(["XU100", "USDTRY"], a.cache / "chart", "5y", "chart", 20, 300)
    run(REG, "--snapshot", out / "snapshot" / "snapshot.csv", "--index", a.cache / "chart" / "XU100.csv",
        "--usdtry", a.cache / "chart" / "USDTRY.csv", "--out", out, timeout=180)
    run(ENG / "macro_snapshot.py", "--out", out, timeout=120)
    say(f"BİTTİ → {out / 'regime.md'} ve {out / 'macro.md'}")


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "yigit-investment-copilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pipeline")
    p.add_argument("--horizon", default="3m")
    p.add_argument("--universe", default="ALL")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--finalists", type=int, default=8)
    p.add_argument("--min-turnover", type=float, default=10_000_000)
    p.add_argument("--kap-days", type=int, default=14)
    p.add_argument("--history-budget", type=int, default=420, help="seconds allowed for bulk history download")
    p.add_argument("--skip-history", action="store_true")
    p.add_argument("--out", type=Path)
    t = sub.add_parser("ticker")
    t.add_argument("code")
    t.add_argument("--horizon", default="3m")
    t.add_argument("--out", type=Path)
    r = sub.add_parser("regime")
    r.add_argument("--out", type=Path)
    k = sub.add_parser("kap")
    k.add_argument("--days", type=int, default=3)
    k.add_argument("--ticker", nargs="*")
    k.add_argument("--out", type=Path)
    m = sub.add_parser("macro")
    m.add_argument("--out", type=Path)
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    if a.cmd == "pipeline":
        cmd_pipeline(a)
    elif a.cmd == "ticker":
        cmd_ticker(a)
    elif a.cmd == "regime":
        cmd_regime(a)
    elif a.cmd == "kap":
        out = a.out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-kap"
        args = ["--days", a.days, "--out", out] + (["--ticker", *a.ticker] if a.ticker else ["--all", "--important-only"])
        run(ENG / "kap_feed.py", *args, timeout=900)
        say(f"BİTTİ → {out}")
    elif a.cmd == "macro":
        out = a.out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-macro"
        run(ENG / "macro_snapshot.py", "--out", out, timeout=120)
        say(f"BİTTİ → {out / 'macro.md'}")


if __name__ == "__main__":
    main()
