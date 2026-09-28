---
description: "Günün notu: rejim, makro, KAP, takvim, hareketliler ve izleme listesi tetikleyicileri (örn. /sabah-bulteni izle.csv)"
agent: borsa-analist
---

yigit-investment-copilot skill'ini kullan. İzleme listesi: "$ARGUMENTS" (boşsa listesiz).

1. `python scripts/borsa.py brief` çalıştır (liste verildiyse `--watchlist <yol>`); BRIEF.md'yi oku.
2. `references/report-templates.md` sabah notu şablonuyla yaz: tek cümle ana fikir → gece/sabah gelişmeleri ve etkisi → bugünün olayları → piyasa ve rejim → en çok üç kanıtlı fikir (tetik, iptal, risk) → izleme listesi tetikleyicileri → zaman damgası.
3. Önemli bir şey yoksa "plan dışı işlem gerektiren gelişme yok" de. Haber uydurma; rutin geri alım bildirimlerini ana haber yapma. Emir verme.
