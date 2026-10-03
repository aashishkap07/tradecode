# Round 14 (C521): was the research tested correctly, and can the book adjust itself better?

Pre-registered 2 Oct 2026, before any number below is computed. Data: the
Binance USDⓈ-M archive (860 symbols, delisted ones included, 2020-01 →
2026-08-31), crypto only (the research TRADFI list excluded), the N2+N3 book at
dial 20% (vol target 26.7%), top 20, $500, Binance costs (0.07% per unit
turnover), funding as paid. Script: `research/omega_c521_research.py`.

The operator asked for two things: check that the ideas already tested were
judged correctly ("not just on simple data"), and build something that adjusts
itself to market conditions in a principled ("relativistic") way. Part A is the
audit, Part B the new candidates, Part C the mathematics of what the evidence
allows, Part D Delta Exchange India against Binance (for the parallel paper
book).

## Part A — audit of the testing itself

- **A1 survivorship.** The corpus must include delisted coins. Measure the
  book with and without coins whose history ends > 30 days before the end.
  Pass if it includes them (it is then conservative, not flattering).
- **A2 look-ahead.** Code review of the engine (universe on volume through
  the previous day; signals at the close of day i, earning day i+1; scaling on
  past returns only). Empirical check: the book at lag 2 (one more day of
  delay) must degrade gently (keep ≥ 50% of its lag-1 Sharpe), and lag 0
  (deliberate look-ahead) must be far better (shows the test can tell).
- **A3 multiple testing.** Deflated Sharpe Ratio (Bailey & López de Prado
  2014) of the N2+N3 book with N = 60 and N = 120 trials (every variant tested
  in rounds 5–13 is about 60), the trial-Sharpe variance taken from the A4
  grid. Pass if DSR ≥ 0.95. Also the Minimum Track Record Length: how many
  months of forward data confirm Sharpe > 0 at 95%.
- **A4 parameter plateau and overfitting.** A grid of 135 neighbours of the
  chosen design: C2 lookback {7, 10, 14, 21, 28} × C3 funding window {3, 7, 14}
  × trend horizons {(3,7,14,28), (7,14,28,56), (14,28,56,112)} × top {15, 20,
  30}. Report the chosen design's rank and the median neighbour's Sharpe.
  Probability of Backtest Overfitting by CSCV (Bailey, Borwein, López de Prado,
  Zhu 2017), 16 time blocks. Pass if PBO < 0.25 and the median neighbour's
  Sharpe ≥ 70% of the chosen one (a plateau, not a spike).
- **A5 risk-matched re-test of the ideas judged on raw return.** Earlier rounds
  compared risk-REDUCING ideas by their return difference, which penalises
  them for carrying less risk. Re-test at equal risk: K4 (EWMA vol, 10-day
  half-life), GK (range-based vol), D1 (drawdown loop: risk × clip(1 − DD/30%,
  0.25, 1)). Test: the Sharpe difference against the base by the HAC test of
  Ledoit & Wolf (2008), and returns at matched volatility (each scaled to the
  base's full-sample vol). **Admission bar (unchanged in spirit):** one-sided
  p < 0.05 on the Sharpe difference, Sharpe difference > 0 in ≥ 3 of 4
  quarters and in the holdout (2025-01 → 2026-08), and max drawdown at matched
  vol not worse than the base's by more than 2 points.

## Part B — new candidates that adjust to the market (same bar as A5)

- **B1 proper-time momentum (a volatility clock).** Markets do not run on the
  calendar: a day of 8% moves carries more information than a day of 1%
  (subordination: Clark 1973; Ané & Geman 2000). Define the market's clock
  increment dτ_t = m²_t / mean(m² over the past 365 days), clipped to
  [0.25, 4], where m²_t is the mean squared return of the eligible coins that
  day. A horizon of H "proper days" is the fewest calendar days whose dτ sum
  reaches H. C1's horizons (7, 14, 28, 56) and C2's 14 are measured on this
  clock; C3 stays on the calendar (funding is paid by the clock on the wall).
  Fast markets shorten the lookbacks, quiet markets lengthen them.
- **B2 ex-ante risk (the book's risk in today's frame).** The base scales the
  book by the realised volatility of its last 60 days, which describes the
  book it used to hold. B2 scales by the forecast volatility of the book it
  holds now: σ_p = √(wᵀΣw), Σ = D·C·D with D the coins' EWMA volatility
  (10-day half-life) and C the EWMA correlation (30-day half-life) shrunk 50%
  to its average (Ledoit–Wolf constant-correlation target). The sleeves keep
  equal risk as now; only the overall scale changes.

Nothing in Part B is admitted unless it passes the A5 bar. A candidate that
misses the bar but has the better tail at equal risk goes to the forward rule
tournament (scored, not traded), as K4 and range vol did.

## Part C — what the mathematics allows (descriptive)

- The Kelly fraction implied by the book's Sharpe (backtest and with the
  ⅓ haircut) and where dial 20% sits as a fraction of Kelly.
- Minimum Track Record Length for the paper book (from A3).

## Part D — Delta Exchange India against Binance (descriptive, for the paper book)

- **D1 prices:** daily returns of the coins both venues list, Delta vs
  Binance, over Delta's available history: correlation and tracking error.
- **D2 funding:** Delta's 8-hour funding against Binance's, per coin: the mean
  difference (does the carry sleeve transfer?).
- **D3 contract sizes:** the share of the book's recent plans that Delta's
  contracts can hold at $500, $1,000 and $2,000.

Delta is a candidate venue, not a strategy change: its paper book trades the
same plan, so D1–D3 measure what moving there would cost.
