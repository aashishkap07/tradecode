# Round 22 (C542) pre-registration: the best exchange pair, and its best settings, after tax

Committed and pushed **before** any test below runs. 8 Oct 2026, ~17:45 IST.

## Why

The operator (8 Oct), after C541:
- "my coindcx account is active";
- "in your earlier studies you seemed to have missed coindcx as a more profitable alternative which was why
  pi42 was chosen";
- "please research again very carefully to find the best exchange pair with best average monthly returns
  target 2-4% after taxation".

**The miss, stated plainly.** On 3 Oct CoinDCX was checked twice:
1. **As a rent source of its own** (Round 16): it is identical to Binance, so CoinDCX against Binance has
   nothing to collect. That was correct.
2. **As the rupee leg opposite Delta** (C528 report): it was set aside because "they still settle in USDT
   behind the scenes" (its instrument data: `settle_currency_short_name` USDT). That was a tax caution, but
   it was never quantified, and the plan moved to Pi42 (C532) without CoinDCX's fee or coin list ever being
   run. Round 21 found that this cost about +14 points a year before tax.

## Facts established before the test (8 Oct, live, from the research machine)

**Where each Indian venue's rent (funding) comes from:**

| venue | rent source | checked how | Delta coins | taker fee | contract | API (fake key) |
|---|---|---|---|---|---|---|
| Delta Exchange India | **its own** (premium-based, 8 h, Delta's formula) | earlier rounds | — | 0.05% + GST | USD-settled | works (C540) |
| CoinDCX | **Binance's** | `fr` == Binance's last settled rate on 191/191; same intervals | 191 | 0.05% + GST | USDT-quoted, rupee margin at a fixed Rs 102 | 401 JSON, **also from the operator's server** (8 Oct 17:07 IST) |
| ZebPay | **Binance's** | `upcomingFundingRate` vs Binance's live estimate: 177 of 179 rupee contracts within 0.002% (median gap 0.0003%); 271/274 USDT | 101 rupee-priced (`BTCINR`), 132 in all | 0.10% (31 USDT pairs 0.06%); GST assumed on top | rupee-priced (like Pi42), or USDT with rupee margin | 400 JSON "signature mismatching" |
| Pi42 | Binance's (4 Oct: 87% within 0.002%) | C532 | 113 | 0.10% + GST | rupee-priced | **403 page to everyone** |
| Mudrex | not published | no public rate; key needed | — | 0.05% (INR) | USDT-quoted, rupee margin | 401 JSON; secret sent unsigned |
| CoinSwitch | not published | every endpoint needs a key | — | 0.05% | USDT-margined | 401 JSON |
| WazirX (futures since May 2026) | not published | no futures API found | — | 0.04% | rupee | — |
| SunCrypto, Cosmic | not published | no API found | — | — | — | — |
| Giottus, Bitbns | — | USDT-margined (VDA) | — | — | — | — |

**What this means for pairs:**
- A rent-gap trade needs two venues whose rates **differ**.
- Every venue with a readable rate other than Delta copies Binance. So any pair of them (CoinDCX + ZebPay,
  CoinDCX + Pi42, ZebPay + Pi42) has a gap of zero: nothing to collect.
- Venues whose rates cannot be read (Mudrex, CoinSwitch, WazirX, SunCrypto, Cosmic) cannot be tested on
  history and stay out until they publish their rates.
- **So the candidate pairs are Delta + one Binance-copier.** They differ only in coin list, fee, access and
  tax treatment.

## Engine (fixed now)

- Round 21's, unchanged: `research/c532_india_only.py`'s `xv_pi42`. That is "ALL harder": midnight timing,
  Delta's mark, 18% GST on rent paid at both venues, whole Delta contracts, $1,000, Oct 2024 -> Sep 2026.
- `research/c531_split_600.py`'s `sides` (65% even-out), `C524_MARK=1`, the same cache, one Delta turnover
  read per run. A coin needs Delta turnover >= $100k and must move with Binance (correlation >= 0.9).
- **New, for tax only:** a copy of the `xv_pi42` loop that keeps each position's two legs apart.
  - It must reproduce `xv_pi42`'s pre-tax total exactly before any figure is read.
- **Costs:**
  - **x5 (the gate, as every round since 15)**;
  - x1 (the expected case, reported).

## Tax (two readings, both reported for every pair)

The operator is in the top slab (31.2%).

- **T1** (the C532 reading for rupee-settled perpetuals on Indian exchanges):
  - both legs are speculative business income;
  - netted by Indian financial year (Apr-Mar);
  - a loss is carried forward;
  - the profit is taxed at 31.2%.
- **T2** (the cautious reading, for a leg settled in USDT behind the scenes):
  - that leg is a VDA: 31.2% of each closed position's leg gain, losses ignored;
  - the Delta leg stays T1.

Which reading is likelier for each venue:
- **T1 likely:** Pi42 and ZebPay's rupee-priced contracts.
- **Uncertain until a CA rules:** CoinDCX's and ZebPay's USDT contracts on rupee margin.

**After-tax month** = (the pre-tax total minus the tax) / 24 months. "Months >= 2% after tax" counts months
>= 2% / 0.688 before tax.

## Part A: the pair

| | second leg | its coins | its cost a side |
|---|---|---|---|
| P0 | Pi42 (reference; blocked) | Pi42's 113 | 0.10% x 1.18 + 0.02% |
| **C** | **CoinDCX** | CoinDCX's 191 | 0.05% x 1.18 + 0.02% |
| Zi | ZebPay, rupee-priced only | ZebPay's 101 | 0.10% x 1.18 + 0.02% |
| Za | ZebPay, all | ZebPay's 132 | 0.10% x 1.18 + 0.02% (31 coins are 0.06%; not credited) |

**A pair passes** only if, at costs x5:
- G1 holds: average month >= +1.5%, no month below -4%, the poorer account >= 40%;
- HAC t >= 2;
- both years are positive;
- the list wobble holds: the 5 largest-P&L coins removed in turn, and turnover floors $75k and $150k, each
  keep the worst month >= -4% and the poorer account >= 40%.

**The plan's pair** = the passing pair with the highest after-tax average month under T1. Excluded: P0,
whose gateway is shut. The T2 ranking is also fixed now: if a CA rules the winner's leg a VDA, the pick is
the passing pair with the highest T2 figure.

## Part B: the winner's settings (bet size x number of pairs)

- **Grid:** at most 10 / 15 / 20 pairs x 8% / 10% / 12% a leg (nine variants; 10 x 10% is today's).
- **A variant replaces 10 x 10% only if, at costs x5, all of these hold:**
  - every Part A bar holds, on every wobble list;
  - it earns >= $50 a year more after tax (T1) than 10 x 10%;
  - it adds at most one more losing month (Round 20's rule).
- **Among the variants that pass:** the highest after-tax (T1) average month wins. If two are within $50 a
  year of each other, the one with fewer pairs and smaller bets wins.
- The entry/exit thresholds, the window and the decision time stay as Round 19 left them. They are not
  re-opened here.

## Part C (information only, never adopted from this run)

- The winner with every order filled at the **maker** fee on both venues: Delta 0.02% x 1.18, CoinDCX 0.02% x
  1.18, no half-spread.
- That upper bound can only be measured with real orders (gate G4).

## What happens next

- **The winner becomes the plan's second leg in paper (C542).** If it is CoinDCX:
  - the Pi42 legs are closed and reopened on CoinDCX in the ledger, with both venues' fees booked;
  - the history is kept.
- **CoinDCX's read-only client and key guide are built (B1 for CoinDCX).**
- **Part B's winner, if any, becomes the plan's settings.** If none passes, 10 x 10% stays.
