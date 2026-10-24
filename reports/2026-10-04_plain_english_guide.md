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

**Why one side has to pay (the full reason):**
- Every bet up is matched by someone betting down, so both sides always hold
  the same total. "Crowded" really means **more eager**.
- Eager up-bettors keep paying a little more to get in, so the bet's price
  floats **above** the coin's real price. With no end date, nothing on the
  calendar pulls it back.
- The rent is a charge on the eager side, set higher the further the two
  prices drift apart. Three things follow:
  - betting up costs rent, so fewer people want to;
  - betting down earns rent, so more people want to;
  - careful traders buy the real coin and bet down the same amount. Their
    price risk cancels and they collect the rent, and their bets down push the
    bet's price back.
- When the prices meet, the rent falls to a small normal level (on Binance
  0.01% every 8 hours). If the bet's price drops below the real price, it
  flips and down-bettors pay up-bettors.
- **Like surge pricing on Ola or Uber:** too many riders, so rides cost extra
  and the extra goes to the drivers, until it balances.
- The exchange doesn't keep the rent; it passes it between traders.
- **The bot is the careful trader on Delta.** It takes the down side to
  collect Delta's rent, and cancels the price risk with a cheap bet up on Pi42
  instead of buying the real coin.

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

## 6. How prices move, and what sets a coin's real price

**A price is the last deal between a buyer and a seller.**
- Picture a **vegetable market**. Sellers call out what they want, buyers
  what they'll pay. The "price" is wherever the last deal happened.
- An exchange is the same market on a screen. It keeps a list of waiting
  sellers and waiting buyers:

  | waiting sellers want | waiting buyers offer |
  |---|---|
  | $103 | $99 |
  | $102 | $98 |
  | $101 | $97 |

- The last deal was at **$100**.

**How eagerness pushes the price.**
- Ten eager buyers arrive and say "I'll take it now". They use up the $101
  seller, then the $102 seller.
- The last deal is now **$102**, so the price went **up**.
- Eager sellers do the opposite and push it **down**.
- More eager buying than selling means the price rises; more eager selling
  means it falls.

**The bets have their own market.**
- A perp (the bet) trades in its **own** list of buyers and sellers, separate
  from the market for the real coin.
- If many people want to bet up, they have to outbid each other to get in, so
  the **bet's** price climbs above the **coin's** price.
- **IPL ticket resale** works the same way. Face value is ₹1,000 (the real
  price), but eager fans pay ₹1,200 on resale.
- Funding, the rent, is what pulls the two prices back together.
- The careful traders who collect that rent also buy the real coin, which
  nudges the real price up a little. The two prices meet in the middle.

**What sets the coin's real price.** It's the same market logic, on the
exchanges where real coins are bought and sold. The exchanges' "real price"
(the index) is an average of the coin's price on several big markets.
People buy or sell because of:
1. **Supply.** How many coins exist and how many new ones are released.
   - Bitcoin is capped at 21 million.
   - Many small coins release more coins to their founders every month, which
     adds sellers.
2. **Usefulness.** Some coins are needed to use a network (ETH pays the fees
   on Ethereum).
3. **Belief and hype.** Most of a coin's price is what people expect it to be
   worth later: news, social media, celebrity posts.
4. **Big buyers.** Funds and companies (for example the Bitcoin funds on US
   stock markets) can buy a lot at once.
5. **Rules.** A country banning or approving crypto moves prices quickly.
6. **The world's money mood.** When interest rates fall and people feel rich,
   they buy risky things; in a panic they sell. Crypto often moves with stock
   markets.
7. **Bitcoin leads.** Most coins follow Bitcoin's direction.

Unlike a company's share, most coins have no profits or factory behind them.
The price is mostly what people believe others will pay later, which is why
crypto swings so much.

**Why small coins jump so much.**
- Coins like AIN or KAITO have few buyers and sellers. It's like a village
  market where one big buyer can empty every stall.
- A little extra demand moves the price a lot. That's how AIN rose 25% in one
  day on 4 Oct.

**What it means for your bot.**
- The bot **doesn't guess** where prices go. Its two bets cancel, so whether a
  coin rises or falls hardly matters.
- It earns from the rent that eager bettors pay.
- Prices matter in only one way: a big move empties one jar and fills the
  other (the even-out).

### 6b. How betting moves a price, step by step (imaginary coin XYZ)

**Every bet is a deal between two people:** one bets up, the other bets down.
The exchange only matches them, like a broker at a property deal. The bets
have their own list of waiting people, separate from the market for real
coins.

**Step 1, a calm day.** The real-coin market last traded at **$100**, and the
bet market looks like this:

| waiting to bet down at | waiting to bet up at |
|---|---|
| $103 | $99 |
| $102 | $98 |
| $101 | $97 |

The bet's last deal was also $100, so both prices agree.

**Step 2, excitement.**
- News arrives ("a big company will use XYZ") and many people want to bet up
  *right now*.
- Betting is easier than buying real coins: you only need a deposit, nothing
  to store, and it's quick.
- They take the $101 offer, then the $102 offer, so the bet's price is now
  **$102**.
- Nobody bought a real coin, so the real price is still **$100**. There's a
  **$2 gap (2%)**.

**Step 3, the rent switches on.**
- The exchange sees the bet $2 above the real price and makes up-bettors pay
  down-bettors.
- Example: 0.1% every 8 hours, which on a $1,000 bet up is **$3 a day**.
- The bigger the gap, the bigger the rent.

**Step 4, a careful trader ("Ravi") closes the gap.**
- Ravi **buys 10 real XYZ coins for about $1,000** and **bets down on 10 XYZ
  at about $102**.
- His buying uses up the cheapest real-coin sellers, so the **real price rises
  to $101**.
- His betting down fills the eager up-bettors, so the **bet price falls to
  $101**.
- The prices meet at **$101**. Ravi's real coins gained $10 and his bet down
  gained $10, so **+$20**, plus rent. From here on his two positions cancel,
  so he carries almost no price risk.

**Step 5, calm again.** The gap is gone, so the rent falls back to its small
normal level.

**The lesson:** the excitement started in the bet market, but through careful
traders like Ravi it **lifted the real coin from $100 to $101**. That's how
betting moves the real price.

**The opposite (panic).** Eager down-bettors push the bet's price *below* the
real price. Down-bettors then pay the rent, and careful traders sell real coins
and bet up until the prices meet.

**The chain reaction (forced closing).**
- Many people bet with thin deposits.
- Say lots of people bet *down* on a small coin and the price rises 5%. Their
  deposits run out and the exchange **closes their bets by force**.
- Closing a bet down means *buying*, which pushes the price up again, so the
  next group runs out, and so on.
- A small coin can jump 20–30% in hours this way (a "short squeeze"). It's
  one reason AIN-style jumps happen, and why the bot uses only 2× and watches
  both jars.

**Your bot is Ravi on Delta, with a twist.**
- Delta's crowd is mostly eager up-bettors, so Delta's bet prices tend to sit
  a bit high and up-bettors pay rent.
- The bot bets down on Delta to collect it.
- Instead of buying the real coin like Ravi (in India that brings crypto tax
  and TDS), it covers the price risk with a cheap **bet up on Pi42**.
- Pi42 follows Binance, where many careful traders keep gaps and rents small.
