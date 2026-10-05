# Event taxonomy and impact rules

`kap_feed.py` assigns these classes from the KAP subject (and summary hints). Importance is a reading priority, not a direction.

| Class | Typical KAP subject | What to check | Usual pitfalls |
|---|---|---|---|
| FINANCIAL_REPORT | Finansal Rapor | Revenue, margins, cash flow, net debt, one-offs, TMS 29 monetary gain/loss, auditor opinion | Nominal growth under inflation; comparing reports with different measuring units |
| MATERIAL_EVENT | Özel Durum Açıklaması | Read the body; reclassify (contract, capex, legal, financing) | Summary lines hide the key number |
| CONTRACT_ORDER | Yeni İş İlişkisi, sipariş, ihale | Value ÷ annual revenue, duration, margin, currency, probability of completion | Framework agreements and options (e.g. "opsiyon") are not firm revenue |
| BUYBACK | Payların Geri Alınmasına İlişkin Bildirim | Program size ÷ market cap; daily purchases ÷ daily value traded; price limits | Buybacks can support price temporarily while insiders sell |
| DIVIDEND | Kâr Payı Dağıtım İşlemleri | Yield after 15% stopaj (check current rate), ex-date, payout vs FCF | Price is adjusted on ex-date; yield chasing before ex-date is not free money |
| BONUS_ISSUE | Bedelsiz sermaye artırımı | SPK approval stage, ratio, source (iç kaynak/emisyon primi) | No value change; retail front-running then mean reversion |
| RIGHTS_ISSUE | Bedelli sermaye artırımı | Size, price, use of funds, controlling holder participation | Dilution; theoretical ex-rights price |
| CAPITAL_CHANGE / FUND_USE | Sermaye artırımı-azaltımı, kayıtlı sermaye, fon kullanım raporu | Stage and purpose | Treat approvals and completions as separate events |
| INSIDER_TRADE | Pay Alım Satım Bildirimi | Person/role, buy or sell (read body), size vs holdings and volume | List view has no direction |
| SUPPLY_OVERHANG | Borsada İşlem Gören Tipe Dönüşüm | Which holder, how many shares vs float | Precedes possible block sales |
| TENDER_OFFER | Pay Alım Teklifi | Price, mandatory or voluntary, deadline | Offer price anchors short-term trading |
| MNA / ASSET_DEAL | Birleşme, bölünme, pay edinimi, duran varlık satışı | Price vs book/EBITDA, related party?, financing | Internal mergers (100% subsidiaries) are usually neutral |
| RELATED_PARTY | İlişkili Taraf İşlemleri | Terms vs market, cash leakage to controlling group | Recurring related-party flows are a governance discount |
| CREDIT_RATING | Kredi Derecelendirmesi | Direction, agency, outlook | Local ratings move slowly |
| SPK_TRADING_BAN / SPK_BULLETIN | SPK duyuruları, bülten | Named persons/stocks, fines, bans | Long lists are weak company-level signals |
| VBTS_MEASURE | Borsa İstanbul tedbir kararları | Level (açığa satış/kredi yasağı → brüt takas → tek fiyat), dates | Measures cut liquidity; exits get harder |
| CIRCUIT_BREAKER | Pay Bazında Devre Kesici | Frequency, direction, news trigger | Common in volatile periods; count matters |
| INDEX_CHANGE | Fiili dolaşım / endeks değişiklikleri | Inclusion/exclusion dates, weight change | Passive flows are dated and often front-run |
| IPO / PROSPECTUS | Halka arz, izahname, pay satış bilgi formu | Price, lock-ups, use of proceeds, allocation | First-day limit-up streaks often reverse |
| DISTRESS / LEGAL | İflas, konkordato, haciz, dava, soruşturma | Amounts vs equity, probability, timing | Denials can be literal but incomplete |
| SETTLEMENT_DEFAULT | Temerrüt İşlemi (Takasbank) | Nothing about the company's credit | Frequently misread as company default |
| GOVERNANCE / COMPANY_INFO / MARKET_NOTICE / DEBT_ISSUE | Routine | Skim for changes in control, auditor, capital | Noise unless something changes |

## Materiality shortcuts

- Contract ≥ 10% of annual revenue, capex ≥ 10% of total assets, buyback ≥ 1% of market cap or ≥ 20% of daily value traded → material; read fully.
- Anything that changes share count, control, solvency or regulatory status → material regardless of size.
- For banks: NPL, provisions, net interest margin guidance, capital ratios, BDDK/TCMB regulation.

## Direction heuristics (base-rate hints, not rules)

- Firm contracts with clear margins, net buybacks by the company while insiders do not sell, upgraded guidance → positive if not already priced.
- Rights issues without growth use, supply-overhang steps, repeated related-party transfers, auditor qualifications → negative drift risk.
- Retail-driven events (bedelsiz, IPO, index inclusion) → strong short-term momentum followed by reversal risk; size small and exit on plan.
