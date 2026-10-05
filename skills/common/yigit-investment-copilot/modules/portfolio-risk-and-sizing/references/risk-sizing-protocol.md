# Portfolio risk and sizing protocol

## Contents

1. Required data
2. Exposure map
3. Quantity limits
4. Portfolio stress
5. Broker and spreadsheet inputs
6. Decision packet

## Required data

Record the instrument code and exchange, product family, direction, currency, executable entry, timestamp and delay, lot or contract size, current quantity, cash available, portfolio value, maximum cash allocation, maximum accepted loss, horizon, invalidation, fees, spread/slippage, settlement, and liquidity. For derivatives also require expiry, multiplier or conversion convention, margin, payoff/barrier terms, and whether loss can exceed deposited cash.

Missing live data does not justify a guessed quantity. Return a formula, a price/term gate, and the exact fields needed to finalize it.

## Exposure map

Keep these quantities separate:

| Field | Meaning |
|---|---|
| Cash outlay | Cash consumed at entry, including known entry costs |
| Market value | Current marked value of the position |
| Gross notional | Contract or underlying exposure before offsets |
| Delta equivalent | First-order underlying exposure at the current state; not constant |
| Modeled loss | Loss at the stated invalidation including estimated execution costs |
| Credible worst case | Product-specific tail loss; may be premium, near-total capital, or unbounded |
| Margin/collateral | Performance security or buying-power use, not a loss ceiling |

For funds and ETFs, map top holdings, issuer, sector, country, currency, duration, credit, commodity and derivative exposure when disclosures permit. Do not count wrappers as independent diversification.

## Quantity limits

Use all applicable limits and round down:

\[
q_{budget}=\left\lfloor\frac{cash-fixed\ entry\ cost}{all\text{-}in\ unit\ cash\ cost}\right\rfloor_{lot}
\]

\[
q_{risk}=\left\lfloor\frac{maximum\ accepted\ loss-fixed\ roundtrip\ cost}{all\text{-}in\ unit\ loss\ at\ invalidation}\right\rfloor_{lot}
\]

\[
q_{concentration}=\left\lfloor\frac{portfolio\ cap-existing\ position\ value}{unit\ position\ value}\right\rfloor_{lot}
\]

Use the smallest non-negative limit. For a long warrant whose entire premium is the stated risk budget, set unit loss to the all-in premium rather than pretending a stop guarantees a smaller loss. For futures, shorts, written options or leveraged accounts, require a multiplier-aware adverse scenario and separately disclose open-ended or excess-of-margin tails.

If edge probabilities are independently defensible, fractional Kelly may be shown only as a secondary ceiling. Shrink the estimated edge, cap the fraction, and never let Kelly override cash, loss, concentration, liquidity or product constraints.

## Portfolio stress

At minimum compare before and after:

- position, issuer, sector, country and currency concentration;
- gross, net and delta-equivalent exposure where meaningful;
- one ordinary adverse move and one gap/tail event;
- correlations moving toward one during stress;
- FX, rate, volatility and liquidity shocks relevant to the instruments;
- fund look-through overlap and settlement or valuation lag;
- spread widening, halted quotation, market-maker absence, barrier or liquidation events.

Historical volatility, beta, VaR, expected shortfall and correlations may describe the sample; they do not bound future loss. State data window, frequency, adjustment, missing holdings and model limits.

## Broker and spreadsheet inputs

Treat an authenticated broker quote or user-supplied timestamped order screen as account-specific execution evidence, but verify product identity and terms independently. Public broker pages may establish rules, tariffs or indicative data; they do not prove the user's live executable quote or entitlement.

For CSV/XLSX exports:

1. keep an untouched source sheet or file;
2. record export time, base currency and valuation basis;
3. map code, name, quantity, average cost, current price, currency, market value and unrealized P/L explicitly;
4. distinguish formula cells from stored values and inspect for stale external links;
5. remove or mask account number, national identifier and other unnecessary personal fields;
6. reconcile totals to the broker summary before sizing.

## Decision packet

Return instrument identity, quote time, proposed action, selected quantity, binding constraint, cash used, modeled invalidation loss, credible worst case, portfolio weight before/after, gross or delta-equivalent exposure when relevant, stress results, liquidity/settlement, assumptions, unresolved inputs and the condition that forces a smaller or zero quantity.


## Account-level guards

- **Risk per trade by regime:** use the band from `market-regime-analysis` (≈1% of capital in strong uptrends, 0.25–0.5% in downtrends); speculative capital has its own fixed cap.
- **Portfolio heat:** sum of open risk (distance to stops × quantity, plus a gap allowance) should stay within a pre-set limit (e.g. 4–6% of capital). New trades wait until heat falls.
- **Drawdown circuit breaker:** after a losing streak (e.g. 3 consecutive stops) or a drawdown beyond a set level (e.g. −8% from the equity peak), halve position risk and pause new speculative trades until a written review is done. Never increase size to "win it back".
- **Correlation:** several BIST stocks in the same sector or with the same macro driver count as one bet when sizing.
