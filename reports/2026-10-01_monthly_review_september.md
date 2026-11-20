# Monthly review #1: September 2026

**Source:** every September log on the server's logs branch (the detail logs
and the hourly state pushes up to 1 Oct 10:17 IST), checked line by line.
Routine "OMEGA monthly review".

**Read this first:** September was a building month, not a trading record. The
book ran for **six days in two stretches**: the first rule from 25 Sep, then the
29 Sep fresh start on the N2+N3 rule. Every paper ledger was reset at that
fresh start, and again at the 1 Oct switch to Binance. So these are checks
that the machinery works. They are not evidence of edge: five days carry a
t-statistic of about 0.14.

---

## 1. The book (C488)

| stretch | rule, dial | from → to (marked) | return | month guard used (worst) | rebalances |
|---|---|---|---|---|---|
| **A** 25 Sep 17:46 → 29 Sep 14:10 IST (Bitget) | the first rule, 15% (vol 20%) | $252.63 → $241.36 | **−$11.27 (−4.5%)** | $11.45 of $37.92 = 30% (worst $11.84 = 31%, 28 Sep 08:41) | 25 Sep first (9 trades), 26 (1), 27 (6), 28 (5), 29 (12) |
| **B** 29 Sep 14:14 → 30 Sep 24:00 IST (Bitget) | N2+N3, 20% (vol 26.7%) | $250.00 → $252.89 | **+$2.89 (+1.16%)** | $0.33 of $50.00 = 0.7% | 29 Sep first (11), 30 Sep (1) |

- **Rebalance failures: none.** No "rebalance failed" line, no "not final"
  retry and no Traceback in any September log. Every daily rebalance ran at
  05:35 IST.
- Stretch A's month anchor was $252.81 (carried from C482, 23 Sep). The book
  started at $252.63.
- **Stretch A decided on the previous day's prices.** C512 found this on
  30 Sep: Bitget's daily candle was not final at 00:05 UTC. Stretch B's second
  day was the first to decide on final closes.
- Had the book not been reset, the two stretches chain to about −3.4% over six
  days. That is a normal week-scale swing for a book at these dials, and well
  inside either month's budget.
- **October so far:** on 1 Oct the Bitget book rebalanced at $252.98 (0
  trades). At 09:17 IST the switch began a fresh Binance book at $500
  (`reports/2026-10-01_binance_first_rebalance.md`; C519 fixes its "14
  targeted, 12 held").

## 2. The spot pot (C501Spot, #15)

| stretch | from → to | invested | held | trades | fees | Savings interest on its cash |
|---|---|---|---|---|---|---|
| 28 Sep 13:09 → 29 Sep (C501, then C502's $2 floor) | $249.98 → $250.14 (+0.06%) | 10% → 24% | 3 → 16 | 20 | $0.075 | $0.045 |
| 29 Sep 14:15 → 1 Oct 05:50 IST | $250.00 → **$250.79 (+0.32%)** | 22% → 28% | 15 → 16 | 27 (3 closed) | $0.073 | $0.072 |

- **"No spot pair" coins: none** on Bitget, and none on Binance's first run.
- **Since 1 Oct on Binance:** $249.97, 3 held, 10% invested. Binance's $5 spot
  minimum makes the floor $6, so most of the rule's $2–6 targets cannot be
  held at $250. India also deducts 1% TDS on each sale. The pot stays paper.

## 3. Idle cash in Savings (C501Savings, #14)

| stretch | days | average idle | interest |
|---|---|---|---|
| 28 Sep 13:09 → 29 Sep 13:17 IST | 1.01 | $170.88 (≈ 70% of equity) | $0.0359 |
| 29 Sep 14:15 → 1 Oct 08:12 IST | 1.75 | $165.87 (≈ 66% of equity) | $0.0606 |

- At 7.63% that pace is about **+0.42–0.45% a month on the whole account**,
  for doing nothing.
- On Binance (1 Oct): $308 idle of $500 (62%) at 6.69% is about +0.34% a
  month.

## 4. The allostatic shadow (K4, #16)

- **The separate K4 ledger:** it ran on 28–29 Sep and wanted 0.61–0.70× gross
  against the running sizing's 0.34–0.42×. It scored 0 days before the fresh
  start reset it. Since C511 it rests while the tournament runs, because the
  tournament's "N2+N3, K4 sizing" row is the same comparison.
- **The tournament's first real day** (30 Sep, final closes): K4 **+1.82%**
  against N2+N3's **+1.17%**, at 0.71× against 0.49× gross. On an up day
  more exposure earns more.
- **Vol and drawdown:** not measurable on one day; that needs at least 20.
  The December re-test (#11) decides K4.

## 5. The C489 intraday shadow (#4)

| stretch | days | M1 (probability model) | M1g (cost-gated) |
|---|---|---|---|
| 25 → 29 Sep | 5 | $252.26 → $255.95 (+1.46%), peak +7.19% on 27 Sep | +0.03% |
| 29 Sep → 1 Oct 08:32 IST | 3 | +2.34% | +1.18% |

- **t-statistic:** not computed yet (it needs at least 20 days).
- **ELIGIBLE: no.** That needs at least 120 days, and the record restarted at
  0 with the Binance switch.
- On Bitget it ran the warm-up model (14 features, no flow). On Binance the
  full 16-feature model runs from the first hour.
- The research expects it to lose after costs, and 8 days of +2% is noise.

## 6. The carry ledger (C490)

| stretch | from → to | entry fees | funding collected |
|---|---|---|---|
| 25 → 29 Sep | $252.26 → $252.18 (−0.03%) | $0.40 | +$0.26 |
| 29 Sep → 1 Oct | $249.94 → $249.66 (−0.11%) | $0.40 | +$0.12 |

- Each fresh start bought a new set of 8 pairs and paid the entry fees again.
  At about 11% a year of funding, a $250 carry book needs about 6 days to
  earn back its entry cost, and neither stretch lasted that long.
- **Binance (1 Oct):** $499.07, 8 held. Four of them (DOT, ENA, PUMP, XPL)
  pay exactly Binance's standard rate, 0.01% every 8 hours = 10.95% a year,
  just above the 10% entry bar (#10: review that bar in December).

## 7. The Savings rate (#17)

- **Bitget:** its Earn API needs a key, and Bitget's pages don't open from
  India, so it can't be read here. The Bitget default stays 7.63% (28 Sep).
  Bitget is no longer the venue.
- **Binance (read 1 Oct from Binance's public Earn listing):** USDT Flexible
  pays **6.69%**. That is a fixed 4.00% bonus on the first 1,000 USDT plus a
  2.69% market rate that floats daily. **Updated `C501_SAVINGS_APR` on
  Binance from 6.8% to 6.69% (C520).** Above 1,000 USDT idle only the market
  rate is paid; that starts to matter at about $1,600 of equity.

## 8. The dial (#6), with the latest numbers

| dial | P(a year averages ≥ 2%/month): backtest / with the ⅓ haircut | worst month | max drawdown | 2022 |
|---|---|---|---|---|
| 15% (C510) | 75% / 50% | −13.6% | 22.6% | −8% |
| **20%** (C510; C518 on Binance at $500: Sharpe 1.87, +4.24%/month) | **81% / 60%** | −17.7% | 36.6% | −21% |
| 20%, after tax reading A (31.2% of each year's net profit) | 72% / 48% | | | |
| 20%, strict tax reading B | about 0%/year left | | | |

**No change:** 20% in paper (it shows the real swings). For live, start lower
(10–15%, #2) and raise the dial only once live tracks paper. The tax answer
(#8) matters far more than the dial.

## 9. Still open

- **Security (#3), before any live key:**
  - rotate the control token;
  - a trade-only API key, withdrawals off, IP allow-listed, on a
    **sub-account**;
  - `data/api_keys.json` at chmod 600, never in the .py;
  - the hard-coded `NEWS_API_KEY` (rotate it and move it out; your call);
  - never open port 8138, and don't copy `deploy/omega.service` over the
    installed unit.
  - `C488_LIVE_OK = False` (checked today).
- **Tax (#8):** the CA's written answers to the four questions in
  `reports/2026-10-01_every_way_to_the_target.md`, section 4. They decide
  whether live money goes to Binance, to Delta Exchange India, or nowhere.
  Two side questions: the spot pot's 1% TDS, and the carry trade's two legs
  taxed separately.

---

## Update the server (C520 = C519 + the 6.69% rate)

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|venue|Loaded state|Savings at|C516|Traceback"
```

**What you should see:** `OMEGA C520`, `venue: BINANCE`, `Loaded state:
$499.83 realised`, `Savings at 6.69%`, no 🛑 line and no Traceback.
