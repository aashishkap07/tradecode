# C490 pre-registration: round 3
Written 2026-09-25, BEFORE any of these tests were run.

The operator asked to go through the original request again and review the best
way to reach 2–4% a month. They asked for "sophisticated mathematical analyses,
both intraday and medium term, individualised for each asset."

Rounds 1–2 (C489) showed the same thing every time: intraday signals carry real
gross information, but **paying the taker fee and the spread 4–9 times a day
destroys it**. Round 3 therefore tests the families that were never tried and
that attack the cost itself, or add an independent medium-term source.

Everything below was fixed before any result was seen.

## Costs (Bitget VIP0, verified 2026-09)
| leg | cost |
|---|---|
| perp maker | 0.02% |
| perp taker | 0.06% + 0.02% half-spread = 0.08% |
| spot maker or taker | 0.10% (+ 0.02% half-spread when taker) |
| funding | the actual Binance archive rate, 8-hourly |

## Data
- **Binance USDT-M hourly and daily archive, 2021-01 → 2026-08.** Hourly: the
  383 coins ever in the daily top 60, delisted ones included. Daily: 860
  contracts.
- **Universe:** each day's point-in-time top 40 by 30-day median quote volume.
- **For R3c:** Binance spot daily closes for the same coins (data.binance.vision
  spot archive).

## R3a — LP: liquidity-provision mean reversion with resting limit orders (intraday)
The literature: short-horizon crypto reversal "concentrates after aggressive
taker flow" and is "compensation for liquidity provision" (arXiv 2608.21888).
So the engine is the liquidity provider, and never pays taker to enter.

**Placement, at every hour close t,** for each universe coin:
- σ = standard deviation of 1-hour returns over the past 168 h (relativistic);
- a resting BUY limit at L = C_t·(1 − 2σ) and a resting SELL limit at
  S = C_t·(1 + 2σ), valid for the next hour.

**Filling — conservative, needs a trade THROUGH the price:**
- long filled at L if the next hour's low < L; short filled at S if its
  high > S;
- if both fill in the same hour, both are held;
- entry fee: maker 0.02%.

**Exits, checked hour by hour, stop FIRST (conservative):**
- **Stop** (taker, 0.08%): the price goes a further 2σ beyond the entry (long:
  low < L·(1 − 2σ)). In the fill hour itself only the stop is checked.
- **Target** (maker, 0.02%): a resting limit at C_t, the price before the move.
  It fills when a later hour's high > C_t (long) or low < C_t (short).
- **Time exit** (taker, 0.08%) at the close of hour 12 after the fill.

**Sizing:** each position is 10% of equity in notional, with at most 10 open at
once. A new fill is skipped while 10 are open. Funding is charged on open
positions.

**Variants:**
- **LP (primary):** as above.
- **LPh:** LP only on coins whose DFA Hurst (168 h) < 0.5, i.e. mean-reverting
  (chaos regime filter).
- **LPm:** LP only when the coin's first-order Markov edge (f14) points back
  toward the mean, i.e. P(reversal) > P(continuation) (Markov filter).

## R3b — IND: per-asset individualised selection (intraday)
- **Each day at 00:00 UTC, for each universe coin,** take three rules on that
  coin alone, held for 4 hours each, non-overlapping:
  - TREND: sign(z_r24);
  - REVERT: −sign(z_r4);
  - FLAT.
- **Replay the last 60 days** of each rule on that coin, net of the taker round
  trip (0.16%).
- **Pick** the rule with the best trailing net mean, if it is above +0.10% per
  trade; otherwise FLAT.
- **Trade** the chosen rule on that coin for the next 24 hours (six 4-hour
  holds). Each position is 1/20 of equity.

## R3c — CARRY: spot-perp cash-and-carry (medium term, market-neutral)
- **Each day, for each universe coin that also trades spot:**
  - enter when the trailing 3-day funding, annualised, exceeds 10%: long spot,
    short the perp, equal notional;
  - exit when it falls below 5% (hysteresis).
- **P&L** = funding received on the short perp + spot price change − perp price
  change (the basis, measured from real spot and perp closes) − costs on both
  legs, charged at entry and at exit.
- **Sizing:** each position is 10% of equity in notional (spot capital plus perp
  margin at 5×), with at most 8 open.

## R3d — per-asset individualised trend lookback (medium term)
- **Each coin gets its own C1 trend lookback,** one of 7, 14, 28 or 56 days.
- **The choice is made walk-forward** each month, from the coin's own trailing
  180-day net performance of each lookback.
- **Compare against the pooled C1** (the sign-average of all four) on the same
  days and weights.
- **To pass, R3d must beat C1:** the paired daily difference is positive in at
  least 3 of 4 quarters AND has t ≥ 2.

## Evaluation and admission (the project's standing bar)
- **Window:** 2021-07 → 2026-08 out of sample, with walk-forward fitting
  wherever anything is fitted.
- **Measure:** daily net returns; Newey-West t with 5 lags; four chronological
  quarters.
- **Admit when** at least 3 of 4 quarters are positive AND t ≥ 2. With 6 primary
  items, t ≥ 2.6 (Bonferroni) is reported too.
- **Also reported:** correlation with the C488 book, and the Sharpe ratio of
  book + item at equal risk.

## Integration rule (declared now)
- **An admitted INTRADAY item (R3a/R3b)** becomes the intraday engine, trading
  the paper account with an equal risk budget beside C488, under the one dial.
- **An admitted R3c** becomes a fourth C488 sleeve at equal risk. It needs a
  spot order path, so it starts as paper.
- **An admitted R3d** replaces C1's pooled lookback.
- **Anything not admitted** is not traded. The C489 shadow keeps running
  regardless.
