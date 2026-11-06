# C499: the book now trades on the same history the research used

**Date:** 27 Sep 2026
**Server:** C498. **Pushed:** C499, which changes how the book gets its data
and therefore how big its positions are.

## 1. The ETH question is solved

On 26 Sep the 05:35 IST rebalance sold the 0.01 ETH, although the rule, rerun
later on the same data, wanted to keep it. I replayed that morning with the
bot's own code and tested every explanation against the three facts the server
logged:
- exactly the 8 held coins were targeted;
- only ETH traded;
- the gross was 0.40×.

| explanation | result |
|---|---|
| a different list of candidate coins (54 tried) | **no match** |
| the funding window sliding during the day | **no match** (same book at 00:05 and 17:57) |
| a code change, the dial, rounding | ruled out |
| **one coin's funding request failed without anyone noticing: ARB** | **matches all three facts exactly**; five other single failures don't |

**What happened:**
1. Bitget didn't answer one of the bot's requests for ARB's funding history
   (a busy moment; a timeout or a rate limit).
2. The bot read that silence as "ARB has no funding", i.e. zero.
3. With zero funding, ARB ranked as the "cheapest" coin to hold long.
4. That pushed ETH, sitting only 0.4bp inside the cut-off, out of the carry
   sleeve.

It cost only about $0.03, but it shows the book could trade on a wrong picture
of the market.

## 2. Looking for it found two bigger problems

**Problem 1: the bot fetched too little funding history.**
- **What it did:** it asked for the last 200 funding payments per coin. That's
  66 days on coins paying every 8 hours, but only **33 days** on the many coins
  paying every 4 hours (ENA, TAO, HYPE, PUMP, ONDO …). Older days were treated
  as zero funding.
- **Why it matters:** the carry sleeve's size depends on how bumpy its last 60
  days were, and 26 of those 60 days were built on missing data. So the whole
  book's size wandered: **+3% too big one day, +43% the next**, measured
  against a benchmark built the research's way.

**Problem 2: the bot only looked at today's 40 busiest coins.**
- **What it did:** the book's size comes from about 130 days of history, and
  back then "the top 20" included coins that aren't busy today.
- **Why it matters:** looking only at today's winners rewrote the past. The
  same book came out **$169** big from 40 coins, **$132** from 60 and **$134**
  from 80. It settles from about 60.

## 3. What C499 does

1. **It fetches all the funding history Bitget keeps** (about 90 days; Bitget
   stores no more). Days before a coin's first record count as **unknown**, not
   zero, so the coin sits out that day's carry ranking instead of looking
   "cheapest".
2. **It fetches history for the 80 busiest coins** instead of 40, so the past
   matches the research's past. It still *trades* only the top 20. That is 672
   requests in about 43 seconds, once a day; I measured zero errors in three
   runs.
3. **A request that fails now stops the rebalance before any trade.** The log
   says, for example, `⚠️ C488 rebalance failed (ARB funding page 2 did not
   load) -- retrying in 10 min`, and the positions are left alone. Skipping a
   day is harmless; trading on a wrong picture is not.

**Result:** on tonight's data the book comes out within **7%** of the
research-faithful benchmark, slightly smaller, which is the safe side. Before,
it was up to 43% off, and in a different direction each day.

**How I measured it:** Bitget keeps only 90 days of funding, so the benchmark
uses Bitget's 90 days plus the Binance archive for older days. That archive is
the source the original research used. The script is
`research/c499_funding_depth.py`.

## 4. Tonight's rebalance on the server (C498)

The same-moment check passed **to the cent**. The server's 12 targets and its
40-coin list are identical to my replay run 3 minutes later with the same code
(after scaling for equity). So the replay tool is proven, and the server did
exactly what its code says.

- **ETH was bought back** (0.01 at $2,692.87), as predicted.
- **It also added** SOL (0.1 → 0.2), ZEC (new long), TAO and ENA (new shorts)
  and more PUMP: 6 trades, $71.58.
- **The book is now 0.70× gross**, bigger than the research-faithful ~0.50×,
  because of Problem 1 above: the carry sleeve's scale doubled overnight on the
  short funding history. It is not dangerous at this size, but it is not the
  strategy we tested. C499 corrects it at the next rebalance.
- **The carry ledger:** +$0.17 today, $252.03 (−0.09% since it started).

## 5. What changes for you

After C499 is deployed, the next 05:35 IST rebalance will move the book to the
research-faithful size. On today's data that is about **$125 of positions on
$250 (0.50×)**, with ETH, SOL and WLD the largest. It only trades differences
bigger than 30% and $6, so expect a handful of trades costing a few cents.

The carry ledger also gets the "fail loudly" behaviour. Nothing else about it
changes.

**Tests:**
- `omega_c499_test.py`: 19 checks. They cover every page being taken; unknown
  ≠ zero, with a negative control showing zeros created fake positions; a
  failed page stopping the rebalance with the book untouched; empty ≠ failure;
  the 80-coin width; and identical results when data is complete.
- The full test run passes, except the one old file that needs a missing data
  folder.

## 6. Deploy C499 (Termius: you're already on the server)

Any time before 05:35 IST on 28 Sep:

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 120
systemctl status omega --no-pager | head -5
sudo journalctl -u omega -n 300 --no-pager | grep -E "OMEGA C4|SESSION|Book guard|C489 shadow|Traceback"
```

After 05:35 IST on 28 Sep, to see the new book being built:

```bash
sudo journalctl -u omega --since "05:30" --no-pager | grep -E "C488 PLAN|C488 CANDIDATES|C488 daily|C488 REBALANCE|rebalance failed"
```

**What you should see:**
- `C488 CANDIDATES (80 with history)`;
- a PLAN line with about 11–13 targets;
- a few `C488 daily:` trades;
- `C488 REBALANCE (daily): … gross about 0.5x`.

If you see `rebalance failed … did not load`, that's the new safety working: it
retries every 10 minutes.
