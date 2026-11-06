# Paper check #1 (29 Sep): the book's fourth daily rebalance, verified

**Server:** C504 since 28 Sep 17:12 IST. **Paper mode:** no real money.
**Verdict:** the book, funding, costs and restarts all behave exactly as
designed. Two small issues were found and fixed in C506; one question is
still open.

## (a) A rebalance every day at 05:35 IST ✅

It ran on 26, 27, 28 and 29 Sep. Today's was at 05:35:52: 12 trades, $187.11
traded, in 37 seconds.

## What happened this morning, in plain words

Monday's close was the weekly refresh for momentum and carry, so the book
turned over more than usual:
- **Out:** the ETH, SOL, PEPE and UNI longs, and the WLD, LINK and PUMP
  shorts.
- **In:** **short BTC, ETH and XRP; long HYPE, ENA and SUI**, still holding
  NEAR and ZEC.
- **Why BTC and ETH are shorts:** the momentum sleeve ranks the top 20 against
  each other. Over 14 days BTC (+6.8%) and ETH (+6.9%) rose, but far less than
  NEAR (+95%), ENA (+79%) and SUI (+62%). The laggards go short and the
  leaders go long. It's a relative bet, not a call that BTC will fall.
- **"realised today −2.63%" sounds worse than it is.** Closing the old
  positions turned losses that were already counted into booked losses
  ($6.46). Marked equity only moved by the fees ($0.11).
- **Where the book stands:** $242.24 marked, down $10.57 from 1 Sep's
  $252.81. That's **28% of this month's loss budget** ($37.92). Drawdowns of
  this size happen several times a year in the tested history.

## (b) The book matches the plan ✅ (within the rules)

| coin | plan | held | why |
|---|---|---|---|
| BTC | −$14.96 | −$16.70 | 2 steps of $8.35 |
| ETH | −$13.94 | **−$26.90** | Bitget's smallest ETH order is 0.01 ETH ($26.90); 0.52 of a step rounds to 1 (known, #18) |
| HYPE | +$12.26 | +$12.22 | |
| ENA | +$11.65 | +$11.55 | |
| XRP | −$8.47 | −$8.99 | 6 XRP |
| SUI | +$7.84 | +$7.82 | |
| NEAR | +$6.32 | +$10.25 (kept) | trimming $3.9 is under the $6 minimum order |
| ZEC | +$6.09 | +$9.28 (kept) | trimming $3.2 is under the $6 minimum order |
| 12 others | under $6 | closed or not opened | the $6 minimum |

The book holds 0.42× against a plan of 0.34×. The difference is almost all
ETH's large minimum order; it fades as the account grows.

**The independent replay.** I rebuilt the plan from Bitget's data at 01:23
UTC, on the bot's own list of 80 coins:
- the same coins sit on the same sides;
- LINK and ADA match to the cent;
- most others differ by 1–5%, and SOL's trend score differs.

A trend score can only change if the daily closing price changed. So the
likely cause is that at 00:05 UTC Bitget served a 28 Sep daily candle that
was not yet final (section 5).

## (c) Costs ≈ 0.08% ✅

- **Fees:** $0.111 on $187.11 = 0.059%, the taker rate.
- **Spread:** each fill was 0.01–3 basis points from the mid price, i.e. at
  the ask or bid.
- **Total:** about 0.07%, inside the research's 0.08% assumption.

## (d) Funding at every settlement ✅

Traced from the account file's hourly copies and checked against Bitget's
own rates:

| settlement (UTC) | booked | from Bitget |
|---|---|---|
| 28 Sep 12:00 (PUMP only, 4-hourly) | +$0.00059 | +$0.00059 |
| 28 Sep 16:00 (all 9) | −$0.00410 | ≈ 08:00's −$0.00414 |
| 28 Sep 20:00 (PUMP) | +$0.00060 | +$0.00059 |
| 29 Sep 00:00 (all 9) + the rebalance | −$6.58425 | funding −$0.0093 (ZEC's rate jumped to 0.067%) + realised −$6.463 − fees $0.111 = −$6.583 |

The last difference, $0.001, is rounding in the log lines.

## (e) Restarts ✅

The 17:12 IST restart (the C504 deploy) resumed with all 9 positions. Marked
equity carried on exactly ($244.23 before and after). C503's fixes held: the
shutdown summary (−$0.47) matched the last SESSION row, and "Log saved" was
written once.

## The paper ledgers

| ledger | today | check |
|---|---|---|
| carry | 05:40 IST, +$0.06 → $252.18 | ✅ **24 of 37 coins now pay over 10%/yr** (12 → 19 → 24 in three days: the crowd is getting more leveraged-long) |
| allostasis (K4) | "K4 0.61× vs running 0.34×" | ✅ first observation; daily scoring starts tomorrow |
| Savings | idle $173.00 | ✅ = $242.24 − ($20.79 margin + 20% of $242.24) |
| intraday shadow | every hour 09:00 → 00:00 UTC, 35–37 coins | ✅ |
| **spot pot** | 05:50 IST: **16 held, 24% invested**, $250.14 | the invested share matches an independent rebuild (24.1%), but the rebuild gives **15 coins**. The log doesn't list the pot's coins, so the extra one can't be named. **C506 fixes that** (below) |

## What was wrong, and C506

1. **A false alarm from my C504 watchdog.** It said "K4 shadow missed today's
   rebalance" every hour from 17:20 to 05:37. K4 was added at 13:09 on 28 Sep,
   after that day's rebalance, so it missed nothing. **Fixed:** K4 is now
   judged only on a rebalance run while K4 was running.
2. **The spot pot's coins weren't in the log.** **Fixed:** after each run a
   second line lists every holding, e.g. `🪙 C501 spot pot holds: LINK $5.86,
   BTC $4.95, …`.
3. **The upload script sent only the account file.** **Fixed:** it now also
   uploads the book's and the ledgers' own files (positions and cash; no keys;
   the redaction step still runs over everything), plus the rebalance's input
   data (section 5).

## 5. Why the replay differs by 1–5%, and the fix

**Test 1, is Bitget's candle final right after the close?** At 02:00 UTC I
polled the just-closed hourly candle of 6 coins at +15 s, +1 min and +3 min.
It was final at +15 s, never changed, and equalled the last minute's close. So
this is **not** a stale-data problem at Bitget.

**Test 2, how close to the edge is the rule?** **SOL's 7-day return on 28 Sep
was −0.008%.** A one-tick difference in a single closing price flips SOL's
trend score between +0.5 and +1.0. The book's plan says SOL +$2.07 (trend
+1.0); a later replay says +$1.13 (trend +0.5). That is SOL's own gap; the
other coins' 1–5% differences went unexplained. **SOL is the only coin in the
top 20 on such a knife-edge today.**

**What it means for your money:** nothing. Every coin sat on the same side,
LINK and ADA matched to the cent, and the differences are cents.

**The problem was the check:** a later fetch can't prove what the bot saw at
00:05.

**C506 fixes the check.** Each rebalance saves the exact data it used
(`c488_inputs.npz`, about 0.5 MB), and the replay tool can load it:
`python3 research/c498_plan_replay.py --inputs c488_inputs.npz`. From
tomorrow the plan can be recomputed to the cent at any time, and the spot
pot's 16-vs-15 question can be settled the same way. The spot pot uses the
same data. A SOL flip would only resize SOL, not add a coin, so the extra coin
is still open.

## Deploy C506 (Termius)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo cp /home/omega/omega/deploy/omega-logpush.sh /usr/local/bin/omega-logpush.sh
sudo chmod +x /usr/local/bin/omega-logpush.sh
sudo systemctl restart omega
sleep 90
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|C504|DATA|Traceback"
sudo -u omega /usr/local/bin/omega-logpush.sh --check
```

**What you should see:**
- `OMEGA C506`;
- no "K4 shadow missed" warning;
- the last command ends "All good".

From tomorrow the spot pot's run is followed by a "holds:" line, and the
ledgers' files reach the logs branch.
