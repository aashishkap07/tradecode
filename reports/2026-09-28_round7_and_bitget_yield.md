# The book's first days, round 7, and what else Bitget pays

**Date:** 28 Sep 2026
**Server:** C499 since 27 Sep 12:25 IST. **Paper mode:** no real money at risk.

## 1. The dashboard and the logs: everything adds up

| figure | check | verdict |
|---|---|---|
| Marked **$243.95**, book open **−$6.43** | $250.39 realised − $6.43 | ✅ |
| Month **$8.86 of $37.92** | $252.81 − $243.95 (23% of the month's budget) | ✅ |
| 9 book rows sum to −$6.36; "open" −$6.43 | the difference is the $0.07 fee to close all 9 | ✅ |
| Today −$1.79 realised | this morning's rebalance closed ARB, ENA and TAO and trimmed SOL and PUMP. The PUMP buy-back realised −$2.05 | ✅ |
| Gross 0.50× (9 positions) | the first C499 rebalance: **80 coins of history**, 9 targets at 0.40×. Positions within 30% of target are left alone, so it holds a little more than 0.40× | ✅ C499 working |
| SESSION −$5.26 with a peak of $249.84 | marked to marked since yesterday's restart; the chart has 80 real samples | ✅ C498 working |
| Shadow: 37–39 coins scored **every** hour (23 of 23) | | ✅ |
| Warnings or errors in the whole session log | **0** | ✅ |
| Carry ledger: −$0.14, funding +$0.20; **19 of 37 coins now pay over 10%/yr funding** (12–13 over the weekend) | the crowd is getting more leveraged-long | ✅ |

**Why the book is down 3.4% since 25 Sep.** Bitcoin barely moved (−1.1%),
but the book was hit on both sides at once:
- **The shorts were squeezed:** WLD +15.7% and PUMP +24.9% since 25 Sep.
- **The longs faded:** PEPE −6.7% and UNI −5.1%.

WLD and PUMP alone cost about $6.7. Their short sizes were also doubled for a
day by the data bug C499 fixed (the 27 Sep book was 0.70×). About $1.1 of the
PUMP loss is due to that oversizing.

**Is that normal?** In the tested history (2020–26), a 3-day loss of 3.4% or
more happened **about 4.4 times a year**. Over the following 30 days the book
made a median of **+1.2%** and was positive 59% of the time. This is an
ordinary bad patch and says nothing about the strategy being broken.

## 2. Are the strategies correct?

**Yes. The book now does exactly what was tested.**
- Tonight's same-moment replay matched the server **to the cent**.
- C499 removed the last known differences from the research (funding depth,
  the candidate list, silent failures).
- The research itself, crypto only, top 20, dial 15%, 2020-05 → 2026-08,
  recomputed today: **+32.6%/yr, Sharpe 1.56, worst month −15.5%, worst drawdown
  31%.**

## 3. Novel ideas: round 7, tested honestly

Your analogies were turned into four concrete rules. They were written down
and pushed **before** any data was touched (`research/c500_preregistration.md`,
commit 6c62a13). To be admitted, a rule had to beat the running book clearly
(t ≥ 2.24), in 3 of 4 time periods, including 2025–26, without a worse
drawdown.

| idea (field) | what it does | result |
|---|---|---|
| **Markov regime / momentum-crash guard** | halves the momentum sleeve when a falling market is rebounding: exactly what just hurt us | **worse**: −1.7%/yr, and worse in 2025–26. Rejected |
| **Superposition (quantum)** | averages several lookback horizons instead of one | +4.6%/yr but not reliable (t 1.26, only 2 of 4 periods, worse in 2025–26). Rejected |
| **Ichimoku cloud** | replaces the trend signal | **worse**: −2.2%/yr, worst month −20%. Rejected |
| **Allostasis (biology)** | reacts faster to rising turbulence: volatility estimated with a 10-day half-life | same return (+0.3%/yr, noise), but **worst month −9.7% instead of −15.5%**, max drawdown 29% vs 31%. Rejected on return. **Its tail reduction is the most interesting result of the round**; it goes on the December forward re-test list |

**Other analogies, and where they already live in the bot:**
- **Homeostasis (biology):** the volatility target is the body's thermostat.
  It's the core of the book and the one loop that proved itself (round 6).
- **Markov chains:** they are features in the intraday model (C489). Real
  signal, eaten by fees.
- **Ecology / diversity:** three unrelated ideas (trend, momentum, carry)
  instead of one. Independent risks partly cancel.
- **Quantum "Zeno effect":** a system watched too often never evolves. A
  trader who trades too often never keeps an edge, because every "look" (a
  trade) costs a fee. This is exactly why the daily book works and the
  intraday bot didn't.
- **Probability / Kelly:** growth is highest at a risk level equal to the
  strategy's Sharpe. We sit well below it on purpose, because our estimate of
  the edge is uncertain, and betting too big destroys compounding.
- **Logic / falsification:** every idea above had to survive a test it could
  fail. Most do fail. That's how the few that work get found.

## 4. The "disabled" intraday bot: could it be changed to make 2% a month?

**No, and the reason is arithmetic, not effort.**
- **What a trade costs:** a typical intraday trade was about $93 of notional.
  The round-trip fee is 0.08–0.16% (maker/taker mix), **$0.07–0.15 per trade**.
- **What a trade earns:** the best edge ever measured, over 213,200 bars, is
  **+0.017% per trade** before fees, **about $0.016**. Fees are 5–9 times that
  edge.
- **What 2% a month needs:** $5 a month net. At about 3 trades a day, that
  needs a gross edge of **0.13–0.22% per trade**, 8–13 times more than ever
  measured.
- **Maker orders don't rescue it:** tested in C491, limit orders get filled
  mostly when the price is about to move against you (−209%/yr).

**About the shadow's +4.4%:** in 4 days it mostly came from **one coin, Q**,
jumping +82% and +33% in two single hours. That's luck. The cost-aware
version (M1g) is +0.68%. It keeps running on paper for free. If after 120 days
its record passes the statistical bar, it gets reconsidered.

## 5. Anything else on Bitget that pays 2–4% a month?

**2–4% a month is 27–60% a year.** Nothing on Bitget pays that without taking
risk comparable to, or bigger than, the futures book. Here is what exists:

| product | what it really is | realistic return | verdict |
|---|---|---|---|
| **Simple Earn Flexible (USDT)** | lending your USDT via Bitget | **7.63% APR now** (≈ 0.6%/month); promos briefly up to 11.5–25% on small amounts | safe-ish (exchange risk), low; **useful for idle cash (see below)** |
| **Fixed savings** | the same, locked 30–60 days | a little higher than flexible | as above |
| **Shark Fin** | principal-protected; bonus APR if the price stays in a range | base about 6% APR + bonus | low |
| **Dual Investment** | **you are selling an option** (insurance) | we measured the option premium: BTC implied vol averaged 50% vs 44% realised, **roughly 0.5–1% of notional a month before Bitget's cut**; realised beat implied 27% of the time, the worst by 44 points | the "up to 300% APR" is the premium annualised on a short window, not profit. It's a short-volatility trade like the grid bot, with rare large losses (being forced to buy BTC after a crash, or sell before a rally) |
| **Launchpool / PoolX** | lock BGB or USDT to farm new tokens | quoted 10–45% APR at the day's token price; **no pools running today**; per-user caps; new tokens usually fall after listing | small dollars at $250, token and BGB price risk |
| **Copy trading** | follow "top" traders | measured: **−8%/yr** | no |
| **Grid bots** | sell volatility in a range | measured: **negative on average, ruinous tails** | no |
| **Spot–perp carry** (our C490 ledger) | buy a coin, short its future, collect funding | ~10–15%/yr when funding is high; lost money in 2025–26; tax problem in India | paper only |
| **BGB fee discount** | pay fees in BGB | spot only, **not futures** | doesn't help the book |

## 6. The practical path to 2–4% a month

There are two real levers.

**Lever 1: the dial (your decision).** Research numbers, and a realistic
forward estimate after the usual one-third haircut:

| dial | research (2020–26) | realistic forward | worst month | worst 12 months |
|---|---|---|---|---|
| 15% (now) | +2.57%/month | ~1.7%/month | −14.6% | −23% |
| 20% (max) | +3.66%/month | ~2.4%/month | −18.6% | −33% |

**Lever 2 (new, low risk): put the idle cash to work.**
- **The idle cash:** at 0.5× exposure the book locks only about 10% of the
  account as margin. With cross margin, keeping about 30–35% in the futures
  wallet still covers the whole monthly loss budget plus margin, so about
  **65–70% could sit in Simple Earn Flexible at ~7.6%**.
- **What it's worth:** **about +0.4% a month** on the total account, with no
  change to the strategy.
- **What it needs in code:** the bot must count the Savings balance as equity
  and top the futures wallet up automatically. Bitget's API supports this
  (subscribe, redeem and balance endpoints). It only matters live, so it's
  noted as pending #14, to build when going live.

**Put together:**

| setup | expected return |
|---|---|
| **dial 15% + idle cash in Savings** | about **2.1% a month**, the bottom of your band |
| **dial 20% + idle cash in Savings** | about **2.8% a month**, the middle of your band, accepting worst months near −19% |

If the allostatic volatility rule (K4) holds up in December's forward test, it
would let a higher dial carry the same tail risk. That is the most promising
research lead from this round.

**Honest note:** these are averages over a year. Individual months will
range from about −6% to +10%, and some will be worse.

## Sources

- Bitget Earn / Savings rates:
  [Simple Earn dual rewards up to 11.5% APR](https://www.bitget.com/support/articles/12560603893393),
  [Flexible Savings guide](https://www.bitget.com/academy/maximize-your-crypto-earnings-a-beginners-guide-to-bitget-flexible-savings),
  [Bitget Earn](https://www.bitget.com/earning)
- Launchpool / PoolX:
  [Launchpool page (0 ongoing on 28 Sep)](https://www.bitget.com/events/launchpool),
  [PoolX explainer](https://www.bitget.com/academy/bitget-poolx-advantages),
  [How Launchpool APR is computed](https://www.bitget.com/support/articles/12560603823740)
- Dual Investment / Shark Fin:
  [Shark Fin, Dual Investment, Savings comparison](https://www.bitget.com/academy/bitget-shark-fin-dual-investment-savings-comparison),
  [Dual Investment explainer](https://www.bitget.com/academy/Introduction-to-Bitgets-Dual-Investment-Product)
- Earn API: [Savings Assets](https://www.bitget.com/api-doc/earn/savings/Savings-Assets),
  [Savings Redeem](https://www.bitget.com/api-doc/earn/savings/Savings-Redeem)
- Fees (BGB discount spot only):
  [Bitget Trading Fees FAQ](https://www.bitget.com/support/articles/12560603892734),
  [Bitget fees explained](https://themexc.com/blog/bitget-fees-explained/)
- Measured here: `research/c500_results.txt`. It uses the Binance archive for
  the book and Deribit DVOL vs BTC realised volatility for the option premium.
