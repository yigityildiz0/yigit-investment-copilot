#!/usr/bin/env python3
"""Render a pipeline (or ticker) run folder as one self-contained HTML dashboard: regime and macro
cards, the ranked candidate table with lane bars and flags, finalist cards with an SVG price chart
(SMA50/SMA200, support/resistance/stop lines, P10–P90 horizon range), KAP highlights and sector
rotation. No external scripts, fonts or images; light and dark themes follow the system.

Usage:
  python scripts/report_html.py --run-dir borsa-out/20260928-1015-pipeline-3m
  python scripts/report_html.py --run-dir borsa-out/20260928-1015-THYAO --history-dir ~/.cache/yigit-investment-copilot/chart
"""

import argparse
import csv
import html
import json
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from pathlib import Path

LANES = ["momentum", "short_momentum", "trend", "setup", "reversal", "value", "quality", "growth", "low_risk",
         "catalyst", "expectations", "liquidity"]
LANE_TR = {"momentum": "Momentum", "short_momentum": "Kısa mom.", "trend": "Trend", "setup": "Kurulum", "reversal": "Dönüş",
           "value": "Değer", "quality": "Kalite", "growth": "Büyüme", "low_risk": "Düşük risk", "catalyst": "Katalizör",
           "expectations": "Beklenti", "liquidity": "Likidite"}
BAD_FLAGS = {"POMPA_COKUS", "POMPA_COKUS_SUPHESI", "TAVAN_SERISI", "SPK_YASAK_LISTESI", "VBTS_TEDBIR", "NEGATIF_OZKAYNAK",
             "FINANSAL_SIKINTI", "ZARAR", "ALTMAN_RISK", "VERI_UYUMSUZ", "HUKUKI_RISK", "PARABOLIK"}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--muted:#5b6270;--line:#e3e6eb;--accent:#2952cc;--up:#13804b;--down:#c8372d;
--warn:#b86e00;--chip:#eef1f6;--sma50:#d98a00;--sma200:#7d4cc9}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e8eaee;--muted:#9aa3b2;--line:#2a2f3a;
--accent:#7aa2ff;--up:#43c383;--down:#ff7a6e;--warn:#f0b35a;--chip:#222734;--sma50:#f0b35a;--sma200:#b99bff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 12px}
.sub{color:var(--muted);font-size:13px}.warnbar{margin:14px 0;padding:10px 14px;border-radius:10px;background:var(--chip);border-left:4px solid var(--warn);font-size:14px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi .v{font-size:22px;font-weight:650}.kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{position:sticky;top:0;background:var(--card);color:var(--muted);font-weight:600}td.l,th.l{text-align:left}
.chip{display:inline-block;padding:1px 7px;margin:1px;border-radius:999px;background:var(--chip);font-size:11.5px}
.chip.bad{color:var(--down);font-weight:600}.pos{color:var(--up)}.neg{color:var(--down)}
.fin{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}.fin h3{margin:0 0 2px;font-size:17px}
.fin ul{margin:8px 0 0;padding-left:18px;font-size:13.5px}.fin.single{grid-template-columns:minmax(0,820px)}.legend{font-size:11.5px;color:var(--muted)}
svg text{font:10.5px system-ui,sans-serif;fill:var(--muted)}footer{margin-top:36px;color:var(--muted);font-size:12.5px}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def f(x, d=2):
    if x is None:
        return "—"
    return f"{x:,.{d}f}"


def signed(x, d=1):
    if x is None:
        return "—"
    cls = "pos" if x > 0 else "neg" if x < 0 else ""
    return f'<span class="{cls}">{x:+.{d}f}</span>'


def read_json(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def flag_chips(flags):
    return "".join('<span class="chip%s">%s</span>' % (" bad" if x in BAD_FLAGS else "", esc(x)) for x in flags)


def lane_bars(row):
    w, h, gap = 7, 26, 2
    parts = []
    for i, lane in enumerate(LANES):
        v = num(row.get(f"lane_{lane}"))
        x = i * (w + gap)
        parts.append(f'<rect x="{x}" y="0" width="{w}" height="{h}" rx="1.5" fill="var(--chip)"/>')
        if v is not None:
            bh = max(1.5, v * h)
            parts.append(f'<rect x="{x}" y="{h - bh:.1f}" width="{w}" height="{bh:.1f}" rx="1.5" fill="var(--accent)"><title>{LANE_TR[lane]} {v:.2f}</title></rect>')
    return f'<svg width="{len(LANES) * (w + gap)}" height="{h}" role="img" aria-label="şerit puanları">{"".join(parts)}</svg>'


def load_series(path, n=260):
    rows = read_csv(path)
    out = []
    for r in rows:
        if str(r.get("complete", "1")) in ("0", "false", "False"):
            continue
        c, a = num(r.get("close")), num(r.get("adj_close"))
        if c:
            out.append((r["date"][:10], a or c))
    return out[-n:] if out else []


def sma(values, n):
    out, total = [], 0.0
    for i, v in enumerate(values):
        total += v
        if i >= n:
            total -= values[i - n]
        out.append(total / n if i >= n - 1 else None)
    return out


def price_chart(series, levels, quantiles, full_values=None):
    if len(series) < 20:
        return '<p class="sub">Fiyat geçmişi yok.</p>'
    W, H, L, R, T, B = 560, 220, 44, 70, 10, 22
    vals = [v for _, v in series]
    allv = full_values or vals
    s50 = sma(allv, 50)[-len(vals):]
    s200 = sma(allv, 200)[-len(vals):]
    extra = [x for x in (levels.get("bull_trigger"), levels.get("bear_trigger"), levels.get("atr_stop_2x"),
                         quantiles.get("p10"), quantiles.get("p90")) if x]
    lo, hi = min(vals + extra) * 0.98, max(vals + extra) * 1.02
    X = lambda i: L + (W - L - R) * i / (len(vals) - 1)
    Y = lambda v: T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    def path(seq):
        pts = [(X(i), Y(v)) for i, v in enumerate(seq) if v is not None]
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) if len(pts) > 1 else ""

    g = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="fiyat grafiği">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--line)"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 3:.1f}" text-anchor="end">{v:,.1f}</text>')
    tags = []
    for label, key, color, dash in (("Direnç", "bull_trigger", "var(--up)", "5 4"), ("Destek", "bear_trigger", "var(--warn)", "5 4"),
                                    ("Stop 2×ATR", "atr_stop_2x", "var(--down)", "2 3")):
        v = levels.get(key)
        if v and lo < v < hi:
            g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{color}" stroke-dasharray="{dash}"/>')
            tags.append([Y(v) + 3, label, color])
    tags.sort()
    for k in range(1, len(tags)):  # keep labels at least 11 px apart
        tags[k][0] = max(tags[k][0], tags[k - 1][0] + 11)
    for y, label, color in tags:
        g.append(f'<text x="{W - R + 4}" y="{y:.1f}" style="fill:{color}">{label}</text>')
    g.append(f'<path d="{path(s200)}" fill="none" stroke="var(--sma200)" stroke-width="1.3"/>')
    g.append(f'<path d="{path(s50)}" fill="none" stroke="var(--sma50)" stroke-width="1.3"/>')
    g.append(f'<path d="{path(vals)}" fill="none" stroke="var(--ink)" stroke-width="1.6"/>')
    if quantiles.get("p10") and quantiles.get("p90"):
        x = W - R + 40
        g.append(f'<line x1="{x}" x2="{x}" y1="{Y(quantiles["p90"]):.1f}" y2="{Y(quantiles["p10"]):.1f}" stroke="var(--accent)" stroke-width="7" stroke-linecap="round" opacity=".35"/>')
        if quantiles.get("p50"):
            g.append(f'<circle cx="{x}" cy="{Y(quantiles["p50"]):.1f}" r="3.5" fill="var(--accent)"/>')
        g.append(f'<text x="{x}" y="{H - 6}" text-anchor="middle">P10–P90</text>')
    g.append(f'<text x="{L}" y="{H - 6}">{esc(series[0][0])}</text><text x="{W - R}" y="{H - 6}" text-anchor="end">{esc(series[-1][0])}</text>')
    g.append("</svg>")
    return "".join(g)


def finalist_card(code, folder, ranked_row, history_dir):
    ta = read_json(folder / "teknik.json") or {}
    fc = read_json(folder / "tahmin.json") or {}
    kap = read_json(folder / f"kap_{code}.json") or {}
    fin = read_json(folder / f"{code}_financials.json") or {}
    full = load_series(history_dir / f"{code}.csv", n=100000) if history_dir else []
    series = full[-260:]
    chart = price_chart(series, ta.get("levels") or {}, fc.get("price_quantiles") or {}, [v for _, v in full][-460:] if full else None)
    p, st = ta.get("indicators") or {}, ta.get("setups") or {}
    tt = st.get("trend_template") or {}
    items = []
    if p:
        items.append(f"RSI {f(p.get('rsi14'), 0)} · ATR %{f(p.get('atr_pct'), 1)} · 1A {signed(p.get('ret_1m_pct'))}% · 1Y {signed(p.get('ret_1y_pct'))}%")
        items.append(f"Trend şablonu {tt.get('passed', '—')}/{tt.get('checked', '—')} · {esc(st.get('weinstein_stage', '—'))}")
    r = ranked_row or {}
    upside = num(r.get("analyst_upside"))
    n_analysts = num(r.get("rec_total")) or 0
    target, close = num(r.get("target_median")) or num(r.get("target_avg")), num(r.get("close"))
    if upside is None and n_analysts >= 2 and target and close:
        upside = target / close - 1
    items.append(f"F/K {f(num(r.get('pe_ttm')))} · PD/DD {f(num(r.get('pb')))} · ROE %{f(num(r.get('roe_pct')), 1)}"
                 + (f" · analist hedefi {signed(upside * 100)}% ({int(n_analysts)} analist; görüş, kanıt değil)" if upside is not None else ""))
    q = fc.get("price_quantiles") or {}
    if q:
        items.append(f"Vade sonu aralığı (model): P10 {f(q.get('p10'))} · P50 {f(q.get('p50'))} · P90 {f(q.get('p90'))}")
    m = fin.get("metrics") or {}
    if m:
        margin = m.get("operating_margin_pct")
        items.append(f"Bilanço {esc(m.get('latest_period'))}: net kâr TTM {f((m.get('net_income_ttm') or 0) / 1e9, 1)} mr"
                     + (f" · faaliyet marjı %{f(margin, 1)}" if margin is not None else ""))
    important = [i for i in kap.get("items", []) if i.get("importance") == "HIGH" and i.get("event_class") != "SETTLEMENT_DEFAULT"]
    buybacks = [i for i in important if i.get("event_class") == "BUYBACK"]
    for k in [i for i in important if i.get("event_class") != "BUYBACK"][:3]:
        items.append(f"KAP {esc(str(k.get('published'))[:10])} {esc(k.get('event_class'))}: {esc((k.get('summary') or k.get('subject') or '')[:90])}")
    if buybacks:
        items.append(f"KAP pay geri alımı: {len(buybacks)} bildirim (son {esc(str(buybacks[0].get('published'))[:10])})")
    flags = [x for x in (r.get("flags") or "").split(";") if x]
    chips = flag_chips(flags)
    return (f'<div class="card"><h3>{esc(code)} <span class="sub">{esc((r.get("name") or "")[:48])}</span></h3>'
            f'<div class="sub">{esc(r.get("sector") or "")} · fiyat {f(num(r.get("close")) or p.get("close"))} · skor {f(num(r.get("composite")), 3)}</div>'
            f'{chips}{chart}<div class="legend">— fiyat · <span style="color:var(--sma50)">SMA50</span> · <span style="color:var(--sma200)">SMA200</span> · '
            f'kesikli çizgiler plan seviyeleri · sağdaki bant model aralığıdır, tahmin değildir</div>'
            f'<ul>{"".join(f"<li>{x}</li>" for x in items)}</ul></div>')


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--history-dir", type=Path, default=Path.home() / ".cache" / "yigit-investment-copilot" / "chart")
    ap.add_argument("--code", help="ticker for a single-stock run folder")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    d = a.run_dir
    regime = read_json(d / "regime" / "regime.json") or {}
    macro = read_json(d / "macro" / "macro.json") or {}
    seed = read_json(d / "scan" / "funnel_seed.json") or {}
    ranked = read_csv(d / "scan" / "scan_ranked.csv")
    by_code = {r["ticker"]: r for r in ranked}
    title = "Borsa raporu"
    report_md = d / "REPORT.md"
    if report_md.exists():
        first = report_md.read_text(encoding="utf-8").splitlines()[0]
        title = first.lstrip("# ").strip() or title
    uni = seed.get("universe") or {}
    snap_meta = read_json(d / "snapshot" / "snapshot.meta.json") or {}
    if uni:
        subline = (f'Veri kesimi {esc(uni.get("data_cutoff", "—"))} · evren {esc(uni.get("total_count", "—"))} → uygun '
                   f'{esc(uni.get("eligible_count", "—"))} · kaynaklar gecikmeli ve resmi olmayan uç noktalar içerir')
    else:
        subline = f'Veri zamanı {esc(snap_meta.get("fetched_at", "—"))} · kaynaklar gecikmeli ve resmi olmayan uç noktalar içerir'
    body = [f"<h1>{esc(title)}</h1>", f'<div class="sub">{subline}</div>',
            '<div class="warnbar"><b>ADAY listesi — al/sat tavsiyesi değildir.</b> Her aday temel, teknik, haber ve risk incelemesinden, kırmızı takım ve ön işlem kapısından geçmeden işlem planına dönüşmez.</div>']
    cards = []
    if regime:
        idx, br = regime.get("index", {}), regime.get("breadth", {})
        cards.append(("Piyasa rejimi", esc(regime.get("regime_label")), f"maruziyet bandı {esc(regime.get('equity_exposure_band_of_plan'))}"))
        cards.append(("Endeks", f(idx.get("close"), 0), f"52h zirveden {f(idx.get('from_52w_high_pct'), 1)}% · dağıtım günü {esc(idx.get('distribution_days_25'))}"))
        cards.append(("Genişlik", f"%{f(br.get('pct_above_sma50'), 0)}", "SMA50 üstündeki hisseler"))
    rates = macro.get("rates") or {}
    if rates.get("policy_rate_pct") is not None:
        cards.append(("Politika faizi", f"%{f(rates['policy_rate_pct'])}", f"TÜFE %{f(rates.get('cpi_yoy_pct'))} · reel %{f(rates.get('real_policy_rate_ex_post_pct'), 1)}"))
    usd = next((m for m in macro.get("markets", []) if m.get("name") == "USD/TRY" and "error" not in m), None)
    if usd:
        cards.append(("USD/TRY", f(usd.get("last"), 4), f"1A {f(usd.get('chg_1m_pct'), 1)}% · 1Y {f(usd.get('chg_1y_pct'), 1)}%"))
    if cards:
        body.append('<div class="grid">' + "".join(f'<div class="card kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="sub">{s}</div></div>' for l, v, s in cards) + "</div>")
    if ranked:
        body.append("<h2>Bileşik sıralama (ilk 25)</h2>")
        head = ("<tr><th>#</th><th class='l'>Kod</th><th class='l'>Sektör</th><th>Fiyat</th><th>Skor</th><th class='l'>Şeritler</th>"
                "<th>1A %</th><th>3A %</th><th>F/K</th><th>PD/DD</th><th>ROE %</th><th>Hedef ↑ %</th><th class='l'>Bayraklar</th></tr>")
        rows = []
        for r in ranked[:25]:
            flags = [x for x in (r.get("flags") or "").split(";") if x]
            up = num(r.get("analyst_upside"))
            rows.append(f"<tr><td>{esc(r.get('rank'))}</td><td class='l'><b>{esc(r['ticker'])}</b></td><td class='l'>{esc((r.get('sector') or '')[:22])}</td>"
                        f"<td>{f(num(r.get('close')))}</td><td>{f(num(r.get('composite')), 3)}</td><td class='l'>{lane_bars(r)}</td>"
                        f"<td>{signed(num(r.get('perf_1m_pct')))}</td><td>{signed(num(r.get('perf_3m_pct')))}</td><td>{f(num(r.get('pe_ttm')), 1)}</td>"
                        f"<td>{f(num(r.get('pb')))}</td><td>{f(num(r.get('roe_pct')), 1)}</td><td>{signed(up * 100) if up is not None else '—'}</td>"
                        f"<td class='l'>{flag_chips(flags)}</td></tr>")
        body.append(f'<div class="tablewrap"><table>{head}{"".join(rows)}</table></div>')
        body.append('<div class="legend">Şerit çubukları soldan sağa: ' + ", ".join(LANE_TR[l] for l in LANES) + " (0–1 yüzdelik; yükseklik = puan).</div>")
    fins = [p for p in (d / "finalists").glob("*") if p.is_dir()] if (d / "finalists").exists() else []
    fins.sort(key=lambda p: (num(by_code.get(p.name, {}).get("rank")) or 10 ** 6, p.name))  # scan rank order
    single = (d / "teknik.json").exists()
    if fins or single:
        body.append("<h2>Finalistler</h2>" if fins else "<h2>Hisse görünümü</h2>")
        body.append('<div class="fin single">' if single and not fins else '<div class="fin">')
        if single:
            code = a.code or next((p.stem.split("_")[0] for p in d.glob("*_financials.json")), None) or d.name.split("-")[-1]
            snap = read_csv(d / "snapshot" / "snapshot.csv")
            body.append(finalist_card(code, d, snap[0] if snap else {}, a.history_dir))
        for p in fins:
            body.append(finalist_card(p.name, p, by_code.get(p.name, {}), a.history_dir))
        body.append("</div>")
    sectors = regime.get("sectors") or []
    if sectors:
        body.append("<h2>Sektör rotasyonu (3A medyan getiri)</h2>")
        rows = "".join(f"<tr><td class='l'>{esc(s['sector'])}</td><td>{s['n']}</td><td>{f(s.get('pct_above_sma50'), 0)}</td>"
                       f"<td>{signed(s.get('median_1m_pct'))}</td><td>{signed(s.get('median_3m_pct'))}</td><td>{signed(s.get('median_6m_pct'))}</td></tr>"
                       for s in sectors)
        body.append(f"<div class='tablewrap'><table><tr><th class='l'>Sektör</th><th>n</th><th>SMA50 üstü %</th><th>1A %</th><th>3A %</th><th>6A %</th></tr>{rows}</table></div>")
    body.append("<footer>Kaynaklar: TradingView tarayıcı uç noktası (gecikmeli, resmi değil), Yahoo Finance (resmi değil), KAP, İş Yatırım, TCMB. "
                "Skorlar araştırma önceliğidir; doğrulanmış getiri üstünlüğü değildir. Model aralıkları olasılık bandıdır, tahmin veya garanti değildir. "
                "Yatırım danışmanlığı değildir.</footer>")
    doc = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{''.join(body)}</main></body></html>")
    out = a.out or d / "REPORT.html"
    out.write_text(doc, encoding="utf-8")
    print(f"OK -> {out} ({len(doc) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
