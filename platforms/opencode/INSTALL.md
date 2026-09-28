# OpenCode kurulumu / installation

Bu ZIP'in içi / contents:

```
skills/yigit-investment-copilot/   → ~/.config/opencode/skills/yigit-investment-copilot/
agents/borsa-analist.md            → ~/.config/opencode/agents/borsa-analist.md
commands/*.md                      → ~/.config/opencode/commands/
```

1. Kopyala (Windows: `%USERPROFILE%\.config\opencode\...`).
2. **Önemli:** Aynı skill zaten `~/.claude/skills` veya `~/.agents/skills` içinde kuruluysa (Claude Code / Codex kullanıyorsan) `skills/` klasörünü kopyalama; OpenCode oradan zaten okur ve aynı isimli iki skill çakışır. Sadece `agents/` ve `commands/` yeterli (`install/install.ps1 -OpenCodeExtras`).
3. OpenCode'u yeniden başlat. Komutlar:
   `/borsa-tara 3m` · `/hisse-analiz THYAO 1m` · `/hisse-sat KRDMD 1000 lot maliyet 44,2` · `/piyasa` · `/sabah-bulteni izle.csv` · `/sektor Finans` · `/fon-tara para piyasası` · `/portfoy-kur 150000 THYAO ASELS BIMAS` · `/izle izle.csv` · `/strateji-test momentum XU100`.
   Ajan: `@borsa-analist` ya da ajan seçicisinden **borsa-analist**.
4. Betikler Python 3.9+ ister (yalnız standart kütüphane).

**If the skill is already installed for Claude Code or Codex, copy only `agents/` and `commands/`** — OpenCode also reads `~/.claude/skills` and `~/.agents/skills`, and duplicate skill names conflict.
