"""Public documentation templates. No private environment data."""
INSTALL='''# Installation / Kurulum

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
'''
MAINTAINING='''# One source, durable collections / Tek kaynak, kalıcı koleksiyonlar

## English

The canonical maintained collection is universal-ai-skill-library. One registry generates category navigation, bilingual skill guides, downloads and domain editions. Repositories are stable audience entry points, not manual forks.

For public maintenance: edit the relevant source under skills/common/ and its record in library-registry.json. Run <code>python tools/rebuild_library.py --root .</code> and <code>python tools/validate_current.py</code>, review the diff, then commit. The build does not install, upload, push or connect accounts. Existing licenses and historical material remain attached.

For the owner’s private master: export a privacy-reviewed portable snapshot first. Never publish private investor profiles, local home paths, tokens, conversation evidence or user PDFs. Regenerate domain views from the same canonical snapshot; do not separately edit their copied skills. Edition and file hashes expose drift. Adding a skill changes source and registry, not repository topology.

Legacy material is accessible but not counted as maintained or runtime-tested. Routine updates require no repository deletion, history rewrite or forced consolidation. Releases and account uploads are separate from a local build.

## Türkçe

Tek güncel kaynak universal-ai-skill-library. Aynı kayıt dosyası kategori gezinmesini, iki dilli rehberleri, indirmeleri ve alan sürümlerini üretir. Alan depoları ayrı elle yönetilen kopyalar değil, kalıcı giriş noktalarıdır.

Skill kaynağı ve library-registry.json kaydını düzenle; üretici ve doğrulamayı çalıştır; farkı inceleyip commit et. Üretici kurulum, yükleme, push veya hesap bağlantısı yapmaz. Özel masterdan yayın öncesinde kişisel profil/yol/anahtar/PDF kontrolü yapılır. Yeni skill için repo birleştirmek veya bölmek gerekmez.
'''
LEGACY='''# Maintained vs historical / Güncel ve tarihsel kapsam

The maintained set is declared in current-release.json, not inferred from every old file. Earlier catalogs, documents and assets remain for traceability; their former counts are not a current maintenance or runtime-test claim. Repository names and Git history are preserved.

Use README and DOWNLOADS for the current edition. Old tags/downloads may contain former provider integrations, larger catalogs or different host assumptions. Gemini Deep Research is not in the maintained edition; the former `slides` skill is now `html-slides` (browser decks only) and editable PowerPoint work moved to `presentation-studio`. No extra billed API fallback is enabled by this edition.

Türkçe: Güncel kapsam current-release.json ile tanımlanır. Eski katalog ve kaynaklar izlenebilirlik için korunur; eski sayı ve test iddiaları güncel kapsam değildir. Güncel README/indirmeleri kullan. Eski sürümler farklı sağlayıcı/host varsayımları içerebilir. Gemini Deep Research güncel sürümde yoktur; eski `slides` artık `html-slides` (yalnız tarayıcı sunumu), PowerPoint işleri `presentation-studio`'da.
'''
LICENSE_SCOPE='''# License scope and provenance / Lisans kapsamı

This is a mixed-origin collection, not blanket relicensing. Original LICENSE, NOTICE, COPYING and font licenses remain with their content. Caveman includes current Apache-2.0 and the retained legacy MIT notice; Graphify includes current and historical notices. A root license alone does not establish every bundled module’s scope.

Repository-authored documentation, graphics and packaging scripts follow the repository documentation license. Skill contents retain their applicable terms. Missing evidence is recorded in provenance-current.json, not silently declared MIT. Consult the relevant rights holder before reuse where permission is unclear.

The public snapshot records hashes and portability adaptations. Private profiles become blank input templates; original user PDFs, credentials and local environment files are not input sources. This is technical provenance, not legal advice or a rights certification for all upstream content.

Türkçe: Koleksiyon tek lisansla yeniden lisanslanmaz. Kaynak lisans/bildirimleri korunur; eksik kanıt MIT kabul edilmez. Özel profiller boş kullanıcı şablonuna çevrilir. Kaynak izi hukuki danışmanlık veya tüm içerik için izin sertifikası değildir.
'''
