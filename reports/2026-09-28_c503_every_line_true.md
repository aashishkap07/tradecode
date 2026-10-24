# C502 checked line by line, and C503: every log line true on its own

**Date:** 28 Sep 2026
**What changes for your money:** nothing. C503 only changes what the logs
and the dashboard *say*, so that every line is true when read by itself.

## 1. The numbers: all true

I checked each figure against the server's own logs (the 14:17 IST push),
Bitget's data, and the arithmetic.

| what | check | result |
|---|---|---|
| Book: 9 positions, $121.00 gross, open −$5.78 | rows add up to $121.00 and −$5.71; the $0.07 is the fee to close | ✅ |
| Marked $244.61, month $8.20 of $37.92 | $250.39 − $5.78; $252.81 − $244.61 | ✅ |
| **Funding at 13:30 IST** | the saved balance moved **−$0.00414**; Bitget's 08:00 UTC rates on these 9 positions give exactly −$0.0041 (PUMP pays every 4 hours, the rest every 8; the bot handles both) | ✅ to a tenth of a cent |
| "today −$1.80" | the morning rebalance −$1.79 + two funding payments of about −$0.004 | ✅ |
| Spot pot BNB $9.38, BTC $8.73, ETH $7.70 | Bitget spot moved +0.16%, +0.04%, +0.11% between 13:09 and 13:40 → $9.375, $8.723, $7.698 | ✅ |
| Savings: idle $171.76, reserve $72.86 | $23.94 margin + 20% of $244.62; the "0.02d" is counted from 13:09, carried across the restart | ✅ |
| 804 markets, fees 0.02% / 0.06% | Bitget lists 804 active USDT perps, all at maker 0.02% / taker 0.06% | ✅ |
| Market hours in IST | US 19:00–01:30 (on EDT until 1 Nov), Korea 05:30–12:00, HK 07:00–13:30 (shut at 13:36, correct) | ✅ |
| Every 8-minute block, 13:44 → 14:16 | session measured from $244.58, peak $244.70, dip 0.04% | ✅ |
| Carry ledger "funding +$0.20" not moving | by design: it adds up all funding once a day at 05:40 IST | ✅ |

## 2. Lines that were not true, or read wrongly (fixed in C503)

**The biggest one:** the start-up log said **"ARCHITECTURE — what is
actually running"**, then described the intraday scanner, which **is not
running**. The same went for the sizing, leverage, limit-order, edge and DRI
lines. They were the scanner's settings, unlabelled.
- **Now:** the log first prints a short **"WHAT IS RUNNING"** summary, read
  from the settings:
  - the book: trend + momentum + carry, the risk level, 20 coins, market
    orders at 05:35 IST, 5x;
  - the paper ledgers and their times;
  - that everything after it describes the idle scanner.
- **Each scanner line is labelled as the scanner's.**

**The other lines:**

| said | the truth | now says |
|---|---|---|
| "756 markets", "294 RWA perps" | old numbers typed into the code; today 804 and 340 | counted live |
| "CHANGELOG.md (auto-updated each revision)" | it stopped updating at C466 | "history is in the Atlas; CHANGELOG.md holds up to C466" |
| "RISK @ $250.39: 15% = $37.92" | 15% of $250.39 is $37.56; the $37.92 is 15% of the month's starting $252.81 | names the $252.81 |
| "0 positions" beside $23.94 locked | 0 *intraday* positions; the $23.94 is the book's margin | "0 intraday positions" |
| "free $226.45" / "Available $226.45" | Bitget would subtract the open loss: ≈ $220.66 | shows the figure after the open P&L |
| "4 EXIT … HARD STOP …" in the Session log | a description, but "HARD STOP" is an alarm word, so it was copied into the Session log as if a stop had fired | written in lower case; real stops still alarm |
| "MARKET bias +0.00 breadth +0.00" every 8 min | nothing measures it while the scanner is idle | row hidden while the book trades |
| "LIFETIME 139tr 44W 95L … +$0.39" | the 139 trades are the intraday bot's (about +$2.63); the +$0.39 is the whole account, book included | "…intraday · account +$0.39 realised" (page too) |
| "Win Rate: Session 0% \| Open 0%" | there were no trades, not 0% wins | "no trades yet \| none open" |
| shutdown summary "+$0.08 from $244.60" | the last status said +$0.11 (from $244.57): two starting points | one starting point, the moment the book is first priced |
| "📝 Log saved" twice | written by the stop signal *and* at exit | once |
| "Same WiFi: http://10.0.0.160…" | a server has no WiFi | "Local network … (this machine's own address)" |
| "Press Ctrl+C to stop safely" | it runs under systemd | "Stop safely: sudo systemctl stop omega" |
| Spot pot and K4 lines | never reached the Session log | now do |

## 3. Deploy C503 (Termius)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|WHAT IS RUNNING|BOOK   trend|PAPER  never|IDLE   the|RISK @|Traceback"
```

**What you should see:**
- `OMEGA C503`.
- The **WHAT IS RUNNING** lines at the top of the Session tab.
- `RISK @ … (15% of this month's anchor $252.81)`.
- In the 8-minute block:
  - OPEN shows "free … after open P&L";
  - LIFETIME ends "intraday · account $+0.39 realised";
  - there is no MARKET row.

Nothing else changes. The book, the carry ledger, the spot pot and the
Savings ledger all carry on, and tomorrow's 05:35–05:50 IST runs happen as
before.
