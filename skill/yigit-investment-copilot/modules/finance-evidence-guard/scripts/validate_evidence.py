#!/usr/bin/env python3
"""Validate a JSON evidence packet for identity, provenance, and staleness."""

import argparse
import datetime as dt
import json
from pathlib import Path


BASE_REQUIRED = {"claim_id", "claim", "claim_type", "source_url", "publisher", "fetched_at"}
NUMERIC_REQUIRED = {"instrument_id", "value", "unit", "currency", "effective_at", "latency"}
ALLOWED_TYPES = {"fact", "estimate", "calculation", "inference", "opinion"}


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--as-of", help="ISO-8601; defaults to now")
    parser.add_argument("--max-age-hours", type=float)
    args = parser.parse_args()

    records = json.loads(args.packet.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("packet must be a JSON array")
    as_of = parse_time(args.as_of) if args.as_of else dt.datetime.now(dt.timezone.utc)

    issues = []
    for index, record in enumerate(records):
        label = record.get("claim_id", f"row-{index}") if isinstance(record, dict) else f"row-{index}"
        if not isinstance(record, dict):
            issues.append({"claim_id": label, "severity": "fail", "issue": "record is not an object"})
            continue
        missing = sorted(BASE_REQUIRED - record.keys())
        if isinstance(record.get("value"), (int, float)) or record.get("value") is not None:
            missing.extend(sorted(NUMERIC_REQUIRED - record.keys()))
        for field in missing:
            issues.append({"claim_id": label, "severity": "fail", "issue": f"missing {field}"})
        if record.get("claim_type") not in ALLOWED_TYPES:
            issues.append({"claim_id": label, "severity": "fail", "issue": "invalid claim_type"})
        try:
            fetched = parse_time(record["fetched_at"])
            if fetched > as_of + dt.timedelta(minutes=5):
                issues.append({"claim_id": label, "severity": "fail", "issue": "fetched_at is in the future"})
        except (KeyError, TypeError, ValueError):
            issues.append({"claim_id": label, "severity": "fail", "issue": "invalid fetched_at"})
        if args.max_age_hours is not None and record.get("effective_at"):
            try:
                age = (as_of - parse_time(record["effective_at"])).total_seconds() / 3600
                if age > args.max_age_hours:
                    issues.append({"claim_id": label, "severity": "conditional", "issue": f"stale by policy: {age:.2f} hours old"})
            except (TypeError, ValueError):
                issues.append({"claim_id": label, "severity": "fail", "issue": "invalid effective_at"})
        if record.get("latency") == "unknown":
            issues.append({"claim_id": label, "severity": "conditional", "issue": "unknown data latency"})

    severities = {item["severity"] for item in issues}
    status = "FAIL" if "fail" in severities else "CONDITIONAL" if issues else "PASS"
    print(json.dumps({"status": status, "records": len(records), "issues": issues}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
