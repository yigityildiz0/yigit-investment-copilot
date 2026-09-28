#!/usr/bin/env python3
"""Append-only, hash-chained forecast ledger with maturity scoring (standard library only).

Every forecast is written BEFORE the outcome is known and is never edited: resolutions and notes
are appended as new records that reference the original id. The SHA-256 chain makes silent edits
detectable. Scoring reports quantile coverage, pinball loss, Brier scores and a naive benchmark.

Commands:
  add      --ticker T --horizon-days H --price P --p10 --p50 --p90 [--target-price X --target-prob 0.3]
           [--loss-threshold 0.10 --loss-prob 0.2] [--action ADAY] [--model v2] [--note "..."]
  resolve  --id ID --price P [--date YYYY-MM-DD]          outcome observed after the horizon
  due      [--today YYYY-MM-DD]                           forecasts past horizon without a resolution
  verify                                                  check the hash chain
  score    [--min-count 20]                               calibration report

Default ledger: ./forecast-ledger.jsonl (override with --ledger; keep one ledger per person).
"""

import argparse
import hashlib
import json
import math
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TRT = timezone(timedelta(hours=3))


def now():
    return datetime.now(TRT).isoformat(timespec="seconds")


def read(ledger):
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(record):
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def append(ledger, record):
    records = read(ledger)
    record["prev_hash"] = records[-1]["hash"] if records else "GENESIS"
    record["hash"] = digest(record)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def cmd_add(a):
    if not (a.p10 <= a.p50 <= a.p90):
        raise SystemExit("quantiles must satisfy p10 <= p50 <= p90")
    for name in ("target_prob", "loss_prob"):
        v = getattr(a, name)
        if v is not None and not 0 <= v <= 1:
            raise SystemExit(f"{name} must be within 0..1")
    rec = {"type": "forecast", "id": uuid.uuid4().hex[:12], "issued_at": now(), "ticker": a.ticker.upper(),
           "horizon_days": a.horizon_days, "maturity_date": (date.today() + timedelta(days=a.horizon_days)).isoformat(),
           "price_at_issue": a.price, "p10": a.p10, "p50": a.p50, "p90": a.p90,
           "target_price": a.target_price, "target_prob": a.target_prob,
           "loss_threshold": a.loss_threshold, "loss_prob": a.loss_prob,
           "action": a.action, "model": a.model, "note": a.note}
    print(json.dumps(append(a.ledger, rec), ensure_ascii=False, indent=2))


def cmd_resolve(a):
    records = read(a.ledger)
    fc = next((r for r in records if r["type"] == "forecast" and r["id"] == a.id), None)
    if not fc:
        raise SystemExit(f"no forecast {a.id}")
    if any(r["type"] == "resolution" and r["forecast_id"] == a.id for r in records):
        raise SystemExit("already resolved; append a note instead of re-resolving")
    rec = {"type": "resolution", "forecast_id": a.id, "resolved_at": now(), "outcome_date": a.date or date.today().isoformat(),
           "outcome_price": a.price, "early": (a.date or date.today().isoformat()) < fc["maturity_date"]}
    print(json.dumps(append(a.ledger, rec), ensure_ascii=False, indent=2))


def cmd_due(a):
    records = read(a.ledger)
    today = a.today or date.today().isoformat()
    resolved = {r["forecast_id"] for r in records if r["type"] == "resolution"}
    due = [r for r in records if r["type"] == "forecast" and r["id"] not in resolved and r["maturity_date"] <= today]
    for r in due:
        print(f"{r['id']}  {r['ticker']}  matured {r['maturity_date']}  issued {r['issued_at'][:10]} @ {r['price_at_issue']}")
    print(f"{len(due)} forecast(s) due")


def cmd_verify(a):
    records, prev = read(a.ledger), "GENESIS"
    for i, r in enumerate(records):
        if r.get("prev_hash") != prev or digest(r) != r.get("hash"):
            raise SystemExit(f"CHAIN BROKEN at line {i + 1} ({r.get('id') or r.get('forecast_id')})")
        prev = r["hash"]
    print(f"OK chain intact: {len(records)} records")


def pinball(y, q, tau):
    return max(tau * (y - q), (tau - 1) * (y - q))


def cmd_score(a):
    records = read(a.ledger)
    forecasts = {r["id"]: r for r in records if r["type"] == "forecast"}
    pairs = [(forecasts[r["forecast_id"]], r) for r in records if r["type"] == "resolution" and r["forecast_id"] in forecasts]
    if not pairs:
        raise SystemExit("no resolved forecasts yet")
    n = len(pairs)
    below = {k: 0 for k in ("p10", "p50", "p90")}
    pin, pin_naive, brier_t, brier_l, dir_hits, dir_n = 0.0, 0.0, [], [], 0, 0
    for fc, res in pairs:
        y = res["outcome_price"]
        for k in below:
            below[k] += y < fc[k]
        pin += sum(pinball(y, fc[k], t) for k, t in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9))) / fc["price_at_issue"]
        naive = fc["price_at_issue"]  # random-walk benchmark: no drift, same spread
        spread = (fc["p90"] - fc["p10"]) / 2
        pin_naive += sum(pinball(y, q, t) for q, t in ((naive - spread, 0.1), (naive, 0.5), (naive + spread, 0.9))) / naive
        if fc.get("target_price") and fc.get("target_prob") is not None:
            hit = (y >= fc["target_price"]) if fc["target_price"] >= fc["price_at_issue"] else (y <= fc["target_price"])
            brier_t.append((fc["target_prob"] - float(hit)) ** 2)
        if fc.get("loss_threshold") and fc.get("loss_prob") is not None:
            lost = y <= fc["price_at_issue"] * (1 - fc["loss_threshold"])
            brier_l.append((fc["loss_prob"] - float(lost)) ** 2)
        if fc["p50"] != fc["price_at_issue"]:
            dir_n += 1
            dir_hits += (fc["p50"] > fc["price_at_issue"]) == (y > fc["price_at_issue"])
    report = {
        "resolved": n, "early_resolutions": sum(1 for _, r in pairs if r.get("early")),
        "coverage": {k: round(v / n, 3) for k, v in below.items()},
        "coverage_target": {"p10": 0.10, "p50": 0.50, "p90": 0.90},
        "pinball_loss_rel": round(pin / n, 5), "pinball_loss_random_walk_rel": round(pin_naive / n, 5),
        "beats_random_walk": pin < pin_naive,
        "brier_target": round(sum(brier_t) / len(brier_t), 4) if brier_t else None,
        "brier_loss": round(sum(brier_l) / len(brier_l), 4) if brier_l else None,
        "direction_hit_rate": round(dir_hits / dir_n, 3) if dir_n else None,
        "sample_warning": n < a.min_count,
        "interpretation": "If far fewer than 10% of outcomes fall below P10 or more than 10% above P90 the ranges are too wide/narrow; "
                          "widen intervals when tails are breached more than expected. Fewer than ~30 resolutions is exploratory.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", type=Path, default=Path("forecast-ledger.jsonl"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--ticker", required=True)
    p.add_argument("--horizon-days", type=int, required=True)
    p.add_argument("--price", type=float, required=True)
    for q in ("--p10", "--p50", "--p90"):
        p.add_argument(q, type=float, required=True)
    p.add_argument("--target-price", type=float)
    p.add_argument("--target-prob", type=float)
    p.add_argument("--loss-threshold", type=float)
    p.add_argument("--loss-prob", type=float)
    p.add_argument("--action", default="ADAY")
    p.add_argument("--model", default="copilot-v2")
    p.add_argument("--note", default="")
    r = sub.add_parser("resolve")
    r.add_argument("--id", required=True)
    r.add_argument("--price", type=float, required=True)
    r.add_argument("--date")
    d = sub.add_parser("due")
    d.add_argument("--today")
    sub.add_parser("verify")
    s = sub.add_parser("score")
    s.add_argument("--min-count", type=int, default=30)
    a = ap.parse_args()
    {"add": cmd_add, "resolve": cmd_resolve, "due": cmd_due, "verify": cmd_verify, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
