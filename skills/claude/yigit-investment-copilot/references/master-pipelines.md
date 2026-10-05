# Master pipelines

Commands assume the skill root as working directory and a host with shell + internet. Without internet, follow `modules/market-data-engine/references/offline-and-chatgpt-mode.md` for the data steps; every analysis step still applies.

## A. "Ne alayım?" / "X ayda en çok ne artar?" (open-ended buy)

1. **Intake** (`references/intake.md`): horizon, budget/loss limit, constraints. Proceed with labelled defaults if unanswered.
2. **Data run:** `python scripts/borsa.py pipeline --horizon <1w|2w|1m|3m|6m|1y> [--universe ALL|XU100] [--finalists 8]` → `borsa-out/.../REPORT.md` (regime, scan, finalist packs).
3. **Regime gate:** read `regime/regime.md`. In "DÜŞÜŞ TRENDİ" say so first: exposure band 0–30%, only relative-strength/defensive names, cash/money-market as a real alternative.
4. **Funnel** (`equity-opportunity-funnel`): scan → ~8–12 `ADAY` (composite + lane specialists) → 3–5 finalists with full diligence.
5. **Deep dive per finalist:** statements and valuation (`public-equity-research` + `valuation-turkey.md`; `valuation_models.py` reverse-DCF / P/B–ROE / RIM for "what is priced in"), events (`news-catalyst-intelligence`), timing (`technical-quant-analysis`), flow/execution (`bist-microstructure-flow` for ≤1 month), ranges (`probabilistic-market-forecast` with multi-signal + abstention; `python scripts/borsa.py taban --horizon <h>` for the outside view of the setup), and the seven PM questions (`references/pm-judgment-standard.md`).
6. **Committee** (`investment-committee`): bear first, bull, rebuttal, lenses, risk committee, PM decision.
7. **Red team** (`investment-red-team`) → **gate** (`pre-trade-investment-gate`) → `validate_funnel.py` on the filled packet.
8. **Plan** (`trade-management-exits/scripts/trade_plan.py`): entry, stop, size, targets, trailing/time stops.
9. **Log** the forecast (`probabilistic-market-forecast/scripts/forecast_ledger.py add --thesis --kill --benchmark-price`).
10. **Answer** in the required short format; offer the detailed tables on request.

Stop conditions: validator not PASS → `SPEKÜLATİF ADAY`/`BEST WITHIN COVERED SET`; all abstention gates fire → `AKSİYON YOK` with the trigger that would reopen.

## B. "X alınır mı?" (named stock)

1. `forecast_ledger.py history --ticker KOD` (past calls and lessons on this name), then `python scripts/borsa.py ticker KOD --horizon <h>` → evidence pack (`python scripts/report_html.py --run-dir <klasör>` for a visual page).
2. Regime (`python scripts/borsa.py regime` if not fresh today).
3. Deep dive (as A5) + one same-sector challenger and cash/XU100 as comparators.
4. Committee → red team → gate → plan → ledger → answer.

## C. "Satayım mı? / Ne zaman satmalıyım? / Stop nereye?" (position review)

1. Get position facts: code, quantity, cost, entry date, original thesis/plan if any (screenshot is fine).
2. `python scripts/borsa.py ticker KOD --horizon <remaining>`.
3. Apply `trade-management-exits/references/exit-playbook.md` in order (thesis break → stop → regime → time → target → extended → better opportunity → concentration).
4. If holding: rebuild the plan (new stop never wider than the old one), set alerts and the next review date. If selling: say how (limit/market, auction timing), and journal it.
5. Update the thesis tracker and resolve/annotate ledger entries (`forecast_ledger.py resolve --lesson` / `note`).
6. Keep open positions in a watchlist CSV (code, entry, stop, targets, review date) and check them with `python scripts/borsa.py izle --watchlist izle.csv`.

## D. "Portföyümü değerlendir"

1. Holdings table (code, qty, cost, weight); mask account data.
2. Regime + macro; per-holding quick pack (`ticker` command or scan rows).
3. `portfolio-risk-and-sizing`: concentration, sector/driver correlation, portfolio heat, cash vs deposit alternative (`python scripts/borsa.py portfoy --holdings pozisyonlar.csv --candidates ... --budget ...` for risk contributions, correlations, VaR/ES and a risk-parity allocation of new cash).
4. Exit playbook per holding; list TUT/AZALT/SAT with reasons; rebalancing plan within the regime band.

## E. Routines

- **Daily (5 min):** `python scripts/borsa.py brief --watchlist izle.csv` → `BRIEF.md` (regime, macro, KAP, calendar, movers, plan triggers), written up with the morning-note template (`references/report-templates.md`); `forecast_ledger.py due`.
- **Weekly:** full `pipeline` for the user's horizon (open `REPORT.html` for the visual version); `python scripts/borsa.py sector` for rotation; thesis tracker reviews for holdings with events next week; journal update.
- **Monthly/quarterly:** `forecast_ledger.py score`; `investment-journal-review`; at most one or two rule changes; if a rule change is proposed, test it in `quant-research-lab`.

## F. "Bu strateji işe yarar mı?"

`quant-research-lab`: research card → PIT gate → walk-forward with costs → audit → verdict → paper trade via the ledger.

## G. "Hangi fon?" (TEFAS)

1. `python scripts/borsa.py fon screen --category "<hisse|para piyasası|altın|borçlanma|...>"` → peer-group leaders ranked by consistency across 3m–5y and cost, with real (CPI-adjusted) returns and qualified-investor/TEFAS flags.
2. `python scripts/borsa.py fon compare A B C --period 3y` → same-window return, volatility, drawdown, Sharpe (policy-rate risk-free), correlations (overlap).
3. `python scripts/borsa.py fon fund KOD` → identity, costs, order hours and settlement (valör), allocation, NAV history; read the KAP documents it links.
4. `fund-etf-analyst` decides the role and allocation range; compare with the money-market alternative and the user's existing funds.

## H. US stocks

`python scripts/borsa.py pipeline --market america --horizon <h>` (S&P 500 members) or `ticker KOD --market america`. KAP and İş Yatırım steps are skipped: verify filings on SEC EDGAR / company IR with dates; FX (USD/TRY) is part of the Turkish investor's return.

## I. Other assets

Crypto → `crypto-research-readonly`; warrants/certificates → `warrant-structured-product-analyst`; VİOP → `turkey-markets-analysis` (leveraged-products) + `portfolio-risk-and-sizing`; basic finance questions → `financial-literacy-coach`.
