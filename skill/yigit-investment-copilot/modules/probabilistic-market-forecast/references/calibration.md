# Calibration

Store each forecast with instrument, issue time, horizon, source cutoff, predicted quantiles, target probability, loss probability, model version and assumptions. When the horizon ends, add the realized adjusted price or return.

Review:

- Quantile coverage: roughly 10% of outcomes should fall below P10, 50% below P50 and 90% below P90 over a sufficiently large comparable sample.
- Brier score for binary targets.
- Directional accuracy versus a naive zero/benchmark forecast.
- Interval width versus realized coverage.
- Performance by asset class, horizon, volatility and catalyst regime.

Do not claim calibration from a handful of trades. Widen intervals and lower confidence when observed tails exceed the model or when the sample is small.
