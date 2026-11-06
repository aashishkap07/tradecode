# Round 24 pre-registration: hidden risks and profit in the running plan (Delta + CoinDCX, 10 × 10%)

Committed and pushed **before** any test below runs. 10 Oct 2026, ~01:15 IST.

## Why

**The operator (10 Oct, with the 00:40 IST dashboard):** "analyse carefully to the core, excavate any hidden issues ...
discover any possibilities of profitability enhancement or sustainance..proceed accordingly".

**What the screens and the live data showed** (verified against the ledger and Delta's and Binance's marks, 00:50 IST):
- **F1: each account is one-sided.**
  - 7 of the 10 pairs are "short Delta / long CoinDCX": Delta India's longs usually pay more rent.
  - So the CoinDCX account holds about $700 of long legs and $300 of short. Delta holds the mirror image.
  - Each pair is neutral, but **each account is not**: a broad altcoin crash takes money from the CoinDCX
    account and gives it to Delta, all at once.
  - Every test so far used **daily closes**, which hide intraday wicks. The crash of **10–11 Oct 2025** has never
    been replayed minute by minute.
- **F2: STRK rose +38.8% within 18 hours on 9 Oct.** The 06:00 IST mark was 0.05565; the 9 Oct 22:00 IST high was 0.07725.
  - That is the plan's CoinDCX short leg.
  - A leg on isolated margin of 1/3 of its size (one of Round 23's candidates) would have been liquidated.
  - Under the plan's cross margin, the accounts went to 114% / 86% and nothing broke.
- **F3: a weak pair holds a slot.** FARTCOIN's gap is 21%/yr, just above the 10% exit and far below the newer
  candidates. The rule never swaps a held pair for a much better one.

## Data and engine (fixed now)

- **Engine:** Round 22's (`research/c542_pairs.py`: `legs` for profit and tax, `research/c531_split_600.py`: `sides`
  for each account with the 65% even-out).
  - The cache is rebuilt from the same public endpoints, for 2024-10-01 → 2026-09-30.
  - Delta + CoinDCX, CoinDCX's coins with ≥ $100k a day on Delta and the same asset, as Round 22's pair C.
  - Costs ×5 for every bar; ×1 is also reported.
  - Tax T1 at 31.2%.
- **Engine check:** with no new rule switched on, the new code must reproduce Round 22's `legs` net and `sides`
  lowest account exactly. Otherwise nothing below is read.
- **Minute data** (test A only):
  - Delta India's 1-minute **mark** candles (`MARK:<symbol>`);
  - Binance's 1-minute **mark-price** klines (CoinDCX's legs: its rent and prices follow Binance's; gate G2).
  - Mark prices are what exchanges liquidate on.

## A. The 10–11 Oct 2025 crash, minute by minute (descriptive; no adoption from A alone)

- **The book:** the pairs the base plan held after its 10 Oct 2025 00:30 UTC decision, at their sizes.
  - Each account starts the day at its value from `sides` that morning.
- **The path:** each account's value every minute from 10 Oct 2025 00:30 UTC to 11 Oct 2025 00:30 UTC, from its own legs'
  mark-price moves. Rent is ignored inside the day.
- **Reported:**
  - each account's lowest value, as a share of its start;
  - the minute that happened;
  - which legs did it.
- **Margin modes compared** (the input to Round 23 and B2):
  - (i) **cross margin:** the account is wiped out if its value falls to its maintenance margin. Taken as 0.5% of
    the notional held there; CoinDCX's and Delta's exact tiers are read and reported if public;
  - (ii) **isolated margin, 1/3 of each leg's size:** a leg is liquidated when its adverse mark move reaches about
    1/3 minus 0.5% maintenance;
  - (iii) **isolated margin, 1/2 of each leg's size**, the same way.
- **Also replayed:** the base plan's 5 worst days for the poorer account by daily close in the 24 months,
  minute by minute, the same way.

## B. Swap a weak pair for a much better one (profit)

At each daily decision, after the normal exits and entries:
- **When it applies:** every slot is full, and the best waiting candidate's 7-day gap beats the weakest held pair's
  by at least Δ.
- **What happens:** the weakest is closed and the candidate opened, both legs, all four sides' costs paid.
- **Limit:** at most one swap per day.

| variant | Δ |
|---|---|
| S40 | 40%/yr |
| S80 | 80%/yr |

**A swap variant replaces today's rule only if, at costs ×5, all of these hold** (Round 22's Part B bar, plus Round
19's paired-difference bar, because two variants are tried):
1. every Round 22 Part A bar holds on every wobble list:
   - G1: average month ≥ +1.5%, no month below −4%, the poorer account ≥ 40%;
   - HAC t ≥ 2;
   - both years positive;
   - the five largest-P&L coins removed in turn, and turnover floors $75k and $150k;
2. it earns ≥ **$50 a year more after tax** (T1) than today's rule;
3. at most **one more losing month**;
4. the daily difference against today's rule has **HAC t ≥ 2.5** and is positive in **≥ 3 of the 4 half-years**;
5. at costs ×1 it is also ahead.

## C. A cap on one-sidedness (sustenance)

- **The rule:** at most K of the held pairs may face the same way. Candidates that would break the cap are skipped
  for the next best.

| variant | K (of 10) |
|---|---|
| K7 | 7 |
| K6 | 6 |

**A cap is adopted only if, at costs ×5, all of these hold:**
1. **Safer:**
   - the poorer account's lowest point (daily `sides`) improves by ≥ 5 points, **or** the even-out transfers a
     year fall by ≥ 30%;
   - **and** test A's crash replay is no worse for either account.
2. **Costs little:** after tax it earns at least today's rule's figure **minus $30 a year**.
3. **Still passes:** every Round 22 Part A bar holds on every wobble list.

**If both a swap and a cap pass:** their combination is run once as a confirmation, against both bars, before
anything changes.

## D. Is the edge fading? (descriptive)

- **Monthly series:**
  - the average |7-day gap| of the 10 widest allowed coins;
  - the base plan's monthly net (costs ×5).
- **Trend:** the slope per year, with its HAC t.
- **Compared:** the last 6 months' average against the first 18 months'.
- **No rule changes from D.** If the slope is negative with t ≤ −2, the plan's expected return is re-based in the
  timeline and the monthly review watches it.

## What happens next

- **A swap or a cap that passes** goes into the bot's paper ledger. It is tested, and the 10 × 10% daily rule
  keeps its name. **If none passes, the plan is unchanged.**
- **A's result goes straight into Round 23 (22 Oct) and B2 (15 Nov):** which margin mode, and how much buffer each
  account needs against a market-wide wick.
- **Nothing here touches real money.** `C488_LIVE_OK` stays False.
