#!/usr/bin/env python3
"""Rank a supplied equity universe with transparent filters and percentile metrics."""

import argparse
import csv
import json
from pathlib import Path


OPS = {
    ">": lambda left, right: left > right,
    ">=": lambda left, right: left >= right,
    "<": lambda left, right: left < right,
    "<=": lambda left, right: left <= right,
    "==": lambda left, right: left == right,
    "!=": lambda left, right: left != right,
}


def numeric(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def percentile_map(values, higher_is_better):
    ordered = sorted(set(values))
    if len(ordered) == 1:
        return {ordered[0]: 0.5}
    result = {value: index / (len(ordered) - 1) for index, value in enumerate(ordered)}
    if not higher_is_better:
        result = {value: 1 - score for value, score in result.items()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    id_column = config.get("id_column", "ticker")
    top_n = int(config.get("top_n", 20))
    missing_penalty = float(config.get("missing_penalty", 0.0))

    with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("universe is empty")
    if id_column not in rows[0]:
        raise SystemExit(f"missing id column: {id_column}")

    survivors, rejected = [], []
    for row in rows:
        reasons = []
        for rule in config.get("hard_filters", []):
            value = numeric(row.get(rule["field"]))
            if value is None:
                reasons.append(f"missing filter field {rule['field']}")
                continue
            if rule["op"] not in OPS or not OPS[rule["op"]](value, float(rule["value"])):
                reasons.append(f"failed {rule['field']} {rule['op']} {rule['value']}")
        for field in config.get("critical_fields", []):
            if row.get(field) is None or str(row[field]).strip() == "":
                reasons.append(f"missing critical field {field}")
        if reasons:
            rejected.append({"id": row[id_column], "reasons": reasons})
        else:
            survivors.append(row)

    metrics = config.get("metrics", [])
    if not metrics:
        raise SystemExit("config requires at least one metric")
    percentile_tables = {}
    for metric in metrics:
        values = [numeric(row.get(metric["field"])) for row in survivors]
        observed = [value for value in values if value is not None]
        if not observed:
            percentile_tables[metric["field"]] = {}
        else:
            percentile_tables[metric["field"]] = percentile_map(observed, metric.get("direction", "higher") == "higher")

    ranked = []
    total_weight = sum(float(metric.get("weight", 1.0)) for metric in metrics)
    if total_weight <= 0:
        raise SystemExit("metric weights must sum to a positive value")
    for row in survivors:
        contribution, missing = 0.0, []
        details = {}
        for metric in metrics:
            field = metric["field"]
            weight = float(metric.get("weight", 1.0))
            value = numeric(row.get(field))
            if value is None or value not in percentile_tables[field]:
                score = missing_penalty
                missing.append(field)
            else:
                score = percentile_tables[field][value]
            contribution += weight * score
            details[field] = {"raw": value, "percentile_score": score, "weight": weight}
        ranked.append({
            "id": row[id_column],
            "research_priority_score": contribution / total_weight,
            "missing_metrics": missing,
            "metric_details": details,
        })
    ranked.sort(key=lambda item: item["research_priority_score"], reverse=True)
    print(json.dumps({
        "universe_rows": len(rows),
        "eligible_rows": len(survivors),
        "rejected_rows": len(rejected),
        "top_candidates": ranked[:top_n],
        "rejected": rejected,
        "warning": "This score prioritizes research only; it is not a buy recommendation and does not replace full diligence.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
