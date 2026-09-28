#!/usr/bin/env python3
"""Macro and cross-asset snapshot for Türkiye-focused investing.

Sources:
- TCMB indicative exchange rates XML (official): https://www.tcmb.gov.tr/kurlar/today.xml
- Yahoo Finance spark endpoint (unofficial, delayed): BIST indices, USD/TRY, EUR/TRY, gold, Brent,
  VIX, DXY, US 10-year yield, S&P 500, EM and Türkiye ETFs — one bulk request.
Policy rate, CPI and CDS are NOT fetched here: take them from TCMB / TÜİK releases (or EVDS with the
user's own API key) and cite the release date.

Usage:
  python macro_snapshot.py --out macro
"""

import argparse
import math
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NetworkError, default_out, get_json, http, iso, md_table, now_trt, setup_stdout, write_json  # noqa: E402

SERIES = [
    ("XU100.IS", "BIST 100"), ("XU030.IS", "BIST 30"), ("XBANK.IS", "BIST Banka"), ("XUSIN.IS", "BIST Sınai"),
    ("TRY=X", "USD/TRY"), ("EURTRY=X", "EUR/TRY"), ("GC=F", "Altın (ons, USD)"), ("BZ=F", "Brent (USD)"),
    ("^VIX", "VIX"), ("DX-Y.NYB", "DXY"), ("^TNX", "ABD 10Y faiz (%)"), ("^GSPC", "S&P 500"),
    ("EEM", "Gelişen piyasalar ETF"), ("TUR", "iShares Türkiye ETF (USD)"),
]


def tcmb():
    raw = http("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=20)
    root = ET.fromstring(raw)
    out = {"bulletin_date": root.attrib.get("Tarih"), "bulletin_no": root.attrib.get("Bulten_No"), "rates": {}}
    for cur in root.findall("Currency"):
        code = cur.attrib.get("CurrencyCode")
        if code in ("USD", "EUR", "GBP", "CHF", "JPY", "CNY"):
            def val(tag):
                node = cur.find(tag)
                return float(node.text) if node is not None and node.text else None
            out["rates"][code] = {"unit": val("Unit"), "forex_buying": val("ForexBuying"), "forex_selling": val("ForexSelling")}
    return out


def spark(symbols):
    url = ("https://query1.finance.yahoo.com/v7/finance/spark?symbols=" + ",".join(symbols) +
           "&range=2y&interval=1d&indicators=close&includeTimestamps=true&includePrePost=false")
    data = get_json(url, timeout=30, retries=2)
    out = {}
    for item in (data.get("spark") or {}).get("result") or []:
        resp = (item.get("response") or [None])[0]
        if not resp:
            continue
        offset = timedelta(seconds=int(resp.get("meta", {}).get("gmtoffset") or 0))
        closes = (resp.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        series = [(datetime.fromtimestamp(t, timezone(offset)).date(), c) for t, c in zip(resp.get("timestamp") or [], closes) if c]
        out[item["symbol"]] = series
    return out


def change(series, days):
    if len(series) < 2:
        return None
    last_date, last = series[-1]
    target = last_date - timedelta(days=days)
    base = next((c for d, c in reversed(series) if d <= target), None)
    return (last / base - 1) * 100 if base else None


def ytd(series):
    if not series:
        return None
    last_date, last = series[-1]
    base = next((c for d, c in reversed(series) if d.year < last_date.year), None)
    return (last / base - 1) * 100 if base else None


def run(out_dir):
    result = {"fetched_at": iso(now_trt()), "tcmb": None, "markets": [], "notes": []}
    try:
        result["tcmb"] = tcmb()
    except (NetworkError, ET.ParseError) as exc:
        result["notes"].append(f"TCMB XML unavailable: {exc}")
    data = spark([s for s, _ in SERIES])
    for sym, label in SERIES:
        series = data.get(sym) or []
        if not series:
            result["markets"].append({"symbol": sym, "name": label, "error": "no data"})
            continue
        vol = None
        rets = [math.log(series[i][1] / series[i - 1][1]) for i in range(max(1, len(series) - 60), len(series))]
        if len(rets) > 10:
            m = sum(rets) / len(rets)
            vol = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(252) * 100
        highs = [c for _, c in series[-252:]]
        result["markets"].append({
            "symbol": sym, "name": label, "last": series[-1][1], "date": series[-1][0].isoformat(),
            "chg_1w_pct": change(series, 7), "chg_1m_pct": change(series, 30), "chg_3m_pct": change(series, 91),
            "chg_ytd_pct": ytd(series), "chg_1y_pct": change(series, 365), "vol_60d_ann_pct": vol,
            "from_52w_high_pct": (series[-1][1] / max(highs) - 1) * 100 if highs else None,
        })
    xu, usd = data.get("XU100.IS") or [], dict(data.get("TRY=X") or [])
    usd_series = [(d, c / usd[d]) for d, c in xu if d in usd and usd[d]]
    if usd_series:
        result["markets"].append({
            "symbol": "XU100/USDTRY", "name": "BIST 100 (USD bazlı)", "last": usd_series[-1][1], "date": usd_series[-1][0].isoformat(),
            "chg_1w_pct": change(usd_series, 7), "chg_1m_pct": change(usd_series, 30), "chg_3m_pct": change(usd_series, 91),
            "chg_ytd_pct": ytd(usd_series), "chg_1y_pct": change(usd_series, 365), "vol_60d_ann_pct": None,
            "from_52w_high_pct": (usd_series[-1][1] / max(c for _, c in usd_series[-252:]) - 1) * 100,
        })
    result["notes"].append("Politika faizi, TÜFE, CDS ve mevduat faizi bu betikte yok: TCMB/TÜİK duyurularından tarihiyle alın.")
    out_dir = Path(out_dir)
    write_json(out_dir / "macro.json", result)
    view = [{"Gösterge": m["name"], "Son": m.get("last"), "Tarih": m.get("date"), "1H%": m.get("chg_1w_pct"), "1A%": m.get("chg_1m_pct"),
             "3A%": m.get("chg_3m_pct"), "YBB%": m.get("chg_ytd_pct"), "1Y%": m.get("chg_1y_pct"), "52hZirveden%": m.get("from_52w_high_pct")}
            for m in result["markets"] if "error" not in m]
    lines = [f"# Makro ve piyasalar — {result['fetched_at']}", ""]
    if result["tcmb"]:
        r = result["tcmb"]["rates"]
        lines.append(f"TCMB gösterge kurları ({result['tcmb']['bulletin_date']}, bülten {result['tcmb']['bulletin_no']}): "
                     + ", ".join(f"{k} alış {v['forex_buying']} / satış {v['forex_selling']}" for k, v in r.items() if k in ("USD", "EUR")))
        lines.append("")
    lines.append(md_table(view, list(view[0].keys())) if view else "(piyasa verisi yok)")
    lines += ["", *[f"- {n}" for n in result["notes"]], "- Kaynak: TCMB (resmi) + Yahoo spark (resmi olmayan, gecikmeli)."]
    (out_dir / "macro.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = a.out or default_out("macro")
    try:
        result = run(out)
    except NetworkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    ok = [m for m in result["markets"] if "error" not in m]
    print(f"OK {len(ok)}/{len(result['markets'])} series, TCMB {'ok' if result['tcmb'] else 'missing'} -> {out}")
    for m in ok[:6]:
        print(f"  {m['name']}: {m['last']:.4g} (1A {m['chg_1m_pct'] or 0:+.1f}%, 1Y {m['chg_1y_pct'] or 0:+.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
