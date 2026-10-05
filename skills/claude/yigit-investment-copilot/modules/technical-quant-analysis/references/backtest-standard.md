# Backtest standard

Require a reproducible strategy definition and record:

- Point-in-time universe and data vintage
- Adjusted-price and corporate-action policy
- Signal timing and next executable price
- Incomplete-candle exclusion
- Walk-forward or rolling validation
- Held-out out-of-sample results
- Parameter search space and multiple-testing control
- Fees, spread, slippage, taxes, borrow/funding and market impact
- Survivorship, delisting and symbol-change handling
- Benchmark and cash return
- Trade count, exposure, turnover, drawdown, tail loss and regime stability

Reject a result that uses future data, revises history with information unavailable at the time, omits meaningful costs, or reports only the best parameter set. Treat small samples and one-regime success as exploratory.
