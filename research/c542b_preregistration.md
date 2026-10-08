# Round 22b: Mudrex, CoinSwitch and every other Indian venue, re-checked (pre-registered 9 Oct 2026)

**The operator (9 Oct):** "what about testing mudrex and coinswitch and any other exchange you might have missed ? if
the data is behind a key , i can create an api key for you to test ..."

These rules are pushed before any pair result exists. The census facts below come before the test; no pair or
return figure has been computed.

## What was found before the test (census)

**Mudrex: its futures are Bybit's order book.** Evidence is in `research/c542b_census/`.
- Mudrex's public last-price candles on 7 Oct 06:00-09:00 UTC were compared with Bybit's trades that day
  (`public.bybit.com/trading/`):
  - LINK: **181 of 181 minute closes are identical, and the volume ratio is 1.000**;
  - AVAX: the same.
  - Against Binance only 30 and 12 of 181 match; against OKX only 10 and 15.
- Mudrex's mark price matches none of Binance, OKX, Bitget or Gate. Bybit's live API is blocked from this
  sandbox (a country block), so it could not be compared here.
- The rent: `funding_fee_perc` is in `GET /fapi/v1/futures`, which needs a key.
  - Prior: Mudrex's rent = Bybit's rent.
- Coins: 468 (found through the public candles), **180 of them also on Delta**.
- Fee: 0.05% + 18% GST (INR margin), per Mudrex's fee page.
- Tax: futures carry no TDS on Mudrex's fee page ("taxation for INR and USDT futures remains unchanged"). One of
  its own FAQs says s.115BBH applies. So the reading is **uncertain until a CA rules**, as it is for CoinDCX.

**CoinSwitch PRO futures: very likely Bybit too.**
- Its site calls it an aggregator that trades "on third-party exchanges".
- Its API's futures exchange code is `EXCHANGE_2`.
- Its ticker fields are Bybit v5's: index, mark, open interest, `funding_rate`, `next_funding_timestamp`.
- Its HFT API lives under `/v5` and answers with Bybit's `retCode`/`retMsg` envelope.
- Its instrument fees (0.065% / 0.024%) are Bybit's 0.055% / 0.02% plus 18% GST.
- Every endpoint, market data included, needs a signed key (Ed25519). It has INR-settled accounts (INR-margined
  contracts).

**Why Bybit matters:**
- Bybit sets its own rent. It does not copy Binance's.
- So a Bybit-copy venue opens two gaps nobody has tested:
  - **Delta vs Bybit:** Delta + Mudrex, or Delta + CoinSwitch;
  - **Binance vs Bybit:** CoinDCX + Mudrex, or CoinDCX + CoinSwitch. Both of these are rupee venues, with no
    Delta in the pair.

**Every other venue looked at:**

| venue | status |
|---|---|
| WazirX | futures since May 2026 (INR); no API |
| Cosmic | no API found |
| SunCrypto | no futures venue found |
| Giottus | perpetuals since Aug 2025; no API found |
| Bitbns | its futures API was last documented in 2022 |
| KoinBX | a futures programme was announced; the API is spot only |
| Bybit, KuCoin, Binance (offshore, FIU-registered) | USDT accounts, not rupee legs. Bybit's rates are covered through Mudrex or CoinSwitch with rupee margin. |

## Step 1: the source test (live, on the server, with the operator's keys)

`research/c542b_server.py`, run once.
- **At one moment** it reads:
  - Mudrex's `funding_fee_perc` for every asset (key);
  - CoinSwitch's `funding_rate` for every pair on every futures exchange code it lists (key);
  - Bybit's tickers `fundingRate` (the predicted rate) and its last settled rate;
  - Binance's `premiumIndex` `lastFundingRate`.
- **"Copies X"** = at least **80%** of the common coins are within **0.002%** of X's rate (the same test as gate G2).
  The predicted and the last settled Bybit rate are both tried, and the better one counts.
- A venue that copies neither Bybit nor Binance has its own rates and no public history. It stays out of the pair
  test, as Mudrex and CoinSwitch did in Round 22.
- **Without a key:**
  - Mudrex is tested on the census prior (its book is Bybit's), and that is labelled as unconfirmed;
  - CoinSwitch is not tested.

## Step 2: the pairs (for a venue that copies Bybit)

**Data:**
- Bybit's funding history and daily closes, Oct 2024 -> Sep 2026 (Round 22's window), fetched on the server from
  Bybit's public API and pushed to the logs branch (`logs/c542b_bybit.json.gz`).
- Bybit's history stands in for the venue's, as Binance's did for CoinDCX.
- Daily rent = the sum of the day's settlements, with the 00:00 settlement counted in the day before (Round 22's
  `shift00`).

**Engine:** Round 22's `legs`/`run` (`research/c542_pairs.py`), unchanged.
- "ALL harder": midnight timing, GST on rent paid, $1,000, the 65% even-out.
- 10 pairs × 10% a leg. Costs ×5 is the gate; costs ×1 is reported.

| | first leg | second leg | coins | cost a side (second leg) |
|---|---|---|---|---|
| **C** | Delta | CoinDCX (Binance's rent) | Round 22's | 0.05% × 1.18 + 0.02% (reference, +3.55% T1) |
| **M** | Delta | Mudrex (Bybit's rent) | Delta ≥ $100k a day ∩ Mudrex's list | 0.05% × 1.18 + 0.02% |
| **S** | Delta | CoinSwitch (Bybit's rent) | Delta ≥ $100k a day ∩ CoinSwitch's list | 0.055% × 1.18 + 0.02% |
| **CM** | CoinDCX (Binance's rent and closes) | Mudrex (Bybit's) | CoinDCX's rupee list ∩ Mudrex's, Bybit turnover ≥ $1M a day | 0.05% × 1.18 + 0.02% each |
| **CS** | CoinDCX | CoinSwitch | CoinDCX's rupee list ∩ CoinSwitch's, Bybit turnover ≥ $1M a day | CoinDCX's / CoinSwitch's |

- **For CM and CS**, the first leg is sized in fractions, with no whole contracts. The wobble floors are $0.5M and
  $2M of Bybit turnover. For M and S they stay at $75k and $150k of Delta turnover.
- **A coin must move with its twin:** a correlation of at least 0.9 between the two legs' daily returns.
- **Mudrex's and CoinSwitch's coin lists:**
  - from their keyed listings when a key is saved;
  - otherwise Mudrex's comes from the public-candle census (468 coins), and CoinSwitch is not run.

**Tax (both readings reported):**
- **M and S:** as in Round 22. T1 means both legs are business income. T2 means the second leg is a VDA.
- **CM and CS:** T1 is the same. Under T2, **both** legs are VDAs (each closed position's leg gain taxed, losses
  ignored).

**Bars:** Round 22 Part A's, unchanged, at costs ×5.
- Average month ≥ +1.5%.
- No month below −4%.
- The poorer account ≥ 40%.
- HAC t ≥ 2.
- Both years positive.
- The list wobble holds (the top-5 coins removed in turn, and both turnover floors).

**Engine checks, before any figure is read:**
1. M's code path, given Binance's matrices instead of Bybit's and CoinDCX's coin list, must reproduce Round 22's C
   row exactly (pre-tax, T1, T2).
2. CM's code path with the first leg's VDA switched off must equal `legs` exactly.

## The decision (fixed now)

**The plan leaves Delta + CoinDCX only if every one of these holds:**
1. A new pair (M, S, CM or CS) passes every bar.
2. Its after-tax month (T1) at costs ×5 is **at least +0.50% a month above C's** (+3.55%, so at least +4.05%).
3. It is also above C at costs ×1 (+4.15%).
4. Its venue's keyed read works from the server.
5. The operator agrees to use that account.

If it moves, it moves as C542 did: in paper, the legs closed and reopened, both venues' fees booked, the history
kept. Otherwise C stays.

**Other outcomes:**
- **A pair that passes but misses the margin** may run as a paper copy beside the plan (like C538's), with no money.
- **A three-account version** (Delta + CoinDCX + Mudrex, each coin on the widest of its three gaps) is reported
  **for information only** this round. It needs its own engine and transfer rules, so it would be a later round.
- **Jumps:** all of this is subject to the same one-coin jump risk as the plan (Round 23, due 22 Oct).
