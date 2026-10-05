# Evidence schema

Store each material record with:

- `claim_id`: stable local identifier
- `claim`: concise statement
- `claim_type`: fact, estimate, calculation, inference, or opinion
- `instrument_id`: ticker plus exchange, ISIN/CIK/accession, fund code, or network plus contract
- `source_url` and `publisher`
- `published_at` or `effective_at`
- `fetched_at`
- `period`: instant, date range, fiscal quarter/year, candle interval, or NAV date
- `value`, `unit`, and `currency` when numeric
- `latency`: realtime, delayed, end_of_day, indicative, or unknown
- `adjustment`: adjusted, unadjusted, split-adjusted, inflation-adjusted, or not_applicable
- `primary`: true or false
- `notes`: conflicts, transformations, and caveats

Required fields depend on the claim, but every current numeric market fact needs instrument identity, source, value, unit/currency, effective time, fetched time, and latency.

Do not store credentials, account numbers, or private portfolio identifiers in an evidence packet.


## Point-in-time and freshness fields

For anything used in a forecast or backtest also store `known_at` (earliest time the fact was usable), `published_at`, `revised_at` and `revision_status`. Never let a value first published after the decision time enter a historical evaluation.

Freshness classes: `live/intraday` · `current-session` · `latest-official` · `latest-filing` · `stale-but-usable` · `historical-reconstructed` · `unknown`. A decision-grade answer names the class of every decisive number.

Provider provenance: when data comes through an aggregator, connector or MCP (TradingView screener, Yahoo, İş Yatırım, borsa-mcp, OpenBB), keep the underlying provider name and the endpoint; an aggregator does not become the primary source.
