#!/usr/bin/env python3
"""Run deterministic completeness and certainty checks on an investment packet."""

import argparse
import json
import re
from pathlib import Path


REQUIRED = [
    "instrument_identity",
    "data_cutoff",
    "action",
    "horizon",
    "sources",
    "facts",
    "calculations",
    "bear_case",
    "base_case",
    "bull_case",
    "invalidation",
    "downside",
    "missing_evidence",
]
CERTAINTY = re.compile(r"\b(kesin|garanti|mutlaka|definitely|guaranteed|cannot lose)\b", re.IGNORECASE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    failures = [f"missing {field}" for field in REQUIRED if field not in packet or packet[field] in (None, "", [], {})]
    warnings = []
    text = json.dumps(packet, ensure_ascii=False)
    if CERTAINTY.search(text):
        failures.append("unsupported certainty language")
    sources = packet.get("sources", [])
    if len(sources) < 2:
        warnings.append("fewer than two sources")
    if not any(isinstance(source, dict) and source.get("primary") is True for source in sources):
        warnings.append("no source marked primary")
    if packet.get("quantity") is not None and not packet.get("quantity_inputs"):
        failures.append("quantity lacks visible inputs")
    if packet.get("leveraged") is True and not packet.get("loss_beyond_deposit_checked"):
        failures.append("leveraged loss beyond deposit not checked")
    if packet.get("data_conflict") and not packet.get("conflict_resolution"):
        failures.append("data conflict unresolved")
    status = "FAIL" if failures else "CONDITIONAL" if warnings else "PASS"
    print(json.dumps({"status": status, "failures": failures, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
