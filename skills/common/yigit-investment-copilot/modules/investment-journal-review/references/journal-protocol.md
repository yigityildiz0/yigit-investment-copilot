# Investment journal protocol

## Append-only record

Preserve separate timestamps for:

- Original decision and evidence cutoff
- Entry and amendments
- Exit or forecast maturity
- Review

The original thesis, probability, range, invalidation and planned risk must remain unchanged. Corrections are appended with reason and effective time.

## Minimum fields

Use exact instrument identity, direction, horizon, strategy/setup, planned entry/exit/invalidation, planned risk, expected scenario distribution, actual execution/costs, realized P&L, process-adherence evidence and source links. Record skipped and rejected decisions when possible.

## Review categories

- Evidence quality and freshness
- Thesis and catalyst logic
- Forecast calibration and benchmark comparison
- Entry/exit timing
- Position size and portfolio fit
- Liquidity, costs and product mechanics
- Rule adherence and observable behavior
- External shock outside the stated scenario set

Use `R = realized P&L / planned loss at entry` only when planned loss was recorded before action. Do not retrofit the denominator.

## Sample discipline

Always report count, missingness, date range, instruments and regimes. Segment only when each group is large enough to interpret. Treat fewer than 30 comparable decisions as exploratory and require a longer sample before claiming a durable edge.
