#!/usr/bin/env python3
"""Summarize normalized trade-journal outcomes without hindsight rewriting."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n"}


def parse_bool(value):
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"invalid boolean: {value}")


def metrics(rows):
    multiples = [row["r_multiple"] for row in rows]
    wins = [value for value in multiples if value > 0]
    losses = [value for value in multiples if value < 0]
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in multiples:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative - peak)
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "count": len(rows),
        "win_rate": len(wins) / len(rows),
        "average_r": sum(multiples) / len(multiples),
        "median_r": sorted(multiples)[len(multiples) // 2] if len(multiples) % 2 else sum(sorted(multiples)[len(multiples) // 2 - 1:len(multiples) // 2 + 1]) / 2,
        "profit_factor_r": gross_profit / gross_loss if gross_loss else None,
        "max_drawdown_r": max_drawdown,
        "process_adherence": sum(row["process_followed"] for row in rows) / len(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    rows = []
    seen = set()
    with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            trade_id = str(raw.get("trade_id", "")).strip()
            if not trade_id or trade_id in seen:
                raise SystemExit("trade_id values must be present and unique")
            seen.add(trade_id)
            planned_risk = float(raw["planned_risk"])
            if planned_risk <= 0:
                raise SystemExit(f"{trade_id}: planned_risk must be positive and recorded before entry")
            pnl = float(raw["pnl_after_costs"])
            try:
                followed = parse_bool(raw["process_followed"])
            except ValueError as exc:
                raise SystemExit(f"{trade_id}: {exc}") from exc
            row = {
                "trade_id": trade_id,
                "strategy": str(raw.get("strategy", "UNSPECIFIED")).strip() or "UNSPECIFIED",
                "r_multiple": pnl / planned_risk,
                "process_followed": followed,
                "profitable": pnl > 0,
            }
            closed_at = str(raw.get("closed_at", "")).strip()
            if closed_at:
                try:
                    row["closed_at"] = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise SystemExit(f"{trade_id}: closed_at must be ISO 8601") from exc
            probability = str(raw.get("forecast_probability", "")).strip()
            outcome = str(raw.get("forecast_outcome", "")).strip()
            if bool(probability) != bool(outcome):
                raise SystemExit(f"{trade_id}: probability and outcome must be supplied together")
            if probability:
                row["forecast_probability"] = float(probability)
                row["forecast_outcome"] = int(outcome)
                if not 0 <= row["forecast_probability"] <= 1 or row["forecast_outcome"] not in (0, 1):
                    raise SystemExit(f"{trade_id}: invalid probability or binary outcome")
            rows.append(row)
    if not rows:
        raise SystemExit("journal must contain at least one row")
    dated_count = sum("closed_at" in row for row in rows)
    if dated_count not in (0, len(rows)):
        raise SystemExit("closed_at must be supplied for every row or none")
    if dated_count:
        rows.sort(key=lambda row: row["closed_at"])

    quadrants = defaultdict(int)
    for row in rows:
        process = "good_process" if row["process_followed"] else "bad_process"
        outcome = "good_outcome" if row["profitable"] else "bad_outcome"
        quadrants[f"{process}_{outcome}"] += 1
    by_strategy = defaultdict(list)
    for row in rows:
        by_strategy[row["strategy"]].append(row)
    scored = [row for row in rows if "forecast_probability" in row]
    result = {
        "overall": metrics(rows),
        "process_outcome_quadrants": dict(sorted(quadrants.items())),
        "by_strategy": {name: metrics(group) for name, group in sorted(by_strategy.items())},
        "forecast_brier_score": sum((row["forecast_probability"] - row["forecast_outcome"]) ** 2 for row in scored) / len(scored) if scored else None,
        "forecast_count": len(scored),
        "warnings": [],
    }
    if len(rows) < 30:
        result["warnings"].append("Fewer than 30 comparable decisions: treat pattern claims as exploratory.")
    if any(len(group) < 10 for group in by_strategy.values()):
        result["warnings"].append("At least one strategy segment has fewer than 10 observations.")
    if not dated_count:
        result["warnings"].append("No closed_at field: maximum drawdown assumes the CSV is already chronological.")
    result["warnings"].append("R-multiples are valid only if planned_risk was frozen before entry; this script cannot verify provenance or omitted trades.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
