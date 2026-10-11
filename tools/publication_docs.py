"""Public documentation templates. No private environment data."""
INSTALL='''# Installation / Kurulum

[Library](../README.md) · [Downloads](../DOWNLOADS.md)

## English

1. Pick a maintained skill and read its purpose, trigger and dependencies.
2. Choose the artifact for the environment you actually use:
   - **Claude Code:** place the complete selected skill directory in the supported personal/project skill directory. Keep resources beside SKILL.md. Extraction does not change user settings.
   - **Codex:** use the local-folder edition in the supported skills directory; use a plugin bundle only when the host supports its manifest.
   - **DeepSeek Harness:** select the directory through your configured filesystem skill provider. Verify it appears and loads in the catalog. A file on disk is not proof of invocation.
   - **Claude web:** unpack the collection and import individual root/support ZIPs through the account’s supported skill flow. The outer collection is not one skill.
   - **ChatGPT web / GPT Knowledge:** do not assume a ZIP installs executable skills or MCP tools. Knowledge uploads are documents. Use a skill/plugin import only if the actual account offers it; otherwise use instructions as reference and disclose missing capabilities.
3. Test one example request. Instructions do not supply an API key, browser session, model, GPU, Office runtime or subscription.
4. Update from the same canonical source; keep one active copy per skill and preserve user edits. Domain collections overlap intentionally.

This edition uses existing host tools, open sources and local computation without an automatic extra billed service. Your existing model/host plan still has its own usage costs. Host capabilities and file limits change; verify current documentation instead of treating these files as account entitlement.

## Türkçe

1. Güncel katalogdan skill seç; amaç, tetikleme ve bağımlılıkları oku.
2. Claude Code/Codex için tam klasörü desteklenen yerel skill dizinine koy. Harness’ta mevcut dosya sistemi sağlayıcısıyla seç ve katalogdan yüklenmesini doğrula.
3. Claude web dış ZIPini aç; kök/destek parça ZIPlerini hesabın desteklediği akışla ayrı yükle. Dış ZIP tek skill değildir.
4. ChatGPT/GPT Knowledge’a ZIP yüklemek çalıştırılabilir skill veya MCP kurmaz. Yalnız hesabın gerçekten sunduğu mekanizmayı kullan; yoksa talimatlar bir referanstır.
5. Bir örnek istekle dene. Dosyanın bulunması, aracın çalışması veya klinik/finansal etkinlik kanıtı değildir. API, GPU, Office veya abonelik paketle gelmez.
6. Aynı kaynaktan güncelle; çift etkin kopya oluşturma. Mevcut model/host kullanımının kendi maliyeti ayrıdır; ek ücretli servis otomatik seçilmez.
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

Use README and DOWNLOADS for the current edition. Old tags/downloads may contain former provider integrations, larger catalogs or different host assumptions. Gemini Deep Research is not in the maintained edition. No extra billed API fallback is enabled by this edition.

Türkçe: Güncel kapsam current-release.json ile tanımlanır. Eski katalog ve kaynaklar izlenebilirlik için korunur; eski sayı ve test iddiaları güncel kapsam değildir. Güncel README/indirmeleri kullan. Eski sürümler farklı sağlayıcı/host varsayımları içerebilir. Gemini Deep Research güncel sürümde yoktur.
'''
LICENSE_SCOPE='''# License scope and provenance / Lisans kapsamı

This is a mixed-origin collection, not blanket relicensing. Original LICENSE, NOTICE, COPYING and font licenses remain with their content. Caveman includes current Apache-2.0 and the retained legacy MIT notice; Graphify includes current and historical notices. A root license alone does not establish every bundled module’s scope.

Repository-authored documentation, graphics and packaging scripts follow the repository documentation license. Skill contents retain their applicable terms. Missing evidence is recorded in provenance-current.json, not silently declared MIT. Consult the relevant rights holder before reuse where permission is unclear.

The public snapshot records hashes and portability adaptations. Private profiles become blank input templates; original user PDFs, credentials and local environment files are not input sources. This is technical provenance, not legal advice or a rights certification for all upstream content.

Türkçe: Koleksiyon tek lisansla yeniden lisanslanmaz. Kaynak lisans/bildirimleri korunur; eksik kanıt MIT kabul edilmez. Özel profiller boş kullanıcı şablonuna çevrilir. Kaynak izi hukuki danışmanlık veya tüm içerik için izin sertifikası değildir.
'''
