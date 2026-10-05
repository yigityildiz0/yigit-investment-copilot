# Türkiye source map

## Primary sources

- KAP — company financials, special disclosures, corporate actions, prospectuses, fund documents: https://www.kap.org.tr/
- Borsa İstanbul — exchange rules, instrument/market information, delayed public data and licensed vendor information: https://www.borsaistanbul.com/en/data
- TEFAS — fund price, return, risk value, asset allocation, settlement and comparison: https://www.tefas.gov.tr/
- TCMB EVDS — rates, FX, money, credit, balance of payments and macro time series: https://evds3.tcmb.gov.tr/
- TÜİK Data Portal — inflation, production, labor, trade and SDMX data: https://veriportali.tuik.gov.tr/
- SPK — regulations, investor guides, prospectus and fund framework: https://spk.gov.tr/
- Treasury and Finance Ministry — budget, debt and public finance: https://www.hmb.gov.tr/
- Issuer or fund founder official page — investor-relations releases, factsheets and operational notices.

## Practical limitations

- Public Borsa İstanbul web data may be delayed by at least 15 minutes. Verify the live-data entitlement of any vendor before calling a quote real-time.
- KAP's documented machine feed is a subscription REST service. The kap.org.tr website itself calls public JSON endpoints (used by `market-data-engine/scripts/kap_feed.py`); they are undocumented and can change — the content is primary, the access path is unofficial.
- TEFAS's old public JSON API returned 404 on 2026-09-28; use the website pages or a connector. Treat community crawlers as unofficial and breakable.
- TEFAS warns that data may be incomplete or not current and that current categories may be applied retrospectively. Cross-check fund prospectus, investor information form, monthly portfolio report, and founder page.
- For paid vendors, a listing in the exchange vendor directory does not prove that the user has an authorized API or subscription.

## Data record

Capture code, exchange/fund founder, currency, source URL, effective date, fetched time, latency, market status, adjusted/unadjusted state, accounting basis, and conflicts.
