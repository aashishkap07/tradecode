# C488 pre-registration — written 2026-09-25, BEFORE any of these tests were run

The operator asked for the combination of strategies most likely to earn 2–4% a
month on short-to-medium horizons across the assets OMEGA trades. Everything
below was fixed before any result was seen. Anything tested later is labelled
as exploratory and cannot be admitted.

## Data
- **Crypto:** the Binance USDT-M perpetual archive (data.binance.vision), daily
  klines and 8-hour funding, 2020-01 → 2026-08, **every symbol including the
  delisted ones**. Universe each day = the 40 most liquid by 30-day median
  quote volume, measured through the previous day, with at least 90 days of
  history. This is point-in-time and survivorship-free.
- **Traditional (the bot's RWA perps):** Yahoo daily futures and indices,
  2000 → 2026, as proxies for Bitget's XAU, XAG, COPPER, XPT, XPD, CL, BZ,
  SP500 and NDX100. Bitget's own contracts have 4–12 months of history, too
  short to test.

## Rules common to every sleeve
- The signal uses closes up to day t. The position earns day t+1
  (crypto: traded at the close; traditional: one extra day of lag).
- Each asset is scaled to 2% daily volatility using a 30-day trailing standard
  deviation, capped at 1×, with equal capital per asset.
- **Costs:** 0.08% per unit of turnover (0.06% taker + 0.02% half-spread).
  **Crypto funding** is the actual historical rate: longs pay positive funding,
  shorts receive it.
- **Traditional funding** is reported two ways: none, and a stress case at
  Bitget's measured current rates (long metals pay 10%/yr, copper 21%/yr, long
  oil *receives* 50%/yr, indices ±4%/yr).

## Sleeves
| id | sleeve | rule |
|---|---|---|
| C1 | crypto trend | sign-average of 1/2/4/8-week returns; daily rebalance with a 30% no-trade band |
| C2 | crypto cross-sectional momentum | 2-week return rank; long top fifth, short bottom fifth; rebalanced weekly |
| C3 | crypto funding carry | trailing 7-day mean funding rank; long lowest fifth, short highest fifth; rebalanced weekly |
| C4 | BTC evening effect | long BTC 22:00–24:00 UTC every day (1-hour data), taker in and out |
| T1 | traditional trend | C1's rule on the 9 RWA proxies |

## The combination (the headline)
- **COMBO-C** = C1 + C2 + C3, each sleeve scaled to equal trailing 60-day
  volatility (past data only), then the total scaled to 20% annual volatility.
  Leverage is capped at 3×.
- **COMBO-CT** = COMBO-C plus T1, same method.
- **No sleeve is dropped or re-weighted after seeing results.**

## Admission bar (the project's standing rule)
A strategy passes only if both hold:
- its net mean return is positive in at least 3 of 4 chronological quarters of
  its own sample;
- its Newey-West t-statistic (5 lags) over the full sample is at least 2.

Only an admitted item may trade money in the bot. An item that does not pass
may run in paper only, clearly labelled.

## What 2–4% a month requires
The target is a volatility choice, not a strategy choice. For a Sharpe ratio S,
2%/month needs about 24/S % annual volatility. The report will state the
drawdown that volatility implied historically.
