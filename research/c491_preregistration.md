# C491 pre-registration: round 4, the limit-order test on 1-minute prices
Written 2026-09-25, BEFORE any 1-minute data was downloaded or looked at.

## Why this round exists
Round 3's R3a (C490) was the pre-registered test of the engine as a liquidity
provider:
- resting limits at 2σ from each hour's close;
- a stop at a further 2σ;
- a maker target at the old close.

Simulated on hourly bars with the conservative ordering (stop first), it failed:
−480%/yr, t −11.8, 0/4 quarters.

A diagnostic run afterwards changed only the unknowable order of prices
**inside** the hour: no stop in the fill hour, and target before stop. It showed
+165%/yr, t +7.1, 4/4 quarters.

So the verdict depends entirely on the path within the hour, which hourly bars
cannot see. This round resolves it with the path itself. R3a's failure stands as
recorded; round 4 is a new test with its own bar.

## Data
- **Binance USDT-M 1-minute klines** from data.binance.vision (monthly archive),
  2024-09-01 → 2026-08-31 (24 months), for every coin that was ever in the
  universe below during that window, delisted ones included.
- **Hourly closes and funding:** the same archive as rounds 1–3.

## Universe
Each day's point-in-time **top 20** by 30-day median quote volume, 90+ days old.
This is the same ranking code as C488 (research/omega_c488_research.py
`universe`, TOPN = 20).

## The rule (the R3a rule, unchanged)
**Placement.** At every hour close t, for each universe coin:
- σ = the standard deviation of 1-hour returns over the past 168 h;
- a buy limit at L = C_t(1 − 2σ) and a sell limit at S = C_t(1 + 2σ), valid for
  the next 60 minutes.

**Fill.** A limit fills at its price in the first minute of the hour that trades
**through** it: the low is below L, or the high is above S.
- One position per coin.
- If both sides trade through, the earlier minute wins; in the same minute, the
  buy.
- Entry fee: maker 0.02%.

**Exits:**
- **Stop** at L(1 − 2σ) for a long, S(1 + 2σ) for a short. It is a taker exit
  (0.08%) at the stop, or at the minute's open if the open is already beyond it
  (a gap).
  - In the fill minute only the stop is checked: the price reached the limit
    before it could reach the stop.
- **Target** at C_t: a resting maker limit (0.02%), filled on a trade-through
  from the minute after the fill.
- **Time exit** at the close of hour 12 after the fill hour, taker 0.08%.

**Sizing:**
- 10% of equity in notional per position, at most 10 open.
- Funding is charged at each settlement on open positions.
- P&L is in return units, as in R3a.

**Missing minutes.** If a coin has no 1-minute data for an hour, it is not
traded that hour. Coverage is reported.

## What is reported, all on the same coins and window
| item | fill path | ordering when stop and target touch in one bar |
|---|---|---|
| **R4-M (PRIMARY)** | 1-minute | stop first |
| R4-Mo | 1-minute | target first |
| R4-H (reference) | hourly (the R3a code) | stop first |
| R4-Ho (reference) | hourly | target first, no fill-hour stop |

## Admission (the standard bar)
- **Measure:** daily net returns; Newey-West t with 5 lags; four chronological
  quarters of 6 months.
- **Admit** R4-M if at least 3 of 4 quarters are positive AND t ≥ 2.
- **Inconclusive** if R4-M fails but R4-Mo passes: the answer then lies inside
  single minutes, which this data cannot see, and nothing ships.

## Integration rule (declared now)
- **Admitted:** the LP rule becomes the intraday engine on the paper account.
  - It uses C487 honest fills: resting orders filled only on live
    trade-through.
  - It gets its own risk budget of 10% notional per position, at most 10 open,
    beside C488.
  - No real money until the live-mode checklist in the Atlas is done.
- **Not admitted or inconclusive:** nothing ships; the C489 shadow continues.
