# Round 23 (C547) pre-registration: protection against one coin jumping several times over in a day

Committed and pushed **before** any test below runs. 23 Oct 2026, ~09:45 IST. (The routine fired 22 Oct.)

## Why

- **BLESS +530% on 15 Oct 2025** emptied the short leg's account in Round 22's 20-pair runs.
- **STRK +38.8% within 18 hours on 9 Oct 2026** hit the plan's CoinDCX short leg.
- **Round 24** (`research/r24_round24.py/.txt`) changed the ground rules:
  - minute data, not daily closes;
  - cross margin, not isolated margin per leg;
  - the C546 cap (at most 6 of 10 pairs facing one way) is part of the plan.
- **15 pairs of 12%** (Round 22's pick) has been held back for this risk alone.

## Data and engine (fixed now)

- **Engine:** Round 24's `legs2` / `sides2` (cache rebuilt 10 Oct from the public endpoints; 2024-10-01 → 2026-09-30;
  Delta + CoinDCX, the 64-coin list; costs ×5 for every bar, ×1 reported; tax T1 31.2%; **K6 cap on**).
  - It is copied as `legs3` / `sides3` with three new switches.
  - **Engine check:** with every switch off, they must reproduce `legs2` / `sides2` with capK=6 exactly. Otherwise
    nothing below is read.
- **Daily mark highs:** Delta's `MARK:<symbol>` 1d candles and Binance's markPriceKlines 1d. "A jump" = the day's
  mark high ÷ the previous day's close − 1, on either exchange.
- **Minute replays:** Round 24's `minute_day` (1-minute mark prices, each leg at its worst extreme each minute, cross
  margin).
  - It is extended so that a stopped leg is frozen at its stop.
  - **Days replayed:**
    - Round 24's six;
    - plus every day on which a coin held by the base book jumped or fell ≥ 30% intraday (daily mark high/low vs
      the previous close, either exchange), the 40 largest if there are more.

## The protections (each on top of 10 × 10% with the K6 cap)

| | rule |
|---|---|
| **J1** | no new pair in a coin with a ≥ +100% jump in the last 90 days |
| **J2** | no new pair in a coin with < 90 days of Binance history (new listings) |
| **Z1** | half-size legs (5%) for that day's candidates in the top quarter of 30-day volatility (std of daily Binance returns) |
| **Z2** | half-size legs for a coin with a ≥ +50% jump in the last 30 days |
| **S50** | a stop on each pair's SHORT leg at +50% above the previous daily close, re-placed at every daily run; when it triggers, the twin is closed at once |
| **S100** | the same at +100% |

How the stop variants are booked:
- **Fill:** the stopped short leg fills 5% of its size worse than the stop.
- **The twin's gain** is capped at the smaller of the stop level and its own day's high move.
- **Costs:** both legs' exit costs are paid. No rent that day.
- **Re-entry:** the pair may re-enter under the normal rule the next day.
- Long legs get no stop: a crash wick would sell them at the bottom, which is Round 24's lesson.

## Stress measures (cross margin, from the daily account book)

- **W530:**
  - on each day, a +530% one-day jump (BLESS, 15 Oct 2025) is put on the held coin with the largest short leg;
  - the measure is the share of days on which that would take its account to zero or below;
  - with a stop, that leg's loss is capped at (stop + 5%) of its size.
- **L100:** the lowest account ratio over the 24 months after a +100% jump (about once a year per 10 coins held) on the
  largest short leg, on every day.

## A protection is adopted into the plan only if ALL hold (costs ×5)

1. Every Round 22 Part A bar holds on every wobble list (G1, HAC t ≥ 2, both years positive; the 5 largest-P&L coins
   removed in turn, turnover floors $75k and $150k).
2. After tax it earns at least the base (10 × 10% + K6) **minus $30 a year**.
3. **Safer:** W530 falls by ≥ 50% (relative), **or** L100 rises by ≥ 10 points.
4. **Minute replays:**
   - no account is wiped on any replayed day;
   - the poorer account's lowest point across the replayed days is ≥ the base's minus 2 points.

**If two or more pass:** their combination is run once against the same bar. It is adopted if it passes; otherwise the
single passing protection with the best L100 is adopted.

## The bigger settings (only with the adopted protections)

10 / 15 pairs × 10 / 12% (the cap stays 60% of the slots). A bigger setting replaces 10 × 10% only if:
- every Part A bar holds on every wobble list;
- W530 is no worse than 10 × 10%'s with the same protections;
- on every replayed day no account is wiped and the poorer account stays ≥ 40%;
- it earns ≥ **$50 a year more after tax** than 10 × 10% (with protections);
- it adds at most one more losing month.

## What happens next

- **What passes goes into the bot's paper ledger (C547)**, with tests, keeping the C544/C545 tax journal complete. A
  stop that passes becomes the order path's resting stop order in B2 (15 Nov).
- **If nothing passes, the plan is unchanged.** The report then says plainly what a one-coin jump would cost.
- `C488_LIVE_OK` stays False.
