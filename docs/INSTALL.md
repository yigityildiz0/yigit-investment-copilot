# Installation / Kurulum

[Library](../README.md) · [Downloads](../DOWNLOADS.md) · [Türkçe](#türkçe)

Pick one skill (or a collection) and install ONE copy per app. Files on disk do not prove activation:
after installing, ask the app something the skill should handle and check that it loads.

| App | Artifact | Steps |
|---|---|---|
| **Claude Code** (CLI / desktop) | `downloads/portable-skills.zip` | Unzip; copy each skill folder to `~/.claude/skills/<name>/` (personal) or `.claude/skills/<name>/` (project). Restart the session; the skill list shows it. |
| **Claude.ai** (web, desktop app) | `packages/claude/<name>.zip` (one ZIP per skill, never split) | Settings → Capabilities → Skills → Upload skill; upload each ZIP separately and enable it. The outer `downloads/Claude.zip` is a collection of per-skill ZIPs, not one skill; unzip it and upload the inner ZIPs. |
| **Codex** (ChatGPT desktop / CLI) | `downloads/Codex.zip` | Unzip into `~/.codex/skills/` (or `~/.agents/skills/`). Too many enabled plugins can truncate the skill list; check it in a new thread. |
| **ChatGPT** (web, with plugins/skills) | `packages/chatgpt/<name>.zip` or `downloads/ChatGPT.zip` | Use the account's plugin/skill import if offered. A Knowledge upload is only documents; it installs nothing. |
| **Gemini CLI** | `downloads/portable-skills.zip` | Copy each folder to `~/.gemini/skills/<name>/` (or `.gemini/skills/` in a project); run `/skills list`. |
| **Gemini app** (web Skills) | `packages/gemini/<name>.zip` | Unzip and upload the folder in Skills. Only md/txt/py/sh/json/yaml/csv/pdf/images are accepted; other files are listed in `GEMINI-UNSUPPORTED-FILES.md`. Availability rolls out per account. |
| **OpenCode** | `downloads/portable-skills.zip` | Unzip next to your config and add `"skills": ["./skills"]` to the OpenCode config. |
| **DeepSeek Harness** | `downloads/portable-skills.zip` | Point the filesystem skill provider (agentsHome) at the extracted folder; verify the catalog lists the skill. |

Commands (Windows PowerShell, Claude Code example):

```powershell
Expand-Archive portable-skills.zip -DestinationPath "$env:TEMP/skills"
Copy-Item "$env:TEMP/skills/presentation-studio" "$HOME/.claude/skills/" -Recurse
```

Instructions supply no API key, browser session, model, GPU, Office runtime or subscription. This
edition uses existing host tools, open sources and local computation without an automatic extra billed
service. Update from the same canonical source; keep one active copy per skill.

## Türkçe

Her uygulamaya bir skill'in tek kopyasını kur; kurduktan sonra skill'in işine giren bir istekle dene.

- **Claude Code:** `portable-skills.zip` içindeki klasörü `~/.claude/skills/<ad>/` altına kopyala.
- **Claude.ai:** Ayarlar → Capabilities → Skills → `packages/claude/<ad>.zip` dosyalarını tek tek yükle ve aç .
- **Codex:** `Codex.zip` içeriğini `~/.codex/skills/` altına aç; yeni sohbette skill listesini kontrol et (çok eklenti listeyi kesebilir).
- **ChatGPT web:** Hesapta eklenti/skill içe aktarma varsa `packages/chatgpt/<ad>.zip`; Knowledge yüklemesi kurulum değildir.
- **Gemini CLI:** klasörleri `~/.gemini/skills/` altına kopyala, `/skills list` ile doğrula.
- **Gemini web:** `packages/gemini/<ad>.zip` dosyasını aç, klasörü Skills bölümüne yükle; desteklenmeyen dosyalar pakette listelenir.
- **OpenCode:** `"skills": ["./skills"]` ayarıyla klasörü göster.
- **DeepSeek Harness:** dosya sistemi skill sağlayıcısını (agentsHome) klasöre yönelt, katalogda göründüğünü doğrula.

Paket API, GPU, Office veya abonelik getirmez; ek ücretli servis otomatik seçilmez.
