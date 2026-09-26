# C494 pre-registration: does a patient (maker-first) rebalance cut the book's costs?
Written 2026-09-26, BEFORE any 1-minute data for this test was fetched.

## Why
Round 5 (C493) measured the crypto-only C488 book at $250 (top 20, positions
under $6 dropped): fees and spread cost **4.6%/yr at dial 15% and 6.3%/yr at
dial 20%**, against about 35–54%/yr of net return. Every rebalance crosses the
spread with market orders (0.06% taker + about 0.02% half-spread = 0.08%). A
daily rebalance is not urgent, so a resting limit order could save most of
that.

**The danger is adverse selection** (Standing Rule 50: a fill is a fact about
the future). A resting buy fills when the price falls toward it, and misses
when the price runs away. The fills that are missed then cost more when they
are finally crossed. Only a path-level test can say which effect wins.

## Data
- Binance USDT-M **1-minute klines**, 2024-09 → 2026-08, for every coin the
  top-20 book traded in that window (point-in-time, delisted coins included).
- Trades: every non-zero daily weight change of the crypto-only COMBO-C, top
  20, dial 15%, positions under $6 at $250 dropped (exactly the C493 capacity
  book), decided at the UTC close of day d and executed from 00:05 UTC on day
  d+1, as the bot does.

## The two execution rules
All costs are per unit of notional traded, signed so that a positive number
is a cost. The arrival price A is the open of the 00:05 minute. The half-spread
h is 0.02% (the research assumption).

**TAKER (what runs now):** cost = 0.06% + h = **0.08%**.

**MAKER-FIRST (the candidate):**
- Post at A·(1 − h) for a buy (the bid) or A·(1 + h) for a sell (the ask).
- **Filled** if any minute from 00:06 to 00:05+W trades THROUGH the price (a
  low below the buy limit, a high above the sell limit; the conservative
  queue assumption of C491). Cost = maker fee 0.02% − h = **0.00%**.
- **Not filled:** cancel and cross at the open of minute 00:05+W. Cost =
  0.06% + h + the price drift from A to that open (adverse if the price ran
  away).
- **W = 30 minutes** (primary).

## The test and the bar
- Per trading day: turnover-weighted mean cost of each rule.
- **Test series:** TAKER cost − MAKER-FIRST cost (the saving).
- **Adopt** only if the saving has Newey-West t ≥ 2, is positive in ≥ 3 of 4
  quarters, AND the mean saving is ≥ 0.02% of notional (a quarter of today's
  cost).
- Also reported: fill rate, the average drift on missed fills, the saving per
  year at dial 15% and 20%, by coin-liquidity tercile, and W = 10 / 60 as
  diagnostics (never used for adoption).

## If adopted
The C488 rebalance posts post-only limits at the touch, waits 30 minutes, then
crosses whatever is left. This is exactly what C487 already does for exits.
It goes in with the C487 honest-fill model in paper, and with the C492
partial-fill handling live.
