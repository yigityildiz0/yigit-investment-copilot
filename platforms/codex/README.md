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

3. Uygulamayı yeniden başlat. Skill'i `~/.codex/config.toml` içindeki `[[skills.config]]` ile açıp kapatabilirsin.

Burada betikler internete erişebildiği için tam BIST taraması, KAP akışı ve bilanço betikleri çalışır.
