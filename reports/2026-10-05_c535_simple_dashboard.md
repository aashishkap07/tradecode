# The dashboard, simplified (C535)

5 Oct 2026. You asked me to go through the 18:19 IST screens word by word, simplify the layout in plain
English, and remove whatever was said twice.

## 1. The screens were correct

Checked against both exchanges' 1-minute prices at 12:49 UTC (18:19 IST):

| on screen | checked |
|---|---|
| plan **$996.00** (−$4.00) | **$995.92** (positions at real prices + $0.98 rent settled since 06:00) |
| Delta account **$485.17** (97%) / Pi42 **$509.84** (102%) | $484.47 / $510.47 (the screen's snapshot is a few minutes off; the total agrees) |
| ledger **$995.21** | $1,000 + $2.27 rent − $4.87 fees − $1.19 prices − $1.00 transfer = **$995.21** exactly |

## 2. What each old part of the page was, and where it went

| old | what it really was | now |
|---|---|---|
| header "NORMAL · up 1138.2 min · daily book, next rebalance 00:05 UTC" | "NORMAL" and the 00:05 UTC rebalance belong to the experiment book, not your plan | "no real money moves · running 18 h 58 min · prices up to date" |
| YOUR PLAN tile | your money, plus a line about the experiments | **Your money**: value, change since $1,000, after tax, the goal; the experiments moved out |
| RISK tile "97% weaker side" | the poorer of your two accounts | **Your two accounts**: both balances, % of the $500 each started with, a bar with the 65% and 50% lines, health in words, the last money move |
| PLAN SO FAR tile | the same −0.40% again | removed (said twice) |
| SCANNING tile | the experiment book's schedule | folded |
| WHAT IS RUNNING | a list of everything, mostly experiments | folded; its point (your plan, paper, live locked) is in **What happens next** |
| ALL ACCOUNTS (AS IF LIVE) | your plan's value three times, then the experiments, tax, budget | folded; the tax line is in **Your money** |
| OPEN POSITIONS "no intraday positions…" | the old scanner, which is off | folded |
| PORTFOLIO BOOK, RULE TOURNAMENT, INTRADAY ENGINE, CASH-AND-CARRY, SPOT POT, SAVINGS, BFUSD, DELTA BOOK | experiments, not your money | folded under **Experiments and details**, with a one-line summary of their results |
| CROSS-VENUE FUNDING (a long paragraph and 10 dense lines) | your 10 pairs | **Your pairs**: a table of coin, the bet on each exchange (↓ down / ↑ up), the gap a year, rent so far, days; totals in two lines |
| PENDLE (off), EQUITY THIS SESSION (the experiment book's chart) | not your plan | folded |
| CONTROLS, LOG | tools | folded, one tap to open |

**The new page, top to bottom:**
1. Your money.
2. Your two accounts.
3. Your pairs.
4. What happens next. Times are in IST: the next daily run is 06:00 IST, with a countdown.
5. Three folded sections: Experiments and details, Controls, Log.

There are no internal codes (C5xx), no UTC times and no jargon (leverage, margin, cross-venue) in the
top part. Nothing was deleted; the detail is one tap away. If the plan isn't running, the old panels
open by themselves, as before.

## 3. Checked

- `omega_c535_test.py`, 15 checks:
  - the four plain sections and their words;
  - the folds;
  - no jargon at the top;
  - the account wording at healthy, under 65% ("Getting low") and under 50% ("Move money now");
  - the no-plan fallback;
  - 412 px width, no JavaScript errors.
- The 8 older page tests now open the folds before reading the panels they check.
- Full battery: **56 of 56** pass.
- Previewed on the server's 18:17 IST state: `reports/2026-10-05_c535_preview/`.
