# C508 pre-registration: an Indian pot through Groww (≈100 USDT = ₹8,800)
Written 2026-09-29, BEFORE any data for this test was computed.

## The question

The operator asked whether the bot can also trade the Indian market through
Groww, with a separate starting equity of about 100 USDT.

## What is possible, from the rules and costs (checked 29 Sep 2026)

- **API access:**
  - Groww has a trading API (₹499/month plus GST).
  - SEBI's retail algo framework has applied since 1 Apr 2026. Orders must
    come from one registered static IP (the server has one), and each order
    is tagged by the exchange.
  - Personal use under 10 orders a second needs no strategy registration.
- **F&O is out at this size:**
  - One Nifty lot is about ₹15–17 lakh of notional, with about ₹1 lakh+ of
    margin.
  - Option *buying* fits in ₹8,800, but SEBI's own studies found about
    9 in 10 retail F&O traders lose money.
  - No F&O is tested.
- **Groww delivery costs per order:**
  - brokerage ₹20 or 0.1% (minimum ₹5), plus 18% GST;
  - on every sale of each holding, DP charges of about ₹20 plus GST (₹0
    under ₹100);
  - STT 0.1% each side on stocks, but **0.001% on the sale of an ETF**;
  - stamp duty 0.015% on buys; exchange 0.003%.
- **What that means at ₹8,800:** a ₹1,800 stock position costs about 1.9% to
  round-trip. Daily or weekly trading, or 5 small stocks, is uneconomic. Only
  a few ETFs, traded a few times a year, can work.

## The rule tested: I1, Indian ETF trend, long or flat, monthly

This is the spot pot's philosophy (S1, admitted at C501/C502) applied in
India.

**Universe** (liquid NSE ETFs with 10 years of data; Yahoo Finance daily
closes, adjusted where Yahoo provides it):
- NIFTYBEES (Nifty 50);
- JUNIORBEES (Nifty Next 50);
- BANKBEES (Bank Nifty);
- GOLDBEES (gold);
- MON100 (Nasdaq-100).

A day with a move over 40% is treated as a data artefact and its return set
to 0 (stated, not hidden).

**Signal:** the trend score = the mean sign of the 21-, 63-, 126- and 252-day
returns (≈ 1, 3, 6, 12 months). It is read on the last trading day of each
month.

**Weights:**
- max(score, 0) × min(1, 0.012 / 60-day daily sd) / 5;
- the whole pot scaled to a **12% annual volatility** set point by the
  trailing 126-day vol of its own unit returns (past only);
- **gross ≤ 1** (no leverage).
- Traded at the next day's close.
- A holding is changed only if its target moves by more than 30% of the
  target and by at least ₹500. A target under ₹1,000 is not opened.

**Cash:** earns **6% a year** (a liquid fund / overnight rate, deliberately
conservative).

**Costs, modelled per order on a ₹8,800 pot:**
- brokerage max(₹5, min(₹20, 0.1%)) × 1.18;
- on each sale, ₹23.6 of DP charges plus 0.001% STT;
- on each buy, 0.015% stamp duty;
- 0.003% exchange fee both ways;
- 0.05% half-spread both ways.

**Admitted as a paper pot only if** (daily excess return over the 6% cash
rate, 2017-10 → 2026-09):
- Newey-West t ≥ 2.0;
- ≥ 3 of 4 equal time quarters positive;
- holdout 2025-01-01 → 2026-09 mean excess > 0;
- max drawdown ≤ 25%.

**Reported, whatever happens:**
- buy-and-hold Nifty 50 (NIFTYBEES) and a 50/50 Nifty/gold buy-and-hold;
- CAGR, per month, months ≥ +2%, worst month, trades per year and costs;
- the tax note: equity STCG 20%, LTCG 12.5% above ₹1.25 lakh; gold ETFs are
  taxed differently. The CA decides.

If I1 fails, the answer is "not worth it at ₹8,800". Nothing is tuned after
seeing a result.
