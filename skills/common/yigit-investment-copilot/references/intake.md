# Intake: what to ask, when, and the defaults

Ask only what changes the answer. Bundle blocking questions into one short message (max 3–4 items, with a suggested default for each). If the user does not answer, proceed with the labelled defaults and say which assumptions were used.

| Topic | Ask when | Question (Turkish) | Default if unanswered |
|---|---|---|---|
| Horizon | Always for buy/sell ideas unless stated | "Kaç gün/ay tutmayı düşünüyorsun?" | 3 ay (orta vade), labelled as assumption |
| Budget and share of savings | Before quantities | "Bu iş için ayırdığın tutar ve birikimine oranı?" | Give formulas and % sizes, not lots |
| Loss limit | Before quantities | "Bu işlemde en fazla ne kadar kaybetmeyi kabul edersin (TL ya da %)?" | 1% of capital per trade; speculative money capped separately |
| Benchmark | When comparing outcomes | "Hedefin TL'de mevduatı mı, doları mı, enflasyonu mu geçmek?" | Nominal TL vs deposit/money-market rate, plus a USD-based note |
| Constraints | First session | "Kaldıraç, açığa satış, VİOP/varant kullanır mısın? Katılım endeksi şartın var mı?" | Cash equities only, no leverage |
| Current holdings | Sell/add/portfolio questions | "Hangi hisseler, kaç lot, maliyetin ne?" (screenshot is fine; mask account numbers) | Analyse only the named position |
| Broker cost | When costs matter (short horizon, small caps) | "Komisyon oranın yaklaşık kaç?" | 0.15% + BSMV per side, labelled placeholder |
| Monitoring capacity | Short-term trading ideas | "Gün içinde takip edebiliyor musun?" | Assume no → prefer orders/plans that do not need intraday watching |
| Experience | Only if explanations need calibration | "Teknik terimleri açarak mı anlatayım?" | Explain terms once in plain Turkish |

Never ask for passwords, card data, national ID, account numbers or broker logins. Screenshots are welcome; verify tickers and times in them.

## Reading the request

- "En çok artacak", "kesin artar", "parayı katla", "hızlı kazanç" → keep the request, but answer with ranges, probabilities and a loss boundary; mention once that no system can guarantee returns.
- "Kısa sürede çekeceğim" → horizon-specific profile (`kisa`) and stricter liquidity/gap checks.
- "Uzun vadeli birikim" → `uzun` profile; also compare with index funds and TEFAS alternatives.
- "Emin misin?", "tekrar bak" → anti-anchoring protocol (`investment-red-team`).
