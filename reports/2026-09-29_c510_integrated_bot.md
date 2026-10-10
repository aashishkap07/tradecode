# C510 (29 Sep 2026): the integrated bot

**Paper mode.** No real money. Live trading stays locked
(`C488_LIVE_OK = False`).

You asked for five things:
- the two momentum refinements running now, not in December;
- the log and dashboard showing truthfully what trades and what doesn't;
- a use for the disabled bot;
- every part working together and adjusting itself;
- a 2–4%/month target with an 80% or better chance.

This covers what I built, what the data says, and what I can't promise.

---

## 0. The short answer

1. **From the next rebalance (30 Sep, 05:35 IST) the paper book trades the
   two refinements together (N2+N3).**
   - **N3, residual momentum:** a coin is ranked on how it moved *beyond
     what the market's move explains*.
   - **N2, no crowded shorts:** no short where the crowd is already short
     (negative 7-day funding).
   - **On today's real Bitget data this drops the BTC and ETH shorts.**
     They were shorted only for rising less than the leaders in a rally.
     Instead it shorts DOGE (plus PEPE, which is under the $6 minimum for
     now) and keeps HYPE, ENA, SUI and the XRP short.
2. **Every candidate rule is now scored side by side, on the same prices,
   every day.** This is the new **rule tournament**: 7 rules, including the
   old admitted one, all in paper. The December test has become a live
   record that starts tomorrow.
3. **The disabled scanner can't be made profitable as a trader.** Its fees
   are 5–9 times its edge. **But its kind of information, the intraday
   price range, is now a risk sensor.**
   - Tested today, pre-registered first (round 11), it improved the book's
     Sharpe from 1.56 to 1.84 and cut the worst month from −14.6% to
     −12.2%.
   - It missed the pass mark by a hair (t 1.87 against 1.96), so it runs in
     the tournament, not in the book.
4. **The log and dashboard now say plainly what trades.**
   - A new "What is running" panel: TRADES / PAPER / OFF.
   - The 8-minute summary leads with the book, not the old scanner's 32%
     win rate.
   - Record and fees show the book's own figures.
   - The boot no longer prints "✅ edge is positive" for a scanner that
     lost money.
5. **The 80% target, honestly:**
   - **On history:** N2+N3 at dial 20% + Savings gave an **81%** chance
     that a year averages ≥ 2%/month.
   - **After the usual out-of-sample haircut:** about **60%**.
   - **Months:** about 1 month in 3 still loses, and the worst month was
     −17.7%.
   - **Nothing honest gets "80% of months ≥ 2%".** That needs a Sharpe of
     4–6, and nobody has one.
   - The dial is your decision (section 6).

---

## 1. What changed in the bot (C510)

### What the book trades

| setting | now | the admitted (researched) value |
|---|---|---|
| C2 momentum rule | **N2+N3** (residual momentum, no crowded shorts) | raw 14-day momentum |
| per-coin volatility | 30-day closes | the same |
| sizing | running 60-day | the same |

C1 trend, C3 carry, the vol target, the gross cap, the $6 floor and the
month guard are all unchanged.

**One setting switches the book back or to any other rule, with no code
edit.** Use a systemd override:
- `OMEGA_C2_RULE=base|n2|n3|n2n3`;
- `OMEGA_VOL_EST=close|park|gk`;
- `OMEGA_SIZING=running|k4`.

The commands are at the end.

**Safety:**
- If the bot ever runs **live** on a rule that hasn't passed its test, it
  says so loudly, once, by name.
- Live trading is still double-locked.

### The rule tournament (new)

At every rebalance it builds the book each rule *would* hold today, on the
same prices, the same dial and the same $6 floor. From the next day it
scores them all identically. Nothing in it trades.

| rule | what it is | what the research found |
|---|---|---|
| admitted C488 rule | raw 14-day momentum | +32.6%/yr, Sharpe 1.56, max DD 31.4% |
| N2 | no crowded shorts | +2.8%/yr better, t 1.02 (pass mark 2.13) |
| N3 | residual momentum | +2.1%/yr better, t 0.82, max DD 25.3% |
| **N2+N3 (traded)** | both | max DD 22.6% vs 29.5%; 2022 −8% vs −12% |
| N2+N3, K4 sizing | fast 10-day volatility memory | worst month −9.7% vs −15.5% |
| N2+N3, range vol | the scanner's information as a sensor | +4.3%/yr, t 1.87 (pass mark 1.96) |
| N2+N3, K4, range vol | everything | descriptive only |

The traded rule's own row is also **a check on the book**. The paper book
and its tournament row should differ only by execution: the $6 minimum
order, the 30% band, quantity steps, and fills at the bid/ask.

### Where it shows

- **Dashboard:**
  - "What is running";
  - a rule line on the book;
  - a "Rule tournament" panel;
  - the Record tile shows the **book's** record (3W 8L, −$8.47 net so far),
    with the old scanner's 44W/95L labelled "off".
- **Log:**
  - `RULE` and `TOURNEY` rows in every 8-minute block;
  - `🏁 C510 tournament` after each rebalance;
  - a `🎯 C510 Book (what trades)` line in each summary.

---

## 2. What N2+N3 changes in practice (real Bitget data, 28 Sep close)

| | admitted rule | N2+N3 |
|---|---|---|
| momentum shorts (chosen Monday) | **BTC, ETH**, TRUMP, XRP | DOGE, PEPE, XRP |
| momentum longs | ARB, ENA, NEAR, SUI | ENA, NEAR, ONDO, SUI |
| book at $241 | BTC −$14.77, ETH −$13.86, HYPE +$11.87, ENA +$11.40, XRP −$8.40, SUI +$7.53 | HYPE +$10.90, ENA +$10.48, XRP −$7.74, TRUMP +$7.20, DOGE −$7.03, SUI +$6.94 |
| gross | 0.28× | 0.21× |

**Why it differs:**
- **BTC and ETH:** the admitted rule shorted them because they rose ~7% in
  14 days while NEAR rose 95%. Residual momentum sees that BTC and ETH
  *always* move less than small coins (low beta). Their rise was normal for
  them, so it doesn't short them.
- **TRUMP:** its funding was negative (the crowd is short). So N2 removes
  the momentum short, and the carry sleeve's long remains.

This is exactly the squeeze risk that cost us PUMP, WLD and LINK last week.

---

## 3. How the rules did in every kind of market (history, 2020–26)

Book + idle cash in Savings (5%/yr), dial 15%, per calendar year. 2026 is
January–August. These are **descriptive only**: N2+N3 was chosen after
seeing its parts, so this history can't prove it.

| year | market | admitted rule | N2+N3 | N2+N3 + K4 |
|---|---|---|---|---|
| 2020 | bull starts | +28% | +40% | +31% |
| 2021 | mania | +48% | +52% | +51% |
| **2022** | **crash (LUNA, FTX)** | **−12%** | **−8%** | **−9%** |
| 2023 | recovery | +60% | +63% | +40% |
| 2024 | bull | +65% | +63% | +73% |
| 2025 | mixed | +42% | +58% | +47% |
| 2026 | chop | +37% | +35% | +45% |
| **max drawdown** | | 29.5% | **22.6%** | **21.5%** |
| worst month | | −14.5% | −13.6% | **−9.7%** |

### How each kind of market is handled

| market | what protects or earns |
|---|---|
| strong trend up or down | C1 trend follows it both ways; the spot pot rides up-trends and sits in cash in down-trends |
| rotation (some coins lead) | C2 momentum, long the leaders and short the laggards; N3 stops it shorting slow coins just for being slow |
| crowded, squeezy markets | N2 doesn't short a coin the crowd is already short; C3 carry is *paid* to take the other side of crowded longs |
| sideways / chop | carry earns funding; Savings earns on idle cash; the 30% band and $6 floor keep trading costs down |
| volatility spikes | the vol target cuts size as volatility rises (K4 and range vol react faster; both are in the tournament) |
| crash | the month guard closes the book if the month's loss reaches the dial (15% → $37.92 in September) |
| broken data | the C499 rule (no trade on incomplete history) and the C504 watchdog on every feed |

**What no rule can do:** avoid losing days and weeks. In every version above,
about 1 month in 3 lost money.

---

## 4. The 80% question, straight

**"80% probability" can mean two different things:**

| | history | after the usual ⅓ haircut for real-life trading |
|---|---|---|
| **a year averaging ≥ 2%/month**, N2+N3, dial 15% + Savings | 75% | 50% |
| same, **dial 20%** | **81%** | **60%** |
| admitted rule, K4 sizing, dial 20% | 80% | 59% |
| **a single month ≥ 2%** (any rule, any dial) | 46–58% | 39–47% (C504) |

The first kind is reachable on history at dial 20%. The second is not
reachable by anything honest. The arithmetic (from C504): 80% of months at
≥ 2% needs a Sharpe of 4–6. Long-run trend-following funds run about 0.5–1; ours
is about 1.6 on history.

**What dial 20% costs:**
- the worst month goes from −13.6% to −17.7%;
- the worst drawdown from 22.6% to 36.6%;
- 2022 would have been −21% instead of −8%.

### Why the refinements can't be "proven" quickly

At their size (+2–4% a year better, with about 6–7%/yr of noise between
them and the base):

| rule | forward data needed to prove it on its own (t ≈ 2) |
|---|---|
| range volatility (GK) | about 7 years |
| N2 | about 28 years |

That isn't a flaw in the method. Small improvements to a noisy strategy
really are that hard to prove. So which rule goes live is a
**judgement**, made on four things:
- a strong reason to expect it to work;
- consistent history (every quarter, and 2025–26);
- no harm to the drawdown;
- the paper book tracking its own tournament row.

N2+N3 passes the first three on history. The fourth starts tomorrow.

---

## 5. The disabled bot: can it be integrated?

**As a trader: no, and I want to be precise about why.**
- **Its record:** 139 trades, 44 wins and 95 losses.
- **What the audits found (C487, C489, C500):** its fees and spread were
  5–9 times the edge it could measure. 2%/month would need 0.13–0.22% of
  gross edge per trade, 8–13 times the best ever measured.
- **Tuning can't fix it:** changing its entry rules changes *which* trades
  it takes, not the cost of each one.

**As a sensor: yes, and I tested it today.**
- **The idea:** the scanner watched prices inside the day. The daily high
  and low carry that information: a coin that swings 12% intraday but
  closes flat is riskier than its close-to-close number says.
- **The two estimators:** Parkinson and Garman–Klass turn the high and low
  into a volatility estimate that reacts faster without getting noisier.
- **The test:** round 11, pre-registered and pushed before any data
  (`research/c510_preregistration.md`, commit f42a18c):

| | vs admitted | t | pass mark | quarters | 2025–26 | max DD | worst month | worst day |
|---|---|---|---|---|---|---|---|---|
| Parkinson | +3.6%/yr | 1.79 | 1.96 | 3/4 | +0.9%/yr | 29.5% | −12.8% | −7.1% |
| Garman–Klass | **+4.3%/yr** | **1.87** | 1.96 | 3/4 | +1.5%/yr | 30.1% | −12.2% | −7.3% |
| admitted | | | | | | 31.4% | −14.6% | −8.5% |

Both improve everything (Sharpe 1.56 → 1.84) but miss the pass mark. As
promised in advance, that's recorded as a fail. So it runs in the
tournament, where its forward record starts tomorrow.

The intraday shadow (C489) keeps measuring hourly too. The idea stays
available if its record ever changes.

---

## 6. The philosophy, in one page

1. **Earn from risks others pay to shed; don't predict.**
   - **Trend:** people underreact, then herd.
   - **Momentum:** leadership persists for weeks.
   - **Carry:** crowded longs pay funding.
2. **Size by risk, never by hope.**
   - The book aims at one volatility (dial × 4/3), and each sleeve gets
     equal risk.
   - Adapting risk is automatic and continuous: the vol target, the Savings
     reserve, and (in the tournament) K4 and the range sensor.
3. **Change rules only on evidence, never on last week.**
   - This is why rules are scored side by side forward, not chosen by
     recent results.
   - Round 5 tested "shift weight to whatever just worked": it lost
     14.6%/yr.
4. **One loss control, on marked equity:** the month guard. There are no
   per-position stops: every position is re-decided daily, and the guard is
   the one thing that closes the book.
5. **Everything talks to everything, through data, not opinions:**
   - **funding** feeds carry and N2;
   - **the market's own move** feeds N3;
   - **each coin's range** feeds the risk sensor;
   - **the book's margin and your dial** feed the Savings reserve;
   - **every feed** is checked by the watchdog;
   - **every rule** is scored by the tournament.
6. **Paper first, the same code as live, and say what's true.** The screens
   now show what trades, what is paper, and what is off.

---

## 7. Your decisions

1. **The dial.** 15% now.
   - **20%** is the historical "80% of years" setting, with worst months
     near −18%.
   - How to change it: Dashboard → Controls → Monthly risk → 20 → Set. It is
     saved across restarts.
   - **My view:** stay at 15% until the paper book has run the N2+N3 rule
     for a month and matched its tournament row. Then decide.
2. **The rule.** N2+N3 in paper now. To trade the admitted rule again, use
   `OMEGA_C2_RULE=base` (below).
3. **Live, when you're ready:** the checklist in Atlas pending #2 and #3
   (API key trade-only, no withdrawals, IP allow-list), and a CA's view (#8).

---

## Deploy C510 (Termius)

This time the log upload script changed too, because it now uploads the
tournament's file.

```bash
sudo -u omega git -C /home/omega/omega pull
sudo cp /home/omega/omega/deploy/omega-logpush.sh /usr/local/bin/omega-logpush.sh
sudo chmod +x /usr/local/bin/omega-logpush.sh
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|RULE|C510|DATA|Traceback"
sudo -u omega /usr/local/bin/omega-logpush.sh --check
```

**What you should see:**
- `OMEGA C510`;
- a boot line `RULE   C2 N2+N3: … a FORWARD TEST in paper`;
- no Traceback;
- the dashboard's new "What is running" and "Rule tournament" panels. The
  tournament says "starts at the next rebalance" until 05:35 IST.

**Only if you want the book back on the admitted rule:**

```bash
sudo mkdir -p /etc/systemd/system/omega.service.d
printf '[Service]\nEnvironment=OMEGA_C2_RULE=base\n' | sudo tee /etc/systemd/system/omega.service.d/c510-rule.conf
sudo systemctl daemon-reload
sudo systemctl restart omega
```

To undo it:

```bash
sudo rm /etc/systemd/system/omega.service.d/c510-rule.conf
sudo systemctl daemon-reload
sudo systemctl restart omega
```

---

## Fresh start at dial 20% (the operator's choice, 29 Sep)

**Is it OK?** Yes. It's paper money, and a fresh start is the cleanest way to
measure the new rule at the new dial: every figure on the screens will
describe exactly what is running.

**Three things to know:**
1. **The screens start again at $250.** That includes the book's record, the
   paper ledgers (spot pot, carry, Savings, K4, intraday shadow, tournament)
   and the old scanner's 139 trades. Nothing is lost: every log and state
   file is on the logs branch, and the Atlas has the numbers.
2. **Dial 20% means bigger swings.**
   - The month's loss budget is $50.
   - The volatility target is 26.7% (it was 20%).
   - History had worst months near −18% and drawdowns up to about 37%.
   - Judge it over months, not days.
3. **The order matters.**
   - The fresh start takes its dial from the service setting `OMEGA_MAX_DD`,
     which your unit sets to 15. A dial chosen on the dashboard *before* the
     fresh start would be overwritten.
   - Choosing it *after* the fresh start comes too late: the book builds
     within a minute of starting.
   - So the commands below set 20 in a small override file first. That
     setting only matters at fresh starts; afterwards the saved dial wins as
     usual.

**Tested before sending.** I ran this exact sequence in the sandbox on live
Bitget data.
- **A bug was found and fixed:** C510 had broken the carry ledger (it crashed
  reading the wider price history). The regression test is in
  `omega_c510_test.py`.
- **After the fix:** fresh $250, dial 20%, month budget $50, rule N2+N3, and
  11 positions built in a minute (0.42× gross): HYPE, ENA, TRUMP, SUI, NEAR
  and ZEC long; XRP, DOGE, PEPE, UNI and FIL short. Carry, spot pot and
  Savings all ran.

```bash
sudo -u omega git -C /home/omega/omega pull
sudo cp /home/omega/omega/deploy/omega-logpush.sh /usr/local/bin/omega-logpush.sh
sudo chmod +x /usr/local/bin/omega-logpush.sh
sudo mkdir -p /etc/systemd/system/omega.service.d
printf '[Service]\nEnvironment=OMEGA_MAX_DD=20\n' | sudo tee /etc/systemd/system/omega.service.d/c510-dial.conf
sudo systemctl daemon-reload
sudo -u omega touch /home/omega/omega/data/FRESH_START
sudo systemctl restart omega
sleep 120
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 300 --no-pager | grep -E "FRESH|OMEGA C5|RULE|month anchor|REBALANCE|C510|Traceback"
sudo -u omega /usr/local/bin/omega-logpush.sh --check
```

**What you should see:**
- `FRESH START requested ... flag consumed`;
- `OMEGA C510 ... risk dial 20%/month`;
- `RULE   C2 N2+N3`;
- `C488 month anchor 2026-09: $250.00 (marked; budget 20% = $50.00)`;
- `C488 REBALANCE (first): ... vol target 26.7%, rule C2 N2+N3`;
- `C510 tournament`;
- no Traceback.

The dashboard's Controls should show the dial at 20.

---

## Files

**Bot:** `omega_v60_reconstructed.py` (C510).

**Tests:**
- `omega_c510_test.py`: 45 checks, Chromium included;
- battery: 35 of 37 pass in parallel. `omega_exit_test.py` needs
  `corpusL/`, as before. `omega_c467_remote_test.py` is a 1-second timing
  check that failed under parallel load and passes alone.

**Research:**
- `research/c510_preregistration.md` (pushed before any data);
- `research/omega_c510_research.py` and `c510_results.txt/.json`;
- `research/c510_normal_range.py` and its `.txt/.json` (N2+N3's "is this
  normal?" table).

**Tools:** `research/c498_plan_replay.py` now replays with the rule and
high/low saved beside each day's inputs.
