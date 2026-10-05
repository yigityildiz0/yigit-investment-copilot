# Data sources (verified 2026-09-28; re-check when a call fails)

Tier: 1 = regulator/exchange/issuer (primary) · 2 = licensed vendor · 3 = reputable secondary/aggregator · 4 = unofficial endpoint / community tool · 5 = social (sentiment only).

## Used by the scripts

| Need | Source and endpoint | Tier | Latency | Notes |
|---|---|---|---|---|
| All BIST stocks, prices, ratios, technical fields, analyst consensus, surprises, dividends, index membership | TradingView screener `POST https://scanner.tradingview.com/turkey/scan` (symbolset `SYML:BIST;XU100` etc.) | 4 | ~15 min delayed (`update_mode=delayed_streaming_900`) | Undocumented public endpoint behind TradingView's screener. Screening only. 52-week fields may miss bonus-issue adjustments. Analyst fields cover ~75 BIST names. |
| US stocks (S&P 500 / Nasdaq-100 / Dow members) | Same screener, `america/scan` with symbolsets `SYML:SP;SPX`, `SYML:NASDAQ;NDX`, `SYML:DJ;DJI` and `is_primary` | 4 | delayed | `bist_snapshot.py --market america`; verify filings on SEC EDGAR. |
| Daily OHLCV, dividends, splits | Yahoo Finance `query1/2.finance.yahoo.com/v8/finance/chart/{SYM}.IS` | 4 | delayed / EOD | Throttles under heavy use (1–40 s per call). Some BIST bonus issues are not adjusted → repaired by the ±10% rule. |
| Bulk close history (20 symbols/call) | Yahoo `.../v7/finance/spark?symbols=...` | 4 | delayed / EOD | Close only, split-adjusted as far as Yahoo knows; no volume. Four batches run in parallel on alternating hosts (latency is erratic). |
| KAP disclosures | `POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria`, `GET /tr/api/member/filter/{KOD}`, `GET /tr/api/notification/attachment-detail/{index}` | 1 (content) / 4 (access path) | minutes | Public JSON behind kap.org.tr; max 2000 rows per query (script splits windows). Official machine feed is KAP's subscription REST service. |
| Financial statements | İş Yatırım `.../Common/Data.aspx/MaliTablo?companyCode=..&financialGroup=XI_29|UFRS_K|UFRS&year1..4&period1..4` | 3 | after filing | Exactly four periods per call. Values are cumulative YTD. Occasional unit errors. |
| Official FX | TCMB `https://www.tcmb.gov.tr/kurlar/today.xml` | 1 | daily ~15:30 | Indicative rates of the previous/current bulletin. |
| Policy rate and corridor | TCMB pages `.../Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo` and `.../faiz-oranlari` (HTML tables) | 1 | on decision | Tables list change dates only; the latest row is the rate in force. Confirm the last PPK decision text. |
| CPI (TÜFE) | TCMB `.../istatistikler/enflasyon+verileri` (HTML table of TÜİK data) | 1 | monthly (3rd of month) | Annual and monthly change; `macro_snapshot.py` also derives the ex-post real policy rate. |
| TEFAS funds | `POST https://www.tefas.gov.tr/api/funds/<endpoint>` JSON: `fonGetiriBazliBilgiGetir` (all returns), `fonYonetimBazliBilgiGetir` (fees), `fonBilgiGetir` (price, size, investors), `fonProfilBilgiGetir` (ISIN, order hours, valör, KAP link), `fonFiyatBilgiGetir` (NAV history, `periyod` 1/3/6/12/36/60 months), `dagilimSiraliGetirT` (allocation, ≤28-day window) | 1 (content) / 4 (interface) | daily NAV | Verified 2026-09-28 (the older `/api/DB/` interface is gone). Throttles bursts: `tefas_funds.py` spaces calls and retries. Fees published as "0" mean "not reported". |

## Primary sources to open manually (all hosts)

- **KAP** — https://www.kap.org.tr (financial reports, özel durum, pay alım satım, geri alım, sermaye artırımı, genel kurul). Company page: `/tr/sirket-bilgileri/ozet/<permalink>`.
- **Borsa İstanbul** — https://www.borsaistanbul.com (duyurular, VBTS tedbirleri, endeks bileşenleri, piyasa verileri). Real-time/level-2/AKD are licensed products.
- **SPK** — https://spk.gov.tr (haftalık bülten: onaylar, idari para cezaları, işlem yasakları).
- **TCMB** — https://www.tcmb.gov.tr (PPK kararları, enflasyon raporu), **EVDS** https://evds3.tcmb.gov.tr (API key required, free).
- **TÜİK** — https://veriportali.tuik.gov.tr (TÜFE, ÜFE, sanayi üretimi).
- **TEFAS** — https://www.tefas.gov.tr (fon fiyatı, getiri, dağılım); the JSON API above backs `tefas_funds.py`. Fund documents (izahname, yatırımcı bilgi formu, portföy dağılım raporu) are on KAP.
- **Hazine ve Maliye Bakanlığı / Resmî Gazete** — tax and regulation changes.
- **Company IR pages** — presentations and guidance (management claims, not proof).

## Browsable full-universe tables (mode B)

- İş Yatırım "Temel Değerler ve Oranlar": https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx — server-rendered tables for all BIST stocks (price, market value, F/K, PD/DD, FD/FAVÖK, sector). Large page; take it in parts if the browser truncates.
- KAP BIST company list: https://www.kap.org.tr/tr/bist-sirketler — membership/identity check.
- TradingView market movers: https://tr.tradingview.com/markets/stocks-turkey/market-movers-all-stocks/ — only ~100 rows server-side; use the user's CSV export for the full list.

## Optional connectors (mode C)

| Connector | What it adds | How to connect | Caveats |
|---|---|---|---|
| **borsa-mcp** (github.com/saidsurucu/borsa-mcp, MIT) | BIST/US stocks, KAP, TEFAS, crypto (BtcTurk/Coinbase), FX/commodities, TCMB inflation/EVDS, screening | Remote: `https://borsa.surucu.dev/mcp` · local: `uvx --from git+https://github.com/saidsurucu/borsa-mcp borsa-mcp` | Third-party server: queries leave your machine. The user adds it; the skill never installs it silently. |
| **OpenBB MCP** | Multi-provider equities/macro/SEC data with provider provenance | See OpenBB Platform docs | Coverage and keys depend on the provider; BIST coverage varies. |
| Financial Datasets MCP / SEC EDGAR / FRED-ALFRED | US filings, fundamentals, macro vintages | Official docs | Use ALFRED vintages for historical macro tests. |

Routing rule: prefer the primary owner of a fact (KAP for filings, TCMB for policy/FX, Borsa İstanbul for market rules), use tier 3–4 sources for discovery and cross-checks, and record `provider`, `fetched_at` and latency for every decisive number.

## Terms and etiquette

Unofficial endpoints can change or disappear and may have usage terms; keep request volume low (the scripts batch, cache for 20 hours and pause between KAP calls), use results for personal research, and do not redistribute licensed data.
