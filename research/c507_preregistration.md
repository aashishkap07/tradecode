# C507 pre-registration: round 10 — the momentum sleeve's short squeezes
Written 2026-09-29, BEFORE any data for these tests was computed.

## Why this round

The book's first four days (25–28 Sep 2026) lost 3.9% live. The same rule
simulated on Bitget's data lost 2.9% over those days, after +9.6% in August
and +3.7% on 1–24 Sep. **In both, the damage came from momentum-sleeve (C2)
shorts that were squeezed:**

| coin | realised live | simulated price P&L |
|---|---|---|
| PUMP | −$3.72 | −1.34% |
| WLD | −$1.49 | −0.81% |
| LINK | −$1.59 | −0.52% |

That is about 60% of the live loss. Four days prove nothing on their own: a
4-day loss this size happened about 8 times a year in 2020–26. But the
failure mode is a real one:
- crypto returns have **positive skew** (pumps are larger than dumps);
- a short on a coin that has lagged is a short on a coin that can be pumped;
- the short leg of cross-sectional momentum is where squeezes happen.

So the question for 6½ years of data is whether the short leg earns its
risk.

## The base

Identical to C500/C505:
- crypto only, top 20;
- C1/C2/C3 combined at target vol 20% (dial 15%), gross cap 3×;
- $6 floor at $250, cost 0.08% of turnover, funding charged;
- the Binance archive, 2020 → 2026-08.

## The three tests (each changes ONLY C2; C1, C3 and the combining are unchanged)

**N1 — Momentum long-only.** C2 keeps its long leg (the top fifth by 14-day
return) and drops its short leg. The combiner re-sizes the sleeve to its
risk share as usual.
- **My prior:** in crypto the long leg carries most of momentum's return and
  the short leg most of its crashes. But the short leg also hedges the long
  leg's market exposure, so the book's drawdown could get worse.

**N2 — No shorting a crowded short.** A C2 short is skipped when the coin's
7-day summed funding is below 0. Negative funding means shorts are paying
longs: the crowd is already short, which is when squeezes happen. The long
leg is unchanged.
- **My prior:** a small improvement, if the effect exists. Negative funding
  is not rare, so it will remove a fair share of shorts.

**N3 — Residual (idiosyncratic) momentum.**
- **The idea:** instead of ranking the raw 14-day return, rank the 14-day
  return minus β × the market's 14-day return.
  - The market is the equal-weight mean daily return of the eligible coins.
  - β is each coin's trailing 60-day slope on the market (past only;
    missing → 1).
- **Why:** raw momentum loads on beta. In a rally it shorts the low-beta
  laggards, which then catch up. Residual momentum is known in equities to
  crash less.
- Everything else, including both legs, is as C2.
- **My prior:** the most principled of the three. Crypto's single strong
  factor makes beta matter.

## Admission (each test, on the daily difference Δ = N − base)

- Newey-West t(Δ) ≥ **2.13** (one-sided 5%, Bonferroni for 3 tests);
- ≥ 3 of 4 equal time quarters with mean Δ > 0;
- mean Δ > 0 over the holdout 2025-01-01 → 2026-08-31;
- N's max drawdown no more than 2 points worse than the base's.

**Also reported:**
- each variant's months ≥ +2%, worst month and max drawdown;
- the base's C2 long leg and short leg measured separately (their own P&L),
  so the question "does the short leg pay?" is answered directly, whatever
  the tests conclude.

Nothing is tuned after seeing a result: 14 days, the fifth, 7-day funding,
the 0 threshold and 60 days are fixed here. A fail is recorded as a fail.
