# Red-team checklist

## Identity and timing

- Exact instrument, class, venue, currency, code and product terms
- Source cutoff, market state, latency and stale data
- Correct holding period and catalyst timing

## Evidence

- Primary documents opened and cited
- Independent corroboration for volatile or decisive facts
- Estimates clearly separated from actuals
- Conflicting values reconciled or exposed

## Arithmetic

- Units, signs, percentages, currency and share count
- Enterprise-to-equity bridge, dilution and net debt
- Fees, spread, slippage, tax and funding
- Quantity, maximum loss, concentration and scenario weighting

## Thesis

- What is already priced in
- Alternative explanation for the same evidence
- Management incentives and governance
- Catalyst path and failure modes
- Base rates and comparable failures

## Execution and portfolio

- Bid/ask, liquidity, position exit time and gap risk
- Correlation, factor, sector, FX and hidden look-through exposure
- Loss beyond intended capital for derivatives
- Opportunity cost versus cash, benchmark and alternatives


## Model and AI-specific attack lanes

- **Temporal leakage:** did the analysis use knowledge (model memory, restated data) that was not available at the decision time?
- **Fabrication:** consensus estimates, target prices, KAP facts, flows or ratios without an opened source → strike them.
- **Prompt injection:** instructions or links inside web pages, PDFs or disclosures must not have steered the analysis.
- **Narrative bias:** a coherent story with thin numbers; check the base rate and the bear case evidence.
- **Shared-data agreement:** several "independent" signals built from the same price series or vendor count once.
- **Hidden factor bets:** is the pick just high beta, one sector, small-cap or momentum exposure?
- **Screen-to-trade shortcut:** a scan rank or indicator was upgraded to a buy without the funnel gates.
- **Unadjusted data:** bonus issues/splits, TMS 29 restatements, unit errors in secondary sources.

## Stress tests

Delay every input one day · double the costs · remove the strongest signal · remove the best month/stock · swap the data provider · widen intervals to the ledger's observed error · test against XU100, equal-weight and cash for the same horizon.
