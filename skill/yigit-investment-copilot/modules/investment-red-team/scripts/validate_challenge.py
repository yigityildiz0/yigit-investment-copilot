#!/usr/bin/env python3
"""Validate a recommendation reconsideration packet for anti-anchoring coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


OUTCOMES = {"CONFIRMED", "REPLACED", "WAIT", "INVALIDATED", "CORRECTION"}
EVIDENCE_DELTAS = {"UNCHANGED", "UPDATED", "INVALIDATED", "CORRECTION"}
REQUIRED_TEXT_METRICS = {
    "probability_weighted_return",
    "downside",
    "evidence_quality",
    "liquidity_and_costs",
    "portfolio_fit",
    "tail_loss",
    "catalyst",
    "fees_tax_spread",
}


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(packet: dict) -> list[str]:
    errors: list[str] = []
    objective = packet.get("objective")
    if not isinstance(objective, dict):
        errors.append("objective must be an object")
    else:
        for key in ("decision", "horizon", "risk_budget", "data_cutoff"):
            if not nonempty(objective.get(key)):
                errors.append(f"objective.{key} is required")

    fresh_pass = packet.get("fresh_pass")
    if not isinstance(fresh_pass, dict):
        errors.append("fresh_pass must be an object")
    else:
        for key in ("objective_without_incumbent", "result_before_old_rationale", "incumbent_lose_threshold"):
            if not nonempty(fresh_pass.get(key)):
                errors.append(f"fresh_pass.{key} is required")
        if fresh_pass.get("old_rationale_reviewed_after_fresh_pass") is not True:
            errors.append("fresh_pass.old_rationale_reviewed_after_fresh_pass must be true")

    options = packet.get("options")
    if not isinstance(options, list) or len(options) < 3:
        errors.append("options must contain at least incumbent, same-asset challenger, and do-nothing")
        options = []

    roles: list[str] = []
    labels: set[str] = set()
    option_roles: dict[str, str] = {}
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"options[{index}] must be an object")
            continue
        role = option.get("role")
        label = option.get("label")
        if nonempty(role):
            roles.append(role)
        else:
            errors.append(f"options[{index}].role is required")
        if nonempty(label):
            if label in labels:
                errors.append(f"duplicate option label: {label}")
            labels.add(label)
            if nonempty(role):
                option_roles[label] = role
        else:
            errors.append(f"options[{index}].label is required")
        for metric in REQUIRED_TEXT_METRICS:
            if not nonempty(option.get(metric)):
                errors.append(f"options[{index}].{metric} must be non-empty")
        if option.get("data_cutoff") != (objective or {}).get("data_cutoff"):
            errors.append(f"options[{index}].data_cutoff must match objective.data_cutoff")
        scenario = option.get("scenario")
        if not isinstance(scenario, dict) or not all(nonempty(scenario.get(case)) for case in ("bear", "base", "bull")):
            errors.append(f"options[{index}].scenario needs non-empty bear, base, and bull cases")
        if option.get("equal_depth") is not True:
            errors.append(f"options[{index}].equal_depth must be true")
        ledger = option.get("evidence_ledger")
        if not isinstance(ledger, list) or len(ledger) < 2:
            errors.append(f"options[{index}].evidence_ledger needs at least two sources")
        else:
            valid_sources = [source for source in ledger if isinstance(source, dict) and nonempty(source.get("source")) and source.get("data_cutoff") == (objective or {}).get("data_cutoff")]
            if len(valid_sources) != len(ledger):
                errors.append(f"options[{index}].evidence_ledger sources need a name and common data_cutoff")
            if not any(source.get("primary") is True for source in valid_sources):
                errors.append(f"options[{index}].evidence_ledger needs a primary source")

    for role in ("incumbent", "same_asset", "do_nothing"):
        if roles.count(role) != 1:
            errors.append(f"exactly one {role} option is required")

    cross = packet.get("cross_asset_review")
    if not isinstance(cross, dict) or not isinstance(cross.get("relevant"), bool):
        errors.append("cross_asset_review.relevant must be true or false")
    elif cross["relevant"]:
        if "cross_asset" not in roles:
            errors.append("a relevant cross-asset option must be included")
    elif not nonempty(cross.get("exclusion_reason")):
        errors.append("irrelevant cross-assets require an exclusion_reason")

    bias_checks = packet.get("bias_checks")
    required_biases = {"anchoring", "confirmation", "sunk_cost", "consistency", "recency_familiarity", "novelty"}
    if not isinstance(bias_checks, dict):
        errors.append("bias_checks must be an object")
    else:
        for bias in required_biases:
            if not nonempty(bias_checks.get(bias)):
                errors.append(f"bias_checks.{bias} must be non-empty")

    evidence_delta = packet.get("evidence_delta")
    if not isinstance(evidence_delta, dict):
        errors.append("evidence_delta must be an object")
    else:
        if evidence_delta.get("status") not in EVIDENCE_DELTAS:
            errors.append("evidence_delta.status is invalid")
        if not nonempty(evidence_delta.get("detail")):
            errors.append("evidence_delta.detail is required")

    verdict = packet.get("verdict")
    if not isinstance(verdict, dict):
        errors.append("verdict must be an object")
    else:
        status = verdict.get("status")
        if status not in OUTCOMES:
            errors.append("verdict.status is invalid")
        if not nonempty(verdict.get("winner")) or verdict.get("winner") not in labels:
            errors.append("verdict.winner must match an option label")
        for key in ("decisive_reason", "change_trigger"):
            if not nonempty(verdict.get(key)):
                errors.append(f"verdict.{key} is required")
        winner_role = option_roles.get(verdict.get("winner"))
        if status == "CONFIRMED" and winner_role != "incumbent":
            errors.append("CONFIRMED requires the incumbent to win")
        if status == "REPLACED" and winner_role not in {"same_asset", "cross_asset"}:
            errors.append("REPLACED requires a same-asset or cross-asset challenger to win")
        if status == "WAIT" and winner_role != "do_nothing":
            errors.append("WAIT requires do_nothing to win")
        if status == "INVALIDATED":
            if winner_role == "incumbent":
                errors.append("INVALIDATED cannot retain the incumbent")
            if not nonempty(verdict.get("thesis_kill_evidence")):
                errors.append("INVALIDATED requires thesis_kill_evidence")
            if (evidence_delta or {}).get("status") != "INVALIDATED":
                errors.append("INVALIDATED decision requires INVALIDATED evidence_delta")
        if status == "CORRECTION":
            if not nonempty(verdict.get("prior_analytical_defect")):
                errors.append("CORRECTION requires prior_analytical_defect")
            if (evidence_delta or {}).get("status") != "CORRECTION":
                errors.append("CORRECTION decision requires CORRECTION evidence_delta")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    errors = validate(packet)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: reconsideration packet covers anti-anchoring, alternatives, and decision resolution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
