# Claude (claude.ai ve Claude Code)

## Claude Code — eklenti (önerilen)

```bash
claude plugin marketplace add yigityildiz0/yigit-investment-copilot
claude plugin install borsa@yigit-investment-copilot
```

Oturum içinden aynı işlem: `/plugin marketplace add yigityildiz0/yigit-investment-copilot`, ardından `/plugin install borsa@yigit-investment-copilot`. Eklenti skill'i ve şu komutları yükler (eklenti adıyla ön ekli):

| Komut | Ne yapar |
|---|---|
| `/borsa:tara 3m` | Tüm BIST taraması → rejim → huni → komite → plan |
| `/borsa:hisse THYAO 1m` | Tek hisse derin analiz ve karar |
| `/borsa:sat KRDMD 1000 lot maliyet 44,2` | Pozisyon değerlendirme: tut / azalt / sat, yeni stop |
| `/borsa:piyasa` | Rejim, genişlik, faiz-enflasyon, önemli KAP |
| `/borsa:bulten izle.csv` | Sabah notu |
| `/borsa:sektor Finans` | Sektör rotasyonu ve üyeler |
| `/borsa:fon para piyasası` | TEFAS fon taraması / karşılaştırması |
| `/borsa:portfoy 150000 THYAO ASELS BIMAS` | Risk paritesiyle dağıtım ve portföy riski |
| `/borsa:izle izle.csv` | Pozisyonları yazılı plana göre kontrol |
| `/borsa:strateji momentum XU100` | Walk-forward strateji testi |

Güncelleme: `claude plugin marketplace update yigit-investment-copilot` ve `claude plugin update borsa@yigit-investment-copilot` (ya da `/plugin` panelinden). Kaldırma: `claude plugin uninstall borsa@yigit-investment-copilot`.

## Claude Code — elle kurulum

`yigit-investment-copilot-claude-code.zip` içindeki `skills/` ve `commands/` klasörlerini `~/.claude/` altına kopyala ya da:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File install/install.ps1 -Claude
```

```bash
# macOS / Linux
bash install/install.sh --claude
```

Bu yol ön eksiz komutlar kurar: `/borsa-tara`, `/hisse-analiz`, `/hisse-sat`, `/piyasa`, `/sabah-bulteni`, `/sektor`, `/fon-tara`, `/portfoy-kur`, `/izle`, `/strateji-test`. Aynı adlı mevcut komut dosyaları `.bak-<zaman>` olarak yedeklenir. **Eklenti ile elle kurulumu birlikte kullanma** (skill iki kez yüklenir).

Claude Code betikleri doğrudan çalıştırır; `python scripts/borsa.py pipeline --horizon 3m` tüm BIST'i tarar ve `REPORT.html` panosunu üretir. Skill, istek uygun olduğunda kendiliğinden devreye girer.

## claude.ai (web / masaüstü / mobil)

1. `yigit-investment-copilot-claude.zip` dosyasını indir (açıklaması claude.ai'nin 200 karakter sınırına göre kısaltılmıştır).
2. Settings → Capabilities → **Code execution** açık olsun.
3. Customize → **Skills** → **Upload a skill** → ZIP'i seç.
4. claude.ai'nin kod ortamında internet kısıtlıdır; skill web araması ve senin yüklediğin CSV ile çalışır (ChatGPT rehberindeki "dışa aktarım" yolu aynıdır). Değerleme, portföy, taban oranı ve tahmin defteri betikleri çevrimdışı da çalışır.
