---
description: Bir işlem stratejisini BIST verisiyle bakış-önü yanlılığı olmadan, maliyetli walk-forward testle sına (örn. /strateji-test momentum XU100)
agent: borsa-analist
---

yigit-investment-copilot skill'ini yükle ve `modules/quant-research-lab/MODULE.md` akışını uygula. Strateji/evren: "$ARGUMENTS".

1. Önce araştırma kartını yaz (hipotez, mekanizma, hedef, evren, bilgi zamanı, kıyaslar, maliyet, başarısızlık koşulu).
2. Evren listesi ve 5 yıllık toplu geçmiş: `python modules/market-data-engine/scripts/price_history.py --tickers-file <liste> --range 5y --mode spark --out h5` (+ XU100 için chart modu).
3. `python modules/quant-research-lab/scripts/walkforward_backtest.py ...` ile walk-forward, maliyet ve Deflated Sharpe.
4. Sonucu XU100, eşit ağırlıklı evren ve nakit/mevduat ile kıyasla; hayatta kalma yanlılığı dahil tüm yanlılıkları yaz; hüküm ver (invalid / research-only / promising / paper-trade candidate).
