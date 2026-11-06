# The full re-analysis: can OMEGA make 2–4% a month?

**Date:** 26 Sep 2026
**Work:** C493 (round 5, "breadth") and C494 (the fee test)
**Bot:** unchanged. It is still C492; only one code comment was corrected.

## The short answer

**Yes, historically, with what is already built, but not with anything new.**
Measured on exactly what the bot trades (crypto only, $250, the top 20 coins,
every cost and funding payment included, 2020–2026), the daily
trend + momentum + carry book (C488) made:

| risk dial | average month (compounded) | 12-month stretches that made ≥ 2%/month | 12-month stretches that lost money | worst 12 months | worst single month |
|---|---|---|---|---|---|
| 10% | +1.6% | 35% | 16% | −15% | −10% |
| **15% (current)** | **+2.6%** | **64%** | 16% | −23% | −15% |
| 20% (maximum) | +3.7% | 76% | 17% | −33% | −19% |

- **Plan on less going forward.** Strategies usually lose about a third of
  their backtest strength once traded, so a fair forward estimate is **about
  1.5–3% a month at dial 20%**.
- **About one year in six loses money.** That is the price of this return.
- **4% a month needs a dial of about 25%,** with a historical drawdown near
  50%. That is outside the 0–20% dial, deliberately.

I also tested seven new ideas from finance, physics, chaos theory,
behavioural science and physiology, each fixed in writing before any data was
looked at. **None was good enough to add**; the details are below. The
biggest finding was a correction instead: the book was **not** fading, as the
Atlas had said for a month.

## 1. Futures from the basics (what the bot actually does)

- **A perpetual future** is a bet on a price with no expiry. You can be long
  (gain if it rises) or short (gain if it falls).
- **Leverage and margin.** At 5x, $100 of margin holds a $500 position. Leverage
  does not change the edge; it only scales the gain and the loss.
- **Funding.** Every 1–8 hours, longs pay shorts or shorts pay longs, depending
  on which side is crowded. That is how a perpetual stays near the spot price.
  It is also an edge: the C3 "carry" sleeve takes the side that is paid.
- **Costs.** Bitget charges 0.06% for a market order and 0.02% for a resting
  limit order, and a market order also crosses the spread (about 0.02%). A
  strategy that trades 5 times a day pays about 0.8% a day in costs, which is
  far more than any short-term signal earns. That is why every intraday design
  failed (C489–C491), and why the book trades once a day.
- **Liquidation.** With isolated margin, each position can be wiped out on its
  own. With cross margin, the whole account backs the book. The bot uses cross
  margin, and its stop is the **month guard**: if the month loses more than the
  dial allows, everything is closed until next month.

## 2. The arithmetic of a monthly target

A book's return is roughly **Sharpe × volatility**.
- **Volatility** is a choice: that is the dial.
- **Sharpe** is the quality of the edge, and it is the only thing research can
  improve.

Compounded monthly growth, for a given Sharpe and volatility:

| Sharpe | 13% vol (dial 10) | 20% vol (dial 15) | 27% vol (dial 20) | 40% vol |
|---|---|---|---|---|
| 0.87 | +0.9% | +1.3% | +1.7% | +2.3% |
| 1.00 | +1.0% | +1.5% | +2.0% | +2.7% |
| **1.33** | +1.4% | **+2.1%** | **+2.7%** | +3.8% |
| 1.60 | +1.7% | +2.5% | +3.3% | +4.8% |

So 2–4% a month needs a Sharpe of roughly **1.3–1.6 at dial 15–20%**. The
crypto-only book measured **1.42 over 2020–26 and 1.56 at $250 with 20
coins**. It is in that zone.

**How to raise Sharpe without raising risk: breadth.** Independent edges add
in quadrature: Sharpe ≈ √(sum of each Sharpe²). The book already works this
way: three modest edges (trend 0.6, momentum 0.7, carry 1.1) that barely move
together combine to 1.42. Round 5 went looking for a fourth and fifth.

## 3. Is there hidden knowledge that professionals keep secret?

I found no sign of it, and good reasons it isn't needed to explain what
professionals earn:
- **Professional results are known.** Crypto quant funds averaged about 48% in
  2025 (directional). The best market-neutral funds make about 13–18% a year,
  at Sharpe above 2.
- **Their edge is mostly things a retail account cannot buy:**
  - fees near zero, or rebates for resting orders;
  - servers next to the exchange;
  - order flow from their own clients;
  - dozens of strategies at once.
- **Your target (27–60% a year) is at the top of what those funds achieve.**
- **Published bots and "90% win rate" backtests** almost never survive live
  trading: overfitting, look-ahead bias and costs.

The honest route for a $250 retail account is the one this project follows:
- a few slow, well-documented edges, combined;
- fixed before testing;
- paid for with as few trades as possible.

## 4. Round 5: seven new ideas, from every field

Each was written down with its rule and its expected sign, and pushed to
GitHub **before** any number was computed (`research/c493_preregistration.md`).

- **Data:** 656 crypto perpetuals on Binance, including every delisted one,
  2020–2026.
- **What counts:** real funding, 0.08% per trade.
- **To be admitted, a sleeve needed all of:**
  - a t-statistic ≥ 2.45 (strict, because 7 ideas were tried at once);
  - positive results in at least 3 of 4 quarters;
  - still working since 2024.

| idea | where it comes from | result | meaning |
|---|---|---|---|
| **Short newly listed coins** | Supply: unlocks and airdrop selling. 2025 listings fell a median 82% | +2%/yr overall. Won every year 2022–26, but **lost 41% in the 2021 mania** | A bet on the market mood, not an edge |
| **Prefer calm coins over wild ones** | The "low-volatility anomaly": people overpay for lottery-like coins | **+12%/yr, t 2.23**, 4/4 quarters, still working | The closest miss. Real-looking, but below the strict bar |
| **Fade coins with sudden volume spikes** | Behavioural: attention makes people overpay | −10%/yr | Wrong way round: spikes keep going (momentum again) |
| **Bet against the crowd's positioning** | Binance's long/short account ratios, a signal that is not price | +6%/yr, t 1.5 | Too weak |
| **Follow the biggest accounts** | "Smart money" | **−8%/yr** | Big accounts are not smart money in aggregate |
| **Trend only where the path is clean** | Chaos theory / fractals: a persistent path travels far for its wiggle (a Hurst proxy) | +2.6%/yr over plain trend, t 1.3 | No real improvement |
| **Strengthen whichever strategy is winning** | Physiology's reinforcing loops ("what fires together wires together") | **−15%/yr** against equal weights | The strategies' results reverse after weeks. The loop that works here is the opposite one: keep risk steady (homeostasis), which the book already does |

**Checks that the test itself works:**
- on random data, nothing passes;
- a fake new-listing effect planted in synthetic data was found (t 6.2);
- a planted low-volatility effect was found and admitted (t 12).

So "nothing passed" means the real market did not have these edges strongly
enough. It does not mean the test could not see them.

**Could not be tested honestly:**
- **Token unlock calendars:** the historical data is paid-only (DefiLlama and
  Tokenomist both refused).
- **Stock perpetuals on Bitget:** their list was picked with hindsight (NVDA,
  PLTR, MSTR…), so any backtest on it is flattered by survivorship.

## 5. The big correction: the book was not fading

Since C488 the Atlas said the book's recent strength had faded:
- Sharpe 0.87 over 24 months;
- "1.5–2% a month realistic".

**Those figures came from a research universe that included Binance's 2026
stock and commodity perpetuals** (TSLA, NVDA, oil…). The bot never trades
those (it skips Bitget's `isRwa` contracts).

On what the bot actually trades:
- **the last 24 months:** Sharpe 1.17, +2.2% a month;
- **the last 12 months:** Sharpe 1.69, +3.3% a month;
- **August 2026:** +5.2%, not a loss.

The data reproduces the old numbers exactly when the stocks are put back in,
so this is a correction, not a new model. It is now Standing Rule 54: *measure
the universe that actually trades*.

## 6. Fees: can a patient rebalance save money? (C494)

At $250 the book pays about **4.6% a year** in fees and spread at dial 15%,
because it rebalances with market orders.

**The test:** every one of its 7,663 real rebalance trades (Sep 2024 – Aug
2026) was replayed on 1-minute prices. The patient version posts a limit
order, waits 30 minutes, then pays up if it is still unfilled.

**The result:**
- 93% filled;
- the average cost fell from 0.080% to 0.049% per trade;
- that is about **+1.1% a year** (t 2.65).

**Not adopted: it missed the bar fixed in advance** (a saving of at least
0.020% per trade; it saved 0.018%). It will be re-tested on fresh data in
December (pending #11). The orders that didn't fill show the catch: the price
had already run 0.77% away.

## 7. What I recommend

1. **Deploy C492 now, in paper.** It is safe: C490's carry ledger and C492's
   live plumbing, which does nothing in paper. This way the 29 Sep check
   covers everything.
2. **Keep dial 15% during the paper check.** Paper is checking the machinery,
   not the edge.
3. **Going live** (after #1 passes and #3 security is done):
   - start at **dial 10%**;
   - after a month in which live tracks paper, move to **15%**;
   - consider **20%** only after about three months.

   At 20% you are signing up for historically about +3.7% a month, a worst 12
   months of −33% and a worst month of −19%.
4. **Tax** (your CA should confirm): under the conservative s.115BBH reading,
   30% of each gain goes to tax with no loss offset. After tax, dial 20% is
   closer to +2.5% a month than +3.7%.

## 8. Deploy (Termius: you're already on the server)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 120
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C4|engine:|C488 REBALANCE|C489 shadow|C490 carry|LIVE|Traceback"
```

**What you should see:**
- `OMEGA C492`;
- a `C489 shadow hour …` line;
- `C490 carry (paper ledger) …`;
- **no** `LIVE` lines, and **no** `Traceback`.

The book and positions are kept; this is a normal restart, not a fresh start.

## Sources

- [Cryptocurrency as an Investable Asset Class (arXiv 2510.14435)](https://arxiv.org/pdf/2510.14435): carry Sharpe falling from 6.45 to negative by 2025.
- [Nearly 9 in 10 new crypto listings since 2025 are underwater](https://cryptorank.io/news/feed/e1b0f-new-crypto-listings-losses-2025-report) and [Animoca Research on 2024 listings](https://cryptorank.io/news/feed/dacb1-tokens-display-up-to-negative-70-median-returns-after-cex-listing-animoca-research).
- [The 72-Hour Shock: 52 token unlocks on Binance (SSRN)](https://papers.ssrn.com/sol3/Delivery.cfm/6632838.pdf?abstractid=6632838&mirid=1) and [Do token unlocks crash prices?](https://insights.unlocks.app/do-token-unlocks-crash-prices/).
- [Revisiting the low-volatility anomaly in cryptocurrency markets](https://www.sciencedirect.com/science/article/abs/pii/S1544612326003818) and [Betting Against Beta (Frazzini & Pedersen)](https://www.nber.org/system/files/working_papers/w16601/w16601.pdf).
- [Cryptocurrency factor momentum (Quantitative Finance)](https://www.tandfonline.com/doi/abs/10.1080/14697688.2023.2269999).
- [Anatomy of cryptocurrency perpetual futures returns](https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/).
- [Binance top-trader long/short ratio (API docs)](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Top-Long-Short-Account-Ratio).
- [Copula-based trading of cointegrated crypto pairs](https://link.springer.com/article/10.1186/s40854-024-00702-7): daily pairs trading is weak after costs.
- [Crypto hedge fund performance, 2025 review](https://cryptofundresearch.com/crypto-hedge-fund-performance/) and [Crypto hedge funds trail bitcoin in 2024](https://www.hedgeweek.com/bitcoin-surges-ahead-of-crypto-in-2024/).
- [Trend following performance report, Aug 2025](https://www.toptradersunplugged.com/trend-following-performance-report-august-2025/).
- [Bitget's overview of TradFi perpetual futures](https://www.bitget.com/support/articles/12560603894212).
- [Backtesting AI crypto strategies: overfitting and look-ahead](https://www.blockchain-council.org/cryptocurrency/backtesting-ai-crypto-trading-strategies-avoiding-overfitting-lookahead-bias-data-leakage/).
