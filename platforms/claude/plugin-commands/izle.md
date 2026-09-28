---
description: "Pozisyonları ve izleme listesini yazılı plana göre kontrol et (örn. /borsa:izle izle.csv)"
argument-hint: "[izleme listesi CSV yolu]"
---

yigit-investment-copilot skill'ini kullan. Liste: "$ARGUMENTS" (boşsa kullanıcıdan CSV iste: code,entry,stop,target1,target2,quantity,review_date,thesis).

1. `python scripts/borsa.py izle --watchlist <yol> --kap-days 3` çalıştır; watch_report.md'yi oku.
2. Uyarıları aciliyet sırasıyla ver: stop kırıldı/yakın, hedef, +1R başabaş, trend bozulması, bilanço/temettü yakın, gözden geçirme tarihi, önemli ya da olumsuz KAP.
3. Her uyarı için planın ilgili adımını söyle; plan dışı işlem önerme. Haber yoksa "tetikleyici yok" de. Emir verme.
