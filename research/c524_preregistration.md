# Round 15 (C524) pre-registration: the intraday shadow's risk weighting, a cross-venue funding spread, and a ledger audit

Committed and pushed **before** any of the tests below are run. 2 Oct 2026.

Context: on 1–2 Oct the intraday shadow (C489 M1, paper only) lost 7–10% on
the 24-hour-volume universe and, after C522 put it back on the research's
universe, 0.56% in one hour from a single coin (short 龙虾 at 4.7% weight,
+12.6% in the hour). The model weights every coin in a cohort equally
(0.5/n per side), with no volatility scaling, so one coin moving 10–30% in an
hour dominates it. The operator asked for that weakness to be fixed (tested
first), for other logical discrepancies to be fixed, and for research into
other ways (not necessarily trading) to earn 2–4% a month with a bot like this.

## Part A — the intraday shadow's weighting (tested on history)

Data: Binance USDⓈ-M 1-hour klines with taker-buy volume (data.binance.vision,
2021-01 → 2026-08), the coins ever in the research universe (C488 rule, top
40 by 30-day median quote volume, 90+ days listed: 295 coins), real funding
events from the C488 daily archive. Engine: `research/omega_c489_research.py`
unchanged (features, walk-forward logistic retrained every 30 days on 180
days, quintile cohorts, 4-hour overlap, 0.08% per unit of turnover, real
funding). Out of sample from 2021-07-01, as before.

Variants (each uses M1's out-of-sample probabilities P, unchanged):
- **M1 (control):** equal weight, 0.5/n per side.
- **M1v (inverse volatility):** on each side w_i = 0.5 × (1/σ_i) / Σ_side(1/σ_j),
  σ_i = standard deviation of the coin's hourly returns over the last 168
  hours (at least 120 valid; otherwise the side's median σ). This is the book's
  own principle (each coin in its own volatility units).
- **M1x (volatility filter):** equal weight, but a coin whose σ_i exceeds 3× the
  cross-sectional median σ of the eligible coins that hour is left out of the
  cohort.

Measures, out of sample: hourly P&L standard deviation, worst hour, worst day,
99.9th percentile of |hourly P&L|, excess kurtosis; net %/yr, Sharpe, the
Ledoit–Wolf HAC Sharpe difference vs M1; the gross (before cost) Sharpe; by
year.

**Admission bar (as the shadow's forward ledger, NOT for trading):** a variant
replaces nothing; it is ADDED to the shadow as a third ledger if
(1) its hourly P&L standard deviation is ≤ 0.8 × M1's, and
(2) its worst day is better than M1's, and
(3) its Sharpe difference vs M1 is ≥ 0 (point estimate).
If both pass, the one with the lower hourly standard deviation is added. A
trading candidate still needs the project's bar (net t ≥ 2, ≥ 3/4 quarters,
holdout positive), which round 4's evidence (costs of 100–270%/yr) says no
weighting can meet; that is reported, not assumed.

Descriptive only (not part of the bar): both variants replayed with the bot's
own code on Binance's real candles for 1–2 Oct 2026 (the 龙虾 hours).

## Part B — a cross-venue funding spread, Delta Exchange India vs Binance (tested on history)

Round 14 D found Delta's funding is a median +5.7%/yr dearer than Binance's
for a long, ranging −60% to +50% by coin (C523-corrected). If the spread per
coin persists, a position that is long the perp on the cheaper venue and
short it on the dearer one (no market direction) collects the difference.

- **Data:** every crypto perp listed on both venues (Delta: crypto only, as
  C521), daily over 2024-10-01 → 2026-09-30 where both venues have it. Delta:
  FUNDING:<SYM> hourly records at each exchange (the value set at T, C523) and
  daily closes; Binance: settled funding history and daily closes.
- **Signal (decided on day t's data, earning day t+1):** s = trailing 7-day
  mean of (Delta funding − Binance funding), annualised, as paid by a long.
- **Rule:** enter when |s| ≥ 20%/yr: short the perp on the venue where longs
  pay more, long it on the other, equal notional. Exit when |s| < 10%/yr or s
  changes sign. At most 10 pairs, each 10% of capital per leg.
- **P&L per pair per day:** the funding received net (short venue's rate −
  long venue's rate) + the price difference (long leg's daily return − short
  leg's), minus costs on entry and exit of both legs: Binance 0.05% + 0.02%
  half-spread, Delta 0.05% × 1.18 GST + 0.02% half-spread.
- **Bar for a paper ledger:** net HAC t ≥ 2 over the whole window, ≥ 3 of 4
  half-years positive, and the last 6 months (2026-04 → 2026-09) positive.
  Reported with the return on capital at 2× gross per venue, the worst month,
  and the capacity (the median daily volume of the coins it picks on Delta).

## Part C — a ledger audit (specification corrections, no performance test)

Each paper ledger's rules are checked against its own research specification
and against the exchanges' real behaviour. Found before this pre-registration
(fixes follow, each with a unit test):

1. **C489 shadow funding.** The research charged each coin's real settlement
   events. The bot charges funding only when the hour is 00/08/16 UTC, at the
   live (predicted) rate. Binance settles about 470 coins every 4 hours and
   some every hour, so half of their payments are missed. Fix: charge the
   settled events of the hour from the funding history.
2. **C489 funding history goes stale.** It is fetched once per coin (and on
   restart), never refreshed, so the `fundz` feature drifts from the
   research's. Fix: one bulk Binance call per hour for all coins' new
   settlements.
3. **C489 costs.** 0.08% per turnover is Bitget's taker 0.06% + 0.02%; on
   Binance it is 0.05% + 0.02% = 0.07%, as the carry ledger already uses.
   The gate's "beats the round trip" threshold follows the same cost.
4. **C489 model freshness.** The research retrained every 30 days on 180
   days; the shadow runs one frozen fit (to Aug 2026). Not changed in the bot
   (it caches 42 days of candles); the monthly review re-fits it with the
   research engine and commits the new `c489_model.json`.
5. **The book's candidate list** is the top 80 by 24-hour volume, then the
   research rule (30-day median volume, 90+ days) picks the top 20 inside
   it. Checked on the daily archive: how often would the research rule over
   ALL coins pick a coin outside that 80? If ever, the candidate width is
   raised.

Checked and found correct (2 Oct): the book's Binance funding against
Binance's settled rates (−$0.01607 vs −$0.01601, all 11 coins within
$0.0001); the carry ledger (research universe, settled events, Binance spot on
Binance); Delta (C523); the spot pot, Savings and BFUSD arithmetic.

## Part D — other ways to 2–4% a month (descriptive research)

Not a test. Every avenue a bot like this could run, trading or not, with its
real current yield (sourced), its risk, its Indian tax treatment where known,
and whether code adds anything. Includes: Simple Earn / BFUSD, BNB HODLer
airdrops and Launchpool, staking, dated-futures basis, cross-venue funding
(Part B), DeFi lending and stablecoin yields, options selling (round 13's
result), P2P lending, and selling compute.
