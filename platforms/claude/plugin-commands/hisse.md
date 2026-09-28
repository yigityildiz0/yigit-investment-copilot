---
description: "Tek hisseyi vadeye göre uçtan uca analiz et ve karar ver (örn. /borsa:hisse THYAO 1m)"
argument-hint: "KOD [vade] [america]"
---

yigit-investment-copilot skill'ini kullan. Hisse ve vade: "$ARGUMENTS" (vade boşsa 3m; ABD hissesiyse `--market america`).

1. Tahmin defteri varsa `forecast_ledger.py history --ticker KOD` ile bu hissedeki eski kararları ve dersleri oku.
2. `python scripts/borsa.py ticker KOD --horizon <vade>` çalıştır; REPORT.md, teknik.md, KAP ve bilanço dosyalarını oku (`python scripts/report_html.py --run-dir <klasör>` ile görsel sayfa).
3. Rejimi kontrol et (bugün yoksa `python scripts/borsa.py regime`).
4. `references/master-pipelines.md` B akışı: derin analiz, `valuation_models.py` (ters DCF / PD/DD–ROE), yedi PM sorusu ve iddia etiketleri, aynı sektörden bir rakip ve nakit/XU100 kıyası, yatırım komitesi, kırmızı takım, kapı.
5. Karar ve işlem planı (giriş, stop, hedefler, adet); tahmini `forecast_ledger.py add --thesis --kill --benchmark-price` ile deftere yazmayı öner. Emir verme.
