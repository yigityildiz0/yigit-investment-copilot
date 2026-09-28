# Backtest audit checklist

Use on our results and on any backtest the user brings (YouTube strategy, Telegram "sistem", broker research).

## Structural
- Point-in-time gate passed; universe reconstructed historically (delisted names included).
- Chronological split; purge/embargo where labels overlap; transforms fitted in-sample only.
- Execution realistic: next-bar fills, price limits, halts, lot/tick rules.

## Selection
- Number of variants disclosed; DSR/PBO or equivalent reported.
- Hyperparameters chosen without peeking at the final test.
- Result not driven by one stock, one sector or one month (remove best contributors and re-run).

## Economic
- Commission, BSMV, spread, impact, delay; turnover and capacity at the intended size.
- Compared with XU100, equal-weight universe and cash/deposit/money-market returns over the same dates.
- Nominal TL vs real and USD-based results shown.

## Robustness
- Sub-periods and regimes, parameter neighbours, +1 day delay, 2× costs, alternative data provider, missing-data stress.

## Red flags
- Smooth equity curve with very high Sharpe on BIST small caps (usually survivorship, stale prices or impossible fills).
- Stops that always fill at the stop price in a market with ±10% gaps.
- "Optimised" indicator settings (e.g. RSI 13/87) without out-of-sample proof.
- Only winners shown; no drawdown table; no trade count.

## Verdict
`invalid` · `research-only` · `promising but not deployment-grade` · `paper-trade candidate`. Never infer future profit from a passed audit.
