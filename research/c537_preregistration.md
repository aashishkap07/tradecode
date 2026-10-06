# Round 19 (C537) pre-registration: when, and how often, the rent-gap trade should decide

Committed and pushed **before** any test below runs. 6 Oct 2026, ~10:30 IST.

## Why

**The operator (6 Oct):** "ensure that all these principles are incorporated intelligently and in the most
profitable manner .. for example, the rate of monitoring of rent gap, fixed daily reviews and then only
the decision to close or not, or in other words the frequency with which the entire function carries out
is the most profitable on average? check other things too in detail".

**The trade as it runs (X1 on Pi42, C533):**
- **Signal:** the trailing 7-day mean of (Delta funding − Pi42/Binance funding), annualised.
- **Rules:** enter at |s| ≥ 20%/yr; exit under 10%/yr or on a sign change; at most 10 pairs, 10% of
  capital a leg.
- **Timing:** decided **once a day at 00:30 UTC** (06:00 IST), just after the 00:00 UTC settlement.

## Data and engine (fixed now)

**Data:**
- Round 15's cache: Delta's FUNDING:<sym> hourly records and Binance's per-settlement funding,
  2024-10-01 → 2026-09-30.
- Coins: the C532/C533 set, i.e. Pi42 lists it, Delta turnover ≥ $100k, and the same asset (daily-return
  correlation ≥ 0.9). That is 52 coins.

**Engine: one settlement-level simulator for every variant, on an hourly clock.**
- **Funding:**
  - Delta pays at its exchange hours: every 1, 4 or 8 h, with C524's 30-day interval detection.
  - Binance/Pi42 pays at each recorded fundingTime.
  - A leg earns or pays each settlement it is held through.
  - 18% GST on any funding paid, applied per settlement, on both legs (as C532).
- **Signal at a decision time T:** the sum of (Delta − Binance) settlements in the 7×24 h before T,
  ÷ 7 × 365. It needs both venues' records over the window.
- **Costs per entry and per exit, both legs:**
  - Pi42 0.10% × 1.18 + 0.02%;
  - Delta 0.05% × 1.18 + 0.02%.
  - Run at ×1 (as quoted) **and** ×5 (round 15's "ALL harder").
- **Sizing:** $1,000 capital, whole Delta contracts at the day's price (as C533).
- **Price legs:** hedged, so they are left out of this comparison (the data is daily only). Their cost
  at each crossing is in the half-spread. Every variant gets the same treatment, so the comparison is
  fair; absolute levels read "rent − costs".

## Variants (each changes ONE thing from the baseline B0)

**B0, the live rule:** decisions daily at 00:30 UTC; 7-day window; enter 20%/yr; exit 10%/yr or sign
change; 10 pairs × 10%.

**Frequency** (the operator's question):

| | decisions |
|---|---|
| F8 | every 8 h, after each 00/08/16 UTC settlement (+30 min) |
| F4 | every 4 h |
| F1 | every hour |

**Exit:**

| | exit when |
|---|---|
| E0 | only on a sign change |
| E5 | under 5%/yr |
| E15 | under 15%/yr |

**Entry:**

| | enter at |
|---|---|
| N15 | 15%/yr |
| N30 | 30%/yr |

**Window:**

| | signal window |
|---|---|
| W3 | 3 days |
| W14 | 14 days |

**Spread:**

| | pairs |
|---|---|
| P15 | 15 pairs × 6.67% a leg (same gross) |

## The bar (a variant replaces the live rule only if ALL hold)

Comparing the variant's daily series with B0's (the paired difference):
1. Improvement ≥ **+3%/yr** of capital at costs ×1.
2. HAC t of the daily difference ≥ **2.5**. This is stricter than 2 because 11 variants are tried.
3. The difference is positive in **≥ 3 of the 4 half-years**, and in the last 6 months.
4. At costs ×5 the variant is still **≥ B0**.

If two or more variants pass, their combination is run once, as a confirmation, against the same bar
before anything changes. If none passes, the bot keeps B0.

## Also reported (descriptive, no bar)

- How often a pair's gap flips sign inside a day, and the rent lost waiting for the next daily run.
- The "base rent": the median gap across all coins and days. Is part of the gap structural (one venue's
  default interest component), so that it persists?
- Persistence: the correlation of the 7-day gap with the next 7 days', and a pair's median holding time.
- Settlement timing: does the 00:30 UTC run miss any settlement at entry or exit?
