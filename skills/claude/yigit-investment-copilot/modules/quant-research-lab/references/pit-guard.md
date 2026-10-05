# Point-in-time guard

## Timestamp model

Each datum carries: `event_time` (when it happened) · `period_end` (accounting/statistical period) · `published_at` (source release) · `known_at` (earliest usable time for a decision) · `ingested_at` · `revised_at`. A historical decision may use only records with `known_at <= decision_time`.

## BIST / Türkiye specifics

- **Financial statements:** use the KAP publish time as `known_at`, not the period end. Filing deadlines differ for consolidated/standalone and quarter/year; many companies file near the deadline.
- **TMS 29 restatement:** a later report restates earlier periods into a newer measuring unit. For historical tests use the figures as first published, not the restated comparatives.
- **Bank accounts:** BDDK/UFRS formats and the TMS 29 exemption for banks mean bank and non-bank fundamentals are not directly comparable.
- **Index membership:** Borsa İstanbul reviews index constituents periodically; use the list valid at each date, not today's list.
- **Corporate actions:** bedelsiz, bedelli and birleşme change share counts and base prices on the ex-date. Adjust prices backward with factors known on the ex-date; do not let future adjustment factors leak into past signals.
- **Delisted / suspended names:** include companies that were later delisted, taken to the Watchlist Market (YİP) or suspended; excluding them overstates returns.
- **Price limits and halts:** a signal that requires trading at a limit-up/limit-down price may not have been executable; mark such fills as unrealistic.
- **Macro:** TÜİK/TCMB series are revised; use the value available at the time (vintage) for historical tests.
- **Text/LLM:** summaries of old news must not contain knowledge from after the news date. LLM training knowledge is itself a leakage source in historical "would the model have predicted" tests.

## Gates (all must pass for PASS)

- No future filings, prices, index lists or revised data in features or universe.
- Rolling statistics use only past bars; scalers/selectors fitted inside training windows.
- Labels define horizon and information interval; overlapping labels purged/embargoed.
- Every tried configuration logged; multiple-testing correction reported.
- Realistic costs included before any deployability claim.

Return `PASS`, `CONDITIONAL` (named limitations, e.g. survivorship with current listings) or `FAIL` (blocking leakage). A FAIL result is never reported as evidence.
