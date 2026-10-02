# Round 16 (C525) pre-registration: more automatable avenues

Committed and pushed **before** the tests below run. 3 Oct 2026 (01:55 IST).

The operator asked again for ways, trading or not, that a bot could run to earn
2–4% a month. Round 15 found one on paper: Delta Exchange India's funding
differs persistently from Binance's (`C524CrossVenue`). This round asks whether
the same mechanism exists elsewhere, and checks one more Indian-retail premium.

Probed first (public APIs, from this sandbox, 3 Oct 01:50 IST):
- **CoinDCX futures ("B-" instruments):** funding identical to Binance's on 339
  of 542 coins (median difference 0). They mirror Binance, so there is nothing
  to collect. Not tested further.
- **Pi42 (INR perps):** market data refuses this sandbox (403). Untested; the
  operator's server may reach it later.
- **Bybit:** refuses this region. Not tested.
- **Hyperliquid** (on-chain perps, no KYC, hourly funding): reachable, with
  full funding history. Median gap to Binance now 0, but 20 of 168 shared
  coins differ by ≥ 20%/yr.
- **Delta India options and Deribit:** reachable.

## H1 — Binance vs Hyperliquid funding spread (tested on history)

The **same rule as round 15's X1**, unchanged:
- s = trailing 7-day mean of (Hyperliquid − Binance) daily funding,
  annualised, as paid by a long;
- enter at |s| ≥ 20%/yr, shorting the perp where longs pay more and buying it
  on the other venue;
- exit at |s| < 10%/yr or a sign change;
- at most 10 pairs, 10% of capital per leg;
- decided on day t's data, earning day t+1.

Costs per leg, in and out: Binance 0.05% + 0.02%; Hyperliquid taker 0.045%
(base tier) + 0.02%.

Data: every coin listed on both, 2024-10-01 → 2026-09-30 (or from the first
day both list it); Hyperliquid `fundingHistory` (hourly) and daily candles,
Binance settled funding and daily closes.

**Bar (a paper ledger), the same as X1's:** net HAC t ≥ 2, ≥ 3 of 4
half-years positive, the last 6 months positive. Reported with the same
stress checks:
- the midnight payment credited to the day before;
- costs ×5 and ×10;
- identity (return correlation ≥ 0.9);
- all at once.

Expectation, stated now: smaller than X1, because global arbitrageurs can reach
both venues.

## D1 — Delta India options vs Deribit (descriptive only)

Indian retail is long Delta's perpetuals (X1). Is it also overpaying for
options? At matched expiries and strikes near the money, Delta's mark implied
volatility vs Deribit's, BTC and ETH, now. Descriptive: no history is available
to test a trade. If Delta is consistently richer, selling Delta options hedged
on Binance becomes a round-17 candidate, pre-registered then.

## Also (descriptive)

Current yields, sourced, for avenues not covered in rounds 13 and 15, which a
bot could automate. Includes Hyperliquid's HLP vault (market-making yield).
