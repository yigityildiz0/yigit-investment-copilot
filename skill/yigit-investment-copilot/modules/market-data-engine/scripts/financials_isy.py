#!/usr/bin/env python3
"""Quarterly financial statements and derived metrics for a BIST company.

Source: İş Yatırım's public MaliTablo JSON endpoint (the data behind its company pages). It is a
secondary source compiled from KAP filings; confirm decisive figures in the KAP filing itself.

Notes that matter for Turkish statements:
- Income-statement and cash-flow lines are cumulative year-to-date (3, 6, 9, 12 months). This
  script derives discrete quarters and TTM sums from them.
- Under TMS 29 (inflation accounting), each report restates prior periods into the purchasing
  power of its own balance-sheet date. Columns taken from different reports are therefore in
  different money units; nominal YoY growth across them is only approximate.
- Banks (UFRS/UFRS_K groups) use a different chart of accounts and are not TMS 29 restated.

Usage:
  python financials_isy.py THYAO --quarters 8 --out fin
  python financials_isy.py GARAN --group UFRS_K --out fin
"""

import argparse
import sys

sys.dont_write_bytecode = True  # keep installed skill folders clean
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NetworkError, default_out, fnum, get_json, iso, md_table, now_trt, setup_stdout, write_csv, write_json  # noqa: E402

ENDPOINT = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
INDUSTRIAL = {  # XI_29 item codes
    "revenue": "3C", "gross_profit": "3D", "operating_profit": "3DF", "net_income": "3Z", "pretax": "3I",
    "da": "4B", "cfo": "4C", "capex": "4CAI", "fcf": "4CB", "dividends_paid": "4CBB",
    "total_assets": "1BL", "equity_parent": "2O", "equity_total": "2N", "cash": "1AA", "st_investments": "1AB",
    "st_fin_debt": "2AA", "lt_fin_debt": "2BA", "inventories": "1AF", "receivables": "1AC",
    "net_fx_position": "4BE", "export_sales": "4BD", "domestic_sales": "4BC", "paid_in_capital": "2OA",
}
BANK = {  # UFRS / UFRS_K item codes
    "net_interest_income": "3C", "net_fees": "3CA", "provisions": "3CF", "operating_profit": "3CH",
    "net_income": "3ZA", "net_income_total": "3Z", "total_assets": "1Z", "loans": "1AF", "deposits": "2A",
    "equity_total": "2O",
}
FLOW_KEYS = {"revenue", "gross_profit", "operating_profit", "net_income", "pretax", "da", "cfo", "capex", "fcf",
             "dividends_paid", "export_sales", "domestic_sales", "net_interest_income", "net_fees", "provisions",
             "net_income_total"}


def quarter_ends(today, count):
    year, month = today.year, ((today.month - 1) // 3) * 3  # last completed quarter-end month
    if month == 0:
        year, month = year - 1, 12
    out = []
    while len(out) < count:
        out.append((year, month))
        month -= 3
        if month == 0:
            year, month = year - 1, 12
    return out


def fetch(code, group, periods):
    query = "&".join(f"year{i + 1}={y}&period{i + 1}={m}" for i, (y, m) in enumerate(periods))
    data = get_json(f"{ENDPOINT}?companyCode={code}&exchange=TRY&financialGroup={group}&{query}", timeout=30)
    if not isinstance(data, dict) or not data.get("ok"):
        raise NetworkError(f"İş Yatırım MaliTablo error for {code}/{group}: {data.get('errorDescription') if isinstance(data, dict) else data}")
    return data.get("value") or []


def load(code, group, quarters):
    wanted = quarters + 4  # one extra year so the oldest quarters can be de-cumulated and TTM compared
    periods = quarter_ends(now_trt().date(), -(-wanted // 4) * 4)  # the endpoint needs exactly 4 periods per call
    table, meta = {}, {}
    for start in range(0, len(periods), 4):
        chunk = periods[start:start + 4]
        for item in fetch(code, group, chunk):
            key = item["itemCode"]
            meta.setdefault(key, ((item.get("itemDescTr") or "").strip(), (item.get("itemDescEng") or "").strip()))
            for i, period in enumerate(chunk, 1):
                table.setdefault(key, {})[period] = fnum(item.get(f"value{i}"))
    return table, meta, periods


def choose_group(code, requested, quarters):
    order = [requested] if requested != "auto" else ["XI_29", "UFRS_K", "UFRS"]
    last_error = None
    for group in order:
        try:
            table, meta, periods = load(code, group, quarters)
        except NetworkError as exc:
            last_error = exc
            continue
        anchor = "1BL" if group == "XI_29" else "1Z"
        if any(v for v in table.get(anchor, {}).values()):
            return group, table, meta, periods
    raise last_error or NetworkError(f"no statement data for {code}")


def discrete(series, periods):
    """YTD cumulative values -> discrete quarter values keyed by period."""
    out = {}
    for year, month in periods:
        value = series.get((year, month))
        if value is None:
            continue
        if month == 3:
            out[(year, month)] = value
        else:
            prev = series.get((year, month - 3))
            if prev is not None:
                out[(year, month)] = value - prev
    return out


def build(code, group, table, meta, periods):
    mapping = INDUSTRIAL if group == "XI_29" else BANK
    available = [p for p in periods if any(table.get(c, {}).get(p) not in (None, 0) for c in (("1BL",) if group == "XI_29" else ("1Z",)))]
    available.sort(reverse=True)
    ytd = {name: {p: table.get(c, {}).get(p) for p in available} for name, c in mapping.items()}
    quarterly = {name: discrete(series, sorted(available)) for name, series in ytd.items() if name in FLOW_KEYS}
    anomalies = []
    for name in ("revenue", "export_sales", "domestic_sales", "da", "net_fees"):
        for p, value in quarterly.get(name, {}).items():
            if value is not None and value < 0:
                anomalies.append(f"{name} {p[0]}/{p[1]:02d}: negative discrete quarter ({value:,.0f}) — likely a unit/restatement "
                                 f"error in the source; TTM for {name} withheld")
                quarterly[name][p] = None
    rows = []
    for p in available:
        row = {"period": f"{p[0]}/{p[1]:02d}"}
        for name in mapping:
            row[f"{name}_ytd" if name in FLOW_KEYS else name] = ytd[name].get(p)
            if name in FLOW_KEYS:
                row[f"{name}_q"] = quarterly[name].get(p)
        rows.append(row)

    def ttm(name, end_index=0):
        qs = []
        for p in available[end_index:end_index + 4]:
            value = quarterly.get(name, {}).get(p)
            if value is None:
                return None
            qs.append(value)
        return sum(qs) if len(qs) == 4 else None

    latest = available[0] if available else None
    metrics = {"latest_period": f"{latest[0]}/{latest[1]:02d}" if latest else None, "periods": len(available),
               "data_anomalies": anomalies}
    if latest:
        for name in FLOW_KEYS & set(mapping):
            metrics[f"{name}_ttm"] = ttm(name)
            metrics[f"{name}_ttm_prev_year"] = ttm(name, 4)
        eq = ytd.get("equity_parent", ytd.get("equity_total", {})).get(latest)
        eq_prev = ytd.get("equity_parent", ytd.get("equity_total", {})).get(available[4]) if len(available) > 4 else None
        ni = metrics.get("net_income_ttm")
        if ni is not None and eq:
            base = (eq + eq_prev) / 2 if eq_prev else eq
            metrics["roe_ttm_pct"] = ni / base * 100 if base else None
        if group == "XI_29":
            rev = metrics.get("revenue_ttm")
            op, da = metrics.get("operating_profit_ttm"), metrics.get("da_ttm")
            metrics["ebitda_ttm"] = op + da if op is not None and da is not None else None
            for label, num in (("gross_margin_pct", metrics.get("gross_profit_ttm")), ("operating_margin_pct", op),
                               ("ebitda_margin_pct", metrics.get("ebitda_ttm")), ("net_margin_pct", ni)):
                metrics[label] = num / rev * 100 if num is not None and rev else None
            debt = sum(v for v in (ytd["st_fin_debt"].get(latest), ytd["lt_fin_debt"].get(latest)) if v is not None)
            cash = ytd["cash"].get(latest) or 0
            metrics["gross_fin_debt"] = debt
            metrics["net_debt_cash_only"] = debt - cash
            metrics["net_debt_incl_st_investments"] = debt - cash - (ytd["st_investments"].get(latest) or 0)
            if metrics.get("ebitda_ttm"):
                metrics["net_debt_to_ebitda"] = metrics["net_debt_cash_only"] / metrics["ebitda_ttm"]
            cfo, capex = metrics.get("cfo_ttm"), metrics.get("capex_ttm")
            metrics["fcf_ttm_calc"] = cfo + capex if cfo is not None and capex is not None else None
            if ni and cfo is not None:
                metrics["cash_conversion_cfo_to_ni"] = cfo / ni
            exp, dom = metrics.get("export_sales_ttm"), metrics.get("domestic_sales_ttm")
            if exp is not None and dom is not None and (exp + dom):
                metrics["export_share_pct"] = exp / (exp + dom) * 100
            metrics["net_fx_position"] = ytd["net_fx_position"].get(latest)
        else:
            nii, fees = metrics.get("net_interest_income_ttm"), metrics.get("net_fees_ttm")
            loans, deposits = ytd["loans"].get(latest), ytd["deposits"].get(latest)
            metrics["loan_to_deposit"] = loans / deposits if loans and deposits else None
            if nii is not None and fees is not None and nii + fees:
                metrics["fee_share_of_core_income_pct"] = fees / (nii + fees) * 100
            prov = metrics.get("provisions_ttm")
            if prov is not None and nii:
                metrics["provisions_to_nii_pct"] = prov / nii * 100
        for name in ("revenue", "net_income", "operating_profit", "net_interest_income"):
            now_v, prev_v = metrics.get(f"{name}_ttm"), metrics.get(f"{name}_ttm_prev_year")
            if now_v is not None and prev_v:
                metrics[f"{name}_ttm_growth_nominal_pct"] = (now_v / prev_v - 1) * 100
    return rows, metrics


def run(code, out_dir, group="auto", quarters=8):
    code = code.upper()
    group, table, meta, periods = choose_group(code, group, quarters)
    rows, metrics = build(code, group, table, meta, periods)
    out_dir = Path(out_dir)
    wide = []
    for key, (tr, en) in meta.items():
        entry = {"item_code": key, "desc_tr": tr, "desc_en": en}
        for p in sorted({p for p in periods if any(table.get(k, {}).get(p) for k in table)}, reverse=True):
            entry[f"{p[0]}/{p[1]:02d}"] = table.get(key, {}).get(p)
        wide.append(entry)
    write_csv(out_dir / f"{code}_statements_raw.csv", wide)
    write_csv(out_dir / f"{code}_quarterly.csv", rows)
    payload = {"code": code, "group": group, "source": "İş Yatırım MaliTablo (secondary; verify in KAP filing)",
               "fetched_at": iso(now_trt()), "metrics": metrics,
               "caveats": ["YTD values converted to discrete quarters; TTM = last four discrete quarters.",
                           "TMS 29: columns from different reports are in different purchasing-power units; growth is nominal/approximate.",
                           "Check consolidation basis and one-offs in the KAP filing notes before valuation."]}
    write_json(out_dir / f"{code}_financials.json", payload)
    view = [{"Metrik": k, "Değer": v} for k, v in metrics.items() if v is not None]
    (out_dir / f"{code}_financials.md").write_text(
        f"# {code} finansallar ({group}) — son dönem {metrics.get('latest_period')}\n\nKaynak: {payload['source']} · {payload['fetched_at']}\n\n"
        + md_table(view, ["Metrik", "Değer"]) + "\n\n" + "\n".join(f"- {c}" for c in payload["caveats"]) + "\n", encoding="utf-8")
    return payload


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("code")
    ap.add_argument("--group", default="auto", choices=["auto", "XI_29", "UFRS_K", "UFRS"])
    ap.add_argument("--quarters", type=int, default=8)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = a.out or default_out(f"fin-{a.code.upper()}")
    try:
        payload = run(a.code, out, a.group, a.quarters)
    except NetworkError as exc:
        print(f"ERROR: {exc}. Without internet, read the latest KAP financial report instead.", file=sys.stderr)
        return 3
    m = payload["metrics"]
    print(f"OK {payload['code']} group={payload['group']} latest={m.get('latest_period')} periods={m.get('periods')} -> {out}")
    keys = ["revenue_ttm", "net_income_ttm", "roe_ttm_pct", "operating_margin_pct", "net_margin_pct", "net_debt_to_ebitda",
            "fcf_ttm_calc", "export_share_pct", "loan_to_deposit", "net_interest_income_ttm", "revenue_ttm_growth_nominal_pct"]
    print({k: (round(m[k], 2) if isinstance(m.get(k), float) else m.get(k)) for k in keys if m.get(k) is not None})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
