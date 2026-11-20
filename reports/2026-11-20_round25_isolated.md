# Round 25: CoinDCX's rupee futures are isolated-only -- what that does to the plan (and a bigger finding)

20 Nov 2026. Pre-registered and pushed before any run: `research/r25_preregistration.md` (commit dd0cc59). Code
`research/r25_round25.py`, results `research/r25_round25.txt` / `.json`, CoinDCX's rules as read
`research/r25_dcx_rules.json`. Times IST unless marked UTC.

## 1. Your screens (10:53 to 11:27), checked

| screen | what it shows | checked |
|---|---|---|
| CoinDCX app, 10:53 | ETH • USDT futures at ≈ ₹1,75,881 (= 1,724.33 × ₹102: the rupee-margined market). "Select margin mode": **Isolated** only, *"Cross margin mode is currently only available in USDT margin Futures."* | **CoinDCX's rupee futures cannot use cross margin.** Its API documentation said so on 15 Nov; the help-centre page did not say cross is for USDT margin only |
| Delta India app, 11:00 | Margin mode **Cross (Current)**; available margin "0 USD" | Delta is right for the plan. Its balance unit is USD, as C551 assumed |
| Oracle, 11:08 | "Success. Congratulations. Your account was successfully upgraded"; Plan type **Pay As You Go** | the server can no longer be stopped as "idle". Next: the budget alert (`omega-zero-spend`) |
| Termius, 11:26 | kernel 7.0.0-1016 (was 1013), no "restart required", both services `active`, `OMEGA C551` at 11:24:46, a new page address | the reboot and C551 worked. "20 updates, 1 security" are installed by the nightly 03:30 window |
| the stops line, 11:24:59 | e.g. NOT CoinDCX short at 0.00214295, ALT 0.0246055 | **checked from the 12:17 IST logs push: all 10 stops leave their account at exactly 25.00% of its half, in rupees** (C550 had left the five CoinDCX ones at 10.3%). The bot shut down cleanly before the reboot; no warnings since; the dry book restarted as designed, all 10 pairs with the plan's Delta contracts |
| the page, 11:27 | $1,051.16; Delta $560.25 + CoinDCX $490.91; after tax $1,035.20 (tax $15.96) | the accounts add up; 31.2% of $51.16 = $15.96 |

## 2. Isolated margin on CoinDCX's rupee futures, as CoinDCX defines it

**From its public instrument data, read 20 Nov 06:29 UTC for all 79 coins tested (all 63 of the list are listed):**
- most of the plan's coins: **5× at most**, maintenance ("safety") margin **1.5%** at the plan's leg size, liquidation fee
  **1.5%** (43 coins);
- seven allow only 4×: ARC, AVAAI, BMT, MUBARAK, PIPPIN, TRUMP, VVV;
- the majors: 10-25×, 0.5-1%, 1%.

**From its API documentation:**
- `positions/add_margin` and `positions/remove_margin`, in rupees for rupee futures;
- `positions/update_leverage`.

**What it means for a bet:**
- **The setup:** each bet has its own small pot of margin. When the price moves against it far enough that the pot is
  nearly empty, CoinDCX closes it (liquidation) and keeps what is left as its fee.
- **What you lose:** the whole pot.
- **The other bet in the pair** (on Delta) has gained the same move, so the pair as a whole loses about the fee plus the
  slippage. But the pair is broken, and has to be closed.
- **Analogy:** under cross margin, all your bets share one fuel tank. Under isolated margin, each has its own small
  jerry can, and a bet whose can runs dry is stopped by the exchange, even if the next can is full.

## 3. Round 25: what was tested

**The question:** can the plan run with CoinDCX's bets on isolated margin, and at what cost? Delta stays on cross.

**The variants** (10 pairs of 10%, the K6 cap; only CoinDCX's margin changes):
- **I2:** each CoinDCX bet posts half its size (2×). No reserve.
- **I3T:** a third (3×), with the rest of the account as a shared reserve that tops up any bet near liquidation.
- **I5T:** a fifth (5×, or the coin's maximum), with a bigger reserve that tops up the same way.
- **The reference:** cross on both, as researched (not available on CoinDCX's rupee futures).

**How it was run:**
- the 24 months on daily price highs and lows (top-ups assumed in time);
- Round 23's 46 worst days minute by minute: top-ups one minute late, as the bot's 60-second watch would be; a
  liquidated bet's twin closed at the next minute's price.
- **New in Round 25:** each bet holds a fixed number of coins, as on a real exchange and in your paper ledger. The
  earlier rounds kept each bet at its starting dollar size every day.

**Checks passed before reading anything:**
- **Engine:** with cross margin and the old booking, the new code reproduces Round 23's engine exactly (net 0.443760,
  lowest account 0.597492, transfers 8.089 a year).
- **Minute replays:** the minute code reproduces Round 23's replays exactly on the six crash days.

## 4. The results (costs ×5; after tax at 31.2%; $1,000)

| | before tax / month | after tax / month | vs cross, $/yr | worst month | CoinDCX liquidations / yr | days a year a pair could not open (no free margin) | poorer account's lowest point | replays: accounts wiped | 10 Oct 2025 crash, lowest |
|---|---|---|---|---|---|---|---|---|---|
| cross, old booking (as researched) | +3.66% | +2.52% | — | −1.44% | 0 | 0 | 59.7% | — | — |
| **cross, real booking (XQ)** | +3.66% | +2.52% | — | −1.44% | 0 | 0 | **5.0%** | **3 days** | 46.7% |
| I2 | +1.63% | +1.12% | **−168** | −7.57% | 18.2 | 206 | below 0 | 1 | 73.1% |
| I3T | +2.75% | +1.89% | **−75** | −4.06% | 10.1 | 71 | 6.3% | 1 | 71.1% |
| **I5T** | +3.16% | +2.18% | **−49** (−41, plus 8 from the minute calibration) | −1.28% | 8.6 | 21 | below 0 | 1 | 44.7% |

**Verdict, as pre-registered: every variant FAILS.**
- **Cost:** even the best, I5T, costs about **$49 a year after tax** against cross, more than the $30 bar.
  - Most of it is about 9 liquidations a year. Each costs the pair about 7% of a bet: CoinDCX's 1.5% fee, the twin's
    one-minute delay and the closing costs.
  - The rest is entries refused for lack of free margin (21 days a year).
- **Accounts:** the poorer account falls below 40% (in fact below zero at the worst moment) in every variant. **So does
  the cross reference itself** under the real booking: 5.0% on 24 Oct 2025, wiped on 3 of the 46 replayed days.
  Section 5 explains why.
- **The minute replays agree with the daily model:**
  - for I2 and I3T the minute model lost *less* than the daily model assumed (the 5% slip was cautious);
  - for I5T $16 more over the 46 days, added to its cost.

**What isolated margin did well:**
- **AKE in September 2026:** it closed the CoinDCX bet before it could empty that account; under cross that account
  was wiped (section 5).
- **On the 10 Oct 2025 crash** it cost 4-6 liquidations of CoinDCX's long bets between 21:14 and 21:22 UTC, the crash's
  worst minutes.

## 5. The bigger finding: bets grow with their coin

**Every earlier round kept each bet at its starting dollar size every day.** Real futures hold a fixed number of coins.
So does your paper ledger, and so does C550. When a coin rises while it is held:
- **both bets grow:** a $100 bet on a coin that triples becomes $300 on each exchange;
- **the pair stays balanced in total,** but one account loses $200 and the other gains $200;
- **the next jump is then measured on the bigger bet.**

**The two days that broke the accounts in the 24 months:**

| day | coin | what happened | effect (cross margin, no stop) |
|---|---|---|---|
| 24 Oct 2025 | **H** | held short on Delta since 0.042; already 3.5× (0.150), so its $101 bet was $359; then **+155% in one day** | the Delta account fell to **4% of its half** that evening, and below zero at the day's highest minute |
| 18-20 Sep 2026 | **AKE** | held short on CoinDCX; +118% on 18 Sep, +39% on 19 Sep; its $196 bet grew to $1,288 (6.6×) | **the CoinDCX account was wiped** on 19-20 Sep (minute replay). Isolated margin contained it |

**How often bets grow, over the 24 months (cross, real booking):**
- a bet was more than 1.5× its target size on 6.6% of pair-days, more than 2× on 3.6%, more than 3× on 1.1%;
- the largest was 7.4×.

**What this means:**
- **The poorer account's "lowest point 59.7%"** in Rounds 23-24 and the 1 Nov review **was too optimistic.** The
  returns are unchanged: each pair is still balanced as a whole.
- **The risk is not about CoinDCX's margin mode.** It comes from letting a bet grow unchecked.
- **The safety net built in B2 would have fired, but it would not have saved the account that day.**
  - H's emergency stop sat at about 0.379 that morning, where Delta's account would be at 25% of its half *if H alone
    moved*. H closed at 0.3816, so the stop fires.
  - But **EVAA**, also a falls bet on Delta and also grown (3.2×, $385), rose 38% the same day: −$148 more. The account
    would still have ended near $7, about 1% of its half.
  - **The stops are set one bet at a time;** they cannot allow for two grown bets jumping together. Keeping bets from
    growing (a trim rule) is what fixes that.
  - No round has yet tested the stops and the real booking together.
- **The page's one-coin-jump line already uses the bets' current sizes,** so it shows the real risk today. Today the
  largest falls bet is $104 (JCT, on Delta).
- **Your paper record has not met such a coin yet.**
  - Since 5 Oct no falls bet has ended (or stands now) more than 9% above its entry price (IO, closed).
  - The biggest moves within a hold were +30-40% (STRK on 9-12 Oct, BEAT on 26-27 Oct).
  - But G1 ("no account below 40%") is scored on this record, so one big trending coin before February could fail
    G1.

## 6. What comes next

**Round 26 (proposed; to be pre-registered and run in the 2 December refresh, with the data through November):** the
plan as it would really run.
- **Real booking:** each bet a fixed number of coins.
- **Delta on cross margin with C550's emergency stops:** each falls bet stopped where its account would be at 25% of its
  half; the twin closed at once.
- **CoinDCX on isolated margin:** I5T, and I3T for comparison; its falls bets also carry C550's stop.
- **A new trim rule:** at each 06:00 run, a pair whose bets have grown past k × the target size (10% of today's
  equity) is cut back to the target on both exchanges, with k = 1.5 or 2.
- **The same bars as Round 25**, plus: the pick must also be ahead (positive) on Oct-Nov 2026 alone, the two months no
  test has seen.

**Why not now:**
- The stops, the trims and isolated margin interact, and modelling them together needs care, not speed.
- On 2 Dec there will be two fresh months to check against.
- B3 (15 Dec) builds whatever passes into the order path.
- The March timetable holds if Round 26 passes on 2 Dec.

**If Round 26 fails, the options:**
- **(a) CoinDCX's USDT-margined futures** (cross is available). Not recommended: buying USDT is a crypto purchase, and
  it breaks the tax opinion's "no crypto ever bought" basis. As your tax adviser (not a registered CA), I would not
  take that route for this trade.
- **(c) Another Indian exchange with cross margin on rupee futures:** a new census of every exchange a bot can reach.
- **(d) A smaller plan on isolated margin:** smaller bets, or more of the money on CoinDCX.

**Nothing changes in the paper plan now.** A trim rule enters it only after it passes Round 26.
