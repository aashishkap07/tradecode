# What you are trading, in plain words (and why we left Binance)

Written 5 Oct 2026 for the operator. No jargon without an explanation.

---

## 1. The one-minute version

- On **two Indian exchanges**, Delta Exchange India and Pi42, the bot holds
  **the same coin twice**:
  - a bet that it **falls** on Delta;
  - a bet of the same size that it **rises** on Pi42.
- **Whatever the price does, the two bets cancel.** One gains what the other
  loses.
- **What's left is "funding".** Funding is a small fee that the exchanges make
  traders pay each other every few hours. On Delta the bot *receives* it. On
  Pi42 it *pays* very little. **The difference is the profit.**
- Today it is all **paper**: a simulation at real prices. No money moves.

## 2. The words, one at a time

### A futures bet ("perpetual future", or "perp")
- It's a bet on a coin's price. **You don't own the coin.**
- Think of betting a friend on tomorrow's price of gold without buying any
  gold.
- "Perpetual" means the bet has no end date. You keep it until you close it.

### Long and short
- **Long** = you win if the price **rises**.
- **Short** = you win if the price **falls**.

### Margin and leverage
- **Margin** is the deposit the exchange holds while your bet is open, like
  the security deposit on a rented flat.
- **Leverage** is how big your bets are compared with that deposit. Our plan
  uses about **2×**: $500 of your money on an exchange holds about $1,000 of
  bets there.

### Funding: the most important one
**Why it exists:**
- A normal futures contract has an expiry date, and on that day its price must
  equal the coin's real price.
- A *perpetual* one never expires, so the exchange needs another way to stop
  its price drifting away from the real one.

**How it works:**
- Every few hours (usually every 8 hours, for some coins every 4 or 1), **the
  more crowded side pays the less crowded side** a small percentage of their
  bet.
  - If most people are betting the price will rise, the **longs pay the
    shorts**.
  - If most are betting it will fall, the **shorts pay the longs**.
- That payment pushes people to the quieter side and keeps the price honest.

**Analogy: rent.**
- When everyone wants the same flat, tenants pay rent to the landlord.
- In a perp, the crowded side is the tenant and the quiet side is the
  landlord.
- **If you hold the quiet side, you are paid rent every few hours just for
  holding it.**

### Why funding is different on two exchanges
- Each exchange has its own crowd, so each sets its own rent.
- **Delta Exchange India's crowd** is mostly Indian traders betting coins
  *up*. On many coins its longs pay shorts a lot of rent.
- **Pi42** follows Binance's global crowd, where the rent on the same coin is
  usually much lower.
  - Pi42 even copies Binance's prices. Tonight 91% of its rates matched
    Binance's.

### The "spread"
- The spread is the **difference in rent** between the two exchanges for the
  same coin, written as % per year.
- Example, KAITO at entry: **97% a year**. Holding $100 short on Delta and
  $100 long on Pi42 collects roughly **0.27% a day, about 27 cents**, while
  the gap stays that wide.
- Gaps shrink after a while. That's why the bot closes a pair when its gap
  falls under 10% a year, and only opens one when the gap has averaged at
  least 20% a year over the last week.

### A "leg" and a "pair"
- A **leg** is **one of the two bets**: the short on Delta is one leg, the
  long on Pi42 is the other.
- The two legs on the same coin make a **pair**, like the two legs of a pair
  of trousers.
- The bot holds up to **10 pairs**, so up to 20 legs. Each leg is about
  **$100**, which is 10% of your $1,000.

### "Side" or "account"
- Your **Delta account** holds $500 and your **Pi42 account** holds $500.
- The screen calls them the "Delta side" and the "Pi42 side".

### Mark price
- The exchange's fair price for a coin, used to value open bets. It isn't the
  last trade, so one odd trade can't distort it.

### Fees and GST
- Each exchange charges a fee to open or close a bet:
  - Pi42 0.10% + 18% GST;
  - Delta 0.05% + 18% GST;
  - plus a little slippage.
- Opening and closing one pair costs about **43 cents** in all. At 27 cents a
  day of rent, that's paid back in about 2 days.

### Liquidation
- If an account loses so much that its deposit no longer covers its bets, the
  exchange **force-closes them**.
- If that ever happened to one leg, the other leg would be left unprotected.
- That's why the bot:
  - uses only 2× leverage;
  - **warns at 65%** of an account's starting money;
  - says **"move money NOW"** at 50%.

### Even-out (transfer)
- Explained with a real example in section 3.

### Paper vs live
- **Paper** = a flight simulator: real prices, real rent, real fees, but no
  real money moves. That's where we are now.
- **Live** = real money. Planned for March 2027, only if the tests in
  `reports/2026-10-04_live_march_roadmap.md` pass.

## 3. One pair, start to finish (KAITO, rounded numbers)

**Setup:**

| | Delta (short) | Pi42 (long) | together |
|---|---|---|---|
| bet size | $100 | $100 | |
| KAITO rises 20% | **−$20** | **+$20** | **$0** |
| KAITO falls 20% | **+$20** | **−$20** | **$0** |
| rent, per day, at a 97%/yr gap | collects ~27¢ | pays ~0¢ | **+27¢ a day** |
| fees to open and close | | | −43¢ once |

**Real example from yesterday:**
- AIN jumped **25%**.
- Its Delta leg lost **$46.18**. Its Pi42 leg gained **$46.54** (checked on both exchanges' minute prices at 21:50 IST).
- Together: **+36 cents**. The price move cancelled, as designed.

**The catch: two separate piggy banks.**
- Overall nothing was lost, but the $46.18 loss came out of the **Delta**
  account and the $46.54 gain went into the **Pi42** account.
- All 10 pairs lean the same way (short on Delta), so after a rally the Delta
  account gets thin and Pi42's gets fat. Last night: Delta **$328**, Pi42
  **$672**.
- So at its daily run the bot **moves money across** when one account drops
  below 65% of the average, and once a month regardless.
  - In paper it does this itself.
  - **Live, it'll be your bank transfer**: withdraw rupees from one
    exchange, deposit on the other. The bot will say how much and which way.

**What to expect:**
- About **4% a month on the whole $1,000 before tax** (~$41).
- About **3.1% after tax** (~$31, about ₹3,000).
- Some months better, some worse.
- That figure already allows for gaps shrinking, fees, and pairs being swapped.

## 4. Why we moved from Binance to Delta + Pi42

There were three reasons, and tax was the big one. I'm acting as your
stand-in CA here; I'm not a registered one, and the law on crypto futures
isn't fully settled. This is the safe reading.

**1. Tax: Binance could have taxed the winning leg and ignored the losing one.**
- Binance's futures are settled in USDT, a crypto token. The safe reading
  treats profit there as **crypto (VDA) income** (s.115BBH):
  - 30% + cess on **every gain**;
  - **losses not allowed to offset anything**.
- In a two-leg trade, one leg always gains and the other loses. Take AIN with
  the long leg on Binance:

  | | Delta leg | Binance leg | your real profit | tax |
  |---|---|---|---|---|
  | Binance as a VDA | −$46.18 (loss, can't be used against the VDA gain) | +$46.54 (taxed at 31.2%) | +$0.36 | **≈ $14.52** |
  | both on Indian rupee exchanges | −$46.18 | +$46.54 | +$0.36 | **≈ $0.11** (31.2% of the net) |

- Over a year of swings like this, the tax could swallow the whole profit.
- **On two Indian rupee exchanges both legs are one business. You're taxed
  only on the net profit**, and a losing year can be carried forward 4 years.

**2. The law on sending money abroad.**
- Under RBI's Liberalised Remittance Scheme, an Indian resident can't send
  money abroad to use as margin for derivatives on a foreign exchange.
- Delta India and Pi42 take **rupees from your Indian bank**, so nothing
  leaves India.

**3. Simpler paperwork.**
- Rupee perps carry **no 1% TDS** (that applies to crypto transfers).
- The profit goes on **ITR-3** as speculative business income at your slab
  (31.2%).

**What we gave up:**
- Pi42 lists fewer coins (182) than Binance, so some of the widest gaps can't
  be traded. AIN, which closes at 06:00 IST, is one of them.
- In the research this cut the expected return from about **+72% a year to
  about +50% a year before tax**.
- But with Binance, much of the +72% could have gone in tax, and there was
  the remittance-law problem. The rupee route keeps far more of what is
  earned, legally.

**Binance is still used, but never with your money:**
- for **prices and funding data** (Pi42 copies Binance's prices, and the bot
  reads Pi42's rent from Binance);
- for the **paper experiment** (the trend/momentum "book"), which is only a
  test bench.

## 5. Quick reference

| word | plain meaning |
|---|---|
| perp / futures | a bet on a coin's price with no end date; you don't own the coin |
| long / short | bet it rises / bet it falls |
| margin | the deposit the exchange holds while a bet is open |
| leverage 2× | $500 deposit holds about $1,000 of bets |
| funding | "rent" the crowded side pays the quiet side every few hours |
| spread | the rent difference between Delta and Pi42 for the same coin, % per year |
| leg | one of the two bets (Delta short, or Pi42 long) |
| pair | the two legs on the same coin; up to 10 pairs |
| side / account | your money on one exchange ($500 each) |
| even-out | moving money from the fuller account to the thinner one |
| mark price | the exchange's fair price used to value bets |
| liquidation | the exchange force-closing bets when a deposit runs out |
| paper / live | simulation at real prices / real money |
