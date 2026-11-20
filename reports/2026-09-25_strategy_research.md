# Which strategies can realistically earn 2–4% a month? — 25 Sep 2026 (C488)

## The short answer

**One combination passed every test.** It is a daily-rebalanced crypto book made
of three independent strategies:

- **Trend:** hold coins that have been rising for weeks; short coins that have
  been falling.
- **Momentum:** each week, buy the strongest fifth of coins over the last two
  weeks and short the weakest fifth.
- **Carry:** each week, buy the coins where holders are *paid* funding, and
  short the coins where longs pay the most funding.

The test used 6½ years of real Bitget-equivalent data, every coin (including
ones that later died), and real fees and funding. The result:

- **+2.5% a month on average**;
- 62% of months positive;
- worst fall from a peak: −31%;
- one losing year (2022, −8.9%).

This is at the bot's current risk setting (15% dial). **The bot now runs this
book by default** (version C488), in paper mode.

## What I looked at

1. **Published research:**
   - trend-following over 140 years;
   - crypto momentum;
   - funding-rate carry;
   - volatility control;
   - Bitcoin time-of-day effects;
   - why short-term trend-following died after 2009.
2. **The rules were written down and committed to git before any test was
   run.** This stops me from cherry-picking whatever happened to look good.
3. **Data:**
   - every Binance perpetual contract since 2020 (860, including delisted ones)
     with its real funding history;
   - 26 years of gold, silver, copper, platinum, palladium, oil, S&P 500 and
     Nasdaq futures, standing in for Bitget's own versions, which are too new
     to test.

## Results

| Strategy | per year | Passed? |
|---|---|---|
| Trend alone | +11.0% | not significant alone |
| Momentum alone | +5.3% | not significant alone |
| Carry alone | +9.5% | yes |
| **All three together** | **+30.0%** | **yes, strongly** (4 of 4 periods, t = 3.19) |
| Trend on gold / oil / indices | −2.1% | **no** |
| Bitcoin's evening effect | −57% after fees | **no**; it has vanished |

**Why together beats alone:** the three strategies make and lose money at
different times (correlation about 0.05). Combined, the bad weeks of one are
usually covered by the others.

**Why not gold, oil and indices:**
- Trend-following on those markets earned nothing from 2007 to 2026. Trend
  funds make most of their money on bonds and currencies, which Bitget does not
  offer.
- Bitget's funding on them is also expensive: holding long gold costs about 10%
  a year, and holding short oil costs about 50% a year.

**Stress tests it survived:**
- still passes the bar at double the trading fees;
- still passes if every trade happens a day late;
- still passes if funding income is ignored;
- still passes whether the book holds 20, 30 or 40 coins.

**The warning signs:**
- It has weakened. Over the last 12 months it made about 26% a year; over the
  last 24 months about 19% a year.
- Carry lost money over the last year.
- August 2026 was its second-worst month ever (−12.8%).

A realistic expectation going forward is about **1.5–2% a month** at the
current dial, not 2.5%.

## Your 2–4% a month target

The risk dial now controls how big the book is:

| Risk dial | Average month (2020–26) | Worst drop from a peak |
|---|---|---|
| 10% | +1.7% | −22% |
| **15% (now)** | **+2.5%** | **−31%** |
| 20% (maximum) | +3.3% | −40% |

**2% a month is realistic but not safe.** **4% a month** would have needed
risk that produced drops of 45–60%, so the dial deliberately stops at 20%. More
return always comes with bigger drops; no strategy removes that.

## What changed in the bot (C488)

- **Every day at 05:35 IST** (00:05 UTC), the bot:
  - downloads about 11 months of daily prices and funding for the most liquid
    coins;
  - works out the target book;
  - trades only the differences, using market orders that are confirmed with
    the exchange.
- **Positions are held for days or weeks.** Funding is paid or received every
  8 hours, as on the real exchange.
- **The old intraday scanner no longer opens new trades.** It lost money under
  honest fills. Any intraday positions already open are managed to their close.
- **At your balance ($250) the book holds up to 20 coins,** because Bitget's $5
  minimum order makes a 40-coin book impossible. From $1,000 it uses 40.
- **Monthly loss limit:** if the month's loss reaches your dial (15%), the book
  is closed and stays flat until next month.
- **Dashboard:**
  - a new **Portfolio book** panel lists every position, its strategy (C1 trend,
    C2 momentum, C3 carry) and its profit;
  - the **Scanning** tile now shows the next rebalance time.
- **Live money is locked off** (`C488_LIVE_OK = False`) until paper results have
  been checked against the real exchange.
- **To go back to the old engine,** set `OMEGA_ENGINE=intraday`.

## How to judge it

This is a **monthly** strategy. Individual days mean little.
- Expect about 6 months in 10 to be positive.
- A typical month moves between −6% and +6%.
- Judge it after 3–6 months, against those numbers.
- **Don't switch it off after a bad week.** That is exactly how trend and carry
  strategies lose their edge in practice.
