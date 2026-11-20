# C510 pre-registration: round 11, the idle scanner's information as a sensor
Written 2026-09-29, BEFORE any data for these tests was computed.

## Why this round

The operator asked whether the disabled intraday scanner could be modified and
integrated with the book.

As a **trader** it cannot. Its record, the C487 audit and the C489 research
all agree: at 15-minute to 4-hour horizons the predictable move per trade is
5–9× smaller than the fee and spread per trade. No tuning of entry rules can
fix a cost structure.

What intraday data *can* do is **measure risk better**. The book sizes every
coin by its volatility, `sc = clip(0.02 / sd, 0, 1)`, where `sd` is the
30-day standard deviation of daily close-to-close returns. That estimate
ignores everything that happened inside each day.

A day's **high and low** carry the intraday path's extremes. Range-based
estimators use them:
- Parkinson (1980): σ² = (ln H/L)² / (4 ln 2);
- Garman–Klass (1980): σ² = ½(ln H/L)² − (2 ln 2 − 1)(ln C/O)².

For a random walk these are about 5 and 7 times as efficient as close-to-close
returns. That means the same accuracy from far fewer days, so the estimate
can react faster without getting noisier.

The scanner's hourly history does not exist for 2020–26. The daily high and
low do: they are in the research archive (Binance daily klines) and in the
Bitget candles the bot already downloads. So the test uses them.

## The base

Identical to C507:
- crypto only, top 20;
- C1/C2/C3 combined at target vol 20% (dial 15%), gross cap 3×;
- $6 floor at $250, cost 0.08% of turnover, funding charged;
- the Binance archive, 2020 → 2026-08.

## The two tests (each changes ONLY the per-coin sd inside sc; the combiner is unchanged)

- **V1, Parkinson, EWMA:** sd² = the exponentially weighted mean of
  (ln H/L)² / (4 ln 2), with a half-life of 10 days, past and today only (the
  day's range is known at its close, the same moment the base's sd uses that
  day's return). It needs at least 20 days of ranges; otherwise the base's sd
  is used.
- **V2, Garman–Klass, EWMA:** the same, with
  ½(ln H/L)² − (2 ln 2 − 1)(ln C/O)², floored at 0 per day.

**My prior:** a small gain at most. The combiner already re-targets the whole
book's volatility, so a better per-coin estimate mostly improves the balance
between coins. The likely benefit is in the tail: faster reaction when one
coin's volatility explodes (a squeeze like PUMP's).

## Admission (each test, on the daily difference Δ = V − base)

- Newey-West t(Δ) ≥ **1.96** (one-sided 5%, Bonferroni for 2 tests);
- ≥ 3 of 4 equal time quarters with mean Δ > 0;
- mean Δ > 0 over the holdout 2025-01-01 → 2026-08-31;
- V's max drawdown no more than 2 points worse than the base's.

**Also reported:** months ≥ +2%, worst month, max drawdown, and the worst
single day.

## Descriptive only (NOT an admission test, stated before any number is seen)

The operator has asked for round 10's N2 (no crowded shorts) and N3 (residual
momentum) to run in the bot now, as a forward test. So the combinations are
reported as they are, for information:
- N2+N3 together;
- N2+N3 with K4 sizing;
- each at dial 15% and 20%;
- the probability of a year averaging ≥ +2%/month (the C504 method: a
  30-day block bootstrap, and a ⅓ haircut);
- returns by calendar year: 2020–21 bull, 2022 bear, 2023 recovery, 2024–26.

These were chosen *after* seeing their parts, so they cannot be admitted on
this data. Their evidence has to come from forward data. The bot will collect
it from today, by scoring every variant on the same inputs each day.

Nothing is tuned after seeing a result. The half-life of 10 days, the 20-day
minimum, and the estimators are fixed here. A fail is recorded as a fail.
