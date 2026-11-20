# C514 pre-registration: round 12, "is there a point where a winning trade is more likely to lose from here?"
Written 2026-09-30, BEFORE any data for these tests was computed.

## Why this round

The operator asked: if a trade is near its most profitable point, so that
beyond it there is a **more than 70% chance of losing**, should the bot
close it? They also asked for rules that capture profit and cut losses.

That is two questions:
1. **Does such a point exist in this book's trades?** This can be measured
   directly. Look at every day a position was held and how far it was in
   profit, measured in that coin's own volatility (a relative, not absolute,
   yardstick). Then count how often the next days lost.
2. **Do exit rules built on it beat simply holding, after costs?**

**My prior:**
- For trend and momentum books, the literature says profit-taking cuts the
  right tail that pays for the strategy (Moskowitz, Ooi & Pedersen 2012).
- A stop-loss adds value only when returns are serially correlated in the
  stop's direction (Kaminski & Lo 2014).
- So I expect P(loss ahead) near 45–55% in every bucket, and take-profit
  rules to lower the return.
- But crypto shows reversal after extreme short-term moves, so the extreme
  buckets are a fair question. That is why it is tested rather than assumed.

## The base: the book as it runs

- The N2+N3 C2 rank (C507/C510);
- crypto only, top 20;
- C1/C2/C3 combined at **dial 20%** (target vol 26.7%), gross cap 3×;
- the $6 floor at $250;
- costs: 0.08% of turnover, plus funding;
- data: the Binance archive, 2020 → 2026-08.

This is `research/omega_c510_research.py`'s descriptive N2+N3 book.

## Definitions

- **A position:** coin *j* is held on day *i* when the base's final weight
  W[i,j] ≠ 0. The weight is decided at the close of *i* and held during
  *i*+1. Its side is *s* = sign(W[i,j]).
- **An episode:** a maximal run of consecutive days with the same nonzero
  side.
  - Its entry day *e* is the first day of the run; its entry price is the
    close of *e*.
  - Its last day is *L*. The position is held through day *L*+1.
- **Open profit in own-volatility units** on day *t* > *e*:
  **z = s · ln(close_t / close_e) / (sd_t · √(t − e))**. Here sd is the
  book's own 30-day trailing standard deviation of daily returns.
- **7-day stretch:** **u = s · ln(close_t / close_{t−7}) / (sd_t · √7)**.

## Part A: the measurement (it answers the question; no admission)

**The buckets.** For every held coin-day with *t* > *e*, bucket z into
(−∞,−2], (−2,−1], (−1,0], (0,1], (1,2], (2,3] and (3,∞).

**For each bucket, report:**
- the number of coin-days;
- P(the next day's signed return < 0);
- P(the next 7 days' signed return < 0);
- **P(the rest of the episode, held as the book holds it, loses)**: the
  signed log return from close *t* to close *L*+1;
- the mean of each.

**The same for the 7-day stretch u.** Price only: funding over a week is
about 0.1–0.2% and is left out, so that "loss" means the price went against
the position.

**The reading, fixed now:**
- **A "70% point" exists** if some bucket with ≥ 500 coin-days has P(7-day
  loss) ≥ 70% or P(rest-of-episode loss) ≥ 70%.
- If none does, the answer to the operator's question is that no such point
  can be seen in advance in this book.

## Part B: five exit rules (admission tests)

Each rule is applied to the base's final weights, after the floor. Nothing
else changes.
- The episodes are the base's.
- An exit decides at close *t* and acts from day *t*+1, so there is no
  look-ahead.
- The extra turnover pays 0.08%, through `R.pnl`.
- After an exit, the coin stays out until the base's episode ends. The next
  episode (a side change, or a re-entry after a zero) starts fresh.

| # | rule | when |
|---|---|---|
| X1 | take profit | the first day z > 2: the weight → 0 for the rest of the episode |
| X2 | take profit | the first day z > 3: the same |
| X3 | scale out | the first day z > 2: the weight is halved for the rest of the episode |
| S1 | stop loss | the first day z < −2: the weight → 0 for the rest of the episode |
| S2 | trailing stop ("chandelier") | the first day s · ln(close_t / best) ≤ −3 · sd_t, where best is the most favourable close since entry: the weight → 0 for the rest of the episode |

**Admission, for each rule** (Δ = the rule's daily return − the base's):
- Newey-West t(Δ) ≥ **2.33** (one-sided 5%, Bonferroni for 5 tests);
- ≥ 3 of 4 equal time quarters with mean Δ > 0;
- mean Δ > 0 over the holdout, 2025-01-01 → 2026-08-31;
- the rule's max drawdown no more than 2 points worse than the base's.

**Also reported:**
- CAGR, Sharpe, max drawdown;
- the worst month, and the share of months ≥ +2%;
- P(a year averages ≥ +2%/month): a 30-day block bootstrap, and the same
  with a ⅓ haircut (the C504 method);
- the average gross.

**Descriptive only:** Part B again at dial 15%.

## What happens after

- Nothing is tuned after seeing a result. The thresholds 2, 3, −2 and 3·sd
  are fixed here. A fail is recorded as a fail.
- An admitted rule enters the bot's rule tournament as a paper row first.
  It becomes the traded rule only after it tracks forward.
