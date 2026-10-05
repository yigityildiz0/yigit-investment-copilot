#!/usr/bin/env python3
"""Audit required metadata for a decision-grade backtest."""

import argparse
import json
from pathlib import Path


REQUIRED_TRUE = [
    "point_in_time_data",
    "adjusted_price_policy",
    "signal_execution_lag",
    "partial_candle_excluded",
    "fees_included",
    "spread_included",
    "slippage_included",
    "walk_forward",
    "out_of_sample",
    "survivorship_bias_control",
    "delistings_included",
    "data_vintage_control",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    failures = [field for field in REQUIRED_TRUE if packet.get(field) is not True]
    warnings = []
    if packet.get("trade_count", 0) < 30:
        warnings.append("fewer than 30 trades")
    if packet.get("parameter_sets_tested", 1) > 1 and not packet.get("multiple_testing_control"):
        failures.append("multiple_testing_control")
    if not packet.get("taxes_included"):
        warnings.append("taxes not included or not applicable")
    status = "FAIL" if failures else "CONDITIONAL" if warnings else "PASS"
    print(json.dumps({"status": status, "failures": failures, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
