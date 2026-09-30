# Every way to 2–4% a month at 80%: a fresh, exhaustive look (1 Oct 2026)

You asked for a look at everything under the sun: Binance, other platforms,
and ways other than crypto. For each avenue the method was the same: the
arithmetic first, then published data, then our own tests on real data.

## 0. First, your C517 check: it passed

- `OMEGA C517` on Bitget, as expected.
- **Crypto-only plan:**
  - 11 positions at $500: BTC, BNB, 1000PEPE, XRP, SUI, DOGE, NEAR, TAO,
    ARB, SOL, HYPE;
  - gross 0.65×;
  - LINK too small for its $20 minimum.
- **The 212 missing contracts are all Binance "TRADIFI_PERPETUAL"** (Apple,
  AMD, oil, even ANTHROPIC), plus 130 contracts being delisted. All are now
  excluded, as they should be.
- **Binance's own tags:** the research's non-crypto names that Binance
  lists as ordinary perpetuals (such as the gold token XAUT) carry the tag
  "RWA"; ALL, BTCDOM and DEFI are indices. All of them are excluded.
- **The switch to Binance paper at $500 is ready.** It waits only for paper
  check #3 (06:45 IST) to confirm this morning's Bitget rebalance.

---

## 1. The short answer

1. **"80% of *months* above +2%" is not available anywhere.** It would need
   a Sharpe of about 4–8, which no known strategy delivers, in crypto or
   anywhere else.
2. **"80% of *years* averaging +2%/month" needs a Sharpe of about 2 at
   25–35% volatility.** Before tax, the book's backtest is exactly there
   (Sharpe 1.87, 81%). With the usual allowance that real results trail
   backtests, it is 60%.
3. **For you, India's tax matters more than any strategy tweak.**
   - Under a strict reading of the 30% crypto tax (each winning position
     taxed, losing ones ignored), the book earns **about 0% a year after
     tax**.
   - Taxed on its net yearly profit, it keeps **about +43% a year**.
   - **A chartered accountant's written answer decides which venue we go
     live on.**
4. **One new, easy improvement: BFUSD on Binance** earns 7.66–9.51% on the
   whole futures wallet while it trades. That is about **+0.3–0.4% a
   month** on top of the Savings approach.
5. **Nothing else found beats what we have:**
   - selling volatility **failed** its pre-registered test;
   - Indian stocks, gold and deposits pay 0.5–1.3%/month;
   - equity F&O and offshore forex are traps, or illegal.

---

## 2. What the target actually demands

**Chance that a year averages ≥ 2%/month** (normal returns):

| volatility ↓ / Sharpe → | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 |
|---|---|---|---|---|---|
| 15% | 25% | 44% | 63% | 80% | 91% |
| 25% | 47% | 66% | **82%** | 92% | 97% |
| 35% | 56% | **74%** | 87% | 95% | 98% |

**Chance that a *single month* is ≥ +2%:** at most 60–75%, even at a Sharpe of
3. So 80% of months is out of reach at any realistic Sharpe.

**How good is a Sharpe of 2?** The best-known funds in the world run at
0.7–1.5 over long periods. The crypto book's 1.87 backtest is already at the
top end. That is possible only because crypto is younger and less efficient,
and a $500 account can use edges too small for big funds.

---

## 3. Where our book stands (Binance, $500, dial 20%, idle cash at 6.8%)

The backtest is 2020–26, pre-tax: **+4.24%/month, Sharpe 1.87 at 29%
volatility.**

| chance of averaging ≥ 2%/month over… | 1 year | 2 years | 3 years |
|---|---|---|---|
| the backtest as it stands | **81%** | 89% | 93% |
| realistic (⅓ haircut) | 60% | 64% | 67% |
| after tax on net profit (reading A) | 72% | 79% | 83% |
| after tax A, realistic | 48% | 47% | 46% |
| after the strict crypto tax (reading B) | ~0 | ~0 | ~0 |

`research/c518_target_math.txt`.

**Judged over 2–3 years, the odds rise** when the expected return beats the
target: 81% becomes 89% and then 93% before the haircut. That is a fairer way
to judge any strategy than a single year.

---

## 4. The biggest finding: India's crypto tax

The book's 3,150 positions of 2020–26 were followed one by one, and each year
was taxed at 31.2% (30% + cess) two ways (`research/c518_tax_india.txt`):

| year | before tax | **A:** tax on net profit, losses offset | **B:** s.115BBH strict: each winning position taxed, losses ignored |
|---|---|---|---|
| 2020 | +46.9% | +34.7% | +17.4% |
| 2021 | +75.4% | +59.7% | +16.7% |
| 2022 | −27.8% | −27.8% | **−87.3%** |
| 2023 | +96.2% | +76.0% | +26.1% |
| 2024 | +82.9% | +60.7% | +11.5% |
| 2025 | +77.4% | +62.1% | +11.2% |
| 2026 (to Aug) | +55.6% | +35.7% | +7.7% |
| **average** | **+58%** | **+43%** | **+0.5%** |

**Why B is so destructive:**
- The book wins by making many trades: 45% of positions win, and the gains
  add up to **4×** its net profit.
- Taxing every gain at 31.2% while ignoring every loss takes **124% of the
  profit**.
- In a losing year like 2022 you would still owe tax on all the winners.

**Which applies?**
- The strict reading is the conservative professional view for crypto
  settled in crypto, like Binance's USDT futures: "each settlement is a VDA
  transaction; Section 115BBH clearly applies". Losses on one VDA "cannot
  offset gains on another" under s.115BBH(2)(b).
- **INR-settled** crypto futures on Indian platforms are argued by some to
  be **business income**, taxed on net profit (reading A). That view is
  "aggressive" and not settled by the CBDT.

**Ask a CA these four questions, in writing:**
1. My bot trades USDT-settled perpetual futures on Binance: about 3,000
   positions a year, 45% profitable. Is the profit taxed under s.115BBH?
2. If so, can losses on some positions offset gains on others within the
   same year?
3. Would INR-settled crypto futures (Delta Exchange India, Pi42) be taxed
   as business income on net profit instead?
4. Does TDS (s.194S) apply to either?

**The answer picks the live venue:**
- **If Binance's futures are taxed on net profit (A):** live on Binance.
- **If Binance is B but INR-settled futures are A:** live on **Delta
  Exchange India** (below).
- **If both are B:** this book should not trade live from India. A slower,
  low-turnover strategy (few, long-held positions) would be the only kind
  worth taxing that way.

---

## 5. Every avenue, checked

### On Binance

| avenue | what it pays | evidence | verdict |
|---|---|---|---|
| **The book** (trend + momentum + carry) | +4.2%/mo backtest, Sharpe 1.87 | 6½ years, 12 research rounds, forward tournament | **keep**: the core |
| **BFUSD as futures margin** | **7.66% base / 9.51% boosted** on the *whole* futures wallet, while it trades | Binance's BFUSD page (Sep 2026); 29–47% at launch, falling with funding rates | **adopt when live**. About +0.3–0.4%/mo over USDT Savings (6.8% on idle cash only). Risks: Binance's delta-neutral backing, the "RWA/stable" wrapper, and its tax treatment (CA) |
| USDT Flexible Savings | 6.8% on idle cash | your app | have it; superseded by BFUSD |
| **BNB airdrops** (HODLer, Launchpool, Megadrop), hedged | +19.7% extra over 15 months (2024–Q1 2025) on BNB in Simple Earn | published analyses | promising as a **small, separate experiment**: BNB in Simple Earn plus a BNB perp short to cancel the price. Past yield ≠ future, and airdrops are taxed as income. Not modelled: no reliable per-event data |
| Funding carry (spot vs perp) | about 11%/yr gross at Bitget's default funding | C490: t 2.78, but **lost in 2025 and 2026** as it got crowded | stays a paper ledger |
| **Selling volatility** (options / variance) | — | **round 13 (below): fails** | no |
| Options writing | — | Binance allows it only at VIP 1 or $100,000 of assets | not available to you |
| Dual Investment, grid bots, copy trading | high "win rates" | they sell the same crash risk as short volatility, which failed after costs | no |
| Spot pot on Binance | +2.6%/mo backtest | **1% TDS on each sale** for Indian users | stays paper |
| Market making, arbitrage | — | need VIP rebates, colocation and big capital | not retail |

### Other platforms

| platform | status | fit |
|---|---|---|
| **Delta Exchange India** | FIU-registered, INR in and out, **221 perpetuals** (live API checked), maker 0.02% / taker 0.05% + 18% GST, API at `api.india.delta.exchange` | **the alternative if the tax answer favours INR settlement.** Contracts are lumpy (BTC $84, BNB $77, SOL $117 each), so **≥ $1,000 (₹85k)** is needed. Liquidity is thin outside BTC/ETH/SOL (XRP $25M/day, DOGE $11M), which is fine at this size. Its list mixes in stock tokens (AAPLX, NVDAX), which the crypto-only filter handles |
| Pi42 | INR-margined perpetuals, "exempt from the 1% TDS" | worth comparing with Delta if the CA favours INR |
| Bitget | not FIU-registered; no new Indian users since Feb 2026 | paper only |

### Outside crypto (India)

| avenue | long-run return | risk | verdict |
|---|---|---|---|
| Nifty200 Momentum 30 | 16.3%/yr (10 y) ≈ 1.3%/mo | vol 20%, worst drawdown 68% | good long-term holding, not 2%/mo |
| Nifty 50 + gold 50/50 | ~15.5%/yr ≈ 1.2%/mo (C508) | DD ~20% | a by-hand holding, no bot needed |
| Equity F&O | **93% of individuals lost** FY22–24, ~₹2 lakh each (SEBI) | a Nifty lot ≈ ₹15–18 lakh | no |
| Offshore forex | illegal for residents under FEMA (RBI's alert list) | penalties | no |
| FDs, bonds, arbitrage funds | 6–7.5%/yr ≈ 0.5–0.6%/mo | low | a floor, not the target |

---

## 6. Round 13: selling crypto volatility (pre-registered, failed)

- **The test** (`research/c518_preregistration.md`, pushed before the data):
  - a ladder of short 30-day variance swaps on BTC and ETH;
  - the strike is Deribit's DVOL less 3 volatility points;
  - it is scaled to 20% volatility;
  - 2021-06 → 2026-08, against the book on the same days.

| stream | %/month | Sharpe | 2025–26 | NW t | blend with the book: P(≥2%/mo, realistic) | verdict |
|---|---|---|---|---|---|---|
| BTC | +0.82 | 1.09 | **−3.9%/yr** | 2.01 | 53% (book alone 54%) | fails (holdout, blend) |
| ETH | −0.26 | −0.17 | −25%/yr | −0.32 | 31% | fails |
| BTC+ETH | +0.24 | 0.25 | −31%/yr | 0.48 | 40% | fails |

- Options are usually priced for more turbulence than arrives, but the gap
  is **smaller than the cost of trading it**. It has been negative since
  2025.
- It did tend to earn in the book's worst months (+2.3% for BTC), which is
  the diversification hoped for. Not enough to matter.
- At a cost of 1.5 points instead of 3, BTC+ETH is +1.1%/month (t 1.29).
  At 5 points it loses.

`research/c518_results.txt`.

---

## 7. What to do

1. **Today:** after paper check #3, switch the paper book to Binance at
   $500 (the commands are in `reports/2026-09-30_c516_binance_phase1.md`).
   Paper trading on Binance prices is useful whichever venue goes live: the
   prices are the same markets.
2. **Before any live money: the CA's written answer** to the four questions
   in section 4. It is worth more than any research round left.
3. **Then the live venue:**
   - **Binance (answer A):** phase 2 on Binance, with **BFUSD as margin** and
     BNB fee payment.
   - **Delta Exchange India (answer B for Binance, A for INR-settled):** a
     Delta port instead; I can build it (its API is open), at ≥ $1,000
     capital.
4. **Judge the result over 2–3 years, not month by month.** A good
   strategy still has losing months: the book lost in about a third of
   months in the backtest.
5. **Optional, small:** try the BNB airdrop idea by hand with a little BNB
   in Simple Earn for 2–3 months, to see what it really pays you after tax.

**What will not get us to "80% of months":** anything. The only honest
routes to a higher chance are:
- a longer horizon;
- a better after-tax structure;
- the forward tournament proving one of the refinements (N2, N3, K4,
  range volatility).

**Sources:**
- Binance BFUSD: [Binance](https://www.binance.com/en/futures/bfusd),
  [The Block](https://www.theblock.co/post/328216/binance-bfusd-launch-apy);
- BNB rewards: [Blockchain.news](https://blockchain.news/news/bnb-holders-177-percent-roi-binance-rewards-launchpool-airdrops);
- Binance options writing: [Binance announcement](https://www.binance.com/en/support/announcement/binance-options-expands-options-writing-access-eligibility-23b9d38c76804aa7bf3786e0188c5c44);
- Delta Exchange India: [Delta API docs](https://docs.delta.exchange/),
  [Plisio](https://plisio.net/profiles/delta-exchange-india);
- Pi42: [Pi42 blog](https://pi42.com/blog/7-best-crypto-futures-trading-platform-in-india/);
- Crypto tax: [TaxBuddy](https://www.taxbuddy.com/blog/section-115bbh-crypto-tax),
  [Mudrex](https://mudrex.com/learn/crypto-tax-on-futures-trading-india/),
  [CoinSwitch](https://coinswitch.co/switch/crypto-futures-derivatives/crypto-futures-options-tax/);
- SEBI F&O study: [AIBI (SEBI release)](https://aibi.org.in/Sebipr/Updated_SEBI_Study_Reveals_93_percentage_of_Individual_Traders_Incurred_Losses_in_Equity_F&O_between_FY22_and_FY24.pdf);
- RBI forex alert list: [Business Standard](https://www.business-standard.com/amp/finance/personal-finance/rbi-expands-alert-list-names-13-unauthorised-forex-trading-platforms-124102300648_1.html);
- Nifty200 Momentum 30: [NSE Indices whitepaper](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/momentum-strategy-whitepaper_2026.pdf);
- the volatility premium: [Athenum](https://www.athenum.xyz/blog/realized-vs-implied-volatility/);
- DVOL: Deribit public API.
