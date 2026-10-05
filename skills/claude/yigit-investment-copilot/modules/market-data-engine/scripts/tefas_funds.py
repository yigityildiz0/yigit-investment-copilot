#!/usr/bin/env python3
"""TEFAS fund data: whole-market screen, single-fund evidence pack and side-by-side comparison.

Source: the public JSON API behind tefas.gov.tr (POST https://www.tefas.gov.tr/api/funds/<endpoint>).
It is official exchange-operator data (TEFAS / Takasbank) but an undocumented interface: field names
can change and the service throttles bursts, so calls are spaced and retried. Fund documents
(izahname, yatırımcı bilgi formu, portföy raporu) remain on KAP; follow `kap_link` for them.

Commands:
  python tefas_funds.py screen --out funds                         # every YAT fund, ranked inside its category
  python tefas_funds.py screen --type EMK --category "hisse" --top 15 --out bes
  python tefas_funds.py fund TTE --period 3y --out tte             # identity, costs, allocation, NAV history, metrics
  python tefas_funds.py compare TTE AFT IPB --period 1y --out cmp  # same-window metrics + return correlations

Rankings are research priority inside a category, never a buy signal; past returns are not forecasts.
"""

import argparse
import math
import sys
import time

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (NetworkError, default_out, get_json, iso, md_table, now_trt, pct_ranks,  # noqa: E402
                    setup_stdout, stdev, tr_float, write_csv, write_json)

API = "https://www.tefas.gov.tr/api/funds/"
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
PERIODS = {"1m": 1, "3m": 3, "6m": 6, "ytd": 0, "1y": 12, "3y": 36, "5y": 60}
RETURN_FIELDS = [("getiri1a", "ret_1m_pct"), ("getiri3a", "ret_3m_pct"), ("getiri6a", "ret_6m_pct"),
                 ("getiriyb", "ret_ytd_pct"), ("getiri1y", "ret_1y_pct"), ("getiri3y", "ret_3y_pct"),
                 ("getiri5y", "ret_5y_pct")]
# Allocation codes whose Turkish labels are verified against TEFAS; any other code is shown raw.
ASSET_LABELS = {
    "hs": "Hisse Senedi", "yhs": "Yabancı Hisse Senedi", "dt": "Devlet Tahvili", "hb": "Hazine Bonosu",
    "fb": "Finansman Bonosu", "ost": "Özel Sektör Tahvili", "vdm": "Varlığa Dayalı Menkul Kıymetler",
    "kba": "Kamu Dış Borçlanma Araçları", "osdb": "Özel Sektör Dış Borçlanma Araçları",
    "kibd": "Döviz Cinsi Kamu İç Borçlanma Araçları", "kkstl": "Kamu Kira Sertifikaları (TL)",
    "osks": "Özel Sektör Kira Sertifikaları", "oksyd": "Özel Sektör Yurt Dışı Kira Sertifikaları",
    "tr": "Ters-Repo", "r": "Repo", "btas": "BİST Taahhütlü İşlem Pazarı Satım", "tpp": "Takasbank Para Piyasası",
    "bpp": "Borsa İstanbul Para Piyasası", "vmtl": "Mevduat (TL)", "vmd": "Mevduat (Döviz)",
    "khtl": "Katılma Hesabı (TL)", "khd": "Katılma Hesabı (Döviz)", "km": "Kıymetli Madenler",
    "kmkba": "Kıymetli Maden Cinsinden Kamu Borçlanma Araçları", "kmkks": "Kıymetli Maden Cinsinden Kamu Kira Sertifikaları",
    "ybyf": "Yabancı Borsa Yatırım Fonları", "ybosb": "Yabancı Özel Sektör Borçlanma Araçları",
    "ybkb": "Yabancı Kamu Borçlanma Araçları", "byf": "Borsa Yatırım Fonları Katılma Payları",
    "yyf": "Yatırım Fonları Katılma Payları", "gykb": "Gayrimenkul Yatırım Fonları Katılma Payları",
    "gsykb": "Girişim Sermayesi Yatırım Fonları Katılma Payları", "vint": "Vadeli İşlemler Nakit Teminatları", "d": "Diğer",
}
_last_call = [0.0]


def tr_lower(text):
    return (text or "").replace("I", "ı").replace("İ", "i").lower()


def call(endpoint, body, spacing=0.8):
    """POST one TEFAS endpoint politely (spaced calls, retries with backoff) and return resultList."""
    wait = spacing - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    try:
        data = get_json(API + endpoint, json_body=body, headers=HEADERS, timeout=45, retries=3, backoff=3.0)
    finally:
        _last_call[0] = time.time()
    if not isinstance(data, dict):
        raise NetworkError(f"TEFAS {endpoint}: unexpected payload")
    if data.get("errorMessage") and not data.get("resultList"):
        raise NetworkError(f"TEFAS {endpoint}: {str(data['errorMessage'])[:120]}")
    return data.get("resultList") or []


def returns_list(fund_type):
    body = {"fonTipi": fund_type, "dil": "TR", "calismaTipi": 2}
    body.update({f"donemGetiri{k}": "1" for k in ("1a", "3a", "6a", "yb", "1y", "3y", "5y")})
    return call("fonGetiriBazliBilgiGetir", body)


_fee_cache = {}


def fee_list(fund_type):
    if fund_type in _fee_cache:
        return _fee_cache[fund_type]
    rows = call("fonYonetimBazliBilgiGetir", {"fonTipi": fund_type, "dil": "TR"})
    out = _fee_cache[fund_type] = {}
    positive = lambda v: v if v is not None and v > 0 else None  # TEFAS publishes "0" for unknown fees
    for r in rows:
        out[r.get("fonKodu")] = {
            "mgmt_fee_applied_pct": positive(tr_float(r.get("uygulananYu1Y"))),
            "mgmt_fee_bylaws_pct": positive(tr_float(r.get("fonIcTuzukYu1G"))),
            "max_total_expense_pct": positive(tr_float(r.get("fonTopGiderKesoran"))),
            "founder_code": r.get("kurucuKod"),
        }
    return out


def cost_of(f):
    """Best available annual cost figure: max total expense, else bylaws fee, else applied fee."""
    for key in ("max_total_expense_pct", "mgmt_fee_bylaws_pct", "mgmt_fee_applied_pct"):
        if f.get(key) is not None:
            return f[key]
    return None


def peer_group(f):
    """Umbrella type + SRI risk band: keeps money-market-like and equity-like funds of one umbrella apart."""
    rv = f.get("risk_value")
    band = "?" if rv is None else "düşük" if rv <= 2 else "orta" if rv <= 4 else "yüksek"
    return f"{f['category']} · risk {band}"


def fund_info(code):
    rows = call("fonBilgiGetir", {"fonKodu": code})
    return rows[0] if rows else None


def fund_profile(code):
    rows = call("fonProfilBilgiGetir", {"fonKodu": code, "dil": "TR"})
    return rows[0] if rows else None


def fund_history(code, period):
    rows = call("fonFiyatBilgiGetir", {"fonKodu": code, "dil": "TR", "periyod": PERIODS[period]})
    series = []
    for r in rows:
        try:
            d, p = date.fromisoformat(str(r.get("tarih"))[:10]), float(r.get("fiyat"))
        except (TypeError, ValueError):
            continue
        if p > 0:
            series.append((d, p))
    series.sort()
    return series


def fund_allocation(code):
    today = datetime.now()
    for fund_type in ("YAT", "EMK", "BYF"):
        body = {"fonTipi": fund_type, "fonKodu": code, "aramaMetni": None, "fonTurKod": None, "fonGrubu": None,
                "sfonTurKod": None, "basTarih": (today - timedelta(days=10)).strftime("%Y%m%d"),
                "bitTarih": today.strftime("%Y%m%d"), "basSira": 1, "bitSira": 500, "fonTurAciklama": None, "dil": "TR",
                "kurucuKod": None, "sFonTurKod": "", "fonKod": code, "fonGrup": "", "fonUnvanTip": ""}
        try:
            rows = call("dagilimSiraliGetirT", body)
        except NetworkError:
            rows = []
        if rows:
            latest = max(rows, key=lambda r: str(r.get("tarih") or ""))
            parts = []
            for key, value in latest.items():
                if key in ("fonKodu", "fonUnvan", "tarih", "bilFiyat") or value in (None, 0, 0.0):
                    continue
                try:
                    weight = float(value)
                except (TypeError, ValueError):
                    continue
                parts.append({"code": key, "asset": ASSET_LABELS.get(key, f"{key} (etiket doğrulanmadı)"), "weight_pct": weight})
            parts.sort(key=lambda p: -abs(p["weight_pct"]))
            return {"date": str(latest.get("tarih"))[:10], "fund_type": fund_type, "parts": parts}
    return None


def inflation():
    """Latest TÜFE from TCMB via macro_snapshot (optional; None when unavailable)."""
    try:
        from macro_snapshot import tcmb_cpi
        return tcmb_cpi()
    except Exception:
        return None


def risk_free(value):
    """Annual risk-free rate as a decimal: the user's value, else today's TCMB policy rate, else 0."""
    if value is not None:
        return value, "kullanıcı girdisi"
    try:
        from macro_snapshot import tcmb_policy
        policy = tcmb_policy()
        return policy["policy_rate_pct"] / 100, f"güncel politika faizi ({policy['policy_rate_since']}'den beri; dönem ortalaması değil)"
    except Exception:
        return 0.0, "0 (politika faizi alınamadı)"


def metrics(series, rf_annual=0.0):
    """Return/risk metrics on a dated NAV series (calendar-day annualisation, 252 trading days for vol)."""
    if len(series) < 3:
        return {}
    rets = [series[i][1] / series[i - 1][1] - 1 for i in range(1, len(series))]
    days = (series[-1][0] - series[0][0]).days or 1
    total = series[-1][1] / series[0][1] - 1
    ann = (1 + total) ** (365 / days) - 1 if total > -1 else None
    sd = stdev(rets)
    vol = sd * math.sqrt(252) if sd else None
    rf_d = (1 + rf_annual) ** (1 / 252) - 1
    ex = [r - rf_d for r in rets]
    mean_ex = sum(ex) / len(ex)
    sharpe = mean_ex / sd * math.sqrt(252) if sd else None
    down = math.sqrt(sum(min(0.0, r) ** 2 for r in ex) / len(ex))
    sortino = mean_ex / down * math.sqrt(252) if down else None
    peak, peak_d, mdd, trough_d, mdd_peak_d = series[0][1], series[0][0], 0.0, series[0][0], series[0][0]
    for d, v in series:
        if v > peak:
            peak, peak_d = v, d
        dd = v / peak - 1
        if dd < mdd:
            mdd, trough_d, mdd_peak_d = dd, d, peak_d
    peak_value = dict(series)[mdd_peak_d]
    recovery = next((d for d, v in series if d > trough_d and v >= peak_value), None)
    years = {}
    for d, v in series:
        years.setdefault(d.year, []).append((d, v))
    by_year = {}
    prev_last = None
    for y in sorted(years):
        base = prev_last if prev_last else years[y][0][1]
        label = str(y)
        if prev_last is None and years[y][0][0] > date(y, 1, 10):
            label += " (kısmi)"
        elif years[y][-1][0] < date(y, 12, 20):
            label += " (YBB)"
        by_year[label] = (years[y][-1][1] / base - 1) * 100
        prev_last = years[y][-1][1]
    worst_20 = min((series[i][1] / series[i - 20][1] - 1 for i in range(20, len(series))), default=None)
    return {"start": series[0][0].isoformat(), "end": series[-1][0].isoformat(), "observations": len(series),
            "total_return_pct": total * 100, "annualized_return_pct": ann * 100 if ann is not None else None,
            "annualized_vol_pct": vol * 100 if vol else None, "sharpe": sharpe, "sortino": sortino,
            "max_drawdown_pct": mdd * 100, "drawdown_peak": mdd_peak_d.isoformat(), "drawdown_trough": trough_d.isoformat(),
            "recovered_on": recovery.isoformat() if recovery else None, "worst_20d_pct": worst_20 * 100 if worst_20 is not None else None,
            "calendar_returns_pct": by_year, "rf_annual_used": rf_annual}



def real_return(nominal_pct, cpi_pct):
    if nominal_pct is None or cpi_pct is None:
        return None
    return ((1 + nominal_pct / 100) / (1 + cpi_pct / 100) - 1) * 100


# --------------------------------------------------------------------------------------------- screen
def cmd_screen(a):
    fund_type = a.type.upper()
    rows = returns_list(fund_type)
    fees = fee_list(fund_type) if fund_type in ("YAT", "EMK") else {}
    cpi = inflation()
    funds = []
    for r in rows:
        code = r.get("fonKodu")
        f = {"code": code, "name": r.get("fonUnvan"), "category": r.get("fonTurAciklama") or "?",
             "on_tefas": r.get("tefasDurum"), "risk_value": tr_float(r.get("riskDegeri"))}
        for src, dst in RETURN_FIELDS:
            f[dst] = tr_float(r.get(src)) if not isinstance(r.get(src), (int, float)) else float(r[src])
        f.update(fees.get(code, {}))
        funds.append(f)
    if a.category:
        needle = tr_lower(a.category)
        funds = [f for f in funds if needle in tr_lower(f["category"]) or needle in tr_lower(f["name"])]
    if a.tefas_only:
        funds = [f for f in funds if f["on_tefas"] is not False]
    total = len(funds)
    # rank inside each peer group: consistency across horizons, not the single best trailing number.
    # A missing horizon counts slightly below neutral (unknown track record is a risk, not a strength).
    horizons = ["ret_3m_pct", "ret_6m_pct", "ret_1y_pct", "ret_3y_pct", "ret_5y_pct"]
    groups = {}
    for i, f in enumerate(funds):
        f["peer_group"] = peer_group(f)
        groups.setdefault(f["peer_group"], []).append(i)
    for idx in groups.values():
        members = [funds[i] for i in idx]
        per_h = {h: pct_ranks([m.get(h) for m in members]) for h in horizons}
        cost = pct_ranks([cost_of(m) for m in members], higher_is_better=False)
        for j, m in enumerate(members):
            vals = [per_h[h][j] for h in horizons]
            m["peer_count"] = len(members)
            m["horizons_ranked"] = sum(1 for v in vals if v is not None)
            m["consistency"] = (sum(v if v is not None else a.missing_score for v in vals) / len(vals)
                                if m["horizons_ranked"] else None)
            m["cost_pct"] = cost_of(m)
            m["cost_rank"] = cost[j]
            m["score"] = (0.8 * m["consistency"] + 0.2 * (cost[j] if cost[j] is not None else a.missing_score)
                          if m["consistency"] is not None else None)
            flags = []
            if m.get("ret_1y_pct") is None:
                flags.append("GECMIS_1Y_YOK")
            if m["on_tefas"] is False:
                flags.append("TEFAS_DISI")
            if "serbest" in tr_lower(m["category"]) or "serbest" in tr_lower(m["name"]):
                flags.append("NITELIKLI_YATIRIMCI")
            if m["peer_count"] < 5:
                flags.append("AZ_EMSAL")
            if m["cost_pct"] is None:
                flags.append("GIDER_BILINMIYOR")
            if cpi and m.get("ret_1y_pct") is not None:
                m["real_1y_pct"] = real_return(m["ret_1y_pct"], cpi.get("cpi_yoy_pct"))
                if m["real_1y_pct"] is not None and m["real_1y_pct"] < 0:
                    flags.append("REEL_KAYIP_1Y")
            m["flags"] = flags
    funds.sort(key=lambda f: (f["score"] is None, -(f["score"] or 0)))
    out = a.out or default_out("tefas-screen")
    out.mkdir(parents=True, exist_ok=True)
    cols = ["code", "name", "category", "peer_group", "score", "consistency", "cost_rank", "horizons_ranked", "peer_count", "flags",
            "ret_1m_pct", "ret_3m_pct", "ret_6m_pct", "ret_ytd_pct", "ret_1y_pct", "ret_3y_pct", "ret_5y_pct", "real_1y_pct",
            "risk_value", "cost_pct", "mgmt_fee_applied_pct", "mgmt_fee_bylaws_pct", "max_total_expense_pct", "founder_code", "on_tefas"]
    write_csv(out / "funds_screen.csv", funds, cols)
    # leaders: retail-buyable funds with at least a one-year record; young funds go to a watch list
    qualified_ok = a.include_qualified or (a.category and "serbest" in tr_lower(a.category))
    leaders, young = [], []
    for grp, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        pool = [f for f in funds if f["peer_group"] == grp and f["score"] is not None
                and (qualified_ok or "NITELIKLI_YATIRIMCI" not in f["flags"])]
        leaders.extend([f for f in pool if "GECMIS_1Y_YOK" not in f["flags"]][: a.per_category])
        young.extend([f for f in pool if "GECMIS_1Y_YOK" in f["flags"]][:1])
    leaders = leaders[: a.top]
    if a.enrich:
        for f in leaders + young:
            try:
                info = fund_info(f["code"]) or {}
            except NetworkError:
                info = {}
            f["aum_try"] = info.get("portBuyukluk")
            f["investors"] = info.get("yatirimciSayi")
            if f["aum_try"] is not None and f["aum_try"] < a.min_aum:
                f["flags"].append("KUCUK_FON")
    meta = {"fetched_at": iso(now_trt()), "source": "tefas.gov.tr JSON API (official operator data, undocumented interface)",
            "fund_type": fund_type, "category_filter": a.category, "tefas_only": a.tefas_only, "funds": total,
            "peer_groups": {k: len(v) for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))},
            "cpi": cpi, "method": ("peer group = umbrella type + SRI risk band; score = 0.8 x mean percentile of 3m/6m/1y/3y/5y "
                                   f"returns (missing horizon = {a.missing_score}) + 0.2 x low-cost percentile; leaders need a 1-year record "
                                   "and exclude qualified-investor (serbest) funds unless asked")}
    write_json(out / "funds_screen.meta.json", meta)

    def view_of(items):
        return [{"Kod": f["code"], "Fon": (f["name"] or "")[:46], "Emsal grubu": f["peer_group"][:34], "Skor": f.get("score"),
                 "1Y%": f.get("ret_1y_pct"), "3Y%": f.get("ret_3y_pct"), "Reel1Y%": f.get("real_1y_pct"),
                 "Gider%": f.get("cost_pct"), "Risk": f.get("risk_value"),
                 "Büyüklük(mn)": (f["aum_try"] / 1e6) if f.get("aum_try") else None, "Yatırımcı": f.get("investors"),
                 "Bayrak": ",".join(f.get("flags") or [])} for f in items]
    view, young_view = view_of(leaders), view_of(young)
    lines = [f"# TEFAS fon taraması — {fund_type}{' · ' + a.category if a.category else ''}", "",
             f"- Veri: {meta['fetched_at']} · kaynak: TEFAS (resmi işletmeci verisi; belgelenmemiş arayüz) · {total} fon, {len(groups)} emsal grubu",
             "- Yöntem: emsal grubu = şemsiye tür + risk bandı (1–2 düşük, 3–4 orta, 5–7 yüksek). Grup içinde 3A/6A/1Y/3Y/5Y getiri yüzdeliklerinin ortalaması (%80; "
             f"eksik dönem {a.missing_score}) + düşük gider yüzdeliği (%20). Tek dönem şampiyonluğu değil, tutarlılık.",
             (f"- Enflasyon: TÜFE yıllık %{cpi['cpi_yoy_pct']:.2f} ({cpi['period']}) · reel getiri = (1+nominal)/(1+TÜFE)−1" if cpi else "- Enflasyon verisi alınamadı: reel getiri hesaplanmadı."),
             "- Liderler en az 1 yıllık geçmişi olan fonlardır; serbest (nitelikli yatırımcı) fonlar " + ("dahil." if qualified_ok else "hariç (`--include-qualified` ile eklenir)."),
             "", "> Liste **ADAY**dır; geçmiş getiri gelecek getiri değildir. Seçmeden önce `fund KOD` ile izahname, gider, dağılım ve düşüş geçmişine bak.",
             "", f"## Emsal grubu liderleri (grup başına en çok {a.per_category}, toplam {len(leaders)})", "",
             md_table(view, list(view[0].keys())) if view else "(sonuç yok)", ""]
    if young_view:
        lines += ["## Yeni fonlar (1 yıldan kısa geçmiş — yalnız izleme)", "", md_table(young_view, list(young_view[0].keys())), ""]
    lines += ["## Emsal grupları", "", ", ".join(f"{k} ({v})" for k, v in list(meta["peer_groups"].items())[:30]), "",
              "Bayraklar: GECMIS_1Y_YOK (1 yıldan kısa geçmiş), TEFAS_DISI (TEFAS'ta işlem görmüyor), NITELIKLI_YATIRIMCI (serbest fon: yalnız nitelikli yatırımcı), "
              "AZ_EMSAL (<5 emsal), GIDER_BILINMIYOR (TEFAS gider oranı yayınlamamış; KAP'tan bak), REEL_KAYIP_1Y (1 yılda enflasyonun altında), KUCUK_FON (büyüklük tabanın altında).",
              "", "Dosyalar: funds_screen.csv (tüm fonlar), funds_screen.meta.json."]
    (out / "funds_screen.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {total} funds ({fund_type}), {len(groups)} peer groups -> {out}")
    for f in leaders[:12]:
        print(f"  {f['code']:>4} {f['peer_group'][:36]:<36} score {f['score']:.3f} 1y {f.get('ret_1y_pct')} flags {','.join(f['flags'])}")
    return 0


# --------------------------------------------------------------------------------------------- fund
def pack(code, period, cpi, rf):
    info = fund_info(code)
    if not info:
        raise NetworkError(f"TEFAS has no fund with code {code}")
    profile = fund_profile(code) or {}
    series = fund_history(code, period)
    alloc = fund_allocation(code)
    fees = {}
    for fund_type in ("YAT", "EMK"):
        table = fee_list(fund_type)
        if code in table:
            fees = table[code]
            break
    m = metrics(series, rf)
    if cpi and m.get("annualized_return_pct") is not None:
        m["real_annualized_vs_latest_cpi_pct"] = real_return(m["annualized_return_pct"], cpi.get("cpi_yoy_pct"))
    return {"code": code, "name": info.get("fonUnvan"), "category": info.get("fonKategori"),
            "price": info.get("sonFiyat"), "daily_return_pct": info.get("gunlukGetiri"), "aum_try": info.get("portBuyukluk"),
            "units": info.get("payAdet"), "investors": info.get("yatirimciSayi"), "market_share_pct": info.get("pazarPayi"),
            "category_rank": info.get("kategoriDerece"), "category_size": info.get("kategoriFonSay"),
            "isin": profile.get("isinKodu"), "tefas_status": profile.get("tefasDurum"), "risk_value": profile.get("riskDegeri"),
            "order_window": f"{profile.get('basIsSaat') or '?'}–{profile.get('sonIsSaat') or '?'}",
            "buy_settlement_days": profile.get("fonSatisValor"), "sell_settlement_days": profile.get("fonGeriAlisValor"),
            "min_buy": profile.get("minAlis"), "min_sell": profile.get("minSatis"),
            "entry_fee": profile.get("girisKomisyonu"), "exit_fee": profile.get("cikisKomisyonu"),
            "kap_link": profile.get("kapLink"), "fees": fees, "allocation": alloc, "metrics": m, "series": series}


def fund_md(p, cpi):
    m, f, al = p["metrics"], p["fees"], p["allocation"]
    fmt = lambda x, d=2: "—" if x is None else (f"{x:,.{d}f}" if isinstance(x, (int, float)) else str(x))
    lines = [f"## {p['code']} — {p['name']}", "",
             f"- Kategori: {p['category']} · kategori sırası {p['category_rank']}/{p['category_size']} (TEFAS'ın günlük sıralaması) · risk değeri {p['risk_value']} (1–7)",
             f"- Fiyat {fmt(p['price'], 6)} · büyüklük {fmt((p['aum_try'] or 0) / 1e6, 1)} mn TL · yatırımcı {fmt(p['investors'], 0)} · pazar payı %{fmt(p['market_share_pct'])}",
             f"- İşlem: {p['tefas_status']} · emir saatleri {p['order_window']} · alış valörü T+{p['buy_settlement_days']} · satış valörü T+{p['sell_settlement_days']} · ISIN {p['isin']}",
             f"- Maliyet: uygulanan yönetim ücreti %{fmt(f.get('mgmt_fee_applied_pct'))} · iç tüzük %{fmt(f.get('mgmt_fee_bylaws_pct'))} · azami toplam gider %{fmt(f.get('max_total_expense_pct'))} (yıllık)"
             + (f" · giriş/çıkış komisyonu {p['entry_fee']}/{p['exit_fee']}" if p['entry_fee'] or p['exit_fee'] else ""),
             f"- Belgeler (izahname, yatırımcı bilgi formu, aylık portföy raporu): {p['kap_link'] or 'KAP fon sayfası'}"]
    if m:
        lines.append(f"- Performans {m['start']} → {m['end']} ({m['observations']} gözlem): toplam %{fmt(m['total_return_pct'], 1)} · yıllık %{fmt(m['annualized_return_pct'], 1)}"
                     + (f" · son TÜFE'ye göre reel yıllık %{fmt(m.get('real_annualized_vs_latest_cpi_pct'), 1)}" if m.get("real_annualized_vs_latest_cpi_pct") is not None else ""))
        lines.append(f"- Risk: yıllık oynaklık %{fmt(m['annualized_vol_pct'], 1)} · en büyük düşüş %{fmt(m['max_drawdown_pct'], 1)} ({m['drawdown_peak']} → {m['drawdown_trough']}, toparlanma: {m['recovered_on'] or 'henüz yok'}) · en kötü 20 gün %{fmt(m['worst_20d_pct'], 1)}")
        lines.append(f"- Sharpe {fmt(m['sharpe'])} · Sortino {fmt(m['sortino'])} (risksiz oran %{fmt(m['rf_annual_used'] * 100, 1)}: {p.get('rf_label', '')}) · takvim yılı getirileri: "
                     + ", ".join(f"{y} %{v:.1f}" for y, v in m["calendar_returns_pct"].items()))
    if al:
        lines.append(f"- Varlık dağılımı ({al['date']}): " + ", ".join(f"{x['asset']} %{x['weight_pct']:.1f}" for x in al["parts"][:8]))
    return "\n".join(lines) + "\n"


def cmd_fund(a):
    cpi = inflation()
    rf, rf_label = risk_free(a.rf)
    p = pack(a.code.upper(), a.period, cpi, rf)
    p["rf_label"] = rf_label
    out = a.out or default_out(f"tefas-{p['code']}")
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / f"{p['code']}_nav.csv", [{"date": d.isoformat(), "value": v} for d, v in p["series"]], ["date", "value"])
    body = {k: v for k, v in p.items() if k != "series"}
    body.update({"fetched_at": iso(now_trt()), "period": a.period, "cpi": cpi,
                 "source": "tefas.gov.tr JSON API; documents on KAP (kap_link)"})
    write_json(out / f"{p['code']}_fund.json", body)
    md = [f"# Fon kanıt paketi — {p['code']} ({a.period})", "", fund_md(p, cpi),
          "Sonraki adım: fund-etf-analyst modülü — izahname/portföy raporu, emsal ve benchmark karşılaştırması, portföydeki çakışma, rol ve dağılım aralığı.",
          f"Derin metrikler (benchmark, takip hatası, yakalama oranları): `python ../fund-etf-analyst/scripts/fund_metrics.py {p['code']}_nav.csv` (dosya yolu çıktı klasörüne göre)."]
    (out / f"{p['code']}_fund.md").write_text("\n".join(md), encoding="utf-8")
    m = p["metrics"]
    print(f"OK {p['code']} {p['category']} price {p['price']} aum {((p['aum_try'] or 0) / 1e6):.0f}mn -> {out}")
    if m:
        print(f"  {a.period}: total {m['total_return_pct']:.1f}% ann {m['annualized_return_pct']:.1f}% vol {m['annualized_vol_pct'] or 0:.1f}% maxDD {m['max_drawdown_pct']:.1f}%")
    return 0


def cmd_compare(a):
    cpi = inflation()
    rf, rf_label = risk_free(a.rf)
    packs = [pack(code.upper(), a.period, cpi, rf) for code in a.codes]
    for p in packs:
        p["rf_label"] = rf_label
    common = set.intersection(*[set(d for d, _ in p["series"]) for p in packs]) if packs else set()
    dates = sorted(common)
    rows, series_aligned = [], {}
    for p in packs:
        s = dict(p["series"])
        aligned = [(d, s[d]) for d in dates]
        series_aligned[p["code"]] = aligned
        m = metrics(aligned, rf)
        rows.append({"Kod": p["code"], "Kategori": (p["category"] or "")[:24], "Toplam%": m.get("total_return_pct"),
                     "Yıllık%": m.get("annualized_return_pct"), "Reel yıllık%": real_return(m.get("annualized_return_pct"), (cpi or {}).get("cpi_yoy_pct")),
                     "Oynaklık%": m.get("annualized_vol_pct"), "MaxDD%": m.get("max_drawdown_pct"), "Sharpe": m.get("sharpe"),
                     "Gider%": p["fees"].get("max_total_expense_pct"), "Büyüklük(mn)": (p["aum_try"] or 0) / 1e6, "Risk": p["risk_value"]})
    corr_lines = []
    rets = {c: [s[i][1] / s[i - 1][1] - 1 for i in range(1, len(s))] for c, s in series_aligned.items()}
    codes = list(rets)
    for i, c1 in enumerate(codes):
        for c2 in codes[i + 1:]:
            x, y = rets[c1], rets[c2]
            if len(x) > 20:
                mx, my = sum(x) / len(x), sum(y) / len(y)
                cov = sum((u - mx) * (v - my) for u, v in zip(x, y))
                vx, vy = math.sqrt(sum((u - mx) ** 2 for u in x)), math.sqrt(sum((v - my) ** 2 for v in y))
                if vx and vy:
                    corr_lines.append(f"- {c1} ↔ {c2}: günlük getiri korelasyonu {cov / (vx * vy):.2f}")
    out = a.out or default_out("tefas-compare")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "compare.json", {"fetched_at": iso(now_trt()), "period": a.period, "common_dates": len(dates),
                                       "funds": [{k: v for k, v in p.items() if k != "series"} for p in packs], "table": rows})
    lines = [f"# Fon karşılaştırması — {', '.join(p['code'] for p in packs)} ({a.period}, ortak {len(dates)} gün)", "",
             md_table(rows, list(rows[0].keys())) if rows else "", "", "## Korelasyon (çakışma kontrolü)", "",
             *(corr_lines or ["- yeterli ortak gözlem yok"]), "", "## Fon ayrıntıları", ""] + [fund_md(p, cpi) for p in packs] + [
             "> Aynı kategori, para birimi ve vade üzerinde, gider sonrası karşılaştır. Korelasyonu 0,9 üstü fonlar portföyde aynı riski iki kez taşır."]
    (out / "compare.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK compared {len(packs)} funds on {len(dates)} common dates -> {out}")
    for r in rows:
        print(f"  {r['Kod']}: ann {r['Yıllık%'] or 0:.1f}% vol {r['Oynaklık%'] or 0:.1f}% maxDD {r['MaxDD%'] or 0:.1f}%")
    return 0


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="rank every fund inside its category")
    s.add_argument("--type", default="YAT", help="YAT (yatırım fonları), EMK (BES emeklilik), BYF (borsa yatırım fonları)")
    s.add_argument("--category", help="substring of the category or fund name, e.g. 'hisse', 'para piyasası', 'altın'")
    s.add_argument("--tefas-only", action="store_true", help="drop funds not traded on TEFAS")
    s.add_argument("--include-qualified", action="store_true", help="let serbest (qualified-investor) funds lead")
    s.add_argument("--missing-score", type=float, default=0.45, help="percentile used for a missing return horizon or cost")
    s.add_argument("--per-category", type=int, default=3, help="leaders per peer group")
    s.add_argument("--top", type=int, default=40)
    s.add_argument("--enrich", action=argparse.BooleanOptionalAction, default=True, help="fetch size/investors for leaders")
    s.add_argument("--min-aum", type=float, default=100_000_000, help="flag funds smaller than this (TL)")
    s.add_argument("--out", type=Path)
    f = sub.add_parser("fund", help="single-fund evidence pack")
    f.add_argument("code")
    f.add_argument("--period", default="3y", choices=sorted(PERIODS))
    f.add_argument("--rf", type=float, help="annual risk-free rate as a decimal for Sharpe (default: today's TCMB policy rate)")
    f.add_argument("--out", type=Path)
    c = sub.add_parser("compare", help="side-by-side comparison on common dates")
    c.add_argument("codes", nargs="+")
    c.add_argument("--period", default="1y", choices=sorted(PERIODS))
    c.add_argument("--rf", type=float, help="annual risk-free decimal (default: today's TCMB policy rate)")
    c.add_argument("--out", type=Path)
    a = ap.parse_args()
    try:
        return {"screen": cmd_screen, "fund": cmd_fund, "compare": cmd_compare}[a.cmd](a)
    except NetworkError as exc:
        print(f"ERROR: {exc}. TEFAS may be throttling or unreachable; wait a minute or use the tefas.gov.tr pages.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
