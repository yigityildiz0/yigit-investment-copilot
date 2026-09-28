# Codex CLI / ChatGPT masaüstü

Codex ve ChatGPT masaüstü uygulaması kişisel skill'leri `~/.agents/skills/` klasöründen okur.

1. `yigit-investment-copilot-chatgpt.zip` dosyasını indir (aynı paket).
2. Klasörü `~/.agents/skills/yigit-investment-copilot/` olarak kopyala ya da kurulum betiğini çalıştır:

```powershell
powershell -ExecutionPolicy Bypass -File install/install.ps1 -Codex
```

```bash
bash install/install.sh --codex
```

3. Uygulamayı yeniden başlat. Skill istekle kendiliğinden seçilir; açıkça çağırmak için mesaja `$yigit-investment-copilot` yaz ya da `/skills` listesinden seç. Görünen ad, simge, renk ve varsayılan istem `agents/openai.yaml` dosyasındadır. Skill'i `~/.codex/config.toml` içindeki `[[skills.config]]` ile açıp kapatabilirsin.

Burada betikler internete erişebildiği için tam BIST ve S&P 500 taraması, KAP akışı, bilanço, TCMB faiz/TÜFE, TEFAS fon ve HTML pano komutları çalışır:

```bash
python scripts/borsa.py pipeline --horizon 3m
python scripts/borsa.py brief
python scripts/borsa.py fon screen --category "para piyasası"
```
