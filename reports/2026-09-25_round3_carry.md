# Round 3, the carry ledger, and the shadow as a dollar account — 25 Sep 2026 (C490)

## Your three questions

**1. Is the "Intraday engine (shadow)" the old complex engine?**
- **No.** It is the new C489 engine I built on your principles:
  - relativistic inputs;
  - predictive (it forecasts the next 4 hours);
  - a probability model;
  - chaos measures (entropy, Hurst);
  - Markov chains.
- **The old intraday scanner (C487) is switched off.** It only comes back if
  someone sets `OMEGA_ENGINE=intraday`.

**2. Why was it waiting 7 days before scoring?**
- **One of its inputs is buy/sell pressure** (taker flow), and Bitget only gives
  the last 30 hours of it. So the engine had to collect a week of it first.
- **Fixed.** It now starts scoring in its first hour with a version of the
  model trained without the flow inputs, then switches to the full model once it
  has a week of flow.
- **That warm-up model is not a shortcut to profit.** Tested on 2021–26, it
  loses after fees just like the full model.

**3. Can it run as a duplicate paper account?**
- **Yes, it now does.** The panel shows it in dollars, starting from your
  account's equity on the day it began:
  - "duplicate paper account from $X — never touches the real one";
  - its $ balance, $ profit or loss, open positions and exposure.
- **It can never move your real (paper) account.** The tests prove that.

## Round 3: four new ideas, tested honestly

The plan was committed before any test, so nothing could be cherry-picked. Data
covers 2021–2026, with all coins including dead ones and real fees and funding.

| Idea | What it does | Result |
|---|---|---|
| **Limit-order market making** | Leave buy/sell orders 2 "normal moves" away from the price, take profit when the price snaps back | ❌ −480%/yr (see below: not settled) |
| **Per-coin strategy choice** | Each coin picks its own best style (trend / reversal / flat) from the last 60 days | ❌ −59%/yr |
| **Cash-and-carry** | Buy the coin on spot, short the same amount of its futures, collect the funding | ✅ **+2.2%/yr, very low risk. PASSED** |
| **Per-coin trend speed** | Each coin gets its own trend lookback instead of the average of four | ❌ worse than the average |

### The carry trade (passed)

**How it works:** when futures buyers pay a high funding fee, you buy the coin
and short its future. The price moves cancel out, and you collect the fee.

**The honest numbers:**
- It adds only about **+0.2% a month** at the size that fits your account.
- It **lost money in 2025 (−4.6%) and 2026 so far (−2.0%).** Large funds now do
  this trade at huge size, which squeezes the fees.
- **Tax risk for India:** if each leg is taxed on its own gain with no loss
  offset, you could owe 30% on the winning leg while the losing leg's loss is
  wasted. That alone can turn it into a loss. **Ask a CA before this ever uses
  real money.**

**So it runs as its own paper ledger in dollars,** exactly as tested, on a new
"Cash-and-carry (paper ledger)" panel. It never touches your account.
- On today's live data it found 37 eligible coins, 17 paying above 10% a year,
  and entered 8.
- Moving it into the account later needs three things:
  - a spot-trading path in the bot;
  - the book's implementation check (due 29 Sep);
  - your CA's view on the tax.

### The market-making idea: failed, but not settled

- **My test used hourly price bars, which can't show what happened inside the
  hour.** Did the price hit your stop-loss first, or your profit target?
  - Assuming "stop first" (the cautious assumption): **−480% a year**.
  - Assuming "target first": **+165% a year**.
  - The truth lies somewhere between.
- **This is the one intraday idea with a real chance.** It is the only design
  that avoids paying the taker fee to get in, and the research literature says
  short-term reversals are exactly a reward for providing liquidity.
- **So I have already committed Round 4:** the same rule, re-tested on
  **1-minute prices**, with the cautious assumption as the pass bar.
  - If it passes, it becomes the intraday engine on the paper account.
  - If it fails, or the answer is "can't tell", nothing ships.

## The best way to 2–4% a month

| Source | Average month (history) | Status |
|---|---|---|
| Daily portfolio book (trend + momentum + carry sleeves), risk dial 15% | +2.5% (realistic 1.5–2%) | **Trading your paper account** |
| Same book at dial 20% | +3.3% (realistic 2–2.5%), worst drop −40% | Your choice |
| Cash-and-carry | +0.2%, recently negative | Paper ledger |
| Intraday probability engine (C489) | loses after fees | Shadow (dollar ledger) |
| Limit-order market making | unknown: −480% to +165%/yr on hourly data | Round 4 (1-minute test) next |

**My honest view as a trader:**
1. **The daily book is the engine that makes money.** 2–3% a month is realistic
   only at dial 15–20%, and only with drawdowns of 30–40% along the way.
2. **4% a month is not reachable** without risking the account.
3. **Intraday trading at retail fees is a fee-paying machine** unless you are
   the one providing liquidity. That is why market making is the one intraday
   idea still worth testing.
4. **Tuning each coin separately made things worse** (tested twice this
   round). With only a few years of data per coin, "individual" settings mostly
   fit noise. One rule for all coins, scaled to each coin's own volatility, is
   more robust.

## Deploy (Termius: you're already on the server)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 120
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 150 --no-pager | grep -E "OMEGA C4|engine:|C488 REBALANCE|C489 shadow|C490 carry|Traceback"
```

**What you should see:**
- `OMEGA C490`;
- a `C489 shadow hour … coins scored (warm-up (14, no flow))` line, with dollar
  amounts;
- `C490 carry (paper ledger) …: … N held, … eligible above 10%/yr`. It runs
  once at start-up, then every day at 05:40 IST.

**On the dashboard:**
- the shadow panel shows "duplicate paper account from $…";
- there is a new **Cash-and-carry (paper ledger)** panel.

The existing book and positions are kept. This is a normal restart, not a fresh
start.
