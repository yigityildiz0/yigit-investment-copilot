#!/usr/bin/env python3
"""Convert a user-supplied screener export (TradingView CSV, İş Yatırım table saved as CSV, a broker
export or a hand-made sheet) into the snapshot.csv schema used by bist_scan.py. For hosts without
internet (ChatGPT web/mobile, claude.ai): the user downloads/exports the table, uploads it, and this
script maps the columns offline.

Header matching is case/accent-insensitive with Turkish and English synonyms. Values in columns whose
header says "mn TL" / "milyon" are multiplied by 1e6; "mr TL" / "milyar" by 1e9. Numbers may use
Turkish formatting (1.234,56) or K/M/B suffixes.

Usage:
  python map_export.py export.csv --out snap          # writes snap/snapshot.csv + snapshot.meta.json
  python map_export.py export.csv --out snap --show   # also print the column mapping it used
"""

import argparse
import csv
import re
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import iso, now_trt, setup_stdout, sha256_file, write_csv, write_json  # noqa: E402

SYNONYMS = {
    "ticker": ["symbol", "sembol", "ticker", "kod", "hisse kodu", "hisse", "code", "name"],
    "name": ["description", "aciklama", "hisse adi", "sirket", "sirket adi", "company", "unvan"],
    "sector": ["sector", "sektor"],
    "industry": ["industry", "endustri", "alt sektor"],
    "close": ["price", "fiyat", "kapanis", "kapanis (tl)", "son", "son fiyat", "last", "close"],
    "change_pct": ["change %", "change", "degisim %", "gunluk degisim (%)", "degisim (%)", "gunluk %"],
    "volume": ["volume", "hacim (lot)", "hacim adet", "lot"],
    "turnover_try": ["volume*price", "value traded", "hacim (tl)", "islem hacmi (tl)", "hacim tl", "hacim"],
    "avg_volume_30d": ["average volume (30 day)", "average volume 30d", "ortalama hacim (30 gun)"],
    "market_cap_try": ["market capitalization", "market cap", "piyasa degeri", "piyasa degeri (tl)", "piyasa degeri (mn tl)"],
    "pe_ttm": ["price to earnings ratio (ttm)", "p/e", "pe", "f/k", "fk"],
    "pb": ["price to book (fq)", "price to book", "p/b", "pb", "pd/dd", "pddd"],
    "ev_ebitda": ["enterprise value to ebitda (ttm)", "ev/ebitda", "fd/favok"],
    "roe_pct": ["return on equity (ttm)", "return on equity", "roe", "roe (%)", "ozsermaye karliligi"],
    "net_margin_pct": ["net margin (ttm)", "net margin", "net kar marji", "net marj"],
    "net_income_ttm_try": ["net income (ttm)", "net income", "net kar", "net donem kari"],
    "rev_growth_yoy_pct": ["revenue growth (ttm yoy)", "revenue yoy growth", "satis buyumesi", "hasilat buyumesi"],
    "div_yield_pct": ["dividend yield %", "dividend yield", "temettu verimi", "temettu verimi (%)"],
    "perf_1w_pct": ["performance % 1 week", "perf %w", "1 hafta (%)", "haftalik %"],
    "perf_1m_pct": ["performance % 1 month", "perf %1m", "1 ay (%)", "aylik %", "1 aylik getiri"],
    "perf_3m_pct": ["performance % 3 months", "perf %3m", "3 ay (%)", "3 aylik getiri"],
    "perf_6m_pct": ["performance % 6 months", "perf %6m", "6 ay (%)"],
    "perf_ytd_pct": ["performance % year to date", "perf %ytd", "yil basindan (%)", "ybb (%)"],
    "perf_1y_pct": ["performance % 1 year", "perf %y", "1 yil (%)", "yillik %"],
    "rsi14": ["relative strength index (14)", "rsi (14)", "rsi14", "rsi"],
    "sma50": ["simple moving average (50)", "sma50", "sma (50)", "50 gunluk ortalama"],
    "sma200": ["simple moving average (200)", "sma200", "sma (200)", "200 gunluk ortalama"],
    "high_52w": ["52 week high", "52 hafta yuksek", "52 haftalik en yuksek"],
    "low_52w": ["52 week low", "52 hafta dusuk", "52 haftalik en dusuk"],
    "beta_1y": ["1-year beta", "beta"],
    "float_pct": ["free float %", "halka aciklik orani (%)", "halka aciklik"],
}
SCALE = [(re.compile(r"\b(mn|milyon|million)\b"), 1e6), (re.compile(r"\b(mr|milyar|billion|bn)\b"), 1e9)]


def norm(text):
    text = unicodedata.normalize("NFKD", (text or "").replace("İ", "I").replace("ı", "i")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_number(text):
    if text is None:
        return None
    s = str(text).strip().replace(" ", "").replace("%", "").replace("TRY", "").replace("TL", "").strip()
    if not s or s in {"-", "—", "n/a", "N/A"}:
        return None
    mult = 1.0
    if s[-1:] in "KkMmBbTt" and re.match(r"^-?[\d.,]+[KkMmBbTt]$", s):
        mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}[s[-1].lower()]
        s = s[:-1]
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    try:
        return float(s) * mult
    except ValueError:
        return None


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--delimiter", help="force a delimiter (default: sniff , ; tab)")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    raw = a.export.read_text(encoding="utf-8-sig", errors="replace")
    delim = a.delimiter or csv.Sniffer().sniff(raw[:5000], delimiters=",;\t").delimiter
    rows = list(csv.DictReader(raw.splitlines(), delimiter=delim))
    if not rows:
        raise SystemExit("export has no rows")
    headers = list(rows[0].keys())
    mapping, used = {}, set()
    for target, names in SYNONYMS.items():
        for h in headers:
            nh = norm(h)
            base = re.sub(r"\(.*?\)", "", nh).strip()
            if h in used:
                continue
            if nh in names or base in names:
                mapping[target] = h
                used.add(h)
                break
    if "ticker" not in mapping or "close" not in mapping:
        raise SystemExit(f"could not find ticker/price columns; headers were: {headers}")
    out_rows = []
    for r in rows:
        t = (r.get(mapping["ticker"]) or "").strip().upper()
        t = t.split(":")[-1].replace(".IS", "").replace(".E", "")
        if not t:
            continue
        row = {"symbol": f"BIST:{t}", "ticker": t, "update_mode": "user-export"}
        for target, header in mapping.items():
            if target == "ticker":
                continue
            if target in ("name", "sector", "industry"):
                row[target] = (r.get(header) or "").strip()
                continue
            value = parse_number(r.get(header))
            for pattern, factor in SCALE:
                if value is not None and pattern.search(norm(header)):
                    value *= factor
            row[target] = value
        if row.get("avg_volume_30d") and row.get("close"):
            row["avg_turnover_30d_try"] = row["avg_volume_30d"] * row["close"]
        elif row.get("turnover_try"):
            row["avg_turnover_30d_try"] = row["turnover_try"]
        out_rows.append(row)
    a.out.mkdir(parents=True, exist_ok=True)
    fields = ["symbol", "ticker", "name", "sector", "industry"] + [k for k in SYNONYMS if k not in ("ticker", "name", "sector", "industry")] + ["avg_turnover_30d_try", "update_mode"]
    path = write_csv(a.out / "snapshot.csv", out_rows, fields)
    meta = {"source": f"user export: {a.export.name}", "source_tier": "user-supplied; verify decisive facts",
            "fetched_at": iso(datetime.fromtimestamp(a.export.stat().st_mtime, now_trt().tzinfo)),
            "latency": "as exported by the user", "universe": "USER", "rows": len(out_rows),
            "tickers": [r["ticker"] for r in out_rows], "csv": path.name, "csv_sha256": sha256_file(path),
            "column_mapping": mapping, "unmapped_headers": [h for h in headers if h not in used]}
    write_json(a.out / "snapshot.meta.json", meta)
    print(f"OK {len(out_rows)} rows -> {path}")
    missing = [k for k in ("market_cap_try", "pe_ttm", "pb", "roe_pct", "perf_3m_pct", "sma50", "sma200", "rsi14") if k not in mapping]
    if missing:
        print("missing (lanes will be thinner): " + ", ".join(missing))
    if a.show:
        for k, v in mapping.items():
            print(f"  {k:<20} <- {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
