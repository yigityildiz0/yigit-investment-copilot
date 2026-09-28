---
description: "Tüm BIST'i vadeye göre tara; rejim, adaylar, finalist kanıtları ve karar (örn. /borsa-tara 3m)"
argument-hint: "[vade: 1w|2w|1m|3m|6m|1y] [XU100]"
---

yigit-investment-copilot skill'ini kullan. Vade ve seçenekler: "$ARGUMENTS" (vade boşsa 3m kabul et ve söyle).

1. Skill kökünden `python scripts/borsa.py pipeline --horizon <vade>` çalıştır (XU100 yazıldıysa `--universe XU100`). REPORT.md'yi oku; görsel sürüm REPORT.html'in yolunu ver.
2. İlk satırda piyasa rejimi ve maruziyet bandı. Düşüş trendinde nakit/para piyasası fonu gerçek alternatiftir.
3. `references/master-pipelines.md` A akışı: huni → finalistlerde derin analiz (`valuation_models.py` ile ne fiyatlanmış, `borsa.py taban` ile taban oranı, `references/pm-judgment-standard.md` yedi soru) → yatırım komitesi → kırmızı takım → işlem öncesi kapı.
4. Yalnız kapıyı geçen 1–3 hisse için `trade_plan.py` ile plan; geçemeyenleri ADAY / İZLE / KANIT BEKLE olarak gerekçesiyle listele.
5. Kısa yanıt formatı; kaynak ve veri zamanı. Emir verme.
