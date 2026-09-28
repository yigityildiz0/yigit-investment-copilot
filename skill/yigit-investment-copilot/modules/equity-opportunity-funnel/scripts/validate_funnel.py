#!/usr/bin/env python3
"""Validate that final equity recommendations passed each funnel stage and gate."""

import argparse
import json
import math
import re
from pathlib import Path


GATES = {
    "identity",
    "current_price",
    "primary_filings",
    "fundamentals",
    "valuation_or_horizon_rationale",
    "technical_timing",
    "catalyst_or_recognition_path",
    "probabilistic_forecast",
    "liquidity_and_costs",
    "downside_and_invalidation",
    "evidence_guard",
    "red_team",
    "runner_up_comparison",
    "action_plan",
}

CANONICAL_UNIVERSE_COUNTS = {
    "BIST 500": 500,
    "XU500": 500,
}


def ids(items):
    return {item["ticker"] for item in items}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def sha256_text(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def require_fields(item, fields, label, failures):
    for field in fields:
        if field not in item or item[field] in (None, "", [], {}):
            failures.append(f"{label} missing substantive field: {field}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    failures, warnings = [], []

    universe = packet.get("universe", {})
    for field in (
        "name",
        "mandate",
        "membership_source",
        "membership_rows",
        "membership_artifact_sha256",
        "source_timestamp",
        "data_cutoff",
        "total_count",
        "covered_count",
        "covered_tickers",
        "eligible_count",
        "excluded_count",
        "coverage_ratio",
        "broad_request",
        "selection_claim",
        "screen_method",
        "screen_artifact",
        "screen_artifact_sha256",
        "exclusions",
    ):
        if field not in universe:
            failures.append(f"universe missing {field}")
    total = universe.get("total_count", 0)
    covered = universe.get("covered_count", 0)
    eligible = universe.get("eligible_count", 0)
    excluded = universe.get("excluded_count", 0)
    ratio = universe.get("coverage_ratio", 0)
    membership_rows = universe.get("membership_rows", [])
    covered_tickers = universe.get("covered_tickers", [])
    if not all(nonempty(universe.get(field)) for field in ("name", "mandate", "membership_source", "source_timestamp", "data_cutoff", "screen_method", "screen_artifact")):
        failures.append("universe identity, source, timestamps, method, and artifact must be non-empty")
    if not sha256_text(universe.get("membership_artifact_sha256")):
        failures.append("membership_artifact_sha256 must be a 64-character SHA-256 digest")
    if not sha256_text(universe.get("screen_artifact_sha256")):
        failures.append("screen_artifact_sha256 must be a 64-character SHA-256 digest")
    if not isinstance(membership_rows, list) or not membership_rows or not all(nonempty(ticker) for ticker in membership_rows):
        failures.append("membership_rows must be a non-empty ticker list")
        membership_rows = []
    if len(set(membership_rows)) != len(membership_rows):
        failures.append("membership_rows contains duplicate tickers")
    if total != len(membership_rows):
        failures.append("total_count must equal the number of membership_rows")
    canonical_count = CANONICAL_UNIVERSE_COUNTS.get(str(universe.get("name", "")).strip().upper())
    if canonical_count is not None and total != canonical_count:
        failures.append(f"{universe.get('name')} must reconcile to {canonical_count} membership rows")
    if not isinstance(covered_tickers, list) or not all(nonempty(ticker) for ticker in covered_tickers):
        failures.append("covered_tickers must be a ticker list")
        covered_tickers = []
    if len(set(covered_tickers)) != len(covered_tickers):
        failures.append("covered_tickers contains duplicate tickers")
    if covered != len(covered_tickers):
        failures.append("covered_count must equal the number of covered_tickers")
    if not set(covered_tickers).issubset(set(membership_rows)):
        failures.append("covered_tickers contains names absent from membership_rows")
    if not all(isinstance(value, int) and value >= 0 for value in (total, covered, eligible, excluded)):
        failures.append("universe counts must be non-negative integers")
    if covered > total:
        failures.append("covered_count exceeds total_count")
    if eligible + excluded != covered:
        failures.append("eligible_count + excluded_count must equal covered_count")
    expected_ratio = covered / total if total else 0
    if not isinstance(ratio, (int, float)) or not math.isclose(ratio, expected_ratio, abs_tol=0.005):
        failures.append("coverage_ratio does not match covered_count / total_count")
    if universe.get("selection_claim") not in {"full_market_best", "best_within_covered_universe"}:
        failures.append("selection_claim must be full_market_best or best_within_covered_universe")
    exclusions = universe.get("exclusions", [])
    if not isinstance(exclusions, list) or len(exclusions) != excluded:
        failures.append("exclusions length must equal excluded_count")
    else:
        exclusion_tickers = []
        for index, exclusion in enumerate(exclusions):
            if not isinstance(exclusion, dict) or not nonempty(exclusion.get("ticker")) or not nonempty(exclusion.get("reason")):
                failures.append(f"exclusions[{index}] needs ticker and reason")
            else:
                exclusion_tickers.append(exclusion["ticker"])
        if len(set(exclusion_tickers)) != len(exclusion_tickers):
            failures.append("exclusions contains duplicate tickers")
        if not set(exclusion_tickers).issubset(set(covered_tickers)):
            failures.append("exclusions contains tickers absent from covered_tickers")

    screened = packet.get("screened", [])
    shortlisted = packet.get("shortlisted", [])
    finalists = packet.get("finalists", [])
    final = packet.get("final_recommendations", [])
    graveyard = packet.get("graveyard", [])

    if not screened:
        failures.append("screened stage is empty")
    if len(screened) != eligible:
        failures.append("every eligible covered name must appear exactly once in screened")
    if len(ids(screened)) != len(screened):
        failures.append("screened contains duplicate tickers")
    expected_screened = set(covered_tickers) - {item.get("ticker") for item in exclusions if isinstance(item, dict)}
    if ids(screened) != expected_screened:
        failures.append("screened tickers must exactly equal covered_tickers minus exclusions")
    if universe.get("broad_request"):
        broad_floor = min(total, 100)
        if covered < broad_floor or expected_ratio < 0.90:
            warnings.append("broad request covers less than 90% of the stated universe or fewer than the broad floor")
        if universe.get("selection_claim") == "full_market_best" and (covered < broad_floor or expected_ratio < 0.90):
            failures.append("full_market_best claim lacks broad coverage")
    if not ids(shortlisted).issubset(ids(screened)):
        failures.append("shortlist contains names absent from screened stage")
    if not ids(finalists).issubset(ids(shortlisted)):
        failures.append("finalists contain names absent from shortlist")
    if not ids(final).issubset(ids(finalists)):
        failures.append("final recommendation was not fully deep-dived")

    for item in final:
        ticker = item.get("ticker", "?")
        if item.get("status") != "recommendation_grade":
            failures.append(f"{ticker} lacks recommendation_grade status")
        gate = item.get("gate", {})
        missing = sorted(GATES - gate.keys())
        failed = sorted(name for name in GATES if gate.get(name) is not True)
        if missing:
            failures.append(f"{ticker} missing gates: {', '.join(missing)}")
        if failed:
            failures.append(f"{ticker} uncleared gates: {', '.join(failed)}")
        require_fields(
            item,
            ("evidence_cutoff", "current_price", "thesis", "forecast", "red_team_verdict", "runner_up", "action_plan", "source_ledger"),
            ticker,
            failures,
        )
        price = item.get("current_price", {})
        if not isinstance(price, dict) or not all(key in price for key in ("value", "currency", "timestamp", "source")):
            failures.append(f"{ticker} current_price needs value, currency, timestamp, and source")
        thesis = item.get("thesis", {})
        if not isinstance(thesis, dict) or not all(thesis.get(key) for key in ("supports", "contradictions", "catalysts")):
            failures.append(f"{ticker} thesis needs supports, contradictions, and catalysts")
        forecast = item.get("forecast", {})
        if not isinstance(forecast, dict) or not all(key in forecast for key in ("horizon", "p10", "p50", "p90", "target_probability")):
            failures.append(f"{ticker} forecast needs horizon, p10, p50, p90, and target_probability")
        runner_up = item.get("runner_up", {})
        if not isinstance(runner_up, dict) or not runner_up.get("equal_depth") or not all(runner_up.get(key) for key in ("ticker", "why_lost")):
            failures.append(f"{ticker} runner_up needs ticker, why_lost, and equal_depth=true")
        action = item.get("action_plan", {})
        if not isinstance(action, dict) or not all(action.get(key) for key in ("entry", "invalidation", "size_or_formula", "exit_or_review")):
            failures.append(f"{ticker} action_plan is incomplete")
        verdict = item.get("red_team_verdict", {})
        if not isinstance(verdict, dict) or verdict.get("status") not in {"PASS", "CONDITIONAL"}:
            failures.append(f"{ticker} red_team_verdict must be PASS or CONDITIONAL")
        elif verdict.get("status") == "CONDITIONAL" and not verdict.get("conditions"):
            failures.append(f"{ticker} conditional red-team verdict lacks conditions")
        ledger = item.get("source_ledger", [])
        if not isinstance(ledger, list) or len(ledger) < 2 or not any(source.get("primary") is True for source in ledger if isinstance(source, dict)):
            failures.append(f"{ticker} source_ledger needs at least two sources including one primary source")

    for item in graveyard:
        if not all(item.get(field) for field in ("reason", "failure_stage", "evidence", "re_entry_condition")):
            failures.append(f"graveyard entry {item.get('ticker', '?')} lacks reason, failure_stage, evidence, or re_entry_condition")
    if not final and not packet.get("no_edge_reason"):
        failures.append("no final recommendation and no no_edge_reason")
    if len(final) > 3:
        warnings.append("more than three final recommendations reduces decisiveness")

    status = "FAIL" if failures else "CONDITIONAL" if warnings else "PASS"
    print(json.dumps({"status": status, "failures": failures, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if failures else 2 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
