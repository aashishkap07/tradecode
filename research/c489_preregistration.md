# C489 pre-registration: the intraday engine
Written 2026-09-25, BEFORE any of these tests were run.

The operator asked for a profitable intraday engine built on these principles:
relativistic analysis, prediction rather than reaction, a rigorous probability
estimator, chaos theory and Markov chains. It must run alongside the C488
medium-term book and target 2–4% a month on $250–$500.

Everything below was fixed before any result was seen. Anything tested later is
labelled exploratory and cannot be admitted.

## What the literature says, and so what this plan must respect
- **15-minute reversal is real but worth about 1.3 bp per trade** against about
  5 bp of cost (arXiv 2608.21888).
- **The quarter-hour effect is worth about 0.5 bp.** Its order imbalance
  predicts returns 4–12 hours ahead (arXiv 2607.09426).
- **Bitcoin intraday momentum** (Shen, Urquhart & Wang 2022, Financial Review)
  is driven by liquidity provision.

So the unit of decision is the **1-hour bar** and the holding horizon is
**4 hours**. A per-trade edge has to beat a taker round trip of 0.16% (0.06% +
0.06% fees + 2 × 0.02% half-spread). Anything faster is ruled out by the cost
arithmetic above, not tested.

## Data
- **Crypto:** the Binance USDT-M archive, 1-hour klines including taker-buy
  volume, 2021-01 → 2026-08, for all 383 coins that have ever been in the
  daily top 60 (delisted ones included), plus the 8-hour funding already
  downloaded for C488.
- **Universe each hour:** that day's point-in-time top 40 by 30-day median
  quote volume (the C488 rule).
- **RWA (gold, silver, oil, S&P, Nasdaq, US stocks on Bitget):** under one year
  of history. **Exploratory only this round; they cannot be admitted.**

## Features
All features are relativistic: each is computed from data up to the close of
hour t, and each is measured against the coin's own past or against the
cross-section, never against an absolute level.

| # | feature | definition |
|---|---|---|
| f1 | z_r1 | 1-hour return / σ₁ₕ (σ₁ₕ = std of 1-hour returns over the past 168 h) |
| f2 | z_r4 | 4-hour return / (σ₁ₕ·√4) |
| f3 | z_r24 | 24-hour return / (σ₁ₕ·√24) |
| f4 | xs_r4 | cross-sectional rank (0–1) of the 4-hour return |
| f5 | flow1 | 1-hour taker-buy share, z-scored against its own 168-hour history |
| f6 | flow4 | 4-hour taker-buy share, z-scored the same way |
| f7 | vsurp | log(1-hour quote volume / its 168-hour median) |
| f8 | volreg | σ over 24 h / σ over 168 h |
| f9 | resid4 | 4-hour return minus β × BTC's 4-hour return (β from 168 h), / residual σ |
| f10 | btc4 | BTC's z_r4, the same for every coin |
| f11 | fundz | latest funding rate, z-scored against the coin's own past 30 days |
| f12 | pe | permutation entropy (order 3) of the last 48 one-hour returns, normalised 0–1 |
| f13 | hurst | DFA Hurst exponent of the last 168 one-hour returns |
| f14 | mk1 | Markov edge: P(up) − P(down) next hour, from the coin's own 3-state chain (states by z_r1 < −0.5, middle, > 0.5) over the past 720 h, Laplace-smoothed |
| f15 | mk2 | the same from a second-order chain (last two states) |
| f16 | rpos | position of the close in the 24-hour high–low range (0–1) |

## Hypotheses (each is a long/short portfolio of the hourly universe)
- **Portfolio construction:** long the top fifth, short the bottom fifth, equal
  weight, gross exposure 1. Each hourly cohort is held for 4 hours, and 4
  overlapping cohorts each carry ¼ of the capital (Jegadeesh–Titman).
- **Costs:** 0.08% per unit of turnover, plus actual funding.

| id | rule (the signal ranked long → short) |
|---|---|
| H1 | −z_r1 (1-hour reversal) |
| H2 | +z_r24 (24-hour continuation) |
| H3 | +flow4 (buying pressure persists) |
| H4 | +mk1 (first-order Markov edge) |
| H5 | +mk2 (second-order Markov edge) |
| H6 | chaos switch: hurst > 0.55 and pe below the cross-sectional median → +z_r24; hurst < 0.45 → −z_r4; otherwise 0 |
| H7 | −resid4 (catch-up to BTC: coins that lagged their beta move) |
| H8 | −fundz (fade crowded funding over the next 4 h) |
| **M1** | **the probability model:** logistic regression on f1–f16, each standardised cross-sectionally every hour. The target is sign(4-hour forward return − cross-sectional median). Retrained every 30 days on the previous 180 days, pooled over coins, L2 penalty C = 0.1. **Walk-forward: out-of-sample from 2021-07 onward.** Ranked by predicted probability. |
| **M1g** | M1 traded only in hours when the top-minus-bottom fifth predicted return spread (calibrated on the training window) exceeds the 0.16% round trip; otherwise flat |

## Evaluation
- **Out-of-sample window:** 2021-07 → 2026-08. This is walk-forward for
  M1/M1g; the simple rules fit nothing.
- **Daily net returns;** Newey-West t with 5 lags.
- **Four chronological quarters** of the out-of-sample window.
- **Admission, the project's standing bar:** positive in at least 3 of 4
  quarters AND t ≥ 2. With 10 candidates, t ≥ 2.8 (Bonferroni at 5%) is also
  reported, and an item at 2 ≤ t < 2.8 is flagged as marginal.
- **Also reported:** correlation with the C488 book's daily returns, the
  combined Sharpe, and capacity at $250 and $500 (the $5 minimum order).

## Integration rule (declared now)
- **If one or more items pass:**
  - The intraday engine trades the highest-t passing item (one item, no
    blending chosen after the fact).
  - It gets an equal risk budget with the C488 book: each is scaled to half
    the dial's volatility, and the total stays capped at the dial.
- **If nothing passes:**
  - The intraday engine runs as a **shadow**: a separate paper ledger with zero
    effect on equity, trading M1 so its honest record accumulates.
  - C488 keeps the full risk budget.

---

## Round 2 — appended 2026-09-25, after round 1 and BEFORE any 2024-01 → 2026-08 test of the items below

**Round 1 result.** All 10 items failed by a wide margin (t between −4 and −35).
- Some raw edges are real and stable, before costs:
  - 24-hour continuation: +13% to +56% a year, in every year;
  - first-order Markov: positive in 5 of 6 years.
- The look-ahead check shows +4,161%/yr gross and a random signal about 0, so
  the harness is sound.
- **Hourly rebuilds turn over the account 4–9 times a day, and costs of 100–270%
  a year swamp those edges.**

**Round 2 design.** Exploration used 2021-07 → 2023-12 only. The data from
2024-01 → 2026-08 is the untouched holdout. Designs explored:
- low-turnover hysteresis books: enter in the top or bottom 10% or 5%, exit at
  the median or the 70th percentile, minimum hold 4 h or 24 h, fixed size per
  position;
- the signals H2, H4 and their combination with flow;
- an execution-timing overlay on the C488 book's daily trades.

**The one item carried to the holdout:** the best exploration Sharpe.
- **H2x** = 24-hour continuation (z_r24 cross-sectional rank).
- Enter long at a rank of 0.90 or above, short at 0.10 or below.
- Exit when the rank crosses 0.5, after at least 4 hours.
- Each position is 1/8 of equity; costs and funding as in round 1.
- Exploration result: Sharpe +0.19, t +0.35.

The timing overlay did no better than random deferral in exploration (at most
+1.3%/yr, t < 1), so it is **not** carried forward.

**Holdout bar:** at least 3 of 4 quarters of 2024-01 → 2026-08 positive AND
t ≥ 2. If H2x fails, the no-pass rule of round 1 applies: shadow only.
