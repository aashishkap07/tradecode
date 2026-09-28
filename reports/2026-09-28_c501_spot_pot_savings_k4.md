# C501: the second $250 in spot, idle cash in Savings, and the allostatic shadow

**Date:** 28 Sep 2026
**What changes for your money:** nothing. All three new pieces are **paper
ledgers**: they measure and never trade. They let testing start today, so the
evidence is there when you decide to go live.

## 1. The spot pot: a second $250, tested first

Before building anything I wrote the rule down and pushed it (commit
13a0875), then tested it on 6 years of real prices. **It passed every
pre-set bar.** It is the first new strategy admitted since the book itself.

**The rule, in plain words:**
- Look at the 20 most-traded real cryptocurrencies.
- **Hold a coin only while it is trending up** (up over most of the last 7,
  14, 28 and 56 days); otherwise stay out. Spot can't short.
- **Size each coin by its own bumpiness:** a coin that swings twice as much
  gets half the money. This is the "relativistic" part: every coin is
  measured in its own units.
- **Self-adjusting:** the whole pot is held at a steady risk level (20% a
  year), and never more than 100% invested. In calm uptrends it holds more;
  in storms or downtrends it holds less or nothing.
- **Cash earns Savings** (7.63% today). Fees are 0.08%, with the BGB discount.

**Why spot and not futures for this:** a futures long pays funding to the
shorts (about 10% a year on average, more when the crowd is long). A spot
coin pays nothing. For a strategy that is only ever long, spot is simply
cheaper.

**6 years of results (2020 → Aug 2026):**

| | spot pot | futures book (dial 15%) | **both together, $250 + $250** |
|---|---|---|---|
| growth | +2.20% a month | +2.55% a month | **+2.47% a month** |
| worst drop | 27% | 31% | **19%** |
| worst month | −10.2% | −15.5% | **−5.8%** |
| months ≥ +2% | 31% | — | 44% |

**The two pots barely move together** (correlation +0.14), so together they
are much steadier than either alone. By year, the spot pot made +39, +77, −6,
+46, +20, +7 and +23% (2026 to August).

**Be aware:**
- **Most months are quiet** (median +0.4%): it earns its money in the
  trending months.
- **It is invested only about a quarter of the time on average.**
- **Today (28 Sep) only BNB, BTC and ETH qualify**, so it would be 10%
  invested, with $224 earning Savings. That's normal in a choppy market.

## 2. Idle cash in Savings

**What the ledger does:** the futures book locks only its margin (about 10%
of the account). The ledger works out, every minute, how much could safely
sit in Savings:

> reserve = margin + your dial's monthly loss budget + 5% buffer

Everything above that is idle. It adjusts by itself: a bigger book or a
higher dial keeps more in the futures wallet.

**Today:** $170.67 of $243.95 is idle (70%). At 7.63% that's **about $1.09 a
month, +0.45%**. It's shown on the dashboard; nothing is moved yet.

## 3. The allostatic shadow (K4)

**What it does:** at every rebalance the bot now builds the book two ways
from the same data:
- the **current way**: risk measured over the last 60 days;
- **allostasis**: risk measured with a 10-day memory, reacting faster.

It scores both identically every day. In the 6-year test the allostatic way
earned the same, but its **worst month was −9.7% instead of −15.5%**.

**Today** it would hold 0.66× against the current 0.40×: calmer recent days
make it more willing. It adjusts both ways.

**What happens next:** it only takes over the real book if it passes again
on **new** data at the December refresh.

## 4. Everything pending, remembered in the Atlas

| # | item | status |
|---|---|---|
| 1 | paper check of the book | reminder 29 Sep 06:45 IST (now includes C501) |
| 2 | live mode for the book | built, switched off |
| 3 | security before any live key (rotate the NewsData key and the control token; trade-only API key) | **your action**, before live |
| 4 | intraday shadow review | monthly reminder |
| 5 | research refresh | reminder 2 Dec |
| 6 | **dial choice** | yours: 15% + Savings ≈ 2.1%/month, 20% + Savings ≈ 2.8%/month; **both pots ≈ 2.5%/month historically, worst month −5.8%** |
| 8 | tax (CA) | also ask about **1% TDS on spot sales** for the spot pot |
| 10 | carry ledger → account | after a CA's view |
| 11 / 16 | forward re-tests incl. **allostasis** and the horizon ensemble | 2 Dec |
| 14 | **idle cash to Savings, live** | paper ledger running; build with the live switch |
| 15 | **the spot pot, live** | paper pot running; needs a spot order path, $250 in the spot wallet, a little BGB with "pay fees in BGB", and the tax check |
| 17 | keep the Savings rate current | monthly reminder |
| 18 | ETH's $27 minimum step at $250 | known; fades with size |

## 5. Deploy C501 (Termius: you're already on the server)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 120
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 300 --no-pager | grep -E "OMEGA C5|C501|SPOT|SAVINGS|Traceback"
```

**What you should see:**
- `OMEGA C501`.
- On the dashboard, two new panels: **Spot pot (paper, second $250)** and
  **Idle cash → Savings (paper)**. The Portfolio book panel gets an
  "allostatic shadow (K4, paper)" line; it says "starts at the next
  rebalance" until 05:35 IST.
- The Savings panel fills within a minute.
- **The spot pot makes its first run a minute or two after the restart.**
  It is due every day after 05:50 IST and hasn't run today; it takes about a
  minute to fetch 80 coins of history. Then it runs daily at 05:50 IST. Look
  for `🪙 C501 spot pot (paper) …` in the log.

**After 05:50 IST on 29 Sep** (the book's rebalance, K4's first
observation, the carry ledger and the pot's second run):

```bash
sudo journalctl -u omega --since "05:30" --no-pager | grep -E "C488 PLAN|C488 REBALANCE|C501|C490 carry"
```

This is a normal restart. The book, the carry ledger and every position are
kept.
