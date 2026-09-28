# Offline / ChatGPT mode (no internet inside the code sandbox)

ChatGPT web/mobile and claude.ai run skill scripts in a sandbox that usually cannot reach the internet. The analysis method stays the same; only the data path changes.

## Path 1 — browse and cite (quick)

1. Tell the user in one line that live scripts cannot run here and you will use web sources with timestamps.
2. Universe and ratios: open the İş Yatırım "Temel Değerler ve Oranlar" page (see `data-sources.md`). Take sector, price, market value, F/K, PD/DD, FD/FAVÖK for all rows you can read; note the page time.
3. Price action: for the 10–20 names that survive, open each stock's chart/quote page (e.g. TradingView symbol page, İş Yatırım company page) and record price, 52-week range and trend facts with time.
4. Events: search `site:kap.org.tr <KOD>` and open the disclosures; read financial reports on KAP.
5. Macro/regime: TCMB (policy rate, FX), TÜİK (CPI), Borsa İstanbul (index level); state the release dates.
6. Funds: tefas.gov.tr "Fon Analiz" and "Getiri Karşılaştırma" pages (returns by period, fees, allocation, size) and the fund's KAP page; record the page date.
7. State coverage honestly (e.g. "480/626 hisse okundu"). A partial scan cannot support a "full-market best" claim.

## Path 2 — user export + offline scripts (best in ChatGPT)

1. Ask the user once for a screener export. Easiest options:
   - TradingView → Stock Screener → Market: Türkiye → add columns (Price, Change %, Volume, Average Volume 30D, Market Cap, P/E, P/B, ROE, Performance 1M/3M/1Y, RSI, SMA50, SMA200, 52W High, Sector) → Export (CSV).
   - İş Yatırım "Temel Değerler ve Oranlar" → export/copy the table to Excel → save as CSV.
2. Run offline:
   ```bash
   python modules/market-data-engine/scripts/map_export.py export.csv --out snap --show
   python modules/market-data-engine/scripts/bist_scan.py --snapshot snap/snapshot.csv --horizon 3m --out scan
   ```
3. If the user uploads a chart CSV (date, open, high, low, close, volume), run `technical-quant-analysis/scripts/technical_indicators.py` and `probabilistic-market-forecast/scripts/forecast_ranges.py` on it.
4. Everything else works offline: KAP reading, valuation (`public-equity-research/scripts/valuation_models.py`), committee, red team, trade plan (`trade-management-exits/scripts/trade_plan.py`), portfolio risk on uploaded price CSVs (`portfolio-risk-and-sizing/scripts/portfolio_builder.py`), base rates on uploaded histories (`probabilistic-market-forecast/scripts/base_rates.py`) and the forecast ledger.

## Path 3 — connector

If the user has connected a finance MCP (e.g. borsa-mcp via ChatGPT Settings → Connectors → developer mode, URL `https://borsa.surucu.dev/mcp`), use it for prices, KAP and statements. Mention that queries go to that third-party server.

## Honesty rules in this mode

- Label each figure with its page and time; web quotes are delayed.
- Never claim you scanned what you did not read.
- When data is thin, return a conditional shortlist and the exact fields needed to finalize, not a confident pick.
