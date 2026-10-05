#!/usr/bin/env python3
"""Fail-closed validator for a read-only pre-trade decision packet."""

import argparse
import json
from pathlib import Path


IDENTITY_FIELDS = ("name", "identifier", "venue", "currency", "product_type")
ENTRY_FIELDS = ("order_type", "price", "source", "timestamp", "market_status")
SIZE_FIELDS = ("quantity", "cash_or_notional", "max_modeled_loss", "loss_limit", "post_trade_weight")
COST_FIELDS = ("fees", "spread", "slippage_status", "tax_status")
CORE_FIELDS = ("decision", "direction", "horizon", "evidence_cutoff", "thesis", "invalidation", "exit_plan", "liquidity", "settlement")


def missing_fields(packet):
    missing = [field for field in CORE_FIELDS if packet.get(field) in (None, "", [], {})]
    for owner, fields in (("identity", IDENTITY_FIELDS), ("entry", ENTRY_FIELDS), ("size", SIZE_FIELDS), ("costs", COST_FIELDS)):
        value = packet.get(owner)
        if not isinstance(value, dict):
            missing.append(owner)
            continue
        missing.extend(f"{owner}.{field}" for field in fields if value.get(field) in (None, "", [], {}))
    scenario = packet.get("scenario")
    if not isinstance(scenario, dict):
        missing.append("scenario")
    else:
        missing.extend(f"scenario.{field}" for field in ("bear", "base", "bull", "stress_loss") if scenario.get(field) in (None, "", [], {}))
    if not isinstance(packet.get("portfolio_fit"), dict) or packet["portfolio_fit"].get("checked") is not True:
        missing.append("portfolio_fit.checked")
    for owner in ("evidence_guard", "red_team"):
        if not isinstance(packet.get(owner), dict) or packet[owner].get("status") not in {"PASS", "CONDITIONAL", "FAIL"}:
            missing.append(f"{owner}.status")
    checks = packet.get("product_checks")
    if not isinstance(checks, dict) or not checks:
        missing.append("product_checks")
    else:
        missing.extend(f"product_checks.{name}" for name, value in checks.items() if value is not True)
    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    missing = sorted(set(missing_fields(packet)))
    failures = []
    for owner in ("evidence_guard", "red_team"):
        if isinstance(packet.get(owner), dict) and packet[owner].get("status") == "FAIL":
            failures.append(f"{owner} failed")
    entry = packet.get("entry", {}) if isinstance(packet.get("entry"), dict) else {}
    size = packet.get("size", {}) if isinstance(packet.get("size"), dict) else {}
    costs = packet.get("costs", {}) if isinstance(packet.get("costs"), dict) else {}
    scenario = packet.get("scenario", {}) if isinstance(packet.get("scenario"), dict) else {}
    numeric_rules = (
        ("entry.price", entry.get("price"), lambda value: value > 0),
        ("size.quantity", size.get("quantity"), lambda value: value > 0),
        ("size.cash_or_notional", size.get("cash_or_notional"), lambda value: value > 0),
        ("size.max_modeled_loss", size.get("max_modeled_loss"), lambda value: value >= 0),
        ("size.loss_limit", size.get("loss_limit"), lambda value: value > 0),
        ("size.post_trade_weight", size.get("post_trade_weight"), lambda value: value >= 0),
        ("costs.fees", costs.get("fees"), lambda value: value >= 0),
        ("costs.spread", costs.get("spread"), lambda value: value >= 0),
        ("scenario.stress_loss", scenario.get("stress_loss"), lambda value: value >= 0),
    )
    for name, raw_value, predicate in numeric_rules:
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            failures.append(f"{name} is not numeric")
        else:
            if not predicate(value):
                failures.append(f"{name} is outside its valid range")
    try:
        if float(size.get("max_modeled_loss")) > float(size.get("loss_limit")):
            failures.append("maximum modeled loss exceeds loss limit")
    except (TypeError, ValueError):
        pass
    if packet.get("thesis_status") == "INVALIDATED":
        failures.append("thesis invalidated")

    conditions = packet.get("conditions", [])
    if not isinstance(conditions, list):
        missing.append("conditions must be a list")
    if failures:
        status, exit_code = "REJECT", 1
    elif missing:
        status, exit_code = "NOT READY", 1
    elif conditions or packet["evidence_guard"]["status"] == "CONDITIONAL" or packet["red_team"]["status"] == "CONDITIONAL":
        status, exit_code = "READY WITH CONDITIONS", 2
    else:
        status, exit_code = "READY", 0
    print(json.dumps({
        "status": status,
        "failures": failures,
        "missing_or_uncleared": sorted(set(missing)),
        "conditions": conditions if isinstance(conditions, list) else [],
        "boundary": "Readiness only. This validator does not place, transmit, or authorize an order.",
    }, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
