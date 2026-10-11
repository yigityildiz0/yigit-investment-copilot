# One source, durable collections / Tek kaynak, kalıcı koleksiyonlar

## English

The canonical maintained collection is universal-ai-skill-library. One registry generates category navigation, bilingual skill guides, downloads and domain editions. Repositories are stable audience entry points, not manual forks.

For public maintenance: edit the relevant source under skills/common/ and its record in library-registry.json. Run <code>python tools/rebuild_library.py --root .</code> and <code>python tools/validate_current.py</code>, review the diff, then commit. The build does not install, upload, push or connect accounts. Existing licenses and historical material remain attached.

For the owner’s private master: export a privacy-reviewed portable snapshot first. Never publish private investor profiles, local home paths, tokens, conversation evidence or user PDFs. Regenerate domain views from the same canonical snapshot; do not separately edit their copied skills. Edition and file hashes expose drift. Adding a skill changes source and registry, not repository topology.

Legacy material is accessible but not counted as maintained or runtime-tested. Routine updates require no repository deletion, history rewrite or forced consolidation. Releases and account uploads are separate from a local build.

## Türkçe

Tek güncel kaynak universal-ai-skill-library. Aynı kayıt dosyası kategori gezinmesini, iki dilli rehberleri, indirmeleri ve alan sürümlerini üretir. Alan depoları ayrı elle yönetilen kopyalar değil, kalıcı giriş noktalarıdır.

Skill kaynağı ve library-registry.json kaydını düzenle; üretici ve doğrulamayı çalıştır; farkı inceleyip commit et. Üretici kurulum, yükleme, push veya hesap bağlantısı yapmaz. Özel masterdan yayın öncesinde kişisel profil/yol/anahtar/PDF kontrolü yapılır. Yeni skill için repo birleştirmek veya bölmek gerekmez.
