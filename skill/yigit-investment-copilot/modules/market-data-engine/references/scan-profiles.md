# Scan profiles, lanes and evidence

`bist_scan.py` ranks every eligible stock in separate **lanes** (0–1 percentile scores, sector-relative where accounting differs) and combines them with **profile weights** into a research-priority composite. The composite decides reading order, not conviction. Missing lanes count as 0.4 (below neutral): unknown is a risk, not a strength.

## Profiles

| Profile | Horizon | Weights (sum 1) |
|---|---|---|
| `kisa` | ≤ 30 days | trend 0.20 · setup 0.20 · short_momentum 0.15 · catalyst 0.10 · reversal 0.10 · liquidity 0.10 · low_risk 0.10 · quality 0.05 |
| `orta` | 31–180 days | momentum 0.20 · growth 0.15 · value 0.15 · quality 0.15 · trend 0.10 · catalyst 0.10 · setup 0.05 · low_risk 0.05 · liquidity 0.05 |
| `uzun` | > 180 days | quality 0.30 · value 0.25 · growth 0.15 · low_risk 0.10 · momentum 0.10 · liquidity 0.05 · catalyst 0.05 |

Override with `--profile` or `--weights file.json`. Change weights only with a written reason (e.g. a walk-forward result from `quant-research-lab`).

## Lane definitions

- **liquidity** — log daily value traded (60-day median from history, else 30-day average × price). Also a hard floor (`--min-turnover`, default 10 mn TL/day).
- **momentum** — 12-1 and 6-1 month returns (skip the last month), 3-month return, 52-week-high proximity, 6-month relative strength vs XU100.
- **short_momentum** — 1-month and 3-month returns, 1-month relative strength, proximity to the 3-month high.
- **trend** — share of trend-template criteria met: price above SMA150/200, SMA150 > SMA200, SMA200 rising, SMA50 above both, price above SMA50, ≥30% above the 52-week low, within 25% of the 52-week high, 6-month RS percentile ≥ 70.
- **setup** — near a 3-month high, volatility contraction, MACD above signal, ADX strength, RSI near 60, not stretched above SMA20, rising relative volume.
- **reversal** — oversold (1-month drop and low RSI) but quality not poor and price not below 85% of SMA200; otherwise heavily discounted.
- **value** — sector-relative earnings yield, book yield, EBITDA/EV and FCF yield, plus dividend yield (EV and FCF metrics skipped for financials).
- **quality** — ROE, ROIC, sector-relative operating and net margin, low debt/equity, Piotroski F (0–9), Altman Z bucket, positive FCF.
- **growth** — TTM revenue, net income and EPS growth; last-quarter revenue and net income growth. Nominal under inflation — ranks are relative.
- **low_risk** — low beta, low volatility, close to the 52-week high (shallow drawdown).
- **catalyst** — earnings date inside the horizon; KAP buybacks, new contracts/orders, bonus issues, dividends, tender offers in the loaded window.

## Flags

`PARABOLIK` (>100% in 3 months or >50% in 1 month) · `TAVAN_SERISI` (≥3 limit-up days in 20) · `POMPA_COKUS` (≥2.5× run-up then below half of the peak) · `POMPA_COKUS_SUPHESI` · `DUSUK_HALKA_ACIKLIK` (<15% free float) · `DERIN_DUSUS` (<50% of 52-week high) · `ZARAR` · `NEGATIF_OZKAYNAK` · `ALTMAN_RISK` · `YUKSEK_KALDIRAC` · `BILANCO_YAKIN` (≤7 days) · `TEMEL_VERI_YOK` · `YUKSEK_VOLATILITE` (top 10%) · `VERI_UYUMSUZ` · KAP-based: `SPK_YASAK_LISTESI` (targeted list ≤15 names), `VBTS_TEDBIR`, `DEVRE_KESICI_SIK`, `TIPE_DONUSUM`, `BEDELLI_SULANMA`, `FINANSAL_SIKINTI`, `HUKUKI_RISK`.

## What the evidence says (use to set expectations, not to promise returns)

- Cross-sectional momentum and value premia are documented across many markets (Jegadeesh & Titman 1993; Asness, Moskowitz & Pedersen 2013), but premia shrink after publication and many published anomalies fail replication (McLean & Pontiff 2016; Hou, Xue & Zhang 2020; Harvey, Liu & Zhu 2016 suggest t > 3 for new factors).
- **Borsa İstanbul specifics:** early ISE studies found short/medium-term *contrarian* profits rather than momentum (e.g. Bildik & Gülay, 1991–2000 data). Fama–French size, value, profitability and investment factors show explanatory power on BIST samples (2009–2019 studies). Treat US-style momentum as unproven on BIST until our own walk-forward test supports it; that is why the short profile keeps a reversal lane.
- Quality/profitability (Novy-Marx 2013; Piotroski 2000) and low-volatility (Frazzini & Pedersen 2014) are defensive tilts; in high-inflation Türkiye use real (inflation-adjusted) and USD-based views as well as nominal TL.
- Liquidity and manipulation risk are larger in small BIST stocks: most pump-and-dump damage is avoided by the liquidity floor and flags, not by clever scoring.

## Using the output

1. Read `scan_summary.md` (counts, weights, top list, lane leaders, flags).
2. Build the medium-diligence list from composite leaders **and** lane specialists (the script's shortlist does this).
3. Record why each name advances or is rejected; failed names go to the funnel graveyard with a re-entry condition.
4. For a strategy claim ("momentum works on BIST") run `quant-research-lab`; the scan itself is not evidence of edge.
