#!/usr/bin/env python3
"""Append-only, hash-chained forecast ledger with maturity scoring (standard library only).

Every forecast is written BEFORE the outcome is known and is never edited: resolutions and notes
are appended as new records that reference the original id. The SHA-256 chain makes silent edits
detectable. Scoring reports quantile coverage, pinball loss, Brier scores and a naive benchmark.

Commands:
  add      --ticker T --horizon-days H --price P --p10 --p50 --p90 [--target-price X --target-prob 0.3]
           [--loss-threshold 0.10 --loss-prob 0.2] [--action ADAY] [--model v2] [--note "..."]
           [--thesis "..."] [--kill "non-price kill condition"] [--benchmark-price XU100_level]
  resolve  --id ID --price P [--date YYYY-MM-DD] [--benchmark-price B] [--lesson "what to do differently"]
  note     --id ID --text "..."                          append-only note (never edit a forecast)
  due      [--today YYYY-MM-DD]                           forecasts past horizon without a resolution
  history  [--ticker T] [--last 20] [--lessons-only]      past calls, outcomes, excess return and lessons:
                                                          read this BEFORE a new analysis of the same name
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
           "action": a.action, "model": a.model, "note": a.note, "thesis": a.thesis, "kill_condition": a.kill,
           "benchmark_price_at_issue": a.benchmark_price}
    print(json.dumps(append(a.ledger, rec), ensure_ascii=False, indent=2))


def cmd_resolve(a):
    records = read(a.ledger)
    fc = next((r for r in records if r["type"] == "forecast" and r["id"] == a.id), None)
    if not fc:
        raise SystemExit(f"no forecast {a.id}")
    if any(r["type"] == "resolution" and r["forecast_id"] == a.id for r in records):
        raise SystemExit("already resolved; append a note instead of re-resolving")
    realized = a.price / fc["price_at_issue"] - 1
    rec = {"type": "resolution", "forecast_id": a.id, "resolved_at": now(), "outcome_date": a.date or date.today().isoformat(),
           "outcome_price": a.price, "early": (a.date or date.today().isoformat()) < fc["maturity_date"],
           "realized_return": round(realized, 6), "inside_p10_p90": fc["p10"] <= a.price <= fc["p90"],
           "benchmark_price_at_outcome": a.benchmark_price, "lesson": a.lesson}
    if a.benchmark_price and fc.get("benchmark_price_at_issue"):
        rec["excess_return_vs_benchmark"] = round(realized - (a.benchmark_price / fc["benchmark_price_at_issue"] - 1), 6)
    print(json.dumps(append(a.ledger, rec), ensure_ascii=False, indent=2))


def cmd_note(a):
    records = read(a.ledger)
    if not any(r["type"] == "forecast" and r["id"] == a.id for r in records):
        raise SystemExit(f"no forecast {a.id}")
    print(json.dumps(append(a.ledger, {"type": "note", "forecast_id": a.id, "noted_at": now(), "text": a.text}), ensure_ascii=False, indent=2))


def cmd_history(a):
    records = read(a.ledger)
    res = {r["forecast_id"]: r for r in records if r["type"] == "resolution"}
    notes = {}
    for r in records:
        if r["type"] == "note":
            notes.setdefault(r["forecast_id"], []).append(r["text"])
    fcs = [r for r in records if r["type"] == "forecast" and (not a.ticker or r["ticker"] == a.ticker.upper())][-a.last:]
    if not fcs:
        print("no forecasts" + (f" for {a.ticker.upper()}" if a.ticker else ""))
        return
    excess, inside, n_res = [], 0, 0
    for fc in fcs:
        r = res.get(fc["id"])
        lesson = (r or {}).get("lesson")
        if a.lessons_only:
            if lesson or notes.get(fc["id"]):
                print(f"- {fc['issued_at'][:10]} {fc['ticker']} ({fc.get('action')}): " + " | ".join(filter(None, [lesson] + notes.get(fc["id"], []))))
            continue
        line = (f"{fc['issued_at'][:10]} {fc['ticker']:<6} {fc.get('action', ''):<8} @ {fc['price_at_issue']} "
                f"P10/P50/P90 {fc['p10']}/{fc['p50']}/{fc['p90']} vade {fc['maturity_date']}")
        if r:
            n_res += 1
            inside += bool(r.get("inside_p10_p90"))
            ex = r.get("excess_return_vs_benchmark")
            if ex is not None:
                excess.append(ex)
            line += (f" -> {r['outcome_price']} ({(r.get('realized_return') or 0) * 100:+.1f}%"
                     + (f", endekse göre {ex * 100:+.1f}%" if ex is not None else "") + f", aralık içinde: {r.get('inside_p10_p90')})")
        else:
            line += " -> açık"
        print(line)
        if fc.get("thesis"):
            print(f"    tez: {fc['thesis']}" + (f" · iptal koşulu: {fc['kill_condition']}" if fc.get("kill_condition") else ""))
        if lesson:
            print(f"    ders: {lesson}")
        for text in notes.get(fc["id"], []):
            print(f"    not: {text}")
    if not a.lessons_only and n_res:
        print(f"{n_res} sonuçlanmış tahmin · P10–P90 içinde {inside}/{n_res}"
              + (f" · ortalama endeks üstü getiri {sum(excess) / len(excess) * 100:+.1f}% (n={len(excess)})" if excess else ""))
        print("Yeni analizden önce: aynı hatayı tekrarlamamak için dersleri ve kaçırılan riskleri oku; küçük örnek kesin sonuç değildir.")


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
    p.add_argument("--thesis", default="")
    p.add_argument("--kill", default="", help="non-price condition that kills the thesis")
    p.add_argument("--benchmark-price", type=float, help="benchmark level at issue (e.g. XU100) for excess return")
    r = sub.add_parser("resolve")
    r.add_argument("--id", required=True)
    r.add_argument("--price", type=float, required=True)
    r.add_argument("--date")
    r.add_argument("--benchmark-price", type=float, help="benchmark level at the outcome date")
    r.add_argument("--lesson", default="", help="one-line lesson for future analyses of this name or setup")
    n = sub.add_parser("note")
    n.add_argument("--id", required=True)
    n.add_argument("--text", required=True)
    h = sub.add_parser("history")
    h.add_argument("--ticker")
    h.add_argument("--last", type=int, default=20)
    h.add_argument("--lessons-only", action="store_true")
    d = sub.add_parser("due")
    d.add_argument("--today")
    sub.add_parser("verify")
    s = sub.add_parser("score")
    s.add_argument("--min-count", type=int, default=30)
    a = ap.parse_args()
    {"add": cmd_add, "resolve": cmd_resolve, "note": cmd_note, "due": cmd_due, "history": cmd_history, "verify": cmd_verify,
     "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
