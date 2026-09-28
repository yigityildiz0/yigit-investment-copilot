---
description: Eldeki pozisyonu değerlendir; tut, azalt ya da sat kararı ve yeni stop planı (örn. /hisse-sat KRDMD 1000 lot maliyet 44,2)
agent: borsa-analist
---

yigit-investment-copilot skill'ini yükle. Pozisyon bilgisi: "$ARGUMENTS".

1. Kod, adet, maliyet ve varsa ilk planı ayrıştır; eksikse tek mesajda sor (varsayılanları belirterek).
2. `python scripts/borsa.py ticker <KOD> --horizon 1m` çalıştır.
3. `modules/trade-management-exits/references/exit-playbook.md` kurallarını sırayla uygula (tez bozulması → stop → rejim → zaman → hedef → aşırı uzama → daha iyi fırsat → yoğunlaşma).
4. Karar: TUT / AZALT / SAT; tutuluyorsa yeni stop (asla eskisinden geniş değil), hedefler, alarm seviyeleri ve bir sonraki gözden geçirme tarihi. Maliyet fiyatı kararı belirlemez. Emir verme.
