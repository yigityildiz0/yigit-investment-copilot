---
description: "Portföy riski ve yeni nakdin risk paritesiyle dağıtımı (örn. /borsa:portfoy 150000 THYAO ASELS BIMAS)"
argument-hint: "bütçe KOD1 KOD2 ... [pozisyonlar.csv]"
---

yigit-investment-copilot skill'ini kullan. Girdi: "$ARGUMENTS".

1. Bütçe, aday kodlar ve varsa mevcut pozisyon dosyasını (code,quantity[,avg_cost][,stop]) ayrıştır; eksikse varsayılanı söyleyerek sor.
2. `python scripts/borsa.py portfoy --candidates <KODLAR> --budget <tutar> [--holdings <csv>] [--max-weight 0.20] [--max-sector 0.35]` çalıştır; portfolio.md'yi oku.
3. Risk payları, yüksek korelasyonlu çiftler, sektör dağılımı, VaR/ES, en kötü 20 gün, beta ve stoplara açık riski yorumla; rejimin maruziyet bandını uygula.
4. Her yeni pozisyonun ön işlem kapısından geçmesi gerektiğini belirt; dağılımı plan olarak ver. Emir verme.
