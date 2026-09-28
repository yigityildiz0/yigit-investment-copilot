# Changelog

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
