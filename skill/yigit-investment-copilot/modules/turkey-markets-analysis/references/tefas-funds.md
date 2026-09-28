# TEFAS fund workflow

1. Confirm code, full name, founder, portfolio manager, category, benchmark, mandate, currency exposure, and investor eligibility.
2. Use TEFAS for dated price/NAV, returns, risk value, asset allocation, fund size, investor count, settlement and dealing cutoff.
3. Use KAP and the founder for prospectus, investor information form, management fee, total expense, tax notice, monthly portfolio report, benchmark and operational changes.
4. Reconcile category and strategy changes across history. Do not apply today's label blindly to the full return series.
5. Calculate total and annualized return, volatility, maximum drawdown, Sharpe, Sortino, downside capture when benchmark data exists, and recovery time. Use `scripts/fund_metrics.py` on dated NAV data.
6. Examine holdings, concentration, FX/interest/equity/commodity exposures, derivative use, liquidity, valuation timing, and overlap with the user's other funds.
7. Separate manager skill from factor beta and one-off regime benefit. Compare net-of-fee performance with the declared benchmark and relevant category.
8. Return `YENİ AL`, `ARTIR`, `TUT`, `AZALT`, `SAT`, or `İZLE` with allocation range, not return-chasing alone.

If a screenshot or OCR supplies the code, verify it independently before continuing.
