# Warrant and structured-product protocol

## Required identity fields

- Product code and ISIN
- Issuer and venue
- Product family and exact payoff
- Underlying identifier and currency
- Direction/type, strike and any cap/barrier/knock-out
- Expiry, last trading day and exercise/settlement
- Conversion convention stated in unambiguous units
- Corporate-action adjustment rules
- Official product document URL and effective date

Do not continue from a symbol or screenshot alone. Different issuers may describe conversion terms differently; restate the verified convention as “underlying units represented by one warrant” before calculation.

## Quote record

Capture bid, ask, last trade, quote timestamp/delay, market status, bid/ask size when available, market-maker status, lot, fees and settlement. Calculate spread in both currency and percentage. A stale last trade is not an executable entry.

## Scenario layers

1. Underlying return distribution and dated catalysts
2. Expiry payoff under the official formula
3. Pre-expiry indicative value across remaining time and implied-volatility assumptions, only for a supported vanilla structure
4. Execution adjustment for spread, fees, liquidity and issuer quotation
5. Stress cases for gap, barrier, volatility crush, market-maker absence, corporate action and issuer risk

Show the assumptions separately. Do not collapse mutually exclusive event branches into one precise target.

## Decision gate

A final action requires verified identity, current executable quote, official payoff terms, horizon before expiry, budget/loss cap, product-appropriate scenarios, spread/liquidity, alternative structure, quantity and invalidation. If one is missing, return a conditional price/term gate rather than a final quantity.
