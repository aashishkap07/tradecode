# C501 pre-registration: round 8 — a second $250 in spot, and the paper forward tests
Written 2026-09-28, BEFORE any data for S1 was computed.

The operator asked for an additional 250 USDT in spot trading with BGB fee
discounts, for the allostatic-volatility idea (K4) and idle cash in Savings
to be integrated now so testing can begin, and for self-adjusting relative
logic.

## S1 — Spot trend, long or flat, cash earning Savings (the second $250)

**Why spot, with our own reasoning.** A long position in a perpetual pays
funding. Across our research period longs paid about 10%/yr on average, and
more when the crowd is long (19 of 37 top coins were above 10%/yr on 28 Sep).
A spot holding pays no funding. So a strategy that is only ever long belongs
in spot, and its idle cash can earn Savings. Spot cannot short, and it has no
leverage, so the strategy must be long-or-flat.

**Rule.** It is written in the book's own relative units, so every coin is
measured against its own volatility.
- **Universe:** the book's research universe. Crypto only (C493 exclusions),
  top 20 by 30-day median quote volume, at least 90 days old.
- **Signal:** C1's trend score, s = mean sign of the 7/14/28/56-day returns.
- **Weights:** long weight ∝ max(s, 0) × min(1, 0.02 / 30-day daily sd) / 20;
  flat when s ≤ 0; banded as C1 (30%).
- **Self-adjusting size:** the whole long book is scaled to a **20% annual
  volatility** set point, using the trailing 60-day vol of its own unit
  returns (past only). **Gross is capped at 1.0** (spot has no leverage).
- **Cash:** 1 − gross, earning **5% a year**. That is deliberately below the
  7.63% Flexible Savings APR of 28 Sep, because rates move.
- **Costs:** **0.10% per unit of turnover**: spot taker 0.08% with the BGB
  discount, plus 0.02% half-spread. No funding.
- **Floor:** positions under $6 at $250 are dropped.
- **Data:** the research's Binance archive, 2020-05 → 2026-08. Perpetual
  closes stand in for spot closes (the basis is small at daily frequency;
  stated, not hidden).

**Admitted as the second pot's strategy only if** (daily excess return over
the 5% cash rate):
- Newey-West t ≥ **2.0**;
- ≥ 3 of 4 equal time quarters positive;
- holdout **2025-01-01 → 2026-08-31** mean excess > 0;
- max drawdown ≤ 35%.

**Reported, not admitted:**
- buy-and-hold BTC;
- equal-weight top-20, rebalanced monthly (long only, no trend);
- the monthly return distribution;
- the correlation with the futures book (COMBO-C, dial 15%);
- the two pots combined ($250 + $250).

If S1 fails, it is not put in the bot. The report then says where the second
$250 is better placed.

## Forward paper tests (no admission now; they measure, and never trade)

- **F1: the allostatic shadow book (K4).** At each C488 rebalance the bot
  also computes the book with EWMA volatility (10-day half-life) from the same
  data, and keeps a daily-marked paper ledger of it. Its purpose is an
  implementation check and live evidence for the December re-test (pending
  #11), where K4 must pass on new data before it may replace the running
  sizing.
- **F2: idle cash in Savings.** A paper ledger of what the main account's
  idle cash would earn. Reserve = locked margin + the dial's monthly budget
  (dial% × equity) + 5% buffer, re-computed hourly. It is self-adjusting: more
  margin or a higher dial keeps more in futures. Interest = idle × APR / 8760
  per hour at the configured APR (7.63% on 28 Sep). It is shown beside the
  account and does not change the book's equity, sizing or guard.
