# VİOP and warrant protocol

## Identify first

For VİOP, verify underlying, contract code, direction, contract multiplier/size, expiry, settlement type, initial and maintenance margin, daily price limits, current bid/ask, open interest, and commissions.

For warrants, verify issuer, underlying, call/put type, strike, expiry, conversion ratio, exercise/settlement, current bid/ask, issuer market-making conditions, and product document.

## Explain the core difference

- A long warrant buyer can generally lose the premium paid but is exposed to time decay, implied volatility, spread, liquidity and issuer terms.
- A VİOP futures position is marked to market daily and losses can exceed the initial margin or deposited speculative amount; margin calls and forced closure are possible.
- Product-specific terms and account agreements own the final answer. Do not generalize another derivative's mechanics.

## Scenario analysis

Use `scripts/leveraged_scenarios.py` only after verified inputs. Show at least adverse, flat, moderate favorable, and extreme moves. Include fees and explicitly separate expiry intrinsic value from a pre-expiry warrant market price.

Never infer that a 10% underlying move creates a fixed warrant return. Delta, time, volatility, ratio, spread and issuer quoting matter.

## Quantity gate

Before answering “kaç adet?” require executable price, lot/contract size, budget, maximum loss, fees, expiry/horizon, and whether losses may exceed paid cash. If a field is missing, still rank suitable product structures and provide the exact formula, entry gate and screen fields needed; finalize the number when the live values arrive.

Do not default to “do not trade” because the user accepts high risk. Choose between VİOP, warrant, cash instrument or no-edge based on budget feasibility, probability-weighted payoff, catalyst, liquidity, spread, expiry and the possibility of loss beyond deposited cash.
