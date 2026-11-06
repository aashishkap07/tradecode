# C496 pre-registration: round 6 — what round 5 left out
Written 2026-09-26, BEFORE any data for these three tests was fetched or computed.

The operator asked whether anything was missed: every futures asset a normal
Bitget account can trade, the methods experienced traders and popular bots
use, and self-adjusting loops. Round 5 covered crypto factors. This round
covers the three gaps that can be tested honestly.

## What a normal Bitget account can trade (checked on the live API, 26 Sep 2026)

- **805 USDT-M perpetuals** (466 crypto, 339 real-world assets: stocks, ETFs,
  metals, energy, indices) and **49 USDC-M perpetuals** (duplicates of USDT-M
  underlyings).
- **No delivery (quarterly) futures on any product line**, so a futures-only
  calendar-basis trade is impossible on this account.
- **The real-world-asset funding history is 90 days deep** (28 Jun → 26 Sep
  2026). Oil longs were paid about 28–34%/yr; gold and silver longs paid
  about 8–10%/yr. A carry test on 90 days has no power (t ≈ 0.5 even at
  Sharpe 1), so it is **not tested** (Standing Rule 17). The oil figure is
  most likely the price of the underlying futures roll, not free money.

## W1 — THE WEEKEND CLOCK (Bitget stock/ETF/commodity perps)

**Idea.** A stock perp trades 24/7 while its underlying market is closed from
Friday's close to Monday's open. Over the weekend the perp is priced by
crypto traders alone: last weekend MSTR's perp did $76M of volume. On Monday
the real market reopens and the perp is pulled to it. If the weekend move is
*incomplete price discovery*, it continues into Monday. If it is *thin-market
overreaction*, it reverses. Either one would be an edge, and only one
round trip a week is needed.

**Data.** Bitget hourly candles for every RWA perp (history-candles, to the
oldest available, about Aug 2025), every weekend with a full set of hours.
Contracts on a 24/7 underlying are excluded (crypto proxies such as PAXG and
XAUT that trade on-chain all weekend are still included, because the rule is
the same for all).

**Measurement, per contract and weekend.**
- F = the close of the Friday **21:00 UTC** hour (after every US cash and
  Globex close, in summer and winter time).
- S = the close of the Sunday **22:00 UTC** hour (before Globex reopens at
  22:00/23:00).
- M = the close of the Monday **15:00 UTC** hour (after the US cash open in
  both summer and winter time).
- Weekend drift D = ln(S/F); Monday move R = ln(M/S).

**The test, with a split fixed now.**
- **Discovery half:** weekends up to 2026-02-28. The sign of the pooled slope
  of R on D, and nothing else, is taken from it.
- **Holdout half:** weekends from 2026-03-01. The rule trades sign(slope) ×
  sign(D) at S, equal weight across all contracts that weekend (gross 1),
  exits at M, and pays 0.16% (taker in and out). Funding over those 17 hours
  is charged at 0.02% adverse (about 10%/yr), since its history is too
  short.
- **Admitted only if the holdout** weekly series has NW t ≥ 2.0, positive
  mean net of costs, and ≥ 3 of 4 quarters positive.
- The discovery half's own slope, t and net result are reported, but never
  used to admit.

## G1 — A POPULAR RETAIL BOT: THE NEUTRAL FUTURES GRID

**Idea.** Grid bots (Bitget sells them in-app) are the most common
"automated profit" retail method. A grid buys every step down and sells every
step up inside a range. It wins steadily in ranges and loses when the price
trends out of the range.

**Rule (a typical Bitget-style setting, fixed now).**
- Each calendar month, for each coin in that month's C494 1-minute set
  (Binance 1m, 2024-09 → 2026-08): a range of **±15% around the month's first
  price**, **20 equal steps**.
- One unit of notional per step (1/20 of the coin's allocation).
- **Neutral:** the grid starts flat; it sells a unit at each step crossed
  upward and buys one at each step crossed downward, inside the range.
- **Fees:** maker 0.02% per fill. Funding is ignored (it favours neither side
  on average).
- **At month end, or when the range is left:** stop trading and hold the
  inventory to month end, then close at taker 0.08%.
- P&L per coin-month in units of the allocation; the average over coins is
  the grid's monthly return.

**Reported:** mean monthly return, % of months positive, worst month, t.
**Admitted only on the round-5 bar** (NW t ≥ 2.45, ≥ 3/4 quarters, positive,
positive 2024+). The expectation, declared: many small winning months and a
few large losses, net ≈ 0 or below. A grid is structurally the opposite of
the C1 trend sleeve, which earns +11%/yr.

## D1 — A DRAWDOWN-CONTROL LOOP (homeostasis on the equity curve)

**Idea.** A self-adjusting loop that cuts risk as the book falls from its
peak and restores it as it recovers (CPPI-like). It is the physiological
analogue of fatigue protecting the system.

**Rule.**
- Each day, multiply the COMBO-C weights by
  m = clip(1 − dd / 0.30, 0.25, 1), where dd is the book's drawdown from its
  running peak through the decision day.
- Crypto only, top 40, dial 15%, as in C493.
- **Test:** the difference series D1 − COMBO-C.
- **Admitted only if** the difference has NW t ≥ 2.0 and ≥ 3/4 quarters
  positive, AND the maximum drawdown is lower.
- **Declared expectation:** round 5 (N6) found the sleeves' returns
  mean-revert over weeks, so cutting after losses is expected to hurt returns
  more than it saves in drawdown.

## Not tested, and why

- **Martingale / doubling-down bots:** by the optional-stopping theorem the
  expected value of any betting system on a fair game is zero before costs.
  Doubling down only trades a high win rate for rare, account-ending losses.
  No data can make that an edge.
- **DCA bots:** DCA is a way of buying, not an edge. Its expected return is
  the asset's own drift.
- **Copy-trading "top traders":** round 5 measured Binance's top accounts in
  aggregate (N4b) as a **losing** signal (−8.1%/yr, t −2.35).
