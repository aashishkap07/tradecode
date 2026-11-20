# Paper check #2 (30 Sep): the first N2+N3 daily rebalance, and a data defect found

**Server:** C511 since 29 Sep 20:13 IST. The ledger is the 14:13 IST fresh
start at dial 20%. **Paper mode:** no real money.

**Verdict:**
- Everything the bot books is right: fills, fees, funding, the ledgers, the
  watchdog.
- **But the check found a real defect in the data the book decides on.** It
  has been there since the book began on 25 Sep. It is fixed in **C512**, and
  measuring it is worth more than anything else in this report.

---

## 1. The defect: each morning's decision used a day-old close

**What happens at 05:35 IST.** The bot downloads each coin's daily history
from Bitget and decides on the day that has just finished. I compared what it
downloaded at 00:05 UTC with Bitget's final data:

| | the bot's copy of 29 Sep (fetched 00:05 UTC) | Bitget's final 29 Sep candle |
|---|---|---|
| ZEC close | 1479.38 | **1417.41** (= the 23:59 UTC minute's close) |
| closes that matched, of 80 coins | **0** | |
| typical gap | 3.3% (the worst: US +79%) | |
| volume | about **1%** of the final | |
| the day before (28 Sep) | 80 of 80 match | |

**What was going on.** Bitget's *history* endpoint was still serving the
just-finished day as a snapshot taken in its first few minutes. By 01:20 UTC
it held the final candle.

**The effect.** The trend signals, the 14-day momentum ranks and the
volatility sizing all read, in effect, the **previous day's close**. The
research always used the day's own close. Funding comes from a separate feed
and was correct.

**This also explains the 29 Sep mystery.** A replay at 01:23 UTC differed
1–5% from the bot's 00:05 plan, and I had tested only whether *hourly*
candles were final. It was the *daily* candle.

**What it costs**, on 2020–26 history (`research/c512_lag_cost.txt`, the
bot's exact defect: price inputs a day old, funding current):

| set-up | correct data | stale price inputs | cost |
|---|---|---|---|
| admitted rule, dial 15% | +35.5%/yr, Sharpe 1.55, worst DD 31.4% | +31.8%/yr, 1.45, 36.7% | 3.7 pts/yr |
| admitted rule, dial 20% | +53.8%/yr, 1.66, 41.5% | +44.9%/yr, 1.47, 48.5% | 8.9 pts/yr |
| **N2+N3, dial 20% (what runs)** | **+60.2%/yr, 1.81, 38.3%** | +55.7%/yr, 1.70, **47.9%** | 4.6 pts/yr, and **~10 points more drawdown** |

**What it changed today: nothing.**
- I recomputed this morning's plan on the final closes, and it is the same
  book to the cent (ZEC differs by 1 cent).
- The momentum and carry sleeves are chosen on Mondays, and no trend signal
  flipped on the stale close.
- **It matters on the days a signal sits near its edge.** For momentum, that
  is every Monday-close rebalance (Tuesday 05:35 IST), when the 14-day ranks
  are set for the week.

### C512, the fix

1. The last few daily candles now come from Bitget's **live** candle
   endpoint, which had the final bar.
2. **Before the book trades,** the just-finished day's close is compared with
   the close of that day's last minute (23:59 UTC). A daily close must equal
   it. If they differ, or either request fails, the rebalance **does not
   trade**: it retries in 10 minutes. This is the C499 rule of complete data
   or no trade.
3. **Checked on live Bitget now:** all 80 candidates load through the check,
   with no false alarm. The loaded 29 Sep closes equal Bitget's final ones.
4. **The carry ledger** gets the same final bar. **The spot pot** uses the
   book's data, so it is fixed too.
5. **The rule tournament's first scored day** (29 Sep) was computed on the
   stale candle for all 7 rules: every rule came out −0.17% to −0.32%.
   - It is dropped, once, with a log line saying why.
   - Its record restarts with 30 Sep, scored on final closes at tomorrow's
     rebalance.
   - The books it holds are kept.

**The tests:**
- `omega_c512_test.py`: 21 checks, including 3 coins on live Bitget data.
- `omega_c499_test.py`'s fake Bitget now also serves the live endpoint.
- The full battery: 38 of 39 pass; `omega_exit_test.py` needs `corpusL/`, as
  always.

---

## 2. The checks you asked for

| check | result |
|---|---|
| **Version** | **C511 since 20:13 IST.** The boot is clean: the IDLE line reads "139 trades, 44W/95L before the 29 Sep 2026 fresh start; it lost after fees"; there is no ~80-line scanner description; the headers read "daily book"; there is no separate K4 line; the book was resumed with 11 positions and $249.93 realised |
| **(1) The plan, to the cent** | ✅ `c498_plan_replay.py --inputs c488_inputs.npz --dial 20` reproduces the 30 Sep PLAN line exactly: 12 targets (HYPE +15.49 … PUMP −6.16) and the same 9 under $6 |
| **The trade** | ✅ **only one:** SELL PUMP 1042 @ 0.005911 ($6.16, fee $0.004), inside Bitget's 00:04–00:06 UTC minute candles. The other 11 stayed within the 30% band. FIL grew from −$6.36 to a −$8.05 target: $1.69 of change, under the $6 order minimum |
| **(2) The tournament's first day** | the N2+N3 row's −0.1821% **equals my hand calculation from the saved inputs to 4 decimals** (price −0.146%, funding −0.002%, entry cost −0.034%). Of that −0.146%, **−0.47% came before the book existed** (00:00→08:44 UTC) and about +0.32% after. The real book made +0.36% from its 08:44 fills to the close. But the whole day was scored on the stale candle, so it is dropped (C512) |
| **(3) Carry, spot pot, Savings, shadow** | ✅ carry 05:40 IST (+$0.07 → $249.61, 8 held); spot pot 05:50 IST (14 held, 20% invested, with its "holds:" line); Savings idle $165 at 7.63%; the intraday shadow scored every hour from 15:00 to 00:00 UTC |
| **Errors** | ✅ 0 Traceback, 0 warnings in 10 hours |
| **(4) DATA** | ✅ "on time" in every block through 05:35–05:50 IST; no C504 alarm |
| **(5) C509** | ✅ "since the book began 29 Sep: +0.07% in 0.6 days (under a day: too early to judge)". 08:44 → 00:05 UTC is 0.64 days |
| **(6) Funding** | ✅ **every settlement matches Bitget's rates** for all 12 positions: 16:00 and 00:00 UTC for the 8-hour coins; 12:00, 16:00, 20:00 and 00:00 for ENA, HYPE and TRUMP. Booked −$0.00308 vs −$0.00298 at entry prices (the difference is mark vs entry price) |
| **(7) C511's changes** | ✅ all as designed |

**One cosmetic fix, in C512:** the FEES row printed "book $0.00" for today's
$0.004 fee. It now shows three decimals below a cent.

---

## 3. Where the book stands (06:14 IST)

- **Equity:** $250.57 marked, **+0.23%** since the fresh start.
- **Positions:** 12, 0.46× gross.
- **Month:** $0 of the $50 loss budget used.
- **The book:**
  - long HYPE, ENA, TRUMP, SUI, NEAR, ZEC;
  - short XRP, DOGE, FIL, PEPE, UNI, PUMP.
- **Too early to judge** (under a day); the C509 line will start rating it
  from tomorrow.

---

## Deploy C512 (Termius)

A normal update. The push script is unchanged; **don't** start fresh.

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|C512|Traceback"
```

**What you should see:**
- `OMEGA C512`;
- `C512: the rule tournament's 1 scored day(s) used Bitget's unfinished daily
  candle and are dropped …`;
- no Traceback.

**Tomorrow at 05:35 IST, one of two things happens:**
- the rebalance runs normally (the live candles were final); or
- the log says `rebalance failed (… daily close not final …) -- retrying in
  10 min`, and it trades a few minutes later on final data.

Either is correct behaviour. The check at 06:45 IST tomorrow will confirm
which.
