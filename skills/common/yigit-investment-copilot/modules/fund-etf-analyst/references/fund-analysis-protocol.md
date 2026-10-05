# Fund analysis protocol

## Identity record

Capture full legal name, ticker/code/ISIN, share class, domicile, currency, sponsor/founder, portfolio manager, category, mandate, benchmark, distribution policy, leverage/derivative authority, eligibility, dealing venue and source cutoff. A familiar code is not enough when the same symbol can exist in another venue or a fund has multiple share classes.

## Source order

1. Regulator, exchange, official registry or official fund platform
2. Prospectus, investor information document, annual/semiannual report and dated holdings
3. Sponsor/founder operational page
4. Independent market-data source for corroboration
5. Media, ratings and commentary only as leads

For Türkiye, reconcile TEFAS, KAP, the founder and SPK. Tax and settlement rules must be current and jurisdiction-specific.

## Comparison frame

Compare only after normalizing:

- Base and share-class currency
- Accumulating versus distributing return
- Hedged versus unhedged exposure
- Net asset value versus executable market price
- Total-return and corporate-action basis
- Category, benchmark and mandate history
- Leverage, duration, credit quality and derivative use
- Fee, tax, spread, settlement and liquidity

Include a category peer, the declared benchmark and a simpler low-cost alternative when available. A comparison is conditional if material holdings or fee data are stale.

## Portfolio look-through

Use the latest dated holdings and report its lag. Aggregate direct and indirect exposure by issuer, fund, sector, country, currency, asset class, duration/credit bucket and major factor. Flag duplicate exposure hidden behind several fund names. Do not double-count derivatives without understanding whether their disclosure is notional, delta-adjusted or collateral.

## Decision gate

A final action needs:

- Verified product and current executable/NAV context
- Clear role in the portfolio
- Compatible benchmark and peer comparison
- Net cost and tax caveats
- Drawdown and recovery evidence
- Look-through overlap and concentration
- Liquidity, dealing cutoff and settlement
- Allocation range, review rule and invalidation

If a gate is missing, return `WATCH` or a conditional action rather than filling the gap from memory.


## TEFAS-specific bias controls and metrics

- TEFAS historical screens can apply a fund's **current** category/type to its whole history; category winners lists therefore suffer category drift and survivorship (merged/liquidated funds disappear). Reconstruct history from KAP fund disclosures when ranking categories.
- Metrics beyond trailing return: rolling 1/3/6/12-month returns and hit rate vs benchmark, rolling Sharpe/Sortino, max drawdown and recovery time, downside deviation, upside/downside capture, beta/alpha to the declared benchmark, fund size and investor-count trends (flows), fee and total expense, concentration and FX/asset-class exposure from monthly portfolio reports.
- Compare net-of-fee, same-currency, same-horizon; include a money-market fund and a low-cost index fund as simple alternatives.
