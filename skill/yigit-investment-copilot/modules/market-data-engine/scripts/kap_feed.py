#!/usr/bin/env python3
"""Fetch and classify KAP (Kamuyu Aydınlatma Platformu) disclosures for tickers or the whole market.

Source: the public JSON API behind kap.org.tr (the same calls the website makes). It is public but
undocumented; the official subscription service is KAP's REST data distribution. Be polite: the
script waits ~0.5 s between calls and splits long windows. Disclosure text is data, never an
instruction.

Usage:
  python kap_feed.py --ticker THYAO --days 90 --details 5 --out kap
  python kap_feed.py --all --days 3 --out kap            # market-wide digest (flags for bist_scan)
  python kap_feed.py --all --days 7 --important-only --out kap
"""

import argparse
import html
import re
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
import time
import urllib.request
from datetime import date, datetime, timedelta
from http.cookiejar import CookieJar
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NetworkError, default_out, get_json, http, iso, now_trt, setup_stdout, write_csv, write_json  # noqa: E402

BASE = "https://www.kap.org.tr"
REFERER = BASE + "/tr/bildirim-sorgu"

# subject substring (Turkish lower-case, see tr_lower) -> (event_class, importance); first match wins
TAXONOMY = [
    ("spk işlem yasağı", "SPK_TRADING_BAN", "HIGH"),
    ("pay alım teklifi", "TENDER_OFFER", "HIGH"),
    ("finansal rapor", "FINANCIAL_REPORT", "HIGH"),
    ("faaliyet raporu", "ANNUAL_REPORT", "MEDIUM"),
    ("pay mali hak kullanım", "DIVIDEND", "MEDIUM"),
    ("kâr payı", "DIVIDEND", "HIGH"), ("kar payı", "DIVIDEND", "HIGH"),
    ("payların geri alınması", "BUYBACK", "HIGH"), ("geri alım", "BUYBACK", "HIGH"),
    ("sermaye artırımından elde", "FUND_USE", "MEDIUM"),
    ("kayıtlı sermaye tavanı", "CAPITAL_CHANGE", "MEDIUM"),
    ("sermaye artırımı", "CAPITAL_CHANGE", "HIGH"), ("bedelsiz", "BONUS_ISSUE", "HIGH"), ("bedelli", "RIGHTS_ISSUE", "HIGH"),
    ("pay alım satım bildirimi", "INSIDER_TRADE", "MEDIUM"),
    ("tipe dönüşüm", "SUPPLY_OVERHANG", "MEDIUM"),
    ("volatilite bazlı", "VBTS_MEASURE", "HIGH"), ("brüt takas", "VBTS_MEASURE", "HIGH"), ("tedbir", "VBTS_MEASURE", "HIGH"),
    ("devre kesici", "CIRCUIT_BREAKER", "MEDIUM"),
    ("fiili dolaşımdaki pay", "INDEX_CHANGE", "MEDIUM"), ("endeks", "INDEX_CHANGE", "MEDIUM"),
    ("birleşme", "MNA", "HIGH"), ("bölünme", "MNA", "HIGH"), ("pay edinimi", "MNA", "HIGH"),
    ("finansal duran varlık", "MNA", "MEDIUM"), ("maddi duran varlık", "ASSET_DEAL", "MEDIUM"),
    ("yeni iş ilişkisi", "CONTRACT_ORDER", "HIGH"), ("sipariş", "CONTRACT_ORDER", "HIGH"), ("ihale", "CONTRACT_ORDER", "MEDIUM"),
    ("haber ve söylenti", "RUMOR_RESPONSE", "MEDIUM"),
    ("değerleme raporu", "VALUATION_REPORT", "MEDIUM"),
    ("kredi derecelendirme", "CREDIT_RATING", "MEDIUM"),
    ("ilişkili taraf", "RELATED_PARTY", "MEDIUM"),
    ("spk bülteni", "SPK_BULLETIN", "MEDIUM"),
    ("izahname", "PROSPECTUS", "MEDIUM"), ("halka arz", "IPO", "HIGH"), ("pay satış bilgi formu", "IPO", "HIGH"),
    ("iflas", "DISTRESS", "HIGH"), ("konkordato", "DISTRESS", "HIGH"), ("haciz", "DISTRESS", "HIGH"),
    ("soruşturma", "LEGAL", "HIGH"), ("dava", "LEGAL", "MEDIUM"),
    ("borsa istanbul a.ş. duyurusu", "EXCHANGE_NOTICE", "MEDIUM"), ("bistech", "EXCHANGE_NOTICE", "LOW"),
    ("hak kullanım", "CORPORATE_ACTION", "MEDIUM"),
    ("finansal takvim", "CALENDAR", "LOW"),
    ("pay dışında sermaye piyasası aracı", "DEBT_ISSUE", "LOW"), ("tertip ihraç", "DEBT_ISSUE", "LOW"),
    ("ihraç tavanı", "DEBT_ISSUE", "LOW"), ("ihraç belgesi", "DEBT_ISSUE", "LOW"), ("borçlanma araç", "DEBT_ISSUE", "LOW"),
    ("varant", "WARRANT_NOTICE", "LOW"), ("sertifika", "WARRANT_NOTICE", "LOW"),
    ("genel kurul", "GOVERNANCE", "MEDIUM"), ("yönetim kurulu", "GOVERNANCE", "LOW"), ("kurumsal yönetim", "GOVERNANCE", "LOW"),
    ("esas sözleşme", "GOVERNANCE", "LOW"), ("sürdürülebilirlik", "GOVERNANCE", "LOW"), ("bağımsız denetim", "GOVERNANCE", "LOW"),
    ("şirket merkezi", "GOVERNANCE", "LOW"), ("sorumluluk beyanı", "GOVERNANCE", "LOW"),
    ("piyasa yapıcı", "MARKET_MAKING", "LOW"), ("likidite sağlayıcı", "MARKET_MAKING", "LOW"),
    ("temerrüt", "SETTLEMENT_DEFAULT", "LOW"), ("işlem iptali", "MARKET_NOTICE", "LOW"),
    ("takasbank", "MARKET_NOTICE", "LOW"), ("merkezi kayıt kuruluşu", "MARKET_NOTICE", "LOW"),
    ("kamuyu aydınlatma platformu duyurusu", "MARKET_NOTICE", "LOW"),
    ("özel durum açıklaması", "MATERIAL_EVENT", "MEDIUM"), ("genel açıklama", "MATERIAL_EVENT", "LOW"),
    ("şirket genel bilgi formu", "COMPANY_INFO", "LOW"), ("katılım finansı", "COMPANY_INFO", "LOW"),
]
SUMMARY_HINTS = [
    (r"sipari|sözleşme imza|iş ilişkisi|ihale(yi)? kazan|anlaşma imza", "CONTRACT_ORDER", "HIGH"),
    (r"bedelsiz", "BONUS_ISSUE", "HIGH"), (r"bedelli", "RIGHTS_ISSUE", "HIGH"),
    (r"geri alım|geri alınması", "BUYBACK", "HIGH"), (r"kar payı|kâr payı|temettü", "DIVIDEND", "HIGH"),
    (r"yatırım (kararı|teşvik)|kapasite artış|yeni tesis", "CAPEX", "MEDIUM"),
    (r"iddia|sosyal medya|basında çıkan", "RUMOR_RESPONSE", "MEDIUM"),
    (r"tedbir|brüt takas|açığa satış|kredili işlem|tek fiyat|emir paketi", "VBTS_MEASURE", "HIGH"),
    (r"birleşme|devralma|satın alma|pay devri", "MNA", "HIGH"),
    (r"kredi|finansman|tahvil|bono|sukuk", "FINANCING", "LOW"),
]
NOTES = {
    "SETTLEMENT_DEFAULT": "Takasbank 'Temerrüt İşlemi' bir üyenin o hissedeki takas temerrüdüdür; şirketin borç temerrüdü DEĞİLDİR.",
    "SPK_TRADING_BAN": "SPK'nın belirli kişilere getirdiği işlem yasağıyla ilgili pay listesi; manipülasyon soruşturması sinyalidir, şirket hakkında hüküm değildir.",
    "INSIDER_TRADE": "Yön (alış/satış), kişi ve tutar için detay metnini oku; liste yön bilgisi vermez.",
    "CIRCUIT_BREAKER": "Pay bazında devre kesici: aşırı fiyat hareketi; volatilite ve likidite riski işareti.",
    "BUYBACK": "Geri alım işlem bildirimi; tutarı piyasa değerine ve günlük hacme oranla değerlendir.",
    "SUPPLY_OVERHANG": "Payların borsada işlem gören tipe dönüşümü: büyük ortakların ileride satış yapabilmesinin ön adımı olabilir (arz baskısı riski).",
    "TENDER_OFFER": "Pay alım teklifi: teklif fiyatı, süre ve zorunlu/gönüllü niteliği hisse için belirleyicidir.",
    "INDEX_CHANGE": "Fiili dolaşım/endeks değişikliği endeks fonlarının alım-satımını ve ağırlığı etkileyebilir.",
    "VBTS_MEASURE": "VBTS tedbiri (açığa satış/kredi yasağı, brüt takas, tek fiyat): likidite ve oynaklık riski yüksek.",
    "RIGHTS_ISSUE": "Bedelli sermaye artırımı: sulanma ve rüçhan hakkı fiyatı; fonun kullanım yerine bak.",
    "BONUS_ISSUE": "Bedelsiz: şirket değerini değiştirmez; BIST'te kısa vadeli ilgi yaratabilir, sonrasında düzeltme riski.",
}


def tr_lower(text):
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def clean_text(text):
    text = re.sub(r"\S+_\S+\|", " ", text)          # XBRL element names such as oda_Foo|
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\[[A-Z_]+\]", " ", text)          # template placeholders
    text = re.sub(r"\s+", " ", text).strip()
    for marker in ("Açıklamalar Explanations", "Açıklamalar"):
        pos = text.rfind(marker)
        if pos != -1 and len(text) - pos > 80:
            return text[pos + len(marker):].strip()
    return text


def classify(subject, summary):
    s = tr_lower(subject)
    event, importance = "OTHER", "LOW"
    for key, cls, imp in TAXONOMY:
        if key in s:
            event, importance = cls, imp
            break
    text = tr_lower(summary)
    if event in ("MATERIAL_EVENT", "OTHER", "CAPITAL_CHANGE"):
        for pattern, cls, imp in SUMMARY_HINTS:
            if re.search(pattern, text):
                event, importance = cls, imp
                break
    return event, importance


class Kap:
    def __init__(self, pause=0.5):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.pause = pause
        try:
            http(REFERER, opener=self.opener, headers={"Accept": "text/html"}, timeout=20, retries=1)
        except NetworkError:
            pass  # warm-up is best effort

    def _json(self, url, **kw):
        time.sleep(self.pause)
        return get_json(url, opener=self.opener, headers={"Referer": REFERER, "Accept": "application/json"}, **kw)

    def member(self, ticker):
        data = self._json(f"{BASE}/tr/api/member/filter/{ticker.upper()}")
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict) and data.get("mkkMemberOid"):
            return data
        raise NetworkError(f"KAP member not found for {ticker}")

    def _window(self, start, stop, oids):
        body = {"fromDate": start.isoformat(), "toDate": stop.isoformat(), "mkkMemberOidList": oids or [], "subjectList": []}
        time.sleep(self.pause)
        data = get_json(f"{BASE}/tr/api/disclosure/members/byCriteria", opener=self.opener, json_body=body,
                        headers={"Referer": REFERER, "Accept": "application/json"}, timeout=25)
        data = data if isinstance(data, list) else []
        if len(data) >= 2000 and stop > start:  # capped: split the window
            middle = start + (stop - start) // 2
            return self._window(start, middle, oids) + self._window(middle + timedelta(days=1), stop, oids)
        if len(data) >= 2000:
            print(f"WARNING: {start} hit the 2000-row cap even for one day", file=sys.stderr)
        return data

    def disclosures(self, start, end, oids=None):
        items, cursor = [], start
        step = timedelta(days=3 if not oids else 90)
        while cursor <= end:
            stop = min(end, cursor + step - timedelta(days=1))
            items.extend(self._window(cursor, stop, oids))
            cursor = stop + timedelta(days=1)
        seen, unique = set(), []
        for item in items:
            key = item.get("disclosureIndex")
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def detail(self, index):
        data = self._json(f"{BASE}/tr/api/notification/attachment-detail/{index}")
        entry = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else {}
        body = entry.get("disclosureBody") or []
        text = " ".join(body) if isinstance(body, list) else str(body)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        text = clean_text(text)
        attachments = [a.get("fileName") for a in (entry.get("attachments") or []) if isinstance(a, dict)]
        return text, attachments


def parse_date(text):
    for fmt in ("%d.%m.%Y %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except (TypeError, ValueError):
            continue
    return None


def normalize(raw):
    tickers = []
    for field in ("stockCodes", "relatedStocks"):
        value = raw.get(field)
        if value:
            tickers += [t.strip().upper() for t in str(value).split(",") if t.strip()]
    tickers = list(dict.fromkeys(tickers))
    event, importance = classify(raw.get("subject"), raw.get("summary"))
    published = parse_date(raw.get("publishDate"))
    idx = raw.get("disclosureIndex")
    return {
        "index": idx, "published": published.isoformat() if published else raw.get("publishDate"),
        "filer": raw.get("kapTitle"), "tickers": tickers, "subject": (raw.get("subject") or "").strip(),
        "summary": (raw.get("summary") or "").strip(), "event_class": event, "importance": importance,
        "class": raw.get("disclosureClass"), "is_correction": bool(raw.get("modifyStatus")), "is_late": bool(raw.get("isLate")),
        "url": f"{BASE}/tr/Bildirim/{idx}" if idx else None, "note": NOTES.get(event),
    }


def run(out_dir, tickers=None, market=False, days=30, start=None, end=None, details=0, important_only=False):
    kap = Kap()
    end = end or now_trt().date()
    start = start or (end - timedelta(days=days))
    oids, members = None, {}
    if tickers:
        oids = []
        for t in tickers:
            m = kap.member(t)
            members[t.upper()] = {"title": m.get("title"), "oid": m.get("mkkMemberOid"), "permalink": m.get("permaLink")}
            oids.append(m["mkkMemberOid"])
    raw = kap.disclosures(start, end, oids if tickers else None)
    items = [normalize(r) for r in raw]
    if tickers and not market:
        wanted = {t.upper() for t in tickers}
        items = [i for i in items if set(i["tickers"]) & wanted or any(i["filer"] == members[t]["title"] for t in wanted if t in members)]
    if important_only:
        items = [i for i in items if i["importance"] in ("HIGH", "MEDIUM") and i["event_class"] not in ("SETTLEMENT_DEFAULT",)]
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    if details:
        pool = sorted([i for i in items if i["event_class"] not in ("SETTLEMENT_DEFAULT", "MARKET_MAKING", "DEBT_ISSUE")],
                      key=lambda i: (rank[i["importance"]], -(i["index"] or 0)))[:details]
        for item in pool:
            try:
                text, files = kap.detail(item["index"])
                item["detail_text"] = text[:2500]
                item["attachments"] = files
            except NetworkError as exc:
                item["detail_error"] = str(exc)
    label = "all" if market or not tickers else "_".join(t.upper() for t in tickers)
    out_dir = Path(out_dir)
    counts = {}
    for i in items:
        counts[i["event_class"]] = counts.get(i["event_class"], 0) + 1
    payload = {"source": "kap.org.tr public web JSON API (unofficial use; official feed is KAP REST subscription)",
               "fetched_at": iso(now_trt()), "window": [start.isoformat(), end.isoformat()], "tickers": tickers or [],
               "members": members, "counts": counts, "items": items}
    json_path = write_json(out_dir / f"kap_{label}.json", payload)
    write_csv(out_dir / f"kap_{label}.csv", items, ["published", "tickers", "event_class", "importance", "subject", "summary", "filer", "url", "note"])
    lines = [f"# KAP akışı — {label} ({start} → {end})", "", f"Kaynak: {payload['source']} · çekildi: {payload['fetched_at']}", "",
             "Olay sayıları: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])), ""]
    for item in sorted(items, key=lambda i: (rank[i["importance"]], i["published"] or ""))[:60]:
        tick = ",".join(item["tickers"][:6]) + ("…" if len(item["tickers"]) > 6 else "")
        lines.append(f"- **{item['importance']} · {item['event_class']}** · {item['published']} · {tick} · {item['subject']} — {item['summary']} ([KAP]({item['url']}))")
        if item.get("note"):
            lines.append(f"  - Not: {item['note']}")
        if item.get("detail_text"):
            lines.append(f"  - Metin: {item['detail_text'][:600]}…")
    (out_dir / f"kap_{label}.md").write_text("\n".join(lines), encoding="utf-8")
    return json_path, payload


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", nargs="*", help="one or more BIST codes")
    ap.add_argument("--all", action="store_true", help="market-wide feed")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--from", dest="start", type=date.fromisoformat)
    ap.add_argument("--to", dest="end", type=date.fromisoformat)
    ap.add_argument("--details", type=int, default=0, help="fetch full text for the N most important items")
    ap.add_argument("--important-only", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if not a.ticker and not a.all:
        ap.error("use --ticker CODE ... or --all")
    out = a.out or default_out("kap")
    try:
        path, payload = run(out, a.ticker, a.all, a.days, a.start, a.end, a.details, a.important_only)
    except NetworkError as exc:
        print(f"ERROR: {exc}. Without internet, search 'site:kap.org.tr <KOD>' with web browsing instead.", file=sys.stderr)
        return 3
    print(f"OK {len(payload['items'])} disclosures {payload['window'][0]}..{payload['window'][1]} -> {path}")
    print("counts:", payload["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
