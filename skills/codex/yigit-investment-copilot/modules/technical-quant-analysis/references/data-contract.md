# OHLCV data contract

Require:

- Exact instrument, venue, currency and timezone
- Candle interval and session rules
- Source and fetched timestamp
- Realtime/delayed/end-of-day status
- Open, high, low, close, volume and unique timestamps
- Corporate-action and continuous-contract adjustment method
- Complete-candle flag or a reproducible method to exclude the current incomplete bar

Validate `high >= max(open, close, low)`, `low <= min(open, close, high)`, positive prices, non-negative volume, ascending unique timestamps, and enough history for every reported window.

For thin instruments, use executable bid/ask and value traded alongside last price. A chart based on stale prints can misrepresent entry and exit feasibility.
