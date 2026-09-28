---
description: "Sektör rotasyonu ve istenirse tek sektörün derin görünümü (örn. /borsa:sektor Finans)"
argument-hint: "[sektör adı]"
---

yigit-investment-copilot skill'ini kullan. Sektör: "$ARGUMENTS" (boşsa yalnız rotasyon tablosu).

1. `python scripts/borsa.py sector` çalıştır (sektör verildiyse `--name "<sektör>"`); SECTOR.md'yi oku.
2. `references/report-templates.md` sektör görünümü şablonu: göreli güç ve genişlik, talep-fiyat-maliyet sürücüleri, kur/faiz duyarlılığı, düzenleme, çarpanlar ve kendi geçmişleri, en iyi ve en kötü konumlanan şirketler, görüşü bozacak koşul.
3. TMS 29 ve bankaların farklı muhasebesi nedeniyle sektörler arası F/K kıyasının sınırını belirt. Emir verme.
