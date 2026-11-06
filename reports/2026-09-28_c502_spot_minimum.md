# C501 on the server, checked, and C502: the spot pot at spot's real minimum

**Date:** 28 Sep 2026
**What changes for your money:** nothing. The spot pot is still a paper pot.

## 1. C501 on the server: everything adds up

| figure (13:13 IST) | check | verdict |
|---|---|---|
| `OMEGA C501`, log since 13:09 | 0 warnings, 0 errors | ✅ |
| Marked **$244.54**, book open **−$5.85** | $250.39 realised − $5.85 | ✅ |
| 9 book rows | sum −$5.79; the $0.06 difference is the fee to close; gross $120.73 = 0.494× | ✅ |
| Month **$8.27 of $37.92** | $252.81 − $244.54 | ✅ |
| PUMP and SOL marks | inside Bitget's own 07:42–07:44 UTC candles | ✅ |
| **Idle cash $171.69 (70.2%)**, reserve $72.85 | margin $23.94 + 15% + 5% of $244.54 = $72.85; $171.69 × 7.63% / 12 = $1.09/month | ✅ |
| **Spot pot $249.98**: BNB $9.36, BTC $8.72, ETH $7.69, cash $224.21 | fees $0.02 = 0.08% of $25.78; 10.3% invested; the same dollars as my own run this morning | ✅ |
| K4 line: "starts at the next rebalance" | as designed; its first comparison is at 05:35 IST tomorrow | ✅ |
| Carry ledger −$0.14, 8 held | the 8 rows sum to −$0.13 (rounding); no funding settlement since 05:30 IST | ✅ |

**Two things that look odd but are right:**
- **The start-up block says "used $2.41 realised";** the dashboard says
  $8.27. The $2.41 is the closed part only. The guard adds the open −$5.8
  once prices come in, which the next status block shows ($8.21).
- **"free $226.45"** is the paper account's realised money minus margin.
  Bitget itself would also subtract the open loss (≈ $220.66). Nothing in the
  book is sized on this figure, so I've only noted it (Atlas pending #19).

## 2. What I found: the spot pot was far too small, and I explained it wrongly

**Yesterday I told you** only BNB, BTC and ETH qualified because the market
was choppy. **That was wrong.**

I rebuilt the day independently from fresh Bitget prices, with the research
code rather than the bot's (they agree exactly). **All 20 coins are in an
uptrend**, and the rule wanted the pot **36% invested**. It held only 10%:
- **The $6 minimum per coin dropped 17 of the 20** (LINK $5.85, SOL $5.78,
  XRP $5.51 … ARB $1.97).
- **Only the three calmest coins get weights above $6.** A pot of $250 spread
  across 20 coins gives most of them $2–6.
- **The $6 came from futures,** where Bitget's minimum is about $5. **On spot,
  Bitget's minimum is $1** for every one of these coins; I checked it on
  Bitget's own symbol list.
- **Why it matters:** the pot was running at about a third of its own risk
  set point. The self-adjusting part was being overruled by a limit that
  doesn't exist on spot.

## 3. The fix was tested first (C502)

As always, the test was written down and pushed **before** any result
(commit c1c9376). The rule stays the same; only the minimums change: a coin is
bought only if its target is at least $2 (so it can still be sold after a 50%
fall), and a change under $1 isn't traded. It had to pass the same four bars
as C501, and would be adopted whatever its return.

I also measured real spot spreads: the median across the 20 is 0.015%,
comfortably inside the 0.10% cost the test assumes.

| 2020 → Aug 2026 | old ($6) | **new ($1 spot minimum)** |
|---|---|---|
| per month | +2.20% | **+2.59%** |
| worst drawdown | 27.0% | 28.8% |
| worst month | −10.2% | −10.0% |
| coins held on average | 4 | 7 |
| bad year 2022 | −6% | −13% |
| **both $250 pots together** | +2.47%/month, worst month −5.8% | **+2.67%/month, worst month −5.7%**, worst drawdown 22% |

**It passed all four bars**, so it's in the bot as C502.
- **The trade-off:** a more-invested pot loses more in a bad year (2022). Most
  months are flat or slightly negative; it earns its money in the trending
  months.
- **What you'll see:** at 05:50 IST tomorrow the pot adds the other coins. On
  today's numbers that would be 18 coins, about 34% invested; ARB and TRUMP
  are just under $2.

## 4. Deploy C502 (Termius: you're already on the server)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|C501|Traceback"
```

**What you should see:**
- `OMEGA C502`.
- The spot pot keeps BNB, BTC and ETH, and doesn't run again today (it has
  already run once).

**After 05:50 IST on 29 Sep:**

```bash
sudo journalctl -u omega --since "05:30" --no-pager | grep -E "C488 PLAN|C488 REBALANCE|C501|C490 carry"
```

**Expected:**
- the book's rebalance;
- the first K4 comparison: `🧬 C501 allostatic shadow (paper)`;
- the carry ledger;
- the spot pot: `🪙 C501 spot pot (paper) … N held` with N around 15–20,
  depending on tonight's close.

This is a normal restart: the book, the carry ledger, the spot pot and every
position are kept.
