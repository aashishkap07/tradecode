# C500 pre-registration: round 7 — ideas from other fields, and what else Bitget pays
Written 2026-09-28, BEFORE any data for these tests was computed.

The operator asked, after the book's first three days (−3.4% marked, driven
by WLD and PUMP shorts squeezing while PEPE/UNI longs fell), whether the
strategies are right, for novel ideas from physics, logic, probability,
Markov chains, Ichimoku and biology, and whether anything else on Bitget can
pay 2–4% a month. Four modifications of the running book are tested, and two
things are measured (descriptive, not admitted/rejected).

## The base: what runs (COMBO-C, crypto only)

`research/omega_c488_research.py` with `R.EXCLUDE ∪ TRADFI` (C493), **top
20** (`R.TOPN = 20`), sleeves C1/C2/C3 exactly as `crypto_sleeves`,
combined by `R.combine` at **target vol 20%** (dial 15%), gross cap 3×,
positions under $6 at $250 dropped (as `c493_target_probability.py`), cost
0.08% per unit turnover, funding charged. Binance USDT-M archive, 2020-01 →
2026-08 (the research's own data).

## The four tests (each changes ONE thing; everything else identical)

**K1 — Momentum-crash guard (Markov regime; the "wavefunction collapse" of a
crowded trade).** Cross-sectional momentum is known to crash when a falling
market rebounds and last month's losers (the short leg) rally hardest
(Daniel & Moskowitz 2016, equities). Market = equal-weight mean daily return
of the eligible coins. State "rebound risk" on day i if the market's
trailing 30-day return (days i−29..i) is < 0 AND its trailing 10-day
volatility is above the median of its own trailing 10-day volatility over
days i−179..i. In that state the C2 weights are multiplied by 0.5 (both
legs); otherwise unchanged. Past data only.

**K2 — Superposition of horizons (ensemble).** Instead of one lookback, the
signal is the average of several: C2 = mean of `xs_rank` of 7-, 14- and
28-day returns; C3 = mean of `−xs_rank` of 3-, 7- and 14-day summed
funding. Same scaling (`sc / (2 N 0.2)`), same weekly hold.

**K3 — Ichimoku trend.** C1's signal (mean sign of 7/14/28/56-day returns)
is replaced by the daily Ichimoku cloud position. The research data has
closes only, so highs and lows are the rolling max and min of closes
(stated, not hidden). Tenkan = mid of 9 days; Kijun = mid of 26; Span A =
(Tenkan + Kijun)/2; Span B = mid of 52; the cloud at day i is the spans
computed at day i−26. Signal +1 if the close is above both spans, −1 if
below both, 0 inside. Same banding and scaling as C1.

**K4 — Allostatic volatility (biology: the body adjusts its set point
before the stress peaks).** In `combine`, both vol estimates (each sleeve's
and the combined book's) use an **EWMA with a 10-day half-life** instead of
a flat 60-day window. The same warm-up length (120 days), target, cap and
lag.

**Admission (each test, on the daily difference D = K − base):**
- Newey-West t(D) ≥ **2.24** (one-sided 5%, Bonferroni for 4 tests);
- ≥ 3 of 4 equal time quarters with mean D > 0;
- mean D > 0 over the **holdout 2025-01-01 → 2026-08-31**;
- K's max drawdown no more than 2 points worse than the base's.

All four are reported in full whatever the outcome. Nothing is tuned after
seeing a result. A fail is recorded as a fail.

## Two measurements (descriptive only)

**M1 — The book's first three days in context.** On the base's daily
returns: how often a 3-day loss of ≥ 3.4% occurred, and the distribution
of the following 30 days' return after such losses.

**M2 — The option-selling premium ("dual investment" / "shark fin").**
Bitget's dual investment pays a fixed yield for agreeing to buy BTC lower
(or sell it higher): it is a short option. Its long-run value to the seller
is the volatility risk premium, implied minus realised volatility, less
Bitget's cut. Measure it: Deribit's BTC implied-volatility index (DVOL,
public API, daily) against the realised volatility of the following 30
days from Bitget's BTC daily closes. Report the mean premium, how often
realised exceeded implied, and the worst 30-day outcomes. If Deribit is not
reachable from here, say so (Standing Rule 17) and reason from the
mechanics only.
