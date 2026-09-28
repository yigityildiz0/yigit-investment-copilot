# Funnel packet schema

Create a JSON packet before an open-ended equity selection receives a final action.

## Universe object

Required fields:

- `name`, `mandate`, `membership_source`, `source_timestamp`, `data_cutoff`
- `membership_rows`: the exact, deduplicated source-universe ticker ledger
- `membership_artifact_sha256`: SHA-256 of the retrieved membership artifact
- `total_count`, `covered_count`, `covered_tickers`, `eligible_count`, `excluded_count`, `coverage_ratio`
- `broad_request`: boolean
- `selection_claim`: `full_market_best` or `best_within_covered_universe`
- `screen_method`, `screen_artifact`, and `screen_artifact_sha256`: enough detail to reproduce and identify the exact rows
- `exclusions`: one `{ticker, reason}` record per covered exclusion

The arithmetic must reconcile: `total_count == len(membership_rows)`, `covered_count == len(covered_tickers)`, covered tickers are a subset of membership rows, and `screened == covered_tickers - exclusions`. The `screened` list must contain every eligible covered ticker exactly once. Recognized fixed-size universes such as BIST 500 must also match their canonical membership count. For a broad request, less than 90% coverage or fewer than `min(100, total_count)` names cannot support a full-market claim. Use `finance-evidence-guard` module to verify the membership source and artifact timestamp; a hash proves artifact identity, not publisher truth.

## Funnel stages

- `screened`: all eligible covered tickers
- `shortlisted`: subset of screened
- `finalists`: subset of shortlisted that received full diligence
- `graveyard`: failed finalists with `failure_stage`, `reason`, `evidence`, and `re_entry_condition`
- `final_recommendations`: subset of finalists

## Final recommendation evidence

Each final item needs:

- `status: recommendation_grade` and all recommendation-gate booleans true
- `evidence_cutoff`
- `current_price`: value, currency, timestamp and source
- `thesis`: supports, contradictions and catalysts
- `forecast`: horizon, P10, P50, P90 and target probability
- `red_team_verdict`: `PASS`, or `CONDITIONAL` with explicit conditions
- `runner_up`: ticker, why it lost and `equal_depth: true`
- `action_plan`: entry, invalidation, size or formula, exit or review
- `source_ledger`: at least two sources, including one marked `primary: true`

Boolean gates without these substantive fields do not pass.

## Execution

Run:

```bash
python scripts/validate_funnel.py packet.json
```

Only JSON status `PASS` and process exit code 0 authorize a final action. Exit code 1 is failure. Exit code 2 is conditional coverage or decisiveness and must remain candidate-grade until corrected.
