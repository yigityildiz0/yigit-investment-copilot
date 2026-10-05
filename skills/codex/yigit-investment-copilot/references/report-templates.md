# Report templates

Outputs are in Turkish; section names below are the ones to use. Keep each template to what the evidence supports: an empty section is written as "yok" or "veri yok", never filled with generic text. Label claims as in [pm-judgment-standard.md](pm-judgment-standard.md).

## 1. Sabah notu (morning note)

Data: `python scripts/borsa.py brief [--watchlist izle.csv]` → `BRIEF.md`.

1. **Ana fikir** — one sentence: what today changes for the user's positions or plan, or "plan dışı işlem gerektiren gelişme yok".
2. **Gece ve sabah gelişmeleri** — the few KAP/news items that matter for holdings, watchlist or the regime, each with its impact chain (event → driver → stock).
3. **Bugünün olayları** — earnings, ex-dividend, general meetings, TCMB/TÜİK/US releases (from official calendars, dated).
4. **Piyasa ve rejim** — regime label and exposure band, index, breadth, USD/TRY, policy rate vs inflation.
5. **Fikirler** — at most three, each with trigger, invalidation and risk; skip the section when nothing qualifies.
6. **İzleme listesi** — plan triggers from the watchlist monitor (stop near, target hit, break-even move, review due).
7. **Zaman damgası** — data time, latency, sources.

## 2. Bilanço öncesi (earnings preview)

1. Date and time of release (KAP financial calendar), last four quarters' reported figures and the surprise history.
2. What the market expects: consensus (when available), management guidance, implied move (recent reaction sizes, ATR).
3. Three swing factors with the direction that matters (e.g. gross margin, FX gain/loss, net monetary position under TMS 29, loan growth for banks).
4. Scenarios: beat / in line / miss with the likely price reaction and the evidence behind each.
5. Position decision into the print: hold full size, reduce to the size that survives a gap, or wait (`BILANCO_YAKIN`).

## 3. Bilanço sonrası (earnings review)

1. Headline versus expectations; quality of the beat or miss (one-offs, FX, monetary gain, provisions, working capital).
2. Operating cash flow versus net income; balance-sheet changes (net debt, FX position).
3. Guidance or tone changes; what management did not say.
4. Thesis check: pillars intact / weakened / broken, and which evidence changed.
5. Action and the next checkpoint (`TUT`, `AZALT`, `YENİDEN DEĞERLENDİR`…) and the ledger note.

## 4. Sektör görünümü (sector overview)

Data: `python scripts/borsa.py sector --name "<sektör>"`.

1. Relative strength and breadth versus the market (3-month median, share above SMA50/SMA200).
2. Demand, pricing and cost drivers; FX and rate sensitivity; regulation.
3. Valuation: median multiples, their own history, dispersion; inflation-accounting caveats.
4. Best and worst positioned companies with one reason each.
5. What would change the view (the sector's kill condition).

## 5. Fikir üretimi (idea generation)

Run several independent sources and keep a hit-rate record of which source produced the winners.

- **Screens:** `bist_scan.py` lanes — value (cheap on several yields), quality (ROE/ROIC, Piotroski, FCF), growth, momentum/trend, reversal, expectations (target upside, surprise).
- **Thematic sweep:** a macro or structural theme (rate cuts, export recovery, defense, energy transition, tourism season) → transmission map (`turkey-transmission-map.md`) → beneficiaries and losers → screen them.
- **Special situations (BIST):** tender offers (pay alım teklifi), mergers and spin-offs, bonus issues (bedelsiz) and rights issues (bedelli) with their dilution, buyback programmes sized against daily value, index inclusion/exclusion, free-float changes, dividend policy changes, asset sales, going-private or delisting risk, SPK/VBTS measures (as risk).
- **Short/avoid list:** the same process inverted — deteriorating quality, expensive with weak momentum, manipulation flags. Useful to cut exposure even though retail short selling is limited.

Each idea leaves the stage as `ADAY` with the source, the one-line thesis and the first diligence question.

## 6. Yatırım notu (one-page investment memo)

1. **Karar ve vade** — action, horizon, size range, data time.
2. **Tez** — what is mispriced and why the gap closes (≤3 sentences).
3. **Fiyatlanan** — reverse-DCF / implied ROE / consensus and our difference.
4. **Kanıt** — the key `GERÇEK` items with dates.
5. **Katalizörler** — dated, with what would count as confirmation.
6. **Değerleme** — base value, mechanical downside, bull case; scenario skew versus the hurdle.
7. **Riskler ve iptal koşulu** — the kill condition, gap risk, binding constraint.
8. **Uygulama** — entry method, stop, targets, quantity, review date.
9. **Güven ve eksik kanıt.**

## 7. Rakam doğrulama (numbers tie-out checklist)

Before publishing any table or memo:

- Totals and sub-totals add up; weights sum to 100% (or the cash remainder is shown).
- Every percentage states its base; growth rates match the two numbers they come from.
- Currency, unit (bin/mn/mr TL) and period (quarterly, TTM, cumulative YTD) are stated and consistent; İş Yatırım cumulative figures were converted to discrete quarters.
- Prices, market caps and multiples come from the same timestamp.
- Per-share figures use the current share count after bonus/rights issues.
- Stop, entry and targets respect BIST price steps; quantities are whole shares and fit the budget.
- Every number traceable to a file in `borsa-out/` or a cited source.
