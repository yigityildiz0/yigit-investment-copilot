#!/usr/bin/env python3
"""One-command data runs for the investment copilot (Python 3.9+, standard library only).

  python scripts/borsa.py pipeline --horizon 3m            # whole-BIST scan -> regime -> KAP -> finalists -> REPORT.md + REPORT.html
  python scripts/borsa.py pipeline --market america        # same flow on S&P 500 members (no KAP / İş Yatırım)
  python scripts/borsa.py ticker THYAO --horizon 1m        # single-stock evidence pack
  python scripts/borsa.py brief --watchlist watch.csv      # morning note: macro, regime, KAP, calendar, movers, watchlist
  python scripts/borsa.py sector                           # sector overview (or --name "Finans" for one sector)
  python scripts/borsa.py regime                           # market regime + macro
  python scripts/borsa.py kap --days 3                     # market-wide KAP digest (or --ticker CODE ...)
  python scripts/borsa.py macro                            # TCMB rates/CPI/FX + cross-asset snapshot
  python scripts/borsa.py fon screen --category "hisse"    # TEFAS funds (screen | fund CODE | compare A B C)
  python scripts/borsa.py taban --horizon 3m               # historical base rates of setups on the cached universe
  python scripts/borsa.py izle --watchlist watch.csv       # check positions/watchlist against their plans
  python scripts/borsa.py portfoy --candidates A B C --budget 250000   # risk-parity allocation + portfolio risk

Everything is read-only research data from public endpoints (TradingView screener, Yahoo Finance,
KAP, İş Yatırım, TCMB, TEFAS). Nothing here places orders. Outputs go to ./borsa-out/<time>-<command>/
and a reusable price cache in ~/.cache/yigit-investment-copilot (override with --cache).
"""

import argparse
import csv
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENG = ROOT / "modules" / "market-data-engine" / "scripts"
TA = ROOT / "modules" / "technical-quant-analysis" / "scripts" / "technical_indicators.py"
FC = ROOT / "modules" / "probabilistic-market-forecast" / "scripts" / "forecast_ranges.py"
BASE_RATES = ROOT / "modules" / "probabilistic-market-forecast" / "scripts" / "base_rates.py"
REG = ROOT / "modules" / "market-regime-analysis" / "scripts" / "bist_breadth.py"
WATCH = ROOT / "modules" / "trade-management-exits" / "scripts" / "watchlist_monitor.py"
PORTFOLIO = ROOT / "modules" / "portfolio-risk-and-sizing" / "scripts" / "portfolio_builder.py"
HTML = ROOT / "scripts" / "report_html.py"
sys.path.insert(0, str(ENG))
from common import md_table, safe_name, yahoo_symbol  # noqa: E402

TRT = timezone(timedelta(hours=3))
HORIZONS = {"1w": 7, "2w": 14, "1m": 30, "2m": 60, "3m": 90, "6m": 180, "9m": 270, "1y": 365, "2y": 730, "3y": 1095}
MARKETS = {"turkey": {"label": "BIST", "bench": "XU100", "bench_name": "XU100", "default_universe": "ALL"},
           "america": {"label": "ABD", "bench": "SPX", "bench_name": "S&P 500", "default_universe": "SPX"}}


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


def stamp_dir(label, out=None):
    return out or Path.cwd() / "borsa-out" / f"{datetime.now(TRT).strftime('%Y%m%d-%H%M')}-{label}"


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


def read_json(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def fetch_history(codes, out, rng, mode, cache_hours, timeout, market="turkey"):
    lst = out / "_list.txt"
    out.mkdir(parents=True, exist_ok=True)
    lst.write_text("\n".join(codes), encoding="utf-8")
    return run(ENG / "price_history.py", "--tickers-file", lst, "--range", rng, "--mode", mode, "--max-age-hours", cache_hours,
               "--market", market, "--out", out, timeout=timeout)


def hist_file(folder, code, market="turkey"):
    """Where price_history.py saved a code (dotted US share classes use the Yahoo symbol)."""
    return folder / f"{safe_name(code.upper() if '.' not in code else yahoo_symbol(code, market))}.csv"


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
    rec_total = num(row, "rec_total")
    if rec_total:
        target = num(row, "target_median") or num(row, "target_avg")
        close = num(row, "close")
        upside = (target / close - 1) * 100 if target and close else None
        lines.append(f"- Analist (görüş, kanıt değil): {int(rec_total)} analist · konsensüs notu {fmt(num(row, 'rec_mark'))} (1 al – 3 sat) · "
                     f"medyan hedef {fmt(target)} ({fmt(upside, 1)}%) · son çeyrek sürprizi HBK {fmt(num(row, 'eps_surprise_pct'), 1)}% / gelir {fmt(num(row, 'rev_surprise_pct'), 1)}%")
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


# ------------------------------------------------------------------------------------------ pipeline
def cmd_pipeline(a):
    days = days_of(a.horizon)
    mk = MARKETS[a.market]
    universe = a.universe or mk["default_universe"]
    out = stamp_dir(f"pipeline-{a.market}-{a.horizon}" if a.market != "turkey" else f"pipeline-{a.horizon}", a.out)
    cache = a.cache if a.market == "turkey" else a.cache / a.market
    out.mkdir(parents=True, exist_ok=True)
    say(f"1/7 {mk['label']} anlık görünüm ({universe}) → {out}")
    snap_args = ["--out", out / "snapshot", "--market", a.market]
    snap_args += ["--universe", "ALL"] if a.market == "turkey" else ["--universe", universe]
    if not run(ENG / "bist_snapshot.py", *snap_args, timeout=180):
        raise SystemExit("Anlık görünüm alınamadı (internet yok mu?). ChatGPT/claude.ai'de web taraması ya da CSV yükleme yolunu kullan.")
    snap = read_csv(out / "snapshot" / "snapshot.csv")
    say(f"2/7 Endeks ve kur geçmişi ({mk['bench_name']})")
    fetch_history([mk["bench"]] + (["USDTRY"] if a.market == "turkey" else []), cache / "chart", "5y", "chart", 20, 300, a.market)
    bench = cache / "chart" / f"{mk['bench']}.csv"
    hist_dir = None
    if not a.skip_history:
        codes = [r["ticker"] for r in snap if a.market != "turkey" or universe.upper() == "ALL" or r.get(f"in_{universe.lower()}") == "1"]
        say(f"3/7 {len(codes)} hisse için 2 yıllık kapanış geçmişi (toplu mod, önbellek 20 saat, süre bütçesi {a.history_budget} sn)")
        t0 = time.time()
        fetch_history(codes, cache / "spark2y", "2y", "spark", 20, a.history_budget, a.market)
        have = sum(1 for t in codes if hist_file(cache / "spark2y", t, a.market).exists())
        say(f"   {have}/{len(codes)} hisse geçmişi hazır ({time.time() - t0:.0f} sn)")
        hist_dir = cache / "spark2y"
    kap_all = out / "kap" / "kap_all.json"
    if a.market == "turkey":
        say(f"4/7 KAP akışı (son {a.kap_days} gün)")
        run(ENG / "kap_feed.py", "--all", "--days", a.kap_days, "--out", out / "kap", timeout=600)
    else:
        say("4/7 KAP yalnız BIST için; ABD'de SEC/şirket duyurularını web'den tarihiyle doğrula")
    say("5/7 Piyasa rejimi ve genişlik")
    reg_args = ["--snapshot", out / "snapshot" / "snapshot.csv", "--out", out / "regime", "--market-label", mk["label"],
                "--index-name", mk["bench_name"]]
    if bench.exists():
        reg_args += ["--index", bench]
    if a.market == "turkey" and (cache / "chart" / "USDTRY.csv").exists():
        reg_args += ["--usdtry", cache / "chart" / "USDTRY.csv"]
    if hist_dir:
        reg_args += ["--history-dir", hist_dir]
    run(REG, *reg_args, timeout=180)
    say(f"6/7 Çok şeritli tarama (vade {days} gün)")
    scan_args = ["--snapshot", out / "snapshot" / "snapshot.csv", "--horizon", a.horizon, "--universe", "ALL" if a.market != "turkey" else universe,
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
    fetch_history(finalists, cache / "chart", "2y", "chart", 20, 600, a.market)
    blocks = []
    for code in finalists:
        fdir = out / "finalists" / code
        hist = hist_file(cache / "chart", code, a.market)
        ta = ta_and_forecast(code, hist, bench, days, fdir) if hist.exists() and bench.exists() else None
        kap = fin = None
        if a.market == "turkey":
            run(ENG / "kap_feed.py", "--ticker", code, "--days", 90, "--details", 3, "--out", fdir, timeout=180)
            kap = read_json(fdir / f"kap_{code}.json")
            run(ENG / "financials_isy.py", code, "--quarters", 8, "--out", fdir, timeout=120)
            fin = read_json(fdir / f"{code}_financials.json")
        blocks.append(finalist_block(code, ranked.get(code, {}), ta, kap, fin))
    if a.market == "turkey":
        run(ENG / "macro_snapshot.py", "--out", out / "macro", timeout=120)
    write_report(out, a, days, seed, blocks, mk)
    if HTML.exists():
        run(HTML, "--run-dir", out, "--history-dir", cache / "chart", timeout=120)
    say(f"BİTTİ → {out / 'REPORT.md'}" + (f" ve {out / 'REPORT.html'}" if (out / "REPORT.html").exists() else ""))


def write_report(out, a, days, seed, blocks, mk):
    regime = read_json(out / "regime" / "regime.json") or {}
    macro = read_json(out / "macro" / "macro.json") or {}
    uni = seed["universe"]
    sources = "TradingView tarayıcı (gecikmeli), Yahoo, KAP, İş Yatırım, TCMB" if a.market == "turkey" else "TradingView tarayıcı (gecikmeli), Yahoo"
    lines = [f"# {mk['label']} pipeline raporu — vade {a.horizon} ({days} gün)", "",
             f"Veri kesimi {uni['data_cutoff']} · evren {uni['total_count']} → uygun {uni['eligible_count']} · dışlanan {uni['excluded_count']} · "
             f"kaynaklar: {sources}. Hepsi araştırma verisi; karar öncesi birincil kaynakla doğrula.", "",
             "> Bu rapor **ADAY** üretir, al/sat kararı değildir. Sıradaki adımlar SKILL.md'deki tam analiz hattına göre yapılır: temel derin analiz, "
             "yatırım komitesi (boğa-ayı), kırmızı takım, ön işlem kapısı, işlem planı, tahmin defterine kayıt.", ""]
    if regime:
        b, idx = regime.get("breadth", {}), regime.get("index", {})
        lines += ["## Piyasa rejimi", "",
                  f"**{regime.get('regime_label')}** · plan içi hisse maruziyeti {regime.get('equity_exposure_band_of_plan')} · işlem başı risk {regime.get('risk_per_trade_hint')}",
                  f"- {mk['bench_name']} {fmt(idx.get('close'))} (52h zirveden {fmt(idx.get('from_52w_high_pct'), 1)}%) · SMA50 üstü hisse %{fmt(b.get('pct_above_sma50'), 1)} · dağıtım günü {idx.get('distribution_days_25')} · takip günü {idx.get('follow_through_day') or 'yok'}",
                  "- Ayrıntı: regime/regime.md" + (" · makro: macro/macro.md" if macro else ""), ""]
    rates = macro.get("rates") or {}
    if rates.get("policy_rate_pct") is not None:
        lines += [f"Makro: politika faizi %{fmt(rates['policy_rate_pct'])} · TÜFE yıllık %{fmt(rates.get('cpi_yoy_pct'))} ({rates.get('period')}) · "
                  f"reel politika faizi %{fmt(rates.get('real_policy_rate_ex_post_pct'), 1)} → nakit/para piyasası fonu getirisi hisse getirisinin karşılaştırma çıtasıdır.", ""]
    summary = (out / "scan" / "scan_summary.md").read_text(encoding="utf-8") if (out / "scan" / "scan_summary.md").exists() else ""
    if summary:
        part = summary.split("## Bileşik sıralama", 1)
        lines += ["## Tarama", "", "## Bileşik sıralama" + part[1].split("## Bayrak sözlüğü")[0] if len(part) > 1 else summary, ""]
    lines += ["## Finalist kanıt paketleri", ""] + blocks
    lines += ["## Yapay zekânın tamamlaması gerekenler", "",
              "1. Her finalist için KAP finansal raporu + özel durumları oku (finalists/<KOD>/kap_*.md), TMS 29 ve tek seferlikleri ayıkla.",
              "2. Değerleme: sektör çarpanları + `valuation_models.py` (ters DCF, PD/DD–ROE, RIM); fiyatın ne fiyatladığını yaz.",
              "3. Taban oranı: `borsa.py taban` ile kurulumların geçmiş sonuçlarını dış görünüm olarak yaz.",
              "4. investment-committee modülü: 7 portföy yöneticisi sorusu, boğa-ayı tartışması, yatırımcı lensleri, risk komitesi.",
              "5. investment-red-team + pre-trade-investment-gate; yalnız geçenler için trade-management-exits ile plan ve adet (`portfolio_builder.py` ile portföy uyumu).",
              "6. Kararı forecast_ledger.py ile deftere yaz; vadesinde puanla ve dersi `--lesson` ile kaydet.",
              "7. Rejim 'DÜŞÜŞ TRENDİ' ise maruziyet bandına uy: nakit/mevduat/para piyasası fonu gerçek bir alternatiftir."]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------------------------------ ticker
def cmd_ticker(a):
    code = a.code.upper()
    days = days_of(a.horizon)
    mk = MARKETS[a.market]
    cache = a.cache if a.market == "turkey" else a.cache / a.market
    out = stamp_dir(code, a.out)
    out.mkdir(parents=True, exist_ok=True)
    say(f"{code}: anlık görünüm, 5y geçmiş, teknik, olasılık" + (", KAP, bilanço" if a.market == "turkey" else "") + f" → {out}")
    run(ENG / "bist_snapshot.py", "--tickers", code, "--market", a.market, "--out", out / "snapshot", timeout=120)
    fetch_history([code, mk["bench"]], cache / "chart", "5y", "chart", 20, 300, a.market)
    hist, bench = hist_file(cache / "chart", code, a.market), cache / "chart" / f"{mk['bench']}.csv"
    ta = ta_and_forecast(code, hist, bench, days, out) if hist.exists() and bench.exists() else None
    kap = fin = None
    if a.market == "turkey":
        run(ENG / "kap_feed.py", "--ticker", code, "--days", 120, "--details", 5, "--out", out, timeout=300)
        run(ENG / "financials_isy.py", code, "--quarters", 12, "--out", out, timeout=120)
        kap = read_json(out / f"kap_{code}.json")
        fin = read_json(out / f"{code}_financials.json")
    snap = read_csv(out / "snapshot" / "snapshot.csv") if (out / "snapshot" / "snapshot.csv").exists() else []
    row = snap[0] if snap else {"close": ta["indicators"]["close"] if ta else None}
    block = finalist_block(code, row, ta, kap, fin)
    files = "teknik.md, tahmin.json, snapshot/" + (f", kap_{code}.md, {code}_financials.md" if a.market == "turkey" else "")
    (out / "REPORT.md").write_text(f"# {code} kanıt paketi — vade {a.horizon}\n\n{block}\nDosyalar: {files}\n", encoding="utf-8")
    if HTML.exists():
        run(HTML, "--run-dir", out, "--history-dir", cache / "chart", "--code", code, timeout=120)
    say(f"BİTTİ → {out / 'REPORT.md'}" + (f" ve {out / 'REPORT.html'}" if (out / "REPORT.html").exists() else ""))


# ------------------------------------------------------------------------------------------ brief
def cmd_brief(a):
    out = stamp_dir("brief", a.out)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(TRT)
    say(f"Sabah bülteni → {out}")
    run(ENG / "bist_snapshot.py", "--out", out / "snapshot", timeout=180)
    fetch_history(["XU100", "USDTRY"], a.cache / "chart", "5y", "chart", 12, 300)
    run(ENG / "macro_snapshot.py", "--out", out / "macro", timeout=150)
    snap_path = out / "snapshot" / "snapshot.csv"
    if snap_path.exists():
        reg = ["--snapshot", snap_path, "--out", out / "regime", "--index", a.cache / "chart" / "XU100.csv"]
        if (a.cache / "chart" / "USDTRY.csv").exists():
            reg += ["--usdtry", a.cache / "chart" / "USDTRY.csv"]
        run(REG, *reg, timeout=180)
    run(ENG / "kap_feed.py", "--all", "--days", a.kap_days, "--important-only", "--out", out / "kap", timeout=600)
    if a.watchlist:
        run(WATCH, "--watchlist", a.watchlist, "--snapshot", snap_path, "--kap-days", max(1, a.kap_days), "--out", out / "watch", timeout=300)
    snap = read_csv(snap_path) if snap_path.exists() else []
    macro = read_json(out / "macro" / "macro.json") or {}
    regime = read_json(out / "regime" / "regime.json") or {}
    kap = read_json(out / "kap" / "kap_all.json") or {}
    watch = read_json(out / "watch" / "watch_report.json") or {}
    today = now.date()

    def dd(text):
        try:
            return (date.fromisoformat(str(text)[:10]) - today).days
        except (TypeError, ValueError):
            return None

    liquid = [r for r in snap if (num(r, "avg_turnover_30d_try") or 0) >= a.min_turnover and num(r, "change_pct") is not None]
    gainers = sorted(liquid, key=lambda r: -num(r, "change_pct"))[:6]
    losers = sorted(liquid, key=lambda r: num(r, "change_pct"))[:6]
    earnings = sorted([r for r in snap if dd(r.get("earnings_next")) is not None and 0 <= dd(r.get("earnings_next")) <= 7],
                      key=lambda r: (r.get("earnings_next"), -(num(r, "market_cap_try") or 0)))
    exdiv = sorted([r for r in snap if dd(r.get("exdiv_next")) is not None and 0 <= dd(r.get("exdiv_next")) <= 10],
                   key=lambda r: r.get("exdiv_next"))
    high_kap = [i for i in kap.get("items", []) if i.get("importance") == "HIGH" and i.get("event_class") not in ("SETTLEMENT_DEFAULT",)]
    rates = macro.get("rates") or {}
    mk = {m["name"]: m for m in macro.get("markets", []) if "error" not in m}
    lines = [f"# Günün notu — {now.strftime('%d.%m.%Y %H:%M')} (TSİ)", "",
             "> Yapay zekâ bu bülteni okuyup en üste **tek cümlelik ana fikri** yazar: bugün neyi değiştiriyor, neyi değiştirmiyor. "
             "Önemli bir şey yoksa \"plan dışı işlem gerektiren gelişme yok\" demek geçerli bir sonuçtur.", "",
             "## Piyasa ve rejim", ""]
    if regime:
        b, idx = regime.get("breadth", {}), regime.get("index", {})
        lines.append(f"- Rejim **{regime.get('regime_label')}** · maruziyet bandı {regime.get('equity_exposure_band_of_plan')} · XU100 {fmt(idx.get('close'))} "
                     f"(52h zirveden {fmt(idx.get('from_52w_high_pct'), 1)}%) · SMA50 üstü hisse %{fmt(b.get('pct_above_sma50'), 1)} · yükselen/düşen {b.get('advancers')}/{b.get('decliners')}")
    def bp(last, pct):
        return (last - last / (1 + pct / 100)) * 100 if last is not None and pct is not None else None

    for name in ("BIST 100", "BIST 30", "BIST Banka", "USD/TRY", "EUR/TRY", "Altın (ons, USD)", "Brent (USD)", "S&P 500", "VIX", "DXY", "ABD 10Y faiz (%)"):
        m = mk.get(name)
        if not m:
            continue
        if "faiz" in name:  # yields: show changes in basis points, not percent of the yield
            lines.append(f"- {name}: {fmt(m.get('last'))} · 1H {fmt(bp(m.get('last'), m.get('chg_1w_pct')), 0)} bp · "
                         f"1A {fmt(bp(m.get('last'), m.get('chg_1m_pct')), 0)} bp · YBB {fmt(bp(m.get('last'), m.get('chg_ytd_pct')), 0)} bp")
        else:
            lines.append(f"- {name}: {fmt(m.get('last'), 4 if 'TRY' in name else 2)} · 1H {fmt(m.get('chg_1w_pct'), 1)}% · 1A {fmt(m.get('chg_1m_pct'), 1)}% · YBB {fmt(m.get('chg_ytd_pct'), 1)}%")
    if rates:
        lines.append(f"- TCMB: politika faizi %{fmt(rates.get('policy_rate_pct'))} ({rates.get('policy_rate_since')}'den beri) · TÜFE %{fmt(rates.get('cpi_yoy_pct'))} ({rates.get('period')}) · reel %{fmt(rates.get('real_policy_rate_ex_post_pct'), 1)}")
    routine = [i for i in high_kap if i.get("event_class") == "BUYBACK"]
    other = [i for i in high_kap if i.get("event_class") != "BUYBACK"]
    lines += ["", f"## KAP — son {a.kap_days} gün, önemli ({len(high_kap)})", ""]
    for i in other[:14]:
        lines.append(f"- {str(i.get('published'))[:16]} · {','.join(i.get('tickers', [])[:4])} · {i['event_class']}: {(i.get('summary') or i.get('subject') or '')[:110]}")
    if routine:
        names = list(dict.fromkeys(t for i in routine for t in i.get("tickers", [])[:1]))
        lines.append(f"- Pay geri alım bildirimi: {len(names)} şirket ({', '.join(names[:30])}{' …' if len(names) > 30 else ''}) — "
                     "tutarı günlük hacme ve piyasa değerine oranla değerlendir; düşen piyasada rutin olabilir.")
    if not high_kap:
        lines.append("- Önemli bildirim yok.")
    lines += ["", "## Takvim (bu hafta)", ""]
    lines.append("- Bilanço (≤7 gün): " + (", ".join(f"{r['ticker']} {r['earnings_next'][5:]}" for r in earnings[:25]) or "yok"))
    lines.append("- Temettü hak kullanımı (≤10 gün): " + (", ".join(f"{r['ticker']} {r['exdiv_next'][5:]}" for r in exdiv[:20]) or "yok"))
    lines.append("- Makro takvim (TCMB PPK, TÜİK enflasyon, ABD verileri) bu betikte yok: resmi takvimlerden tarihiyle kontrol et.")
    lines += ["", f"## Hareketliler (günlük, likit ≥{a.min_turnover / 1e6:.0f} mn TL)", "",
              "- Yükselen: " + ", ".join(f"{r['ticker']} {num(r, 'change_pct'):+.1f}%" for r in gainers),
              "- Düşen: " + ", ".join(f"{r['ticker']} {num(r, 'change_pct'):+.1f}%" for r in losers)]
    if watch:
        lines += ["", "## İzleme listesi", ""]
        for it in watch.get("items", []):
            lines.append(f"- **{it['code']}** {fmt(it.get('close'))} ({fmt(it.get('change_pct'), 1)}%): {', '.join(it.get('alerts') or []) or 'tetikleyici yok'}")
    lines += ["", "## Bülten biçimi (yapay zekâ için)", "",
              "1. Ana fikir (tek cümle) · 2. Gece/sabah gelişmeleri ve portföye etkisi · 3. Bugünün olayları · 4. Fikirler: yalnız kanıtı olan, riskiyle birlikte · "
              "5. İzleme listesi uyarıları → plan tetikleyicisi · 6. Zaman damgası ve veri gecikmesi. Tahmin değil, bağlam ver; haber yoksa işlem de yok."]
    (out / "BRIEF.md").write_text("\n".join(lines), encoding="utf-8")
    say(f"BİTTİ → {out / 'BRIEF.md'}")


# ------------------------------------------------------------------------------------------ sector
def cmd_sector(a):
    out = stamp_dir("sector", a.out)
    out.mkdir(parents=True, exist_ok=True)
    run(ENG / "bist_snapshot.py", "--market", a.market, "--universe", MARKETS[a.market]["default_universe"], "--out", out / "snapshot", timeout=180)
    rows = read_csv(out / "snapshot" / "snapshot.csv")
    rows = [r for r in rows if num(r, "close")]

    def med(values):
        v = sorted(x for x in values if x is not None)
        return None if not v else v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2

    def share(flags):
        f = [x for x in flags if x is not None]
        return 100 * sum(f) / len(f) if f else None

    groups = {}
    for r in rows:
        groups.setdefault(r.get("sector") or "?", []).append(r)
    table = []
    for name, items in groups.items():
        cap = sum(num(r, "market_cap_try") or 0 for r in items)
        table.append({"Sektör": name, "n": len(items), "Piyasa değeri (mr)": cap / 1e9,
                      "1A%": med([num(r, "perf_1m_pct") for r in items]), "3A%": med([num(r, "perf_3m_pct") for r in items]),
                      "1Y%": med([num(r, "perf_1y_pct") for r in items]),
                      "SMA50 üstü%": share([num(r, "close") > num(r, "sma50") if num(r, "sma50") else None for r in items]),
                      "SMA200 üstü%": share([num(r, "close") > num(r, "sma200") if num(r, "sma200") else None for r in items]),
                      "F/K med": med([num(r, "pe_ttm") for r in items if (num(r, "pe_ttm") or 0) > 0]),
                      "PD/DD med": med([num(r, "pb") for r in items if (num(r, "pb") or 0) > 0]),
                      "ROE% med": med([num(r, "roe_pct") for r in items])})
    for t in table:
        if t["Sektör"] == "?":
            t["Sektör"] = "Sınıflanmamış"
    table.sort(key=lambda t: (t["Sektör"] == "Sınıflanmamış", -(t["3A%"] if t["3A%"] is not None else -999)))
    lines = [f"# Sektör görünümü — {datetime.now(TRT).strftime('%d.%m.%Y %H:%M')} ({MARKETS[a.market]['label']}, {len(rows)} hisse)", "",
             "Medyan değerler; sektör etiketi TradingView sınıflamasıdır. Göreli güç (3A) ve genişlik (SMA50/200 üstü) rotasyonu, çarpanlar ucuzluk/pahalılığı gösterir; "
             "enflasyon muhasebesi (TMS 29) ve bankaların farklı muhasebesi nedeniyle sektörler arası F/K kıyası sınırlıdır.", "",
             md_table(table, list(table[0].keys())) if table else "(veri yok)", ""]
    if a.name:
        needle = a.name.lower()
        members = [r for r in rows if needle in (r.get("sector") or "").lower() or needle in (r.get("industry") or "").lower()]
        members.sort(key=lambda r: -(num(r, "market_cap_try") or 0))
        view = [{"Kod": r["ticker"], "Alt sektör": (r.get("industry") or "")[:24], "Fiyat": num(r, "close"),
                 "Piy.değ.(mr)": (num(r, "market_cap_try") or 0) / 1e9, "1A%": num(r, "perf_1m_pct"), "3A%": num(r, "perf_3m_pct"),
                 "1Y%": num(r, "perf_1y_pct"), "F/K": num(r, "pe_ttm"), "PD/DD": num(r, "pb"), "ROE%": num(r, "roe_pct"),
                 "Net marj%": num(r, "net_margin_pct"), "Anl.": num(r, "rec_total")} for r in members[:40]]
        lines += [f"## {a.name} — üyeler (piyasa değerine göre, ilk 40)", "", md_table(view, list(view[0].keys())) if view else "(eşleşme yok)", "",
                  "Sektör derinlemesine analiz sırası: talep/fiyatlama sürücüleri → maliyet ve kur duyarlılığı → düzenleme → sektör çarpanları ve tarihsel bandı → "
                  "en iyi ve en kötü konumlanan şirket → sektörü bozacak koşul (public-equity-research modülü)."]
    (out / "SECTOR.md").write_text("\n".join(lines), encoding="utf-8")
    say(f"BİTTİ → {out / 'SECTOR.md'}")


# ------------------------------------------------------------------------------------------ others
def cmd_regime(a):
    out = stamp_dir("regime", a.out)
    run(ENG / "bist_snapshot.py", "--out", out / "snapshot", timeout=180)
    fetch_history(["XU100", "USDTRY"], a.cache / "chart", "5y", "chart", 20, 300)
    run(REG, "--snapshot", out / "snapshot" / "snapshot.csv", "--index", a.cache / "chart" / "XU100.csv",
        "--usdtry", a.cache / "chart" / "USDTRY.csv", "--out", out, timeout=180)
    run(ENG / "macro_snapshot.py", "--out", out, timeout=150)
    say(f"BİTTİ → {out / 'regime.md'} ve {out / 'macro.md'}")


def cmd_fon(a):
    rest = list(a.rest)
    if "--out" in rest:
        out = Path(rest[rest.index("--out") + 1])
        args = [a.action] + rest
    else:
        out = stamp_dir(f"fon-{a.action}", a.out)
        args = [a.action] + rest + ["--out", out]
    ok = run(ENG / "tefas_funds.py", *args, timeout=900, capture=True)
    if ok:
        print(ok.strip())
    say(f"BİTTİ → {out}")


def cmd_taban(a):
    days = days_of(a.horizon)
    out = stamp_dir(f"taban-{a.horizon}", a.out)
    hist = a.cache / "spark2y"
    if a.refresh or not any(hist.glob("*.csv")):
        snap_dir = out / "snapshot"
        run(ENG / "bist_snapshot.py", "--universe", a.universe, "--out", snap_dir, timeout=180)
        codes = [r["ticker"] for r in read_csv(snap_dir / "snapshot.csv")] if (snap_dir / "snapshot.csv").exists() else []
        say(f"{len(codes)} hisse için 2 yıllık geçmiş")
        fetch_history(codes, hist, "2y", "spark", 20, 600)
    fetch_history(["XU100"], a.cache / "chart", "5y", "chart", 20, 300)
    args = ["--history-dir", hist, "--horizon-days", days, "--step", a.step, "--out", out]
    if (a.cache / "chart" / "XU100.csv").exists():
        args += ["--benchmark", a.cache / "chart" / "XU100.csv"]
    res = run(BASE_RATES, *args, timeout=900, capture=True)
    if res:
        print(res.strip())
    say(f"BİTTİ → {out / 'base_rates.md'} (2 yıllık geçmiş = bir-iki rejim; uzun dönem için price_history.py --range 5y klasörü ver)")


def cmd_izle(a):
    out = stamp_dir("izle", a.out)
    res = run(WATCH, "--watchlist", a.watchlist, "--kap-days", a.kap_days, "--out", out, timeout=600, capture=True)
    if res:
        print(res.strip())
    say(f"BİTTİ → {out / 'watch_report.md'}")


def cmd_portfoy(a):
    out = stamp_dir("portfoy", a.out)
    codes = list(a.candidates)
    if a.holdings and Path(a.holdings).exists():
        codes += [r.get("code", "").upper() for r in read_csv(a.holdings) if r.get("code")]
    fetch_history(codes + ["XU100"], a.cache / "chart", "2y", "chart", 20, 600)
    run(ENG / "bist_snapshot.py", "--tickers", *codes, "--out", out / "snapshot", timeout=120)
    args = ["--history-dir", a.cache / "chart", "--candidates", *a.candidates, "--budget", a.budget, "--method", a.method,
            "--max-weight", a.max_weight, "--benchmark", a.cache / "chart" / "XU100.csv", "--out", out]
    if (out / "snapshot" / "snapshot.csv").exists():
        args += ["--snapshot", out / "snapshot" / "snapshot.csv"]
        if a.max_sector:
            args += ["--max-sector", a.max_sector]
    if a.holdings:
        args += ["--holdings", a.holdings]
    if a.stops:
        args += ["--stops", a.stops]
    res = run(PORTFOLIO, *args, timeout=300, capture=True)
    if res:
        print(res.strip())
    say(f"BİTTİ → {out / 'portfolio.md'}")


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
    p.add_argument("--market", default="turkey", choices=sorted(MARKETS))
    p.add_argument("--universe", help="ALL/XUTUM/XU100/XU050/XU030 (turkey, default ALL) or SPX/NDX/DJI (america, default SPX)")
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
    t.add_argument("--market", default="turkey", choices=sorted(MARKETS))
    t.add_argument("--out", type=Path)
    b = sub.add_parser("brief", help="morning note")
    b.add_argument("--watchlist", type=Path)
    b.add_argument("--kap-days", type=int, default=1)
    b.add_argument("--min-turnover", type=float, default=50_000_000)
    b.add_argument("--out", type=Path)
    s = sub.add_parser("sector")
    s.add_argument("--name", help="sector or industry substring for a member table, e.g. 'Finans'")
    s.add_argument("--market", default="turkey", choices=sorted(MARKETS))
    s.add_argument("--out", type=Path)
    r = sub.add_parser("regime")
    r.add_argument("--out", type=Path)
    k = sub.add_parser("kap")
    k.add_argument("--days", type=int, default=3)
    k.add_argument("--ticker", nargs="*")
    k.add_argument("--out", type=Path)
    m = sub.add_parser("macro")
    m.add_argument("--out", type=Path)
    f = sub.add_parser("fon", help="TEFAS: screen | fund CODE | compare A B ...")
    f.add_argument("action", choices=["screen", "fund", "compare"])
    f.add_argument("rest", nargs=argparse.REMAINDER, help="arguments passed to tefas_funds.py")
    f.add_argument("--out", type=Path)
    g = sub.add_parser("taban", help="historical base rates of setups")
    g.add_argument("--horizon", default="3m")
    g.add_argument("--universe", default="ALL")
    g.add_argument("--step", type=int, default=5)
    g.add_argument("--refresh", action="store_true")
    g.add_argument("--out", type=Path)
    w = sub.add_parser("izle", help="watchlist / position monitor")
    w.add_argument("--watchlist", type=Path, required=True)
    w.add_argument("--kap-days", type=int, default=3)
    w.add_argument("--out", type=Path)
    q = sub.add_parser("portfoy", help="risk-based allocation")
    q.add_argument("--candidates", nargs="+", required=True)
    q.add_argument("--budget", type=float, required=True)
    q.add_argument("--holdings", type=Path)
    q.add_argument("--method", default="erc", choices=["erc", "invvol", "equal"])
    q.add_argument("--max-weight", type=float, default=0.20)
    q.add_argument("--max-sector", type=float)
    q.add_argument("--stops")
    q.add_argument("--out", type=Path)
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    if a.cmd == "kap":
        out = stamp_dir("kap", a.out)
        args = ["--days", a.days, "--out", out] + (["--ticker", *a.ticker] if a.ticker else ["--all", "--important-only"])
        run(ENG / "kap_feed.py", *args, timeout=900)
        say(f"BİTTİ → {out}")
    elif a.cmd == "macro":
        out = stamp_dir("macro", a.out)
        run(ENG / "macro_snapshot.py", "--out", out, timeout=150)
        say(f"BİTTİ → {out / 'macro.md'}")
    else:
        {"pipeline": cmd_pipeline, "ticker": cmd_ticker, "brief": cmd_brief, "sector": cmd_sector, "regime": cmd_regime,
         "fon": cmd_fon, "taban": cmd_taban, "izle": cmd_izle, "portfoy": cmd_portfoy}[a.cmd](a)


if __name__ == "__main__":
    main()
