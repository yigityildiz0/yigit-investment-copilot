# Investment thesis schema

## Immutable baseline

- Record ID and version
- Instrument identity, venue and currency
- Created time and evidence cutoff
- Decision horizon and portfolio role
- Current price/value with source and delay
- What is priced in
- Variant thesis
- Pillars: claim, KPI, expected path, source, cadence and failure condition
- Catalysts: event, window, expected effect and disconfirming outcome
- Valuation/forecast ranges and assumptions
- Risks and contradictory evidence
- Entry, add, trim, exit and thesis-kill rules
- Next review date
- Source ledger and baseline hash when available

## Append-only update

- Update time and new evidence cutoff
- Parent record/version and unchanged baseline hash
- New or corrected evidence with source
- KPI/catalyst delta versus frozen expectation
- Forecast/valuation delta and cause
- Rule triggered, if any
- Company-thesis status
- Security-readiness status
- Portfolio-action status
- Next trigger and review date

Corrections must state what was wrong, why it was wrong and when the correction became known. A materially changed premise should start a new thesis version rather than silently editing history.
