---
description: "TEFAS fonlarını tara ya da karşılaştır (örn. /fon-tara para piyasası · /fon-tara TTE IIH AFT)"
agent: borsa-analist
---

yigit-investment-copilot skill'ini kullan ve `modules/fund-etf-analyst/MODULE.md` akışını uygula. Girdi: "$ARGUMENTS".

1. Girdi kategori ise `python scripts/borsa.py fon screen --category "<kategori>"`; fon kodlarıysa `python scripts/borsa.py fon compare <KODLAR> --period 3y` ve tek kod için `fon fund <KOD>`.
2. Emsal grubu içinde tutarlılık ve maliyetle sırala; tek dönem getirisiyle seçme. Reel (TÜFE'ye göre) getiri, en büyük düşüş, valör, emir saatleri, toplam gider ve KAP belgelerini belirt.
3. Serbest (nitelikli yatırımcı) ve TEFAS dışı fonları işaretle; para piyasası alternatifini ve kullanıcının mevcut fonlarıyla çakışmayı (korelasyon) göster.
4. Rol ve dağılım aralığıyla karar ver. Emir verme.
