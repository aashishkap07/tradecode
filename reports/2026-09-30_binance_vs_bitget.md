# Binance or Bitget, from India (30 Sep 2026)

**You asked:** Bitget's links don't open in India. You also have a Binance
account. Would Binance be better, with the bot changed to match?

**Short answer:**
- **For real money, yes, Binance is the better home.** It is legally
  registered in India; Bitget is not, and stopped taking new Indian users in
  February 2026.
- **But at $250 it costs about 0.4% a month** of the tested return, because
  Binance won't take small orders in BTC and a few other big coins.
- At $500 the two are about equal; at $1,000 Binance is slightly ahead.
- (Corrected the same day with the minimums your server read live: BTC is
  $50, not the $100 in Binance's 2023 announcement.)
- **Paper trading can stay on Bitget**, since its public prices still reach
  your server. Moving the bot is a real build, in two phases, after two
  checks only you can run.

---

## 1. Legal and access

| | Binance | Bitget |
|---|---|---|
| **India status** | **Registered with FIU-IND** (the anti-money-laundering regulator) in 2024, after an ₹18.82 crore penalty; operating legally ([Business Standard](https://www.business-standard.com/markets/news/binance-set-to-resume-operations-in-india-with-fiu-ind-registration-124081500764_1.html), [OpenRate](https://openrate.live/blog/is-binance-legal-india-2026)) | **Not registered.** It stopped onboarding new Indian users on 6 Feb 2026; existing accounts can still trade and withdraw ([crypto.news](https://crypto.news/bitget-eyes-indian-fiu-registration-following-binance/), Bitget's own FAQ "Temporary Restriction of Services in India") |
| **Website from India** | works | blocked (as you found) |
| **What it means for live money** | trades are reported to the Indian authorities, so declare everything | an unregistered venue can be cut off further at any time, with your money on it |

**Tax:**
- **1% TDS** applies to buying and selling actual coins (spot), and Binance
  deducts it for Indian users.
- It is generally **not applied to futures**, which is why most Indian
  crypto volume has moved to futures (market reports; the CA confirms). On
  Binance's spot deductions, see
  [Binance Square](https://www.binance.com/en/square/post/23139072773857).
- So on Binance the futures book has no TDS drag. The **spot pot** (daily
  spot rebalancing) would lose 1% on every sale, so it should stay paper.
- The 30% question (s.115BBH) is unchanged. **Ask the CA** (Atlas #8).

---

## 2. Costs and order sizes, on real figures

| | Binance USDⓈ-M | Bitget USDT-M |
|---|---|---|
| taker fee (the book uses market orders) | **0.05%**; **0.045%** paying in BNB ([Binance FAQ](https://www.binance.com/en/support/faq/detail/360033544231)) | 0.06% |
| maker fee | 0.02% | 0.02% |
| smallest order | **read live on your server (30 Sep 12:58 IST): BTC $50, ETH $20, LINK $20, SOL $5, 1000PEPE $5**. LTC, BCH and ETC are $20 per [Binance's 2023 notice](https://www.binance.com/en/support/announcement/updates-on-minimum-notional-value-for-btcusdt-and-ethusdt-perpetual-contracts-2023-11-02-e4384cba297a4bd2a154be644d5d76f9), not yet re-read; the rest $5 | about $5, with coin steps (ETH 0.01 ≈ $27) |
| liquidity | the deepest in crypto | good for the top 20 |
| sub-accounts | any verified user with 2FA, up to 5 ([Binance FAQ](https://www.binance.com/en/support/faq/binance-sub-account-functions-and-frequently-asked-questions-360020632811)) | yes |

**What that does to the book** (`research/c515_venue_cost.py`):
- the same N2+N3 book at dial 20%;
- the same 2020–26 **Binance** price history the strategy was built on;
- costed each way.

| equity | Bitget | Binance | Binance + BNB fees | why |
|---|---|---|---|---|
| **$250** | **+4.01%/mo** (Sharpe 1.81, DD 38%) | +3.63%/mo (1.69, 36%) | +3.66%/mo | BTC's $50 minimum removes 89% of the days the book wants BTC; 9.6 coins held vs 11.2 |
| $500 | +3.96%/mo | +3.90%/mo | +3.94%/mo | about equal |
| **$1,000** | +3.95%/mo | **+4.02%/mo** (1.75, 41%) | **+4.06%/mo** | minimums matter less; lower fees win |

These are research figures before the usual ⅓ real-life haircut. They
compare the two venues on equal terms.

---

## 3. What moving the bot involves

Almost every data feed and the live order path are Bitget-specific today. A
switch is two phases:

| phase | what changes | risk |
|---|---|---|
| **1. Paper on Binance** | Replace the data feeds: the book's daily candles, funding, prices and contract rules; carry; the spot pot; the Savings rate. Also 1000-unit contracts such as PEPE, which Binance quotes per 1,000 coins. C512's check that a day is final gets a Binance version. **Bonus:** Binance's candles include taker-buy volume for every coin, so the intraday shadow's full model finally has its data. | none, it is paper |
| **2. Live on Binance** | The order path, equivalent to C492: one-way mode, cross margin, leverage, orders, the position and balance sync every 60 s, and funding from Binance's income history. `C488_LIVE_OK` stays False until you ask. | the usual live checklist |

**One limit on my side:** Binance's trading API refuses my sandbox's location
(HTTP 451). Its public archive works, so the history can be tested here. But
the live endpoints have to be proven from **your server**.

---

## 4. Two checks before any building

**Done 30 Sep 12:58 IST: your server gets `200` from Binance, and the
minimums above are its live reading.** Check 2 (the app) is below, as it was
asked.

**1. Can your server reach Binance's futures API?** In Termius:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://fapi.binance.com/fapi/v1/time
curl -s https://fapi.binance.com/fapi/v1/exchangeInfo | python3 -c "import json,sys;d=json.load(sys.stdin);print({s['symbol']:[f['notional'] for f in s['filters'] if f['filterType']=='MIN_NOTIONAL'][0] for s in d['symbols'] if s['symbol'] in ('BTCUSDT','ETHUSDT','SOLUSDT','LINKUSDT','1000PEPEUSDT')})"
```

- `200`, then a list of minimums: good.
- `451` or `403`: Binance blocks the server's country. The bot would need a
  server in an allowed region.

**2. In the Binance app:**
- Is **Futures → USDⓈ-M** open for you (the futures quiz done)?
- Is 2FA on, so a sub-account can be made later?

**Then the decision is yours:**
- which venue for real money;
- and whether to start it with $250, or with $500–1,000 so the book can
  hold BTC.

---

## 5. The app checks, step by step (added 30 Sep, after check 1 passed)

These paths are from Binance's own help pages. App menu names can shift a
little between versions. If a name differs, the search bar at the top of
the Home screen finds each item by name.

**A. Make sure you are in Binance Pro.** Futures is not shown in Binance
Lite.
1. Open the app and tap your **profile icon** (top-left).
2. At the top of that screen is a **Lite / Pro** switch. Choose **Pro**.

**B. Is USDⓈ-M futures open for you?**
1. Tap **Futures** in the bottom bar.
2. At the top, choose the **USDⓈ-M** tab (next to COIN-M).
3. **Already open:** you see a chart and an order form (Buy/Long,
   Sell/Short, "Cross", a leverage like "20x") on a pair such as BTCUSDT
   Perpetual. Nothing more to do.
4. **Not yet open:** you see **"Open Now"** (or "Open Futures Account"). Tap
   it and take the **futures quiz**; all answers must be right, and you can
   retry. There may also be a short **questionnaire** about your experience.
   Finish both.
5. **Blocked for your region:** a message says futures are not available.
   Tell me, because that decides the move.
6. **Don't** change the position mode, the margin mode or the leverage
   there. The bot will set its own through the API when it goes live.

**C. Is 2FA on?**
1. Profile icon → tap your **profile** section at the top → **Security**.
2. Look at **Authenticator App** (Binance or Google Authenticator) and
   **Passkeys**. "On", or a green tick, means enabled.
3. If the Authenticator App is off: tap it → **Enable** → copy the setup key
   → add it in Google Authenticator (**+** → "Enter a setup key") → type the
   6-digit code back into Binance.
4. An authenticator app is safer than SMS. **Keep the setup key written
   down offline**: it is your only way back in if you lose the phone.

**D. Identity verification**: the same profile screen shows "Verified"
next to your name. Sub-accounts and API keys need it.

**Not now:** creating the sub-account and its API key. That comes in phase 2
(live). It is easiest on the website: Profile → Sub Accounts, then API
Management. Nothing to create yet.
