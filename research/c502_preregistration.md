# C502 pre-registration: the spot pot's minimum order
Written 2026-09-28, BEFORE any S1 result with a different floor was computed.

## What the first live run showed

The server's first spot-pot run (28 Sep 07:39 UTC, C501) held BNB $9.36,
BTC $8.72 and ETH $7.69: 10.3% invested. I rebuilt the day independently from
fresh Bitget history with the research library (`_c501_s1_targets` and the
research code agree to 0.0e+00). It showed:
- **all 20 coins of the top 20 are trending up** (score +0.5 to +1.0);
- the rule wants the pot **35.8% invested**;
- the **$6 floor drops 17 of the 20** (LINK $5.85, SOL $5.78, XRP $5.51 …
  ARB $1.97). Only the three calmest coins get weights above $6.

**The $6 floor was a carry-over from futures**, where Bitget's minimum is
about $5 of notional. Bitget **spot's** minimum is **1 USDT** for every one of
these 20 pairs (`/api/v2/spot/public/symbols`, `minTradeUSDT` = 1, 28 Sep).
At $250 the floor is what decides the pot's size, not the trend or the
volatility set point: the pot runs far below its own 20% set point. The
pre-registration (C501) stated the floor, and its results include it, so the
live pot matches what was tested. The rule's author (me) got the exchange
constraint wrong.

## Test

S1 exactly as admitted in C501 (same signal, per-coin volatility units, 30%
band, 20% vol set point on the 60-day unit vol, gross ≤ 1, 0.10% per unit of
turnover, cash at 5%, 2020-05 → 2026-08, the Binance archive, crypto only,
top 20). Only the minimums change:
- **Position floor $2** at $250: twice the exchange minimum, so a position
  can still be sold after a 50% fall.
- **Order minimum $1:** a change smaller than $1 is not traded (the position
  is kept as it is), and a position already below $1 cannot be sold. This is
  simulated day by day on the final weights.

**Adopted in the pot only if it passes C501's four bars** (daily excess over
the 5% cash rate):
- Newey-West t ≥ 2.0;
- ≥ 3 of 4 equal time quarters positive;
- holdout 2025-01-01 → 2026-08-31 mean excess > 0;
- max drawdown ≤ 35%.

**It is adopted if it passes, whether its return is higher or lower than the
$6 version's.** The floor is an exchange constraint, not a signal parameter,
and $2 is the faithful one. If it fails, the pot stays at $6 and the report
says why.

**Reported, not decided on:**
- the $6 version under the same simulation;
- average exposure;
- the monthly distribution;
- the two pots together.
- **Real spot costs:** the top 20's current spot half-spreads from Bitget's
  tickers. If their median is above 0.05%, the test is re-run with the cost
  at 0.08% + the measured median half-spread, and that result decides.
