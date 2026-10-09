# The 10 Oct screens, the hidden issues, and Round 24

**10 Oct 2026, ~03:00 IST.** You sent the dashboard at 00:40 IST and asked:

> "analyse carefully to the core, excavate any hidden issues ... discover any possibilities of profitability
> enhancement or sustainance..proceed accordingly ...update the time line accurately"

## 0. In short

- **Every number on both screens is right.** I checked them against the server's ledger and against Delta's and
  Binance's live prices (section 1).
- **Hidden issue found: each account is one-sided.** Every pair is balanced, but 7 of the 10 point the same way, so
  each account carries a one-way market bet.
  - **What it means:** replayed minute by minute, the crash of **10–11 Oct 2025** would have dropped one account to
    **50%** within an hour.
  - **The fix tested and adopted (C546):** at most **6 of 10 pairs may face the same way**. That raised the worst
    crash-day point to **70%** and the worst daily point over 24 months from 57% to **66%**. Profit is about the same
    (+$3 a year).
- **The margin question for real money is now settled by data.** One shared balance per exchange ("cross margin")
  survived every replayed day. Separate fixed margin per bet ("isolated", 1/3 or 1/2 of the bet) would have wiped
  out **9–10 bets** on 10 Oct 2025.
- **Profit ideas tested honestly:**
  - "Swap a weak pair for a much stronger one" earned **+$38–46 a year** more, but failed the bar.
  - The aggressive version even emptied an account (chasing the widest gaps means chasing the jumpiest coins).
  - **Not adopted.**
- **Is the edge fading? No.** Over the 24 months the gaps grew (85% → 167% a year), but they have dropped back from a
  peak in July. September was a weaker month (+3.0% before tax), like October so far.
- **Two things for your server and your tax** (sections 2 and 6).

## 1. The screens, checked

| on the screen | checked against | result |
|---|---|---|
| $1,000.91 (+$0.91) | ledger at the 9 Oct 06:00 run $999.54 + rent waiting $1.08 + price moves since 06:00 +$0.29 | ✓ |
| after tax $1,000.63 (tax $0.28) | 31.2% × $0.91 | ✓ |
| Delta $570.99 (114%) · CoinDCX $429.92 (86%) | each account's ledger value + its legs' moves since 06:00, on live marks at 00:50 IST: $571.77 / $428.02 (10 minutes later) | ✓ |
| rent collected +$8.98, +$1.08 waiting | ledger funding $8.98; the open pairs' rent $7.38 + $1.08 = the column's sum $8.46 | ✓ |
| fees $6.95, moving money $1.00, price −$1.49 | ledger | ✓ |
| days 7.0 / 4.8 | opened 3 Oct 01:42 IST and 5 Oct 06:00 IST | ✓ |
| last daily run 9 Oct +$1.27 (rent +$1.50, prices −$0.23) | the run's record | ✓ |
| scoreboard: yours +$3.24, 8 h +$3.25, 3-day +$2.93, 15 × 12% +$0.32 (vs $1.27 since 8 Oct) | the copies' daily snapshots | ✓ (the 15-pair copy is behind by the entry fees of its 5 new pairs on 9 Oct, about $0.95) |
| real accounts 0.00 | the read-only reads every 10 minutes | ✓ |
| version C545, running 4 h 18 min | `OMEGA C545` in the session log at 20:23 IST, no errors | ✓ |

**Why Delta shows 114% and CoinDCX 86%:**
- **STRK jumped +38.8% in 18 hours.** The 06:00 mark was 0.0557; the high at 22:00 IST was 0.0773.
- Your STRK pair is "long on Delta, short on CoinDCX". So Delta's leg gained about $26 and CoinDCX's lost about $26.
  NOT (+6%) and H (−7%) added smaller swings.
- The pair as a whole lost nothing, and its rent gap is actually wider now.
- **Analogy:** a see-saw. The whole thing stays balanced, but one end goes up and the other goes down. Nothing to do:
  the monthly even-out on 1 Nov moves about $70 back across.

**Gate G2 re-checked tonight:** CoinDCX's rent equals Binance's on **191 of 191** shared coins.

## 2. Hidden issues

| # | issue | what I did |
|---|---|---|
| 1 | **Each account is one-sided** (7 of 10 pairs face the same way). Delta India's buyers usually pay more rent, so most pairs are "short Delta / long CoinDCX". | Tested in Round 24 and fixed: the **C546 cap**, at most 6 of 10 one way (section 3) |
| 2 | **Every earlier test used daily closing prices,** which hide crashes that happen and recover within an hour. On 10 Oct 2025, mark prices of many altcoins fell **40–93% within minutes**. | Replayed on 1-minute data (section 3A). The result goes into Round 23 and B2 |
| 3 | **"Isolated margin per bet"** (a Round 23 candidate) would have been ruinous on 10 Oct 2025. Tonight's STRK move (+38.8%) would also have liquidated a bet with 1/3 margin. | Round 23 and B2 instructions updated: **cross margin on both exchanges**, tested on minute data. CoinDCX's API documents cross margin for rupee-margined futures (`position_margin_type: crossed`, `margin_currency_short_name: INR`). B2 confirms it on your real account |
| 4 | **Oracle's free tier stops servers it considers idle.** If, over 7 days, the server's CPU, network (and, on ARM servers, memory) are each under 20% most of the time, Oracle may stop it. A stopped server also can't send an alarm. | **Your to-do:** upgrade the Oracle account to **Pay As You Go**. It stays free within the Always Free limits, and Oracle then doesn't stop idle servers. B3 adds an **outside "dead-man's switch"** alarm (section 7) |
| 5 | The page said "last move: from Pi42". That was true on 5 Oct, but confusing now. | Now reads "from Pi42 (your second account then)" |
| 6 | A "Pi42 not read" warning at every restart: your Pi42 read-only key is still saved. | Harmless. **Optional:** delete the Pi42 key (already on your list) |
| 7 | Is the public dashboard link a risk? | No. Every request, even just viewing, needs your token (C467-D); the link alone shows nothing |

## 3. Round 24 (pre-registered before it ran: `research/r24_preregistration.md`; results `research/r24_round24.txt`)

The same history and engine as Round 22: Delta + CoinDCX, 64 coins, Oct 2024 – Sep 2026, costs ×5. The engine check
passed: with the new rules off, the code reproduces Round 22's figures exactly.

### A. Ten bad days, minute by minute

Each account's lowest point during the day, from 1-minute mark prices, taking every bet's worst moment:

| day | rule | lower account's lowest point | cross margin wiped out? | bets liquidated with isolated margin of 1/3 · 1/2 |
|---|---|---|---|---|
| **10 Oct 2025 (the crash)** | today's rule | **50.1%** (Delta, 21:22 UTC) | no | **10 · 9** |
| 10 Oct 2025 | **with the cap (K6)** | **69.9%** | no | 10 · 9 |
| 5 Aug 2026 (BLESS +148% intraday) | today's / cap | 61.2% / 57.1% | no | 1 · 1 |
| 16 Jun 2026 | today's / cap | 67.2% / 77.0% | no | 4 · 0 / 3 · 0 |
| 8 May 2025 | today's / cap | 69.8% / 83.2% | no | 0 · 0 |
| 11 Jun 2026 (H +138% intraday) | today's / cap | 71.1% / 69.1% | no | 3 · 2 |
| 7 Nov 2025 | today's / cap | 71.0% / 80.4% | no | 3 · 2 / 4 · 3 |

**Today's own 10 pairs put through 10 Oct 2025:**
- 7 of them were listed then.
- The CoinDCX account would have fallen to **55%** at 21:20 UTC, then recovered. Delta stayed at 99%.
- Individual coins' mark prices fell: FARTCOIN −84%, IO −81%, TST −90%, NOT −84%, AIXBT −83%, H −57%, KAITO −40%.

**Honest note:** on two of these days (5 Aug and 11 Jun 2026), the cap left the poorer account 2–4 points lower than
today's rule. Both were single-coin jumps, not crashes. Those are Round 23's job.

**What it means:**
- **Cross margin is the right design.** The bets on one exchange share the account, so the gains on its short bets
  hold up its long bets during a crash.
- **Isolated margin per bet is the wrong design.** In a crash nearly every bet facing the crash's way is cut off at
  the bottom. The twin bet on the other exchange then gives its gain back as prices recover.

### B. Swapping a weak pair for a much stronger one (profit)

| | after tax a month | vs today | poorer account's lowest | transfers a year | verdict |
|---|---|---|---|---|---|
| today's rule | +3.41% | — | 56.9% | 7.6 | — |
| swap when 40%/yr better | +3.73% | +$38/yr | **−34% (account emptied)** | 11.1 | fails |
| swap when 80%/yr better | +3.80% | +$46/yr | 56.9% | 11.1 | fails: under the $50 bar; t 2.31 under 2.5 |

**Analogy:** always trading up to the shiniest car on the lot. Sometimes you get a lemon that breaks down on the
motorway. The coins with the widest gaps are often the most excitable ones.

### C. The cap on one-sidedness (staying power)

| | after tax a month | vs today | poorer account's lowest | transfers a year | verdict |
|---|---|---|---|---|---|
| at most 7 of 10 one way | +3.48% | +$8/yr | 61.5% | 6.6 | fails ("safer" not reached) |
| **at most 6 of 10 one way** | **+3.44%** | **+$3/yr** | **66.3%** | 7.1 | **PASS**: every Round 22 bar on every list; the crash day no worse for either account |

**Analogy:** don't seat everyone on the same side of the boat. A wave (a crash) then tips it far less, and the
journey takes just as long.

### D. Is the edge fading?

| | widest-10 gaps | the plan's month, before tax (costs ×5) |
|---|---|---|
| first 18 months (Oct 2024 – Mar 2026) | 85%/yr | +3.78% |
| last 6 months (Apr – Sep 2026) | 167%/yr | +8.50% |
| July 2026 (the peak) | 259%/yr | +16.68% |
| September 2026 | 96%/yr | +3.04% |

- **Over the two years the edge grew, not shrank:** the trend is +99 points a year, t 6.3.
- **But it comes in waves.** The peak was July; September and early October are back near the long-run average.
- **Plan on the 24-month figure, not the peak:** about **+3.4% a month after tax** at costs ×5, and about +4.0% at
  normal costs, with the cap.

## 4. What changed in the bot (C546, paper)

- A new pair is **held back if 6 pairs already face its way**; the next-best pair in the other direction can still
  enter. Nothing already open is closed for it.
  - Today: 7 face "short Delta", so the next "short Delta" pair waits until one of those closes.
- The 15-pair test copy uses the same 60% rule: 9 of 15.
- **The page** says how many pairs face each way, and when a direction is full. **The daily log** names any pair held
  back.
- **Tests:** `omega_c546_test.py` (13 checks) and the full battery.

## 5. Into Round 23 (22 Oct) and B2 (15 Nov)

- **Round 23 must:**
  - test every jump-protection idea on **1-minute** data around these days, not daily closes;
  - **reject isolated margin at 1/3 or 1/2 per bet**, unless a variant survives 10 Oct 2025;
  - prefer cross margin with enough balance in each account.
- **B2 must:** set **cross margin** on both exchanges, and confirm on your real accounts that CoinDCX's rupee-margined
  futures accept it. If either exchange refuses, the order path doesn't go live until that is solved.

## 6. Your two tax points (as your tax adviser; I'm not a registered CA)

**"My salary and this income go into the same bank account. Is that the same as declaring it to my employer?" No.**
- **Same account:** it's just where the money lands. Your employer's payroll doesn't see your bank account, so it
  deducts tax only on your salary. Having one account is perfectly fine for tax. Nothing needs to change, and the
  statement simply names that account.
- **Declaring to the employer:** this is a formal step. From 1 April 2026 it is **Form 122** under the Income-tax Act,
  2025, s.392(4)(a) (under the old Act it was s.192(2B)). You give it to your employer's payroll, listing other income
  (not a loss) under heads other than salary. They then deduct extra TDS from your salary each month to cover it.
- **Your three options for tax on the bot's profit during the year:**
  1. **Pay advance tax yourself** online on 15 Jun, 15 Sep, 15 Dec and 15 Mar. It takes about five minutes each time
     and keeps your employer out of it. **My recommendation from 2027-28**; I give you the amounts in the monthly
     review.
  2. **Form 122 to your employer:** no dates to remember. But your employer learns you trade, your estimate needs
     updating as the year goes, and a loss can't be declared.
  3. **Pay it all when you file:** the late-payment interest is about 1% a month on the shortfall. That is fine only
     for tiny amounts.
- **For 2026-27 (live only in Feb–Mar 2027):** the tax is about ₹1–2 thousand. **No advance tax is needed**; you pay
  it with the return.

**"No server rent, I'm on the free tier."** Understood: there is no business expense to claim, and nothing changes in
the statement. One thing to do for the server's sake, not the tax's: upgrade to Pay As You Go (issue 4).

## 7. Your to-dos from this round

| when | what |
|---|---|
| **this week** | Upgrade your Oracle Cloud account to **Pay As You Go** (Billing → Upgrade and manage payment). It needs a card, but stays free within the Always Free limits, and Oracle then doesn't stop "idle" servers. Optionally set a budget alert of ₹100 |
| any time | Send me the output of `nproc; free -m; uptime; uname -m`. It shows the machine's size and how busy it is |
| optional | Delete the Pi42 read-only key (on Pi42's site and in `data/api_keys.json`) |
