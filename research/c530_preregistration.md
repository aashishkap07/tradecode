# Round 17 (C530) pre-registration: the cross-venue trade's sizing and each venue's risk

Committed and pushed **before** the tests below run. 4 Oct 2026, 14:30 IST.

## Why

The cross-venue paper ledger (C524, round 15's X1) holds 10 pairs, each leg
a fixed 10% of its equity. Live, it is **two accounts**: half the capital
on Delta (the short legs), half on Binance (the long legs). Money does not
move between them by itself.

On 4 Oct, AIN rose from $0.0242 at entry (2 Oct 20:12 UTC) to $0.0536, a
gain of 122%:
- the pair itself was flat (−$0.13);
- the Delta side fell to **60% of its $250** by 11:33 IST, at 4.05×
  leverage (C529's margin watch warned).

A fixed 10% leg ignores each coin's own volatility. The book sizes every
coin in its own volatility units; this trade does not. That is the
operator's "everything relative" principle not applied.

## D (descriptive, no bar): each venue's risk under X1 as tested

Data: round 15's "ALL harder" set (the midnight payment to the day before,
Delta's mark, costs ×5, coins with $100k of Delta turnover, the same asset
on both), 2024-10 → 2026-09.

- **Each side:** each venue's equity = half the capital + its own legs'
  P&L (price, funding, its own costs) since the last re-balancing between
  the venues. A re-balance is assumed on the 1st of each month.
- **Report:**
  - the lowest side ratio (side equity ÷ its half) in each month: median,
    worst;
  - the share of months in which a side fell below 65% and below 50%.
- **Note:** daily closes understate intraday spikes (AIN rose 20% within
  hours on 4 Oct).

## H1: X1v, legs scaled by each coin's own volatility

Identical to X1 (entry |s| ≥ 20%/yr, exit < 10% or a sign change, at most
10 pairs, costs), except the size of a new pair's legs:

    leg = 10% × equity × min(1, σ_med / σ_c)

- σ_c = the coin's 30-day standard deviation of daily Binance returns, on
  the entry day;
- σ_med = the median σ of the coins with |s| ≥ 20% that day;
- sizes are fixed at entry, as in X1.

**Bar.** X1v replaces X1 in the ledger only if **all** of these hold:
- (a) the worst month's lowest side ratio improves by ≥ 10 points, **or**
  the share of months with a side below 50% at least halves;
- (b) X1v's net return is ≥ 70% of X1's;
- (c) X1v's net HAC t ≥ 2 and ≥ 3 of 4 half-years are positive.

Otherwise X1's sizing stays, and the risk is handled by the C529 margin
watch and the reserve.

## Also decided now (not a test): the operator's new allocation

- **The cross-venue ledger is rebased from $500 to $250.** Every position
  and figure is scaled ×0.5, as if it had begun with $250; Delta legs are
  rounded to whole contracts and the Binance legs re-matched. Its
  percentages and record are unchanged.
- **A Pendle fixed-yield paper ledger, at most $100.**
  - **Universe:** active stablecoin markets on Ethereum or Arbitrum, issued
    by an established protocol (Ethena, Sky, Liquity, Agora, Spark, Aave,
    Frax), or flagged "prime" by Pendle.
  - **Filters:** liquidity ≥ $3M, 21–200 days to expiry.
  - **Choice:** the highest implied APY.
  - **Holding:** held to maturity, then rolled into the best market then.
  - **Value:** PT price = (1 + implied APY)^(−days/365); marked daily from
    the market's current implied APY.
  - **Costs:** the market's fee rate × years to expiry, + 0.05% slippage,
    + gas ($1 on Ethereum, $0.05 on Arbitrum), in and at each roll.
  - **Tax:** as a VDA (31.2% of the gain).
  - **Stated now:** on 4 Oct the qualifying markets pay **5.1–5.4%**,
    which is **below Binance Savings (6.66%)**.
