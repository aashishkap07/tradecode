# Round 25 pre-registration: the plan with CoinDCX's legs on ISOLATED margin

Committed and pushed **before** any test below runs. 20 Nov 2026, ~12:00 IST. (Item (j) of the 2 Dec refresh routine,
brought forward: the operator answered on 20 Nov.)

## Why

- **The operator's screenshots, 20 Nov 2026:**
  - **CoinDCX app, 10:53 IST:** ETH • USDT futures, rupee margin. "Select margin mode" offers only **Isolated**, with the
    note *"Cross margin mode is currently only available in USDT margin Futures."*
  - **Delta India app, 11:00 IST:** Margin mode **Cross (Current)**; available margin shown in USD.
- **So CoinDCX's rupee (INR) futures cannot use cross margin.** Its API documentation said so (15 Nov); its app
  confirms it. Round 24 (10 Oct) chose cross margin on both exchanges: on 1-minute data, isolated legs at 1/3 or 1/2
  of their size were liquidated on the 10 Oct 2025 crash (9-10 legs).
- **CoinDCX's own rules, read 20 Nov from its public instrument data (rupee-margined):**
  - on the coins checked, ALT and NOT: leverage at most 5×; maintenance ("safety") margin 1.5% of a position at the
    plan's leg size (~₹8,500; the first tier, under ₹65,000 / ₹32,500); liquidation fee 1.5%;
  - ETH: 20×, 0.5%, 1.0%;
  - every coin's own figures are read below.
- **Its API can move margin:**
  - `positions/add_margin` and `positions/remove_margin`, in rupees for rupee futures;
  - `positions/update_leverage`.
- **What liquidation means here:** a liquidated isolated leg loses all the margin posted on it. The maintenance margin
  left at liquidation goes as the fee.
- **The sizing problem:**
  - Each account holds about 2× its own money in legs (10 pairs × 10% of the whole $1,000 on a $500 account).
  - So with the plan's sizes, isolated margin on CoinDCX averages at least 2×, unless margin is left free as a
    top-up reserve.

## Data and engine (fixed now)

- **Engine:** Round 23's `legs3` / `sides3` / `run3`:
  - with the C549 correction (`c524_xvenue.C549_HOURLY = True`);
  - the K6 cap (at most 6 of 10 pairs facing one way);
  - CoinDCX's costs ×5 for every bar (×1 reported); tax T1 at 31.2%;
  - the cached 24 months 2024-10-01 → 2026-09-30 (rebuilt 1 Nov for C549);
  - **the coin list fixed as Round 23's 63 coins** (`research/r23_round23.json`).
- **Reference values (C549):** +3.66% a month before tax, +2.52% after tax (×5 costs), +3.13% after tax (×1), poorer
  account's lowest point 59.7%.
- **Wobble lists:** as Round 23: the 5 largest-P&L coins removed in turn; Delta turnover floors $75k and $150k, on today's
  turnover.
- **Copied as `legs5` / `sides5`** with one switch: CoinDCX's margin mode.
  - **Engine check:** with the switch at cross they must reproduce `legs3` / `sides3` exactly (net, lowest account,
    transfers a year). Otherwise nothing below is read.
- **The accounts in Round 25 are booked at constant quantity** (as a real futures position, and as the paper ledger
  holds them), for every variant and for the cross reference:
  - each leg's price result = its quantity × the price change, at Binance's mark for CoinDCX's leg and Delta's for
    Delta's;
  - rent on its current notional.
  - The earlier rounds booked a constant dollar size each day; the two differ only for coins that trend for weeks.
  - **"XQ"** = cross on both, booked this way: the reference for the account bars below.
  - The profit and tax engine (`legs5`) keeps Round 23's booking, so its reference is exactly `run3`'s.
- **CoinDCX's rules per coin:** read once, now, from its public instrument data (rupee-margined) and saved with the read
  time:
  - the maintenance rate at the leg's size (the first tier of `dynamic_safety_margin_details`);
  - `liquidation_fee`;
  - `max_leverage_long` / `max_leverage_short`.
  - A coin CoinDCX no longer lists: 1.5%, 1.5% and 5×.
- **Prices:**
  - CoinDCX's legs on Binance's mark prices (CoinDCX's rent and prices follow Binance's; gate G2);
  - daily mark highs and lows as Round 23 (Delta `MARK:` 1d candles, Binance `markPriceKlines` 1d);
  - minute replays on 1-minute marks (Round 24's `minute_day` data).

## How a CoinDCX leg on isolated margin is booked

- **Entry:** the leg posts **margin = its size ÷ L** from the CoinDCX account's free balance. L is the variant's
  leverage, at most the coin's own maximum. If the free balance is short, that pair is not opened that day (counted).
- **Its equity** = posted margin + its price result since entry. Rent goes to the free balance.
- **Liquidation:**
  - **When:** at the day's adverse mark extreme (a long's low, a short's high; Binance's mark), its equity falls to
    or below maintenance (the coin's rate × quantity × price).
  - **The CoinDCX side:** the account loses all the leg's posted margin.
  - **The twin (Delta's leg) is closed at once.** Its gain = the smaller of the move to the liquidation price and its
    own day's extreme move that way, minus 5% of its size for the one-minute delay (Round 23's slip), plus Delta's exit
    cost.
  - **Re-entry:** the pair may re-enter under the normal rule the next day.
- **Top-ups (the variants marked T):**
  - **The rule:** the bot keeps each leg's equity at no less than its size ÷ L (its starting distance to liquidation),
    adding margin from the free balance.
  - **When the free balance cannot cover every leg,** it is shared in proportion to need.
  - **Timing:** the 24-month daily engine assumes this is done in time (each minute). The minute replays make it one
    minute late (the 60-second watch).
  - **At each daily run,** a leg returns top-ups it no longer needs to the free balance (only posted margin above
    size ÷ L; an unrealised profit is never counted as movable).
- **Delta's account stays on cross margin, unchanged.** An account is "wiped" when its value falls to its maintenance
  (0.5% of the notional held there, as Round 24).
- **Even-outs:** they work as before (the 65% trigger), but money can leave CoinDCX only from its free balance.

## The variants (each is 10 × 10% with the K6 cap; only CoinDCX's margin changes)

| | CoinDCX margin per leg | top-ups |
|---|---|---|
| **I2** | ½ of its size (2×) | none (all the money is posted) |
| **I3T** | ⅓ (3×) | from the free balance |
| **I5T** | ⅕ (5×, or the coin's maximum if lower) | from the free balance |
| X / XQ | cross on both (the plan as researched; **not available on CoinDCX's rupee futures**) | — |

## The minute replays

- **Days:** Round 23's 46 (Round 24's six + the 40 largest days on which a held coin moved ≥ 30% intraday), fixed in
  `research/r23_round23.json`.
- **The books:** each variant's own, at the start of each day: each CoinDCX leg's posted margin and entry price, the free
  balance, and Delta's account.
- **Every minute:**
  - each CoinDCX leg is checked at the minute's adverse extreme against its liquidation price;
  - **a liquidated leg's twin is closed at the next minute's close** (Delta's 1-minute mark): the actual price, no
    assumed slip;
  - T variants top up at each minute's close, effective from the next minute;
  - Delta's account is as Round 24's `minute_day` (cross).
- **Calibration:**
  - E = the minute model's loss from liquidations on the replayed days, minus the daily model's on the same days and
    pairs.
  - **If E > 0, half of E is added to the yearly cost before bar 2 is read.** The replayed days are inside the 24 months.

## The bars (costs ×5)

1. **Part A on every wobble list:** average month ≥ +1.5% before tax; no month below −4%; the poorer account ≥ 40%; HAC
   t ≥ 2; both years positive.
2. **Cost:** after tax ≥ the cross reference's (`run3`) − **$30 a year**, after the calibration.
3. **Accounts:** the poorer account's lowest daily point ≥ XQ's − **5 points**.
4. **Replays:** no account wiped on any replayed day, and the poorer account's lowest point across them ≥ XQ's −
   **5 points**.

**What each result means:**
- **PASS** = all four hold.
- **USABLE AT A COST** = bars 1, 3 and 4 hold, but bar 2 fails. It is reported with its cost in dollars a year after
  tax. Cross margin is not available on CoinDCX's rupee futures, so the cross reference is not a real choice. **Whether
  to go ahead at that cost is the operator's decision.**
- **FAIL** = bar 1, 3 or 4 fails.

**More than one PASS (or, failing that, more than one USABLE):** the higher after-tax result wins. Within $5 a year, the
one with fewer liquidations.

**Reported but not bars:** liquidations a year, pairs not opened for lack of free margin, top-ups used, CoinDCX's lowest
free balance, E, and each variant at costs ×1.

## What happens next

- **PASS:**
  - B3 (15 Dec) builds it into the order path: CoinDCX's legs isolated at the chosen leverage, the top-up watch, margin
    returned at each daily run.
  - The dry run compares it with paper, and the paper ledger models the liquidations from then on.
  - G6's jump part at the go/no-go is scored on this design.
- **USABLE AT A COST:** the operator decides: accept the stated cost, or the options below.
- **FAIL:** March cannot use CoinDCX's rupee futures as planned. The options are stated, each needing its own work:
  - (a) CoinDCX's USDT-margined futures (cross available; not recommended, because it breaks the tax opinion's
    "no crypto bought" basis);
  - (c) another rupee exchange with cross margin on rupee futures (a census);
  - (d) a smaller plan on isolated margin (smaller legs, or more of the money on CoinDCX).
- **Nothing here touches real money.** `C488_LIVE_OK` and `C550_LIVE_OK` stay False.
