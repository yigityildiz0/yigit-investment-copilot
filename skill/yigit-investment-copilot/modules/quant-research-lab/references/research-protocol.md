# Research protocol

## Research card (write before touching data)

| Field | Content |
|---|---|
| Hypothesis | One sentence, falsifiable |
| Mechanism | Why it should work (risk premium, behavioural bias, structural flow) and why it has not been arbitraged away on BIST |
| Target / horizon | e.g. 21-day forward return rank, 3-month excess return vs XU100 |
| Universe | Definition and how it is reconstructed historically |
| Information time | When each input is known (price close, KAP publish time, filing deadline) |
| Baselines | XU100, equal-weight universe, deposit/money-market rate, simplest competing rule |
| Costs | Commission, BSMV, spread, impact at intended size |
| Failure condition | Pre-committed result that kills the idea |
| Trial log | Every variant tried (count feeds DSR) |

## Sequence

1. Data and provenance check (`finance-evidence-guard`).
2. Point-in-time gate (`pit-guard.md`).
3. Descriptive look (does the effect exist in simple sorts?).
4. Simple baseline model.
5. Walk-forward / purged CV (`walk-forward-protocol.md`).
6. Cost and capacity model (`cost-liquidity.md`).
7. Regime and factor decomposition (is it just beta, size, sector, momentum?).
8. Calibration and abstention thresholds (`probabilistic-market-forecast`).
9. Backtest audit (`backtest-audit.md`).
10. Prospective paper trading via the forecast ledger.
11. Red-team review (`investment-red-team`).

## Promotion criteria (all required)

- Out-of-sample improvement over simple baselines, net of realistic costs.
- Plausible mechanism and no structural leakage.
- Stable across folds, sub-periods and parameter neighbours; not dominated by one stock or one month.
- Deflated Sharpe probability ≥ 0.95 when many variants were tried (or a clearly stated lower confidence).
- Capacity sufficient for the intended position size.
- Monitoring and retirement rules written down (what degradation stops it).

## Experiment accounting

Record failed experiments as carefully as successes. Multiple testing inflates the best result: with N variants, the expected best Sharpe of pure noise grows roughly with √(2·ln N). The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) and the Probability of Backtest Overfitting (Bailey et al., 2017) quantify this; `strategy_stats.py` implements PSR/DSR.
