# Claude (claude.ai ve Claude Code)

## claude.ai (web / masaüstü / mobil)

1. `yigit-investment-copilot-claude.zip` dosyasını indir (açıklaması claude.ai'nin 200 karakter sınırına göre kısaltılmıştır).
2. Settings → Capabilities → **Code execution** açık olsun.
3. Customize → **Skills** → **Upload a skill** → ZIP'i seç.
4. claude.ai'nin kod ortamında internet kısıtlıdır; skill web araması ve senin yüklediğin CSV ile çalışır (ChatGPT rehberindeki "dışa aktarım" yolu aynıdır).

## Claude Code (terminal / masaüstü uygulaması)

ZIP'i aç ve klasörü `~/.claude/skills/yigit-investment-copilot/` olarak kopyala ya da:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File install/install.ps1 -Claude
```

```bash
# macOS / Linux
bash install/install.sh --claude
```

Claude Code betikleri doğrudan çalıştırır; `python scripts/borsa.py pipeline --horizon 3m` ile tüm BIST taranır. Skill, istek uygun olduğunda otomatik devreye girer ya da `/yigit-investment-copilot` ile çağrılır.
