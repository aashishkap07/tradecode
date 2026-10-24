# Paper check #3 (1 Oct 2026): C512's first live test passed, and everything reconciles

**Server:** C517 since 01:22 IST, which includes C512's "final day or no
trade" check. The book is the 29 Sep fresh start, dial 20%, paper.

**Verdict:** every check passed. Nothing to fix.

---

## The checks

| # | check | result |
|---|---|---|
| version | which code ran the rebalance | ✅ `OMEGA C517` |
| **1** | **C512 live: did the 00:05 UTC rebalance trade at once, or wait for a final candle?** | ✅ **at once:** 05:35:40 IST, 40 s, **no "not final" retry**. Bitget's live daily candle was already final at 00:05, so the 23:59-minute check passed first time |
| **2** | the saved inputs' last day (30 Sep) against Bitget's FINAL 30 Sep candles | ✅ **80 of 80 coins: close and volume identical** (max difference 0). Before C512 it was 0 of 80 |
| 2 | the plan, to the cent (`c498_plan_replay.py --inputs … --dial 20`) | ✅ identical to the logged PLAN: HYPE +17.10, ENA +16.17, TRUMP +12.51, XRP −11.60, SUI +10.54, DOGE −9.19, NEAR +8.35, PUMP −8.34, ZEC +7.86, PEPE −7.65, UNI −7.48, FIL −7.18; the same 9 under $6 |
| 2 | trades | **0**: every position was within its 30% band of the new target |
| **3** | the rule tournament's first real day (30 Sep, final closes), recomputed by hand from the books held and the saved prices | ✅ to 4 decimals: **N2+N3 +1.1699%** (price +1.1727%, funding +0.0003%, entry cost −0.0031%); admitted rule +1.2795%; K4 +1.8181% |
| 3 | the real book over the same day | **+1.12%** ($250.18 → $252.98) against N2+N3's +1.17%. The 0.05% gap is execution: step rounding (NEAR held $10.59 vs $8.35), the band, mid prices five minutes after the close |
| 4 | the C512 drop line | ✅ 30 Sep 09:32:53 IST: "C512: the rule tournament's 1 scored day(s) used Bitget's unfinished daily candle and are dropped …" |
| 4 | the October month anchors (server clock IST, 00:00:09 IST) | ✅ the book's guard: **$252.89 marked, budget 20% = $50.58**. (The idle scanner's realised anchor is $249.93 / $49.99) |
| 4 | C509 | ✅ the first real rating: "since the book began 29 Sep: **+$2.98 (+1.19%) in 1.6 days**; normal for that long −1.5% to +2.2%; **top 22%: normal**". The month line: "+0.04% in 0.2 days (under a day: too early to judge)" |
| 4 | funding at every settlement (30 Sep 03:43 → 1 Oct 00:46 UTC) | ✅ **all 12 positions exactly equal** to Bitget's rate × quantity × price. 8-hourly coins: 3 settlements (08, 16, 00 UTC). ENA, HYPE, PUMP, TRUMP: 6 (every 4 h). Total −$0.00119 both ways, across 5 restarts |
| 4 | carry | ✅ 05:40 IST: +$0.05 → $249.66, 8 held, 25 of 37 eligible above 10%/yr |
| 4 | spot pot | ✅ 05:50 IST: $250.79 (+0.32%), 16 held, 28% invested, 8 trades |
| 4 | Savings | ✅ idle $167.12 at 7.63%, +$0.058 so far |
| 4 | shadow | ✅ every hour; M1 $256.10 (+2.47% in 3 days, paper only, warm-up model) |
| 4 | DATA, errors | ✅ "on time" in every block; **0 Traceback and 0 warnings** in all 3 overnight sessions (C513 from the 18:16 IST reboot, C516, C517) |

---

## In plain words

- **The fix works.** For five days the book had been deciding on the
  previous day's prices without anyone knowing. This morning it decided on
  the true final prices, and checked them first.
- **The paper book is ahead:** +1.19% in 1.6 days ($252.98). The research
  says that is normal for this period: in the top 22% of outcomes, nothing
  unusual. Two days prove nothing either way.
- **The tournament has started counting.** On its first real day the
  admitted rule (+1.28%) and K4 sizing (+1.82%) beat the traded N2+N3
  (+1.17%). One day is noise; it takes months.
- **Every cent reconciles:** plan, prices, funding, ledgers.

---

## Next: the switch to Binance paper (the "go")

Paper check #3 passed and your C517 Binance check passed, so the switch can
go ahead. It is a **fresh start**: the Bitget paper ledger closes at about
$253, and a Binance paper account begins at $500. It stays paper. Live money
waits for the CA's answer on tax (`reports/2026-10-01_every_way_to_the_target.md`,
section 4).

```bash
sudo mkdir -p /etc/systemd/system/omega.service.d
printf '[Service]\nEnvironment=OMEGA_VENUE=binance\nEnvironment=OMEGA_CAPITAL=500\n' | sudo tee /etc/systemd/system/omega.service.d/c516-venue.conf
sudo systemctl daemon-reload
sudo -u omega touch /home/omega/omega/data/FRESH_START
sudo systemctl restart omega
sleep 120
sudo journalctl -u omega -n 300 --no-pager | grep -E "venue|Connected|Fresh start|REBALANCE|C516|Traceback"
```

**What you should see:**
- `venue: BINANCE`;
- `Connected | … futures markets (Binance USDⓈ-M)`;
- `Fresh start: $500.00`;
- within a minute or two, `C488 REBALANCE (first): … of $500.00`, with a
  crypto-only plan like your check's;
- no Traceback.

The dashboard will show "Binance perps", Savings at 6.8%, and the spot pot
with its 1% TDS line. The dashboard link stays the same, because restarting
the bot doesn't restart the tunnel.

**To go back to Bitget at any time:**

```bash
sudo rm /etc/systemd/system/omega.service.d/c516-venue.conf
sudo systemctl daemon-reload
sudo -u omega touch /home/omega/omega/data/FRESH_START
sudo systemctl restart omega
```
