# Your plan for $1,000 (at most $1,200), with tax on net profit only

3 Oct 2026. You asked for:
- a budget of **$1,000** ($1,200 only if the target otherwise becomes
  unlikely);
- a target of **2–4% a month**;
- tax worked out **on profits only**.

Every number below comes from real history
(`research/c528_budget_plan.py/.txt/.json`).

## First: the $2,250 was never a bill

The "every account" total added up **every paper experiment the bot runs**:
the spot pot, the carry ledger and the Delta copy of the book. They are
research, not a shopping list.

## 1. How the tax works (India, Oct 2026)

| | INR-settled futures (**Delta Exchange India**) | USDT-settled futures (**Binance**) |
|---|---|---|
| what changes hands | rupees only | USDT, itself a crypto asset ("VDA") |
| most likely treatment | **business income** (speculative) | contested: business income, or the VDA rule |
| what is taxed | **the year's net profit only**, at your slab + 4% cess; fees and funding deductible; a loss is carried forward 4 years against future trading profit | business income: the same as Delta. **VDA rule: 30% + cess on every winning trade, losses ignored, no carry-forward** |
| TDS | none deducted | 1% when you sell USDT for rupees (creditable) |

**What doesn't change:**
- The new **Income-tax Act 2025** (in force from 1 Apr 2026) keeps the VDA
  rule unchanged.
- No CBDT circular or court ruling yet says which treatment crypto futures
  get.

**So "tax on profits only" is the right basis for Delta India.** It is
probably right for Binance too, but that is the contested part.

**What the bot now does:**
- **The plan total is taxed on net profit only** (C528).
- The dashboard shows "your plan after tax on its net profit" at
  `C528_TAX_RATE`: default **31.2%**, the top slab with cess. Set it to
  your own slab.
- A loss is taxed nothing.
- Under the new regime, if your total income stays within the 87A rebate
  limit (₹12 lakh), business income at normal rates may carry no tax at
  all. Your CA confirms.

## 2. The plan

| where | amount | venue | why there |
|---|---|---|---|
| **Main book** | **$500** | **Delta Exchange India** (rupees) | the cleanest "profits only" tax case; no USDT premium; no TDS |
| **Cross-venue trade** | **$500** | **$250 Delta India** (short legs) + **$250 Binance** (long legs) | the trade needs two venues; Binance's funding is the other side |
| **Reserve** | **$200, not invested** | your bank / Savings | only to top up a venue's margin after a sharp move |
| **Invested** | **$1,000** | | **$1,200 only if the reserve is ever used** |

**Why the book moves to Delta India:**
- **It costs about 0.3% a month.** On the book's own positions, Delta's
  funding averaged **3.7% a year more** than Binance's (2024-10 → 2026-08).
  So far in 2026 it is *cheaper* (−0.7% a year). Delta lists 94% of what
  the book holds, and whole contracts carry 93% of it at $500.
- **What that buys:**
  1. **Tax:** net-profit treatment is far more defensible on rupee-settled
     contracts. Under the VDA rule, the book on Binance nets **about 0% a
     year** (`research/c518_tax_india.txt`).
  2. **No USDT premium.** Funding Binance means buying USDT in India, which
     traded **7–10% above the dollar** in 2026. If that premium shrinks
     while your money is on Binance, you lose it. Only the $250 for the
     cross-venue trade's long legs stays exposed.
  3. **No 1% TDS** on the way in or out.
- **If your CA says Binance futures are business income too,** the book
  can stay on Binance and save the ~0.3% a month. It is a CA decision, not
  a strategy one.

**Why not put all $1,200 to work?**
- Returns are percentages: more money adds dollars, not better odds.
- The $200 is a safety margin for the two-venue trade. A broad 30–50% jump
  in small coins hurts the Delta short side before the Binance long side
  can be moved across.

**Why the two parts?** They make money for unrelated reasons (monthly
correlation −0.03): when one stalls, the other usually keeps going.

## 3. What to expect, after tax on net profit

The book uses its full 2020–26 history, including 2022's −28% year, with
its average cut by a third. The cross-venue trade uses its 24 months with
every assumption made harder. "Pessimistic" halves its edge again. Each
figure comes from 20,000 simulated years. Per month, after tax on the
year's net profit:

**$500 book + $500 cross-venue:**

| your slab (+ cess) | 0% | 10.4% | 20.8% | **31.2% (top)** |
|---|---|---|---|---|
| planning: typical month | +4.31% | +3.94% | +3.56% | **+3.16%** |
| planning: odds of averaging ≥ 2% | 93% | 91% | 88% | **83%** |
| pessimistic: typical month | +2.96% | +2.69% | +2.42% | **+2.13%** |
| pessimistic: odds of averaging ≥ 2% | 73% | 69% | 62% | **54%** |

- Chance of a losing year: ~0% (planning), 4% (pessimistic).
- **With the book on Delta India** (its extra funding included), at the
  top slab: **+3.08% a month, 81% odds** (planning); **+2.02%, 51%**
  (pessimistic). At a 10.4% slab: +3.84% and 89% (planning), +2.56% and
  65% (pessimistic).

**The alternatives, at the top slab (planning case):**

| split | typical month after tax | odds of ≥ 2% | chance of a losing year |
|---|---|---|---|
| all $1,000 in the book | +2.15% | 53% | 13% |
| **$500 book + $500 cross-venue** | **+3.16%** | **83%** | **~0%** |
| all $1,000 in cross-venue | +3.93% | 89% | ~0% (but 48% odds and 9% losing years in the pessimistic case) |
| $500 book + $500 in Savings | — | 25% (pre-tax) | 9% |

Months still lose: about **1 in 6**. Judge it by the year.

## 4. The one tax risk left: the Binance leg

**The risk:** the cross-venue trade can't avoid Binance; its long legs live
there. If your CA says Binance's USDT-settled futures fall under the VDA
rule, those legs are taxed on every winning trade, while the matching
Delta losses only count against Delta profits. Result:

| the cross-venue trade, per year | before tax | after tax |
|---|---|---|
| both legs business income (profits only), top slab | +62% (stress-tested) | about +43% |
| **Binance leg VDA, Delta leg business income** | +62% (stress-tested) | **+12.6%** |

**In that case the plan becomes $1,000 in the book on Delta India**
(+1.95% a month at the top slab, 49% odds, 15% chance of a losing year).
That is, unless we find a rupee-settled venue for the long legs:
- **CoinDCX's INR-margined futures** carry Binance's funding, but they
  still settle in USDT behind the scenes (checked on its API today).
- **Pi42** is untested (its API refuses this sandbox; your server may
  reach it).
- That search is round 17's job if it comes to this.

## 5. Gates before any real money

`C488_LIVE_OK` stays `False`; only you switch it.

### Gate 1: your CA (this decides the venues)

1. Delta Exchange India perpetual futures (INR-settled): business income?
   Speculative or not?
2. Binance USDⓈ-M perpetual futures (USDT-settled): VDA under the VDA
   section, or business income?
3. If both are business income, can a loss on one venue offset a profit on
   the other within the year?
4. Funding paid and received: deductible / taxable as business income?
5. Does the 87A rebate apply to this income at my total income?
6. TDS: any obligation on either?

| the CA says | the plan |
|---|---|
| both business income | as in §2 (the book may stay on Binance to save ~0.3%/month) |
| Delta business, Binance VDA | **$1,000 book on Delta India**; the cross-venue trade waits for a rupee-settled long leg |
| both VDA | **no live trading**; money stays in FD / Savings (0.55–0.67% a month) |

### Gate 2: the cross-venue trade's paper trial (the bar is written now, before the result)

Review on **28 Nov 2026**, after 8 full weeks of paper. Fund it only if
**all** hold:
- (a) net return over the 8 weeks ≥ **+3.7%** after its costs (about
  2%/month);
- (b) at least **6 of 8 weeks** positive;
- (c) funding collected ≥ **2× its fees**;
- (d) Delta's funding mechanics and listings unchanged.

If it fails: **$1,000 in the book** (on Delta, per gate 1).

### Gate 3: the Delta book's paper record

The same plan already runs on paper on Delta India beside the Binance book
(since 2 Oct). On 28 Nov, if the Delta copy has fallen behind the Binance
book by more than 1% a month (beyond the expected ~0.3%), keep the book on
Binance and accept the tax question there.

### Gate 4: the live order paths (my work)

- The book's live orders on the chosen venue, and both legs of the
  cross-venue trade.
- A margin watch on each venue that tells you when to use the reserve.
- The book and the cross-venue legs never share a position.
- Each is tested on paper, then with a tiny live order.

## 6. Timeline

| when | you | me |
|---|---|---|
| this week | send the 6 questions to your CA | everything stays on paper; start the live order path for the book |
| the CA answers | — | I set the venues to match (§5 table) |
| **28 Nov 2026** | — | the gate 2 and gate 3 reviews |
| gates pass | deposit $750 on Delta India (book $500 + short legs $250), $250 on Binance (long legs) | start live; margin watch on |
| every month | read the monthly review | it compares each part with the tables above, after tax on net profit |

## 7. Rules for live money

1. Don't add money after a bad month or pull it out after a good one.
2. The reserve is for margin only.
3. The risk dial stays at 20% (at 30%: +6.9% a month on average but a 51%
   worst drop; the code caps it at 20).
4. The book trades 20 coins at every size (C528). At $1,000, 40 coins
   averaged +4.06% a month with a 47% worst drop, against 20 coins' +4.76%
   and 37%.
5. Keep every exchange statement. Business income needs ITR-3 and proper
   books, and a loss carried forward needs a return filed on time.

## 8. What changed in the bot (C528)

- **"Your plan"** on the dashboard = **the book on Delta India + the
  cross-venue trade = $1,000**, with the budget line ($1,000 + $200
  reserve).
  - The Binance book (with Savings) keeps running as the comparison for
    gate 3. It, the spot pot and carry are marked **experiment**.
  - If the CA rules Binance's futures business income too, set
    `C527_PLAN = ('book', 'savings', 'xvenue')`.
- **Tax on net profit only:** "your plan after tax on its net profit" at
  `C528_TAX_RATE` (default 31.2%); a loss is not taxed.
- `C488_TOPN = 20` (was `'auto'`). `C527_PLAN`, `C528_BUDGET`,
  `C528_RESERVE`, `C528_TAX_RATE` in the config.
- `research/c528_budget_plan.py/.txt/.json`: the splits, the profits-only
  tax by slab, and the mixed case.

Sources:
- crypto futures tax treatment:
  [CAclubindia: speculative treatment of crypto futures](https://www.caclubindia.com/articles/crypto-futures-tax-in-india-how-speculative-treatment-can-reduce-tax-55965.asp),
  [KoinX: two tax systems for crypto futures](https://www.koinx.com/in/crypto-tax-stories/crypto-futures-traders-in-india-are-filing-taxes-under-two-different-systems),
  [Mudrex: tax on crypto futures](https://mudrex.com/learn/crypto-tax-on-futures-trading-india/),
  [CoinSwitch: crypto F&O tax 2026](https://coinswitch.co/switch/crypto-futures-derivatives/crypto-futures-options-tax/);
- the new Act:
  [Income-tax Act 2025 and VDA rules (Patron)](https://www.patronaccounting.com/blog/crypto-vda-taxation-income-tax-act-2025-rules);
- CoinDCX INR futures:
  [CoinDCX INR margin futures](https://coindcx.com/blog/crypto-futures-trading/coindcx-launches-inr-margin-futures/);
- the USDT premium:
  [India's USDT premium (The Block)](https://theblock.co/post/406502/indias-usdt-premium-tops-8-5-as-crypto-remittance-crackdown-squeezes-stablecoin-supply-report).
