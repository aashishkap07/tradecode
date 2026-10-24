# C493 pre-registration: round 5 — breadth
Written 2026-09-26, BEFORE any of these signals was computed. The Binance
archive download that feeds them was still running when this file was pushed.

## Why this round, and the one piece of arithmetic that decides it

The operator asked for a serious re-analysis of everything, from the basics,
drawing on every field, aimed at **2–4% a month** (27–60% a year).

A futures book's return is roughly **Sharpe × volatility**. Volatility is a
choice (the risk dial): the same Sharpe at twice the volatility makes twice
the return, with twice the drawdown. So the only thing research can add is
**Sharpe**, and the only reliable way to raise the Sharpe of a book of modest
edges is **breadth**. Independent edges add in quadrature:

    Sharpe(combined) ≈ √(Σ Sharpeᵢ²)   (for uncorrelated sleeves at equal risk)

This is the "fundamental law of active management", IR ≈ IC·√breadth, and it is
the same arithmetic as averaging independent noisy measurements in physics.
C488 is exactly this: three sleeves with Sharpe 0.6–1.0, correlated at about
0.05, combine to 1.33. Each extra **independent** sleeve with Sharpe s raises
the book to √(1.33² + s²):
- s = 0.5 → 1.42;
- two such sleeves → 1.50;
- four → 1.66.

At 20% volatility, those Sharpe levels are 2.2–2.8% a month **before** decay.
So this round looks for **new, independent, daily-to-weekly edges**. They must
be slow enough that costs (0.08% per unit of turnover) do not eat them;
Standing Rule 52 is why nothing intraday is retried.

## What is already settled (not retested)

- **Intraday on price, flow, Markov, chaos or entropy:** real gross edges,
  negative after costs (C489, rounds 1–2).
- **Limit-order liquidity provision:** fails on 1-minute paths (C491).
- **Per-coin trend/revert switching:** fails (C490 R3b).
- **Trend on commodities and indices:** about 0 since 2007 (C488 T1).
- **Spot-perp carry:** admitted but small and decaying; it runs as a paper
  ledger (C490).

## Not testable, and why (Standing Rule 17: name the source tried)

- **Token unlocks.** The evidence is strong: 88.5% of 52 large Binance unlocks
  2023–25 were negative within 72 h, with declines starting about 30 days
  before. But point-in-time unlock calendars are paid only:
  `api.llama.fi/emissions` answered "Upgrade to the paid API plan", and
  Tokenomist is paid. N1 below captures much of the same supply overhang,
  because unlock cliffs are concentrated in a token's first months.
- **Stock and ETF perps on Bitget.** There is no point-in-time universe. The
  list Bitget carries today (NVDA, PLTR, MSTR, …) was chosen after those stocks
  won, so any backtest on it is survivorship-biased by construction.

## Data, costs, conventions (identical to C488)

- **Data:** the Binance USDT-M archive, daily klines and actual funding, every
  contract, delisted ones included, 2020-01 → 2026-08. Stablecoins, indices and
  the 2026 stock/commodity perps are excluded (the C488 `EXCLUDE` list plus
  `TRADFI` from `research/c488_tradfi_check.py`).
- **Universe:** the point-in-time top 40 by 30-day median quote volume, age
  ≥ 90 days. N1 has its own universe.
- **Timing:** weights are decided at the UTC close of day i and earn day i+1
  (lag 1).
- **Costs:** 0.08% per unit of turnover; funding as paid.
- **Scaling:** `sc = clip(0.02 / σ30, 0, 1)` per coin, where σ30 is the trailing
  30-day standard deviation of daily returns.
- **Rebalancing:** "weekly" means the target chosen on Monday (UTC) is held all
  week, as in C2/C3.

## The hypotheses (seven tests, signs declared in advance)

**N1 — NEW-LISTING SHORT (supply overhang).**
- *Mechanism:* newly listed tokens carry low float and high FDV, with airdrop
  recipients and early investors selling into the first months and vesting
  cliffs close behind. 2025 CEX listings: median −82%, 12% profitable (Delphi
  Consulting, 652 listings); 2024: negative median (Animoca Research).
- *Listing day:* the first day with a close in the archive; age = days since
  then.
- *Active on day i if:* 14 ≤ age ≤ 120, and the 7-day median quote volume
  (days i−7..i−1) ranks in the top 100 of all symbols trading that day. The
  first two weeks are skipped: that is the listing pump and its squeezes.
- *Weight:* −clip(0.02/σ14, 0, 1) / max(n_active, 10), with σ14 over the last
  14 daily returns. Rebalanced daily with the 30% band (as C1). The position
  exits after day 120.
- *Sign:* shorts earn.

**N2 — LOW VOLATILITY (low-risk premium).**
- *Mechanism:* leverage-constrained and lottery-seeking buyers overpay for
  high-volatility coins. A low-volatility premium is documented in crypto
  post-2017, strongest with 2–3 month volatility.
- *Rule:* in the top-40 universe, rank by the 60-day standard deviation of
  daily returns; long the lowest fifth, short the highest fifth.
  w = −xs_rank(σ60)·sc / (2N·0.2), weekly.
- *Sign:* low-vol minus high-vol earns.

**N3 — ATTENTION (abnormal volume).**
- *Mechanism:* attention spikes bring in buyers who overpay; the price then
  gives it back.
- *Rule:* A = median(qv, days i−7..i−1) / median(qv, days i−60..i−1). Short
  the highest fifth, long the lowest. w = −xs_rank(A)·sc / (2N·0.2), weekly.
- *Sign:* low attention minus high attention earns.

**N4a — CROWD CONTRARIAN (positioning, not price).**
- *Data:* the Binance futures `metrics` archive, the last 5-minute row of each
  UTC day. `count_long_short_ratio` is the long/short ratio over **all
  accounts** (the crowd).
- *Signal:* z = (x_i − mean(x over the last 30 days)) / std(x over the last 30
  days), with x = ln(ratio), needing ≥ 20 valid days.
- *Rule:* w = −xs_rank(z)·sc / (2N·0.2), weekly. Short where the crowd has
  crowded long, relative to its own normal.
- *Sign:* contrarian earns.

**N4b — FOLLOW THE BIG ACCOUNTS.**
- *Rule:* the same construction on `sum_toptrader_long_short_ratio` (the top
  20% of accounts by margin, position-weighted).
  w = +xs_rank(z)·sc / (2N·0.2), weekly.
- *Sign:* following earns.
- *Window:* N4a/N4b are evaluated only where the metrics exist for at least 10
  universe coins. If that is under 2 years, they are reported as
  **insufficient data**, not as failures.

**N5 — PATH EFFICIENCY (fractal / chaos, at a horizon costs allow).**
- *Mechanism:* a persistent path (Hurst > 0.5) travels far relative to the
  distance it wiggles. Kaufman's efficiency ratio is the daily-scale proxy for
  the path's fractal dimension.
- *Rule:* ER = |ln(Cᵢ/Cᵢ₋₂₈)| / Σ₂₈|ln(Cₖ/Cₖ₋₁)|. The C1 trend weight times
  ER / mean(ER over the universe that day): the same average size, more weight
  on clean trends. Banded daily as C1.
- *Test:* the difference series pnl(N5) − pnl(C1) (it replaces C1 only if it
  beats it).

**N6 — FACTOR MOMENTUM (a self-reinforcing loop).**
- *Mechanism:* strategy returns are themselves persistent (factor momentum:
  Ehsani & Linnainmaa in equities, and a documented crypto factor momentum at a
  3-week lookback). This is the physiological loop the operator asked about: a
  pathway that has been firing is strengthened, one that has been failing is
  rested.
- *Rule:* in `combine`, each sleeve's equal-risk weight is multiplied by
  mₖ = 1 if its unit P&L over the last 21 days (through the decision day) > 0,
  else 0, fixed on Mondays. The vol target is then applied as usual.
- *Test:* FM(C1, C2, C3) − COMBO-C, as a difference series (it only runs on the
  existing sleeves, so its test does not depend on the others).

## The admission bar (for each of the seven)

Seven tests, one-sided at a family-wise 5% (Bonferroni 5%/7). Each must meet
all four conditions, on the series named above:
- **Newey-West t ≥ 2.45**;
- **≥ 3 of 4 quarters positive**;
- **mean > 0**;
- **mean > 0 over 2024-01 → 2026-08** ("it still works": the C488 edges have
  faded, and a sleeve that died before 2024 does not help the operator now).

## The combination (declared now)

**COMBO-E** combines at equal risk (C488 `combine`, 20% volatility, gross ≤
3×):
- C2 and C3;
- **C1, or N5 if N5 is admitted;**
- every admitted sleeve among N1, N2, N3, N4a, N4b.
If N6 is admitted, COMBO-E uses the factor-momentum weights.

Reported against COMBO-C:
- full-period and 2024-01 → 2026-08 results: net/yr, Sharpe, t, max drawdown,
  average month, % months positive, by year;
- correlations between all sleeves;
- the dial each of 2%, 3% and 4% a month would need, and its historical
  drawdown;
- **capacity:** the book at $250 and $1,000 with positions under $6 dropped and
  the C488 coin count (Standing Rule 51).

## What ships (integration rule, declared now)

- **If COMBO-E beats COMBO-C on Sharpe** both over the full period **and** over
  2024-01 → 2026-08, **and** survives the $6 floor at $250: the admitted
  sleeves are added to the C488 engine. They run in paper first, like the rest
  of the book, with parity tests against this research code.
- **Otherwise nothing ships**, and the report says so.

Diagnostics that are reported but **never** used for admission: N1 entry day
7/14/30 × exit day 60/120/180; N2 with 30- and 90-day volatility.
