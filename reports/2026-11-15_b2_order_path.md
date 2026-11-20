# B2: the two-exchange order path (C550), built and tested dry -- and one blocker: cross margin on CoinDCX

Build step B2 of `reports/2026-10-04_live_march_roadmap.md` (routine `trig_01XjNNKCDMzqwQjXGge7753r`, fired 15 Nov 2026;
finished 20 Nov after an interruption). The tests were pre-registered and pushed before any code:
`reports/2026-11-15_b2_preregistration.md` (commit 780c15d). Times are IST unless marked UTC.

## 0. In one minute

- **The order path is built: C550.** It turns each day's plan into the exact orders both exchanges would get. In this
  step it **sends none**: every order goes to an in-memory pretend exchange and is logged.
  - **Analogy:** a flight simulator. The pilot runs the whole flight, every switch and every checklist, but the plane
    never leaves the hangar.
- **Real orders stay locked behind two separate keys:**
  - the lock `C550_LIVE_OK`, off, and separate from `C488_LIVE_OK`, which also stays off;
  - cross margin confirmed on BOTH exchanges, which is not yet the case.
- **All 26 pre-registered tests pass** (56 checks, mocked exchanges, zero real network calls). The full battery: section 8.
- **The blocker, plainly:** CoinDCX's own API documentation says *"Cross margin mode is not supported on INR margined
  Futures"*. The plan trades CoinDCX's **rupee** futures, and Round 24 requires cross margin.
  - CoinDCX's help centre (updated about 4 months ago) suggests the app may now offer it; the two disagree.
  - **Only your account can settle it.** Section 3 has a 2-minute check in each app.
  - Until both are confirmed, the order path **cannot** go live, by design.
- **Your paper plan, checked again (to 20 Nov):**
  - **$1,051.08 (+5.11%)**; every daily run since 2 Nov positive;
  - the books balance to the cent;
  - today's rent recomputed from both exchanges matches to the cent; all 10 gaps identical;
  - CoinDCX's rent still equals Binance's on 191 of 191 coins.
- **Your new CoinDCX key works** (since 6 Nov 11:38). The 14 Nov restart was inside the 03:30 update window, as designed.

## 1. The paper plan, 7-20 Nov (the standing full check)

| | |
|---|---|
| equity | **$1,051.08** at 20 Nov 06:00 (+5.11% since the start; +$12.93 since 6 Nov). Every run 2-20 Nov positive |
| the books | $1,000 + rent $64.38 − fees $10.25 − price $1.05 − transfers $2.00 = **$1,051.08**, exact; Delta $552.98 + CoinDCX $498.10 |
| rent re-computed | 15 Nov: **$0.7890** (booked $0.79). 20 Nov: **$1.0090** (booked $1.01) = the 10 held pairs $1.0042 + BILL's last day $0.0048 |
| the gaps | all held coins' 7-day gaps recomputed from Delta's and Binance's records: identical (15 and 20 Nov) |
| swaps | 8 Nov MEME → 1MBABYDOGE; 11 Nov 1MBABYDOGE → BILL; 16 Nov H → AIN; 20 Nov BILL → JCT (each "spread under 10%/yr") |
| hourly rent | no held coin paid hourly in either window; none of the 250 Delta coins is hourly now |
| G2 | **191 of 191** coins: CoinDCX's latest rent rate = Binance's, same interval, all active (15 Nov) |
| restarts | one: **14 Nov 03:40**, a clean stop/start inside the new 03:30-03:50 update window (the session summary was printed) |
| warnings | only Pi42's daily "firewall" note (expected). CoinDCX reads fine since your new key (6 Nov 11:38) |
| tax statement | a scratch run on the 15 Nov ledger: net ₹3,962; its checks OK; ties to the ledger (₹3,962 + open ₹3 = ₹88,926 − ₹84,961) |
| tax law | no CBDT circular or notification on crypto derivatives since 1 Nov. The July CBDT note is about exchanges' reporting duties, not the tax treatment |

**One loss worth understanding: 1MBABYDOGE, −$1.32 in 3 days (8-11 Nov).**
- The data was right: no hourly payments, and both exchanges' records agree.
- Its 7-day average was −178% a year, driven by a squeeze on 2-4 Nov. But the daily gap had already turned positive on
  6-7 Nov. The bot opened facing the old direction, paid rent, and closed when the average faded.
- That is the 7-day rule's lag: right on most days, late at a turning point. It is the reason the 3-day copy (w3) runs.
- A possible filter, "the latest day must agree in sign", is an idea for a **pre-registered** test (the 2 Dec refresh),
  not a change now.

## 2. What C550 does (in plain English)

**Analogy:** two shopkeepers, one in each market, must buy and sell the same item at the same moment so you never hold
just one side. C550 is the person carrying the two order slips. It always goes to the shop that might say "no" first
(CoinDCX), and only after that shop has handed over the goods does it go to the second shop (Delta).

**Each day, after the plan's 06:00 run:**
1. **For every pair the plan closed:**
   - CoinDCX's own "exit position" call first (it can only close, never open);
   - then Delta's close, marked **reduce-only** (it can only shrink a position).
   - If CoinDCX can't close, Delta's leg is kept so you stay hedged, and it retries every minute.
2. **For every pair the plan opened, CoinDCX first:**
   - **Checks first:** the market isn't close-only, both keys work, and both rupee rates were read just now.
   - **The size:** equal rupees. CoinDCX's quantity = Delta's dollars × 85 ÷ 102 ÷ price, down to CoinDCX's step. Both
     rates are read live, so if CoinDCX ever changes its ₹102, the size follows.
   - **The CoinDCX order is read back.** Only then is Delta's leg sent, with the plan's own contracts (a part-fill
     re-sizes it to the rupees that filled).
   - **If Delta's leg fails,** CoinDCX's is undone at once.
   - **If an answer is lost,** the exchange is asked what happened before anything is re-sent. Nothing is ever sent
     twice.
3. **An emergency stop on every "falls" bet** (each short leg), resting on its exchange where that leg's account would
   fall to 25% of its half:
   - **Delta:** a reduce-only stop on the **mark price**;
   - **CoinDCX:** the position's own stop loss. CoinDCX documents only last-price triggers, so a wick on CoinDCX's own
     order book could trigger it. That is noted for B3.
   - Re-placed each day and whenever the account or leg changes.

**Every minute: the watch.**
- If a leg has disappeared (its stop fired, the exchange liquidated it, or auto-deleveraging took it), the **twin is
  closed at once**.
- Both legs are written in the tax journal as "emergency stop" / "liquidated" / "auto-deleveraged", with an alert.

**At every start: the exchanges first.**
- Before doing anything, it reads both exchanges.
- A lone leg (the bot stopped between two orders) is closed first and reported. A pair on both exchanges is
  recognised, even if the bot's own record was lost.

**Every hour:** the exchanges' positions against the bot's record; any unexplained difference is an alert. In the dry
run it checks your REAL accounts hold nothing, and alerts if they ever do.

**The kill switch:** creating the file `data/c550_kill` cancels every order and closes every leg on both exchanges;
nothing new opens until the file is removed.

**Your keys:** if either exchange says a key is refused or expired (as CoinDCX did on 28 Oct), nothing new opens, closes
are still attempted, and you're alerted.

**The tax journal:** its own ledger has the same shape and the same "close" records as the plan's, with real fill
prices, fees, and rent from each exchange's own funding records by the month each was paid. So the tax statement
(`omega_tax_statement.py --live`) can read it directly. Tested.

**Kept provably separate:**
- the read-only client (C540) is unchanged;
- C550's order classes refuse any request not on their own short list (no wallet transfers, no withdrawals);
- keys stay only in `data/api_keys.json`.

## 3. The blocker: cross margin

**Why it matters (Round 24, 10 Oct):**
- On the 10 Oct 2025 crash, minute by minute, cross margin (each account's whole balance backing all its bets) kept the
  poorer account at 69.9% with the cap, and nothing was wiped.
- Isolated margin (each bet with its own small pot) would have liquidated 9-10 legs.

**What each exchange says:**

| | Delta India | CoinDCX (rupee futures) |
|---|---|---|
| its guide or help centre | "All contracts support Cross Margin mode"; an account-level setting, changeable only with no open positions | help centre (≈4 months old): "Select the Margin Type (INR or USDT)… Select the Margin Mode: Isolated or Cross Margin" |
| its API documentation | the mode-change call lists `isolated` and `portfolio`; the wallet has a `cross_position_margin` field | **"Cross margin mode is not supported on INR margined Futures"** (said three times) |
| readable by your read-only key now? | no: an empty account shows no mode (`/v2/users/trading_preferences` has none) | no: the cross-margin details call is documented as not for INR |

**What I need from you (about 2 minutes, in each app; no money needed):**
1. **CoinDCX app:** Futures → open any coin's order form → set **Margin Type: INR** → look at **Margin Mode**. Is
   **Cross** offered, or only Isolated? A screenshot is ideal.
2. **Delta India app:** Portfolio → **Change Margin Mode**. Is **Cross** offered? If so, switch the account to Cross
   now: it can only be changed while the account is empty.

**If CoinDCX's rupee futures are isolated-only, the honest options:**
- **(a) CoinDCX's USDT-margined futures, which do support cross.**
  - It needs USDT bought with rupees: a crypto purchase, with 1% TDS on selling it back and VDA tax on any USDT gain.
  - It breaks the "no crypto ever transferred" basis of the tax opinion.
  - **Not recommended.**
- **(b) Isolated margin on CoinDCX at about 1× (each leg's margin ≈ its whole size), with the bot topping up a leg from
  the account's free money when it nears liquidation** (CoinDCX's add-margin call).
  - This is a "hand-made cross margin". A short CoinDCX leg would be liquidated only near a +100% day.
  - 13 held coins jumped that much in 24 months, so expect a few forced closes a year. Each costs CoinDCX's liquidation
    fee (1.0-1.5% of the leg) plus the twin's close.
  - **This needs its own pre-registered research round on 1-minute data before adoption.** I'd run it in the
    2 December refresh window, before B3.
- **(c) Another rupee exchange with cross margin on INR futures:** a fresh census.

The order path already handles (b): the margin type is a single parameter, and a fill on anything but cross stops new
pairs (test T22).

## 4. The exchanges' rules, as recorded for B2

| | Delta India | CoinDCX |
|---|---|---|
| order id we choose | `client_order_id`, max 32 characters, unique among open orders; readable back by that id | none on futures orders: restart safety comes from our write-ahead record plus reading positions and open orders |
| "can only shrink" | `reduce_only` on any order | none; its **exit-position** call and the position **stop loss** close a whole position and can never open one |
| stop trigger | `stop_trigger_method`: `mark_price` (used), last traded, spot | `stop_trigger_instruction`: `last_price` (only this documented) |
| rupee rate | ₹85 per $ (`/v2/settings`, keyless) | ₹102 per USDT (`/futures/data/conversions`, keyless; "may change… in extreme market movements"; last changed 26 May 2026) |
| fees | 0.05% taker + 18% GST | 0.059% taker incl. GST on 493 of 504 rupee markets; 0.1003% on AGT, BULLA, CT, DODOX; commodities 0.0118% (each market's own fee is read) |
| liquidation | on the mark price; the engine takes over; if it can't close within a 5% loss, **auto-deleveraging**; an insurance fund; a liquidation fee (transaction type `liquidation_fee`) | a "liquidation clearance" fee by market and size (1.0-1.5% in its instrument data) on the position's notional; **no auto-deleveraging documented** in its API |
| errors | `{success:false, error:{code}}`, e.g. `insufficient_margin`, `ip_not_whitelisted_for_api_key`; signatures valid 5 s | HTTP 422 with a message (e.g. "API key expired. Please generate new keys.") |

CoinDCX's own fee and cross-margin web pages refused automated reading (HTTP 403), so the table uses its API
documentation, its instrument data and its help centre.

## 5. The preview on your real ledger (20 Nov 06:00 state, live public prices)

`research/c550_preview.py` ran C550's first dry day on the server's ledger with live Delta, Binance and CoinDCX data.
Orders went only to the pretend exchange; the real order function was replaced by one that fails if touched.

- **All 10 pairs built, CoinDCX first.** Delta's contracts equal the plan's on all 10.
- **The two legs are equal in rupees within ₹2**, e.g. AIN ₹8,311 vs ₹8,313, ALT ₹6,833 vs ₹6,833.
- **CoinDCX quantities respect its steps** (22.43 AUCTION, 260.4 KAITO, 1,417.2 STRK).
- **10 emergency stops**, 5 on each exchange: e.g. AIN's Delta short stops at 0.584 (a +437% day); NOT's CoinDCX short
  at 0.00256.
- **The day line says what would block live** ("the lock is off; cross margin not confirmed on CoinDCX and Delta
  India"). It also gives your real accounts (Delta 0; CoinDCX ₹0.07, no positions) beside the plan's ($552.98 /
  $498.10).

## 6. The tests (`omega_c550_test.py`, the 26 pre-registered)

All pass (56 checks). Every exchange is mocked; the real network functions raise if touched, and none was. Two
honest notes:
- **My first test draft had arithmetic slips** (35 Delta contracts where the trade is 50; one case set below CoinDCX's
  minimum, so it never reached the step it tested). The tests' criteria are unchanged.
- **One real gap was found and fixed in the code, not the test:**
  - CoinDCX's step rounds its quantity down. The first draft then shrank Delta's leg to match (49 contracts instead of
    the plan's 50).
  - The pre-registered T3 requires the plan's contracts on a full fill, and T5 allows the legs to differ by one CoinDCX
    step. They do (₹136 against a ₹204 step).
  - So Delta now keeps the plan's size on a full fill and re-sizes only on a part-fill (T10).

## 7. What changes in the plan

- **B3 (15 Dec)** runs this order path dry every day on the server, compares its orders with the paper plan, and adds
  the phone alert and the outside dead-man's switch. **G3's four clean weeks** count from there.
- **Cross margin must be confirmed on both exchanges before the pilot (1 Feb).** If CoinDCX's rupee futures are
  isolated-only, option (b) needs its pre-registered round first (proposed for the 2 Dec refresh window). The go/no-go
  scores G6's jump part on whatever is then built and tested.
- **Nothing about your money changes now.** It is still paper, and no deposits until 1 Feb.

## 8. Tests and battery

`omega_c550_test.py`: 26 tests, 56 checks, all pass. Full battery: **69 of 69** (66 Python + 3 shell). Getting there
took one container fix (the browser path link, as on 1 Nov) and two test fixes:

- **The first full run was 67 of 69.** `omega_c489_test.py` (1 check) and `omega_c530_test.py` (4 checks) failed.
- **Both fail the same way on the code from before C550** (checked in a separate copy of the last commit), so C550 did
  not cause them. Both are **date problems in the tests, not in the bot**:
  - **c489:** the test stamps its saved "flow" with 21 Sep 2026. The bot correctly keeps only the last 1,000 hours
    (about 42 days), so once the real clock passed about 2 Nov the stamp was dropped and the restart check failed. The
    test now stamps the current hour.
  - **c530:** the live-wiring part reads Pendle's saved 4 Oct list against today's date. The list's qualifying sUSDe PT
    matures on 26 Nov, under the rule's 21-day minimum from about 5 Nov, so "no market qualifies" and four checks on
    the Pendle row and panel failed. The test now moves the list forward by the whole days since 4 Oct, so it stands to
    today exactly as it stood to 4 Oct.
- **No check was loosened.** After the fixes, both pass, and so do `omega_c550_test.py` and the boot test, rerun on
  the final files.
- **Why nobody saw it sooner:** the last full battery ran on 1 Nov (68 of 68), before either date. The 6 Nov
  verification checked the server, not the battery. This is the first full run since. From now on both tests use
  today's date in these two places, so they cannot expire this way again.

## 9. Termius commands

**Deploy C550** (it only adds the dry order path; your plan's trading is unchanged):

```
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sudo journalctl -u omega --since "3 min ago" | grep -m1 "OMEGA C55"
```

Expect `OMEGA C550`. About two minutes after the restart (the dry path builds the plan's current 10 pairs at once, then
every day after the 06:00 run):

```
sudo -u omega bash -c 'grep -h "C550" "$(ls -t /home/omega/omega/omega_detail_*.log | head -1)" | tail -6 | cut -c1-300'
```

Expect "(dry) boot: both exchanges read", the pairs "opened … CoinDCX … then Delta …", the emergency stops, and
"would be blocked live: the lock C550_LIVE_OK is off; cross margin not confirmed on CoinDCX and Delta India". Send me
that output. After any restart the dry book starts again (its exchanges live in memory); that is by design.
