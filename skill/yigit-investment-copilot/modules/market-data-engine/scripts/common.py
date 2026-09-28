#!/usr/bin/env python3
"""Shared helpers for the market-data-engine scripts (Python 3.9+, standard library only).

Every network call goes through `http()`. Callers pass the exact public endpoint they use;
nothing here contacts a host on its own. Outputs are plain CSV/JSON/Markdown files.
"""

import csv
import gzip
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRT = timezone(timedelta(hours=3), "TRT")  # Türkiye is UTC+3 all year
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")

YAHOO_ALIASES = {
    "USDTRY": "TRY=X", "EURTRY": "EURTRY=X", "GBPTRY": "GBPTRY=X",
    "GOLD": "GC=F", "ALTIN": "GC=F", "SILVER": "SI=F", "BRENT": "BZ=F", "WTI": "CL=F",
    "VIX": "^VIX", "DXY": "DX-Y.NYB", "US10Y": "^TNX", "SPX": "^GSPC", "SP500": "^GSPC",
    "NDX": "^NDX", "NASDAQ": "^IXIC", "DAX": "^GDAXI", "EEM": "EEM", "TUR": "TUR",
}


class NetworkError(RuntimeError):
    """Raised when an endpoint cannot be reached or returns an unusable response."""


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def now_trt():
    return datetime.now(TRT)


def iso(dt):
    return dt.isoformat(timespec="seconds")


def http(url, *, data=None, json_body=None, headers=None, timeout=20, retries=2, backoff=1.5, opener=None):
    """GET (or POST when data/json_body is given) with retries. Returns raw bytes."""
    head = {"User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip"}
    if headers:
        head.update(headers)
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        head.setdefault("Content-Type", "application/json")
    last = "unknown error"
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, data=data, headers=head)
            opener_call = opener.open if opener else urllib.request.urlopen
            with opener_call(request, timeout=timeout) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in (400, 401, 403, 404, 405):
                break
        except Exception as exc:  # timeouts, DNS, TLS, resets
            last = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    raise NetworkError(f"{url.split('?')[0]} -> {last}")


def get_json(url, **kwargs):
    raw = http(url, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NetworkError(f"{url.split('?')[0]} returned non-JSON content") from exc


def fnum(value):
    """Float or None for blanks, NaN and unparsable values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if (isinstance(value, float) and math.isnan(value)) else float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "-", "n/a"}:
        return None
    try:
        return float(text)
    except ValueError:
        return tr_float(text)


def tr_float(text):
    """Parse Turkish-formatted numbers such as '1.234.567,89' or '% 19,10'."""
    if text is None:
        return None
    cleaned = str(text).replace("%", "").replace("TL", "").replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt_cell(row.get(key)) for key in fieldnames})
    return path


def fmt_cell(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return repr(round(value, 6)) if abs(value) < 1e15 else str(value)
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    return value


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def yahoo_symbol(code, market="turkey"):
    """Map a user code to a Yahoo Finance symbol. BIST codes get the .IS suffix; for US codes a
    share-class dot becomes a dash (BRK.B -> BRK-B)."""
    raw = code.strip()
    upper = raw.upper()
    if upper in YAHOO_ALIASES:
        return YAHOO_ALIASES[upper]
    if any(mark in raw for mark in ("=", "^")) or upper.endswith(".IS"):
        return raw
    if market != "turkey":
        return upper.replace(".", "-").replace("/", "-")
    if "." in raw:
        return raw
    return upper + ".IS"


def safe_name(symbol):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in symbol.replace(".IS", ""))


def default_out(label):
    stamp = now_trt().strftime("%Y%m%d-%H%M")
    return Path.cwd() / "borsa-out" / f"{stamp}-{label}"


def market_status(moment=None):
    """Rough BIST equity session status (holidays are not modelled)."""
    moment = moment or now_trt()
    if moment.weekday() >= 5:
        return "closed-weekend"
    minutes = moment.hour * 60 + moment.minute
    if minutes < 9 * 60 + 40:
        return "pre-open"
    if minutes < 10 * 60:
        return "opening-auction"
    if minutes < 18 * 60:
        return "continuous"
    if minutes < 18 * 60 + 10:
        return "closing-session"
    return "closed"


def pct_ranks(values, higher_is_better=True):
    """Average-rank percentiles in [0, 1] for non-None values; None stays None."""
    indexed = [(value, index) for index, value in enumerate(values) if value is not None]
    result = [None] * len(values)
    if not indexed:
        return result
    if len(indexed) == 1:
        result[indexed[0][1]] = 0.5
        return result
    indexed.sort(key=lambda item: item[0])
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][0] == indexed[position][0]:
            end += 1
        rank = (position + end) / 2 / (len(indexed) - 1)
        for k in range(position, end + 1):
            result[indexed[k][1]] = rank if higher_is_better else 1 - rank
        position = end + 1
    return result


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def stdev(values):
    values = [value for value in values if value is not None]
    if len(values) < 2:
        return None
    center = sum(values) / len(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def median(values):
    values = sorted(value for value in values if value is not None)
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def md_table(rows, columns, headers=None):
    """Render a list of dicts as a GitHub-flavoured Markdown table."""
    headers = headers or columns
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, float):
                value = f"{value:,.2f}" if abs(value) >= 100 else f"{value:.2f}" if abs(value) >= 1 else f"{value:.3f}"
            cells.append("" if value is None else str(value).replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# Borsa İstanbul equity price steps (fiyat adımları). Commonly published table; confirm with the
# broker or Borsa İstanbul before relying on exact rounding. Used only to round planned levels.
BIST_TICKS = [(20.0, 0.01), (50.0, 0.02), (100.0, 0.05), (250.0, 0.10), (500.0, 0.25),
              (1000.0, 0.50), (2500.0, 1.00), (float("inf"), 2.50)]


def bist_tick(price):
    for upper, tick in BIST_TICKS:
        if price < upper:
            return tick
    return 2.5


def round_tick(price, mode="nearest"):
    if price is None or price <= 0:
        return price
    tick = bist_tick(price)
    steps = price / tick
    if mode == "down":
        steps = math.floor(steps + 1e-9)
    elif mode == "up":
        steps = math.ceil(steps - 1e-9)
    else:
        steps = round(steps)
    return round(steps * tick, 4)
