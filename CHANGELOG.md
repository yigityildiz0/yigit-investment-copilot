# Changelog

## 2.1.0 — 2026-09-29

A deep audit against official (Anthropic financial-services plugins, OpenAI public-equity standards) and popular independent finance-agent projects, then everything worth adopting, rebuilt for BIST.

### Added
- **Analyst expectations lane** in the scan (median target upside and consensus rating with ≥2 analysts, fresh EPS/revenue surprise within 75 days); value lane gains sales/EV, operating-cash-flow yield and positive PEG; new flags `HEDEF_USTU`, `ANALIST_ZAYIF`, `TEMETTU_YAKIN`. Snapshot now carries ~115 fields (targets, recommendations, surprises, ex-dividend dates, debt/cash, capex).
- **US market mode**: `bist_snapshot.py --market america --universe SPX|NDX|DJI`, market-aware scan, histories and regime; `borsa.py pipeline --market america`.
- **TEFAS fund engine** (`tefas_funds.py`): whole-market screen ranked inside peer groups (umbrella type + risk band) by multi-horizon consistency and cost, real returns, qualified-investor/TEFAS flags; single-fund pack (fees, valör, order hours, allocation, NAV metrics); same-window comparison with correlations.
- **Macro**: TCMB policy rate and corridor, TÜFE annual/monthly and the ex-post real rate in `macro_snapshot.py`.
- **Valuation models** (`valuation_models.py`): cost of equity (USD CAPM + country risk, Fisher to TRY), scenario DCF with a sensitivity grid, reverse DCF, justified P/B–ROE with implied ROE, residual income, dividend discount.
- **Historical base rates** (`base_rates.py`): forward-return distributions after seven setups versus the same-day baseline, by year, with overlap-deflated t and today's matches; `borsa.py taban`.
- **Portfolio builder** (`portfolio_builder.py`): equal-risk-contribution / inverse-volatility allocation with name and sector caps, risk contributions, correlation pairs, diversification ratio, VaR/ES, worst 20 days, beta, heat to stops; `borsa.py portfoy`.
- **Watchlist monitor** (`watchlist_monitor.py`): positions and watchlist checked against written plans (stop, targets, +1R, trend, events, review date, KAP); `borsa.py izle`.
- **Morning note and sector view**: `borsa.py brief` and `borsa.py sector`, with report templates (morning note, earnings preview/review, sector overview, idea generation incl. BIST special situations, one-page memo, numbers tie-out).
- **Self-contained HTML dashboard** (`report_html.py`) for pipeline and single-stock runs: regime cards, lane bars, SVG price charts with plan levels and the P10–P90 band, light/dark themes.
- **PM judgment standard**: seven portfolio-manager questions, claim labels, valuation and risk standards; new actions `KANIT BEKLE`, `YENİDEN DEĞERLENDİR`, `KORUMA`, `PAS`; new investor lenses (Burry, Pabrai, Jhunjhunwala, Ackman, Wood).
- **Forecast memory**: ledger entries carry thesis, kill condition and benchmark level; resolutions record excess return and a lesson; `history` and `note` commands.
- **Claude Code plugin** (`.claude-plugin/marketplace.json`, plugin `borsa` with ten `/borsa:*` commands), unprefixed Claude Code commands, five more OpenCode commands (`/sabah-bulteni`, `/sektor`, `/fon-tara`, `/portfoy-kur`, `/izle`), Codex `agents/openai.yaml`, twelve golden prompts, eleven offline regression tests and a `claude-code` release package.

### Changed
- Profile weights rebalanced for the expectations lane; missing analyst coverage counts as neutral.
- Bulk price downloads run four batches in parallel on alternating hosts (full S&P 500 in ~2.5 minutes instead of timing out).
- Installers also place Claude Code commands and back up same-name files instead of overwriting them.

## 2.0.0 — 2026-09-28

The second generation of the finance skills from [universal-ai-finance-skills](https://github.com/yigityildiz0/universal-ai-finance-skills) (17 separate skills), rebuilt as one routed copilot with a live data engine.

### Added
- **market-data-engine**: one-call snapshot of every BIST stock (~626 rows, ~90 fields, index membership), bulk and full price histories with corporate-action repair (BIST ±10% limit rule), KAP disclosure feed with event classification, İş Yatırım quarterly statements with TTM and anomaly checks, TCMB + cross-asset macro snapshot, export mapper for offline hosts, multi-lane horizon-aware scan that seeds the funnel validator.
- `scripts/borsa.py` orchestrator: `pipeline`, `ticker`, `regime`, `kap`, `macro`.
- **news-catalyst-intelligence**, **investment-committee** (bear-first debate, investor lenses, risk committee), **trade-management-exits** (`trade_plan.py`, exit playbook), **bist-microstructure-flow**, **quant-research-lab** (walk-forward backtests, cost model, PSR/DSR).
- Market regime dashboard (`bist_breadth.py`): breadth, sector rotation, distribution and follow-through days, USD-based trend, exposure bands.
- Forecast ledger (`forecast_ledger.py`): append-only, hash-chained, scored against a random-walk benchmark.
- Technical engine upgrade: ADX/DMI, Bollinger, OBV, MFI, swing support/resistance clusters, relative strength, weekly trend, setups, ATR/chandelier levels.
- Investing playbook (synthesis of classic books and academic evidence), intake questions, master pipelines, BIST market mechanics, Türkiye macro transmission map, valuation notes for Türkiye.
- OpenCode agent `borsa-analist` and commands `/borsa-tara`, `/hisse-analiz`, `/hisse-sat`, `/piyasa`, `/strateji-test`.
- Merged methodology from a 20-skill research pack (point-in-time guard, corporate-action universe reconstruction, backtest integrity audit, walk-forward runner, transaction-cost model, text signals, KAP event impact, macro/regime-factor engine, multi-signal forecast, calibration and abstention, performance monitor, model-risk red team, source routing).

### Changed
- All previous modules kept and extended (evidence provenance fields, model-risk attack lanes, TEFAS bias controls, portfolio heat and drawdown breaker, discipline checks).
