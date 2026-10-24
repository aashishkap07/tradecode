# Trade forensics — the 34 trades since C485 (24 Sep 00:36 → 25 Sep 07:17 IST)

Every trade checked against Bitget 1-minute candles from 3 hours before entry to 4 hours after exit,
and compared with how the same style of entry did across every coin the bot has traded, in the same hour.
Regenerate any time with `python3 omega_live_forensics.py <logs-folder> <work-folder> --ver C486 --market`.

## The answers, in plain English

**Why the numbers "reset".** The bot was stopped by the server at 06:14:55 on 25 Sep (and at 06:54 on 23 Sep):
both times inside 06:00–07:00, when Ubuntu installs its daily security updates and restarts services that use
updated libraries. Nothing was lost — positions and stops carried over — but the dashboard only showed
*this run's* numbers, and its "session" figure had a bug that made it read +$0.00 always. Fixed in C486: the
tile now shows this run, today (survives restarts) and the all-time record.

**What went wrong.** 34 trades, 9 wins / 25 losses, −$5.92.
1. *Size* — since C482 every trade is full size all day; a hard stop now costs about $0.80 instead of $0.50.
2. *The market* — on the morning of 25 Sep this entry style lost money on almost every coin.
3. *24 Sep* — the market suited this entry style, yet the bot's picks did 0.9% worse per trade than
   same-style entries in the same hour. The only thing that changed the picking was C485 turning off two
   small votes, so C486 turns them back on (exactly as before) and records them on every trade.

**Could the losses have been prevented?** 13 of the 25 losses (−$5.66) were never meaningfully in profit
(best point under +0.5%) — only *not entering* avoids those. The other 12 (−$4.70) were up first, then fell
back. Moving the stop to breakeven, locking part of the peak, trailing, or exiting early on a timer would have
saved some of these but cost more on other trades: tested on all 164 trades since 19 Sep, **none of them beats
what the bot actually did** (table below). So the losses were not an exit mistake — they come from entries that
carry no edge: the bot buys coins that already ran ~4% in 3 hours, near the top of their range, and across
7 months of history that style loses money on its own after fees.

**Was the profit maximally extracted?** Close to the best that a real rule could have taken. After a winning
exit, price fell on average 0.6% within the hour and 1.1% within 4 hours (57% of the time it ended more than 1%
below the exit), so the exits mostly sold near a local top. There was a brief extra +0.9% (median) available in
the next hour, but it reversed too often to be captured by any rule tested.

## Every trade

All % are price moves in the trade's direction (+ = good for the trade). Best/worst = while open (Bitget 1-minute candles). Ran-up = the coin's move the trade's way in the 3 h before entry. Range = where the entry sat in the last 3 h (100% = at the extreme the trade chases). After exit = from the exit price.

| # | opened → closed (IST) | coin | side | size | result | exit reason | best / worst | ran up 3h | range | after exit 1h / 4h | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23 Sep 23:36 → 00:54 | PUMP | short | $35×1 | **$-0.08** | C399_CONVICTION_COLLAPSE | +1.0 / -0.5 | +2.6% | 90% | -0.1 / -0.6 | was up +1.0% first, then gave it back; little changed after |
| 2 | 24 Sep 00:39 → 01:31 | ARB | short | $31×1 | **$-0.25** | C399_CONVICTION_FADING | +0.3 / -0.9 | +2.1% | 97% | +1.0 / +2.3 | wrong from the start (never above +0.3%) — only not entering avoids it; price recovered +2.3% after the exit — shaken out |
| 3 | 24 Sep 02:05 → 02:44 | SHIB | short | $25×3 | **$-0.11** | PEAK_FLOOR | +0.4 / -0.2 | +0.5% | 71% | -0.7 / -0.3 | wrong from the start (never above +0.4%) — only not entering avoids it; little changed after |
| 4 | 24 Sep 04:50 → 05:01 | 龙虾 | long | $32×1 | **$-0.11** | PEAK_FLOOR | +2.1 / -0.3 | +2.4% | 84% | -1.7 / -14.6 | was up +2.1% first, then gave it back; price went -14.6% further against after the exit — the exit saved money |
| 5 | 24 Sep 05:12 → 05:37 | 龙虾 | long | $22×1 | **$-0.53** | C377_RISK_STOP | +0.7 / -3.1 | +2.5% | 75% | -1.9 / -12.1 | was up +0.7% first, then gave it back; price went -12.1% further against after the exit — the exit saved money |
| 6 | 24 Sep 08:48 → 09:01 | KMNO | long | $27×1 | **$-0.36** | REGIME_EXIT | +0.4 / -1.3 | +8.6% | 96% | -1.3 / -2.0 | wrong from the start (never above +0.4%) — only not entering avoids it; price went -2.0% further against after the exit — the exit saved money |
| 7 | 24 Sep 11:01 → 11:27 | FF | long | $28×2 | **$+0.62** | TRAILING_TP | +1.4 / -0.0 | +2.7% | 88% | +0.8 / -4.4 | won; exit close to fair |
| 8 | 24 Sep 11:01 → 11:32 | CELR | long | $30×1 | **$-0.27** | PEAK_REVERSAL | +1.0 / -1.3 | +5.3% | 94% | +4.6 / -2.6 | was up +1.0% first, then gave it back; price went -2.6% further against after the exit — the exit saved money |
| 9 | 24 Sep 12:52 → 13:33 | UAI | short | $26×2 | **$-0.32** | REGIME_EXIT | +1.1 / -0.6 | +0.3% | 81% | +1.6 / +2.9 | was up +1.1% first, then gave it back; price recovered +2.9% after the exit — shaken out |
| 10 | 24 Sep 13:04 → 13:51 | RAY | long | $26×1 | **$-0.83** | C377_RISK_STOP | +0.3 / -3.2 | +8.8% | 88% | -3.0 / -4.2 | wrong from the start (never above +0.3%) — only not entering avoids it; price went -4.2% further against after the exit — the exit saved money |
| 11 | 24 Sep 13:32 → 13:56 | ETC | long | $29×1 | **$-0.03** | PEAK_FLOOR | +2.0 / -0.2 | +2.5% | 81% | -0.8 / -2.2 | was up +2.0% first, then gave it back; price went -2.2% further against after the exit — the exit saved money |
| 12 | 24 Sep 14:21 → 14:40 | FET | short | $25×2 | **$-0.09** | C399_CONVICTION_COLLAPSE | +0.5 / -0.6 | +1.4% | 84% | +1.0 / -3.9 | wrong from the start (never above +0.5%) — only not entering avoids it; price went -3.9% further against after the exit — the exit saved money |
| 13 | 24 Sep 19:04 → 19:33 | MORPHO | long | $36×1 | **$+0.06** | REL_TRAIL | +1.9 / -0.6 | +7.0% | 94% | -2.6 / -2.7 | won; price reversed -2.6% after the exit — good exit |
| 14 | 24 Sep 20:03 → 20:15 | ETC | long | $23×1 | **$-0.90** | C377_RISK_STOP | +0.5 / -3.8 | +9.1% | 94% | +1.4 / -1.1 | was up +0.5% first, then gave it back; price went -1.1% further against after the exit — the exit saved money |
| 15 | 24 Sep 20:03 → 20:19 | RENDER | long | $34×1 | **$-0.64** | C455_FLOW_REFUSED | +0.4 / -2.0 | +5.2% | 91% | +0.7 / +3.2 | wrong from the start (never above +0.4%) — only not entering avoids it; price recovered +3.2% after the exit — shaken out |
| 16 | 24 Sep 19:53 → 20:22 | DOT | long | $37×1 | **$-0.53** | C399_CONVICTION_COLLAPSE | +1.0 / -1.7 | +4.6% | 94% | +1.7 / +1.0 | was up +1.0% first, then gave it back; little changed after |
| 17 | 24 Sep 20:50 → 21:18 | TRUMP | long | $31×1 | **$-0.08** | C399_CONVICTION_COLLAPSE | +0.5 / -0.4 | +3.9% | 67% | +2.6 / +2.0 | was up +0.5% first, then gave it back; price recovered +2.0% after the exit — shaken out |
| 18 | 24 Sep 20:50 → 21:49 | STONK | long | $31×1 | **$+0.33** | REL_DECAY | +1.7 / -0.4 | +6.2% | 98% | -4.7 / -4.0 | won; price reversed -4.7% after the exit — good exit |
| 19 | 24 Sep 21:35 → 22:11 | ALGO | long | $35×1 | **$+0.80** | TRAILING_TP | +2.6 / -0.9 | +4.9% | 79% | -1.6 / -2.3 | won; price reversed -1.6% after the exit — good exit |
| 20 | 24 Sep 21:54 → 22:26 | BTW | long | $33×1 | **$-0.77** | C377_RISK_STOP | +0.8 / -2.6 | +3.3% | 97% | -11.0 / -2.1 | was up +0.8% first, then gave it back; price went -2.1% further against after the exit — the exit saved money |
| 21 | 24 Sep 22:37 → 22:50 | INJ | long | $21×1 | **$+0.04** | REL_TRAIL | +1.8 / -0.1 | +5.4% | 82% | -4.8 / -4.4 | won; price reversed -4.8% after the exit — good exit |
| 22 | 24 Sep 22:41 → 23:05 | NEAR | long | $17×1 | **$-0.29** | C399_CONVICTION_COLLAPSE | +0.3 / -1.8 | +4.9% | 83% | -0.2 / +2.4 | wrong from the start (never above +0.3%) — only not entering avoids it; price recovered +2.4% after the exit — shaken out |
| 23 | 24 Sep 21:35 → 23:32 | AXTI | long | $25×1 | **$+0.91** | PEAK_REVERSAL | +4.8 / -0.5 | +6.6% | 72% | +0.5 / -1.9 | won; exit close to fair |
| 24 | 24 Sep 23:48 → 00:32 | CYPH | long | $14×1 | **$+0.02** | PEAK_REVERSAL | +2.4 / -0.5 | +15.8% | 83% | +2.2 / +0.7 | won; kept going +2.2% within 1 h — some profit left |
| 25 | 25 Sep 00:50 → 01:06 | FET | long | $29×2 | **$-0.90** | C377_RISK_STOP | +0.5 / -1.5 | +0.4% | 81% | -0.1 / +2.7 | was up +0.5% first, then gave it back; price recovered +2.7% after the exit — shaken out |
| 26 | 25 Sep 00:21 → 01:22 | XAI | long | $6×1 | **$-0.53** | C399_CONVICTION_COLLAPSE | +0.4 / -8.5 | +34.5% | 86% | -0.8 / -9.4 | wrong from the start (never above +0.4%) — only not entering avoids it; price went -9.4% further against after the exit — the exit saved money |
| 27 | 25 Sep 00:50 → 01:48 | LDO | long | $33×2 | **$+0.70** | TRAILING_TP | +1.6 / -0.2 | +2.2% | 91% | +0.4 / +0.4 | won; exit close to fair |
| 28 | 25 Sep 01:35 → 03:08 | XPL | long | $21×1 | **$+0.96** | PEAK_REVERSAL | +6.7 / -1.0 | +7.9% | 75% | -4.2 / -1.5 | won; price reversed -4.2% after the exit — good exit |
| 29 | 25 Sep 02:33 → 03:14 | PENDLE | long | $32×1 | **$-0.20** | C399_CONVICTION_COLLAPSE | +0.2 / -0.6 | +3.6% | 73% | +0.0 / +0.3 | wrong from the start (never above +0.2%) — only not entering avoids it; little changed after |
| 30 | 25 Sep 03:21 → 03:33 | CHIP | long | $26×1 | **$-0.61** | REL_DRAWDOWN | +0.3 / -2.4 | +8.9% | 85% | -1.1 / -3.3 | wrong from the start (never above +0.3%) — only not entering avoids it; price went -3.3% further against after the exit — the exit saved money |
| 31 | 25 Sep 04:16 → 04:39 | CYS | long | $39×1 | **$-0.53** | REGIME_EXIT | +0.5 / -1.4 | +1.9% | 86% | -1.0 / — | wrong from the start (never above +0.5%) — only not entering avoids it |
| 32 | 25 Sep 06:01 → 06:51 | 1000BONK | long | $23×2 | **$-0.18** | PEAK_FLOOR | +0.8 / -0.3 | +1.0% | 59% | -0.4 / — | was up +0.8% first, then gave it back |
| 33 | 25 Sep 06:39 → 06:57 | PUMP | long | $33×2 | **$-0.34** | C399_CONVICTION_COLLAPSE | +0.4 / -0.7 | +2.1% | 98% | +0.2 / — | wrong from the start (never above +0.4%) — only not entering avoids it |
| 34 | 25 Sep 06:46 → 06:58 | JUP | long | $25×3 | **$-0.88** | C377_RISK_STOP | +0.4 / -1.1 | +4.4% | 93% | -0.7 / — | wrong from the start (never above +0.4%) — only not entering avoids it |

**C485: 9 wins / 25 losses, net $-5.92.** Losers never meaningfully up (best < +0.5%): 13 ($-5.66); up first then gave it back: 12 ($-4.70).

## Would a different exit have done better? (every trade with a recorded stop, all versions)

| exit rule (full size, 0.08% fees) | mean % per trade | beats actual in (of 4) |
|---|---|---|
| **what the bot actually did** | **-0.014** | — |
| own stop & target only | -0.285 | 0/4 |
| breakeven once +0.5% | -0.102 | 1/4 |
| breakeven once +1.0% | -0.197 | 1/4 |
| lock 30% of peak once +1% | -0.165 | 1/4 |
| trail 50% of peak once +1% | -0.052 | 2/4 |
| trail 60% of peak once +1.5% | +0.003 | 2/4 |
| exit at 30 min if never +0.3% | -0.319 | 1/4 |

## Market regime: the bot's entry style across ALL traded coins, next-hour result

| day | long chases: n / avg next hour | short chases: n / avg next hour |
|---|---|---|
| 19 Sep | 440 / -0.005% | 283 / -0.175% |
| 20 Sep | 402 / -0.085% | 363 / -0.327% |
| 21 Sep | 651 / +0.248% | 302 / -0.516% |
| 22 Sep | 473 / -0.255% | 388 / -0.417% |
| 23 Sep | 412 / -0.335% | 518 / -0.021% |
| 24 Sep | 564 / +0.223% | 374 / -0.156% |
| 25 Sep | 85 / -0.444% | 93 / +0.011% |

Selection edge (bot pick's next hour minus same-style market entries, same hour): all versions -0.167% (n=164); C485 -0.862% (n=34).

