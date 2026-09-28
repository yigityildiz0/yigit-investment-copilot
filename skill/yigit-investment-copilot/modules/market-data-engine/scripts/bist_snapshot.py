#!/usr/bin/env python3
"""Download a one-shot snapshot of every Borsa İstanbul stock with prices, liquidity,
valuation, profitability, growth, risk and technical fields.

Source: TradingView's public screener endpoint (scanner.tradingview.com/turkey/scan). It is an
undocumented, unofficial endpoint: data are delayed (~15 min), fundamentals are secondary data,
and the service can change without notice. Use it for broad screening only; verify finalists with
KAP filings and a second price source.

Usage:
  python bist_snapshot.py --out borsa-out/snap            # all listed BIST stocks
  python bist_snapshot.py --universe XU100 --out snap100   # index members only
  python bist_snapshot.py --tickers THYAO ASELS --out one  # specific names
"""

import argparse
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (NetworkError, TRT, default_out, fnum, get_json, iso, market_status, now_trt,  # noqa: E402
                    setup_stdout, sha256_file, write_csv, write_json)

ENDPOINT = "https://scanner.tradingview.com/turkey/scan"
INDEX_SETS = ("XU030", "XU050", "XU100", "XUTUM")

# (TradingView field, output column, kind)
FIELDS = [
    ("name", "ticker", "str"), ("description", "name", "str"), ("sector.tr", "sector", "str"),
    ("industry.tr", "industry", "str"), ("sector", "sector_en", "str"),
    ("close", "close", "num"), ("change", "change_pct", "num"), ("gap", "gap_pct", "num"),
    ("volume", "volume", "num"), ("Value.Traded", "turnover_try", "num"),
    ("average_volume_10d_calc", "avg_volume_10d", "num"), ("average_volume_30d_calc", "avg_volume_30d", "num"),
    ("average_volume_90d_calc", "avg_volume_90d", "num"), ("relative_volume_10d_calc", "rel_volume_10d", "num"),
    ("market_cap_basic", "market_cap_try", "num"), ("enterprise_value_current", "ev_try", "num"),
    ("total_shares_outstanding", "shares_out", "num"), ("float_shares_percent_current", "float_pct", "num"),
    ("price_earnings_ttm", "pe_ttm", "num"), ("price_book_fq", "pb", "num"), ("price_sales_ratio", "ps", "num"),
    ("enterprise_value_ebitda_ttm", "ev_ebitda", "num"), ("price_free_cash_flow_ttm", "p_fcf", "num"),
    ("dividends_yield_current", "div_yield_pct", "num"),
    ("return_on_equity", "roe_pct", "num"), ("return_on_assets", "roa_pct", "num"),
    ("return_on_invested_capital", "roic_pct", "num"), ("gross_margin", "gross_margin_pct", "num"),
    ("operating_margin", "op_margin_pct", "num"), ("net_margin", "net_margin_pct", "num"),
    ("debt_to_equity", "debt_to_equity", "num"), ("current_ratio", "current_ratio", "num"),
    ("net_debt", "net_debt_try", "num"), ("free_cash_flow", "fcf_try", "num"),
    ("total_revenue_ttm", "revenue_ttm_try", "num"), ("net_income_ttm", "net_income_ttm_try", "num"),
    ("ebitda_ttm", "ebitda_ttm_try", "num"),
    ("total_revenue_yoy_growth_ttm", "rev_growth_yoy_pct", "num"),
    ("net_income_yoy_growth_ttm", "ni_growth_yoy_pct", "num"),
    ("earnings_per_share_diluted_yoy_growth_ttm", "eps_growth_yoy_pct", "num"),
    ("total_revenue_qoq_growth_fq", "rev_growth_qoq_pct", "num"),
    ("net_income_qoq_growth_fq", "ni_growth_qoq_pct", "num"),
    ("piotroski_f_score_ttm", "piotroski", "num"), ("altman_z_score_ttm", "altman_z", "num"),
    ("beta_1_year", "beta_1y", "num"),
    ("Perf.W", "perf_1w_pct", "num"), ("Perf.1M", "perf_1m_pct", "num"), ("Perf.3M", "perf_3m_pct", "num"),
    ("Perf.6M", "perf_6m_pct", "num"), ("Perf.YTD", "perf_ytd_pct", "num"), ("Perf.Y", "perf_1y_pct", "num"),
    ("price_52_week_high", "high_52w", "num"), ("price_52_week_low", "low_52w", "num"),
    ("High.3M", "high_3m", "num"), ("Low.3M", "low_3m", "num"), ("all_time_high", "ath", "num"),
    ("RSI", "rsi14", "num"), ("ADX", "adx14", "num"), ("MACD.macd", "macd", "num"),
    ("MACD.signal", "macd_signal", "num"), ("Stoch.K", "stoch_k", "num"), ("ATR", "atr14", "num"),
    ("SMA20", "sma20", "num"), ("SMA50", "sma50", "num"), ("SMA100", "sma100", "num"),
    ("SMA150", "sma150", "num"), ("SMA200", "sma200", "num"), ("EMA20", "ema20", "num"),
    ("EMA50", "ema50", "num"), ("EMA200", "ema200", "num"), ("BB.upper", "bb_upper", "num"),
    ("BB.lower", "bb_lower", "num"), ("Volatility.D", "volatility_d_pct", "num"),
    ("Volatility.W", "volatility_w_pct", "num"), ("Volatility.M", "volatility_m_pct", "num"),
    ("VWAP", "vwap", "num"), ("Recommend.All", "tv_rating", "num"), ("Recommend.MA", "tv_rating_ma", "num"),
    ("Recommend.Other", "tv_rating_osc", "num"),
    ("earnings_release_next_date", "earnings_next", "date"), ("earnings_release_date", "earnings_last", "date"),
    ("update_mode", "update_mode", "str"), ("typespecs", "typespecs", "list"),
]


def payload(columns, symbols=None, tickers=None, start=0, end=1500):
    body = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "options": {"lang": "tr"},
        "markets": ["turkey"],
        "symbols": {"query": {"types": []}, "tickers": tickers or []},
        "columns": columns,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [start, end],
    }
    if symbols:
        body["symbols"] = {"symbolset": symbols}
    return body


def scan(columns, symbols=None, tickers=None):
    data = get_json(ENDPOINT, json_body=payload(columns, symbols, tickers),
                    headers={"Origin": "https://tr.tradingview.com", "Referer": "https://tr.tradingview.com/"})
    if not isinstance(data, dict) or "data" not in data:
        raise NetworkError("TradingView scanner returned an unexpected payload")
    return data


def convert(kind, value):
    if value is None:
        return None
    if kind == "num":
        return fnum(value)
    if kind == "date":
        try:
            return datetime.fromtimestamp(float(value), TRT).date().isoformat()
        except (TypeError, ValueError, OSError):
            return None
    if kind == "list":
        return ";".join(value) if isinstance(value, list) else str(value)
    return str(value).strip()


def index_members(code):
    data = scan(["name"], symbols=[f"SYML:BIST;{code}"])
    return {row["d"][0] for row in data.get("data", [])}


def fetch_snapshot(universe="ALL", tickers=None):
    columns = [field for field, _, _ in FIELDS]
    symbols = None
    if universe and universe.upper() != "ALL":
        symbols = [f"SYML:BIST;{universe.upper()}"]
    tv_tickers = [f"BIST:{t.strip().upper()}" for t in tickers] if tickers else None
    # Split the column list in two to stay well below any request-size limit, then merge.
    half = len(columns) // 2
    first = scan(columns[:half], symbols, tv_tickers)
    second = scan(["name"] + columns[half:], symbols, tv_tickers)
    extra = {row["s"]: row["d"] for row in second.get("data", [])}
    rows = []
    for item in first.get("data", []):
        values = list(item["d"])
        tail = extra.get(item["s"])
        values += tail[1:] if tail else [None] * (len(columns) - half)
        row = {"symbol": item["s"]}
        for (field, name, kind), value in zip(FIELDS, values):
            row[name] = convert(kind, value)
        rows.append(row)
    members = {}
    for code in INDEX_SETS:
        try:
            members[code] = index_members(code)
        except NetworkError:
            members[code] = None
    for row in rows:
        for code in INDEX_SETS:
            row[f"in_{code.lower()}"] = None if members[code] is None else int(row["ticker"] in members[code])
        close, avg30 = row.get("close"), row.get("avg_volume_30d")
        row["avg_turnover_30d_try"] = close * avg30 if close and avg30 else None
    return rows, {code: (sorted(m) if m is not None else None) for code, m in members.items()}, first.get("totalCount")


def run(out_dir, universe="ALL", tickers=None):
    out_dir = Path(out_dir)
    fetched = now_trt()
    rows, members, total = fetch_snapshot(universe, tickers)
    if not rows:
        raise NetworkError("snapshot is empty")
    csv_path = write_csv(out_dir / "snapshot.csv", rows, ["symbol"] + [name for _, name, _ in FIELDS]
                         + [f"in_{c.lower()}" for c in INDEX_SETS] + ["avg_turnover_30d_try"])
    modes = sorted({row.get("update_mode") or "unknown" for row in rows})
    meta = {
        "source": "TradingView screener endpoint scanner.tradingview.com/turkey/scan (unofficial, public)",
        "source_tier": "secondary aggregator — screening only; verify decisive facts with KAP/official data",
        "fetched_at": iso(fetched),
        "market_status_at_fetch": market_status(fetched),
        "latency": "delayed (update_mode: " + ", ".join(modes) + "); fundamentals as reported by the vendor",
        "universe": universe.upper() if not tickers else "TICKERS",
        "reported_total": total,
        "rows": len(rows),
        "tickers": [row["ticker"] for row in rows],
        "index_members": members,
        "csv": csv_path.name,
        "csv_sha256": sha256_file(csv_path),
        "caveats": [
            "TMS 29 inflation accounting: growth and margin fields may mix restated and nominal periods.",
            "Banks/insurers: EV/EBITDA, margins and current ratio are not meaningful; use sector-specific metrics.",
            "Performance fields are vendor-calculated; corporate-action adjustments can differ from KAP/İş Yatırım.",
        ],
    }
    write_json(out_dir / "snapshot.meta.json", meta)
    return csv_path, meta


def main():
    setup_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--universe", default="ALL", help="ALL (default), XU030, XU050, XU100, XUTUM or another BIST index code")
    parser.add_argument("--tickers", nargs="*", help="optional explicit ticker list")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or default_out("snapshot")
    try:
        csv_path, meta = run(out, args.universe, args.tickers)
    except NetworkError as exc:
        print(f"ERROR: {exc}. If this host has no internet (e.g. a sandbox), use web browsing or an uploaded CSV instead.", file=sys.stderr)
        return 3
    print(f"OK {meta['rows']} rows -> {csv_path}")
    print(f"fetched_at {meta['fetched_at']} | {meta['latency']} | sha256 {meta['csv_sha256'][:16]}")
    counts = {code: (len(v) if v is not None else "n/a") for code, v in meta["index_members"].items()}
    print(f"index members: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
