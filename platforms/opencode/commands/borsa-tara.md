---
description: Tüm BIST'i verilen vadeye göre tara ve en iyi adayları derin analizle değerlendir (örn. /borsa-tara 3m)
agent: borsa-analist
---

yigit-investment-copilot skill'ini yükle. Vade: "$ARGUMENTS" (boşsa 3m kabul et ve belirt).

1. Skill kökünden `python scripts/borsa.py pipeline --horizon <vade>` çalıştır ve oluşan REPORT.md'yi oku.
2. Piyasa rejimini ve maruziyet bandını ilk satırda söyle.
3. `references/master-pipelines.md` A akışını uygula: huni, finalistlerde derin analiz, yatırım komitesi, kırmızı takım, işlem öncesi kapı.
4. Yalnız kapıyı geçen 1–3 hisse için `trade_plan.py` ile işlem planı çıkar; geçemeyenleri gerekçesiyle ADAY/İZLE olarak listele.
5. Kısa yanıt formatını kullan; kaynak ve veri zamanlarını belirt. Emir verme.
