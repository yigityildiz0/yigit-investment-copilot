# Walk-forward protocol

## Designs

- **Expanding walk-forward** — train on all history up to the fold, test on the next block. Good when regimes persist.
- **Rolling walk-forward** — fixed-length training window (default 504 trading days ≈ 2 years). Good when old regimes mislead (e.g. pre-2021 low-inflation vs post-2021 high-inflation Türkiye).
- **Purged k-fold / CPCV** — for labels that overlap in time (e.g. 21-day forward returns sampled daily); purge training samples whose label window overlaps the test fold and add an embargo after each test fold.
- **Nested validation** — inner loop picks hyperparameters, outer loop measures; the final holdout is touched once.

## Rules

1. Freeze features, parameters and thresholds before looking at the final holdout.
2. Refit frequency in the test must equal the planned live refit frequency.
3. Execution delay: decide at close t, trade at close t+1 (the script's `--delay 1`) unless intraday execution is realistic.
4. Report the distribution of fold results, not only the stitched total.
5. Keep an append-only experiment registry.

## Registry fields

`experiment_id`, date, data snapshot hash, universe definition, source versions, features/signals, target, horizon, train/validation/test dates, purge/embargo, parameters, cost model, seed, code version, metrics, verdict.

## Minimum sample

Treat fewer than 3 folds, fewer than ~30 out-of-sample periods, or a single market regime as exploratory. BIST has had sharp regime breaks (2018 FX crisis, 2021–2023 negative real rates, 2023 policy normalisation, 2025 political shock); a strategy that only worked in one of them is regime-specific.
