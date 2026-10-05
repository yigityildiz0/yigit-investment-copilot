# Module: bist-microstructure-flow

> Part of the `yigit-investment-copilot` skill. Paths below are relative to this module folder (`modules/bist-microstructure-flow/`).
> Original trigger scope: Read short-horizon liquidity and flow evidence on Borsa İstanbul — order book depth (derinlik), broker distribution (AKD), custody/settlement distribution (takas), VWAP, volume anomalies, limit-up/limit-down queues, foreign ownership share, VBTS measures and manipulation red flags — from licensed data, broker-app screenshots or public notices. Use for "AKD ne diyor", "takas analizi", "derinlikte alıcı var mı", "tahtacı var mı", "tavan serisi devam eder mi", "yabancı alıyor mu", or when a short-term trade needs execution and flow context. Flow is timing/liquidity context, never proof of ownership or manipulation.

# BIST Microstructure and Flow

Read [references/flow-signals.md](references/flow-signals.md) and [references/manipulation-red-flags.md](references/manipulation-red-flags.md).

## Inputs

- **Licensed feeds** (Matriks, Foreks, broker platforms such as İşCep/TradeMaster and others): depth, AKD, takas, trade prints. Borsa İstanbul sells level-2/broker-ID/second-level analytics as data products.
- **Screenshots from the user's broker app**: verify ticker, date/time and whether the screen is delayed; read numbers carefully; never infer what is not visible.
- **Public**: KAP notices (VBTS measures, circuit breakers, SPK bans, buybacks, insider trades), Borsa İstanbul announcements, MKK/Borsa İstanbul foreign-share statistics, snapshot fields (relative volume, turnover, VWAP).

## Workflow

1. Confirm entitlement, timestamp and latency; name the source.
2. Normalise: compare today's volume/value with the 20–60 day median and with the same session time; for AKD/takas compare net positions with float and average volume.
3. Read the book: spread in ticks, depth on each side within 2–3% of price, iceberg/refresh behaviour if visible, queue size at limit prices.
4. Cross-check with KAP/news and with XU100/sector moves: flow without news in a small-float stock is a warning, not a buy signal.
5. Translate into execution: can the planned size enter and exit within 1–2% of ADV? Where would a stop realistically fill? Is a limit-down gap likely to trap the position?
6. Hand the result to `trade-management-exits` (execution) and `investment-committee` (as the technical/flow brief).

## Hard rules

- Broker IDs are intermediaries, not beneficial owners; "X kurum topluyor" does not reveal who or why.
- Do not accuse anyone of manipulation; report red flags and let SPK/KAP facts speak.
- A single snapshot of depth or AKD is noise; require persistence across sessions and consistency with price/volume.
- Never redistribute licensed data; summarise.

## Output

Source/time · liquidity table (value traded vs median, spread, depth, ADV share of the planned order) · flow observations with persistence · red flags · execution implication (entry method, max size, exit feasibility) · confidence.
