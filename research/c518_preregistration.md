# C518 pre-registration: round 13, selling crypto volatility as a second income stream
Written 2026-10-01 (01:40 IST), BEFORE any volatility-index data was downloaded or computed.

## Why this round

The operator asked for a fresh, exhaustive look at every way to reach 2–4% a
month with more than 80% probability.

**What the target requires (worked out in the report):**
- A year averaging ≥ 2%/month with 80% probability needs an
  **out-of-sample Sharpe of about 1.8–2.0 at 30–35% volatility**.
- The book's backtest Sharpe is 1.81; after the usual ⅓ haircut it is about
  1.2, which gives 60%.

**The one lever that raises a portfolio's Sharpe without new forecasting
skill:** combining return streams that are positive on their own and weakly
correlated. The combined Sharpe grows with √(number of independent streams).

**The candidate.** The strongest documented second stream in crypto that the
book does not already hold is the **volatility risk premium** (VRP).
- Options are priced for more turbulence than usually arrives: the median
  gap for BTC is about 5.6 volatility points, and implied has been above
  realized about 68% of the time.
- A seller of 30-day volatility collects that premium and loses in sudden
  crashes.
- The book is trend-following, which tends to *gain* in large sustained
  moves, so the two may diversify each other. That is the reason to test it
  rather than assume it.

**Where it could be traded.**
- **Not on Binance:** writing options there needs VIP 1 or $100,000 of
  assets.
- **Delta Exchange India** (FIU-registered, INR-settled) sells BTC/ETH
  options in 0.001 BTC lots, at 0.01% of notional, capped at 3.5% of
  premium.
- The test measures the premium itself; the venue comes after.

## Data

- **Implied:** Deribit's DVOL index (BTC and ETH), daily closes, from the
  first day available to 2026-08-31. DVOL is a model-free 30-day implied
  volatility index, like VIX: its square is the 30-day variance-swap rate.
- **Realized:** daily log returns of Binance's BTCUSDT and ETHUSDT
  perpetuals (the project's archive, the same series the book is measured
  on).

## The stream (fixed now)

A **ladder of short 30-day variance swaps**, one new tranche a day, each
1/30 of the stream. The day's P&L of each live tranche is the realized-variance
accrual:

  **(K_j / 365 − r_t²) × N_j**, with

- K_j = ((DVOL_j − c)/100)², where c = **3 volatility points**: the cost,
  bid/ask and index-to-traded-option gap, fixed now. It is also reported at
  1.5 and 5 as descriptive sensitivity.
- r_t = that day's log return.
- N_j = 1 / (2·√K_j) (vega notional: a tranche earns about one unit per
  volatility point of premium).
- The ladder's daily return is scaled to **20% annualised volatility**,
  using its trailing 60-day realized volatility (a lag of one day, no
  look-ahead), capped at 3× the unit stream.

**Limits of the proxy, stated now.**
- It books realized variance day by day, but not the mark-to-market move in
  implied volatility. So in a crash its drawdown is somewhat **smaller** than
  a real options book's; its total P&L over each tranche's life is exact.
- Delta hedging and discrete options differ from a variance swap. That is
  part of what c = 3 points is meant to absorb.

## Tests

- **V1** BTC, **V2** ETH, **V3** the two combined (equal risk).

**Admission as a candidate second stream, each of V1–V3:**
1. Newey-West t of its net daily return ≥ **2.0**;
2. ≥ 3 of 4 equal time quarters positive;
3. holdout 2025-01-01 → 2026-08-31 positive;
4. **the blend improves the target:** the N2+N3 book at dial 20% (with
   Savings) combined with the stream at equal risk, scaled back to the
   book's own volatility, must
   - raise P(a year averages ≥ 2%/month) under the **⅓ haircut** by
     **≥ 5 points** (the C504 bootstrap, same seed rule), and
   - not worsen the book's max drawdown by more than 2 points.

**Also reported:** each stream's
- annual return, volatility, Sharpe and worst month;
- the worst 30 days (around the May 2021, June 2022 and Nov 2022 crashes);
- correlation with the book, overall and in the book's worst 10% of months.

## What admission would mean

- **Not a trade.** An admitted stream becomes a paper ledger first (as the
  carry ledger did).
- **Live** needs all three of:
  - a venue that lets a retail account write options (Delta Exchange
    India);
  - a CA's view on how INR-settled options are taxed;
  - a separate build.
- Nothing is tuned after the result. The 3-point cost, the 30-day tenor, the
  20% volatility target and the equal-risk blend are fixed here. A fail is
  recorded as a fail.
