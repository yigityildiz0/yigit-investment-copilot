---
description: "Bir stratejiyi BIST verisiyle bakış-önü yanlılığı olmadan, maliyetli walk-forward testle sına (örn. /strateji-test momentum XU100)"
agent: borsa-analist
---

yigit-investment-copilot skill'ini kullan ve `modules/quant-research-lab/MODULE.md` akışını uygula. Strateji/evren: "$ARGUMENTS".

1. Araştırma kartını yaz (hipotez, mekanizma, hedef, evren, bilgi zamanı, kıyaslar, maliyet, başarısızlık koşulu).
2. Hızlı dış görünüm: kurulum hazır listedeyse `python scripts/borsa.py taban --horizon <vade>` (tabana göre fark, yıllara göre istikrar).
3. Evren ve 5 yıllık geçmiş: `python modules/market-data-engine/scripts/price_history.py --tickers-file <liste> --range 5y --mode spark --out h5` (+ XU100 chart modu); `walkforward_backtest.py` ile walk-forward, maliyet ve Deflated Sharpe.
4. XU100, eşit ağırlıklı evren ve nakit/mevduat ile kıyasla; hayatta kalma dahil yanlılıkları yaz; hüküm ver (invalid / research-only / promising / paper-trade candidate).
