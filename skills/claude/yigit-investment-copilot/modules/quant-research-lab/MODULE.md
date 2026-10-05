# Module: quant-research-lab

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/quant-research-lab/`).
> Original trigger scope: Test whether a trading or forecasting idea actually works before money relies on it: research cards, point-in-time data gates, historical universe and corporate-action handling, walk-forward and purged validation, transaction-cost and liquidity models, multiple-testing correction (Deflated Sharpe, PBO), backtest audits and promotion to paper trading. Use for "bu strateji işe yarar mı", "backtest yap", "momentum BIST'te çalışıyor mu", "geçmişte bu sinyal kazandırdı mı", "bu backtest gerçekçi mi", "sistem kur", or when a scan weight or rule change needs evidence. Research only; a passed test is not a promise.

# Quant Research Lab

Own evidence about strategies and signals. Read [references/research-protocol.md](references/research-protocol.md) first, then [references/pit-guard.md](references/pit-guard.md) for data integrity, [references/walk-forward-protocol.md](references/walk-forward-protocol.md) for validation design, [references/cost-liquidity.md](references/cost-liquidity.md) for costs and capacity, and [references/backtest-audit.md](references/backtest-audit.md) before judging any result (ours or someone else's).

## Tools

```bash
# 5-year bulk histories (close-only) for a universe, then walk-forward selection among signal/top-k combinations
python ../market-data-engine/scripts/price_history.py --tickers-file xu100.txt --range 5y --mode spark --out h5
python scripts/walkforward_backtest.py --history-dir h5 --benchmark h5/XU100.csv --rebalance 21 --train 504 --test 126 \
    --top-k 5 10 20 --cost-bps 25 --out wf
python scripts/strategy_stats.py returns.csv --periods-per-year 12 --trials 24 --trial-sr-var 0.0025   # PSR / DSR
python scripts/cost_model.py --price 46.9 --order-try 250000 --adv-try 3e8 --daily-vol-pct 3 --capacity
python ../technical-quant-analysis/scripts/backtest_audit.py packet.json   # audit an external backtest packet
```

Built-in walk-forward signals: `mom_12_1`, `mom_6_1`, `mom_3_0`, `rev_1m`, `prox_52w`, `lowvol_60`, `trend_200`, `combo_mom_prox`. Add new signals only through a research card.

## Workflow

1. **Research card before data.** Hypothesis, economic mechanism, target and horizon, universe, information timestamp, baseline, expected turnover/cost, and the failure condition. Record every variant you try (trial count feeds the Deflated Sharpe).
2. **Point-in-time gate.** Only information known at the decision time; no today's index list applied to the past; corporate actions repaired; revised macro never used as if known. Verdict `PASS / CONDITIONAL / FAIL`; stop on FAIL.
3. **Simple baseline first.** Buy-and-hold XU100, equal-weight universe, cash/deposit rate and a naive rule. A complex model must beat simple baselines out of sample, net of costs.
4. **Walk-forward.** Choose parameters on the training window, apply unchanged to the next test window, stitch only test periods. Purge/embargo overlapping labels. Keep a final holdout untouched until rules are frozen.
5. **Costs and capacity.** Commission + BSMV + spread + impact at realistic size; stress costs ×2. A result that dies at 2× cost is fragile.
6. **Robustness.** Sub-periods (pre/post 2021 inflation regime, 2023 rate-hike cycle, 2025 political shock), sectors, parameter neighbours, delayed execution (+1 day), removing the best period/stock.
7. **Audit and verdict.** `research-only`, `promising but not deployment-grade`, `paper-trade candidate`, or `invalid`. Report the naive in-sample best next to the walk-forward result so overfitting is visible.
8. **Prospective test.** Promote only to paper trading with `probabilistic-market-forecast/scripts/forecast_ledger.py`; judge after enough live resolutions.

## Interpretation rules

- Nominal TL returns flatter results in a 30–70% inflation environment: always compare with CPI, deposit/money-market rates and USD-based returns.
- Current listings only = survivorship bias. Today's XU100 members are yesterday's winners; do not test "XU100 stocks" with today's list and call it realistic.
- DSR probability below 0.95 or OOS below both XU100 and equal-weight after costs → no demonstrated edge.
- Fewer than ~30 OOS periods or fewer than 3 folds → exploratory only.
- A backtest is never a forecast; it shows how a rule behaved under past conditions.

## Output

Research card · data/PIT verdict · split design · OOS table vs baselines (CAGR, Sharpe, max drawdown, hit rate, turnover, DSR) · naive in-sample best for contrast · cost stress · robustness notes · biases · verdict and next test.
