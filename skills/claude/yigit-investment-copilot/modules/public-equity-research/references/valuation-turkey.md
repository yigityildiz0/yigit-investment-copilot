# Valuation notes for Türkiye

## Consistency first

- Discount TL cash flows with a TL discount rate and USD cash flows with a USD rate. Mixing a TL growth rate with a USD discount rate (or the reverse) is the most common error in inflationary markets.
- Convert a USD cost of equity to TL with the inflation differential: `CoE_TL = (1 + CoE_USD) × (1 + π_TR) / (1 + π_US) − 1`.
- USD cost of equity ≈ US risk-free rate + beta × mature-market equity premium + Türkiye country risk premium (sovereign default spread or CDS scaled by relative equity/bond volatility; Damodaran's method). Record the inputs and date.
- Terminal growth in real terms should not exceed long-run real GDP growth; in nominal TL add expected long-run inflation consistently.
- `python ../scripts/valuation_models.py coe --rf-usd <US10Y> --erp 5 --crp <CRP> --beta <β> --infl-try <expected π_TR> --infl-usd <π_US> --local-rf <TRY bond>` returns the USD, nominal TRY and real cost of equity with a bond-based cross-check (paths relative to this references folder; from the skill root use `modules/public-equity-research/scripts/valuation_models.py`).

## Reading TMS 29 statements

- Figures are restated into the purchasing power at the balance-sheet date; comparatives are restated in each new report. Compare like with like (the same report's current and prior columns).
- The "net monetary position gain/loss" (parasal kazanç/kayıp) can swing net profit; a firm with net monetary liabilities books gains in high inflation. Judge operating profit and operating cash flow, not only net profit.
- Equity is restated; P/B below 1 is common and not proof of cheapness.
- Banks were exempted from TMS 29 (check the current BDDK position); do not compare bank and non-bank ROE blindly.

## Sector frames

- **Banks:** justified P/B ≈ (sustainable ROE − g) / (CoE − g); drivers: NIM path vs policy rate, loan growth, asset quality (NPL, cost of risk), capital ratios, fee growth. Use `financials_isy.py` (UFRS_K) for NII, fees, provisions, loans/deposits.
- **Holdings:** sum-of-the-parts using market values of listed stakes + valued unlisted assets − holding net debt; apply a discount only with a reason (governance, cash leakage, liquidity).
- **GYO (REITs):** NAV from appraisal reports (KAP "Değerleme Raporu"), occupancy, FX-linked rents, development pipeline; discount to NAV vs history.
- **Exporters/industrials:** USD-based margins, capacity utilisation, energy costs; use mid-cycle margins for cyclicals.
- **Airlines/tourism:** unit revenue vs unit cost (ex-fuel), fuel hedges, fleet leases (IFRS 16 debt), seasonality.
- **Energy/utilities:** regulated returns, tariff mechanisms, receivables, FX debt.

## Price-implied expectations (reverse DCF)

Solve for the revenue growth, margin or ROE that the current price requires, then judge plausibility against history, peers and the macro path. A cheap multiple with an implausible implied decline can still be fair; an expensive one with credible growth can still be attractive. Use `valuation_models.py reverse-dcf --price --shares --net-debt --cash0 --rate --terminal-growth --infl` (implied nominal and real growth) and `pb-roe --price --bvps` (implied sustainable ROE) for banks and asset-heavy firms.

## Cross-checks

At least two frames that fit the business (e.g. EV/EBITDA vs peers + reverse DCF; P/B–ROE + dividend discount for banks). State the range, not a point target, and the two or three assumptions that move it most.
