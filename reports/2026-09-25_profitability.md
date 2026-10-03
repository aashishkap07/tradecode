# Can OMEGA be made profitable? — 25 Sep 2026 (C487)

**Short answer: not by changing a setting.** Every trade since 19 Sep was checked
against Bitget's real 1-minute prices. The bot's entry picks carry no edge. Costs
(fees plus the spread) are about as large as everything it earns. The paper
account was also flattering it: it counted fills a real order would have missed,
and those missed fills were mostly the winners. C487 makes paper honest and makes
live mode safe. It does not make the strategy profitable, and nothing tested
here does.

## 📉 WHERE THE MONEY GOES — 164 trades, 19–25 Sep, against Bitget 1-minute candles

**1. The entries carry no edge; the exits are what keep it near zero.** Hold each
trade for a fixed time from its own entry price, in its own direction, before
any cost:

| hold | mean | median | up | t (day-clustered) |
|---|---|---|---|---|
| 5 min | +0.02% | +0.03% | 51% | +0.28 |
| 30 min | −0.22% | −0.24% | 46% | −1.28 |
| 1 h | −0.14% | −0.43% | 41% | −0.62 |
| 4 h | −0.41% | −0.68% | 41% | −0.80 |
| **the bot's own exits** | **−0.01%** after fees | | | |

No exit rule can turn a no-edge entry into a profitable trade. Every simple
alternative exit was replayed in C486, and none beat the actual exits in 3 of 4
splits.

**2. Costs decide the sign.** Over the 156 trades with a fee record:
- before costs: +$4.23;
- the exit spread: −$1.44 (117 taker exits at a median 3.9 bp);
- fees: −$2.98 (0.063% of notional per round trip);
- **net: −$0.20.**

The gross edge is about 3 bp per trade. The cheapest realistic round trip is
4 bp (maker both ways) and a taker round trip is 12–16 bp.

**3. Paper fills flattered the result by about its whole size.** A resting order
fills only when price comes back *through* it. Of the 164 entries, price came
back within 1 / 2 / 5 minutes for 63% / 75% / 82%. The ones it never came back
to were the winners:

| entry | n | win | net |
|---|---|---|---|
| price came back through it (a resting order fills) | 123 | 28% | **−$6.47** |
| price never came back (a resting order MISSES live) | 41 | 44% | **+$7.57** |

This is textbook adverse selection. C286's backward-looking check filled nearly
all of them. Only 26 of 43 maker exits would have filled within a minute.

**4. Realistic totals for the same 164 trades:**

| execution | total |
|---|---|
| paper, as booked | +$1.10 |
| resting entries, filled honestly | **−$6.66** |
| every entry crossing the spread (taker) | **−$3.28** |

Taker minus honest maker is +$3.38, t +0.72, 2 of 4 splits: **not separable.
Entries stay maker** (Rule 48: no switch without evidence).

**5. No logged entry reading predicts the outcome.** There were 92
feature × outcome tests; about 5 at |t|≈2 are expected by chance, and none reach
|t|≥3 on returns. Two readings run weakly *backwards*:
- the bot's own expected-profit estimates: S3_P ρ −0.17, t −2.14, 4/4; ev_p t −2.04;
- how far the coin had already run: moved_pct t −2.76.

The strong relations with MFE (target/stop/ATR, t≈+3.8) are volatility
artefacts: bigger ranges make bigger excursions both ways.

**6. Longer horizons, 5 years, 30 coins, pre-registered** (`omega_c487_edge_bench.py`).
Costs: 0.06% taker + 0.02% half-spread per unit turnover, plus 0.01%/8 h funding
on longs. Admitted only with ≥3/4 quarters positive AND |t| ≥ 2.

| strategy (daily bars) | net / yr | t | quarters + | max DD |
|---|---|---|---|---|
| trend blend 1/2/4/8 weeks | +16.3% | +1.69 | 3/4 | 22% |
| alts long while BTC > 50-day avg | +16.4% | +1.36 | 4/4 | 35% |
| 4-week trend | +15.7% | +1.32 | 3/4 | 30% |
| 1-week trend | +14.1% | +1.16 | 3/4 | 26% |
| 20/10-day breakout | +7.5% | +0.73 | 3/4 | 31% |
| cross-section 1-week momentum | −2.4% | −0.95 | 2/4 | 20% |
| cross-section 1-day reversal | −19.3% | −8.24 | 0/4 | 61% |
| buy & hold (reference) | −1.3% | −0.08 | 2/4 | 54% |

**Nothing is admitted.** The same ideas on 4-hour bars are worse. The 1-day trend
rebalanced every 4 hours makes **−40.9%/yr (t −3.23)**. The faster a
strategy trades, the more of it the costs eat. This bot holds for about 1 hour and
trades about 18 times a day, which is the most expensive corner of this table.
Survivorship bias (these are coins alive today) flatters the long-biased rows.

> **→ Standing Rule 50: A FILL IS A FACT ABOUT THE FUTURE.** Whether a resting
> order fills is decided by what the market does *after* it arrives. That is
> also when the fills that happen are the bad ones. Any simulator that answers
> from the past is not a simulator, and live code that does not read the order
> back is not trading.

---

## 🧭 WHAT IT MEANS (the operator's question, answered)

- **Do not go live with this engine.** Under realistic execution it loses:
  honest maker entries −$6.66 per 164 trades, taker entries −$3.28.
- **Lower the risk dial while it has no edge.** At 15%/month the permitted loss
  is $37.92 a month; 5% risks a third of that and changes nothing else.
- **Let C487 run for a week** so the paper record finally means what it says.
  `omega_c487_fill_bench.py` repeats this study on any new logs.
- **The only candidate that came close is slow trend-following** (days to weeks
  per trade, about 40 turns a year). It is a different kind of bot, not a setting
  in this one, and it did not pass the bar (t 1.69). Running it as a paper-only
  side book to gather out-of-sample evidence is an operator decision.

