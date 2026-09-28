#!/usr/bin/env python3
"""Download a one-shot snapshot of every listed stock (Borsa İstanbul by default, or US markets)
with prices, liquidity, valuation, profitability, growth, analyst consensus, surprises, dividends,
risk and technical fields.

Source: TradingView's public screener endpoint (scanner.tradingview.com/<market>/scan). It is an
undocumented, unofficial endpoint: data are delayed (~15 min), fundamentals and analyst figures are
secondary data, and the service can change without notice. Use it for broad screening only; verify
finalists with KAP / SEC filings and a second price source.

Usage:
  python bist_snapshot.py --out snap                         # all listed BIST stocks
  python bist_snapshot.py --universe XU100 --out snap100     # index members only
  python bist_snapshot.py --tickers THYAO ASELS --out one    # specific names
  python bist_snapshot.py --market america --universe SPX --out spx   # S&P 500 members
"""

import argparse
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (NetworkError, TRT, default_out, fnum, get_json, iso, market_status, now_trt,  # noqa: E402
                    setup_stdout, sha256_file, write_csv, write_json)

MARKETS = {
    "turkey": {"prefix": "BIST", "indexes": {"XU030": "SYML:BIST;XU030", "XU050": "SYML:BIST;XU050",
                                            "XU100": "SYML:BIST;XU100", "XUTUM": "SYML:BIST;XUTUM"}, "primary_only": False},
    "america": {"prefix": None, "indexes": {"SPX": "SYML:SP;SPX", "NDX": "SYML:NASDAQ;NDX", "DJI": "SYML:DJ;DJI"},
                "primary_only": True},
}

# (TradingView field, output column, kind)
FIELDS = [
    ("name", "ticker", "str"), ("description", "name", "str"), ("sector.tr", "sector", "str"),
    ("industry.tr", "industry", "str"), ("sector", "sector_en", "str"), ("exchange", "exchange", "str"),
    ("currency", "currency", "str"),
    ("close", "close", "num"), ("change", "change_pct", "num"), ("gap", "gap_pct", "num"),
    ("volume", "volume", "num"), ("Value.Traded", "turnover_try", "num"),
    ("average_volume_10d_calc", "avg_volume_10d", "num"), ("average_volume_30d_calc", "avg_volume_30d", "num"),
    ("average_volume_90d_calc", "avg_volume_90d", "num"), ("relative_volume_10d_calc", "rel_volume_10d", "num"),
    ("market_cap_basic", "market_cap_try", "num"), ("enterprise_value_current", "ev_try", "num"),
    ("total_shares_outstanding", "shares_out", "num"), ("float_shares_percent_current", "float_pct", "num"),
    ("price_earnings_ttm", "pe_ttm", "num"), ("price_book_fq", "pb", "num"), ("price_sales_ratio", "ps", "num"),
    ("enterprise_value_ebitda_ttm", "ev_ebitda", "num"), ("enterprise_value_to_revenue_ttm", "ev_sales", "num"),
    ("price_free_cash_flow_ttm", "p_fcf", "num"), ("price_to_cash_f_operating_activities_ttm", "p_cfo", "num"),
    ("price_earnings_growth_ttm", "peg", "num"), ("dividends_yield_current", "div_yield_pct", "num"),
    ("dividend_payout_ratio_ttm", "payout_pct", "num"),
    ("ex_dividend_date_upcoming", "exdiv_next", "date"), ("ex_dividend_date_recent", "exdiv_last", "date"),
    ("return_on_equity", "roe_pct", "num"), ("return_on_assets", "roa_pct", "num"),
    ("return_on_invested_capital", "roic_pct", "num"), ("gross_margin", "gross_margin_pct", "num"),
    ("operating_margin", "op_margin_pct", "num"), ("net_margin", "net_margin_pct", "num"),
    ("debt_to_equity", "debt_to_equity", "num"), ("current_ratio", "current_ratio", "num"),
    ("net_debt", "net_debt_try", "num"), ("total_debt_fq", "total_debt_try", "num"),
    ("cash_n_equivalents_fq", "cash_try", "num"), ("free_cash_flow", "fcf_try", "num"),
    ("capital_expenditures_ttm", "capex_ttm_try", "num"),
    ("total_revenue_ttm", "revenue_ttm_try", "num"), ("net_income_ttm", "net_income_ttm_try", "num"),
    ("ebitda_ttm", "ebitda_ttm_try", "num"),
    ("total_revenue_yoy_growth_ttm", "rev_growth_yoy_pct", "num"),
    ("net_income_yoy_growth_ttm", "ni_growth_yoy_pct", "num"),
    ("earnings_per_share_diluted_yoy_growth_ttm", "eps_growth_yoy_pct", "num"),
    ("total_revenue_qoq_growth_fq", "rev_growth_qoq_pct", "num"),
    ("net_income_qoq_growth_fq", "ni_growth_qoq_pct", "num"),
    ("revenue_surprise_percent_fq", "rev_surprise_pct", "num"), ("eps_surprise_percent_fq", "eps_surprise_pct", "num"),
    ("earnings_per_share_forecast_next_fq", "eps_fcst_next_fq", "num"), ("revenue_forecast_next_fq", "rev_fcst_next_fq", "num"),
    ("price_target_average", "target_avg", "num"), ("price_target_median", "target_median", "num"),
    ("price_target_high", "target_high", "num"), ("price_target_low", "target_low", "num"),
    ("recommendation_mark", "rec_mark", "num"), ("recommendation_buy", "rec_buy", "num"),
    ("recommendation_over", "rec_over", "num"), ("recommendation_hold", "rec_hold", "num"),
    ("recommendation_under", "rec_under", "num"), ("recommendation_sell", "rec_sell", "num"),
    ("recommendation_total", "rec_total", "num"),
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
CHUNK_COLUMNS = 60
PAGE = 1500


def endpoint(market):
    return f"https://scanner.tradingview.com/{market}/scan"


def payload(market, columns, symbols=None, tickers=None, start=0, end=PAGE):
    filters = [{"left": "type", "operation": "equal", "right": "stock"}]
    if MARKETS.get(market, {}).get("primary_only"):
        filters.append({"left": "is_primary", "operation": "equal", "right": True})
    body = {
        "filter": filters,
        "options": {"lang": "tr"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": tickers or []},
        "columns": columns,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [start, end],
    }
    if symbols:
        body["symbols"] = {"symbolset": symbols}
    return body


def scan(market, columns, symbols=None, tickers=None, start=0, end=PAGE):
    data = get_json(endpoint(market), json_body=payload(market, columns, symbols, tickers, start, end),
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


def index_members(market, symbolset):
    out, start = set(), 0
    while True:
        data = scan(market, ["name"], symbols=[symbolset], start=start, end=start + PAGE)
        out |= {row["d"][0] for row in data.get("data", [])}
        start += PAGE
        if start >= (data.get("totalCount") or 0):
            return out


def fetch_rows(market, symbols, tickers, max_rows):
    """Page through the universe for every column chunk and merge rows by symbol."""
    columns = [field for field, _, _ in FIELDS]
    chunks = [columns[i:i + CHUNK_COLUMNS] for i in range(0, len(columns), CHUNK_COLUMNS)]
    merged, order, total = {}, [], None
    for c_index, chunk in enumerate(chunks):
        cols = chunk if c_index == 0 else ["name"] + chunk
        start = 0
        while True:
            end = min(start + PAGE, max_rows) if max_rows else start + PAGE
            data = scan(market, cols, symbols, tickers, start, end)
            total = data.get("totalCount") if total is None else total
            for item in data.get("data", []):
                values = item["d"] if c_index == 0 else item["d"][1:]
                if item["s"] not in merged:
                    if c_index:
                        continue  # row appeared only in a later page; skip to keep columns aligned
                    merged[item["s"]] = {}
                    order.append(item["s"])
                for (field, name, kind), value in zip(FIELDS[sum(len(c) for c in chunks[:c_index]):], values):
                    merged[item["s"]][name] = convert(kind, value)
            start = end
            limit = min(total or 0, max_rows) if max_rows else (total or 0)
            if start >= limit:
                break
    rows = []
    for symbol in order:
        row = {"symbol": symbol}
        row.update(merged[symbol])
        rows.append(row)
    return rows, total


def fetch_snapshot(universe="ALL", tickers=None, market="turkey", max_rows=None):
    spec = MARKETS.get(market, {"prefix": None, "indexes": {}, "primary_only": True})
    symbols = None
    uni = (universe or "ALL").upper()
    if uni != "ALL":
        symbols = [spec["indexes"].get(uni, f"SYML:{spec['prefix'] or market.upper()};{uni}")]
    tv_tickers = None
    if tickers:
        prefix = spec["prefix"]
        tv_tickers = [t.strip().upper() if ":" in t else f"{prefix}:{t.strip().upper()}" if prefix else t.strip().upper()
                      for t in tickers]
    rows, total = fetch_rows(market, symbols, tv_tickers, max_rows)
    members = {}
    for code, symbolset in spec["indexes"].items():
        try:
            members[code] = index_members(market, symbolset)
        except NetworkError:
            members[code] = None
    for row in rows:
        for code in spec["indexes"]:
            row[f"in_{code.lower()}"] = None if members[code] is None else int(row["ticker"] in members[code])
        close, avg30 = row.get("close"), row.get("avg_volume_30d")
        row["avg_turnover_30d_try"] = close * avg30 if close and avg30 else None
    return rows, {code: (sorted(m) if m is not None else None) for code, m in members.items()}, total


def run(out_dir, universe="ALL", tickers=None, market="turkey", max_rows=None):
    out_dir = Path(out_dir)
    fetched = now_trt()
    rows, members, total = fetch_snapshot(universe, tickers, market, max_rows)
    if not rows:
        raise NetworkError("snapshot is empty")
    index_cols = [f"in_{c.lower()}" for c in MARKETS.get(market, {"indexes": {}})["indexes"]]
    csv_path = write_csv(out_dir / "snapshot.csv", rows, ["symbol"] + [name for _, name, _ in FIELDS] + index_cols
                         + ["avg_turnover_30d_try"])
    modes = sorted({row.get("update_mode") or "unknown" for row in rows})
    currencies = sorted({row.get("currency") or "?" for row in rows})
    meta = {
        "source": f"TradingView screener endpoint scanner.tradingview.com/{market}/scan (unofficial, public)",
        "source_tier": "secondary aggregator — screening only; verify decisive facts with KAP/SEC/official data",
        "market": market,
        "currency": currencies[0] if len(currencies) == 1 else currencies,
        "fetched_at": iso(fetched),
        "market_status_at_fetch": market_status(fetched) if market == "turkey" else "see exchange hours",
        "latency": "delayed (update_mode: " + ", ".join(modes) + "); fundamentals/analyst data as reported by the vendor",
        "universe": universe.upper() if not tickers else "TICKERS",
        "reported_total": total,
        "rows": len(rows),
        "tickers": [row["ticker"] for row in rows],
        "index_members": members,
        "csv": csv_path.name,
        "csv_sha256": sha256_file(csv_path),
        "caveats": [
            "TMS 29 inflation accounting (Türkiye): growth and margin fields may mix restated and nominal periods.",
            "Banks/insurers: EV/EBITDA, margins and current ratio are not meaningful; use sector-specific metrics.",
            "Analyst targets/recommendations are opinions with incentives and uneven coverage (~75 BIST names).",
            "52-week fields can miss bonus-issue adjustments; prefer repaired price histories for 52-week metrics.",
        ],
    }
    write_json(out_dir / "snapshot.meta.json", meta)
    return csv_path, meta


def main():
    setup_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--market", default="turkey", help="turkey (default) or america")
    parser.add_argument("--universe", default="ALL", help="ALL, XU030/XU050/XU100/XUTUM (turkey) or SPX/NDX/DJI (america)")
    parser.add_argument("--tickers", nargs="*", help="optional explicit ticker list")
    parser.add_argument("--max-rows", type=int, help="cap rows (largest by market value first); default: all for turkey, 3000 otherwise")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or default_out("snapshot")
    max_rows = args.max_rows if args.max_rows else (None if args.market == "turkey" else 3000)
    try:
        csv_path, meta = run(out, args.universe, args.tickers, args.market, max_rows)
    except NetworkError as exc:
        print(f"ERROR: {exc}. If this host has no internet (e.g. a sandbox), use web browsing or an uploaded CSV instead.", file=sys.stderr)
        return 3
    print(f"OK {meta['rows']} rows ({meta['market']}, reported total {meta['reported_total']}) -> {csv_path}")
    print(f"fetched_at {meta['fetched_at']} | {meta['latency']} | sha256 {meta['csv_sha256'][:16]}")
    counts = {code: (len(v) if v is not None else "n/a") for code, v in meta["index_members"].items()}
    print(f"index members: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
