# ChatGPT (web / mobil / masaüstü)

## Hesaba yükleme

1. `yigit-investment-copilot-chatgpt.zip` dosyasını indir (Releases).
2. ChatGPT → **Skills** (bazı hesaplarda Plugins → Skills) → **Create** → **Upload from your computer** → ZIP'i seç.
3. Tarama bitince skill kullanılabilir. Güncellerken eski sürümü kaldırıp yenisini yükle.

## ChatGPT'de nasıl çalışır?

ChatGPT'nin kod ortamında genellikle internet yoktur. Skill bunu bilir ve şu yollardan birini seçer:

- **Web ile:** birincil kaynakları (KAP, Borsa İstanbul, TCMB, TÜİK, İş Yatırım tabloları) açar, her sayıyı saatiyle yazar.
- **Senin dışa aktarımınla (önerilen):** TradingView Hisse Tarayıcı → Türkiye → sütunları seç → CSV dışa aktar; dosyayı sohbete yükle. Skill `map_export.py` ile eşleyip `bist_scan.py` taramasını çevrimdışı çalıştırır.
- **Bağlayıcı ile:** Ayarlar → Connectors (geliştirici modu) → MCP sunucusu olarak borsa-mcp (`https://borsa.surucu.dev/mcp`). Üçüncü taraf sunucudur; sorgular oraya gider.

## Masaüstü ChatGPT / Codex

Bilgisayarında Codex ya da ChatGPT masaüstü kullanıyorsan skill klasörünü `~/.agents/skills/` içine koy (ayrıntı: `../codex/README.md`); orada betikler internete çıkabildiği için tam BIST taraması çalışır.
