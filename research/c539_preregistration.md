# Round 20 (C539) pre-registration: how big each bet in the rent-gap trade should be

Committed and pushed **before** any test below runs. 7 Oct 2026, ~18:45 IST.

## Why

The operator (7 Oct): "check all the strategies and their numbers in all dimensions and optimise wherever
feasible".

Round 19 (C537) already tested the rent-gap trade's timing, exit, entry, window and pair count. The one
dimension of the plan not yet tested at $1,000 is **the size of each bet**: today 10% of the capital per
leg ($100), so each $500 account carries about $1,000 of bets (1.8-2.0x on the 7 Oct screens).

Bigger bets earn proportionally more rent, but they also mean:
- bigger monthly swings;
- an account that runs low sooner;
- thinner coins harder to trade.

## Data and engine (fixed now)

- **The C533 study, unchanged except the bet size:**
  - `research/c532_india_only.py`'s `xv_pi42`: the X1 rule, "ALL harder" (midnight timing, Delta's mark,
    costs x5, Pi42's fee 0.10% x 1.18 + 0.02%, 18% GST on rent paid);
  - $1,000, whole Delta contracts;
  - 2024-10 -> 2026-09;
  - the coins Pi42 lists that trade >= $100k a day on Delta and move with Binance's (the C532/C533 set).
- **Each account on its own:** `research/c531_split_600.py`'s `sides`, with the 65% even-out rule as live.
- **Run with `C524_MARK=1`** (Delta's daily mark from the cache).
- **Engine check:** the 10% baseline must reproduce C533's figures (+50.3%/yr, t 6.07, 167 entries, worst
  month -3.89%) before any variant is read.

## Variants (one change: the bet size per leg)

| | size per leg |
|---|---|
| S8 | 8% ($80) |
| **B0** | **10% ($100), the live rule** |
| S12 | 12% ($120) |
| S15 | 15% ($150) |

## The bar (a size replaces 10% only if ALL hold)

1. Net return >= B0's + 5%/yr of capital (at costs x5).
2. **Its worst month >= -4%.** This is the operator's own March gate G1 ("no month below -4%"); B0's is
   -3.89%.
3. ~~With the 65% even-out rule, its lowest account >= 50% of its half at every daily close (never a "move
   money NOW").~~ **Amended, see below:** with the 65% even-out rule, its lowest account >= 40% of its
   starting half at every daily close (gate G1's "no side below 40%").
4. Losing months no more than B0's + 1.

A smaller size (S8) is descriptive, because B0 passes gate G1 on history (worst month -3.89%, lowest account
47.8%).

### Amendment (7 Oct, ~18:55 IST, before any variant was run)

The first version said B0 never lets an account fall below 50%. That was wrong. C533's own saved result
(`research/c533_india_1000.json`, `sides_1000_0.65`, computed 4 Oct) has B0's lowest account at 47.8% of its
$500 half.

Bar 3 now uses the threshold the plan itself must pass in gate G1: no account below 40%.

How often an account fell below 50% (the "move money NOW" alert) is reported for every size, with no bar.

## Also reported (no bar)

- Each size's average month.
- The share of months >= +2%.
- The lowest account.
- Transfers a year.
- How many entries were skipped because one contract was bigger than the leg.
