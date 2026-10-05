#!/usr/bin/env python3
"""Watchlist and open-position monitor: checks every name against its written plan and flags what
needs attention today (research tool; never places orders).

Input CSV (UTF-8; only `code` is required):
  code,entry,stop,target1,target2,quantity,review_date,thesis
  THYAO,300,272,345,380,200,2026-10-15,Yolcu büyümesi + kur
  ASELS,,,,,,,izleme: ihracat siparişleri

It pulls a fresh delayed snapshot for the codes (TradingView screener) and, with --kap-days, their
recent KAP disclosures, then evaluates: stop breached/near, targets hit, R-multiple, break-even
trigger (+1R), trend damage (close below SMA50/SMA200), sharp daily move, earnings or ex-dividend
soon, review date passed, fresh important KAP news. Output: watch_report.md / .json sorted by urgency.

Usage:
  python watchlist_monitor.py --watchlist watch.csv --kap-days 3 --out watch
  python watchlist_monitor.py --watchlist watch.csv --snapshot snap/snapshot.csv --out watch   # offline
"""

import argparse
import csv
import json
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import date
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "market-data-engine" / "scripts"
sys.path.insert(0, str(ENGINE))
from common import NetworkError, fnum, iso, md_table, now_trt, read_csv, setup_stdout, write_json  # noqa: E402

URGENCY = {"STOP_ALTINDA": 100, "KAP_NEGATIF": 90, "STOPA_YAKIN": 80, "SERT_DUSUS": 70, "HEDEF2": 60, "HEDEF1": 55,
           "BILANCO_YAKIN": 50, "BASABAS_TASI": 45, "SMA200_ALTINDA": 40, "GOZDEN_GECIR": 35, "KAP_ONEMLI": 33,
           "TEMETTU_YAKIN": 30, "SMA50_ALTINDA": 25, "SERT_YUKSELIS": 20}
ACTION = {"STOP_ALTINDA": "Plan gereği çıkışı değerlendir (stop kırıldı)",
          "KAP_NEGATIF": "Olumsuz olabilecek KAP bildirimi: oku; tez bozulduysa fiyat beklemeden çık",
          "STOPA_YAKIN": "Stop emrini ve boyutu kontrol et; stopu genişletme",
          "SERT_DUSUS": "Nedenini bul (KAP/haber/piyasa); plan dışı panik satış yok",
          "HEDEF2": "Planlanan kısmi kâr al / izleyen stopa geç",
          "HEDEF1": "Planlanan ilk kısmi kâr (≈⅓) ve stopu başabaşa çek",
          "BILANCO_YAKIN": "Boşluk (gap) riskine göre tutulacak boyutu seç",
          "BASABAS_TASI": "+1R üstünde kapanış: stopu giriş fiyatına taşı",
          "SMA200_ALTINDA": "Uzun vadeli trend bozuldu; tezi yeniden sına",
          "GOZDEN_GECIR": "İnceleme tarihi geçti: tezi, değerlemeyi ve planı güncelle",
          "KAP_ONEMLI": "Yeni önemli KAP bildirimi: etkisini tez defterine yaz",
          "TEMETTU_YAKIN": "Hak kullanımında fiyat temettü kadar düşer; stop seviyesini buna göre değerlendir",
          "SMA50_ALTINDA": "Orta vadeli trend zayıf; izleyen stop kuralını uygula",
          "SERT_YUKSELIS": "Sert yükseliş: kovalamadan planlı kâr alma/izleyen stop"}
NEGATIVE_KAP = {"DISTRESS", "LEGAL", "SPK_TRADING_BAN", "VBTS_MEASURE", "RIGHTS_ISSUE", "SUPPLY_OVERHANG"}


def load_watchlist(path):
    items = []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            code = (r.get("code") or r.get("kod") or "").strip().upper()
            if not code:
                continue
            items.append({"code": code, "entry": fnum(r.get("entry")), "stop": fnum(r.get("stop")),
                          "target1": fnum(r.get("target1")), "target2": fnum(r.get("target2")),
                          "quantity": fnum(r.get("quantity")), "review_date": (r.get("review_date") or "").strip() or None,
                          "thesis": (r.get("thesis") or "").strip()})
    return items


def days_until(text, today):
    try:
        return (date.fromisoformat(str(text)[:10]) - today).days
    except (TypeError, ValueError):
        return None


def evaluate(item, row, kap_items, today):
    c = fnum(row.get("close")) if row else None
    alerts, info = [], {}
    if c is None:
        return ["VERI_YOK"], {"note": "fiyat alınamadı"}
    e, s = item["entry"], item["stop"]
    info["close"] = c
    info["change_pct"] = fnum(row.get("change_pct"))
    if e:
        info["move_since_entry_pct"] = (c / e - 1) * 100
    if e and s and e > s:
        r = (c - e) / (e - s)
        info["r_multiple"] = r
        if r >= 1 and s < e:
            alerts.append("BASABAS_TASI")
    if s:
        if c <= s:
            alerts.append("STOP_ALTINDA")
        elif c <= s * 1.03:
            alerts.append("STOPA_YAKIN")
        info["dist_to_stop_pct"] = (c / s - 1) * 100
    if item["target2"] and c >= item["target2"]:
        alerts.append("HEDEF2")
    elif item["target1"] and c >= item["target1"]:
        alerts.append("HEDEF1")
    ch = info["change_pct"]
    if ch is not None and ch <= -5:
        alerts.append("SERT_DUSUS")
    if ch is not None and ch >= 7:
        alerts.append("SERT_YUKSELIS")
    s50, s200 = fnum(row.get("sma50")), fnum(row.get("sma200"))
    if s200 and c < s200:
        alerts.append("SMA200_ALTINDA")
    elif s50 and c < s50:
        alerts.append("SMA50_ALTINDA")
    dte = days_until(row.get("earnings_next"), today)
    if dte is not None and 0 <= dte <= 7:
        alerts.append("BILANCO_YAKIN")
        info["days_to_earnings"] = dte
    dx = days_until(row.get("exdiv_next"), today)
    if dx is not None and 0 <= dx <= 10:
        alerts.append("TEMETTU_YAKIN")
        info["days_to_exdiv"] = dx
    rd = days_until(item["review_date"], today)
    if rd is not None and rd <= 0:
        alerts.append("GOZDEN_GECIR")
    important = [k for k in kap_items if k.get("importance") == "HIGH" or k.get("event_class") in NEGATIVE_KAP]
    if any(k.get("event_class") in NEGATIVE_KAP for k in important):
        alerts.append("KAP_NEGATIF")
    elif important:
        alerts.append("KAP_ONEMLI")
    info["kap"] = [f"{k.get('published', '')[:10]} {k.get('event_class')}: {(k.get('summary') or k.get('subject') or '')[:90]}"
                   for k in important[:3]]
    return alerts, info


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watchlist", type=Path, required=True)
    ap.add_argument("--snapshot", type=Path, help="use an existing snapshot.csv instead of fetching")
    ap.add_argument("--kap-days", type=int, default=0, help="also scan the last N days of KAP for these codes")
    ap.add_argument("--market", default="turkey")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    items = load_watchlist(a.watchlist)
    if not items:
        raise SystemExit("watchlist is empty")
    codes = [i["code"] for i in items]
    notes = []
    if a.snapshot and a.snapshot.exists():
        snap = {r["ticker"]: r for r in read_csv(a.snapshot)}
        source = f"snapshot file {a.snapshot.name}"
    else:
        from bist_snapshot import fetch_snapshot
        try:
            rows, _, _ = fetch_snapshot(tickers=codes, market=a.market)
            snap = {r["ticker"]: r for r in rows}
            source = "TradingView screener (delayed ~15 min)"
        except NetworkError as exc:
            snap, source = {}, "unavailable"
            notes.append(f"Fiyat alınamadı: {exc}")
    kap = {}
    if a.kap_days and a.market == "turkey":
        try:
            import kap_feed
            _, payload = kap_feed.run(a.out / "kap", tickers=codes, days=a.kap_days, important_only=True)
            for item in payload.get("items", []):
                for t in item.get("tickers", []):
                    kap.setdefault(t, []).append(item)
        except Exception as exc:  # KAP is optional context; never block the price checks
            notes.append(f"KAP alınamadı: {type(exc).__name__}: {exc}")
    today = now_trt().date()
    results = []
    for item in items:
        alerts, info = evaluate(item, snap.get(item["code"]), kap.get(item["code"], []), today)
        alerts.sort(key=lambda x: -URGENCY.get(x, 0))
        results.append({**item, **info, "alerts": alerts, "urgency": max([URGENCY.get(x, 0) for x in alerts] or [0]),
                        "actions": [ACTION[x] for x in alerts if x in ACTION]})
    results.sort(key=lambda r: -r["urgency"])
    a.out.mkdir(parents=True, exist_ok=True)
    write_json(a.out / "watch_report.json", {"checked_at": iso(now_trt()), "source": source, "notes": notes, "items": results})
    view = [{"Kod": r["code"], "Fiyat": r.get("close"), "Gün%": r.get("change_pct"), "Girişten%": r.get("move_since_entry_pct"),
             "R": r.get("r_multiple"), "Stopa%": r.get("dist_to_stop_pct"), "Uyarılar": ",".join(r["alerts"]) or "—"} for r in results]
    lines = [f"# İzleme listesi — {iso(now_trt())}", "", f"- Kaynak: {source}" + (f" · KAP son {a.kap_days} gün" if a.kap_days else ""), *[f"- {n}" for n in notes], "",
             md_table(view, list(view[0].keys())), "", "## Yapılacaklar (planına göre; emir değildir)", ""]
    for r in results:
        if r["actions"]:
            lines.append(f"- **{r['code']}**: " + " · ".join(r["actions"]))
            for k in r.get("kap", []):
                lines.append(f"  - KAP: {k}")
    if not any(r["actions"] for r in results):
        lines.append("- Bugün plan tetikleyicisi yok. \"Haber yok\" da geçerli bir sonuçtur: plan dışı işlem yapma.")
    lines += ["", "Uyarılar kullanıcının kendi yazılı planına göre üretilir; stop/hedef yoksa yalnız trend, olay ve KAP kontrolleri yapılır. "
              "Çıkışlar exit-playbook sırasıyla değerlendirilir: tez → stop → rejim → zaman → hedef/değerleme → daha iyi fırsat."]
    (a.out / "watch_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {len(results)} names, {sum(1 for r in results if r['alerts'])} with alerts -> {a.out}")
    for r in results[:10]:
        print(f"  {r['code']:<6} {r.get('close')}  {','.join(r['alerts']) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
