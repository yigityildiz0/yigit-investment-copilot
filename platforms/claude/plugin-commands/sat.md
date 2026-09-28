---
description: "Eldeki pozisyonu değerlendir: tut, azalt ya da sat ve yeni stop planı (örn. /borsa:sat KRDMD 1000 lot maliyet 44,2)"
argument-hint: "KOD adet maliyet [ilk plan]"
---

yigit-investment-copilot skill'ini kullan. Pozisyon bilgisi: "$ARGUMENTS".

1. Kod, adet, maliyet ve varsa ilk planı ayrıştır; eksikse tek mesajda sor (varsayılanları belirterek).
2. `python scripts/borsa.py ticker <KOD> --horizon 1m` çalıştır; defterde kayıt varsa `forecast_ledger.py history --ticker <KOD>` oku.
3. `modules/trade-management-exits/references/exit-playbook.md` kurallarını sırayla uygula (tez bozulması → stop → rejim → zaman → hedef → aşırı uzama → daha iyi fırsat → yoğunlaşma).
4. Karar: TUT / AZALT / SAT / KORUMA; tutuluyorsa yeni stop (asla eskisinden geniş değil), hedefler, alarm seviyeleri ve sonraki gözden geçirme tarihi. Pozisyonu izleme CSV'sine eklemeyi öner. Maliyet fiyatı kararı belirlemez. Emir verme.
