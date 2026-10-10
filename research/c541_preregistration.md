# Round 21 (C541) pre-registration: CoinDCX in Pi42's place as the plan's second leg

Committed and pushed **before** any test below runs. 8 Oct 2026, ~16:45 IST.

## Why

On 8 Oct, Pi42's trading gateway (`fapi.pi42.com`) answered 403 to every request, with or without a key. It
refused this research machine (US), the operator's server (Oracle Mumbai) and the operator's phone on
Indian 5G. So it is an allow-list, not a cloud or country block. The operator has emailed Pi42 support and
asked (8 Oct): "while i wait for their reply, it would be better to look for another Indian rupee
exchange". The B2 routine (15 Nov) already says a different rupee venue "needs its own pre-registered
study". This is that study.

## Facts established before the test (8 Oct, 10:45-11:10 UTC, from this research machine)

| | CoinDCX (INR-margin futures) |
|---|---|
| public API (`api.coindcx.com`, `public.coindcx.com`) | 200 JSON |
| private API with a fake key (`/exchange/v1/derivatives/futures/positions`) | **401 JSON "Invalid credentials"**, i.e. the gateway lets the request reach its key check (Pi42: 403 web page) |
| coins it lists that Delta India also lists | 191 (Pi42: 113) |
| its last rent rate vs Binance's last settled rate, on those 191 | **identical on 191 of 191** (its instruments are Binance's pairs, `B-<coin>_USDT`, `mkt` = Binance's symbol) |
| its rent interval vs Binance's | identical on 191 of 191 |
| fee (its instrument data) | taker 0.059% = 0.05% + 18% GST, maker 0.0236% (Pi42: 0.10% + GST) |
| minimum order | 6 to 60 USDT (BTC 60); every coin fits a $100 leg |
| margin in rupees | contracts stay USDT-quoted; rupees are converted at a fixed rate (support page: 1 USDT = Rs 102; spot USDT/INR Rs 99.24 at 11:00 UTC) for margin and settlement |

So Binance's funding history stands in for CoinDCX's, as it already does for Pi42's (C532).

Other rupee venues looked at the same day (reported, not tested here):
- **ZebPay:** public and fake-key private API answer in JSON; it has a read-only key permission; its futures
  show Binance's own trade IDs. But it publishes no rent rate or rent history, and its taker fee is
  0.06-0.10%.
- **Mudrex:** INR margin since March 2026. Its private API answers in JSON. But the key is sent as a plain
  header with no signature, no IP lock is documented, and no rent rate or rent source is published.
- **CoinSwitch:** USDT-margined (bought with rupees). That brings the USDT itself into the VDA rules the plan
  avoids.

## Data and engine (fixed now)

- **The Round 20 engine, unchanged:** `research/c532_india_only.py`'s `xv_pi42`. That is:
  - the X1 rule, "ALL harder" (midnight timing, Delta's mark, costs x5, 18% GST on rent paid at **both**
    venues, kept although CoinDCX's terms may not charge it);
  - $1,000, 10% a leg, whole Delta contracts;
  - 2024-10 -> 2026-09;
  - `C524_MARK=1`, the same cache of Delta and Binance history.
- **Accounts:** `research/c531_split_600.py`'s `sides`, with the 65% even-out rule.
- **One coin list date:** each variant uses Delta's turnover read once, in the same run (Round 20 showed the
  list moves day to day). A coin needs Delta turnover >= $100k and must move with Binance (correlation
  >= 0.9).

## Variants

| | second leg's coins | second leg's cost a side |
|---|---|---|
| **P0** (reference, today's plan) | Pi42's 113 (`research/c532_pi42/pi42_universe.json`) | Pi42: 0.10% x 1.18 + 0.02% half-spread |
| D1 (the fee alone) | Pi42's 113 | CoinDCX: 0.05% x 1.18 + 0.02% half-spread |
| **D2** (the candidate) | CoinDCX's (the 191 above) | CoinDCX |

The fixed rupee rate is a sizing detail, not a cost: the CoinDCX leg is sized in rupees so that its dollar
value matches Delta's leg. A change of the fixed rate would revalue only that leg's open profit or loss. It
is not modelled; this is stated.

## The bar for D2 (all must hold)

1. **Gate G1** on history:
   - average month >= +1.5%;
   - no month below -4%;
   - the poorer account never below 40% (with the 65% even-out).
2. HAC t >= 2.0 on the daily P&L.
3. Each year (Oct 2024-Sep 2025 and Oct 2025-Sep 2026) net positive. The four half-years are reported.
4. **List wobble:**
   - D2 must keep the worst month >= -4% and the poorer account >= 40% when each of the 5 coins with the
     largest total P&L in D2 is removed in turn;
   - the same at Delta turnover floors of $75k and $150k.

D2 does **not** have to beat P0: the reason to switch is access, not return. P0 and D1 are reported beside
it so the coin-list and fee effects are visible.

## What happens on each outcome

**D2 passes:**
1. CoinDCX becomes the plan's second leg in the paper ledger as a new version: a new paper account
   alongside, then the switch. The Pi42 ledger is kept until the switch.
2. B1's read-only client gets a CoinDCX entry. Its signature is checked first against CoinDCX's documented
   example and a fake key's 401.
3. The B2 routine (15 Nov) builds the order path on CoinDCX instead of Pi42.
4. If Pi42 opens its gateway first, the choice is the operator's. The report states both.

**D2 fails:**
- The plan stays on Pi42, waiting for its support.
- ZebPay is the next candidate, but only once its rent can be read.
