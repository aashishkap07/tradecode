# The completeness audit: every dimension, checked (C504)

**Date:** 28 Sep 2026
**What changes for your money:** nothing. C504 adds a data watchdog and fixes
one display. The research below measures; it does not change the book.

## 1. C503 on the server: verified

Your screenshots (14:59 IST) and the server's 15:17 IST logs show every C503
line as intended:
- the **WHAT IS RUNNING** summary;
- "free $220.92 after open P&L" ($244.86 − $23.94);
- "LIFETIME … intraday · account $+0.39 realised";
- "Win Rate (intraday trades) … no trades yet | none open";
- no MARKET row, and no false "HARD STOP" in the Session log;
- the session measured from $244.70, the chart's first point.

The numbers add up as before:
- the book rows sum to $120.30;
- marked $244.77 = $250.39 − $5.62;
- the month's $8.04 = $252.81 − $244.77;
- Savings $171.88 = $244.77 − $72.89.

**One more untrue line, found and fixed:** at 14:32 IST the intraday shadow
logged **"gate OPEN"** for the 09:00 UTC hour, the first time its cost-gated
model opened, taking 16 paper positions. After the 14:46 restart the
dashboard said **"gate shut"**, because the gate was never saved.
**C504 saves it.**

## 2. Error-free code and logs

- **Server logs since the book started (25 Sep 17:46):** 0 errors, 0 failed
  data fetches, 0 unfilled or partial orders.
- **A static scan of the code (pyflakes):** 12 undefined names. **All 12 are
  in the idle intraday scanner**, and 5 are guarded or inside error
  handlers. **None is in the book, the carry ledger, the spot pot, Savings
  or K4.** They are listed for the scanner cleanup (pending #7).
- **Tests:** 34 test files; everything passes except the one old test that
  needs a data folder not in the repo.

## 3. Correct data, at the correct frequency: checked, then automated

**Checked by hand, from three days of server logs and Bitget:**

| engine | fetches | how often | verified |
|---|---|---|---|
| book prices | Bitget futures tickers (bid, ask, funding rate) | every 30 s | every 8-min block moves; PUMP and SOL marks inside Bitget's own 1-minute candles |
| book funding | each coin's interval (8h, or 4h for PUMP) | at every settlement | **every settlement for 2 days**: 00/08/16 UTC and 04/12/20 for PUMP. 28 Sep 04:00: +$0.00059 = 2341 × $0.005035 × 0.005%; 08:00: −$0.00414, both exactly Bitget's rates |
| the rebalance | 330 days of candles + full funding history, 80 coins | daily 05:35 IST | 26, 27, 28 Sep on time; "80 with history" |
| intraday shadow | 1-hour candles + taker flow, 40 coins | hourly at :02 | **every hour from 26 Sep 17:00 to 28 Sep 09:00 UTC**, 36–39 coins |
| carry ledger | spot tickers, 120 days, funding events | daily 05:40 IST | 26, 27, 28 Sep on time |
| spot pot | spot tickers (every 60 s while it holds) + daily run | 05:50 IST | the marks follow Bitget spot to the cent |
| Savings | the book's marked equity and margin | every minute | reserve and idle add up to the cent |

**Now the bot checks this itself (C504).** Every 8-minute block has a
**DATA** row, and the dashboard's "daily book" tile says **"data on time"**.
If a feed falls behind its own schedule, it says **"DATA LATE"** with the
reason, and a warning goes to the Session log. It repeats hourly while the
problem lasts, and it tells you when things recover.

The limits it enforces:

| feed | expected | "late" after |
|---|---|---|
| book prices | every 30 s | 3 minutes old |
| funding | at each settlement | 10 minutes past a settlement |
| rebalance | 00:05 UTC | 01:05 UTC |
| K4 comparison | at each rebalance | the book ran and K4 did not |
| shadow hour | :02 each hour | 90 minutes |
| carry | 00:10 UTC | 01:10 UTC |
| spot pot | 00:20 UTC | 01:20 UTC |
| spot prices | every 60 s while it holds | 5 minutes |
| Savings | every 60 s | 5 minutes |

## 4. The 70–90% question: the honest arithmetic

`research/c504_target_probability.py` uses 6 years of real data, 2020 →
Aug 2026. The **haircut** columns take a third off the average return, the
usual allowance for the future being worse than the backtest.

| set-up | per month | months ≥ +2% | **a year averaging ≥ +2%/month** | worst month | worst drawdown |
|---|---|---|---|---|---|
| book, dial 15% (running) | +2.57% | 49% | 61–66% (haircut 42%) | −14.6% | 31% |
| book 15% + idle cash in Savings | +2.86% | 50% | 67–71% (haircut 45%) | −14.5% | 30% |
| book 20% + Savings | +3.92% | 53% | **78–80% (haircut 58%)** | −18.5% | 41% |
| spot pot alone | +2.50% | 32% | 49–53% (haircut 39%) | −11.0% | 29% |
| **both pots, book 15%** | +2.79% | 46% | 63–64% (haircut 43%) | **−5.6%** | 21% |
| **both pots, book 20%** | +3.35% | 54% | **72–74% (haircut 50%)** | **−6.7%** | 27% |

**Why "70–90% of months" is out of reach:**
- A month clears +2% with probability Φ((average − 2%) ÷ spread).
- For **70%** of months, with a realistic 4–6% monthly spread, the average
  must be **+4–5% a month**. That is an annual Sharpe of **3–3.5**.
- For **90%** of months, it takes **Sharpe 5.6–7.9**.
- The best funds on record run about Sharpe 2. No honest strategy offers
  that, and anyone who promises it is selling something.

**What is achievable is a year:**
- **a 72–80% chance that the year averages +2% a month**, at dial 20%;
- **50–58% after the haircut.**

**Months are lumpy.** Only 8–14% of months land between +2% and +4%. The
year's gains come from a few strong trending months, with flat or losing
months between them.

**The dial, measured, not guessed** (book + Savings):
- Dial 10% → 15% → 20% raises the chance of a +2%/month year from 45% to
  67% to 78%.
- **Beyond 20% it barely improves** (25%: 80%; 30%: 81%), while the worst
  drawdown grows from 41% to 57%.
- **Dial 20% is the knee of the curve.** Growth-optimal (Kelly) sizing on
  this data would be even higher, but in-sample Kelly always overstates, so
  staying below it is correct.

**The most interesting deduction:** both pots at dial 20% give a better
chance of a +2%/month year (74%) than the book alone at 15% (67%), with a
much smaller worst month (−6.7% vs −14.6%) and a smaller worst drawdown
(27% vs 31%). The two pots barely move together, so one pot's bad months are
often the other's quiet ones. **This is the case for the dial decision (#6)
and for taking the spot pot live (#15).** Both are your decisions.

## 5. Ideas from other fields: round 9 (pre-registered, commit 50e7875)

| field | the idea | result |
|---|---|---|
| **chaos theory** | trend only where the coin's own path is persistent (Hurst via the variance ratio) | −0.7%/yr, not admitted. The 4-horizon trend rule already demands persistence; only 43% of coin-days are persistent at 7 days |
| **information theory** | momentum ranks mean more when coins are spread out (dispersion scaling) | −0.3%/yr, noise; not admitted |
| **control theory / calculus** | a drawdown feedback loop (cut size as losses deepen) | worst month −5.9% instead of −14.6%, but −8%/yr. Sharpe 1.51 < 1.56: it is **a lower dial in disguise**. Not admitted |

**Across rounds 7–9, 10 ideas from 8 fields have been tested:** Markov
regimes, superposition, Ichimoku, allostasis, the spot trend, the spot
minimum, Hurst, entropy, feedback control and Kelly.
- **Admitted:** the spot pot (and its minimum fix).
- **Waiting for a forward test:** allostasis (K4).
- **Rejected:** the rest.

That's normal. Most good-sounding ideas fail a fair test, and that's how the
ones that work are found. Kelly and ergodicity (a single account compounds
at its *time* average, not the average across many accounts) are what set
the dial analysis above.

## 6. Paper vs live: every difference

| area | paper | live | gap |
|---|---|---|---|
| book fills | ask/bid, taker 0.06% | market orders, read back (C492) | none at $10–30 orders |
| book funding | Bitget's quoted rate at each coin's settlement | Bitget's funding bills | **none: matched to $0.0001 twice** |
| sizes, steps, minimums | Bitget's contract table | the same | none |
| partial fills | always full | handled (C492) | negligible at this size |
| "available" | shown after open P&L (C503) | Bitget's figure | none |
| spot pot fees | 0.08% (BGB discount) | needs a BGB balance and "pay fees in BGB" turned on | set up when going live (#15) |
| spot quantity precision | exact | rounded to the pair's step | cents |
| Savings interest | from the first minute | from the next hour or next day, depending on the product; paid to the spot account | paper runs a few cents ahead |
| Savings rate | fixed 7.63% | changes; tiered (the first tier covers $172) | monthly review (#17) |
| India's 1% TDS on spot sales | not modelled | may apply | CA question (#8) |

## 7. How the engines fit together

- **Futures wallet:** the book, with about $24 of margin. The rest is idle;
  about 70% could sit in Savings (paper now; live needs pending #14).
- **Spot wallet:** the second $250, the spot pot (paper now; live needs
  #15).
- **The carry ledger and K4:** paper only.
- **They don't compete for the same money.** The book's month guard watches
  only the book, and the spot pot has its own $250.
- **Overlap:** both hold ETH long (about $26 in the book, $8 in the pot).
  Overall the two pots' daily returns correlate +0.14.

## 8. Bitget: anything left unexplored?

Everything on Bitget has now been looked at:
- **Savings:** flexible and fixed.
- **Structured products:** Shark Fin, Dual Investment.
- **Token farming:** Launchpool and PoolX.
- **Copy trading and bots:** grid, futures grid, Martingale.
- **Staking and loans.**
- **Spot and spot margin.**

**Nothing pays 2–4% a month without risk as large as the book's:**
- staking pays the coin's own yield (2–7% a year) while you carry the coin's
  price risk;
- fixed savings locks the cash the book may need;
- Martingale bots have ruinous losing streaks;
- loans are a cost.

The engines in the bot are the ones that passed their tests: the book, the
spot pot, and idle cash in Savings.

## 9. Deploy C504 (Termius)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|C504|DATA|Traceback"
```

**What you should see:**
- `OMEGA C504`;
- in the 8-minute block, a row `DATA  on time  prices …s  funding booked  book today  shadow …:00  carry today  spot pot today`;
- on the dashboard's "daily book" tile: "next rebalance 00:05 UTC · data on time";
- the intraday shadow panel keeps the gate state across restarts.

## Sources

- Bitget Flexible Savings: when interest starts and how it is paid, [Bitget Academy](https://www.bitget.com/academy/maximize-your-crypto-earnings-a-beginners-guide-to-bitget-flexible-savings)
- Bitget Savings APR tiers, [Bitget Support](https://www.bitget.com/support/articles/11449577117977)
- Everything else is measured here: `research/c504_results.txt`,
  `research/c505_results.txt`, the server's logs, and Bitget's API.
