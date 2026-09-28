#!/usr/bin/env python3
"""Download daily (or weekly) OHLCV history with adjusted closes, dividends and splits.

Source: Yahoo Finance chart endpoint (query1/query2.finance.yahoo.com/v8/finance/chart). Public,
unofficial, delayed; BIST codes use the `.IS` suffix (THYAO -> THYAO.IS, XU100 -> XU100.IS).
Aliases: USDTRY, EURTRY, GOLD, BRENT, VIX, DXY, US10Y, SPX, NDX, EEM, TUR.

Output per symbol: <CODE>.csv (date,open,high,low,close,adj_close,volume,complete) and
<CODE>.meta.json (source, fetched time, currency, corporate-action events, bar count).

Usage:
  python price_history.py THYAO ASELS XU100 USDTRY --range 5y --out hist
  python price_history.py --tickers-file list.txt --range 2y --out hist --workers 6
"""

import argparse
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (NetworkError, TRT, default_out, get_json, iso, market_status, now_trt,  # noqa: E402
                    safe_name, setup_stdout, write_csv, write_json, yahoo_symbol)

HOSTS = ("https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com")
VALID_RANGES = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}


def fetch_chart(symbol, rng="2y", interval="1d"):
    last_error = None
    for host in HOSTS:
        url = (f"{host}/v8/finance/chart/{symbol}?range={rng}&interval={interval}"
               f"&events=div%2Csplits&includeAdjustedClose=true")
        try:
            data = get_json(url, timeout=25, retries=1)
        except NetworkError as exc:
            last_error = exc
            continue
        chart = data.get("chart", {})
        if chart.get("error"):
            last_error = NetworkError(f"{symbol}: {chart['error'].get('description', chart['error'])}")
            continue
        results = chart.get("result") or []
        if results:
            return results[0]
        last_error = NetworkError(f"{symbol}: empty result")
    raise last_error or NetworkError(f"{symbol}: no data")


def parse(result, interval):
    meta = result.get("meta", {})
    offset = timedelta(seconds=int(meta.get("gmtoffset") or 10800))
    zone = timezone(offset)
    stamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    rows, seen = [], set()
    for i, ts in enumerate(stamps):
        values = [quote.get(key, [None] * len(stamps))[i] for key in ("open", "high", "low", "close", "volume")]
        if values[3] is None:
            continue
        day = datetime.fromtimestamp(ts, zone).date().isoformat()
        if day in seen:  # Yahoo occasionally repeats the live bar
            rows = [row for row in rows if row["date"] != day]
        seen.add(day)
        o, h, l, c, v = values
        o = o if o is not None else c
        h = h if h is not None else max(o, c)
        l = l if l is not None else min(o, c)
        rows.append({"date": day, "open": o, "high": h, "low": l, "close": c,
                     "adj_close": adj[i] if adj and i < len(adj) and adj[i] is not None else c,
                     "volume": v if v is not None else 0, "complete": 1})
    now = now_trt()
    if rows and interval == "1d":
        last_day = rows[-1]["date"]
        if last_day == now.date().isoformat() and market_status(now) in ("pre-open", "opening-auction", "continuous", "closing-session"):
            rows[-1]["complete"] = 0
    events = []
    for kind, items in (result.get("events") or {}).items():
        for item in items.values():
            entry = {"type": kind, "date": datetime.fromtimestamp(item["date"], zone).date().isoformat()}
            if kind == "dividends":
                entry["amount"] = item.get("amount")
            else:
                entry["ratio"] = item.get("splitRatio") or f"{item.get('numerator')}:{item.get('denominator')}"
            events.append(entry)
    events.sort(key=lambda e: e["date"])
    info = {
        "currency": meta.get("currency"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "instrument_type": meta.get("instrumentType"),
        "timezone": meta.get("exchangeTimezoneName"),
        "regular_market_price": meta.get("regularMarketPrice"),
        "regular_market_time": iso(datetime.fromtimestamp(meta["regularMarketTime"], zone)) if meta.get("regularMarketTime") else None,
        "events": events,
    }
    return rows, info


def repair_corporate_actions(rows, events, is_bist):
    """BIST caps daily moves at ±10%, so a close-to-close jump beyond -20%/+25% in the adjusted
    series means a corporate action (bonus/rights issue, reverse split) that the vendor did not
    adjust. Apply the vendor split ratio when one exists on that date, otherwise estimate the
    factor from the ex-date open (open ≈ exchange-adjusted base price). Returns the repair log."""
    if not is_bist or len(rows) < 2:
        return []
    splits = {}
    for e in events:
        if e.get("type") == "splits" and e.get("ratio"):
            try:
                num, den = (float(x) for x in str(e["ratio"]).split(":"))
                splits[e["date"]] = den / num  # post/pre price factor
            except ValueError:
                pass
    log = []
    for i in range(len(rows) - 1, 0, -1):
        prev, cur = rows[i - 1], rows[i]
        ratio = cur["adj_close"] / prev["adj_close"] if prev["adj_close"] else 1.0
        if 0.80 <= ratio <= 1.25:
            continue
        if cur["date"] in splits:
            factor, method = splits[cur["date"]], "vendor split ratio"
        else:
            factor, method = (cur["open"] / prev["close"] if prev["close"] else ratio), "estimated from ex-date open"
        if not factor or factor <= 0:
            continue
        for j in range(i):
            for key in ("open", "high", "low", "close", "adj_close"):
                rows[j][key] *= factor
            rows[j]["volume"] = rows[j]["volume"] / factor if factor else rows[j]["volume"]
        log.append({"date": cur["date"], "raw_ratio": round(ratio, 4), "factor": round(factor, 6), "method": method})
    return list(reversed(log))


MARKET = {"name": "turkey"}  # set from --market; decides the Yahoo suffix


def fetch_one(code, out_dir, rng, interval, max_age_hours):
    symbol = yahoo_symbol(code, MARKET["name"])
    name = safe_name(code.upper() if "." not in code else symbol)
    csv_path = out_dir / f"{name}.csv"
    if max_age_hours and csv_path.exists():
        age = (time.time() - csv_path.stat().st_mtime) / 3600
        if age <= max_age_hours:
            return code, csv_path, "cached"
    result = fetch_chart(symbol, rng, interval)
    rows, info = parse(result, interval)
    if len(rows) < 2:
        raise NetworkError(f"{symbol}: fewer than two bars")
    for row in rows:
        row["vendor_adj_close"] = row["adj_close"]
    repairs = repair_corporate_actions(rows, info["events"], symbol.endswith(".IS") and info.get("instrument_type") == "EQUITY"
                                       and interval == "1d")
    info["ca_repairs"] = repairs
    write_csv(csv_path, rows, ["date", "open", "high", "low", "close", "adj_close", "volume", "complete", "vendor_adj_close"])
    fetched = now_trt()
    write_json(out_dir / f"{name}.meta.json", {
        "code": code, "yahoo_symbol": symbol, "source": "Yahoo Finance chart API (unofficial, delayed)",
        "fetched_at": iso(fetched), "range": rng, "interval": interval, "bars": len(rows),
        "first_date": rows[0]["date"], "last_date": rows[-1]["date"],
        "last_bar_complete": bool(rows[-1]["complete"]),
        "adjustment": "adj_close = Yahoo dividend/split adjustment plus ca_repairs (BIST ±10% limit rule: jumps beyond "
                      "-20%/+25% are treated as unadjusted corporate actions). vendor_adj_close keeps Yahoo's value. "
                      "Confirm repaired dates against KAP (bedelsiz/bedelli/birleşme).",
        **info,
    })
    return code, csv_path, "downloaded"


def fetch_spark_batch(symbols, rng, interval, first_host=0):
    """Close-only bulk history for up to 20 symbols per request (fast; no OHLC/volume/adjclose).
    Yahoo latency is erratic (1-40 s for the same request), so parallel batches alternate hosts."""
    last_error = None
    for host in HOSTS[first_host:] + HOSTS[:first_host]:
        url = (f"{host}/v7/finance/spark?symbols={','.join(symbols)}&range={rng}&interval={interval}"
               f"&indicators=close&includeTimestamps=true&includePrePost=false")
        try:
            data = get_json(url, timeout=45, retries=1)
        except NetworkError as exc:
            last_error = exc
            continue
        out = {}
        for item in (data.get("spark") or {}).get("result") or []:
            response = (item.get("response") or [None])[0]
            if response:
                out[item.get("symbol")] = response
        return out
    raise last_error or NetworkError("spark: no data")


def run_spark(codes, out_dir, rng="2y", interval="1d", max_age_hours=0, workers=4):
    """Fast mode: close-only series (open/high/low set to close, volume 0) with the same
    corporate-action repair. Enough for momentum, 52-week, trend and volatility features.
    Batches of 20 symbols run `workers` at a time (default 4; polite to the endpoint)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed, todo = {}, {}, []
    for code in codes:
        name = safe_name(code.upper() if "." not in code else yahoo_symbol(code, MARKET["name"]))
        path = out_dir / f"{name}.csv"
        if max_age_hours and path.exists() and (time.time() - path.stat().st_mtime) / 3600 <= max_age_hours:
            ok[code] = {"path": str(path), "status": "cached"}
        else:
            todo.append((code, yahoo_symbol(code, MARKET["name"]), name))
    batches = [todo[start:start + 20] for start in range(0, len(todo), 20)]
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as pool:
        futures = {pool.submit(fetch_spark_batch, [sym for _, sym, _ in batch], rng, interval, k % len(HOSTS)): batch
                   for k, batch in enumerate(batches)}
        done = []
        for future in as_completed(futures):
            batch = futures[future]
            try:
                done.append((batch, future.result()))
            except NetworkError as exc:
                for code, _, _ in batch:
                    failed[code] = str(exc)
    for batch, responses in done:
        for code, sym, name in batch:
            response = responses.get(sym)
            if not response or not response.get("timestamp"):
                failed[code] = "no spark data"
                continue
            closes = (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            fake = {"meta": response.get("meta", {}), "timestamp": response["timestamp"],
                    "indicators": {"quote": [{"open": closes, "high": closes, "low": closes, "close": closes,
                                              "volume": [0] * len(closes)}]}}
            rows, info = parse(fake, interval)
            if len(rows) < 2:
                failed[code] = "fewer than two bars"
                continue
            for row in rows:
                row["vendor_adj_close"] = row["adj_close"]
            is_equity = sym.endswith(".IS") and (info.get("instrument_type") in (None, "EQUITY"))
            info["ca_repairs"] = repair_corporate_actions(rows, [], is_equity and interval == "1d")
            path = write_csv(out_dir / f"{name}.csv", rows,
                             ["date", "open", "high", "low", "close", "adj_close", "volume", "complete", "vendor_adj_close"])
            write_json(out_dir / f"{name}.meta.json", {
                "code": code, "yahoo_symbol": sym, "source": "Yahoo Finance spark API (unofficial, delayed; close only)",
                "fetched_at": iso(now_trt()), "range": rng, "interval": interval, "bars": len(rows), "ohlc": False,
                "first_date": rows[0]["date"], "last_date": rows[-1]["date"],
                "adjustment": "Yahoo split-adjusted close (no dividend adjustment) plus ca_repairs (ex-date move assumed 0).",
                **info})
            ok[code] = {"path": str(path), "status": "downloaded"}
    return ok, failed


def run(codes, out_dir, rng="2y", interval="1d", workers=6, max_age_hours=0):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = {}, {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fetch_one, code, out_dir, rng, interval, max_age_hours): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                _, path, status = future.result()
                ok[code] = {"path": str(path), "status": status}
            except Exception as exc:  # keep going; report per symbol
                failed[code] = str(exc)
    return ok, failed


def main():
    setup_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("codes", nargs="*")
    parser.add_argument("--tickers-file", type=Path)
    parser.add_argument("--range", default="2y", choices=sorted(VALID_RANGES))
    parser.add_argument("--interval", default="1d", choices=["1d", "1wk", "1mo"])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-age-hours", type=float, default=0, help="reuse existing CSVs younger than this")
    parser.add_argument("--mode", choices=["chart", "spark"], default="chart",
                        help="chart = full OHLCV per symbol (slower); spark = bulk close-only, ~20 symbols per request")
    parser.add_argument("--market", default="turkey", help="turkey (CODE -> CODE.IS) or america (plain tickers)")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    MARKET["name"] = args.market
    codes = list(args.codes)
    if args.tickers_file:
        codes += [line.strip() for line in args.tickers_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    codes = list(dict.fromkeys(code for code in codes if code))
    if not codes:
        parser.error("give at least one code")
    out = args.out or default_out("history")
    if args.mode == "spark":
        ok, failed = run_spark(codes, out, args.range, args.interval, args.max_age_hours, min(args.workers, 4))
    else:
        ok, failed = run(codes, out, args.range, args.interval, args.workers, args.max_age_hours)
    print(f"OK {len(ok)} | FAILED {len(failed)} -> {out}")
    for code, error in sorted(failed.items()):
        print(f"  FAILED {code}: {error}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
