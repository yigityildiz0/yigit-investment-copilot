---
description: Tek bir hisseyi vadeye göre uçtan uca analiz et (örn. /hisse-analiz THYAO 1m)
agent: borsa-analist
---

yigit-investment-copilot skill'ini yükle. Hisse: "$1", vade: "$2" (boşsa 3m).

1. `python scripts/borsa.py ticker $1 --horizon <vade>` çalıştır; REPORT.md, teknik.md, KAP ve finansal dosyalarını oku.
2. Güncel piyasa rejimini kontrol et (bugün yoksa `python scripts/borsa.py regime`).
3. `references/master-pipelines.md` B akışı: derin analiz, aynı sektörden bir rakip ve nakit/XU100 ile kıyas, yatırım komitesi, kırmızı takım, kapı.
4. Karar ve işlem planı (giriş, stop, hedefler, adet formülü) ver; tahmini deftere yazmayı öner. Emir verme.
