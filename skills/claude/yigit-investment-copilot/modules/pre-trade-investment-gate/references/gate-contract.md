# Pre-trade gate contract

## Critical packet

The packet must contain:

- `identity`: name, identifier, venue, currency and product type
- `decision`, `direction`, `horizon` and `evidence_cutoff`
- `entry`: order type, executable price/source/timestamp and market status
- `thesis`, `invalidation` and `exit_plan`
- `scenario`: bear, base and bull plus maximum or stress loss
- `size`: quantity, cash/notional, maximum modeled loss, loss limit and post-trade portfolio weight
- `costs`: fees and spread, with tax/slippage status
- `liquidity` and `settlement`
- `portfolio_fit.checked = true`
- evidence-guard and red-team status

Product-specific terms belong in `product_checks`. Mark each required item true only after verifying the official owner document and current execution context.

## Evaluation order

1. Reject when evidence or red-team status is `FAIL`, modeled loss breaches the explicit loss limit, or the thesis/payoff is invalid.
2. Return `NOT READY` when a critical field or product check is missing.
3. Return `READY WITH CONDITIONS` when a named condition remains and can be checked immediately before action.
4. Return `READY` only when all gates clear.

Readiness is a research result, not an instruction to submit an order. The skill never communicates with a broker or wallet.


## Discipline checks (block the trade if any is true)

- No written plan (entry, stop, size, targets, kill condition) or the stop was set after the size.
- The order chases a limit-up queue or a parabolic move without a planned setup.
- Revenge or recovery motive after a loss; size above the regime's risk band.
- Market regime exposure band already full.
- Event risk inside the next sessions (earnings, genel kurul, bonus/rights date, TCMB/TÜİK release) not reflected in size.
- The forecast was not logged in the ledger before the order.
