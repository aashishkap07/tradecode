# 30 Sep 2026: the C513 screens, which accounts the bot can touch, and round 12 (should a winning trade be closed early?)

This answers your message with the five screenshots from 10:54 IST (C513,
running since 10:05 IST).

**In short:**
1. **The screens:** everything adds up. C513's two wording fixes show, and
   nothing is wrong.
2. **Your accounts:** today nothing trades on your Bitget account at all.
   Live, only the futures book would trade. It would use *everything* in the
   USDT-M futures wallet, and it would take over manual cross-margin
   positions there. So use a **sub-account** for the bot.
3. **Your question: close trades near their best point, where a loss is 70%
   likely from there?** On 6½ years and 2,692 of the book's trades, **that
   point never appears.** The chance of losing from any level of profit is
   42–57%. **Taking profit early was the most harmful rule tested:** −17.7
   points a year, and it was worse in every quarter.

---

## 1. The screens, checked (05:23–05:25 UTC)

| on screen | checked against | result |
|---|---|---|
| 12 positions: HYPE $14.57 … PUMP $5.96 | quantity × Bitget's 1-minute prices, from the server's `c488_book.json` (05:47 UTC push) | ✅ all 12 lie inside Bitget's 05:23–05:25 UTC price ranges, which matches your phone's 10:54. The page marks at the live bid/ask midpoint, not a minute's close |
| gross $113.89, open +$0.29 | the rows sum to $113.88 and +$0.35; open = +$0.35 − the $0.07 fee to close | ✅ |
| marked $250.22 | realised $249.93 (server state $249.9255) + $0.29 | ✅ |
| "since the book began (29 Sep): +0.09% in 0.9 days" | $250.22 ÷ $250.00 | ✅ C513's sign and span |
| tournament "first score at the next rebalance, for 2026-09-30" | the C513 wording; the 7 books unchanged | ✅ |
| Savings: idle $164.81, reserve $85.41, +$0.03 in 0.86 d | $22.86 margin + 25% × $250.22 = $85.41; 29 Sep 08:45 → 30 Sep 05:24 UTC = 0.86 d | ✅ |
| carry $249.61, −$0.33 | the per-coin figures equal the ledger file to the cent | ✅ (see below) |
| log: C513 boot, "IDLE", no scanner description, the 8-minute block | as designed | ✅ |

**Three figures that look odd but are right:**
- **"SESSION −$0.22" in red while the book is +$0.29.**
  - A session starts at each restart. Yours was at 10:05 IST, when the book
    happened to be marked at about $250.44.
  - It is now $250.22, so the session reads −$0.22.
  - The book's real result is the "since the book began" line: **+0.09%**.
- **"MONTH … used $0.07 realised" at boot, but "$0.00 of $50" on the
  dashboard.**
  - The boot line counts realised money only: $250.00 − $249.93 = the entry
    fees.
  - The month guard, the one that acts, counts marked equity, which is above
    $250.
- **The carry ledger doesn't move during the day.** It is marked once, at its
  00:10 UTC run. So −$0.33 is its figure from this morning.
  - **Where the −$0.33 comes from:** mostly $0.40 of entry costs, less $0.05 of
    funding already earned.
  - **Why it is normal:** a new carry position starts in the red by its
    costs and earns them back from funding over about two weeks.

**Worth knowing:**
- **PUMP: the book is short, and the spot pot is long.**
  - The book's short comes from its carry sleeve (C3): PUMP's crowd pays
    high funding, so the book takes the other side.
  - The spot pot is long because PUMP is in an uptrend.
  - Different rules, both paper, in separate pots. It is expected, not a
    conflict.
- **The intraday shadow (M1 +0.23%, 433 trades in 2 days) is paper only.**
  - Its costs are charged: 0.08% of turnover.
  - Two days mean nothing. Its research verdict is that it loses after
    fees.
  - Its "full model" needs 30 coins with a week of taker-flow data. Bitget
    serves that for only 23 of the 40, so it will probably stay on the
    warm-up model. This is known and recorded (C495).

---

## 2. Your two Bitget wallets: what the bot can and cannot touch

**Today (paper mode): nothing.**
- In paper mode the bot does not even load `api_keys.json`.
- It reads only public market data: prices, candles and funding.
- Your real spot and futures balances are never read, and no order reaches
  Bitget.
- The "$250 book" and the "$250 spot pot" are the bot's own paper
  accounts. They mirror your plan of two separate pots.

**Everything except the book is paper, even in live mode.** These have no
order path at all:
- the spot pot;
- the carry ledger;
- Savings;
- the rule tournament;
- the intraday shadow.

**Live mode (locked: `C488_LIVE_OK = False`), once switched on:**
- **Only the futures book trades, and only USDT-M perpetuals.** The exchange
  is set to swaps.
- The bot has **no spot-order, transfer or withdrawal code** (checked).
  Your spot wallet stays untouched.
- **Two things you must know before going live:**
  1. **It sizes on the whole USDT-M futures wallet.** Every 60 seconds the
     ledger takes Bitget's wallet figure as its equity. If that wallet holds
     $1,000, the book trades as a $1,000 book, not $250.
  2. **It adopts manual positions held in cross margin.** A position you
     open by hand in that wallet, in cross margin (the book's mode), is
     treated as the book's own. The next rebalance trades it to the book's
     target, which usually means closing it. Isolated-margin positions are
     left alone, with a warning.
- **So: run the bot in a Bitget sub-account.** Bitget lets each sub-account
  have its own API key with its own permissions ([Bitget sub-account
  guide](https://www.bitget.com/academy/bitget-sub-account-guide), [how to
  create one](https://www.bitget.com/support/articles/12560603827448)). The
  set-up:
  - move only the book's money (e.g. $250) into the sub-account's USDT-M
    futures wallet;
  - make the key trade-only, with withdrawals off and IP allow-listed;
  - keep it a classic account, not UTA.

  Your own spot and futures then stay in your main account, invisible to the
  bot. This is now a step in the live checklist
  (`reports/2026-09-26_live_mode.md`).

---

## 3. Round 12: is there a "70% chance of loss" point, and should we exit there?

**The test was pre-registered and pushed before any number was computed**
(`research/c514_preregistration.md`, commit 0967bd0).

**The data:**
- the book as it runs: N2+N3, dial 20%, top-20 crypto;
- 2020 → Aug 2026;
- costs and funding included.

**The yardstick is relative, as you asked.** Each trade's open profit is
measured in *its own coin's volatility*: **z = the move since entry ÷ (that
coin's daily volatility × √days held)**. A z of +2 means "unusually far in
profit for this coin, this soon".

### Part A: the chance of losing from here

| open profit z | coin-days | P(loss) next day | P(loss) next 7 days | P(loss) over the rest of the trade | average next 7 days |
|---|---|---|---|---|---|
| z ≤ −2 (deep loss) | 285 | 44% | 45% | 54% | +1.5% |
| −2 to −1 | 1,838 | 47% | 50% | 51% | −0.6% |
| −1 to 0 | 6,753 | 51% | 51% | 53% | −0.3% |
| 0 to +1 | 8,577 | 51% | 51% | 54% | +0.4% |
| +1 to +2 | 4,215 | 51% | 50% | 55% | +1.1% |
| +2 to +3 (well in profit) | 1,174 | 51% | 50% | 54% | +0.9% |
| z > +3 (far in profit) | 268 | 51% | **44%** | 57% | **+2.2%** |

**What this says:**
- **No level of profit makes a loss likely.** The highest chance in any
  bucket with enough data is 55%, against the pre-registered 70%.
- **The trades furthest in profit had the *lowest* chance of losing over
  the next week (44%), and the best average (+2.2%).** In crypto, strength
  tends to continue for a while. That is the momentum the book is built on.
- The 7-day stretch (a coin's last week, in its own volatility) gives the
  same picture: 42–55% everywhere.

**The shape of the book's trades (descriptive, price moves not dollars):**
- 2,689 trades; **45% won**;
- average win +13.9%, average loss −9.1%;
- **the best 10% of trades made about three times the entire net profit.**
  The other 90% together gave back about two-thirds of that.

That is the fingerprint of a trend book. It wins by catching a few big moves,
not by winning often. **Anything that cuts the big winners short cuts the
profit.**

### Part B: five exit rules against simply holding

Pass bars: t ≥ 2.33, better in ≥ 3 of 4 quarters, better in 2025–26, and a
drawdown no more than 2 points worse.

| rule | %/month | vs holding | t | quarters better | worst month | max DD | P(a year ≥ 2%/mo), bootstrap / realistic | verdict |
|---|---|---|---|---|---|---|---|---|
| **hold (what runs)** | **+4.01** | — | — | — | −17.8% | 38.3% | **81% / 61%** | — |
| X1 take profit at z > 2 | +2.57 | **−17.7 pts/yr** | **−2.48** | 0/4 | −16.7% | 40.4% | 66% / 48% | **fails; clearly harmful** |
| X2 take profit at z > 3 | +3.83 | −2.5 | −0.77 | 1/4 | −18.4% | 33.6% | 82% / 60% | fails |
| X3 sell half at z > 2 | +3.33 | −8.8 | −2.47 | 0/4 | −17.2% | 38.8% | 77% / 54% | fails; harmful |
| S1 stop at z < −2 | +4.05 | +0.6 | +0.23 | 2/4 | −14.8% | 36.2% | 82% / 60% | fails (no gain; see below) |
| S2 trailing stop 3 sd from the best | +3.06 | −10.5 | −1.45 | 1/4 | −11.4% | 32.5% | 69% / 48% | fails |

At dial 15% (descriptive) the ranking is the same.
- Take-profit costs 12 points a year.
- The stop S1 again changes nothing on returns. Its worst month is better
  (−11.2% vs −13.8%) but its drawdown is worse (25.6% vs 24.9%).

**The code was checked independently:** on every one of the 2,692 trades,
each exit fires exactly where a separate recomputation says it should, and
nowhere else.

**The answer to your question: no, don't close winning trades early.**
- The "70% point" does not exist in this book's trades.
- Closing at "unusually good" profit removes exactly the trades that pay
  for everything else.
- The trailing stop gives smaller worst months (−11.4%) by holding less
  (0.67× vs 0.89×), but it earns 10 points a year less.
- A lower dial buys the same calm more cheaply. Dial 15% has a worst month
  of −13.8% at +2.9%/month.

**Recorded, not built:** the stop at z < −2 (S1) left returns unchanged and
trimmed the tail at dial 20%, but not consistently at dial 15%. It goes on
the December forward re-test list (Atlas #11), where it is judged on data it
has never seen.

---

## 4. The strategy, in the terms you asked for

The book already does these things, and each is tested:

| your principle | how the bot does it | the evidence |
|---|---|---|
| **Relativistic** | every coin is sized by *its own* volatility, ranked *against the other coins*, and the momentum ranking is *relative to the market* (N3's residual momentum) | the 2020–26 tests; N3 is a forward test in the tournament |
| **Predictive** | trend over 7–56 days, 14-day relative momentum, and funding (who is crowded and paying) | admitted rounds 1–5, t 3.19 |
| **Maximal profit capture** | positions are held while the signal holds, with no profit caps | round 12: caps cost up to 17.7 pts/yr |
| **Loss minimising** | losses are controlled for the **whole book**, not per trade: 12–20 coins long *and* short; the book sized to a volatility target; gross ≤ 3×; the month guard stops the book at a 20% loss of the month's marked equity | round 12: per-trade stops don't help; the portfolio controls do the work |
| **Self-adjusting** | the volatility target re-sizes every day as markets calm or storm; the tournament scores 7 rule variants on the same prices every day | forward, in the bot |

**The target: 2–4% a month, with 80% confidence.** At dial 20%, with idle
cash in Savings:
- **81%** of simulated years average ≥ 2%/month (a bootstrap of 2020–26);
- **61%** after the standard ⅓ "real life is worse than backtests" haircut.

Nothing tested today raises that. The honest range is **60–80%**, with a
worst month near −18% and drawdowns up to about 38% along the way.
Promising more would be fitting the past. The paper record, and then the
first live months at a small size, are what firm this up.

**What's next:**
- **Tomorrow, 05:35 IST:** the first rebalance on C512's checked final
  prices.
- **06:45 IST:** paper check #3, and the tournament's first real score.
- **December:** the forward re-tests (N2, N3, K4, range volatility, and now
  the S1 stop) on data none of them has seen.
