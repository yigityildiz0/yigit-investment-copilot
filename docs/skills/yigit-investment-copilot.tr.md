# yigit-investment-copilot

[English](yigit-investment-copilot.en.md) · [Türkçe](yigit-investment-copilot.tr.md) · [Library](../../README.tr.md)

**Değerleme, senaryo ve portföy riski kontrolleriyle BIST, TEFAS ve ABD yatırımlarını araştırır.**

## Örnek istek

> Bu şirketin açıklamalarını incele; kötü/temel/iyi senaryoları oluştur.

## Tetikleme ve yönlendirme

İstek, hostun skill açıklamasıyla eşleştirilir. Host destekliyorsa kanonik adla açık seçim de yapılabilir. Sohbete /ad yazmak tek başına kayıtlı bir komut yaratmaz.

<details>
<summary>Kaynak açıklamasının tam metni</summary>

Investment research and decision copilot for BIST stocks, TEFAS funds, US stocks, ETFs, crypto, VİOP, warrants and gold. Scans all of Borsa İstanbul (and S&P 500) with live data scripts, ranks candidates for a stated horizon, combines fundamental, valuation, analyst-expectation, technical, KAP/news, macro-regime and flow evidence, runs an investment committee and red-team review, then gives probability ranges, buy/hold/sell/trim decisions, entry-stop-target plans, position size, portfolio risk and exit rules; screens TEFAS funds, writes morning notes, backtests strategies and tracks forecast calibration with lessons. Turkish triggers: ne alayım, hangi hisse, BIST'i tara, X ayda en çok ne artar, alınır mı, satayım mı, ne zaman satmalıyım, stop nereye, kaç lot, KAP haberi, bilanço, değerleme, teknik analiz, piyasa ne durumda, sabah bülteni, sektör, portföy, hangi fon, varant, kripto, emin misin. Research only; never places orders.

</details>

## Çalışma mantığı

Varlığı ve tarihli kanıtı doğrular; tablo/değerlemeyi karşılaştırır; senaryo ve likidite/maliyet varsayımlarını sınar; emir değil karar çerçevesi üretir.

Kök giriş dosyası görevi karşılar; yalnız gereken modül ve referanslar yüklenir. Betik içermesi çalıştırıldığı anlamına gelmez. Mevcut araç, veri ve kapsam doğrulandıktan sonra görev yürütülür.

## Girdi, çıktı ve doğrulama

- Girdi: örnek istekteki hedef, ilgili dosya/URL/veri ve sonucu değiştiren kısıtlar.
- Çıktı: isteğe uygun yanıt, plan, taslak veya yetkili dosya değişikliği; dayanak ve belirsizlik açık.
- Doğrulama: yapılan kontrol ile önerilen kontrol ayrı belirtilir; erişilmeyen kaynak veya çalıştırılmayan araç kullanılmış sayılmaz.

## Ortam ve sınırlar

Paket model ağırlığı, izin, hesap veya API kredisi sağlamaz. Bu sürüm mevcut host araçları, açık erişim ve yerel işlemi kullanır; ücretli servis otomatik alternatif değildir. Klinik/yatırım çıktıları profesyonel kararın veya emir işleminin yerine geçmez.

## Modüller ve kaynak

[SKILL.md](../../skills/common/yigit-investment-copilot/SKILL.md) · [Installation](../INSTALL.md) · [License scope](../LICENSE-SCOPE.md)

| Module | Source scope |
|---|---|
| [bist-microstructure-flow](../../skills/common/yigit-investment-copilot/modules/bist-microstructure-flow/MODULE.md) | Read short-horizon liquidity and flow evidence on Borsa İstanbul — order book depth (derinlik), broker distribution (AKD), custody/settlement distribution (takas), VWAP, volume ano |
| [crypto-research-readonly](../../skills/common/yigit-investment-copilot/modules/crypto-research-readonly/MODULE.md) | Research crypto assets in a strictly read-only mode using verified network and contract identity, multi-venue price checks, liquidity and derivatives structure, tokenomics and unlo |
| [equity-opportunity-funnel](../../skills/common/yigit-investment-copilot/modules/equity-opportunity-funnel/MODULE.md) | Search a broad investable stock universe and progressively narrow it into recommendation-grade equity ideas. Use when the user asks which stock to buy, the best or highest-upside s |
| [finance-evidence-guard](../../skills/common/yigit-investment-copilot/modules/finance-evidence-guard/MODULE.md) | Automatically verify financial evidence whenever an answer uses a current price, NAV, filing value, fee, tax/legal rule, target, catalyst, macro release, analyst estimate, or the u |
| [financial-literacy-coach](../../skills/common/yigit-investment-copilot/modules/financial-literacy-coach/MODULE.md) | Teach practical financial literacy with transparent calculations and adaptive explanations across budgeting, emergency funds, debt/credit, interest, inflation, compounding, fees, t |
| [fund-etf-analyst](../../skills/common/yigit-investment-copilot/modules/fund-etf-analyst/MODULE.md) | Analyze and compare mutual funds, ETFs, index funds, money-market funds, pension funds, and TEFAS products using exact identity, mandate, benchmark, holdings, look-through overlap, |
| [investment-committee](../../skills/common/yigit-investment-copilot/modules/investment-committee/MODULE.md) | Run a structured investment committee on a finalist or a named stock before any buy, add, hold or sell decision: four analyst briefs (fundamental, technical/flow, news/KAP, macro/s |
| [investment-journal-review](../../skills/common/yigit-investment-copilot/modules/investment-journal-review/MODULE.md) | Review one completed investment/trade or a journal of many decisions while preserving the original plan, separating process quality from profit/loss, testing thesis and forecast ac |
| [investment-red-team](../../skills/common/yigit-investment-copilot/modules/investment-red-team/MODULE.md) | Independently challenge and audit an investment recommendation, thesis, valuation, portfolio action, technical setup, fund comparison, crypto analysis, or leveraged-product scenari |
| [investment-thesis-tracker](../../skills/common/yigit-investment-copilot/modules/investment-thesis-tracker/MODULE.md) | Create and maintain an append-only investment thesis with original evidence cutoff, what is priced in, falsifiable pillars, KPIs, catalysts, valuation and entry gates, risks, kill/ |
| [market-data-engine](../../skills/common/yigit-investment-copilot/modules/market-data-engine/MODULE.md) | Acquire and screen market data for Borsa İstanbul and cross-asset context: a one-shot snapshot of every listed BIST stock, bulk and full OHLCV price histories with corporate-action |
| [market-regime-analysis](../../skills/common/yigit-investment-copilot/modules/market-regime-analysis/MODULE.md) | Classify and explain the current market regime across trend, volatility, breadth, liquidity, rates, inflation, FX, credit, earnings revisions, positioning, correlations, and dated  |
| [news-catalyst-intelligence](../../skills/common/yigit-investment-copilot/modules/news-catalyst-intelligence/MODULE.md) | Turn KAP disclosures, company news, macro releases and market chatter into dated, source-ranked events with materiality, novelty, expectation gap, a financial-impact chain and a ca |
| [portfolio-risk-and-sizing](../../skills/common/yigit-investment-copilot/modules/portfolio-risk-and-sizing/MODULE.md) | Size and stress-test a proposed stock, fund, ETF, warrant, option, futures, crypto, or mixed-portfolio position using available cash, loss budget, invalidation, lot size, fees, lev |
| [pre-trade-investment-gate](../../skills/common/yigit-investment-copilot/modules/pre-trade-investment-gate/MODULE.md) | Run a final read-only readiness check before an investment or trade across exact identity, evidence cutoff, executable entry, thesis, payoff, catalysts, invalidation, quantity, max |
| [probabilistic-market-forecast](../../skills/common/yigit-investment-copilot/modules/probabilistic-market-forecast/MODULE.md) | Estimate realistic price and return ranges, target probabilities, downside probabilities, and probability-weighted scenarios for stocks, funds, ETFs, futures, warrants, crypto, com |
| [public-equity-research](../../skills/common/yigit-investment-copilot/modules/public-equity-research/MODULE.md) | Perform recommendation-grade research on a named listed company using exact security identity, point-in-time primary filings, business/segment economics, earnings quality, balance  |
| [quant-research-lab](../../skills/common/yigit-investment-copilot/modules/quant-research-lab/MODULE.md) | Test whether a trading or forecasting idea actually works before money relies on it: research cards, point-in-time data gates, historical universe and corporate-action handling, wa |
| [technical-quant-analysis](../../skills/common/yigit-investment-copilot/modules/technical-quant-analysis/MODULE.md) | Perform evidence-based technical and quantitative analysis from verified OHLCV data, including trend, momentum, volatility, volume, support/resistance, multi-timeframe structure, s |
| [trade-management-exits](../../skills/common/yigit-investment-copilot/modules/trade-management-exits/MODULE.md) | Turn an approved idea into a written trade plan and manage it until exit: entry method and order type on Borsa İstanbul, structure/ATR stops, R-multiples, targets, partial profit-t |
| [turkey-markets-analysis](../../skills/common/yigit-investment-copilot/modules/turkey-markets-analysis/MODULE.md) | Analyze Turkish financial markets using BIST, KAP, TEFAS, TCMB EVDS, TÜİK, SPK, issuer and fund documents. Use for BIST stocks, Turkish ETFs or certificates, TEFAS funds, TRY and F |
| [warrant-structured-product-analyst](../../skills/common/yigit-investment-copilot/modules/warrant-structured-product-analyst/MODULE.md) | Analyze listed warrants, certificates, turbos, and related structured products from the official product terms, executable quote, underlying distribution, strike/barrier, expiry, c |
