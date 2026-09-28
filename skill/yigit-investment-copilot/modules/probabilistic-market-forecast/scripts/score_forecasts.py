#!/usr/bin/env python3
"""Score matured binary probability forecasts with Brier and calibration bins."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    args = parser.parse_args()
    records = json.loads(args.records.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise SystemExit("records must be a non-empty JSON array")
    squared = []
    bins = {"0-20": [], "20-40": [], "40-60": [], "60-80": [], "80-100": []}
    for row in records:
        probability = float(row["probability"])
        outcome = int(row["outcome"])
        if not 0 <= probability <= 1 or outcome not in (0, 1):
            raise SystemExit("probability must be 0..1 and outcome 0 or 1")
        squared.append((probability - outcome) ** 2)
        index = min(4, int(probability * 5))
        bins[list(bins)[index]].append((probability, outcome))
    calibration = {}
    for name, values in bins.items():
        if values:
            calibration[name] = {
                "count": len(values),
                "mean_forecast": sum(p for p, _ in values) / len(values),
                "observed_rate": sum(o for _, o in values) / len(values),
            }
    print(json.dumps({
        "count": len(records),
        "brier_score": sum(squared) / len(squared),
        "calibration_bins": calibration,
        "warning": "Calibration conclusions require enough comparable matured forecasts.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
