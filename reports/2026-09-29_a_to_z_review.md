# A to Z review (29 Sep 2026): what the bot is doing, why it lost in its first four days, and what can change

This was written after the C506 deploy screenshots (10:02 IST restart, `OMEGA
C506`, the log push check all OK, DATA "on time"). You asked for five things:
- a full re-analysis of the philosophy, principles and methods behind the
  2–4%/month target;
- what could be improved, including new ideas;
- why you see only losses since the switch;
- whether the bot trades metals, Korean equity or US stocks;
- whether India could run in the same code through Groww, with its own
  100 USDT.

Every number below comes from the server's own files, Bitget's data or the
research scripts in `research/`, which can be re-run.

---

## 0. The short answer

1. **The losses are the strategy having a bad patch, not the code failing.**
   - I re-ran the same rule on Bitget's own prices for the same days. It
     lost **2.9% over 25–28 Sep**, just after making +9.6% in August and
     +3.7% on 1–24 Sep.
   - Live paper lost about 1% more than that. All but about $0.30 of the gap
     is explained (section 3).
2. **How rare is it?** Four days down 4.5% sits in the **bottom 2%** of all
   3.7-day spans in the 2020–26 test. A 4-day loss of 3.9% or more happened
   about **8 times a year**. After those episodes, the book was higher 90 days
   later **80% of the time** (median +10.9%). That is history, not a promise.
3. **About 60% of the loss came from three momentum shorts** that were
   squeezed: PUMP, WLD and LINK.
   - This round's tests asked whether the short side is worth it. Its own
     return is about zero (+0.3%/yr). But it made **+29% in 2022**, the
     crash year, when the long side lost 29%. It is insurance, and removing
     it made the worst drawdown worse (38.6% against 31.4%).
   - Two refinements look promising but are **not proven** (t 0.8–1.0): skip
     shorts the crowd is already short, and residual momentum. They go to the
     December forward test. **No rule change now.**
4. **Markets: crypto only.** Bitget lists metals, US and Korean stocks,
   Hong Kong stocks, indices and energy as perpetuals. The bot excludes them
   on purpose (section 6).
5. **India via Groww is possible, but not worth automating at ₹8,800.**
   - The rules allow it: the Groww API is ₹499/month + GST, orders must come
     from a static IP, and personal use under 10 orders a second needs no
     registration.
   - The tested Indian trend pot made only **+6.8%/yr**, and **5.3%/yr of the
     pot went on costs**. It failed its bar.
   - A plain **50/50 Nifty BeES + Gold BeES, bought by hand and held**, did
     better historically: +15.5%/yr, about 1.2%/month. That still isn't
     2–4%, and no bot is needed for it.
6. **New in C509:** the dashboard and the log now tell you whether the result
   so far is normal. For example: "since the book began (25 Sep, 3.7 days):
   −$11.30 (−4.47%) · normal for that long: −1.8% to +2.7% · bottom 2%:
   rare."

---

## 1. The philosophy: what we believe and why

A futures trader earns from one of three places:
- **being faster** (latency, market making);
- **knowing more** (information);
- **being paid to carry a risk** others want to shed.

At $250 on a retail connection we can't win the first two. The C487–C491
research proved it for our old intraday scanner: it paid **5–9× more in fees
than its edge**. So the whole design rests on the third place: **persistent,
documented risk premia and behaviours**, harvested slowly and cheaply.

The principles we follow, in order of importance:

| # | principle | what it means in the bot |
|---|---|---|
| P1 | **Trade only what has been measured, on what actually trades** | Every sleeve was tested on 6½ years of our own data (2020 → 2026, 656 contracts, delisted coins included). Rule 54: the research list and the trading list must be the same list. |
| P2 | **Evidence before money** | Each idea is pre-registered and pushed to GitHub *before* its data is computed. It must clear a Newey-West t ≥ 2 (stricter when several ideas are tested at once), 3 of 4 time quarters positive, a positive recent holdout, and no worse drawdown. Most ideas fail. That is the filter working. |
| P3 | **Size by risk, not by conviction** | The book aims at a fixed volatility (20%/yr at dial 15%). The three sleeves get equal risk. Gross exposure is capped at 3×. |
| P4 | **One loss control, on marked equity** | The month guard: if the book loses the dial's share of the month's starting equity (15% of $252.81 = $37.92 for September), everything closes until next month. There are no per-position stops: every position is re-decided each day, and the guard is the one thing that can close the book. |
| P5 | **Costs decide** | Rebalance once a day. Skip trades under $6 or under 30% of the target (the "band"). Taker fees ≈ 0.06%, all-in ≈ 0.07–0.08%, checked on real fills. |
| P6 | **Negative feedback, not positive** | Rule 55: hold risk at a set point. Never let a recent winner grow its share, because sleeve returns mean-revert over weeks (round 5, N6: −14.6%/yr). |
| P7 | **Paper first, same code as live** | Paper uses live Bitget prices, real funding and the taker fee. Live stays locked (`C488_LIVE_OK = False`). |
| P8 | **Honest targets** | 2–4%/month is at the edge of what exists. For 70–90% of months to make ≥ 2% you need a Sharpe of 3–8. No documented strategy has that. What we have is Sharpe ≈ 1.4–1.6, which *averages* 2–4%/month with big swings. |

### What the target really means (from `research/c504_results.txt`)

| set-up | average month | months ≥ +2% | months < 0 | a whole YEAR averaging ≥ 2%/month (history / after a ⅓ haircut) | worst month | worst drawdown |
|---|---|---|---|---|---|---|
| book, dial 15% + Savings (**now**) | +2.86% | 50% | 33% | 67% / 45% | −14.5% | 29.5% |
| book, dial 20% + Savings | +3.92% | 53% | 32% | 78% / 58% | −18.5% | 40.6% |
| both pots (book 20% + spot pot) | +3.35% | 54% | 37% | 74% / 50% | −6.7% | 26.8% |

**Read this carefully:**
- **Even in the good history, a third of all months lost money.** The target
  is reachable *as a yearly average*, not as a monthly guarantee.
- A losing first week is exactly what this table predicts will happen often.

---

## 2. The methods in detail

### The book (C488): three sleeves, one daily rebalance

Every day at **00:05 UTC (05:35 IST)** the bot does the following:
1. It downloads about 330 days of daily candles and funding for the most
   liquid crypto perpetuals: the top 80 by volume, trimmed to the **top 20**
   for sizing at our account size.
2. It works out three sleeves, below.
3. It combines them and trades the difference between what it holds and what
   it should hold.

| sleeve | what it bets on | how | re-decided | why it should work |
|---|---|---|---|---|
| **C1 trend** | each coin keeps going the way it has been going | score = average of the signs of its 7, 14, 28 and 56-day returns (−1 … +1), sized by its volatility; long if up, short if down | daily, with a 30% band | slow-moving capital and herding; the most documented futures premium (time-series momentum, 100+ years across assets) |
| **C2 momentum** | the strongest coins beat the weakest | rank the 20 coins by 14-day return; long the top fifth, short the bottom fifth, dollar-neutral | weekly (Monday's close) | relative strength persists for weeks in crypto; the long side carries the return, the short side hedges the crash (section 5) |
| **C3 carry** | coins where longs pay high funding underperform | rank by 7-day funding; short the most expensive fifth, long the cheapest | weekly | crowded longs pay you to take the other side |

**Combining.** Each sleeve is scaled to the same risk, and then the whole
book is scaled to its volatility target:
- dial 15% → 20%/yr → about 1.3% a day;
- gross is capped at 3×.

With $250 and the $6 minimum, that gives 8–12 positions and 0.3–0.7× gross.

**What it looks like today** (the 29 Sep rebalance, after Monday's weekly
refresh):
- **short:** BTC, ETH, XRP (14-day laggards, +7% against leaders at
  +60–95%);
- **long:** HYPE, ENA, SUI, NEAR, ZEC.

The BTC and ETH shorts are *relative* bets, not a forecast that BTC falls.

### The paper ledgers (never touch the book's money)

| ledger | what | when | status |
|---|---|---|---|
| **Savings (C501)** | idle cash that would sit in Bitget Flexible Savings at 7.63% APR | continuous | about $172 idle ≈ +$1.1/month |
| **Spot pot (C501/C502, S1)** | a separate $250: long or flat trend on the top 20 spot coins, cash in Savings | 00:20 UTC | admitted in round 8; 16 coins, 24% invested |
| **Carry ledger (C490)** | the classic funding trade: long spot, short perp | 00:10 UTC | passed (t 2.78) but lost in 2025–26 as it got crowded; paper only |
| **K4 allostatic shadow** | the same book sized with a 10-day volatility memory | each rebalance | same return, worst month −9.7% vs −15.5%; decided in December |
| **Intraday shadow (C489)** | the old intraday idea, scored hourly | hourly | expected to lose after costs; kept only as a measurement |

### The safety net

- **The month guard** (P4).
- **The C504 data watchdog:** every feed checked against its own schedule
  (prices within 3 min, funding within 10 min of settlement, and so on).
- **The C499 rule:** no trade on incomplete history.
- **C506:** every rebalance saves its exact inputs, so any day's plan can be
  recomputed to the cent.
- **Live mode stays locked.**

---

## 3. Why you are seeing losses: the numbers

### The timeline (marked equity: open positions valued at the current price)

| moment | equity | note |
|---|---|---|
| 1 Sep (month anchor) | $252.81 | the old intraday scanner was still running |
| 25 Sep 17:46:57 IST: **the book's first build** | **$252.63** | the scanner's whole September: −$0.18, i.e. flat after 24 days |
| 29 Sep 11:11 IST (your screenshot) | **$241.33** | **−$11.30 (−4.47%) in 3.7 days** |

### The same rule on Bitget's own data (`research/c507_sim_recent.py`, run 29 Sep)

| period | simulated book |
|---|---|
| July 2026 | +0.71% |
| August 2026 | **+9.63%** |
| 1–24 Sep | +3.71% |
| **25–28 Sep (the live days)** | **−2.92%** |

**The rule itself had a bad four days.** We happened to switch it on right
after a strong three months (+14.5% compounded). Neither the good run nor the
bad week predicts the next one.

### Where the live loss came from

Closed positions, from the server's own `c488_book.json`:

| coin | sleeve | side | booked result |
|---|---|---|---|
| **PUMP** | C2 momentum | short | **−$3.72** |
| **LINK** | C2 momentum | short | **−$1.59** |
| **WLD** | C2 momentum | short | **−$1.49** |
| UNI | trend/momentum | long | −$0.86 |
| PEPE | trend/momentum | long | −$0.76 |
| ETH (twice), ENA | | | −$0.22 |
| ARB, TAO, SOL | | | +$0.16 |
| **all closed** | | | **−$8.47** |

The rest, −$2.83, is mostly the positions still open:
- their marked loss at 11:11 IST was −$2.47 (the dashboard's $243.80
  realised − $241.33 marked);
- their fees and funding so far were −$0.06;
- **about $0.30 I have not yet traced to a line.** It is possibly the old
  scanner closing a position after the first build. It's too small to change
  any conclusion, and it's on the list for paper check #2.

**PUMP + LINK + WLD = −$6.80, about 60% of the whole −$11.30.** All three
were *shorts on laggards that bounced*. This is the known way cross-sectional
momentum loses: crypto pumps are bigger than its dumps (positive skew), and a
coin that has fallen hardest is the one most likely to be squeezed.

### Why live lost about 1% more than the simulation

1. **26–27 Sep oversizing.** The book held 0.70× against a plan of about
   0.5×, because of a history-fetch bug. It was found and fixed in C499 on
   27 Sep. It made PUMP's loss about $1.1 larger.
2. **ETH's minimum order.** 0.01 ETH ≈ $27 against targets of $14–31, so ETH
   is held at 0 or 1 step, often far from its target (known, pending #18; it
   fades as equity grows).
3. **Costs.** About 0.07% of each rebalance's turnover, which is inside the
   research assumption.

None of these is a flaw in the strategy. The two code defects found in these
days are fixed.

### Is −4.47% in 3.7 days normal? (C509, from `research/c509_normal_range.txt`)

The spread of the book's returns over spans of 3.7 days in 2020–26
(interpolated between the 3- and 4-day rows):

| percentile | 1st | 5th | 10th | median | 90th | 95th | 99th |
|---|---|---|---|---|---|---|---|
| return | −5.0% | −2.6% | −1.8% | +0.1% | +2.7% | +4.2% | +7.4% |

**−4.47% sits at about the 2nd percentile: rare, but inside the tested
range.** From today the bot works this out itself and shows it (section 9).

---

## 4. What history says happens next (`research/c507_start_context.txt`)

**After a 4-day loss of 3.9% or more** (25 episodes in 6.3 years, about 8 a
year):

| after | median | share positive |
|---|---|---|
| 30 days | +2.0% | 64% |
| 90 days | +10.9% | 80% |
| 182 days | +18.3% | 75% |
| 365 days | +42.7% | 78% |

**From a random start day**, the chance of being *below* where you started:
- 30 days: 33%
- 90 days: 24%
- 1 year: 16%

**The part nobody likes to hear.** The book spends most of its life below a
previous high:
- only **8% of days** set a new high;
- the typical dip lasts 4 days, but 1 in 20 lasts over 71 days;
- the longest took **638 days** to recover.

That is what a Sharpe-1.5 strategy feels like from the inside. If the month
guard isn't hit, the right move after a bad week is usually to do nothing.

---

## 5. Could anything be improved? What we have tested

### Ten rounds so far (all pre-registered; the files are in `research/`)

| round | ideas (field) | result |
|---|---|---|
| C488 | trend, momentum, carry | **admitted** (the book): +32.6%/yr, Sharpe 1.56, DD 31.4% |
| C489 | intraday prediction model (16 features, ML) | fails on costs: turnover 4–9×/day |
| C490 | spot–perp carry | passed, but crowded since 2025 → **paper ledger** |
| C491 | limit-order (maker) intraday | fails: −209%/yr on 1-minute paths |
| 5 (C493) | new-listing short, low volatility, attention, crowd positioning, following top traders, path efficiency (Hurst), factor momentum | none admitted. Low vol was a near miss (t 2.23), so it gets a forward re-test. **Following the biggest accounts loses 8%/yr** |
| 6 (C496) | weekend drift of stock perps, grid bot, drawdown control (CPPI) | all fail. **The grid bot's worst coin-month lost 275% of its allocation** |
| 7 (C500) | Markov crash guard, horizon ensemble, Ichimoku, allostatic vol (K4) | none admitted; K4 halves the worst month, so it gets a forward test |
| 8 (C501/C502) | the spot trend pot | **admitted as a paper pot** |
| 9 (C505) | chaos (variance-ratio gate), information theory (dispersion), control theory (drawdown feedback) | none admitted |
| **10 (C507, today)** | fixes for the momentum sleeve's short squeezes | none admitted; 2 go to the forward test |

### Round 10 in detail (`research/c507_results.txt`)

This round was written and pushed *before* its data (commit f7fc72f).

**First, the direct question: does C2's short side pay?**

| C2 leg alone | per year | t | 2020 | 2021 | **2022** | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| long side | +15.5% | 2.52 | +32% | +38% | **−29%** | +28% | +13% | +3% | +12% |
| short side | +0.3% | 0.05 | −17% | −18% | **+29%** | −13% | +5% | +11% | +4% |

The short side earns nothing on average. But in 2022 it made exactly what the
long side lost. **It is a crash hedge, not a profit centre.**

| test | change | vs the book | t | quarters | 2025–26 | max DD | verdict |
|---|---|---|---|---|---|---|---|
| N1 | drop the short side | +0.79%/yr | 0.13 | 2/4 | −2.40%/yr | **38.6%** (vs 31.4%) | fails. **Worse drawdown**: removing the hedge exposes the crash |
| N2 | skip a short when its 7-day funding is negative (the crowd is already short) | +2.82%/yr | 1.02 | **4/4** | +2.62%/yr | 29.8% | not admitted (bar t 2.13); **forward test** |
| N3 | residual momentum: rank the 14-day return after removing each coin's market beta | +2.14%/yr | 0.82 | 3/4 | +3.36%/yr | **25.3%** | not admitted; **forward test** |

**Why not switch to N2 or N3 now, when they look better?**
- A t of 0.8–1.0 means a result this size turns up by luck about one time in
  six. With three ideas tested, one of them looking this good by chance is
  likely.
- Changing the rule right after a bad week is the classic mistake: you end up
  tuning to last week's losers.
- **The December forward test** runs them on data after August 2026, which
  none of the research has seen, alongside K4 and the round-5 near-misses.
  Anything that passes goes in then.

### The real levers you have today (no new research needed)

1. **The dial (pending #6).** Dial 20% + Savings historically took the chance
   of a +2%/month year from 67% to 78%. The worst month went from −14.5% to
   −18.5%. Above 20% the chance barely rises while the drawdown grows. **20%
   is the knee.** Your call.
2. **Both pots together (book + spot pot).** Their daily returns correlate
   only +0.14. Together at dial 20%: a 74% chance of a +2%/month year, with a
   **worst month of −6.7%** instead of −18.5%. This is the best
   risk-for-return trade on the table.
3. **Savings for idle cash (pending #14).** About +0.4%/month on the account,
   with no change to the strategy. It needs the live switch.
4. **Account size.** At $250, ETH's minimum order and the $6 floor add
   tracking error. At about $1,000 the book spreads to 40 coins and these
   effects shrink.

### Ideas from other fields, and what became of them

You asked about quantum physics, calculus, chaos and logic. Where an idea
could be turned into a testable trading rule, it was tested:
- **chaos theory:** the Hurst exponent, variance ratios, path efficiency;
- **control theory:** drawdown feedback, CPPI, allostatic set-points;
- **information theory:** dispersion scaling;
- **Markov regimes:** the crash guard;
- **physiology:** allostasis (K4, the one survivor so far).

Several fields had no testable rule to offer:
- **Quantum physics** gives no testable trading rule. "Quantum" trading
  products are marketing.
- **Calculus** is already inside every vol target and ranking.
- **Probability** is the whole admission process.

The lesson from all ten rounds: **the simple, slow premia work; clever
overlays mostly add turnover and fail.**

---

## 6. Which markets does it trade? Crypto only, on purpose

Bitget's USDT perpetuals (the live contract list, 29 Sep): **804 contracts.**

| type | count | examples | traded? |
|---|---|---|---|
| crypto | 464 | BTC, ETH, SOL, HYPE… | ✅ the top 20 by volume |
| US stocks & ETFs | 315 | NVDA, TSLA, AAPL, QQQ… | ❌ |
| metals | 8 | PAXG, XAUT, XAU, XAG, XPT, XPD, copper… | ❌ |
| Hong Kong stocks | 8 | | ❌ |
| Korean stocks | 3 | | ❌ |
| indices | 3 | | ❌ |
| energy | 3 | oil | ❌ |

The book reads Bitget's `isRwa` flag and trades crypto only. All 80 of
today's candidates are crypto. Why:
1. **No history to test on.** Most were listed from mid-2025, and Bitget's
   funding history for them is 90 days deep: too short to test anything (a
   Sharpe-1 strategy would show t ≈ 0.5).
2. **Survivorship bias.** Bitget's stock list was chosen with hindsight
   (today's winners), so any backtest on it flatters itself.
3. **When they leaked into the research, results got *worse*.** From Dec
   2025, Binance's stock and commodity perps crept into the research
   universe. Taking them out raised the 2020–26 result from +33.0%/yr
   (t 3.55) to +36.0%/yr (t 3.96).
4. **The one test we could run failed.** Round 6's weekend-drift rule on
   319 stock and commodity perps flipped sign out of sample (t −3.55).
5. **Their funding.** Oil longs were paid 28–34%/yr and gold longs 8–10%/yr.
   That is interesting, but it's 90 days of data. It's on the list to
   re-check each quarter; nothing to trade yet.

---

## 7. India through Groww: is it possible, and is it worth it?

### What's possible (checked 29 Sep 2026)

- **API access.** Groww offers a trading API for **₹499/month + GST**
  ([Groww Trade API](https://groww.in/trade-api)).
- **The rules.** SEBI's retail algo framework has applied since
  **1 April 2026**
  ([HDFC Sky summary](https://hdfcsky.com/sky-learn/algo-trading/sebi-algo-trading-rules),
  [Zerodha on static IPs](https://inthemoneybyzerodha.substack.com/p/sebi-algo-trading-changes-april-2026)):
  - orders must come from **one registered static IP** (your VPS has one);
  - each order is tagged by the exchange;
  - personal use under **10 orders a second** needs no strategy
    registration.
- **Costs per delivery order** ([Groww pricing](https://groww.in/pricing)):
  - brokerage ₹20 or 0.1% (minimum ₹5), plus 18% GST;
  - about ₹20 + GST of DP charge on every sale;
  - STT 0.1% on stocks (only 0.001% on an ETF sale);
  - stamp duty 0.015%.
- **F&O is out.** One Nifty lot is about ₹15 lakh of exposure. Option
  *buying* fits in ₹8,800, but SEBI's own studies found about 9 in 10 retail
  F&O traders lose.

So, **technically yes**: the same bot could hold a second, separate ₹8,800
(≈100 USDT) pot that trades through Groww.

### Is it worth it? The test (pre-registered as C508, commit e95b74d)

**I1:** the spot pot's idea in India.
- **Universe:** five liquid ETFs (Nifty 50, Nifty Next 50, Bank Nifty, gold,
  Nasdaq-100).
- **Rule:** long or flat by trend, monthly, 12% volatility, cash earning 6%.
- **Costs:** Groww's real costs on ₹8,800.

| | result (2018-04 → 2026-09) |
|---|---|
| **I1 at ₹8,800** | **+6.8%/yr** (0.55%/month), max DD 20%, **t 0.32 → not admitted** |
| its costs | 24 trades a year, **₹3,953 = 5.3% of the pot every year** |
| months ≥ +2% | 24% |
| buy-and-hold Nifty 50 | +10.9%/yr, max DD 36% |
| **50/50 Nifty BeES + Gold BeES, held** | **+15.5%/yr (1.2%/month), max DD 20%** |

The same rule on a bigger pot (descriptive only, `research/c508_sizes.txt`):
- **₹50,000:** +10.4%/yr (costs 1.65%/yr);
- **₹1 lakh:** +10.8%/yr (costs 1.19%/yr).

It still doesn't beat a simple 50/50 hold, and still falls short of the t
bar (1.36–1.47).

### My recommendation

- **Don't build an Indian bot at this size.**
  - The API fee, ₹499 + GST a month ≈ ₹7,070 a year, is **80% of ₹8,800**.
    It isn't even in the test's costs above.
  - The fixed DP charge on every sale eats small trades.
- **If you want Indian exposure, the evidence says:** buy Nifty BeES and Gold
  BeES in equal parts by hand in the Groww app. Top up monthly, rebalance
  once a year, and don't trade it.
  - **Historically ≈ 1.2%/month** with a 20% worst drawdown. It isn't 2–4%,
    but it is diversified away from crypto.
  - Tax: equity STCG is 20%, and LTCG is 12.5% above ₹1.25 lakh. Gold ETFs
    are taxed differently. Ask your CA.
- I'd revisit an automated Indian pot only above about ₹6 lakh, where the
  API fee falls to about 1%/yr. Even then it has to beat the simple 50/50
  hold, which I1 never did.

---

## 8. Corrections to what I told you earlier

- **"The crowd is getting more leveraged-long" (29 Sep paper check) was
  wrong.** I read "24 of 37 coins now pay over 10%/yr" as rising leverage.
  But Bitget's *default* funding rate is 0.01% per 8 hours = **10.95%/yr**,
  and 14 of the top 40 sit exactly on that default. Coins drifting back to
  the default is calm, not crowding. The carry ledger's 10%/yr entry
  threshold sits just under the default, so it will count many ordinary
  coins; that is noted for the December review.

---

## 9. What C509 adds (the "is this normal?" line)

- **On the dashboard, under the book:**
  > since the book began (25 Sep, 3.7 days): −$11.30 (−4.47%) · normal for
  > that long: −1.8% to +2.7% (10th–90th percentile of the 2020–26 test) ·
  > bottom 2%: **rare**
- **In the 8-minute log block**, a CONTEXT row:
  `since 25 Sep $-11.30 (-4.47%) in 3.7d | normal -1.8% to +2.7% | bottom 2%: rare`.
- **After each daily rebalance**, a log line: `📏 C509 since the book
  began …`.
- **From October**, a second line for the month so far, once the book is
  older than the month.

The words mean:
- **normal:** 10th–90th percentile;
- **uncommon:** 5–10 or 90–95;
- **rare:** 1–5 or 95–99;
- **beyond the tested range:** outside 1–99. That would be the time to worry
  about the code or the market, and the moment to look closely.

How it works:
- **The start is exact:** 25 Sep 12:16:57 UTC, $252.63, from the first build
  in the log.
- **The range scales with the dial:** at dial 20% the range widens by 20/15.
- **Tests:** `omega_c509_test.py`, 30 checks, including the page in
  Chromium. The full battery: 35 of 36 pass; the 36th, `omega_exit_test.py`,
  is the known one that needs the `corpusL/` data.

---

## 10. Still open

- **The spot pot's 16 coins against an independent 15**, and SOL and UNI
  held at their older sizes. This will be settled at **paper check #2
  (30 Sep 06:45 IST)**:
  - from the first `c488_inputs.npz` and the new "holds:" line;
  - by comparing the saved closes with fresh Bitget closes.
- **Your decisions:** the dial (#6), and whether both pots go live together
  (#15), after the security steps (#3) and a CA's view (#8).

---

## Deploy C509 (Termius)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|C504|C509|DATA|Traceback"
```

**What you should see:**
- `OMEGA C509`, with no Traceback;
- the dashboard's book panel shows the "since the book began" line;
- the next 8-minute block has a CONTEXT row;
- tomorrow's 05:35 IST rebalance is followed by a `📏 C509` line.

The push script hasn't changed since C506, so there is nothing to re-copy.
