# Monthly review, 1 Nov 2026 (October): a counting error found and fixed (C549), the research figure corrected, and CoinDCX's close-only day

The scheduled monthly review (routine `trig_01JZa71yehwKWQQgbKtw5XHE`), with the standing full check (your rule of 23 Oct:
"check carefully for errors/discrepancies/pnl/taxations/logic rules/trading mechanism in detail everytime"). Every figure
was re-computed from the exchanges' own records (Delta India, Binance, CoinDCX) and the server's ledgers (logs push
1 Nov 04:47 UTC). Times are IST unless marked UTC.

## 0. In one minute

- **October on paper: +3.44% before tax** ($1,000 → $1,032.20 by the 31 Oct run; $1,033.19 after today's). 28 of 30
  days were positive. After tax at your slab that is about **+2.4%**.
- **I found a real error in how the bot reads Delta's rent, and fixed it (C549).** When Delta switches a coin to hourly
  rent payments during a squeeze, the bot counted some payments 4 times and missed others. It made two pairs face
  the wrong way:
  - ARK (27-28 Oct, −$0.28);
  - BMT (28-31 Oct, +$0.34);
  - the BMT pair held now (since 31 Oct, −$0.36 so far). After the update, the next run closes it.
- **The same error was in the research behind the plan.** Corrected, the expected return is **+3.66% a month before tax
  and +2.52% after tax** (was +4.62% / +3.18%), or **+3.13% after tax at normal costs** (was +3.78%). Still well above
  G1's bar of +1.5% a month before tax. But it is about a fifth less than we planned on, and you should know that
  before March.
- **The tax-risk figures in G6(b) are corrected too:**
  - **+2.66%** a month under the business-income reading (was +3.71%);
  - **−1.17%** if only the CoinDCX leg were a VDA (was +0.23%);
  - **−4.90%** if both were (was −2.95%).
- **Binance was hacked (about $6.3 billion, 29-30 Oct).** CoinDCX, which uses Binance for liquidity, made **every
  futures market close-only for some hours on 30 Oct**. Most reopened the same day, but four (ERA, GTC, LA, SOPH) are
  still close-only today. None is held. **C549 now checks CoinDCX's own "close-only" flag before opening a pair.**
- **Gates so far:**
  - **G1 passes:** +3.84% per 30 days before tax; no losing month; lowest account 65% (bar 40%).
  - **G2 passes:** CoinDCX's rent equals Binance's on 191 of 191 coins.
  - **G6's tax watch:** no change in October.
- **Your real CoinDCX account can't be read since 28 Oct 20:30** (the bot only reads it, it never trades). CoinDCX
  answers "HTTP 422" and the log didn't say why. C549 logs CoinDCX's own reason; after you deploy it, the next hourly
  check will tell us.

**Analogy:** a shop's till that rang up some items four times and skipped others whenever the supplier switched from
weekly to daily deliveries. The shop still made money, the till is fixed, and the yearly sales forecast built on the
same till has been redone with the right count.

---

## 1. October on paper (your plan: Delta India + CoinDCX, 10 pairs × 10%, $1,000)

| | |
|---|---|
| equity | **$1,032.20** after the 31 Oct run (from $1,000.00 at the 4 Oct start); $1,033.19 after 1 Nov's |
| October, day by day compounded | **+3.44% before tax** (30 daily runs; 28 positive, the worst day −$4.66 on 5 Oct, the first run after the rebase and the Pi42 start) |
| G1's window (5-31 Oct) | +3.45%, i.e. **+3.84% per 30 days** before tax (9-31 Oct, all on CoinDCX: +4.46% per 30 days) |
| after tax (31.2%, your slab) | about **+2.4%** for October |
| research expected, a month (costs ×5, as written in the plan) | before tax **+3.66%** (was +4.62%) · after tax **+2.52%** (was +3.18%) · after tax at normal costs **+3.13%** (was +3.78%); see section 3 |
| rent vs costs, since the start | rent **+$44.70** · exchange fees and GST **−$8.80** · price differences −$0.71 · transfer charges −$2.00. **Rent pays its costs about 5 times over** |
| pairs opened / closed in October | 10 at the 5 Oct start (Pi42); then 6 opened and 6 closed: FARTCOIN → AUCTION (11 Oct), IO → MEME (17 Oct), TST → ARC (22 Oct), BEAT → ARK (27 Oct), ARK → BMT (28 Oct), BMT → BMT the other way (31 Oct). Pi42 → CoinDCX move on 8 Oct (10 pairs, $2.08) |
| the one-way cap (C546: at most 6 of 10 facing one way) | held back 1 coin, once (ARK, 9 Oct) |
| even-outs between the accounts | 5 Oct: $163.07 Pi42 → Delta; 1 Nov: $58.11 Delta → CoinDCX (each $1 charge). None mid-month |
| lowest point of each account | **Delta 65% of its half on 5 Oct 05:33**, just before the first even-out (the bot's warning line). No warning after that, so both stayed above 65% all month. On 10 Oct, STRK's jump took CoinDCX to about 86% (your screens). G1's bar is 40% |
| coins held that moved ≥ 30% within a day | STRK +38% (9 Oct), +48% (10 Oct), −33% (12 Oct); BEAT +30% (26 Oct), +33% (27 Oct). All absorbed: the other leg moves the opposite way |
| the one-coin-jump line today | a one-day jump that would empty an account: **Delta +508% (BMT), CoinDCX +584% (AUCTION)**. After C549's next run (BMT out, ARK in), the preview shows Delta's at about +600% |
| restarts | none since 24 Oct 03:35 (inside the new 03:30-03:50 update window); version C548 |
| warnings in the logs (since 24 Oct) | Pi42 403 once a day (expected: Pi42 is shut); **CoinDCX read-only "HTTP 422" every hour since 28 Oct 20:30** (section 6) |

## 2. The error: Delta's hourly rent switch (fixed in C549)

**What Delta does.**
- Most Delta coins pay rent every 4 hours (153 coins) or every 8 hours (97).
- During a squeeze, Delta switches a coin to **hourly** payments for a few days, then back.
- In October 7 coins did this: ARK (twice), RLC, GTC, IOST, IRYS, BMT and ORDER. All were 4-hour coins.
- Delta's record of a coin's rent is one line per hour:
  - on a 4-hour coin, the same rate repeats for 4 hours (one payment);
  - on an hourly coin, it changes every hour (24 payments a day).

**What the bot did.** It looked up the coin's interval **as Delta showed it at the moment**, and applied that to the
whole 8 days of records:
- **read while the coin was hourly:** every old 4-hourly payment was counted **4 times**. ARK read −1,176% a year on
  27 Oct (truly −51%). BMT read −1,016% on 28 Oct (truly −27%). Both were opened facing the wrong way;
- **read after it switched back:** **3 of every 4 hourly payments were missed**. BMT read +244% on 31 Oct (truly −86%),
  so the bot turned it round to face the wrong way again. ARK's rent for 27→28 Oct was booked at $0.32 of a true $0.90.

I reproduced both logged signals exactly with the bot's own function (−1,176 and −1,016), and the corrected rule gives
−51% and −27%.

**The fix (C549).** The bot now finds each payment from the records themselves. A payment happened at an hour when:
- it is on the coin's usual timetable; or
- the rate changed from the hour before (a rate only changes at a payment); or
- it sits inside a run of hourly payments, even when two in a row are equal (GTC 13 Oct 17-20 UTC, at Delta's floor
  rate).

Checked on all 250 Delta coins over 34 days: exactly 6 payments a day for every 4-hour coin, 3 for every 8-hour coin,
24 in an hourly run. The bot also remembers each coin's usual timetable, so a coin that is hourly at the moment is still
read right. The same rule is used for the signal, the daily rent booking, the three test copies and the page's "waiting"
rent.

**Analogy:** the till asked "how often does this supplier deliver?" once, and used that answer for the whole week,
including the days the supplier had changed its schedule. Now the till reads each delivery note.

**What it cost on paper:**

| | |
|---|---|
| ARK, opened the wrong way (27→28 Oct) | −$0.28 |
| BMT, opened the wrong way (28→31 Oct) | +$0.34 (by luck: the price moved its way) |
| BMT, held now, wrong way (since 31 Oct) | −$0.34 so far (it pays rent). **The next run with C549 closes it** (the preview below) |
| rent under-booked on ARK and BMT | **+$0.66 that the ledger did not book** (ARK $0.59, BMT $0.08; ₹57) |
| net | about zero in money. The real cost is three wasted slots for 1-3 days each |

**The test copies were hit harder**, because they decide more often:

| copy | closed trades in the 7 coins | still held on a false signal |
|---|---|---|
| f8 (every 8 hours) | −$3.35 | ORDER, BMT, IRYS |
| w3 (3-day average) | −$1.37 | none |
| b15 (15 × 12%) | −$1.43 | ORDER, BMT, IRYS |
| your plan | +$0.06 | BMT |

So their October scores carry noise. The 2 Dec decision on them should weigh November more.

**Not corrected in the ledger.** The paper ledger keeps what it booked (+$0.66 short), as it did for the C539 finding on
5 Oct. Rewriting history would make the record harder to audit. With real money, the exchange books the rent itself and
the bot only reconciles against it, so this error could not have taken real money, only mis-steered decisions.

**The preview** (`research/c549_preview.py`, made from the server's 1 Nov state and live prices) does the next daily run
with C549:
- **BMT closes** ("spread changed sign": truly −137% a year against its side);
- **ARK opens** long Delta / short CoinDCX at −138% a year (truly negative every day since 28 Oct);
- the other 9 pairs' spreads all agree with their sides;
- the page has no errors, and both accounts are at about 103% of their half.

## 3. The same error was in the research, and the plan's figures are corrected

The research engine (`research/c524_xvenue.py`, used by every round) counted only each coin's usual timetable, so it
missed 3 of 4 hourly payments.
- **Over the 24 months**, 50 of 185 coins had hourly days, 17 of the plan's 63 (RIVER 29 days, LAB 23, SOPH 17,
  DUSK 9, H 7, ...).
- **Independent check:** on 546 of the 595 hourly days Binance was also paying hourly, so these are real squeezes, not
  a quirk of the rule.

`research/c549_hourly_check.py` runs the plan's engine (Round 23's: 10 × 10%, the 6-of-10 cap, CoinDCX's costs) both
ways on the same data. The "before" column reproduces Round 23's published figures exactly.

| a month | before C549 | **with C549** |
|---|---|---|
| before tax (costs ×5) | +4.62% | **+3.66%** |
| after tax (costs ×5) | +3.18% | **+2.52%** |
| after tax, normal costs | +3.78% | **+3.13%** |
| worst month | −1.28% | −1.44% |
| losing months | 5 of 24 | 6 of 24 |
| poorer account's lowest | 59.7% | 59.7% |
| year 1 (Oct 2024 – Sep 2025) | +10.5% in the year | +10.7% |
| year 2 (Oct 2025 – Sep 2026) | +100.3% in the year | +77.2% |

**What it means:**
- **The trade is still clearly profitable in the research.** The plan's bar is unchanged, G1's +1.5% a month before
  tax, and both the corrected research and October's +3.84% are well above it.
- **The planning figure falls by about a fifth.** At $1,000 that is about $25 a month after tax instead of $32.
- **Most of the profit came in year 2.** That was true before too, but it is worth repeating: the rent gap was much
  wider from Oct 2025. If it narrows back to year-1 levels, the plan earns about 1% a month before tax.
- **The tax-risk figures (G6(b))**, re-run on today's 63 coins (`research/c549_tax_readings.py`, Round 22b's engine,
  without the cap):

| how the tax department reads it, after tax a month | 9 Oct (71 coins) | 1 Nov before C549 | **1 Nov with C549** |
|---|---|---|---|
| business income, both legs netted (my opinion) | +3.71% | +3.30% | **+2.66%** (normal costs +3.31%) |
| the CoinDCX leg alone a VDA | +0.23% | −0.63% | **−1.17%** |
| both legs VDAs | −2.95% | −4.18% | **−4.90%** |

  - In rupees: if the worst reading were ever applied to a full year at $1,000, the extra tax would be about
    **₹75,000-95,000** for that year (was ₹60,000-80,000).
  - The trade works only under the business-income reading. That is unchanged, but the margin is thinner.

## 4. Three smaller fixes in C549

1. **A day's missing records no longer forces an exit.**
   - On 27 Oct, 173 of about 194 coins were scored (a fetch gap), and BEAT was closed for "no 7-day spread", although its
     true spread was still +40-70% a year. Two exits' fees wasted.
   - Now such a pair is held, and closed only if the spread is still missing at the third run in a row. A delisted coin
     is still closed at once, as before.
   - The log says "held, no spread today (records did not load)".
2. **No pair is opened where CoinDCX takes closing orders only.**
   - CoinDCX marks such a market `exit_only` in its own data. The bot asks, once per coin per 30 minutes, only for a
     pair it is about to open.
   - On paper an unanswered question counts as open. With real money (B2), it must count as "do not open".
3. **CoinDCX's own reason is logged when it refuses a read.**
   - The message is cut to 120 characters, and anything that looks like a key or signature is removed.
   - Also: a settings comment that C548 had moved onto the wrong line is back where it belongs (no effect on behaviour).

**Tests:**
- `omega_c549_test.py`: 33 checks, using the real October records of ARK, BMT, GTC and RLC (`test_fixtures/`).
- The full battery: **68/68** (section 9).

## 5. Gates so far

| gate | status 1 Nov |
|---|---|
| **G1** paper record (≥ +1.5% a month before tax, no month below −4%, neither account below 40%) | **passing**: +3.84% per 30 days; October +3.44%; lowest account 65% |
| **G2** CoinDCX copies Binance's rent (≥ 80% within 0.002%) | **pass**: 191 of 191 identical (last rate and interval), all 191 active; `research/c541_coindcx_check.py` re-run today |
| **G3** real-money code | not started (B2 on 15 Nov) |
| **G4** pilot | February |
| **G5** safety | not started (alerts from 15 Dec) |
| **G6** tax | (a) the opinion holds; (b) **the risk figures are corrected** (section 3); (c) no adverse change in October (section 7) |
| **G6** jumps | your choice (b), final at 20 Feb with B2's safety net |

## 6. The exchanges (venue watch)

- **Binance, 29-30 Oct:** a security breach of about **$6.3 billion** (a compromised engineer's laptop, according to
  early reports).
  - Binance says about 90% is covered and plans to reopen withdrawals on Sunday.
  - Futures trading went on. The plan reads Binance's rent and prices (as CoinDCX's source), and they were recorded
    normally.
- **CoinDCX, 30 Oct 09:38:** all futures markets became **close-only** ("recent developments impacting a global
  liquidity provider"; a spokesperson named Binance). Deposits, withdrawals and funds were unaffected.
  - Most markets reopened the same day.
  - CoinDCX's own data today shows **4 of its 504 rupee markets still close-only: ERA, GTC, LA, SOPH**. None is held.
  - **What it means for the plan:** CoinDCX depends on Binance. When Binance has trouble, CoinDCX may stop new
    positions. Closing is still allowed, so the safety net (close the twin) still works. But a pair could not be opened
    or re-opened that day. The paper bot now respects this (C549), and B2 must too (section 10).
- **CoinDCX fees** (its own data, today): 493 rupee markets at 0.059% taker (0.05% + 18% GST, as the plan assumes); 7
  commodities at 0.0118%; **4 small coins at 0.1003%** (AGT, BULLA, CT, DODOX). None is held or on the research list. B2
  should read each market's own fee.
- **CoinDCX disclosed "wallet-sweeping" losses on 22 Oct.** It says it absorbed them and credited the affected
  deposits. This is separate from the futures pause, but it is a reminder of exchange risk: keep on each exchange only
  what the plan needs.
- **Your real CoinDCX account (read-only) answers "HTTP 422" since 28 Oct 20:30.** That was before the Binance news.
  - It worked until 19:30 that day (wallet ₹0.07).
  - A fake key gets "401 Invalid credentials", so CoinDCX still recognises yours. 422 means it refuses something about
    the request or the key (an expired key, or a new rule).
  - After you deploy C549, the log line will carry CoinDCX's own reason. Please check `api.coindcx.com` → API
    dashboard: is the key still listed, enabled and bound to 140.245.30.104?
  - This read is needed for B2/B3 (reconciling real balances), not for paper.
- **Delta India:** 60 minutes of maintenance on 18 Oct at 01:00 (nothing ran then). A WebSocket change on 31 Oct does
  not affect the bot, which uses only Delta's REST interface. Rupee rate, contract sizes and the 0.05% taker fee are
  unchanged (fee read from Delta's product list).

## 7. Tax watch, and the statement (edition 4)

**The law:** no change in October.
- The 30% VDA rate and 1% TDS are unchanged; no CBDT circular or notification on crypto derivatives.
- The Income-tax Act 2025 is in force from 1 April 2026 (sections renumbered; the statement already cites both).
- **New this year:** exchanges must report crypto-asset transactions to the department (1961 Act s.285BAA, from
  1 April 2026). Your AIS may later show entries from Delta or CoinDCX. The statement's handover pack (section 13,
  step 3) already says what to do: compare them, and if they are labelled "VDA", give AIS feedback that the income is
  offered as speculative business income.

**The statement, edition 4** (`reports/tax/ITR_TY2026-27_rent_gap_PAPER.md`, PAPER, not for filing). As your tax adviser
(not a registered CA), I checked it line by line:
- **Net speculative business income ₹2,827** year to date (edition 3: ₹1,701). Turnover ₹12,531; gross profit ₹3,030;
  expenditure ₹202. Tax at 31.2% would be ₹882, so no advance tax (under ₹10,000).
- **It ties to the ledger:**
  - equity ₹87,821 minus ₹84,961 at the journal's start = **₹2,860 = net income ₹2,827 + open positions' unrealised
    ₹33**, to the rupee;
  - every one of the 16 journaled positions agrees with the ledger;
  - the 1 Nov even-out charge (₹85) sits in November, as it should.
- **Money held:** ₹87,788 = each exchange's wallet without the open positions' unrealised result (Delta ₹43,044,
  CoinDCX ₹44,744). That is the right figure for "sundry debtors": money the exchanges owe you, not paper profit.
- **The C549 error shows in it:** ARK's and BMT's rent are ₹57 short, because the statement is made from the ledger.
  Paper only. With real money, the statement is reconciled against each exchange's own statement (B3), which books
  every hourly payment.
- **Schedule VDA stays empty and the business-income reading stays my opinion.** But **G6(b)'s numbers are now
  +2.66% / −1.17% / −4.90%** (section 3), and that is what you will be asked to accept at the go/no-go.

## 8. The paper copies and the experiments

| (since its copy began) | the copy | your plan, same days |
|---|---|---|
| f8, decides every 8 hours (from 6 Oct) | **+2.97%** | +4.03% |
| w3, 3-day average (from 7 Oct) | **+3.67%** | +3.92% |
| b15, 15 pairs × 12% (from 9 Oct) | **+4.72%** | +3.50% |

- **f8** trails, partly because the hourly error hit it hardest (section 2).
- **b15** leads, as more money at work should, but it also holds three wrong-way pairs until C549's next run.
- **Decided on 2 Dec** with November's record, on the corrected rule.
- **The six switched-off experiments stayed silent:** no line from them in the logs since 23 Oct. The rule tournament's
  K4 score (kept on purpose) is the only "K4" mention.
- **The Delta book's own rent step** (a separate paper strategy, decided 2 Dec) still steps by Delta's current interval,
  re-read every 6 hours. None of its 13 coins had an hourly stretch in October, so it was unaffected. The 2 Dec review
  will either adopt `_c549_paid` there or note why not.

## 9. Build steps, version, your to-dos

- **Version:** C548 on the server since 23 Oct; **C549 ready to deploy** (section 11).
- **Restarts:** none since 24 Oct 03:35, which was inside the new update window.
- **Tests:** `omega_c549_test.py` 33/33; the full battery **68/68** (65 Python + 3 shell). Two older checks needed
  care:
  - C539's two source-text checks looked for the exact lines C549 rewrote. They now also accept the C549 lines; the
    behaviour they protect (rent up to the run, the signal stopping at midnight) is unchanged and passes;
  - the headless boot test needed its scratch folder in this fresh container. It then booted `OMEGA C549` and
    answered on its port in 3 seconds, with no errors.
- **Your to-dos:**
  - **deploy C549** (section 11);
  - **check the CoinDCX API key** (section 6) and send me the line after deploying;
  - **the reboot check** (`cat /var/run/reboot-required`, monthly);
  - **log in to the Oracle console once** this month (accounts unused for 60 days can be closed);
  - **send the Pay As You Go screenshot** if the upgrade is done (Billing → Upgrade and manage payment). The budget
    alert `omega-zero-spend` should stay silent, and no Oracle "idle instance" e-mail should arrive;
  - **by 15 Dec:** choose the alert channel;
  - **before 1 Feb:** bank account and 2FA on both exchanges.

## 10. What changes in the plan's next steps

- **B2 (15 Nov, the order path)** must also:
  - read each CoinDCX market's `exit_only` flag and its own taker fee before opening;
  - place the **CoinDCX leg first** (the one that can be refused), and Delta's only after it fills. An unanswered
    status read means "do not open";
  - treat a refused order as "do not open the twin" (and close it if it already filled);
  - fix the CoinDCX read (the 422) before anything else.
- **The December refresh (2 Dec)** re-runs everything with the corrected engine (it is now the default) and decides the
  copies on November's record.
- **The end-November review and the go/no-go** compare against the corrected research (+3.66% before tax, +2.52% after,
  costs ×5) and show you G6(b)'s corrected numbers.
- All four scheduled tasks have been updated to say so.

## 11. Termius commands

**1. Deploy C549:**

```
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sudo journalctl -u omega --since "3 min ago" | grep -m1 "OMEGA C54"
```

Expect `OMEGA C549`. Tomorrow's 06:00 run should close BMT and open ARK (the preview).

**2. The CoinDCX read and the reboot check** (read-only; about 15 minutes after the restart, send me the output):

```
sudo journalctl -u omega --since "20 min ago" | grep "C540 real account CoinDCX" | tail -2
cat /var/run/reboot-required 2>/dev/null || echo "no reboot needed"
```
