# Borsa İstanbul equity market mechanics

Last checked 2026-09-28 from broker/exchange public pages. Rules change: confirm on borsaistanbul.com, spk.gov.tr, gib.gov.tr or with the broker before a decision depends on them.

## Sessions (Pay Piyasası)

| Time (TRT) | Session |
|---|---|
| 09:40–09:55 | Opening auction: orders collected, no matching |
| 09:55–10:00 | Opening price determination and matching |
| 10:00–18:00 | Continuous trading |
| 18:00–18:05 | Closing auction: orders collected |
| ~18:05 | Closing price determination |
| 18:08–18:10 | Trades at the closing price |

Half-days before some holidays and exchange-announced changes apply. KAP disclosures published after the close are priced at the next opening auction.

## Prices and limits

- **Daily price limit:** ±10% of the base price for equities (the base price is adjusted for corporate actions on ex-dates). Consequence: a close-to-close change beyond −20%/+25% in a price series means an unadjusted corporate action, not a real move.
- **Price steps (fiyat adımları)** commonly published: <20 TL 0.01 · 20–50 TL 0.02 · 50–100 TL 0.05 · 100–250 TL 0.10 · 250–500 TL 0.25 · 500–1000 TL 0.50 · 1000–2500 TL 1.00 · ≥2500 TL 2.50. The scripts round planned levels with this table.
- **Lot:** 1 lot = 1 share.
- **Circuit breakers:** stock-level ("pay bazında devre kesici", published on KAP) and index-level halts exist; trading resumes with an auction.

## Settlement and cash

- **T+2** settlement. Most brokers let you reuse sale proceeds for purchases before settlement; cash withdrawal waits for settlement. Check your broker.

## Orders (typical broker menus)

- Types: **limit**, **piyasa** (market), **piyasadan limite** (market-to-limit).
- Validity: **günlük** (day), **KİE** (kalanı iptal et / immediate-or-cancel), **GİE** (gerçekleşmezse iptal et / fill-or-kill), **tarihli** (good-till-date) where offered.
- Conditional stop/take-profit orders are broker-side features with broker-specific behaviour; they do not guarantee the stop price, especially through a limit-down gap.

## Market segments

Yıldız Pazar, Ana Pazar, Alt Pazar, Yakın İzleme Pazarı (watchlist, higher risk), Piyasa Öncesi İşlem Platformu. Segment changes follow exchange criteria (market value, free float, liquidity).

## Volatility-based measures (VBTS)

Applied in stages for about one month each, published by Borsa İstanbul and on KAP: (1) açığa satış and kredili işlem yasağı, (2) brüt takas (gross settlement: buyers must pay in full; sold shares must be held), (3) tek fiyat (single-price auctions a few times a day), plus order-package restrictions. Stocks under measures have reduced liquidity and higher exit risk.

## Short selling and margin

Allowed only in eligible stocks and suspended by VBTS measures or regulator decisions; periods of market-wide bans have occurred (e.g. after shocks). Verify the current status before planning any short or margin trade.

## Taxes (resident individuals; verify annually)

- Capital gains on BIST-traded shares: 0% withholding at the last check (special rules exist for some securities, e.g. investment trust shares; funds are taxed differently).
- Cash dividends: 15% withholding since 22 Dec 2024 (was 10%).
- BSMV applies to brokerage commissions.
- Non-residents and corporations: different rules; ask a tax advisor.

## Corporate actions in practice

- **Bedelsiz (bonus issue):** shares increase; price base adjusted down on the ex-date; no value created.
- **Bedelli (rights issue):** rüçhan hakkı (rights) trade separately for a period; theoretical ex-rights price; dilution if not taken up.
- **Temettü:** base price reduced by the dividend on the ex-date.
- **Birleşme / bölünme / sermaye azaltımı:** check the exchange notice for the adjustment factor.
- **Halka arz (IPO):** book-building on the exchange; allocations and lock-ups in the prospectus; first-day limit-up streaks are common and often reverse later.
