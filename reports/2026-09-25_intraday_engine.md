# The intraday engine you asked for — 25 Sep 2026 (C489)

## The short answer

I built the intraday engine exactly on your principles:
- **relativistic:** every input is measured against the coin's own history or
  against the other coins;
- **predictive:** everything forecasts the next 4 hours;
- **a probability model** that is retrained as it goes (walk-forward);
- **chaos theory:** permutation entropy and the Hurst exponent;
- **Markov chains**, first and second order.

Then I tested it on 5 years of hourly data before letting it near your money.

**It loses money, and so does every intraday design I tried,** on crypto and on
Bitget's gold, oil, index and stock contracts. The reason is not the maths. It
is the fees.

So the new intraday engine **runs live in "shadow" mode:**
- it trades a paper account of its own, every hour, on the real market;
- it can never touch your money;
- the dashboard shows its honest record;
- if that record ever proves itself (4+ months, passing the same test as
  everything else), it is flagged **ELIGIBLE**.

Your money stays with the daily portfolio book (C488), the only engine that has
passed.

## What I tested

1. **Research:**
   - very fast patterns (15 minutes) are real but worth about 1.3 bp per trade,
     while one round trip costs about 16 bp;
   - so I tested hourly decisions held for 4 hours.
2. **The plan was written and committed before any test,** so nothing could be
   cherry-picked.
3. **Data:** every coin that has been in the top 60 since 2021 (383 coins,
   including ones that later died), hour by hour, with real funding.

## Results (Jul 2021 – Aug 2026)

| Idea | Profit before fees | After fees |
|---|---|---|
| 24-hour momentum | **+40% / yr** | −78% / yr |
| Markov chain (1st order) | **+20% / yr** | −196% / yr |
| Buy/sell pressure (order flow) | +12% / yr | −260% / yr |
| Chaos switch (Hurst / entropy) | +5% / yr | −265% / yr |
| Probability model (all 16 inputs) | +6% / yr | −100% / yr |
| Probability model, trading only when it's confident | +2% / yr | −6% / yr |

- **Some predictions are genuinely right.** 24-hour momentum made money before
  fees in every single year.
- **But an intraday engine trades its whole account 4–9 times a day,** and at
  Bitget's 0.06% fee per side plus the spread, that costs 100–270% a year.
- **The low-trading version also failed.** I tried a version that holds longer
  and trades less. Its best form was chosen on 2021–23 data, then tested once on
  2024–26 data it had never seen: it lost 121% a year there.
- **Using the signals to time the portfolio's daily trades** did no better than
  timing them at random.
- **Bitget's other contracts fail too.** I checked 24 of them (gold, silver,
  copper, platinum, palladium, oil, gas, S&P 500, Nasdaq, and 13 US stocks
  including Tesla, Nvidia and Apple). Every one loses after fees.

## Your 2–4% a month target

| Risk dial | Average month (2020–26) | Worst drop | Realistic going forward |
|---|---|---|---|
| 15% (now) | +2.5% | −31% | +1.5–2% |
| 20% (max) | +3.3% | −40% | +2–2.5% |

- **Only the daily portfolio book produces this return.**
- **4% a month isn't realistic** without drawdowns that would likely end the
  account.
- **Tax:** Indian crypto gains may be taxed at a flat 30% with no loss offset.
  Ask a CA; the treatment of futures is unsettled. After that tax, 2% a month
  becomes about 1.4%.
- **Bitget has paused new sign-ups in India;** existing accounts continue
  normally.

## What changed in the bot (C489)

- **New "Intraday engine (shadow)" panel on the dashboard:**
  - its two paper records (the model, and the confident-only model);
  - how many coins it scores;
  - its warm-up status.
- **It needs about 7 days to collect order-flow data** (Bitget only publishes
  the last 30 hours), then starts scoring.
- **Nothing else changed:** the portfolio book trades exactly as before.

## What to watch

- Check the shadow panel once a month.
- If either record ever shows **ELIGIBLE**, tell me and we'll review it before
  it trades real money.
- If it keeps falling, that's the market confirming the research.
