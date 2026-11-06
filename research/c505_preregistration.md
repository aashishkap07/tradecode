# C505 pre-registration: round 9 — chaos theory, information theory, control theory
Written 2026-09-28, BEFORE any data for these tests was computed.

The operator asked for ideas from other fields (quantum physics, advanced
mathematics, calculus, probability, chaos theory, logic) to be explored and
built in where they help. Round 7 (C500) tested the Markov regime,
superposition of horizons, Ichimoku and allostasis. This round takes three
more fields and turns each into one precise, testable change to the running
book. My own reasoning on each is written first, so it cannot be fitted to the
result afterwards.

## The base: what runs (COMBO-C, crypto only)

Identical to C500:
- `research/omega_c488_research.py` with `R.EXCLUDE ∪ TRADFI`, top 20;
- C1/C2/C3 as `omega_c500_research.py` builds them, combined by `R.combine`
  at target vol 20% (dial 15%), gross cap 3×;
- $6 floor at $250, cost 0.08% per unit turnover, funding charged;
- Binance USDT-M archive, 2020 → 2026-08.

## The three tests (each changes ONE thing)

**L1 — Chaos theory: trend only where the coin's own path is persistent.**
- **The reasoning:** a trend rule earns only when a coin's returns are
  persistent (Hurst exponent H > 0.5). A random walk (H = 0.5) or an
  anti-persistent, mean-reverting path (H < 0.5) turns a trend rule into
  paying fees. The variance ratio is the statistically stable way to read H
  on short data:
  - VR = var(7-day returns) / (7 × var(1-day returns)), over the trailing
    120 days, per coin;
  - VR > 1 ⇔ H > 0.5.
- **Rule:** C1's weight for a coin is kept when its VR > 1 and halved when
  VR ≤ 1. Past data only. Everything else is unchanged.
- **My prior:** a small gain at best. The 4-horizon trend signal already
  requires agreement across horizons, which is itself a persistence filter.

**L2 — Information theory: momentum ranks carry information only when the
cross-section is spread out.**
- **The reasoning:** when all 20 coins have moved alike over 14 days, their
  momentum ranks are ordering noise (low entropy of the signal, little
  information per rank). When returns are widely dispersed, ranks separate
  real winners from losers.
- **Measure:** D = the cross-sectional standard deviation of the eligible
  coins' 14-day returns, relative to its own trailing 180-day median.
- **Rule:** C2's weights are multiplied by clip(D / median, 0.5, 1.5). Past
  data only.
- **My prior:** plausible. In equities, momentum is known to be stronger in
  high-dispersion markets, but crypto's cross-section is dominated by one
  factor.

**L3 — Control theory / calculus: a drawdown feedback on the whole book.**
- **The reasoning:** the vol target is a feed-forward controller (it sizes
  from the estimated risk). It has no feedback from the result: in a losing
  streak it keeps the same size. A proportional controller on the drawdown is
  the other half of a two-loop controller. The derivative of equity feeds
  back on size, as in constant-proportion portfolio insurance.
- **Rule:** the book's weights at day i are multiplied by
  f_i = clip(1 − DD_i / 0.25, 0.25, 1). DD_i is the controlled book's own
  drawdown from its running peak, through day i (past only; computed day by
  day, with the extra turnover from changing f charged at 0.08%).
- **My prior:** a smaller drawdown and a smaller return. Feedback controllers
  cut exposure after losses, and in trend-following the rebound often comes
  right after. Likely to fail the return bar. Reported for its effect on the
  probability of a losing month.

**Admission (each test, on the daily difference Δ = L − base):**
- Newey-West t(Δ) ≥ **2.13** (one-sided 5%, Bonferroni for 3 tests);
- ≥ 3 of 4 equal time quarters with mean Δ > 0;
- mean Δ > 0 over the holdout 2025-01-01 → 2026-08-31;
- L's max drawdown no more than 2 points worse than the base's.

**Also reported for each** (descriptive, not a bar): the share of months
≥ +2% and ≥ 0, the worst month.

All three are reported in full whatever the outcome. Nothing is tuned after
seeing a result: the 120 days, 7 days, the halving, 14 days, 180 days, the
0.5–1.5 clip, 0.25 and the 0.25 floor are fixed here. A fail is recorded as a
fail.

## Considered and not tested, with the reasoning

- **Random-matrix theory / the effective number of bets:** the vol target
  already measures the book's real volatility, correlations included, so
  scaling by an "effective N" would count the same thing twice.
- **Kelly / ergodicity (time average vs ensemble average):** not a rule to
  admit but a question about the dial. It is measured in
  `research/c504_target_probability.py`: at which dial the long-run growth
  of one account peaks.
- **Quantum superposition / measurement:** tested at C500 (K2, the horizon
  ensemble, not admitted). The Zeno point, that watching too often destroys
  the edge, is why the book trades daily.
