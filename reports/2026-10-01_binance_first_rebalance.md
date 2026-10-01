# The first Binance paper rebalance (1 Oct 2026, 09:17 IST), and C519

**Server:** C517, switched to Binance paper at 09:17 IST with a fresh start at
$500 (the `c516-venue.conf` drop-in). Checked against the five screenshots
(09:19–09:20 IST), the server's logs branch and Binance's own public data.

**Verdict:** the switch worked. One real defect: the plan targeted 14 positions
and the book holds 12. **C519 fixes it.**

---

## 1. What the screens and the logs say

| # | check | result |
|---|---|---|
| 1 | the switch | ✅ `venue: BINANCE (… PAPER only …)`; `Connected \| 739 futures markets (Binance USDⓈ-M)`; fees maker 0.02% / taker 0.05%; `Fresh start: $500.00`; header `OMEGA C517 PAPER Binance perps`; October anchors $500.00 (budget 20% = $100.00) |
| 2 | **the plan, to the cent** (`c498_plan_replay.py --inputs` on the server's saved inputs) | ✅ identical: BNB +66.65, BTC +63.10, 1000PEPE −38.90, XRP −26.49, SUI +24.10, DOGE −20.86, NEAR +19.06, TAO −16.61, ARB +12.31, **ETH +11.12**, SOL +7.58, **LINK +6.90**, HYPE +6.28, ADA +6.21; under $6: WLD, FIL, PUMP, UNI, ENA, ZEC, AKE. Crypto only: 80 candidates, 20 eligible |
| 3 | **the data the plan used, against Binance's own archive** (data.binance.vision) | ✅ closes **and** quote volumes identical on **80/80** coins for 28 and 29 Sep (78/78 on 15 Jul); daily funding identical on **all 2,418 coin-days of August**. 30 Sep's archive file is not published yet (it comes a day late): tomorrow's check |
| 4 | the 12 fills against Binance's own prices in that minute (03:47 UTC; Binance futures refuses this sandbox, so spot is the yardstick) | ✅ all within 20 bp of spot, as a perp trades: BTC 83,648 (spot 83,680–83,700), SOL 118.20 (118.24–118.32), XRP 1.4970 (1.4975–1.4984) … |
| 5 | fees and equity | ✅ 12 fees at 0.05% = $0.17; equity $499.83 = $500 − $0.17; marked $499.58 = $499.83 − $0.25 open; month used $0.42 of $100 |
| 6 | gross | ✅ $333.01 on the page = the 12 rows; 0.667× held vs the plan's 0.652× (BTC holds one 0.001 step = $83.65 for a $63.10 target; ETH and LINK are missing) |
| 7 | Savings | ✅ idle $308.06 = $499.58 − reserve $191.51 (margin $66.60 + the month budget $99.9 + 5% $24.98); × 6.8% / 12 = $1.75/month, as shown |
| 8 | carry | ✅ 8 pairs × $49.98, entry $0.095 each (spot 0.10% + perp 0.05% + spreads) = $0.76; prices inside Binance's minute. DOT, ENA, PUMP, XPL pay exactly Binance's standard 0.01% per 8 h = 10.95%/yr |
| 9 | spot pot | ✅ the rule wants 20 coins, 33.2% invested; Binance spot's $5 minimum makes the floor $6, and only BNB $9.71, ETH $9.61, SOL $6.54 clear it (LINK $5.96 just misses) = 10.3% invested. Fills inside Binance's minute. On Bitget's $2 floor it would hold 16 |
| 10 | shadow | ✅ Binance's hourly candles carry the taker-buy volume, so the **full 16-feature model runs from the first hour** (Bitget needed a week of collected flow); 39 of 40 coins scored |
| 11 | tournament, C509 | ✅ "first score at the next rebalance, for 2026-10-01"; C509 "under a day: too early to judge" |
| 12 | errors | ✅ 0 Traceback; the only red line was the 🛑 venue line (section 3) |
| ✗ | **14 targeted, 12 held, "14 trades"** | ❌ section 2 |

---

## 2. The defect: 14 targeted, 12 held, "14 trades"

The plan's floor was a flat **$6**. Binance's smallest order is **$20 for ETH,
LINK, LTC, BCH and ETC** ($50 BTC). Today's plan had **ETH +$11.12 and LINK
+$6.90**, between the two. When the book tried to open them, the order step
saw "under Binance's minimum" and returned without a word; the loop counted
the attempt as a trade anyway. So the log said 14 trades, and the book holds 12.

**Does it matter for money?** Hardly: $18 of $333. But it matters for truth. The
research priced exactly this rule (a coin under its own minimum is not held),
so the plan must say the same thing as the book, and a skipped order must
never be silent. And the rule tournament's "traded" rule held ETH and LINK,
which the book could not.

On Bitget this could not happen: every contract's minimum there is $5.

---

## 3. C519: what changes

- **Each coin's floor is the larger of $6 and the venue's own minimum order.**
  On Binance that is BTC $50; ETH, LINK, LTC, BCH and ETC $20; $6 for the rest.
  On Bitget every one of 812 contracts has a $5 minimum (read 1 Oct), so the
  floor stays $6 and nothing changes there. The research already used this
  floor (C515, C518: `max($6, the coin's minimum)`), so the paper book now
  trades what was tested.
- **The PLAN line names what fell under a coin's floor.** Today's would read
  `under $6 or Binance's minimum: 9 (ETH +11.12 < $20, LINK +6.90 < $20, WLD +4.17, …)`.
- **"N trades" counts fills, not attempts.** After the trades, every plan
  target the book does not hold is named with its reason (a step too coarse,
  under the venue's minimum, a contract not trading, or not filled) in one
  warning line.
- **The rule tournament and the K4 shadow use the same floors**, so their
  "traded" rule holds what the book could hold.
- **The saved inputs (`c488_inputs.npz`) carry each coin's floor and the
  venue,** so `research/c498_plan_replay.py --inputs` reproduces a Binance plan
  to the cent (it now reads Binance's market table when the inputs came from
  Binance, and needs no markets at all when it cannot reach them).
- **The venue switch prints a calm line** ("the saved book is Bitget's (12
  positions); this run starts fresh on Binance, so it begins flat") when the
  fresh start is already chosen. The 🛑 line stays for a switch without a fresh
  start, where the book really is blocked.

**Today's plan under C519** is 12 targets, ETH and LINK out. BTC (+$63.10, over
its $50) stays, held as one 0.001 step = $83.65. That is exactly what the book
holds, so C519 by itself causes no trade at the next rebalance. The tournament's
books saved at 09:17 still hold ETH and LINK under "N2+N3 (traded)"; 1 Oct is
scored on them, and every day after on the floors.

**Tests:** `omega_c519_test.py`, 26 checks. The battery: 41 of 42 (the exit
test needs `corpusL/`, as before). Two full boots: on a
simulated Binance with an old Bitget book and FRESH_START (the calm line, the
floors in the PLAN line, 0 errors), and fresh on real Bitget data (the same
plan as the server's, 12 targeted, 12 held, "under $6: 9").

---

## 4. Update the server

The restart resumes the Binance book (it is saved as a Binance book, so it is
not blocked). C519's floors apply from the next rebalance, 00:05 UTC
(05:35 IST).

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|venue|Loaded state|C516|Traceback"
```

**What you should see:** `OMEGA C520` (C519 plus the monthly review's Savings
rate, 6.69%: `reports/2026-10-01_monthly_review_september.md`), `venue:
BINANCE`, `Loaded state: $499.83 realised` (the Binance book resumed), no 🛑
line and no Traceback. The dashboard keeps its 12 positions.

Tomorrow after 05:35 IST, this line shows the first C519 rebalance:

```bash
sudo journalctl -u omega --since "05:30" --no-pager | grep -E "C488 PLAN|C488 REBALANCE|not held|Traceback" | cut -c1-400
```

---

## 5. Next

- **Paper check #4 (2 Oct, after 05:35 IST):** the first C519 plan (12 = 12,
  no "not held" line); the 30 Sep and 1 Oct closes against Binance's archive
  (published a day late); the tournament's first Binance day; funding at
  Binance's settlements (8-hourly, and 4-hourly where Binance lists it).
- **Still paper.** Live money waits for the CA's written answers on tax
  (`reports/2026-10-01_every_way_to_the_target.md`, section 4).
  `C488_LIVE_OK` stays False, and the Binance live order path (phase 2) is not
  built.
