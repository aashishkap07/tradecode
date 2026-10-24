# How the bot works, what everything is worth now, and the 2–4% question

3 Oct 2026. You asked for four things:
1. a plain-English explanation of what the bot does;
2. a check of its logic for mistakes and false reasoning, and whether it really adjusts itself;
3. the total equity and net P&L of everything, as if it were live;
4. ways other than trading that a program could earn 2–4% a month.

**Note first: none of your money is in the bot.** Every account below is paper
(`C488_LIVE_OK = False`). "As if live" means: what each paper account would be
worth now if it were real money, at real prices.

---

## 1. What the bot does

Think of the bot as a small fund manager looking after a few separate jars.
Each jar has one job. The bot never mixes them up.

### Jar 1: the main book ($500, Binance futures)

Every day at 05:35 IST (00:05 UTC), it looks at the 20 most-traded coins (each
listed for at least 90 days) and holds a mix of longs and shorts, chosen by
three habits:

| habit | the idea in plain words | analogy |
|---|---|---|
| **trend** | a coin that has been rising over 1–8 weeks tends to keep rising for a while; a falling one tends to keep falling | a rolling ball keeps rolling until something stops it |
| **momentum** | buy the coins beating the market, short the ones lagging it | backing this term's class toppers against the class average, not against zero |
| **carry** | futures have a "funding" fee that one side pays the other every few hours; the bot leans to the side that *receives* it | when everyone wants to rent umbrellas, own the umbrella shop |

Then it decides **how much** of each to hold:
- **Each coin is sized by its own turbulence.** A wild coin gets a small
  position; a calm one gets a bigger one. The turbulence uses each day's
  high, low, open and close, not just the close.
  - *Analogy:* measure how rough the sea was all day, not just at sunset.
- **The whole book has a speed limit:** about 27% swing a year, at most 3×
  leverage. When markets get rough, it shrinks; when calm, it grows.
  - *Analogy:* cruise control that slows down on a bumpy road.
- **It ignores small drifts.** It trades only when a position is more than 30%
  away from its target, which saves fees.
  - *Analogy:* you don't steer for every pebble.
- **A monthly fuse:** if the month's loss on marked equity uses the whole
  monthly budget (20% of equity), it stops for the rest of the month.
- **No stop-loss on single coins.** This is on purpose: round 12 tested stops,
  and they sold at the worst moments in this jumpy market.
  - *Analogy:* a fire alarm that goes off whenever you cook, so you stop
    cooking.

### The other jars (all paper)

| jar | what it does | analogy |
|---|---|---|
| **Savings** | the part of jar 1's cash not needed as margin earns Binance's Flexible Savings rate (6.69%) | the cash in your wallet you don't need today goes into a savings account |
| **BFUSD** (shown, not added) | the *whole* futures wallet earns 7.66%, but turning USDT into BFUSD probably costs 1% TDS once | a better savings account with an entry toll |
| **Spot pot** ($250) | buys real coins (no leverage) when their trend is up, holds cash otherwise; the cash earns Savings | the main book's trend habit, long-only and without borrowing |
| **Carry** ($500) | buys a coin and shorts its futures, so the price moves cancel; it collects the funding | renting out umbrellas you own: you don't care if umbrella prices move, only about the rent |
| **Delta India book** ($500) | the main book's exact plan, on Delta Exchange India's contracts, fees and funding | the same recipe cooked in a different kitchen, to see what the Indian kitchen costs |
| **Cross-venue** ($500) | the same coin, short on Delta India, long on Binance. Prices cancel; Indian traders pay more funding to be long, and that gap is collected | the same flat rents for more in one city than another: rent it out where rent is high, rent one where it is low |

### Experiments (not counted as money)

- **Rule tournament:** 9 variants of the book's rules, scored on the same
  prices every day.
  - *Analogy:* a cooking contest where every cook gets the same ingredients.
- **Intraday shadow:** the old hourly engine, kept on paper to see whether it
  ever earns its costs.

---

## 2. Everything, marked now (12:02 IST, 3 Oct)

The server's ledgers (logs push 11:17 IST), marked at live Binance and Delta
prices. Carry and cross-venue include the funding settled since their 00:10
and 00:30 UTC runs, which the ledgers book at their next run.

| account | started with | now | net P&L |
|---|---|---|---|
| Main book (Binance futures) | $500.00 | $499.48 | −$0.52 (−0.10%) |
| Savings on its idle cash | — | +$0.12 | +$0.12 |
| Spot pot | $250.00 | $249.73 | −$0.27 (−0.11%) |
| **Planned money (these three)** | **$750.00** | **$749.33** | **−$0.67 (−0.09%)** |
| Funding carry | $499.83 | $499.09 | −$0.75 (−0.15%) |
| Same book on Delta India | $500.00 | $499.92 | −$0.08 (−0.02%) |
| Delta vs Binance funding gap | $500.00 | $499.66 | −$0.34 (−0.07%) |
| **Every paper account, as if each were funded** | **$2,249.83** | **$2,248.00** | **−$1.83 (−0.08%)** |

**Where the −$1.83 comes from:** costs. Fees, the book's exit fee and TDS add
up to about **$2.55**:

| account | costs so far |
|---|---|
| carry | $0.95 |
| cross-venue | $0.74 |
| main book (incl. its $0.15 exit fee) | $0.33 |
| spot pot (incl. $0.26 TDS, which is creditable) | $0.32 |
| Delta book | $0.20 |

So before costs, the positions themselves have earned about **+$0.72**. Two or
three days in, that's normal.
- *Analogy:* the entry ticket is paid on day one; the show pays back over
  weeks.
- Carry earns about $0.10 a day of funding at today's rates. That takes
  about 9 days to recover the fees it has paid, and about a week more for
  its exit fees.

**One early sign worth watching:** the cross-venue ledger collected **+$0.30
of funding in its first 6 hours** (2 of a day's 6 settlements).
- That pace is about 5% a month before costs, in line with the 2024–26
  research (3.8–5.8%).
- **But one morning proves nothing.** Two of its ten spreads have already
  narrowed: CROSS from 101% to 65% a year, FARTCOIN from 112% to 95%. The
  research expected this; a coin keeps about 0.71 of its gap week to week.

**What would differ if it were live:**
- Fills: the paper book fills at the bid/ask with the taker fee, which is
  close to reality at $500; at much larger sizes, small coins would cost more.
- Exchange outages and rejected orders.
- Indian tax: 30% on gains with no loss set-off for spot crypto, plus the
  open CA questions on futures and on the two-venue trade (pending #8).

**From now on, the dashboard shows this (C527):**
- a new **"All accounts (as if live)"** panel near the top;
- a **TOTAL** row in the log's 8-minute status block;
- `c527` in the API.

It uses the prices the bot already holds. Carry and cross-venue get the price
move since their daily run, plus the funding settled since then, read once an
hour.

---

## 3. Logic check: mistakes, false reasoning, and where the bot stands

I went through the reasoning behind each part, not just the code.

**No new bug turned up in the ledgers.** Two gaps were found and fixed in C527:
- the new total would have left out up to a day of the cross-venue ledger's
  funding, which is the whole point of that ledger (now read hourly);
- the Savings rate was typed in by hand, though Binance publishes it (now
  read every 6 hours).

These are the reasoning traps that matter for this bot:

| # | the trap | in plain words | where the bot stands |
|---|---|---|---|
| 1 | **Small-sample fallacy** | "2 wins, 1 loss" after 3 days means nothing; a coin toss does that | ✅ The bot doesn't act on its own short record. Telling skill from luck needs **11–24 months** of live record (MinTRL) |
| 2 | **"Every month" vs "on average"** | 2% a month *on average* is not 2% *every* month | ⚠️ The book swings about ±7.7% in a typical month. Even working as researched, **about 4 months in 10 will lose money**. Judge it by the year, not the month |
| 3 | **Backtest optimism (overfitting)** | try enough recipes on old data and one looks brilliant by luck | ✅ Every idea is written down before testing (pre-registration). The search's overfitting score (PBO 0.93) is why expectations were **cut by a third** |
| 4 | **Multiple testing** | 16 research rounds: some "passes" will be luck | ✅ for the strong ones. The cross-venue trade (t 12.5, still positive at 10× costs) is far beyond luck. Hyperliquid (t 3.7, dies at 5× costs) was **not** added. ⚠️ All of it is one 2-year market regime |
| 5 | **Hot hand** | switching to whichever rule is ahead this week | ✅ The tournament **never** switches rules by itself. Changing the traded rule needs evidence over many months |
| 6 | **Gambler's fallacy** | "NEAR fell 14%, it's due to bounce" | ✅ The bot never averages down because a coin "should" bounce. It re-weighs every coin daily on the same rules |
| 7 | **Rear-view mirror** | the speed limit uses *past* turbulence, so it slows down *after* the bump | ⚠️ A known limit. In a crash, coins fall together and diversification vanishes when you need it most. The monthly fuse is the backstop |
| 8 | **"Equal risk" isn't quite equal** | the three habits get equal *own* turbulence, but they move together sometimes | ⚠️ A simplification, not an error. Each habit is scaled by 1 / its own 60-day swing; their correlation is ignored. Today: carry gets more size (0.47×) because it is calmer, trend less (0.23×) |
| 9 | **"Free money" (cross-venue)** | prices cancel, so it looks riskless | ⚠️ Real risks:<br>• one leg can be liquidated in a spike, so it needs margin on **both** venues<br>• small coins can be delisted<br>• the India-only gap could close (regulation, new market makers)<br>• tax across two venues<br>• it can't grow large on small coins |
| 10 | **"Funding is income"** | funding is paid only while the crowd leans one way, and it can flip | ✅ Carry and cross-venue leave when it fades. ⚠️ Carry's fees ($0.95) still exceed its funding ($0.17) |
| 11 | **Double counting** | the Delta book is the *same* strategy as the main book | ✅ That is why the "planned money" total leaves it out. "Every account" assumes each is funded separately |
| 12 | **BFUSD + Savings** | both can't happen to the same wallet | ✅ BFUSD is shown as the alternative, never added |
| 13 | **Hand-typed rates** | Savings (6.69%) and BFUSD (7.66%) were typed in by hand, and Savings' market part moves daily | **Fixed for Savings in C527:** it now reads Binance's public Simple Earn listing every 6 hours (3 Oct: 2.69% market + 4.00% on the first 1,000 USDT, shared with the spot pot's cash). ⚠️ BFUSD has no public source: **update it monthly from the app** |
| 14 | **Which "today"?** | the bot's trading day starts 05:30 IST (00:00 UTC) | ⚠️ Not an error, but a "today" figure on the dashboard is the UTC day |
| 15 | **Paper vs live** | paper fills are kind | ✅ Paper uses bid/ask and taker fees, and the Delta book whole contracts; close enough at this size |

---

## 4. Does the logic really adjust itself? Yes, with clear exceptions

**What adjusts itself, and to what:**

| what | measured against | how often |
|---|---|---|
| each coin's size | its own turbulence (daily high/low/open/close) | daily |
| the book's total size | its own recent turbulence (60 days); at most 3× | daily |
| the three habits' shares | each habit's own turbulence | daily |
| momentum | each coin vs the market, not vs zero | daily |
| which coins | the top 20 by 30-day median volume, re-ranked | daily |
| monthly loss budget | a % of marked equity, not a fixed dollar amount | live |
| Savings rate (C527) | Binance's own floating rate and bonus tier | every 6 hours |
| cash kept for margin (Savings) | margin in use + the month's budget + 5% | every minute |
| spot pot | 20% volatility target, each coin in its own turbulence units | daily |
| cross-venue | the funding gap in %/yr against fixed bars; each leg 10% of its own equity | daily |
| Delta book | its own equity, in whole contracts | at each rebalance |

**Seen live today:**
- The "+GK+XA" tournament rule held **1.31×**, because its calmness reading
  said the market was quiet.
- The cross-venue ledger's spreads are re-measured daily. The bot will close
  CROSS by itself if its gap falls under 10% a year.

**What is fixed on purpose:** the rules themselves (the 1–8 week windows, the
20%/10% bars, the 30% band).
- A rule that re-fits itself to last week's data chases noise. *Analogy:* a
  chef who changes the recipe every night based on yesterday's diners ends up
  with no recipe.
- Rules change only through a written test first, then the tournament.

**What was fixed and shouldn't have been:** the Savings rate. Since C527 it
reads itself from Binance. BFUSD's rate is still typed by hand because Binance
publishes it only inside the app (item 13 above).

---

## 5. Earning 2–4% a month without trading: the research

Current figures, Sep–Oct 2026, for things a program could run:

| avenue | about per month | can code run it? | the catch | verdict |
|---|---|---|---|---|
| Bank FD (SBI 6.8%, small finance banks ~8%) | 0.55–0.67% | no need | none: insured to ₹5 lakh | the safe baseline |
| Binance Savings / BFUSD | 0.56% / 0.64% | yes (already on paper) | platform risk; BFUSD's 1% TDS | already in the bot |
| P2P lending India (LenDenClub) | ~0.7% | partly | defaults; RBI banned "assured returns" in 2024 | FD-like return, more risk |
| ETH staking | ~0.3% + ETH's price | yes (a validator) | price risk, 32 ETH or a pool | no |
| sUSDe (Ethena) / Aave USDT | 0.3–0.4% | yes | smart-contract risk; the yield is funding, so it can drop to zero | below Savings |
| Hyperliquid HLP vault | ~1–2% | deposit only | 5–12% drawdowns, on-chain | a manual option |
| **GPU rental** (an RTX 4090 on Vast.ai etc.) | **~$63–74 net on a ~$2,000 card (3–3.7% of the card)** | yes: a host program | you must buy the card; it loses value; you are paid only while rented (60–85%); prices are falling ($0.12–0.13/h); Indian power costs | **the closest real candidate. But it is a hardware business needing new capital, not a use for your $750, and after the card's depreciation it is nearer 1–2%** |
| Bandwidth sharing (Grass, Honeygain) | a few dollars per device | yes | paid in a volatile token; not a return on capital | pocket money |
| MEV / liquidation bots | ~0 for a newcomer | yes | a speed race against professionals with private infrastructure | no |
| **USDT's Indian premium** (USDT trades 7–10% above the dollar rate in India) | looks like a lot | yes | it requires sending money abroad to buy USDT; the Enforcement Directorate raided exactly these remittance chains in 2026; 1% TDS on every sale | **don't: legal risk** |
| Referral programmes | depends on your audience | — | not a return on capital | — |
| *(trading, but market-neutral)* **Delta vs Binance funding gap** | **3.8–5.8% on 2024–26 data; first morning on pace** | yes, running on paper | the risks in §3 item 9 | **the only candidate in the range; its live paper record started 2 Oct** |

**The honest bottom line:**
- **Safe money pays about 0.5–0.7% a month** today: FD, Savings, BFUSD.
- Anything steadily paying 2–4% a month carries a risk you can't see yet.
  - *Analogy:* if a shop sells ₹100 notes for ₹70, ask what is wrong with
    the notes.
- The realistic plan is a mix:
  - the book, about 1.5–2% a month **on average**, with losing months;
  - plus the cross-venue trade, **if** its live paper record holds for
    several months;
  - plus Savings on idle cash.

Sources:
- Fixed deposits:
  [FD rates 2026 (Business Today)](https://www.businesstoday.in/amp/personal-finance/investment/story/looking-for-the-best-fd-these-banks-are-offering-up-to-8-10-interest-in-july-2026-541857-2026-07-09),
  [small finance bank FD rates (Stable Money)](https://stablemoney.in/fixed-deposit-interest-rates/bn/small-finance-bank-fd-rates).
- P2P lending:
  [LenDenClub factsheet, June 2026](https://www.lendenclub.com/wp-content/uploads/2026/07/LenDenClub-Factsheet-June-2026.pdf),
  [RBI P2P rules (YourStory)](https://ts.yourstory.com/2024/09/p2p-lending-rbi-crackdown-nbfc-lendenclub-bhavin-patel-startup).
- Staking and stablecoin yields:
  [Ethereum staking 2026 (KuCoin)](https://www.kucoin.com/blog/ethereum-staking-in-2026-yield-trends-validator-queue-dynamics-and-mev-impact-exlained?lang=en_US),
  [Ethena sUSDe 2026 (Eco)](https://eco.com/support/en/articles/15254002-ethena-usde-and-susde-2026-delta-neutral-yield).
- GPU rental:
  [RTX 4090 AI rental earnings (Miningboard)](https://miningboard.com/de/rigs/nvidia-rtx-4090/ai-rental),
  [renting a GPU for AI (Miningboard)](https://miningboard.com/guides/rent-gpu-for-ai-earnings).
- Bandwidth sharing:
  [Grass guide (CoinStats)](https://coinstats.app/news/5afe9028d58a2d5655cabe45bef5449b2db358d34377797d8c07a5901c7dde70_What-is-Grass-GRASS-Complete-Guide-for-2025).
- MEV bots:
  [MEV bots and tools 2026 (QuickNode)](https://www.quicknode.com/builders-guide/best/top-8-mev-bots-and-tools).
- India's USDT premium:
  [India's USDT premium tops 8.5% (The Block)](https://theblock.co/post/406502/indias-usdt-premium-tops-8-5-as-crypto-remittance-crackdown-squeezes-stablecoin-supply-report),
  [USDT premium and capital controls (Crowdfund Insider)](https://www.crowdfundinsider.com/?p=288424).
- From earlier rounds (13, 15, 16): Savings, BFUSD, HLP, Aave, basis.
- Measured here: every ledger and price in §2.

---

## 6. C527: what changed in the code

1. **`_c527_total`** adds up every account:
   - the book's marked equity (exit fee included), Savings, spot pot and
     Delta book at their own marks;
   - carry and cross-venue at their daily mark, plus the price move since
     (from prices under 15 minutes old), plus the funding settled since.
   - It reports two totals (planned money; every account). BFUSD is shown,
     not added. The shadow and the tournament are named and left out.
2. **`C527Pending`** reads, once an hour, the funding settled since carry's and
   cross-venue's daily run:
   - one Binance call per settlement hour (all coins at once, cached);
   - one Delta call per pair, so about 11 public calls an hour.
   - It never changes a ledger. When a ledger books the funding, its reading
     is dropped, so nothing is counted twice.
   - Checked against an independent per-coin calculation on today's real data:
     carry +$0.0087, cross-venue +$0.2957, identical.
3. **The Savings rate reads itself** from Binance's public Simple Earn
   listing every 6 hours: the floating market rate, plus the 4% bonus on the
   account's first 1,000 USDT, shared by the Savings ledger's idle cash and
   the spot pot's cash. If it can't be read, the configured 6.69% stands in.
   The Savings panel says which one is in use.
4. **Display:** the dashboard panel "All accounts (as if live)", the log's
   TOTAL row, and `c527` in the API.
5. **Test:** `omega_c527_test.py` (41 checks) loads the server's own ledgers
   (`research/c527_snapshot/`) and marks them at one fixed set of real prices:
   - each row and both totals match an independent calculation;
   - stale prices are refused;
   - the funding windows and call counts are checked;
   - the Savings rate's tier, 6-hour refresh and fallbacks are checked;
   - the page renders without JavaScript errors.
