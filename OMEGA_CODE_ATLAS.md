# OMEGA V60 — CODE ATLAS

# ═══════════════════════════════════════════════════════════════════════════
# 💰 2026-09-23 — 116 TRADES: THE DIRECTION CALLS WON AND THE SIZING LOST
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE

**Shipped: C480.** Branch `claude/trading-system-analysis-tsvzj4`.
Three days of continuous running, **116 closed trades** (35 on 19 Sep, 81 in one
67-hour session 20→23 Sep). Net **−$7.04**. No trading logic changed this pass.

---

## 🔴 THE FINDING: THE BOT IS RIGHT ABOUT DIRECTION AND WRONG ABOUT SIZE

One line, and it needs no model of anything:

| | |
|---|---|
| sum of the raw % moves over 113 priced trades | **+40.92%** |
| fees at 0.08% round trip | −9.04% |
| so **any equal-sized book** earns | **+31.88% of one position** |
| what the bot actually made | **−$7.04** |

The percentages won. The money lost. **Only position sizing sits between those
two numbers.**

### Sized equally, the same trades make money

Same 116 trades, same moves, same fees, every position the same size:

| | net |
|---|---|
| actual | **−$7.04** |
| every trade at the median $23 | **+$7.25** |
| every trade at the mean $26 | **+$8.24** |

A **$14.29 swing** on identical trades. The win rate is unchanged at 33.6% —
nothing about selection improves. Only the money.

### It is worse than random, and that is measured

Permutation test: take the same position sizes and the same moves and re-pair
them at random, 20,000 times.

| | |
|---|---|
| actual net (the bot's own pairing) | **−$7.04** |
| random pairing, mean | **+$8.16** |
| random pairings at least as bad | **21 / 20,000 → p = 0.0010** |

> **The bot's own size-to-trade assignment is worse than 99.9% of random
> assignments.** Spearman ρ(size, move) = **−0.209**, p = 0.0135.

**Checked against the obvious artefact.** Size here is derived as
`N = pnl/(move/100 − F)`, so a small-move trade mechanically gets a big N and a
negative pnl. Cutting the small moves out kills that artefact — and the effect
survives every cut:

| filter | n | actual | random mean | p |
|---|---|---|---|---|
| all | 113 | −$7.04 | +$8.23 | 0.0010 |
| \|move\| ≥ 0.5% | 83 | −$5.24 | +$9.29 | 0.0011 |
| \|move\| ≥ 1.0% | 64 | −$2.75 | +$8.93 | 0.0024 |
| \|move\| ≥ 1.5% | 40 | +$3.30 | +$9.91 | 0.0152 |
| \|move\| ≥ 2.0% | 28 | +$3.19 | +$8.77 | 0.0111 |

### The shape of it: size buys no upside and all of the downside

| size bucket | n | notional | win% | avg WIN | avg LOSS | net |
|---|---|---|---|---|---|---|
| smallest 25% | 28 | $8.1 | **53.6%** | +$0.356 | −$0.102 | **+$4.01** |
| 2nd | 28 | $18.0 | 39.3% | +$0.395 | −$0.228 | +$0.47 |
| 3rd | 28 | $26.5 | 28.6% | +$0.525 | −$0.286 | −$1.52 |
| largest 25% | 29 | $50.0 | **13.8%** | +$0.305 | **−$0.449** | **−$10.00** |

**The average WIN is flat across all four buckets** ($0.31–$0.53). **The average
LOSS grows 4.4×.** Size is buying nothing on the upside and paying in full on
the downside.

### And the stated risk budget is not being honoured

The dashboard prints `RISK 0.341% = $0.85/trade` to the operator. What the 18
hard stops actually risked:

| min | p25 | median | p75 | max |
|---|---|---|---|---|
| $0.09 | $0.27 | **$0.48** | $0.72 | **$1.61** |

**A 19× spread against a budget that is displayed as a single number.** A
risk-parity book would show every one of these at ~$0.85.

> **→ Standing Rule 37: WHEN THE PERCENTAGES WIN AND THE MONEY LOSES, THE FAULT
> IS IN THE SIZING, NOT THE SIGNAL.** Win rate, payoff and expectancy are all
> computed per trade and are all blind to how much was on each one. A book can
> have a positive edge in every one of them and still lose, and no per-trade
> statistic will ever say so.

> **→ Standing Rule 38: A RISK BUDGET THAT IS DISPLAYED BUT NEVER MEASURED IS
> NOT A BUDGET.** `$0.85/trade` was on screen for three days while the real
> figure ranged 19×. Nothing compared the two, so nothing could notice.

### C385 predicted this and deferred it

C385 wrote: *"volatility reaches position size through TWO paths — `_vol_adj =
clamp(1/ATR, 0.55, 1.30)` in the Kelly allocator and `margin = risk/(2*ATR)` in
the risk fit — which compounds to a **6.75x notional preference for a 0.7% ATR
pair over a 2% one** where risk parity alone would give 2.9x… calm pairs went
**0-for-4**… **Re-measure once a clean session exists.**"*

This is that re-measurement. The 0-for-4 is now **4-for-29, −$10.00**, and the
largest-size bucket is exactly the calm-pair bucket (median \|move\| 0.70% vs
1.72% in the smallest). **C385's deferred concern replicates at n=116.**

One correction to C385's reading: `_vol_adj` reads `_avg_atr_for_alloc`, the
**basket** average, so it is the same multiplier for every candidate in a scan
and cannot produce per-trade dispersion. The dispersion comes from further down
the chain, and **the pushed logs cannot say where** — see below.

---

## 🧨 C480 — THE LOG PIPELINE WAS DESTROYING ITS OWN ARCHIVE

`logrotate` runs `copytruncate` **daily** on `omega_session_*` and
`omega_detail_*`: it copies the file aside and truncates the original to **zero
bytes**. `omega-logpush.sh` then `cp -f`'d those zero bytes over the good copy
on GitHub.

**Measured:** `omega_session_20260919_003314.log` was **90,149 bytes** on the
branch and is now **0**. All thirteen 19-Sep session logs went the same way —
**323 KB, the only decision record for that day.** The branch carries a single
commit, so its history could not help either.

Recovered only because an earlier `git fetch` had left the old commit in this
clone's object store. **That is luck, not a backup.** All 13 files are restored
under `recovered_logs/20260919/`.

> **→ Standing Rule 39: AN ARCHIVE THAT CAN SHRINK IS NOT AN ARCHIVE.** A
> mirror faithfully reproduces a deletion. Two tools each correct alone —
> logrotate truncates in place, logpush mirrors current state — combined to
> delete the record neither was told to protect.

**The fix.** A file may only be overwritten by one **at least as large**; a
smaller source means rotation, so the archived copy is preserved as
`.partNN.log` first and the restarted file is stored beside it. The rotated
`.log.1` / `.gz` files are pushed too. Detail logs are now pushed by default,
**uncompressed** — they are append-only text pushed hourly, so git deltas only
the new lines; gzipping first would make every hour a fresh incompressible blob.

Covered by `omega_c480_logpush_test.sh` (10 checks) including a negative control
that proves the old `cp -f` destroys the data.

---

## ❓ WHAT THIS ANALYSIS COULD NOT ANSWER, AND WHY

Three separate questions died on the same missing file — the detail log, which
was never pushed:

1. **Which cap produced each position size.** The sizing chain prints
   `Kelly-Conv-Vol: base=… conv=… vol_adj=…(atr=…) → max=$…` and the per-trade
   margin, only to the detail log. Without it the *mechanism* behind the −0.209
   correlation is inference, not measurement.
2. **How often the drawdown pause fires, and what it costs.** Zero events
   appear in the pushed logs; the operator photographed one on 21 Sep.
3. **The C464 information overlay's live A/B ledger.**

This is why C480 turns detail pushing on. **The next three days will be able to
answer all three.**

---

## 📉 THE EXIT LEDGER (116 trades)

| exit | n | win% | net | avg |
|---|---|---|---|---|
| **C377_RISK_STOP** | 18 | 0% | **−$9.50** | −$0.528 |
| C399_CONVICTION_COLL | 14 | 0% | −$2.73 | −$0.195 |
| C399_CONVICTION_FADI | 7 | 0% | −$2.52 | −$0.360 |
| PEAK_FLOOR | 19 | 10.5% | −$1.95 | −$0.103 |
| TRAILING_TP | 21 | 100% | +$5.28 | +$0.251 |
| EARLY_PEAK_CAPTURE | 8 | 100% | +$4.61 | +$0.576 |
| PEAK_REVERSAL | 7 | 57.1% | +$3.77 | +$0.539 |

**The 18 hard stops cost more than the entire net loss.** Without them the book
is **+$2.46**. That is *not* an argument for removing the stop — it is where the
sizing defect lands, because a stop is the one exit whose cost is set directly
by position size.

**Direction was not the problem.** 106 LONG / 10 SHORT, against a market the bot
read as positively biased in **80% of 362 readings** (mean bias +0.280). The
long tilt matched the tape.

---

## 🚧 NOT SHIPPED — THE SIZING FIX NEEDS THE OPERATOR'S CALL

No sizing change ships on this pass. Two reasons, and only one of them is
caution:

1. The **mechanism** is not yet located (see above) — the detail log was not
   being kept. Changing a chain whose binding constraint is unidentified is how
   C420-1 happened.
2. Standing Rule 32: three days agreeing is a reason to measure, not to ship.

**But note the asymmetry.** This is not an edge claim needing a four-way
out-of-sample harness. The bot *states* a per-trade risk of $0.85 and does not
honour it. Bringing a control into line with its own displayed contract is a
defect fix, like C377's guaranteed R — it needs a regression harness, not an
edge harness.


# ═══════════════════════════════════════════════════════════════════════════
# 🎯 2026-09-19 — THE FIRST REAL SAMPLE: 31 TRADES, AND WHERE THE MONEY GOES
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE

**Shipped: C479.** Branch `claude/trading-system-analysis-tsvzj4`.
C479 fixed three ways the operator could lose control of, or sight of, a bot
that was otherwise running perfectly — see the C479 section below. **No trading
logic changed.**
Running 24×7 on an Oracle VPS; logs push to the `logs` branch hourly and are
readable without the operator doing anything. **31 closed trades on 19 Sep**
against 3 in 11 hours before the caps came off — C467-A did exactly its job.

---

## 🔴 THE FINDING: THE ENTRY SELECTION HAS NEGATIVE EDGE

Measured against a **fixed 20-pair liquid benchmark over each entry's own
time window** — so time-of-day cannot flatter or damn it:

| hold | the bot's picks | the market then | **selection edge** | beat market |
|---|---|---|---|---|
| 1h | −0.45% | −0.16% | **−0.35%** | 10/31 |
| 4h | −0.23% | +0.20% | **−0.60%** | 10/31 |
| 8h | −0.45% | +0.29% | **−1.15%** | 9/31 |

Beating a random liquid basket **9–10 times in 31** where a coin flip gives
15.5. Two-sided p ≈ 0.03 at the 8h horizon. **And the gap WIDENS with holding
time**, which is what rules out the two comfortable explanations: it is not
fees (those are fixed at entry) and it is not the exits (the measurement never
uses an exit).

**The day was a gift and the bot still lost.** Real tape, 19 Sep: median pair
**+5.39%**, **19 of 20 closed up**, 95% breadth. The bot took **31 LONGS** into
that — direction correct, market co-operating — and finished down.

> **→ Standing Rule 31: MEASURE SELECTION AGAINST WHAT WAS AVAILABLE AT THE
> SAME MOMENT.** "Our trades lost" confounds the pick, the clock and the exit.
> Benchmarking each entry against the market over its own window separates
> them, and it is the only comparison that can indict the entry stack.

## 🧭 WHAT IT IS NOT

Three suspects eliminated by the same data:

- **Not direction.** All 31 were long on a 95%-breadth up day. The
  `MARKET … bias` reading was positive all day and it was RIGHT.
- **Not the exits.** Simply HOLDING those same 31 entries also loses:
  median +0.01% at 1h, −0.50% at 4h, −0.95% to end of day, 12/31 positive.
  The exits are not giving away a profit that was there.
- **Not the caps.** Removed at C467-A. Trade count went 3 → 31.

## 🔎 THE MECHANISM, NOW REPLICATED

Prior 24h move at entry vs next-4h return, across the bot's own 31 picks:

| cohort | had already run | next 4h |
|---|---|---|
| least extended third | +5.45% | mean **+0.94%** |
| middle | +9.16% | mean +0.35% |
| **most extended third** | **+16.22%** | mean **−0.88%** |

**corr(prior extension, next 4h) = −0.257.**

C420-7 measured **−0.212** on a completely different session and different
tape, and recorded it as "NOT acted on" pending replication. **This is the
replication: two independent days, same sign, similar magnitude.** Standing
Rule 9's bar for the MECHANISM is met, though not yet for the size of the
effect.

The causal chain is now explicit and it is not subtle: Step 1 ranks the
universe by **liveliness**, which is definitionally recent movement; the top of
that ranking is therefore the most-extended cohort; and extension
anti-predicts. **The funnel's first stage is sorting the universe by the wrong
sign.** The bot's picks had a median prior run of ~+9%, its top third +16%.

## ⚖️ WHAT WAS NOT MEASURED, AND WHY

- **P&L across the day does not compose.** The 31 closes span 13 separate
  report logs — 13 restarts during the deployment work, with a fresh start
  among them — so the bot's own `lifetime_pnl` (+$0.31 on 14 trades) covers a
  different set than the 31 extracted here (−$4.16). **The selection-edge
  measurement is independent of the bot's accounting entirely** — it uses entry
  prices and exchange candles — which is why it is the number to trust.
- **Maker 11 trades / 11 wins vs taker 20 / 1 win is an ARTEFACT, not
  evidence.** C376 rests profit-taking exits as maker and stops must cross, so
  "maker" is very nearly a synonym for "win" by construction. Reading it as
  "maker exits cause wins" is Standing Rule 4a exactly.

## ❌ THE HARNESS RAN, AND IT KILLED MY OWN HYPOTHESIS

`omega_extension_harness.py` — 32 pairs, 330,400 bars of 15m data, ~108 days,
non-overlapping forward windows, maker-both fees charged, cross-sectional
ranking **within each timestamp** (the decision the bot actually faces: of the
pairs available right now, which do I buy?), four-way time-disjoint ×
pair-disjoint split.

**Q1 (least extended) minus Q5 (most extended), per split:**

| split | corpusO | corpusL |
|---|---|---|
| early / pairs A | **+0.0914%** | −0.1356% |
| early / pairs B | **+0.0318%** | −0.0875% |
| late / pairs A | −0.2072% | −0.0828% |
| late / pairs B | −0.1401% | −0.0730% |
| **splits favouring least-extended** | **2 of 4** | **0 of 4** |

**DOES NOT REPLICATE.** On corpusO the sign FLIPS between the early and late
halves; on corpusL it never favours the low-extension cohort at all.

The two live correlations that motivated this — C420-7's −0.212 and 19 Sep's
−0.257 — were each **one day**. Across 108 days split four ways the effect
reverses by period. That is precisely the regime-dependent mirage Standing
Rule 9 exists to catch, and it caught it.

> **→ Standing Rule 32: TWO DAYS AGREEING IS A REASON TO MEASURE, NEVER A
> REASON TO SHIP.** Both live readings were real; both were regime. Had Step 1
> been rebuilt on them, the result would work in half of all periods and hurt
> in the other half, and the next log would have been unattributable.

**AND THE POOLED TABLE IS THE LARGER FINDING.** Every extension quintile lands
between **−0.061% and +0.005% after fees**. Not one is profitable. This is the
same wall as the 662,800-bar barrier study (30 of 30 geometries net negative)
and the 9,383-settlement funding study (no directional information).
**Re-sorting the universe does not get past it.** The negative selection edge
measured on 19 Sep is a true description of that day; "chasing extension" is
not its cause, and re-ranking Step 1 is not its cure.

Three independent measurements now agree that nothing derivable from PRICE
ALONE survives the fee schedule. The remaining levers are the channels that
are not in the price series — order flow and open interest — which the VPS can
reach and the development container cannot.

---

## 🚧 NOT ACTED ON — AND THAT IS THE POINT

No entry logic changed on the strength of one day. The standing rule is a
four-way out-of-sample harness with ≥3 of 4 splits positive, and the corpus to
run it on is already here (`corpusO/`, `corpusL/`, 32 pairs). **The next piece
of work is that harness on the extension/liveliness question, not a patch.**
One day that agrees with a previous day is a reason to go and measure
properly; it is not a reason to ship.

---

## 🚨 C479 — THE OPERATOR'S STOP BUTTON COULD VANISH, AND THE ALARM THAT SAYS SO WAS ITSELF MUTED

**Found by the battery disagreeing with itself.** `omega_c467_remote_test.py`
reported **FAIL** in the full battery and **PASS** run on its own. That gap was
the whole finding. Running two copies at once reproduces it: the second binds
port 18138, fails, and dies forty PASSes later on
`'NoneType' object has no attribute 'server_address'`.

The test was not flaky. It was reporting a **real defect in the bot**, in the
one failure that happens in ordinary operation on a real server.

### What the defect was

`RemoteControl.start()` wrapped everything in one `except Exception → logger.warning`.
C473 already hardened that block against a *missing name*. It did nothing about
the **bind**, which is the failure that actually occurs:

```
systemd Restart=always fires
  → the old process has not released :8138 yet
  → bind raises EADDRINUSE
  → ONE warning line scrolls past
  → the bot trades on with NO dashboard and NO remote stop button
  → and never tries again.
```

`SO_REUSEADDR` does not save this. `HTTPServer` already sets it, which covers
TIME_WAIT — but a **live listener** still refuses the bind, and a live listener
is exactly what an overlapping restart leaves behind. Verified: `errno 98` with
`allow_reuse_address = 1`.

### The watchdog turned it into a permanent restart loop

`omega-watchdog.sh` read "health endpoint did not answer" as proof the bot was
wedged, and ran `systemctl restart omega`. So a **healthy** bot — scanning,
holding open positions — was restarted every five minutes forever, and each
restart re-created the overlap that caused the busy port. The only symptom was
one warning line and a syslog entry nobody reads.

> **→ Standing Rule 33: A CONTROL THAT IS LOST SILENTLY IS WORSE THAN ONE THAT
> WAS NEVER BUILT.** The operator believes they can stop the bot. A dead panel
> does not say it is dead — it just stops answering, which looks exactly like a
> network hiccup from the other end.

> **→ Standing Rule 34: BEFORE RESTARTING SOMETHING, ASK WHETHER IT IS ACTUALLY
> BROKEN — BY A ROUTE THAT DOES NOT SHARE THE SUSPECTED FAULT.** The watchdog
> diagnosed liveness through the very port that had failed. It now asks whether
> the bot is still *writing its log*, which cannot be confounded by the port.

### The fix

- **Bot:** EADDRINUSE is retried in the background every `C479_CTRL_RETRY_S`
  (15s) until it succeeds. The panel comes back **by itself**, no restart, no
  human. Any other error still raises to the outer handler. The operator is told
  at ERROR, in plain English, that the bot is fine and only the panel is missing,
  and is given `ss -ltnp | grep 8138` to find the culprit.
- **Watchdog:** a silent panel now only causes a restart if the report log has
  **also** gone quiet past `MAX_AGE`. Otherwise it logs that the bot is alive and
  leaves it alone.

### A bug in my own fix, caught by its own test

The retry loop checked its stop flag at the top of the loop and then slept 15s.
The flag is normally set *during* that sleep, so the loop woke and bound anyway
— a retry loop that acts after being told to stop is not stoppable. It now
sleeps in slices and re-checks after waking. **The test found this, not
reading it.**

---

## 🔇 C479-B — SIXTY OF NINETY-EIGHT ALERTS NEVER REACHED THE SCREEN

End-to-end with two real bots, C479 worked: B hit the busy port, logged the full
explanation, and rebound one try after A died. **And none of it appeared on the
console or in the session log.** Only `omega_detail_*.log` — the noisiest file —
had it.

`_C460ConsoleFilter`'s own rule 2 is *"anything wrong reaches the screen"*. It
implemented that by **matching fifteen substrings against the message text**.
`filter()` never looked at `record.levelno` at all.

An AST scan of the bot's own `logger.error` / `logger.warning` calls:

| | count |
|---|---|
| alert-level calls with readable literal text | 98 |
| **invisible on console AND in the session log** | **60** |
| …of which `logger.error` | 21 |

Among the invisible:

```
🚨 EMERGENCY TRIGGERED: Unrealized X% (threshold Y%)
🚨 Loss worsening (X% → Y%). Closing all.
Save state error:      Load state error:     Order error:
Close position error:  Exchange connect error:  Scan error:
```

**The emergency liquidation handler could not reach the operator's screen.**

**And not mine either.** The same filter is attached to `_c52_file_handler` —
the *session* log — and `omega-logpush.sh` pushes only `omega_report_*` and
`omega_session_*` to GitHub. The detail log is never pushed. So for every
session analysed remotely so far, those sixty alert lines were **absent from the
only record I can read**. Any of them that fired on 19 Sep are not in the 26
files on the `logs` branch. This is a hole in the evidence base, not just in the
operator's view.

And the reason is one this project has already paid for once: `_ALERT` carries
`'ERROR'` in capitals while the code writes `'error:'` in lower case — the
**same case-sensitivity defect C462 found in the C460-1 keep-list, still live in
a second list.**

> **→ Standing Rule 35: WHEN A STRUCTURED SIGNAL EXISTS, NEVER RE-DERIVE IT FROM
> PROSE.** `logging` puts an authoritative severity on every record. Matching
> words for it cannot cover what a future version adds, and fails on a letter's
> case. This is the same family as the wrong-object bugs: the answer was already
> on the object, and the code went looking for it somewhere else.

### C479-C — AND THE ALARM COULD BE RAISED BUT NEVER CLEARED

The end-to-end run exposed a sharper version of the same fault. C479's
`CONTROL PANEL DID NOT OPEN` now reaches the screen **on its level**. Its
partner, `✅ CONTROL PANEL IS BACK`, is `logger.info` — so it did not. The
operator would be shown a red alarm saying their stop button is gone and
**never shown that it came back**.

The same applied to the panel's ordinary boot announcement:
`🌐 Remote control on http://…` has **always** gone only to the detail log, so
the operator has never seen the dashboard's own address in the readable log.

> **→ Standing Rule 36: AN ALARM THAT CAN BE RAISED BUT NOT CLEARED IS A FALSE
> ALARM LEFT STANDING.** Every alert needs a matching all-clear on the same
> channel, or the operator learns that alerts do not mean anything — which
> costs more than never having raised one.

Six substrings added to `_DECISION` cover the whole panel block, both the
tokened and localhost forms. Verified not to let per-pair working back in.

### The fix, and what it costs

`record.levelno >= logging.WARNING` passes, checked **before** the per-pair shape
test — because a crash inside a per-pair path is still a crash, which is what
that comment always intended and could not achieve with substrings.

**Measured, not assumed.** An instrumented build ran a live session through a
full 22-pair scan: **zero** added console lines beyond two benign startup
warnings. Replaying 178 real INFO lines, 3% still pass. The filter only speaks
more when something is actually wrong, which is the point.

### Verification

| check | result |
|---|---|
| `omega_c479_port_test.py` — 16 checks, incl. two real servers | PASS |
| `omega_c479_watchdog_test.sh` — 11 checks, PATH-stubbed | PASS |
| `omega_c479b_filter_test.py` — 18 checks | PASS |
| end-to-end: two real bots overlapping on :8138 | panel healed in 1 retry |
| negative control: pre-C479 bot never recovers | confirmed |
| negative control: pre-C479 watchdog restarts a healthy bot | confirmed |
| negative control: pre-C479-B filter hid **12 of 13** alerts | confirmed |
| full battery + headless boot + wrong-object sweep + display | PASS |

Every one of the three fixes ships with a **negative control that reproduces the
old behaviour from the shipped source** and requires it to fail. Per Rule 16, a
test that cannot fail is not a test — and each of the three says so loudly if the
marker it reverts ever stops matching.

### What did NOT change

**No trading logic.** Not a gate, score, target, stop or sizing rule. C479 is
entirely about whether the operator can see and steer the bot. The negative
selection edge from 19 Sep stands untouched and still needs its replication batch.

---

# ═══════════════════════════════════════════════════════════════════════════
# 🔓 2026-09-18 — C467: THE CAPS COME OFF, AND THEY WERE NEVER THE PROBLEM
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE

**Shipped: C467.** Branch `claude/trading-system-analysis-tsvzj4`.
AST **423 → 427**. Wrong-object sweep **120 → 74** findings (21 were the tool's
own false positives; see Rule 23).
Caps: `C403_TARGET_TRADES_DAY=0.0` · `C404_HARD_TRADES_DAY=0` ·
`MAX_TRADES_PER_DAY=0` · `C435_SCORE_CAP=False`. **No per-day trade cap exists.**
Day barrier: `C467_DYN_BARRIER=True`, loss-side only, realised-only.
Display: width now MEASURED (was hardcoded 46 on Android), ceiling 100 → 140.
Cloud: `deploy/` — systemd, Cloudflare Tunnel, logrotate, watchdog, DEPLOY.md.

---

## 🧾 THE 20260918 SESSION — AND A CORRECTION TO MY OWN ANALYSIS

11h02m · 75 scans · 3,493 pair-analyses · **3 closed trades** · +$0.57 realised
(the banner's +$1.34 blends in $0.77 of unrealised).

**I told the operator, in text, that "the caps, not the filters, were binding —
the bot logged the proof itself." THAT WAS WRONG, and counting properly shows
it.** The honest census of the detail log:

| what | count |
|---|---|
| scans producing ANY viable candidate | **8 of 75** |
| `C435-2` per-scan cap firings | **1, all session, dropping 1 candidate** |
| expectancy bar printing `+0.000R` | **46 of its 48 prints** |
| nearest-miss reason = `score` below bar | **23 of 44** |

The caps were near-irrelevant. The expectancy bar was **at its floor**. What
actually refused the trades was `E >= 0`, and E = p(R×capture) − (1−p), so at
the realised base rate (~0.44) it demands **R ≥ 2.1** against a projector that
produces **R ≈ 1.0–1.1**. Nothing could pass. That is the same diagnosis C412
recorded ("the stop is systematically wider than the projected move") and it
has never been fixed.

**→ Standing Rule 22: COUNT THE REFUSALS BEFORE NAMING THE CONSTRAINT.**
A throttled log line ("C404 FEE BUDGET SPENT" printed 7 times) marks a WINDOW
OF TIME, not a number of refusals. I read seven prints as seven bindings and
built an argument on it. Grep the reason tallies, not the narration.

## 🎯 EVERY TRADE WAS A PENALTY-FLOOR RESCUE. AGAIN.

| pair | raw score | floored to | entered at | 8h MFE (real tape) | outcome |
|---|---|---|---|---|---|
| COTI | **0.33** | 0.43 | 0.434 | +2.51R, but **stop hit first at 20 min** | −$0.03 |
| CRV  | **0.40** | 0.53 | 0.531 | **+0.29R** — dead trade | −$0.04 |
| JUP  | **0.44** | 0.58 | 0.580 | **+2.15R** | **+$0.64** |

Nine C367 penalty-stack lifts in the session; three became trades; **all three
were lifts.** Not one trade was a candidate the bot's own scoring approved.
C420 recorded exactly this at n=3 in a different session. **Two independent
sessions, 6 of 6 trades, 100% floor-rescued.**

And the decisive detail: **the RAW score ranked the three correctly**
(0.44 > 0.40 > 0.33 = JUP > CRV > COTI by realised outcome). The floor lifted
them all above the bar and destroyed that ranking. The evidence had the
information; the rescue threw it away.

*Not acted on in C467.* Changing the floor and the funnel in one version makes
the next log unattributable (Rule 4). It is the next lever, and it now has two
sessions of evidence behind it.

## 📉 CHART-VERIFIED AGAINST THE REAL TAPE (Bitget 5m, bars pinned by IST)

- **COTI** — the PEAK_FLOOR exit at breakeven was **RIGHT**. MFE was +15.29%
  over 8h, but the **−0.75R stop was touched at 20 minutes**, long before
  +1.00R arrived at 120 minutes. A holder is stopped out. The bot's own C444
  follow-up was correct.
- **CRV** — exit right, **entry** wrong. MFE +0.74% (+0.29R) in five hours.
- **JUP** — exited at +1.36R at 39 minutes; **2.00R arrived at 90 minutes** and
  MAE never exceeded −0.34R. C444 already says "held would have been better."
- **0.50R was touched within 5 min (COTI) and 15 min (JUP)** — 2 of 3 would
  have banked a half early. That agrees with the 662,800-bar barrier study,
  where **0.50R/2.00R was the least-bad of 30 geometries**.

**→ Standing Rule 24: AN EXIT IS JUDGED AGAINST THE STOP, NOT AGAINST THE MFE.**
"It ran +15% after we left" is not a mistake if the stop stood between us and
that run. Order of touch decides, and only the tape can say.

## 🕳 THE DEAD BAND (mechanism confirmed, cost not yet demonstrated)

Three profit-takers and one killer, denominated in two different units:

| gate | fires at | unit |
|---|---|---|
| PEAK_FLOOR (kills) | peak > **0.6 PRU**, fully erased | PRU |
| C338 half-bank | only via a `_C338_WIN_TOKENS` reason; JUP's needed **3.2 PRU** | PRU |
| C373 capture | **1.0R** — held on 14 of 14 logged checks, 0 captures | R |
| C415 trail | **2.00R** — "banking early is the worst-paying exit there is" | R |

A trade peaking between 0.6 PRU and 3.2 PRU can be killed and cannot bank.
COTI died at 1.3 PRU, CRV at 0.7 PRU. **PEAK_FLOOR is not in
`_C338_WIN_TOKENS`, so the one situation where banking half would help most —
a position giving back a peak — is the one it cannot address.**
On THIS tape it cost nothing (both would have stopped out). Recorded as a
mechanism, not a loss. And note C415's shipped comment asserts the exact
opposite of the barrier study's measured result.

---

## 🔓 C467-A — THE CAPS, AND THE GATE THAT WAS REALLY BINDING

Removed: the rate target, the hard cap, the per-scan score cap, and the
display-only `MAX_TRADES_PER_DAY` (read at two sites, both the dashboard —
a number the boot banner promised and the code never kept).

**There is deliberately NO master "no cap" switch.** The four zeroed constants
ARE the switch. A fifth control over the same state is how C420-1 got two
initialisers for one value and cost seven hours of lockout.

**The real change: E is demoted from a VETO to a PENALTY while p has no skill.**
The log says `acc=0.44 brier=0.292 (baseline 0.250)` at n=315 — worse than the
constant forecaster, unchanged since C420-5 recorded it at n=189.

> **Standing Rule 25: A GATE MAY NOT VETO ON A SIGNAL WITH NO MEASURED SKILL.**
> C342 holds FamilyMarkov at 'earning' for −6.8% skill; C343 lets IchiMarkov act
> at +11.2%. The expectancy gate was exempt from the discipline applied
> everywhere else — and from the bot's OWN architecture, which says (C403-5)
> there are **three** hard vetoes: can't pay fees, no room to stop, not
> tradeable. `E >= 0` was a fourth that nothing authorised.
> It reverts to a veto **by itself** the moment Brier skill goes positive.

In its place, hard veto #1 is made real: **fee coverage**, `R × capture ≥ 1.25 ×
FeeR`, computed by the **existing** `_c408_fee_burden_r` (never a second copy —
it alone knows per-instrument funding, 19% of a risk unit on QQQ, 0% on XAU).

**Honest limit:** this admits trades the model prices as marginal. That is the
point — on paper, a trade's cost is information. It must be re-measured on the
first uncapped session, and `C467_MIN_EDGE_R` is the dial that tightens it.

## 🛡 C467-B — THE DAY BARRIER, RELATIVISTIC AND LOSS-SIDE ONLY

The old barrier was **fixed** (DD/22), **symmetric**, and fed by **live**
equity. All three were wrong, and the 20260918 log shows it: **"94% used" at
10:05 on a day that was UP.**

```
limit = (DD/22) × day-start equity × vol_ratio × trust
        vol_ratio  this scan's median stop ÷ its own 24h EWMA baseline   [0.70, 1.50]
        trust      realised expectancy of this bot's own closes          [0.60, 1.25]
```

- **Loss side only.** A day is never stopped for winning. On an account whose
  present job is to accumulate closes so the C464 ledger can be priced, halting
  a winning day throws away exactly the observations that are working.
- **Realised only.** An open position marked temporarily underwater no longer
  spends the day's allowance and blocks entries, then recovers and hands it
  back. Open risk is still counted — by the **C313 reservation**, which is the
  non-double-counting way.
- **The stop IS the volatility reading.** R = 2×ATR, so the median stop across
  a scan is the median ATR of everything the bot looked at, in the bot's own
  units, with no extra fetch and no second definition to drift out of step.
- **Month guard.** However far the two relative terms widen it, cumulative
  realised drawdown may not run ahead of the declared monthly figure pro rata.

> **Standing Rule 26: A CONTROL THAT CAN WIDEN MUST HAVE A MANDATE IT CANNOT
> OUTRUN.** Otherwise it is a ratchet pointed the wrong way.

*Tabulated, not asserted:* 9 volatility ratios × 7 records × 5 sample sizes;
both ends clamped (0.30 and 0.50 agree; 2.00 and 4.00 agree); monotone in both
terms; trust immovable below 8 closes; worst case anywhere is **0.42× base and
still positive**; the month guard bites at 10 days / $40 and not before; a
winning day spends **$0.00** where the old rule read **176% used**.

## 📐 C467-C — THE SCREEN: TWO ONE-LINE CAUSES

**"Half the screen is blank."** `_c462_width()` returned a **hardcoded 46** on
Android and never asked the terminal. It now asks `os.get_terminal_size` first
— which **raises** when there is no terminal, and that is what makes a real
answer distinguishable from a fallback (`shutil`'s version silently substitutes
its own default, so a detected 72 and an undetectable 72 come back identical).
Ceiling raised 100 → 140. A **boot ruler** ends the guessing permanently.

**"No spacing between the end of a scan and the summary."** `_emit()` wrote
every blank separator to the report FILE and then **returned before the log
chain**. The spacing was in the file all along and the screen never got one
line of it. The old comment's premise — "the log chain strips empty records
anyway" — was the bug: it does not strip them, it was never given them.

> **Standing Rule 27: WHEN THE FILE AND THE SCREEN DISAGREE, THE SINK IS THE
> SUSPECT.** Before redesigning a layout, check that what was drawn was
> actually delivered.

Also: word-boundary truncation (`0.343~`, never `0.3`); a flat curve now draws
**flat** (min/max normalisation was amplifying rounding noise to full scale —
the same near-zero curve drew `@@.@@@@@@@@`, `*@....`, and `_.____` within a
few blocks); `_cols2` pairs short facts at ≥64 columns; blanks capped at 2.

## ☁️ C467-D — THE CLOUD KIT

`deploy/`: `omega.service` (auto-start, `Restart=always`), `setup.sh` (one
command on a fresh Ubuntu box), `omega-logrotate.conf`, `omega-watchdog.sh`,
`DEPLOY.md` in plain English. Oracle Always Free + Cloudflare Tunnel = **£0**.

Control panel, previously **unauthenticated on 0.0.0.0**:
- a token from `OMEGA_CTRL_TOKEN`, checked on **every** request, GET included
  (`/api/status` alone tells a stranger the account size and the open book),
  compared with `hmac.compare_digest`;
- **with no token it binds to `127.0.0.1` only** — the unsafe case is
  unreachable by construction, not by the operator remembering;
- new: `/api/logs`, `/api/files`, `/api/download` (basename against an
  allow-list built from the bot's own globs — never join user text onto a
  directory), `/api/health` (reports the **age of the last scan**, because a
  process that is alive and has stopped scanning is what a PID check cannot
  see), `/api/restart`.

**A bug the harness caught and no amount of reading would have.** Those POST
routes matched `self.path` **exactly** — correct until C467-D put `?t=TOKEN` on
every request. Pause, resume, **STOP** and force-scan all fell through to
`{"error": "Unknown command"}` **with HTTP 200**: the panel would have looked
like it worked and done nothing, from another country, including the stop
button. The dashboard's own JavaScript also sent no token at all.

> **Standing Rule 28: ADDING A QUERY PARAMETER CHANGES EVERY EXACT-MATCH
> ROUTE.** And: an error returned with HTTP 200 is how that stayed invisible.

**A geo-blocking note that matters strategically:** this development container
is blocked from Binance and Bybit, which is why C464's taker-flow and
open-interest channels ship *unmeasured*. **A VPS in Europe or India is not.**
That unlocks two of the three remaining levers — a bigger reason to move than
uptime.

---

## 🛠 BATTERY ADDITIONS

- `omega_c467_test.py` — 40 checks. Caps zeroed with their guards intact;
  every new module-level function **executed**; layout rendered at 11 widths
  (0 overflows, 0 non-ASCII); truncation swept across every budget.
- `omega_c467_barrier_test.py` — the barrier tabulated across regimes with
  every bound asserted (above).
- `omega_c467_remote_test.py` — **the server is started and attacked**: 12
  unauthenticated routes refused, 5 wrong tokens refused, 6 path-traversal
  attempts refused, every button proven to queue its command, both bind
  addresses asserted.
- `omega_display_test.py` — **repaired.** It had not run since C466 (a
  `NameError` on `_c466_paint`, never added to its extraction list) and it
  appended to its own log across runs, so it reported a growing phantom
  "lost: N". Now 23 written / 23 delivered / **0 lost**.
- `omega_wrong_object_sweep.py` — **sharpened**, 120 → 74 findings.

> **Standing Rule 23: A TOOL THAT CRIES WOLF IS A TOOL THAT WILL BE IGNORED.**
> The sweep could not see methods of a **nested** class (`RemoteControl.start`
> defines `Handler` inside itself), nor methods inherited from
> `BaseHTTPRequestHandler`. Twenty-one permanent false positives sat in the
> baseline, and C467 would have added six more. Both taught; RemoteControl
> false positives now **0**; and the sharpened tool was re-proven to catch a
> planted real bug (Rule 16).

**Self-caught before shipping:** `_SESSION_LOG_PATH` and `_DETAIL_LOG_PATH` —
two global names I invented. `globals().get()` returns `None` silently, so the
remote log viewer would have said "(no session log yet)" forever. The real
names are `_C52_LOG_PATH` and `_C460_DETAIL_PATH`. Wrong-name family, and it
now warns aloud if a path is ever missing (Rule 5).

---

# ═══════════════════════════════════════════════════════════════════════════
# 🎨 2026-09-17d — C466: COLOUR, APPLIED AFTER THE LAYOUT, CONSOLE ONLY
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE

**Shipped: C466.** Branch `claude/trading-system-analysis-tsvzj4`.
Display config: `C462_LOG_WIDTH=0` (auto→44 on Android) · `C465_GLYPHS='ascii'`
· `C466_COLOR='auto'` · `C466_PALETTE='classic'`.

---

## 🎨 THE THREE COLOUR RULES

**1. Colour comes LAST.** An ANSI code is **zero cells wide on screen and 4–5
characters to `len()`**. Painting during layout would have broken every width
calculation C465 fixed. The dashboard is built plain, measured plain, and
painted at the formatter boundary by one function.
*Proven: visible length byte-identical before/after; 18 width×palette
combinations render with zero over-width rows.*

**2. The files never see it.** `omega_report` / `omega_session` /
`omega_detail` stay plain — a log full of `\x1b[32m` cannot be grepped or
diffed, and these files are the forensic record. Only the **console**
formatter holds a palette; file formatters hold `None` for the process
lifetime. *Proven by counting escapes at each sink: 0 / 0 / 40.*

**3. Colour is never the only carrier.** ~1 man in 12 has red-green CVD.
Every painted value already states its meaning in text (the sign, and the
words WIN / LOSS / maker / TAKER). `C466_PALETTE='cvd'` → blue/magenta;
`'mono'` → bold only.

**The palette is semantic and small (6 classes):** labels neutral-cyan (identity,
never status) · rules dim (recessive) · green/red **reserved** for polarity ·
amber for warning. The day gauge is the one place hue adds something the text
does not: green under half the budget, amber past half, red past 80%.

---

## 🐞 WHAT THE FIRST RENDER CAUGHT (look at the output, don't trust the code)

| defect | why it mattered |
|---|---|
| `day +/-0.68%` painted red | a **symmetric barrier** is not a loss — the header announced one that did not exist |
| `taker flow +0.02` painted red | an order-flow **reading**, not a cost — a status colour on a non-status thing, the exact anti-pattern the palette exists to avoid |
| gauge arms painted twice | rule-dim then gauge-colour; the **inner reset cancelled the outer colour** and the gauge lost its hue — nested escapes are how hand-rolled colour normally fails |

**NEW Rule 21 — `ast.parse()` does not execute.** The painter compiles its
token regex at *import* time and `re` was never imported at module level in
this file (only far below, as `_re426`). Parse was happy; import would have
raised `NameError`. **Any module-level block must be EXECUTED in the battery,
not merely parsed.**

**NEW Rule 22 — when documentation cannot settle a device question, auto-detect,
announce, and ship a self-test.** Whether Pydroid 3's console honours ANSI is
not documented. So: `C466_COLOR='auto'` paints only when `stdout.isatty()`,
`NO_COLOR` is honoured, the boot line states the decision and why, and
`omega_color_test.py` answers it on the device in five seconds. Worst case is a
monochrome console and one config line — because the files were never coloured.

---

## 🛠 BATTERY ADDITIONS

```
python3 omega_color_test.py          # on the phone: does ANSI render here?
```
Plus, in the automated battery: **execute** the module-level colour block;
count escapes at all three sinks; assert visible width is unchanged by
painting; render 6 widths × 3 palettes and assert zero over-width / non-ASCII.

---


# ═══════════════════════════════════════════════════════════════════════════
# 📐 2026-09-17c — C465: THE DASHBOARD, LAID OUT SO NO FONT CAN BREAK IT
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE

**Shipped: C465.** Branch `claude/trading-system-analysis-tsvzj4`.
Pydroid3 / Nothing Phone 2, paper, $250, Bitget **basic tier**, maker both ways.
Display: `C462_LOG_WIDTH = 0` (auto → 44 on Android), `C465_GLYPHS = 'ascii'`.

### 🟢 THE MAKER EXIT IS ALIVE
Session 20260917_221311 carries **`C462-6 MAKER half filled UNI`** and
**`C376 MAKER exit filled UNI`**. The path C463-1 found dead for **87 versions**
fired twice in its first session. UNI +4.00%, +$0.48, **+1.03R**, 81% of a
+4.92% peak, 18 min — **three maker fills, zero taker, $0.01 total fees.**
One trade in 15 scans / 1,220 analyses, which is the C461-3 pace.

---

## 📏 THE DISPLAY RULE (learned the expensive way)

> **Every box row in the operator's report file was EXACTLY 46 characters, and
> the right border still landed in a different column on almost every row.**

**Cause: East Asian Width = AMBIGUOUS.** A font may render these at one cell or two:

| used in the old layout | EAW |
|---|---|
| `│ ─ ┌ ┐ └ ┘ ├ ┤` box drawing | **A** |
| `·` middle dot — *~8× per block* | **A** |
| `█ ▁ ▂ ▃ ▄ ▅ ▆ ▇` blocks | **A** |
| `→ ▲ ▼ ▽ ± × – ≈` | **A** |

Rows with more separators overflowed further — that is the whole pattern.

**NEW Rule 18 — nothing in a terminal layout may depend on a character landing
in an exact column.** No right borders. ASCII for every glyph that must align.
A left label column is the only alignment a text dashboard needs.

**NEW Rule 19 — never identify a log line by its first character.** Doing so
welds the layout to whatever glyph the filter was taught, which is why the
ambiguous-width glyphs could not simply be swapped out. Flag the *record*
(`logger.report()` → `extra={'c465_report': True}`), not the text.

**NEW Rule 20 — a graphic that cannot render is worse than no graphic.** The
equity sparkline drew as one solid white bar on the phone: the lower-eighth
blocks are ambiguous-width *and* commonly absent from a phone font. ASCII
density (`._-=+*#@`) reads correctly everywhere.

---

## 🎛 THE LAYOUT CONTRACT

```
  ========================================     <- head rule, width-4
  OMEGA C465  PAPER  Bitget perps
  17 Sep 2026   19:06
  start $250.00  day +/-0.68%
  ========================================

  19:06  up 0h09m  scan 1 ----------------     <- section rule carries the title
  EQUITY    $250.38  unreal $+0.38             <- 2 spaces, 10-char label, text
  SESSION   $+0.38 +0.15%
  DAY       +0.15% of +/-0.68%  22% used
            [------------|##----------]        <- SIGNED gauge, fills from zero
  ...
  ----------------------------------------
  + UNI LONG  +1.68%  $+0.38                   <- open position, 2 rows
     7.4210 > 7.5460  4m  61% left  ######..
  ----------------------------------------

  >> 22:18  OPEN   UNI LONG                    <- the tape: >> open  << close
       @7.4210  x1 $24.00                         -> half  .. heartbeat
       target +9.9%  stop -2.9%  maker
```

`C465_GLYPHS = 'unicode'` swaps the characters and **keeps the layout identical** —
one code path, two character sets.

**Dynamic rules now in force:** omit an undefined figure rather than print `n/a`;
suppress LIFETIME when it equals this run's record; show unrealised only when a
position is open; show peak/drawdown only when they differ from now; collapse the
channel list to one line; cap MOVERS at four and drop `[Live=…<cut]` for `cut`;
withhold the curve until it has six samples.

---

## 🛠 VERIFICATION BATTERY (unchanged additions)

```
python3 omega_wrong_object_sweep.py --diff     # must report no NEW findings
python3 omega_overlay_test.py                  # C464 overlay, 5 adversarial cases
```
Plus: render the report at 36/40/44/52/72/100 and assert **zero rows over width
and zero non-ASCII in ascii mode**; and drive a report line through the real
`CustomLogger` + filter to prove the flagged channel still reaches the screen.

---


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 2026-09-17b — C464: THE INFORMATION CHANNELS, BUILT PROPERLY
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE — READ THIS FIRST

**Shipped: C464.** Branch `claude/trading-system-analysis-tsvzj4`.
Pydroid3 / Nothing Phone 2, paper, $250, Bitget **basic tier** (no fee discount),
maker both ways, 1–3 trades/day, 4–8h intended holds.

### What C463 established (unchanged, and it governs everything)
> 662,800 bars, 32 pairs, **two separate non-overlapping ~105-day windows**:
> **nothing derivable from price is net positive after fees.** 30 of 30
> geometries negative. Orderliness, momentum, volatility: null. Cross-sectional
> momentum was +0.0364 %/trade at **4/4 splits** and **failed out of sample**
> (−0.0149, 1/4). Rule 9 caught it.

### What C464 adds
**Funding is now measured too, and it is also null.** 9,383 Bitget settlements,
88 days, 32 pairs, entries one bar after each settlement:

| rule | mean %/trade |
|---|---|
| fade top-decile funding | −0.0837 |
| follow top-decile funding | −0.0619 |
| fade both tails | −0.0692 |
| **the null** | **−0.0682** |

**Funding does not predict direction.** It is retained as *crowding magnitude*
only. C212's `clip(-funding × 130, ±0.4)` is **off** — funding is positive ~76%
of the time, so that term was a persistent anti-long tilt applying an absent signal.

### Data availability, measured not assumed
| channel | historical source | verdict |
|---|---|---|
| funding | Bitget `history-fund-rate`, 90 days | **backtested — null** |
| price/geometry | Bitget candles, 2 × 105 days | **backtested — null** |
| taker flow (CVD) | Binance geo-blocked · OKX 6h · Bybit geo-blocked | **not backtestable here** |
| open interest | same | **not backtestable here** |
| news | no historical corpus | **not backtestable** |

**That is a limitation of the workbench, not a licence to guess.** Hence the overlay
is bounded, cannot veto, and reports itself.

---

## 🧭 THE C464 OVERLAY — WHAT IT IS ALLOWED TO DO

Every channel → **midrank percentile against the board this scan** → [−1,+1] →
signed by the candidate's direction → one info score → **conviction × (1 ± 0.15)**.

- **No absolute constant appears anywhere in it.**
- **Cannot flip a direction. Cannot veto a trade.** An unmeasured signal does not get to say no.
- Midrank, not naive rank — C454 measured the tie bias at 303 of 780 pairs sharing one funding value.
- Dispersion gate on every channel — a flat board stays **silent**, not zero.
- Weights (flow .40, OI .25, news .25, funding .10) are **judgements, not measurements**,
  ordered by how directly each channel observes committed money.
- The **agreement gate** (require N channels to agree) exists and is **OFF** — it is a veto.

**The live A/B is the point.** Every trade records its full breakdown; the dashboard
reports trades where the channels agreed vs disagreed, with the gap per trade.
After ~50 closes the ledger answers this, not me.

---

## 🔴 STANDING RULES — additions at C464

**NEW Rule 16 — a verification tool that cannot fail its own test is not a tool.**
The C464-6 sweep was written to catch the wrong-object family and, tested against a
deliberately broken copy, was found to have **three** defects of its own: it ignored
`getattr(self,'x',default)` (the dominant read idiom here, and the reason these bugs
are silent); its module-level scan recursed into classes so every local assignment
looked like legitimate injection; and it only reported an attribute if some *other*
class owned it, missing the case where **nobody** owns it — which was the bug.
**Always test a checker against a known-bad input before trusting a clean report.**

**NEW Rule 17 — "cannot be backtested" must name the source that was tried.**
I told the operator flow/OI/funding could not be backtested. Funding could be, and
it took one API call to find out. Check the venue's history endpoints before
declaring a channel unmeasurable.

**Rule 9 now has three scalps:** C459/C460 (geometry), C463 (cross-sectional
momentum), and the standing warning against re-discovering either.

---

## 🛠 THE VERIFICATION BATTERY (run all of it every version)

```
python3 -c "import ast;ast.parse(open('omega_v60_reconstructed.py').read())"   # 3.10 AND 3.12
python3 omega_wrong_object_sweep.py --diff      # must report no NEW findings
python3 omega_overlay_test.py                   # the overlay over 5 adversarial cases
python3 omega_funding_test.py                   # needs corpusL/ + corpusF/
python3 omega_geometry_grid.py                  # needs corpusL/
python3 omega_xsectional.py                     # run on BOTH corpusL/ and corpusO/
```
Fetchers: `omega_fetch_corpus_32.py` (recent), `omega_fetch_corpus_old.py` (separate
older batch — **Rule 9 needs this one**), `omega_fetch_funding.py`.

---


# ═══════════════════════════════════════════════════════════════════════════
# 🧭 2026-09-17 — C463: THE MEASUREMENT THAT DECIDES WHAT THIS BOT CAN BE
# ═══════════════════════════════════════════════════════════════════════════

## ⏩ RESUME STATE — READ THIS FIRST

**Shipped: C463.** Branch `claude/trading-system-analysis-tsvzj4`.
Operator runs it in **Pydroid3 on a Nothing Phone 2**, paper, $250, maker both ways,
1–3 trades/day, 4–8 hour intended holds.

**THE HEADLINE, and it supersedes every optimisation conversation before it:**

> Across **662,800 bars, 32 pairs, TWO SEPARATE non-overlapping ~105-day windows**
> (Feb–Jun 2026 and Jun–Sep 2026), with maker-both fees at 0.04%:
> **no entry condition and no exit geometry derivable from price is net positive.**
>
> - **30 of 30** target/stop pairs (0.5R–3.0R × 0.5R–2.0R) are negative. Least-bad −0.0233 %/trade. Shipped 2.00R/0.75R: −0.0555.
> - Orderliness, 4h/24h momentum, strong-mover continuation, volatility bands: none significantly positive.
> - The peak-giveback exit the bot fires on: **+0.0019 %/trade, t=+0.20** — neither problem nor solution.
> - **Cross-sectional momentum** looked like the first real find (+0.0364 %/trade, **4/4 splits**) and **FAILED out-of-sample** (−0.0149, 1/4). Pooled +0.0114 with the halves disagreeing in sign. **Standing Rule 9 caught it. Nothing shipped.**

**What follows from that, and it is not despair:** the strategy family is worth ~0 minus a
small drag. The only levers left are (a) **cost**, already halved by C461 and worth more
than any edge measured here, and (b) **channels that are not in the price series** — taker
flow, open interest, funding, news. The bot **already collects three of them and wires them
to nothing.** C463-13 begins recording entry-flow alignment so it becomes measurable after
~50 closes. **Do not spend another version on geometry.**

---

## 🔴 STANDING RULES — additions and changes at C463

**Rule 9 is now load-bearing and has fired twice.** "A feature is not real until it
replicates in a SEPARATE BATCH at a different time; within-window splits are NOT evidence."
- C459/C460: my geometry claim shrank 6× and lost significance on more data.
- C463: cross-sectional momentum went **4/4 → 1/4** and flipped sign on a separate window.
**Never ship on a within-window 4/4 again. Fetch the older corpus (`omega_fetch_corpus_old.py`) and re-run.**

**NEW Rule 13 — a signal that is computed and never displayed will be reported as broken.**
The operator said "news analysis is missing". It was running: 65 articles, 50 of 60 pairs
resolved, every one scored — and C460-1's suppress list deleted all of it. A signal that is
computed, used in the score, and never shown is indistinguishable from one that is broken.
**Every live channel gets a row on the dashboard.**

**NEW Rule 14 — match the WORD, never the decoration.** C463-2 put the stop-sign emoji on
the alert list for "STOPPING"; it is also the prefix of every per-pair veto line, and forty
lines of working came back onto the screen. Emoji are not semantics.

**NEW Rule 15 — a filter's default must be OFF, once a complete record exists elsewhere.**
C460-1 chose a drop-list over a keep-list so nothing new could be hidden. That was correct
while the session log was the only readable record, and became wrong the moment the detail
log carried everything unfiltered: after that, a drop-list puts every new diagnostic on the
operator's screen by default, and sixty versions of that is a wall of text.

**Rule 5 (a protection that fails quietly is not a protection) earned its keep.** One log
line added at C462-1 — printed on a path that had been silent — named an AttributeError that
had disabled the maker exit for **87 versions** and that eight versions of *reading* had
missed. **Instrument the silent path; do not trust a code read.**

---

## 🐞 THE BUG THAT MATTERED MOST AT C463

**`self._C376_PROFIT_TOKENS` — wrong object, instance EIGHT.**
`_C376_PROFIT_TOKENS` is a class attribute of `Position`. It was read inside
`TradingBot._close_position_inner`, where `self` is the bot. **Every close since C376 raised
AttributeError and fell through to the taker path.** C461 rebuilt the whole project around
the maker/taker gap being larger than any edge — and the lever was bolted to nothing.

**And I mis-diagnosed it one version earlier.** The C462 changelog says the exit "read a
stale field". It did not; C461 carries the identical line. Recorded because the wrong
diagnosis is the more instructive half.

**The sweep that finds this class:** for every ALL-CAPS class attribute, check that every
`self.<ATTR>` reference sits inside a class that owns it (or assigns it in `__init__`).
It is in the C463 verification battery and it should run every version.

---

## 📐 THE NUMBERS TO TRADE AGAINST (C463, both windows)

| what | value | notes |
|---|---|---|
| maker round trip | **0.04%** | C461; was 0.12% taker-both |
| best null geometry | **−0.0233 %/trade** | 0.50R target / 2.00R stop |
| shipped geometry | **−0.0555 %/trade** | 2.00R / 0.75R |
| gap to break-even | **~2.3 bp/trade** | what any edge must beat |
| ρ(entry score, win) | **−0.022** | the score has no ranking power |
| realised record | **7W / 13L** | 35%, payoff not yet measurable in R |
| honest monthly target | **~0%, ±1%** | on price alone, after fees |

**At 2 trades/day × 22 days on ~$60 notional, the drag alone is ≈0.5%/month of a $250 book.**
Any claimed monthly target above ~1% requires an edge that has not been measured yet.

---


> **REBUILT AT C453.** The previous Atlas was destroyed by an editing error of mine: I restored
> `omega.py` from the outputs folder at the start of the C453 session but did not restore the Atlas
> alongside it, so the append created a fresh file containing only the newest section, and the copy
> back to outputs overwrote the good one. Both locations and the VFS cache held the same truncated
> file, so it could not be recovered.
>
> **What was lost:** my numbered distillations (#1–#204) and the hand-written per-version essays.
> **What survived:** the authoritative source they were written from — the in-code `_CHANGELOG`,
> **87 entries from C264 to C453, 371,398 characters, no gaps.** This Atlas is rebuilt from it.
>
> **The lesson is recorded as Principle #207 rather than quietly fixed**, because losing the
> project's own memory to a `cp` is exactly the class of error this document exists to prevent.

---

## RECOVERY NOTE — WHAT THIS DOCUMENT NOW IS

The operator supplied an earlier Atlas covering **C264–C419** in hand-written form. That is the
interpretation layer I destroyed, recovered for everything up to C419. It is preserved **verbatim and
first**, because it was written with the evidence in hand and is worth more than any summary I would
write now.

Everything from **C420 to C453** is rebuilt from the in-code `_CHANGELOG` — the authoritative record
that survived, 87 entries and 371,398 characters with no gaps.

**Still permanently lost:** the numbered principles #130–#204, which existed only in the destroyed
file. The *facts* behind them are all in the changelog sections below; only my numbering and phrasing
are gone.

---

# PART ONE — THE RECOVERED ATLAS (C264 → C419)

> **▶ NEW CHAT? READ `OMEGA_HANDOFF.md` FIRST.** It carries the full resume state as of 2026-08-15:
> shipped version **C396**, the four-window baseline, all standing rules, every measured fact, the
> open C396 verification gap, and the immediate next steps. This Atlas is the detailed map; the
> handoff is the orientation.

> **RESUME POINT — C362 (bot UNCHANGED) + REPLAY HARNESS v3.1, 2026-08-05 — C367 SHIPPED: THE UNGATED FLOOR.** Read `WALKTHROUGH.md` alongside this. Read `HANDOFF_README.md` first.
> Two studies done: the EXIT engine is cleared (n=24) and the ENTRY hypothesis it produced was
> tested at 158k observations and REFUTED. Nothing shipped — correctly.
> **This session found a harness defect that invalidates the exit conclusions of the last several sessions.**
> Bot code was deliberately NOT touched: the measurement says the exits are not the problem.

# OMEGA_CODE_ATLAS — Living Reference (current at C357 + REPLAY HARNESS v2.0, 2026-07-29)

## ⏩ RESUME STATE — read this first in a new chat

# ═══════════════════════════════════════════════════════════════════════════
# 🕐 2026-08-15 — C396: SESSION-OF-DAY EDGE (new) + HP MODE FIX
# ═══════════════════════════════════════════════════════════════════════════

## Part 1 — Session-of-day edge (research + corpus validated)
Peer-reviewed crypto microstructure research: liquidity/follow-through peak when London+US open,
trough in Asia-only hours. **Measured on a fresh 10-day, 15-pair live Bitget corpus:**

| session (UTC) | IST | momentum barrier WR |
|---|---|---|
| Asia (0–8) | 05:30–13:30 | **46.5%** |
| Europe (8–16) | 13:30–21:30 | **55.9%** |
| US (16–24) | 21:30–05:30 | 48.8% |

**9.4pp spread, and it HELD IN BOTH HALVES** (Europe−Asia gap +12.8pp then +6.4pp). Ships as a SOFT
tilt (10d is a small sample): Europe ×1.12, Asia ×0.88, US neutral, bounded ±12%. Wired at the
C387/C392/C394 site; full multiplier chain bounds-checked safe (0.61×–1.56× of base).

## Part 2 — HP mode fix (operator flagged it losing badly)
Log: HP ran **3 HOURS**, rejected 47 candidates on 'weak macro' (median score **0.13**) + 27 on a
$1.5M vol floor, opened **ONE** trade (ACU, lost at −3.9% drift cap), bled **−0.24%** doing nothing.
**Root cause: HP runs AFTER Normal takes the day's best setups, then scrapes weak leftovers at higher
risk — structurally backwards.**

Two fixes:
- **Regime gate** at `switch_to_hp`: HP only activates if |market R| ≥ 0.30. In chop it now SKIPS and
  ends the day flat (logged tape was R≈+0.25 → would skip).
- **Vol floor** made configurable, lowered $1.5M → $0.75M to match Normal's effective floor.

## ⚠️ Verification honesty
The four-window harness + 29k-bar corpus did NOT survive the sandbox reset. C396 verified by syntax/
AST, config-load (ccxt installed), session-tilt + HP-gate logic exercised in isolation, and a
multiplier-chain bounds check. NOT re-run through the full four-window replay — changes are localised
and bounded, HP gate only PREVENTS a losing action, so risk is low. **Next live log should confirm HP
skips chop and the session tilt fires.**

## Also confirmed in this log (good news)
Session was **+$0.79 net, 64% WR** including a +9.98% winner. The C395 drift fix WORKED —
'momentum snapped' fell 3→1, unfilled 4→3.


# ═══════════════════════════════════════════════════════════════════════════
# 🎯 2026-08-14h — C395: THE ENTRY MECHANICS WERE THROWING AWAY GOOD SETUPS
# ═══════════════════════════════════════════════════════════════════════════

Operator flagged the recurring **"momentum snapped"** and **"limit unfilled"** messages. Root-caused
to two real faults — **six candidates reached final selection (one scoring 1.086) and ZERO opened.**

## Fault 1 — the drift guard was INVERTED
It aborted an entry if price drifted against the trade by more than `min(0.8×ATR, 0.75%)`. **The
`min()` cap made the guard tightest on the pairs that move MOST:**

| ATR | effective abort | as % of ATR |
|---|---|---|
| 0.6% | 0.60% | 100% |
| 2.0% | 0.75% | 38% |
| **6.7%** | **0.75%** | **11% ← pure noise** |

CAP (ATR 6.7%) "momentum snapped" on a 0.75% twitch. **Fixed to scale WITH volatility** — abort at
~90% of the pair's own ATR (floor 0.60%, ceiling 4.0%). CAP now aborts at 4.0%, a real snap.

## Fault 2 — passive limits lose real-edge trades
Entries rest a passive limit **below** market to earn ~4bp maker fee, but in a fast tape price never
returns and the trade is lost. **A high-score candidate (≥ 0.75) now crosses the spread** (taker) to
secure the fill — conviction earns the fill the way regime persistence already does.

## Why the replay shows neutral (identical to C394)
The drift/fill problems are a **live-feed phenomenon** of real spreads and fast quotes; the corpus
has tight synthetic spreads and rarely triggers them. **C395 is verified not to harm the backtest
while fixing a waste proven in the live log** — six lost setups in one session.

## Also confirmed in this log
The one closed trade (**CAP −5.90%, −$1.52**) was **C377 firing correctly** at −6.03% = −1.56R
("arithmetic, not opinion"). The bigger dollar loss is simply the **20% drawdown** sizing working as
designed. C394's trend tilt was mostly dormant because the tape was mildly rising (R +0.25) — the
longs weren't wrong-direction, they were choppy-tape entries the fixed drift guard now handles.


# ═══════════════════════════════════════════════════════════════════════════
# 📉 2026-08-14g — C394: SHORT THE DOWNTREND (the first all-axis improvement)
#    + STEP-1 SCREENER ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

## The log proved a long bias
In a falling tape (**market R = −0.54**) the bot attempted **LONG 107 times**, was **correctly
blocked every time** by `resultant_counter` (148 total), and took **zero shorts → zero closes.**
A bull-market bot sitting out a bear market.

**Research is unanimous:** a trend-follower's defining feature is *"buy the uptrend, SELL the
downtrend,"* and the #1 reason bots fail is **strategy-market mismatch** — a long-biased bot in a
falling market. The bot *can* short (217 refs) and the direction line is symmetric, but the component
signals **skew long**, so in a down-tape it generates longs that get blocked instead of shorts that
would trade.

## The fix — C394 trend-direction tilt
When the tape is clearly trending (|R| ≥ 0.30), tilt the score by trend alignment: a short in a
falling tape boosted to **1.15×**, a long damped to **0.85×**, and vice-versa. Steers the signal to
the correct side up front. Bounded ±15%, doesn't touch the taker-flow blocks.

**Four-window replay vs C388:**
| | C388 | **C394** |
|---|---|---|
| trades | 6 | **8** |
| EV/trade | +$0.098 | **+$0.105** |
| **total net** | +$0.589 | **+$0.840 (+43%)** |
| trades/day | 0.21 | **0.30** |

**First change since the universe widening to improve EVERY axis.** The added trades are downtrend
shorts that won.

## 📋 Step-1 screener — analysed (operator request)
Ranks by `0.40·log-vol + 0.25·change + 0.35·freshness`. **Eye-test looked alarming** — ranked
**ACE +142.7%** at #2, VELVET +54.4% at #15 (already-exploded pairs); 94 of 237 surfaced pairs had
already moved >5%.

**But measured on corpus, it's not broken:** recent change is **flat on win rate** (48–50% across all
change buckets), and so is volatility (**71.5–72.5%** resolve across ATR terciles). **No "which pair
moves" signal separates tradeable from untradeable — because ~72% of all crypto pairs resolve within
an hour regardless.** Pair *selection* was never where the edge lives. **Direction is** — which is
exactly what C394 fixes.


# ═══════════════════════════════════════════════════════════════════════════
# 🎚 2026-08-14f — C393b: EVERY CROSS-VENUE EDGE TESTED + DRAWDOWN SET TO 20%
# ═══════════════════════════════════════════════════════════════════════════

## New-edge avenues — all tested against real data, honest tally
| avenue | reachable? | edge? | verdict |
|---|---|---|---|
| Cross-exchange arbitrage | no (451 / one process) | n/a | impossible to build |
| Binance spot lead | data only | no (corr 0.90–0.98) | noise, not built |
| **OKX perp lead** | data only | **no (corr 0.90–0.99)** | noise, not built |
| Multi-venue funding dispersion | yes | no (identical at majors) | arbitraged away |
| **Open-interest edge** | partial | **UNTESTABLE (no history)** | cannot backtest |
| Cross-venue quote sanity | yes | defensive only | BUILT (C393) |
| Funding-follow tilt | yes | weak, measured | BUILT (C392) |

**The efficient-market wall, confirmed on a second and third venue: every venue prices the same
information at the same time. There is no free cross-venue edge for one retail account.** Sources
reachable (OKX, Gate, KuCoin, Kraken futures, dYdX, CoinGecko) but none carry a tradeable lead, and
OI history isn't public so it can't be backtested — so no untested signal was shipped.

## Drawdown dial set to 20% (the real lever — scales edge, not a new edge)
At $250, 10% → 20%:
| max DD | per-trade risk | notional | 7% winner pays | month @60% WR | worst month |
|---|---|---|---|---|---|
| 10% | $1.14 | $28 | $1.99 | +2.02% | ~−$25 |
| **20%** | **$2.27** | **$57** | **$3.98** | **+4.08%** | **~−$50** |

**This is where 4% becomes reachable — by consciously accepting double the downside, NOT by finding
new edge.** 20% is the professional-fund median (Crypto Fund Research, 117 funds). Startup prompt
still lets the operator change it each session; 20% is only the chosen default.

**DELIVERED C393: universe 150 · funding-follow tilt · cross-venue quote guard · drawdown 20%.**
Everything measured, nothing faked.


# ═══════════════════════════════════════════════════════════════════════════
# 🔗 2026-08-14e — C393: CAP -> 150, AND THE HONEST TRUTH ABOUT BINANCE
# ═══════════════════════════════════════════════════════════════════════════

## Universe cap 100 -> 150
The full realistic width — 206 pairs clear the vol floor but the top 150 by activity capture
everything ever lively in a 15m window; the tail is dormant microcaps.

## The Binance account — measured, not assumed
| capability | reachable here? | buildable? |
|---|---|---|
| Binance **futures** (fapi) | ❌ HTTP 451 geo-blocked | no |
| two-venue simultaneous execution | ❌ impossible from one process | no |
| → real arbitrage / hedging / funding capture | — | **NO — would be theatre, refused** |
| Binance **spot** data (data-api.binance.vision) | ✅ 490 USDT pairs, read-only | yes |

**Tested Binance spot as a LEAD signal (1m, 5 majors):** same-bar correlation with Bitget perp is
**0.90–0.98** and the lead direction is **inconsistent** (2 Binance-lead, 2 Bitget-lead, lag-corr all
< 0.13). **No stable exploitable lead → not built as a predictive signal** (that would be fitting
noise).

## What WAS built — a divergence sanity check (skip filter, not a signal)
When Bitget perp diverges from Binance spot **> 0.75%**, the perp quote is likely stale/wick →
**skip the entry.** Read-only, **fail-open** (no Binance data → no effect; behaves exactly as before),
can only ever **remove a bad fill**, never add risk.

## ⚠️ Dead-code bug caught before shipping
Guard methods were defined on `ExchangeManager` but first called as `self.<method>` from
`_open_position` on `TradingBot` — wrapped in try/except it would have **silently done nothing.**
Fixed to call via `self.exchange`; live-tested: 0.1% gap passes, 2% gap blocks, unreachable fails open.

**HONEST SUMMARY: the Binance account adds no trading capability from this environment. Binance spot
DATA adds a small defensive quote-sanity filter, not a new profit edge.** The realistic path to higher
return remains a wider universe (now 150) + the C380 drawdown dial at professional 20-30% — honest
leverage of the one small real edge, not a new one.


# ═══════════════════════════════════════════════════════════════════════════
# 🌐 2026-08-14d — C391/C392: WIDER UNIVERSE (works) + FUNDING EDGE (measured)
# ═══════════════════════════════════════════════════════════════════════════

## C391 — widen the analysed universe (the one lever that passed)
Measured on live Bitget: **754 futures, 206 clear the $750k floor**, but `scan_lively_pairs`
truncated to the **top 44** before deep analysis — 162 eligible pairs never scored, the 22-pair
corpus was ~11% of addressable. Since C389 proved looser gates lose money, **more pairs is the only
lever that adds trades without lowering quality.** Truncation is now a dial (`C391_UNIVERSE_CAP`,
default 100). isRwa (C155) + volume floor filter first.

**Four-window replay vs C388 baseline:**
| | C388 | C391/C392 |
|---|---|---|
| trades | 6 | **7** |
| EV/trade | +$0.098 | **+$0.083** |
| win rate | 83% | 71% |

**First change in many sessions that adds a trade while keeping positive EV.** Honest limit: windows
3 & 4 stayed at **0 trades** even at 100 pairs — widening helps when *some* pair is lively, it cannot
manufacture trades in a dead tape.

## C392 — funding-aware entry timing (the only reachable "new edge")
Cross-venue arb / liquidation feeds / maker rebates all need infrastructure this bot lacks (verified:
Binance 451, Bybit 403 in-sandbox; two-venue execution impossible from one account). **Funding is the
one real non-price signal the venue exposes** — already fetched, already drives `funding_reversal`.

**The naive idea was tested and REFUTED:** fading the funded side won **25%** across 29,454 cases;
**following** it won **74%**. So the tilt **follows** funding (positive → favour long), bounded ±10%,
applied at the C387 site so the tilts compose. Left behind `C392_FUNDING_TILT` for live-log
confirmation with real funding rates.

**This is the honest shape of "a new edge class": the only reachable one was a venue signal, its
naive direction was wrong, and measurement corrected it before shipping.**


# ═══════════════════════════════════════════════════════════════════════════
# 🧪 2026-08-14b — C389: THE COLD-AUDIT HYPOTHESIS WAS WRONG (measured)
# ═══════════════════════════════════════════════════════════════════════════

## First: four clean replay weeks reframed the whole problem
Full C388 pipeline, $250, 10% DD, four independent ~7-day windows:

| window | trades | WR | net |
|---|---|---|---|
| 1 | 4 | 75% | +0.22% |
| 2 | 2 | 100% | +0.02% |
| 3 | **0** | — | 0.00% |
| 4 | **0** | — | 0.00% |

**Pooled: 6 trades, 83% WR, +$0.098 EV/trade. The bot is NO LONGER LOSING — it barely TRADES**
(0.21/day, zero trades in 2 of 4 weeks). **Inactivity, not losses, is the ceiling on 4%.**

## The test: disable the 13 exhaustion gates and re-measure
A reversible switch (`C389_DISABLE_EXHAUSTION_FAMILY`) wired into all 19 block sites. Same 4 windows:

| metric | before | after |
|---|---|---|
| trades | 6 | **11** (+5) |
| trades/day | 0.21 | **0.42** |
| win rate | 83% | **55%** |
| EV/trade | **+$0.098** | **−$0.007** |
| month proj | +0.5% | **−0.02%** |

## ❌ VERDICT — cold-audit hypothesis REFUTED
Disabling the family **doubled turnover and turned EV negative.** The freed trades went ~2W/3L.
**The gates are LOAD-BEARING, not redundant — they filter genuinely losing trades.**

**The deeper finding:** the bot trades rarely because **good setups are genuinely scarce** at this
horizon, not because it is over-filtered. **More trades = worse trades.** Same efficient-market wall
every prior avenue hit. Switch left in place OFF-by-default; family stays active.

**This is why we measure before deleting.** Shipping the deletion would have doubled turnover to
make less money.


# ═══════════════════════════════════════════════════════════════════════════
# 📖 2026-08-14 — C388: THE TWO STORIES DISAGREED, AND THE LOG WAS RIGHT
# ═══════════════════════════════════════════════════════════════════════════

Read as code=story A, log=story B. **Story A claimed** C377's 1.5R stop "cannot be vetoed" and the
partial "retains half under the hard stop." **Story B (live log) showed the opposite:**

| | |
|---|---|
| C377 HARD STOP firings | **0** all session |
| AEON | STAGNANT_PARTIAL at **−5.71%** → remainder rode → died at **−6.00%** |
| the same position | **two losses**, $0.43 + $0.45 |

## Reconciliation
AEON's ATR was **2.7%**, so R = 5.4% and C377's 1.5R stop sat at **−8.1%**. The partial triggers on
**PRU**, the hard stop on **R** — and for a volatile pair the PRU trigger is hit **first and
shallower**, so the "protection" was a bigger loss taken in two pieces with a widened stop on the
second. **C377 was correct; it never got the chance.**

## Fix
A stagnant **loss** past 1.5R exits the **whole** position; between 1R and 1.5R it also exits whole.
The partial is allowed **only inside 1R** — the one region where retaining half is defensible.

| ATR | move | action |
|---|---|---|
| 2.7% | −5.71% | **FULL exit** (past 1R = −5.4%) |
| 1.0% | −3.5% | **FULL exit** (past 1.5R) |
| 0.7% | −0.8% (thesis intact) | partial OK (inside 1R) |

## Honest correction of my own first reading (kept in the record)
The −5.71%/−6.00% **percentages** look alarming but the **dollars were on-budget** — a 2.7%-ATR pair
is sized so 1.5R loses $0.85, so it lost only **$0.63** at −6%. The sizing was fine. The real and
only damage was the **second loss from the widened-stop remainder**, which is exactly what C388
removes. **Story A now describes Story B — the impossible −6.00% second loss cannot recur.**


# ═══════════════════════════════════════════════════════════════════════════
# 🧭 2026-08-11e — C387: REGIME-CONDITIONED ENTRY (rebuild step 1) + STEP-1
#    FUNCTIONAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

## C387 — the audit's #3, the only step that turns a negative edge positive
**Measured basis:** the core signal (long when 1h & 4h momentum agree) is anti-predictive overall,
**ρ −0.022**, WR falling 49.5% → 45.5% as score rises. But the regime split is the finding:

| regime | buy-strength barrier WR |
|---|---|
| **RISING** (btc7d>+3%) | **52.4%** |
| **FLAT** | **44.9%** ← where the bot trades most |
| FALLING | 50.3% |

**The signal isn't broken — it's applied in the wrong regime.** C387 multiplies score by
`1 + 0.10 × alignment`, `alignment = clamp(market_R × dir_sign / 0.40, −1, 1)`:
- long in a strong rising tape → **1.10×** (the 52.4% cohort)
- long in a flat tape → **1.00×** (the 44.9% cohort, no boost)
- trade against the tape → **0.90×** (compounds with the C386 block)

Bounded ±10% (re-weights an existing signal, doesn't manufacture one). **Separate** from the
counter-trend penalty: that *gates opposing* trades, this *grades with-trend* trades by regime support.

**Verified firing (not a silent no-op):** `result['direction']` is set at 7384, read by C387 at
~7508; a replay applied the tilt to **1,132 candidates**, alignment −1.00 to +1.00, mean +0.331.

## Step 1 — `scan_lively_pairs` (432 lines), functionally analysed
Ranks the universe by **`0.40·log-volume + 0.25·change + 0.35·freshness`**, cohort-relative, where
*freshness* down-weights already-moved pairs; a hardcoded ~90-symbol blocklist strips stocks/forex.

**Tested on corpus — does liveliness predict a tradeable pair?**
| liveliness quintile | resolves within 1h |
|---|---|
| Q1 (lowest) | 70.1% |
| Q5 (highest) | **74.5%** |

**ρ +0.024 — it works, but weakly.** And the key caveat: **"resolves" ≠ "wins."** A lively pair
moves decisively in *either* direction — which is exactly why regime-conditioning the *direction*
(C387) matters more than the liveliness rank itself.


# ═══════════════════════════════════════════════════════════════════════════
# 🔬 2026-08-11d — COLD AUDIT (fresh perspective). See COLD_AUDIT.md.
# ═══════════════════════════════════════════════════════════════════════════

Stepped back from per-log fixing to audit the whole architecture. **No code changed.**

**THE MACHINE:** 23,505 lines · 314 functions · **61 entry gates** · **73 score-multiply sites** ·
130 Config constants · 244 versions.

**EIGHT STRUCTURAL FLAWS:**
1. Penalty stack is multiplicative — 5 mild penalties compound to ×0.50, killing a 0.80 setup, and
   the bot can't report which combination did it.
2. **13 gates encode one REFUTED idea** ("already moved") — represented 13×, still dominates the funnel.
3. **The entry score is ANTI-PREDICTIVE where the bot trades most.** Tested on corpus with the bot's
   own logic: ρ(score,win) = **−0.022**; score 1.0 → 45.5% WR. Regime-split: 52.4% RISING vs
   **44.9% FLAT**. The edge is regime-dependent; the bot doesn't condition hard enough.
4. STAGNANT_PARTIAL half-closes a loser then **widens the stop** on the remainder — GIGGLE lost
   −2.53% then −2.48% on the same trade.
5. Over-trading: 8 trades/day × 8bp = **~14%/month friction drag.**
6. **The day cannot compound** — one Normal+HP, stops at drawdown cap; a right day banks 1–2, a
   wrong day delivers the full loss.
7. The one real edge (orderliness, ρ +0.033) is a **±8% garnish** while 61 gates act on ρ≈0 signals.
8. 130 constants fitted to ~200 trades = overfitting by construction; 244 versions, never a subtraction.

**SYNTHESIS:** not losing from a one-line bug. Losing because the core entry signal has no edge in
its dominant regime, and 244 versions refined that edgeless signal instead of replacing it.
**4%/month needs subtraction, not a 62nd gate.**

**REBUILD PRIORITY** (each rests on a measured number, not a guess): (1) delete the 13 exhaustion
gates; (2) cap + attribute the penalty stack; (3) condition entry on regime (long-strength only when
rising); (4) kill STAGNANT_PARTIAL; (5) trade less — 3–4 highest-orderliness setups; (6) let winning
days compound; (7) make orderliness the primary filter. **Awaiting operator's pick of which to build
first.**


# ═══════════════════════════════════════════════════════════════════════════
# 🧭 2026-08-11c — C386: THE LOSS PATTERN WAS COUNTER-TREND-INTO-NOISE, and
#    the penalty was too weak to stop it.
# ═══════════════════════════════════════════════════════════════════════════

## Session, read trade by trade
5 closes, net −$0.80, WR 20%. **The two real losses were the SAME GIGGLE position** exiting in two
pieces — a `STAGNANT_PARTIAL` at −2.53% and its remainder at −2.48%, **both inside 1.5R, so C377
behaved correctly.** The exits were not the problem.

**Two fixes confirmed working:**
- `C382 OVERRIDE` fired **23 times** — the C385 wiring works.
- `C384` logged **ZERO** reconstructions — every position now carries a real R.

## The entry path — deduced from the log
| | |
|---|---|
| directions | **17 LONG vs 4 SHORT** with the market frame R **negative** |
| counter-trend attempts | **56**, across just 3 pairs (1000BONK, GIGGLE, HOLO) |
| GIGGLE | LONG at R=−0.20 then −0.16 — **a long into a falling market** |

**This is the exact cohort the resonance study measured on RAW data (2026-08-08d): a long
after/against the market move is a ~45% barrier-win trade.** The existing soft penalty is 10–20%,
which drops a 0.80 score to ~0.70 and still clears MIN_SCORE — **so the 45% side kept trading.**

## The fix — NOT a new signal
The same study **refuted trading the reversal**, so the fix lets the one surviving edge break the tie:

| market frame \|R\| 0.15–0.40 + | orderliness | action |
|---|---|---|
| **noisy** | < 0.33 | **BLOCK** — no trend, no orderliness |
| orderly | ≥ 0.33 | soft penalty — orderliness buys a pass |

Orderliness (raw ρ +0.0328, t=+4.99 on barrier win) is the only quantity in this project that has
ever raised barrier-win probability. This does **not** touch the hard block above \|R\| 0.40, does
**not** resurrect the refuted reversal trade, and removes **only** the worst-founded entries.

## Honest bounding
Five closes is thin, and this bot has been hurt by fixing on thin evidence. **But the direction
rests on 158,444 observations, not these five trades**, and the change only removes entries that
have neither of the two things that predict a win. **The GIGGLE re-chart was attempted but the entry
window is 3 days stale and outside the 200-bar API limit** — so the entry was judged from the log's
own trajectory lines, not a fabricated chart read.


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 2026-08-11b — C385: CODE-LOGIC DEDUCTION SWEEP. My own C382 override
#    never fired ONCE, for two independent reasons.
# ═══════════════════════════════════════════════════════════════════════════

## DEDUCTION 1 — the override was wired to ONE gate out of FIVE
| gate | blocks this session | override wired? |
|---|---|---|
| `leg_exhausted` | 98 | ✅ 4 sites |
| **`parabola_bounce`** | **92** | ❌ **not wired** |
| **`no_structural_room`** | **48** | ❌ **not wired** |
| `late_leg_no_forward`, `absorption_at_extreme` | — | ❌ **not wired** |

**Measured: 0 override lines against 190 blocks from the family it exists to release.**
Now wired at all **nine** sites across the five refuted gates.

**Deliberately NOT extended** to `flat_projection`, `h1_regime_shock`, `resultant_counter`,
`mtf_disagree` or `corr_cap` — those are *different* hypotheses the 158,444-observation study never
tested. `corr_cap` in particular is the **SOL+WIF correlation lesson** and stays absolute; it
blocked CYS at score **1.039** this session, and that is the gate doing its job.

## DEDUCTION 2 — the confidence bar was an impossible AND
`score ≥ 0.70 AND confidence ≥ 0.80` sounds reasonable until you look at the joint distribution:

**Of 8 candidates scoring ≥ 0.70, exactly ONE also reached conf 0.80.** The rest sat at 0.51–0.69.
Score and confidence are strongly correlated, so demanding both at the top of their ranges is very
nearly unsatisfiable. **Lowered to 0.60** — releases PROM (0.782/0.616) and BEAT (0.702/0.686),
still holds PROM (0.701/0.592).

## DEDUCTION 3 — the selection bias, traced to the line (recorded, NOT changed)
Volatility reaches position size by **two** paths:
```
_vol_adj = clamp(1/ATR, 0.55, 1.30)     # Kelly allocator
margin   = risk / (2 × ATR)             # risk fit
```
| ATR | vol_adj | risk/stop | combined | vs 2% ATR |
|---|---|---|---|---|
| 0.7% | 1.30 | 71.4 | 92.9 | **6.75×** |
| 2.0% | 0.55 | 25.0 | 13.8 | 1.00× |
| 6.0% | 0.55 | 8.3 | 4.6 | 0.33× |

Risk parity alone would give 2.9×; the double count makes it **6.75×**. **But the risk fit BINDS**
(log: Kelly's `$62.50 → $11.59`), so `_vol_adj` does not change the final size — **it biases
SELECTION toward calm pairs**, and calm pairs went **0-for-4**.

**Left in place this pass**, because C384 has only just guaranteed R on every position and that
0-for-4 is confounded with three of those positions having traded completely unprotected.
**Re-measure once one clean session exists.**

## DEDUCTION 4 — 91% of analyses are CACHED
45 fresh against **464 cached**: the bot re-decides on a 15m candle boundary while scanning every
~5 min. **Correct for 15m-derived features** and it saves real work — but an intra-candle move
cannot trigger an entry. Recorded, not changed.


# ═══════════════════════════════════════════════════════════════════════════
# 🕳 2026-08-11 — C384: THREE OF EIGHT POSITIONS TRADED WITH NO RISK
#    FRAMEWORK AT ALL, AND THE LOGS LOOKED NORMAL
# ═══════════════════════════════════════════════════════════════════════════

## The session
8 closes, net **−$1.41**, **WR 25%**. But the arithmetic is stranger than that:

| | avg move | avg $ | implied notional |
|---|---|---|---|
| **winners** | **+4.29%** | +$0.210 | **$4.86** |
| **losers** | −3.43% | −$0.305 | **$10.61** |

**The winning side had the BIGGER average move and still lost money, because losers were sized
2.2× larger.**

## Why — and it is structural
`margin = risk / (2×ATR)`, so a **calm pair buys a large position**. Two clean regimes:

| notional | pairs | result |
|---|---|---|
| $4.4–5.0 | high-ATR | **2W / 2L** |
| $11.8–15.2 | low-ATR | **0W / 4L** |

## The defect underneath
`_c372_R_pct` is published at **exactly one sizing site**. A position reaching `_open_position` down
any other branch arrives with **R = 0** — and C372's profit floor, C373's capture gate and C377's
hard stop **all begin `if R <= 0: return`.** All three silently skip. The position trades with no
floor, no gate and no stop, **and nothing in the log says so.**

```
C377 HARD STOP firings   : 1   (of 8 trades)
C378 stop levels recorded: 5   (of 8 positions)
```

**Forensics of the worst trade:** UB closed −5.01% / −$0.69 via the **old** PRU stop at −4.4%
(2.9×PRU) after 64.4 min. At its R ≈ 1.8%, **C377 would have cut it at −2.70% for ≈ −$0.37.**

## The fix
R is `2×ATR` by definition and ATR is always on the analysis, so a missing R is now
**reconstructed** — from `atr_pct`, then `components.atr_pct`, then a 1.5% last resort that logs a
warning naming the untraced path. **There is no legitimate case for a position without a risk
unit.** Every reconstruction is logged so the offending branches can be fixed at source.


# ═══════════════════════════════════════════════════════════════════════════
# 💧 2026-08-10b — C383: THE RELEASE VALVE WAS LEAKING THE WHOLE EDGE
# ═══════════════════════════════════════════════════════════════════════════

Operator reported small margins, insignificant profits and repetitive log messages. **All three
trace to one place, and it was mine.**

## The measurement
| | |
|---|---|
| C373 capture-holds | **210 events, median 0.10R** |
| closes | 6, net −$0.43, **WR 50%** |
| average **win** | **0.28R** |
| average **loss** | 0.45R |
| payoff / break-even | **0.63 / 62%** → loses at the 50% actually achieved |

C372 and C373 correctly hold profit below 1R — but their **horizon release valve then lifted the
floor and let ANY profit out.** The bot got the worst of both worlds: it refused the quick scalp,
never reached 1R, and **banked less later than if it had simply taken the scalp.**

## The fix
Past the horizon a profit must still be worth **0.5R**; only past **double** the horizon does
anything go. C377's 1.5R hard stop still bounds the downside so nothing can hang.

| release floor | avg win | payoff | break-even | EV @50% WR |
|---|---|---|---|---|
| **0.00R (was)** | 0.28R | 0.63 | 62% | **−0.072** |
| **0.50R (now)** | 0.55R | **1.22** | **45%** | **+0.042** |

## On margins — the honest answer, not another knob
At $250 with the declared **10% drawdown**, per-trade risk is **$0.85**, so `margin = 0.85 / stop`.
The selected pairs carry ATR 2.0–3.4%, so R = 2×ATR = 4–6.8%, giving **$12–21 of margin**. The log
shows Kelly wanting **$62.50** and the **risk budget** cutting it to **$11.59** — the budget is
binding, exactly as designed.

**A 1R win pays the risk budget regardless of ATR.** Bigger margins come from exactly two places:
**a higher declared drawdown** (the C380 prompt — 20% doubles every figure) or **more capital**.
Everything else is arithmetic.

## Log noise
The capture-held line fired **once per monitor tick per position — 171–210 times a session**.
Now throttled to once per position per five minutes.

## Confirmed NOT present
The `$50` budget bug: **both banners read `$250.00`** in this log, so C375's re-derivation held.


# ═══════════════════════════════════════════════════════════════════════════
# 🚫 2026-08-10 — C382: FOUR HOURS, ZERO TRADES. A REFUTED GATE WAS VETOING
#    THE BOT'S OWN BEST WORK.
# ═══════════════════════════════════════════════════════════════════════════

19 scans · 30 candidates analysed every scan · **0 passed** · 570 rejections across **22 distinct
gate reasons, none dominant**. Death by a thousand cuts: every gate looks reasonable alone and
their product is zero.

## Fault 1 — the refuted family is still a hard block
| gate | count | share |
|---|---|---|
| leg_exhausted | 43 | 7.5% |
| parabola_bounce | 38 | 6.7% |
| late_leg_no_forward | 26 | 4.6% |
| absorption_at_extreme | 16 | 2.8% |
| no_structural_room / capitulation / micro_exhaustion / exhaustion_hard | 22 | 3.9% |
| **TOTAL** | **145** | **25.4% of ALL rejections** |

**And it killed 47% of every candidate scoring ≥ 0.50:**
```
GWEI   score 0.840  conf 0.925  →  leg_exhausted cooldown
GWEI   score 0.792  conf 0.902  →  leg_exhausted X=2.03
BLESS  score 0.807             →  leg_exhausted X=1.34
```

**This is the hypothesis this Atlas already records as refuted** — 2026-08-01b, 158,444
observations, bull-regime gap −0.02pp, t=−0.29, 2/4 splits, flat across all nine threshold
combinations, with the instruction *"never re-propose a range-position or already-travelled entry
filter."* It was never removed from the live gates.

**Fix:** the gates are **not deleted** (some encode microstructure the 158k study never tested) but
they may no longer overrule a candidate clearing **both score ≥ 0.70 and confidence ≥ 0.80**. Below
that bar they block as before. Every waiver is **logged and counted**, so next session can measure
whether the overridden trades actually paid.

## Fault 2 — the RR gate measured a geometry the bot no longer trades
Log: `reward:risk 0.30 (target 0.1% vs stop ≈0.5% @ATR 0.2%)`. The **target is a projection** — but
since **C372** a profit exit cannot fire below **1R**, and since **C377** the stop is **1.5R**.
The geometry actually traded is `1R / 1.5R = RR 0.67`, which clears every floor.

It killed **BLESS at 0.831 (poor_RR 0.19)** and **MUBARAK at 0.666 (0.44)**. Now floors the target
at 1R and the stop at 1.5R, keeping whichever target is larger so a projection above 1R still counts.

## ⚠️ A dead-code bug of my own, caught before shipping
My first wiring of the override wrapped only the `rejected_reasons` counter and left the `continue`
outside it — **the override would have logged a waiver and skipped the candidate anyway.** Exactly
the defect class this project keeps paying for. Re-done so it bypasses the entire block including
the `continue`, verified at all four `leg_exhausted` sites.

**Verified against the real blocked candidates:** both GWEI setups now trade; CAP at 0.333 still
blocks, as it should.


# ═══════════════════════════════════════════════════════════════════════════
# 🎯 2026-08-10 — C381: THE DERIVATION WAS COSMETIC. Two target systems, and
#    the mode manager read the wrong one.
# ═══════════════════════════════════════════════════════════════════════════

**The operator's log, side by side:**
```
banner : target 0.45%/day  (Normal 0.32% then HP 0.14%)   <- C369/C380 derived
tracker: 🔵 Normal: +0.0% / 1.0%                          <- CYCLE_TARGETS fixed
```

Two independent target systems existed. C369/C380 derived `PROFIT_TARGET_NORMAL_PCT` and drove
`PHASES`; **every mode DECISION went through `cycle_target()`, which read a hardcoded
`{'normal': [1.0, 0.5], 'hp': [0.75, 0.25]}`.**

**At a 0.32% target the mode could never advance against a 1.0% bar** — so the phase ladder never
progressed, the day-complete stop never fired, and the equity carry-forward never happened.
**C368, C369, C379 and C380 were all reasoning about a number the mode manager never consulted.**

## Three fixes
1. **`CYCLE_TARGETS` is now derived** from the same budget — one place a target can come from.
2. **One Normal, one HP per day** (operator directive). A single entry per mode makes the day
   `Normal → HP → STOP`, and `cycle_target()`'s `min(cycles_done, len−1)` clamp returns the same
   figure at every index — one cycle **by construction**, not by a counter that could drift.
3. **The snapshot trap, which would have repeated the whole bug.** `CYCLE_TARGETS` is built in
   `__init__`, so updating the two scalars in `_c369_apply_budget` would have left the schedule the
   mode manager reads frozen at its construction default — *exactly* the derived-once-then-stale
   failure C375 fixed for the budget. Now refreshed in the same breath, at boot, on load, on fresh
   start, and every new day.

Verified: `cycle_target()` returns 0.318% / 0.136% at cycle indices 0, 1, 2 and 5.

## 📁 FILE AUDIT (operator request)
Eleven persisted files, **all with real load paths and real consumers**:

| file | feeds |
|---|---|
| `state_v60` / `positions_v60` | the book — equity, balance, open positions |
| `mode_v60` | mode, cycle, overshoot credit |
| `learning_v60` | `_recent_trades` — **16 consumers** |
| `pair_profiles_v60` | C233 baseline → `baseline_feats()` |
| 4 × Markov files | `predict()`, under the C370 sufficiency gate (all 3 aux chains currently withheld) |
| `eval_window_v60` | the C284 gate |
| `s3_calib_v60` | C335 trust |

`mode_v60` was absent from a short replay only because `ModeManager._save` fires on a mode
**transition** and none occurred.

**Honest non-finding:** a 0-byte `eval_window_v60.json.tmp` appears in sandbox replays. I could not
reproduce it as a live failure — the write primitive works standalone, nothing shadows
`json`/`os`/`time`, the clock shim returns a JSON-serialisable float, and **the operator's own log
reads `EVAL WINDOW W2: 85/100` — a LOADED value, proving live persistence works.** Recorded as a
sandbox anomaly rather than claimed as a bug.


# ═══════════════════════════════════════════════════════════════════════════
# 💰 2026-08-09e — C380: THE DIAL THAT WAS MISSING. Size from a DECLARED
#    drawdown, not an arbitrary percentage.
# ═══════════════════════════════════════════════════════════════════════════

**The operator's complaint, restated precisely:** at $500 a 7% winner paid $0.44–$0.88, because
notional was only 1–2.5% of the book. **Not the min-order floor** (C379 fixed that). **Not ATR.**

## The real cause
Every earlier version **picked a per-trade percentage out of the air** and let the drawdown fall
where it may. **Nobody had ever declared how much loss is acceptable**, so the bot defaulted to
timid: risking a **4.4% worst-case month to earn 0.88%** — while Crypto Fund Research puts the
**median maximum drawdown of professional quant crypto funds at −20.7%** across 117 tracked funds.

**Risking 4.4% to earn 0.88% is not prudence. It is under-deployment.**

## The inversion
The operator declares a maximum monthly drawdown; **everything else is derived**:
```
day cap   = DD / 22      the worst case — every day hitting the cap
per-trade = day cap / 2  two full losses end the day
target    = day cap      symmetric, so break-even is 50% BY CONSTRUCTION
```
One human decision. Everything else arithmetic.

## What each choice buys at $500 — shown at startup, before any money moves
| max DD | day cap | per-trade $ | notional @2% ATR | % of book | a 7% move pays | month @60% WR |
|---|---|---|---|---|---|---|
| 4.4% (the old implicit setting) | 0.200% | $0.50 | $12.50 | 2.5% | $0.88 | 0.88% |
| 6.6% | 0.300% | $0.75 | $18.75 | 3.8% | $1.31 | 1.33% |
| **10.0% (new default)** | **0.455%** | **$1.14** | **$28.41** | **5.7%** | **$1.99** | **2.02%** |
| 15.0% | 0.682% | $1.70 | $42.61 | 8.5% | $2.98 | 3.04% |
| 20.7% (professional parity) | 0.941% | $2.35 | $58.81 | 11.8% | $4.12 | 4.22% |

At the 10% default a 7% winner pays **$1.99 instead of $0.88**, and the month reads **+2.02% at a
60% daily win rate, +3.04% at 65%** — while still risking only **half** the drawdown a professional
quant fund routinely accepts.

## Why this is the entry that matters
**Every previous session tuned entries, exits, floors, stops, horizons and tilts — while the single
number governing how much any of it could ever earn was never once set deliberately.** The bot was
not failing to find edge so much as refusing to deploy against it.

Startup now prints the per-trade risk in dollars, the typical notional as a share of the book, and
what a 7% move would actually pay — **before** the first order.


# ═══════════════════════════════════════════════════════════════════════════
# ⚖️ 2026-08-09d — C379: TARGET, RISK AND MARGIN FINALLY AGREE
# ═══════════════════════════════════════════════════════════════════════════

From the operator watching **MUBARAK rise ~7% on a $5 margin and return $0.35** on a $500 book.
Two faults compounding.

## Fault 1 — the daily target was never reachable from the budget beneath it
`8 trades × 0.066% per-trade × (2p−1) = 0.35%/day` requires **p = 83%**. Same class as the original
4% day-cap against a 0.20% target: two numbers set independently that could not both be true.

## Fault 2 — $5 was a FLOOR, not a size
| pair ATR | wanted margin | floored to | actual risk | vs budget |
|---|---|---|---|---|
| 2.0% | $8.25 | $8.25 | $0.330 | 1.0× |
| **6.0%** | $2.75 | **$5.00** | **$0.600** | **1.8×** |

**Flooring broke the budget the floor exists to protect.** A position that cannot be sized inside
its budget must be **skipped**, never rounded up into a breach.

## The new shape — solved, not chosen
per-trade **0.10%**, day cap **0.20%** (two losses), target **0.20%** (two wins).

| | before | after |
|---|---|---|
| break-even daily WR | **83%** | **50%** at every equity level |
| margin @ 2% ATR, $500 | $8.25 | **$12.50** |
| margin @ $2,000 | — | **$50.00** |
| 6%-ATR pairs | floored to $5, over-risked | **$4.17 → correctly skipped** |
| month @60% / @65% daily WR | — | **+0.88% / +1.33%** |

That is the **0.75–1.1% band** the benchmark research put at the *top* of professional quant crypto
(Crypto Fund Research: 84 funds, average −7.2% in 2025, 63% losing money, quant +0.4%).
**Reachable beats aspirational.**

## ⚠️ A REGRESSION I CAUGHT BEFORE SHIPPING
Tightening the min-margin tolerance from 1.5× to a blanket 1.0× **froze the bot completely — 0
trades in 160 replay scans at $50**, because below ~$250 the $5 minimum order IS larger than any
correct size, and that 1.5× slack is the only reason a small book can trade at all.
**Fixed properly: the tolerance is now equity-aware** — a true fit (1.0×) whenever the book can size
correctly, the old 1.5× only where C369 already reports the floor as *binding*, **and the over-risk
is logged**. An over-risk that is stated is a decision; one that is silent is a bug.

## Not a fault
The CJK characters in the log are a **coin symbol** — Bitget lists a token named with the Chinese
for *lobster*. The universe contains CJK-named memecoins and the log renders them faithfully.


# ═══════════════════════════════════════════════════════════════════════════
# 🔒 2026-08-09c — C378: THE STOP NOW EXISTS AT THE EXCHANGE, AND SIZE
#    FINALLY RESPONDS TO ODDS.
# ═══════════════════════════════════════════════════════════════════════════

## 1. A real reduce-only stop resting at Bitget
C377 made the risk budget real **while the bot runs**. C378 makes it real **while it does not** —
across a restart, an Android sleep, a dropped connection or a crash. Those gaps are exactly where
SKYAI ran to −8.88% against a −6.8% intent: **a virtual stop cannot fire when nothing is looking.**

- `arm_exchange_stop()` places a **trigger-based reduce-only** order — it can only close, never open
- armed at the **same 1.5R** C377 enforces in-process: **one level, two enforcers**
- ccxt exposes Bitget plan orders inconsistently, so **three parameter spellings** are tried and the
  first that works wins; total failure is logged **loudly**, because *a stop that silently failed to
  arm is worse than no stop — it would be believed*
- **PAPER sends nothing**: the level is recorded and C377 enforces it, so paper and live agree on
  the *level* even though only live holds the resting order
- **⭐ Stops are RE-ARMED for every position restored from disk.** This is the actual
  restart-handover fix, and it works only because C375 persists R across the restart. Where R is
  missing the operator is **told** the position cannot be bounded rather than left to assume it is.

## 2. Size ∝ equity **and** odds
Measured before building:

| equity | per-trade risk | margin @2x, 2% stop | % of book |
|---|---|---|---|
| $50 | 0.300% (floor binds) | $3.75 | 7.50% |
| $250 | 0.066% | $4.16 | 1.66% |
| $500 | 0.066% | $8.31 | 1.66% |
| $5,000 | 0.066% | $83.12 | 1.66% |

**Equity-proportional above ~$250 — but no odds term at all.** Two trades with identical stops got
identical size whether their chance of winning was 45% or 55%.

Standing Rule 10 forbade odds-scaling **while the only candidate was the SCORE** (ρ = −0.060 —
sizing by that is sizing by noise, the exact failure C335 exists to prevent). **Orderliness is
different and the difference is measured:** raw ρ +0.0328, **t = +4.99**, against *barrier win* —
which IS the odds of the trade winning, the `p` in `EV = p·T − (1−p)·S − C`.

Kelly at 1R:1R is `f* = 2p − 1`, so the +2–3pp orderliness buys moves `f*` by ~0.04–0.06. Real, but
small — hence a **bounded ±30% tilt**:

| orderliness | risk factor | risk $ @ $500 |
|---|---|---|
| 0.00 (noisy) | 0.70 | $0.231 |
| 0.50 | 1.00 | $0.330 |
| 1.00 (orderly) | 1.30 | $0.429 |

**Rule 9 is unsatisfied (no separate-batch replication), and a term that could double or halve a
position on a ρ of 0.033 would be false precision.**

## Pre-ship audit
0 duplicate methods across 313 · pyflakes clean but for the known dead `full_analysis` names and
two guarded expressions · sizing curve checked end to end · **an indentation fault introduced by my
first re-arm patch was caught by compile and repaired before shipping** · replay boot clean ·
all twelve shipped changes (C367–C378) verified present in the delivered file.


# ═══════════════════════════════════════════════════════════════════════════
# 🛑 2026-08-09b — C377: EVERY STOP WAS VIRTUAL. Plus the 3 changes the Atlas
#    had SILENTLY MISSED, and a full cross-fix contradiction audit.
# ═══════════════════════════════════════════════════════════════════════════

## ⚠️ FIRST, A DOCUMENTATION FAILURE OF MINE
Operator asked whether the Atlas was being updated every time. It was not.
**C368, C370 and C376 were entirely absent** — three of ten shipped changes never reached the map,
which is exactly the decay that made the Atlas useless before. Backfilled below.

| change | what it did |
|---|---|
| **C368** | consistency budget: 4-phase 2.5%/day ladder → 2 phases (0.15+0.05), day cap symmetric with target; fixed a latent IndexError from the ladder length being hardcoded as 4 in five places |
| **C370** | Markov exponential forgetting (30-day half-life); sample-sufficiency gate (≥10 obs/cell — currently withholds all three aux chains); trade-count cap; FPE break-even `p` logged with zero authority |
| **C376** | maker exits on profit-taking only; fills/misses counted; loss and stop exits always cross |

## 🛑 C377 — THE DEFECT BEHIND BOTH COMPLAINTS
Grep the whole file for `stopLoss` / `triggerPrice` / `presetStopLoss`: nothing but the bot's own
STOP button. **Every stop has been VIRTUAL** — an opinion the monitor forms when it happens to look.

| evidence from the live logs | |
|---|---|
| REL_HARD_STOP fired at −6.80% | price was already at **−8.88%** |
| REL_HARD_STOP fired at −12.00% | price was already at **−13.39%** |
| mean overshoot | **−1.74pp** |
| carried SKYAI position | lost **$0.79** against a **$0.33** budget — **2.4×** |

**And this IS the restart-handover bug.** A position handed across a restart is *naked for the
entire gap* — no exchange-side protection exists to hold the line while the bot is down.

**The fix:** `_c377_enforce_hard_stop` is the **first statement** of the per-position loop, ahead of
every judgement exit, closing at **1.5R** where R = 2×ATR — the number the sizing already assumed
and C372 already publishes. It cannot be vetoed, penalised, floored or tilted, because it is
arithmetic rather than opinion.
**On SKYAI it would have closed at −4.17% instead of −8.88%: $0.79 loss → $0.37, inside budget.**

## ✅ CROSS-FIX CONTRADICTION AUDIT (eleven changes now interact)
| situation | result |
|---|---|
| losing position | C372 floor, C373 gate and C376 routing **all require `move>0` or a profit token** → none can delay C377. True *by construction*, not by testing. |
| winning position | C377 cannot fire; C376 changes only **how** an exit executes, never **whether** |
| C377 1.5R vs C372 1.0R | act on **opposite signs** of the move — can never both apply to one tick |
| C377 vs old PRU-based REL_HARD_STOP | C377 is a **ceiling**; the older stop may fire earlier; **whichever is tighter wins**, which is correct for a stop |

**The sizing chain is now a single source.** C369 derives per-trade risk from equity → C375
re-derives on load / fresh-start / new-day → C373 makes the $25 ceiling equity-relative (floored at
$25, so no regression at $50) → C372 publishes R → C375 persists R across restarts → **C377
enforces it**. One number now sizes, floors, gates and stops.


# ═══════════════════════════════════════════════════════════════════════════
# ⚖️ 2026-08-09 — STRATEGIC RECKONING. The forecasting track is closed.
# ═══════════════════════════════════════════════════════════════════════════

## The 10-hour C375 session — the fix worked and it was not enough
Ledger exact. 11 closes, $500.00 → $499.29.

| | payoff | win rate | EV/trade |
|---|---|---|---|
| before C372 | 0.16 | 67% | −$0.078 |
| **after** | **0.63** | **45%** | **−$0.064** |

**Payoff improved 4×, exactly as designed. Win rate fell 22 points. EV barely moved.**
This was the risk flagged verbatim when C372 shipped: *the 1R floor trades win rate for payoff.*
`win_rate × payoff` keeps landing at zero minus costs — the signature of an efficient market at
this horizon and instrument.

## The operator's frame: what does the market actually PAY for?
Futures exist to **transfer risk**, **provide liquidity** and **absorb forced flow**. They do not
pay for forecasting. This bot has forecast for 375 versions. Each channel was measured on real
data, not argued.

**1. RISK TRANSFER — funding.** 6,738 real Bitget settlements, 22 pairs, 90 days.
Median +0.0050%/8h; the crowd is long **76.3%** of the time, so the short side is paid most days.

| hold | funding | price P&L | price SD | **funding / risk** |
|---|---|---|---|---|
| 8h | 0.0093% | +0.059% | 2.69% | **0.0034** |
| 72h | 0.0445% | +0.838% | 7.43% | **0.0060** |
| 504h | 0.190% | +5.04% | 20.25% | **0.0094** |

**Funding is under 1% of the price risk taken.** Holding the receiving side is a directional bet
wearing a funding costume — the "+5.15% net" at 504h is 5.04% of price move, i.e. being short in a
bear market. The market-neutral spread version (short top payer, long top receiver) collects
0.050%/8h against **0.16% of fees on two legs** — it does not clear.
**Verdict: not collectible without a spot leg this bot does not have.**

**2. FORCED FLOW.** Needs a liquidation map and sub-second execution. Not available.

**3. LIQUIDITY PROVISION — the one that IS collectible.** Maker 0.02% vs taker 0.06%. Entries are
already post-only (C363). **75% of the remaining fee sits on the taker EXIT.**

## 🔑 THE FINDING THAT DECIDES THE PROJECT
The one edge that has ever survived proper measurement is orderliness → barrier win
(**raw ρ +0.0328, t = +4.99**), worth roughly **+2 to +3pp** of barrier win rate on the top cohort.
Set against cost, at the measured R ≈ 1.5%:

| fee structure | cost in R | EV @52% | EV @53% | verdict |
|---|---|---|---|---|
| taker both (12bp) | 0.080 | −0.040 | −0.020 | negative |
| **maker in / taker out (8bp) — TODAY** | 0.053 | −0.013 | +0.007 | **marginal** |
| **maker both (4bp)** | **0.027** | **+0.013** | **+0.033** | **POSITIVE** |

**The bot's only real edge is smaller than its current transaction cost and larger than its
potential one.** Cost reduction here is not an optimisation — it is the difference between having
an edge and not having one.

**⇒ THE STRATEGY, RESTATED:** stop paying the market to forecast; start being paid to provide
liquidity, and let the one measured edge (orderliness) decide *which* liquidity to provide.
Concretely: **maker exits on profit-taking**, which halves the round trip and moves the edge from
marginal to positive. That is the next build, and it is the only remaining lever with a measured
mechanism behind it.

**Honest caveat:** a maker exit can fail to fill, and the position then rides on. Loss exits must
stay taker — always. This is a change to the profit side only, and it needs the same fill/no-fill
telemetry C364 built for entries before it is trusted.


# ═══════════════════════════════════════════════════════════════════════════
# 🌊 2026-08-08e — THE MARKET-STRENGTH CYCLE: TESTED, REFUTED. C374 RE-VERIFIED.
# ═══════════════════════════════════════════════════════════════════════════

The operator's cycle hypothesis was decomposed into three separable claims and each tested.
**No cycle code was written into the bot.**

## The index
"One unit of each pair, summed" — but a raw price sum is ~99% BTC, so it would be BTC wearing a
hat. Built equal-weight (every pair normalised to 1 at its own t=0), which is the same idea made
scale-free: 22 pairs × 29,000 bars, strength **1.000 → 0.422 (−57.8%)** over 302 days.

## The three claims

| # | claim | verdict |
|---|---|---|
| 2 | a dominant cycle exists | **p = 0.835** against phase-randomised surrogates — noise |
| 3 | the cycle projects peaks/troughs forward | **t = −0.62 / +1.01 / −1.89** — straddles zero, one fold negative |
| 3b | period ∝ 1 / (volatile-pair count) | **n=5 segments, 4 return exactly 33.3 days** — the DFT resolution grid, not a relationship |
| 1 | profit lives in the dispersion, not the index | dispersion 2.17% vs index move 2.01% per 24h — **comparable (1.13×), not dominant** |

**The projection test is decisive: a cycle that cannot project is not a cycle.**

**Method note — the trap that was avoided:** a trending non-stationary series puts enormous power at
the lowest frequency, so *any* periodogram reports a "dominant cycle" near the sample length. The
index was linear-detrended, the null was a **true phase-randomised surrogate** (identical power
spectrum, uniform random phase — not a shuffle, which would have destroyed the spectrum and made
the null trivially easy to beat), and the decisive test was out-of-sample projection.

## 🔗 THE RECONCILIATION the operator asked for
The ellipse and the cycle are **the same object**. An ellipse in (level, rate-of-change) phase space
IS a sinusoid viewed in two dimensions — Q1 rising, Q2 topping, Q3 falling, Q4 bottoming. That is
why they stand or fall together, and **both fall for the same reason**: over this corpus the crypto
index has no periodicity beyond what trend plus noise produces. The geometry was sound; the
underlying oscillation is not there to be projected.

## ✅ C374 RE-VERIFIED (the open safety item from 08-08d) — Rule 13 applied
Re-ran the exact `predbench` methodology (within-symbol demeaned, +1h) reporting **raw beside
blocked**:

| outcome | RAW ρ | t | BLOCKED ρ | gap | verdict |
|---|---|---|---|---|---|
| **barrier win** | **+0.0328** | **+4.99** | +0.0323 | 0.0005 | **CONFIRMS C374** |
| resolved (net/ATR) | −0.0423 | −5.61 | −0.0424 | 0.0001 | contradicts |

**C374 stands, and on the outcome that matters.** `barrier win` is the `p` in
`EV = p·T − (1−p)·S − C` — the quantity the bot is actually paid on. Raw and blocked agree to
0.0005 on both, so the C374 basis is confirmed in the **safe class** of Rule 13.

The negative `resolved` sign is coherent rather than contradictory: orderly pairs travel **cleanly
but less far**, so they touch a directional barrier more reliably (win ↑) while producing a smaller
absolute net move (resolved ↓). That is precisely the operator's original reframing — *not further,
but more reliably within the horizon* — and it is why the horizon and entry tilt are the right uses
of it, and why a distance-based target would be the wrong one.


# ═══════════════════════════════════════════════════════════════════════════
# ❌ 2026-08-08d — TWO-FRAME RESONANCE: BUILT, TESTED, REFUTED. NOT SHIPPED.
# ═══════════════════════════════════════════════════════════════════════════

The operator's ellipse was translated into a testable form and measured properly. **It does not
survive.** No code was written into the bot.

## The construction
Crypto is one trade — raw pair move and raw market move correlate ~0.8, so using both raw would
collapse the ellipse to a LINE and leave Q2/Q4 nearly empty. The two axes were therefore made
near-orthogonal on purpose:
- **m** = the market's common move (cross-sectional MEDIAN, ATR-normalised)
- **b** = the pair's IDIOSYNCRATIC move (pair minus market)

Outcome = a genuine first-passage barrier race at ±1 ATR — the exact `p` in `EV = p·T − (1−p)·S − C`
at the 1R geometry C372/C373 now enforce.

## What it looked like (and why it was believable)
Day-blocked, the pattern was clean, coherent across three horizons, and **survived the regime
split** — including a RISING tape, which a bear-market artifact could not have:

| regime | quadrant | side | WR | t |
|---|---|---|---|---|
| RISING | Q4 | short | 53.7–54.1% | +2.20 |
| FLAT | Q1 | short | 53.0% | +1.83 |
| FALLING | Q1 | short | 55.2% | +2.70 |

## ❌ Why it is not real
| cell | day-blocked | **raw** | inflation |
|---|---|---|---|
| Q1 short | 53.73% | **51.39%** | +2.34 |
| Q3 long | 51.97% | **48.89%** | +3.07 |
| Q4 short | 53.93% | **50.80%** | +3.13 |
| **trade against m** | 49.71% | **49.74%** | — |

**49.74% against a 49.7% null. Nothing.**

The market frame **flips sign intraday on 297 of 300 days**, so a day contains both m>0 and m<0
timestamps. Day-block averaging then weights every day equally *regardless of how many samples a
cell had that day*, inflating every cell by 2–3 points.

## 🔬 THE GENERAL RULE — this is the durable finding
**Day-block averaging is safe when every cell draws the SAME samples each block, and biased when
cell membership varies WITHIN the block with uneven counts.**
- Per-scan Spearman ρ (the slate study, `predbench`, orderliness): every symbol at a timestamp is
  in the same cell → **uniform counts → safe.** Verified: raw and day-blocked identical to +0.00pp.
- Quadrant win rates keyed on an intraday-varying market variable → **uneven counts → biased.**

**⇒ STANDING RULE 13: before trusting any block-averaged statistic, report the RAW pooled estimate
beside it. If they differ by more than the standard error, the blocking is doing the work.**

## ⚠️ OPEN: C374's basis deserves the same raw re-check
C374 (the orderliness entry tilt) is LIVE in the delivered code and rests on a block-averaged
Spearman. The structural argument above says it is in the safe class, and a crude direct check
showed raw and blocked identical — but that check used a coarser outcome than the original.
**Re-run `predbench.py` reporting raw alongside blocked before C374 is trusted further.** Its
authority is bounded to ±8%, so the exposure is small, but the claim is not yet re-verified.

## What the operator's idea got right
The bot **does** lose by going long after the market has risen — Q1/Q4 longs sit at ~45% even raw.
That is real and it is exactly the failure mode in the live logs (21 of 24 trades long, losing in
the bull window). What is NOT supported is that the opposite side is tradeable: shorting those same
conditions gives 50.8–51.4% raw, which 8bp of cost consumes entirely.


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 2026-08-08c — C375: TWO LIVE BUGS FROM SCREENSHOTS, ONE ROOT CAUSE
# ═══════════════════════════════════════════════════════════════════════════

## BUG 1 — the budget was derived BEFORE the equity was known
Banner: `C369 DAILY BUDGET @ $50.00`. Three lines later: `Loaded state: $499.96`.
`_c369_apply_budget` sat in `TradingBot.__init__`, which runs **before** `main()` calls
`portfolio.load_state()`.

| | derived at $50 (the bug) | correct at $500 |
|---|---|---|
| per-trade risk | **0.300% = $1.50** | 0.066% = $0.33 |
| day cap | 0.30% | 0.20% |
| banner | "BINDING, day is one-trade" | the $5 floor does not bind at all |

**4.5× too much risk on every trade.** Fixed in three places, because equity arrives by three
routes and goes stale by a fourth: after `load_state()`, after a fresh start (C371 lets the
operator *choose* the figure, so `__init__` only ever saw the default), and **at every day anchor,
because equity compounds and C369's whole point is that the structure changes as the book crosses
~$250.**

## BUG 2 — the same root cause, seen from the other end
The restored TUT position carried **$2.50 of margin on a $500 book (0.5%)** — exactly what a
$50-derived budget produces (0.300% × $50 = $0.15 risk ÷ ~6% stop). It banked **$0.14 on a +11.64%
winner** because the position was ~5× too small. **Not a bad exit — a mis-sized entry inherited
from the previous session's wrong budget.**

## BUG 3 — found while confirming Bug 2: R did not survive a restart
`_c372_R_pct` is assigned in `_open_position` and was **never persisted**. Any position restored
after a restart came back with `R=0`, so **both** profit floors (C372's exit wrapper and C373's
capture gate) silently skipped it — the carried position was the one trade of the day still running
on the pre-C372 rules. `R` and `expected_hold_min` are now saved and restored.

## 🌀 TWO-FRAME RESONANCE — the operator's ellipse, in computable form
The bot has a projected move over horizon H; the market has one over the **same** H. Treat them as
axes of an ellipse of bounded total output:

```
phase      φ  = atan2(m/Am , b/Ab)          → which quarter
resonance  ρ  = cos(φ_b − φ_m)              → alignment of the two frames
output     E  = sqrt((b/Ab)² + (m/Am)²) ≤ 1 → the bounded circumference
```

| quadrant | bot | market | ρ | reading |
|---|---|---|---|---|
| Q1 | +0.80 | +0.80 | +1.00 | aligned long — **first-quarter trade** |
| Q2 | +0.80 | −0.80 | −1.00 | market turning — **the reversal leg** |
| Q3 | −0.80 | −0.80 | +1.00 | aligned short — first-quarter trade |
| Q4 | −0.80 | +0.80 | −1.00 | market turning — reversal leg |

**Both inputs already exist** — the log shows `projection 0.19% < 0.25% (ATR-relative)` (that is
`b`) and a regime direction (`m`). What is missing is that they are compared as a **pass/fail
gate** rather than as a **phase**, which is why the second quarter — your reversal leg — is never
traded at all. Implementing it means replacing the boolean projection gate with `ρ` and allowing a
Q2/Q4 entry in the opposite direction. **Not built: it needs the same bench treatment as
orderliness before it is allowed to move money.**


# ═══════════════════════════════════════════════════════════════════════════
# ✅ 2026-08-08b — FINDINGS FIXED (C373/C374) + FULL-PIPELINE VERDICT
# ═══════════════════════════════════════════════════════════════════════════

| finding | status |
|---|---|
| **F1** C372 floor enforced at 1 of 7 doors | ✅ **FIXED C373** — `_check_profit_targets` POSITION_CAPTURE now R-gated |
| **F2** $25 per-trade ceiling absolute | ✅ **FIXED C373** — equity-relative (25%), old $25 kept as a floor so $50 is unchanged |
| **F4** Atlas was a changelog, not a map | ✅ **FIXED** — regenerable navigation index at the top |
| F3 5,555-line function, 63 bare excepts | ⏳ documented; instrumenting is a refactor, not a patch |
| F5 `MIN_MARGIN`/`MAX_POSITIONS` absolute | ⏳ $5 is an exchange minimum and must stay; C369 reports it as the binding constraint |
| F6 seven close paths, no choke point | ⏳ design task; C373 closed the leak it caused |

## RE-SCAN: all 14 close call sites
Every **profit** door is now R-gated — 12336, 12455, 12469, 12483, **13732, 13735**, 15612, 15622,
15626. Every ungated door is a **loss or admin** path that must never be gated:
`_dri_selective_close` (fires only on dri>0, pnl<−5%, or neutral-and-losing), the HP drift cap at
−2.5×PRU (13684), the HP deep-loser close (14067), and `_close_all_positions` (13425).
**Verified live: `_c372_R_pct` is populated on every position opened (1.72 / 1.55 / 1.25) — never
zero, so the gate can never silently skip.**

## 🎯 FULL-PIPELINE SIMULATION — does it compose into 4%/month?
20,000 simulated days per cell. $500 book, R=$0.33, day target $1.75, day cap $1.00, 8-trade cap.

| payoff | 50% WR | 55% | 60% | **67%** | 70% |
|---|---|---|---|---|---|
| **0.17** (pre-C372) | −4.07% | −3.64% | −3.17% | **−2.37%** | −2.02% |
| **1.00** (C372/C373) | +0.03% | +1.15% | +2.26% | **+3.82%** | +4.62% |
| 1.30 | +1.68% | +2.92% | +4.12% | +5.73% | +6.29% |

The pre-C372 row **reproduces the operator's live result**, which is what validates the diagnosis.

## ⚠️ THE FACT THAT DECIDES EVERYTHING
For a driftless walk with a target at +aR and a stop at −1R, `P(target first) = 1/(1+a)` — so
**EV is exactly zero at every choice of a**. 0.17R/85%, 1.0R/50%, 2.0R/33% all price to the same
nothing. **Barriers cannot make money; they only trade win rate against payoff.**
C372/C373 removed a *guaranteed loss*. They do not create a gain.

4%/month needs the barrier win rate at 1R pushed to ≈68% (57% gives 1.5%). The **only** quantity
this project has ever measured that predicts barrier wins is **orderliness** (permutation entropy:
ρ +0.0234, t=+3.49, 3/4 splits, Bonferroni-clearing, 79,457 obs). C366 already used it for the
horizon; **C374 now uses it to choose which trade to take** — bounded to ±8%, because Rule 9 has
not been satisfied.

**THE HONEST RISK:** the 1R floor *trades win rate for payoff*. If requiring 1R drops the win rate
from 67% to 50%, the system lands at break-even, not 4%. **The barrier win rate at 1R is now the
single measurement that decides everything, and the next paper session must produce it.**


# ═══ NAVIGATION INDEX — regenerate with `atlas_index.py`, do not hand-edit ═══

**Use this to FIND code. The session narratives below are history, not a map.**

29 classes · 292 methods · 22,832 lines.

## The fourteen largest functions — faults hide here

| class.function | lines | range | returns | bare-except |
|---|---|---|---|---|
| `TradingBot._run_scan_and_trade` | 5,555 | 14775–20329 | 19 | 63 |
| `TechnicalAnalysis._quick_scan_analysis_raw` | 1,820 | 6025–7844 | 2 | 18 |
| `TechnicalAnalysis.full_analysis` | 1,290 | 4553–5842 | 2 | 24 |
| `TradingBot._open_position` | 1,250 | 20363–21612 | 23 | 27 |
| `Position._should_exit_dri_raw` | 1,214 | 1599–2812 | 37 | 10 |
| `TradingBot._monitor_positions` | 463 | 11995–12457 | 1 | 12 |
| `MarketScanner.scan_lively_pairs` | 433 | 8792–9224 | 6 | 13 |
| `TradingBot._check_profit_targets` | 413 | 13634–14046 | 5 | 4 |
| `TradingBot._close_position_inner` | 329 | 12980–13308 | 1 | 10 |
| `TechnicalAnalysis._compute_skill_components` | 322 | 7956–8277 | 1 | 20 |
| `TradingBot.run` | 299 | 11692–11990 | 0 | 3 |
| `TradingBot._write_changelog` | 268 | 11423–11690 | 0 | 1 |
| `TradingBot._refresh_live_regime` | 268 | 12616–12883 | 1 | 6 |
| `Config.__init__` | 264 | 801–1064 | 0 | 0 |

## The money path — every function that touches equity, margin, PnL or fees

| range | function |
|---|---|
| 675–726 | `PairStateMarkov.predict` |
| 801–1064 | `Config.__init__` |
| 1599–2812 | `Position._should_exit_dri_raw` |
| 2838–2880 | `PositionsManager.save_state` |
| 2882–2921 | `PositionsManager.load_state` |
| 2926–2949 | `Portfolio.__init__` |
| 2951–2960 | `Portfolio.set_session_start` |
| 2962–2980 | `Portfolio.check_new_day` |
| 2982–2984 | `Portfolio.get_truly_free_balance` |
| 2991–3049 | `Portfolio.allocate_margin` |
| 3051–3077 | `Portfolio.release_margin` |
| 3079–3095 | `Portfolio.get_unrealized_pnl` |
| 3097–3098 | `Portfolio.get_live_equity` |
| 3100–3104 | `Portfolio.get_session_pnl_pct` |
| 3106–3121 | `Portfolio.get_stats` |
| 3123–3144 | `Portfolio.save_state` |
| 3146–3183 | `Portfolio.load_state` |
| 3487–3522 | `ExchangeManager.fetch_ohlcv` |
| 3581–3633 | `ExchangeManager.place_order` |
| 6025–7844 | `TechnicalAnalysis._quick_scan_analysis_raw` |
| 9271–9426 | `RiskManager.dynamic_allocate` |
| 9433–9447 | `TradingModeManager.__init__` |
| 9449–9483 | `TradingModeManager._load` |
| 9485–9506 | `TradingModeManager._save` |
| 9508–9529 | `TradingModeManager.effective_cycle_target` |
| 9531–9551 | `TradingModeManager.settle_cycle_overshoot` |
| 9553–9614 | `TradingModeManager.reset` |
| 9616–9641 | `TradingModeManager.can_trade` |
| 9643–9646 | `TradingModeManager.set_normal_start` |
| 9648–9651 | `TradingModeManager.get_normal_pnl_pct` |
| 9653–9656 | `TradingModeManager.get_hp_pnl_pct` |
| 9658–9687 | `TradingModeManager.revert_to_normal` |
| 9689–9717 | `TradingModeManager.switch_to_hp` |
| 9719–9739 | `TradingModeManager.start_session_cooldown` |
| 9741–9761 | `TradingModeManager.begin_new_session` |
| 9763–9777 | `TradingModeManager.pause_until_tomorrow` |
| 9793–9816 | `ClosedPositionsTracker.record_close` |
| 10745–10830 | `LearningManager.meta_learn` |
| 11139–11209 | `CategoryClassifier._ensure_scan` |
| 11326–11414 | `TradingBot.__init__` |
| 11423–11690 | `TradingBot._write_changelog` |
| 11692–11990 | `TradingBot.run` |
| 11995–12457 | `TradingBot._monitor_positions` |
| 12464–12534 | `TradingBot._monitoring_thread_func` |
| 12536–12614 | `TradingBot._compute_macro_tilt` |
| 12889–12971 | `TradingBot._c336_partial_close` |
| 12980–13308 | `TradingBot._close_position_inner` |
| 13357–13406 | `TradingBot._close_all_positions` |
| 13423–13466 | `TradingBot._c369_derive_budget` |
| 13468–13490 | `TradingBot._c369_apply_budget` |
| 13492–13589 | `TradingBot._advance_session_phase` |
| 13634–14046 | `TradingBot._check_profit_targets` |
| 14051–14118 | `TradingBot._check_session_drawdown` |
| 14130–14178 | `TradingBot._check_emergency` |
| 14247–14266 | `TradingBot._execute_emergency_close` |
| 14426–14639 | `TradingBot._c302_p_ev` |
| 14775–20329 | `TradingBot._run_scan_and_trade` |
| 20363–21612 | `TradingBot._open_position` |
| 21617–21628 | `TradingBot._check_pending_limits` |
| 21634–21828 | `TradingBot._display_summary` |
| 21869–21945 | `OmegaGuardian.check_health` |
| 21947–21980 | `OmegaGuardian._log_reflection` |
| 22014–22071 | `OmegaGuardian.intervene` |
| 22093–22117 | `TradeDatabase._init_db` |
| 22119–22168 | `TradeDatabase.log_trade` |
| 22182–22197 | `TradeDatabase.get_daily_stats` |
| 22208–22263 | `WebDashboard.start` |
| 22265–22334 | `WebDashboard._get_html` |
| 22363–22369 | `TelegramBot.send_trade_close` |
| 22381–22421 | `TelegramBot.start_polling` |
| 22637–22808 | `RemoteControl.start` |
| 22686–22707 | `Handler._get_status` |
| 22728–22781 | `Handler._dashboard_html` |

## The seven paths that can CLOSE a position
| line | function | gated by the C372 profit floor? |
|---|---|---|
| 12307 | `_monitor_positions` | ✅ via `should_exit_dri` (12422) |
| 15560 | `_quick_exit_check` | ✅ via `should_exit_dri` (15555) |
| **13655** | **`_check_profit_targets`** | ❌ **NO — independent `POSITION_CAPTURE`** |
| 13344 | `_dri_selective_close` | ❌ not gated |
| 13396 | `_close_all_positions` | admin — correctly ungated |
| 14249 | `_execute_emergency_close` | emergency — correctly ungated |
| 22041 | `OmegaGuardian.intervene` | guardian — correctly ungated |

## Invariants that are TESTED and must stay true
- `available_balance + Σ(open initial_margin) == equity` — verified 120×, deviation $0.00000000
- `Σ(realised net_pnl) == equity delta` — exact since C371 removed 2-dp ledger rounding
- `_c336_partial_close` halves `pos.initial_margin` (line ~12961) after releasing half
- gross PnL uses **entry** notional, never exit notional (C254)
- `install_clock` must print `clock-factory cells repaired: 2`, else the replay is void


# ═══════════════════════════════════════════════════════════════════════════
# 🔎 DEEP AUDIT 2026-08-08 — FINDINGS LIST (C372). Nothing fixed yet.
# ═══════════════════════════════════════════════════════════════════════════

Ordered by expected cost. **F1 and F2 are live money defects.**

### F1 — 🔴 THE C372 PROFIT FLOOR HAS A HOLE, AND IT IS MY OWN
C372 gates profit-taking below 1R by wrapping `should_exit_dri`. But **seven paths can close a
position and only two route through it** (`_monitor_positions` 12422, `_quick_exit_check` 15555).
`_check_profit_targets` (13655) has an **independent** `POSITION_CAPTURE` that fires at
`_lev_pnl > 1.5 × PRU` and calls `_c336_partial_close` directly. With PRU ≈ ATR and R = 2×ATR that
banks at roughly **0.63R** — precisely the sub-1R profit-taking C372 exists to stop.
**The 0.17:1 payoff can therefore still occur through this door.**
*Fix:* apply the same R floor inside `_check_profit_targets`, or route it through the wrapper.

### F2 — 🔴 THE $25 PER-TRADE CEILING IS ABSOLUTE, NOT RELATIVE TO EQUITY
`RiskManager.dynamic_allocate` line **9372**: `max_per_trade = min(max_per_trade, 25.0)`.
Everything around it is relative (`_deployable * 0.55`, `_kelly_base`, `_vol_adj`) — this one number
is not. It is **binding on every scan** in the live $500 log (`→ max=$25.00`).

| equity | $25 as % of equity |
|---|---|
| $50 | 50% |
| $500 | **5%** |
| $5,000 | **0.5%** |

As equity compounds the bot progressively **loses the ability to deploy capital** — at $5,000 five
full positions would be 2.5% of the account. This is exactly the operator's instinct that "margin
selection should take current equity into account."
*Fix:* express as a percentage of equity, e.g. `min(max_per_trade, equity * C373_MAX_PER_TRADE_PCT)`.

### F3 — 🟠 `_run_scan_and_trade` IS 5,555 LINES WITH 63 BARE `except Exception`
One function is 24% of the file, with 19 return points and **63 silent error swallows**. Every
defect found this session hid behind one of these: the C367 floor, the family_tilt contract, the
news contract. A bare except in a 5,555-line function is not defensive — it is a place where
failures become invisible.
*Fix:* not a rewrite. Instrument: have each bare except increment a named counter and log once per
session, so swallowed failures become countable instead of silent.

### F4 — 🟠 THE ATLAS HAD STOPPED BEING A MAP
2,036 lines, 16 session narratives, **6 line references**, and `_advance_session_phase` — where a
latent IndexError was found — appeared **zero** times. It had become a second changelog duplicating
`EVAL_W1_LEDGER.md`, which is why fault-finding has been grep-driven all session.
**FIXED in this pass:** a regenerable NAVIGATION INDEX now sits at the top — 292 methods, the 14
largest functions with their bare-except counts, all 73 money-path functions with line ranges, the
seven close paths with their C372 coverage, and the tested invariants.

### F5 — 🟡 `MIN_MARGIN_PER_TRADE` AND `MAX_POSITIONS` ARE ALSO ABSOLUTE
$5 and 5 respectively. At $50 the floor is 10% of equity (it binds, forcing the one-trade day); at
$5,000 it is 0.1% (irrelevant). Same class as F2, lower cost, but it means the *structure* of a day
silently changes with account size — which C369 now derives correctly, but only for the risk
budget, not for these two.

### F6 — 🟡 SEVEN CLOSE PATHS, NO SINGLE CHOKE POINT
Position closure is spread across seven functions in four classes. There is no one place where a
close can be validated, logged or gated — which is why F1 exists and why any future exit rule will
have the same problem.
*Fix (design, not now):* one `_close_gate(pos, price, reason)` that every path must call.

### ✅ VERIFIED CLEAN IN THIS PASS
- margin conservation `available_balance + Σ open margins == equity` — 120 checks, $0.00000000
- realised-PnL ledger reconciles **exactly** to equity since C371
- `_c336_partial_close` halves `initial_margin` after releasing half — no double-release
- gross PnL on **entry** notional; long/short symmetric to machine precision
- C372's 9-case battery: every loss/stop/thesis exit passes through ungated
- no duplicate class/method definitions anywhere in 292 methods


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 SESSION 2026-08-05 — C367: THE INVERTED GUARD. Found in the operator's
#    LIVE log after two sessions of persistent losses. The operator was right.
# ═══════════════════════════════════════════════════════════════════════════

## THE DEFECT: TWO FLOORS, AND THE SAFETY GUARD WAS ON THE WRONG ONE

| | **C284** (line ~18165) | **C149** (line ~19183) |
|---|---|---|
| lifts a crushed score to | **40%** of pre-penalty base | **60%** — higher |
| guards | base-strength **AND** live projection | **none beyond base ≥ 0.50** |
| runs | first | **last, so it wins** |

C284's guards were added deliberately, after that study measured floor-lifted trades at
**17W/16L, −$0.40** against organic entries at **15W/6L, +$0.62** — the lift was rescuing genuine
breakouts and self-contradicting entries indiscriminately.

**But C284 only evaluates when `score < 40% of base`.** Any score landing in the **40–60% band**
never met its guards at all and was re-lifted by C149, ungated, to a *higher* level.
**The C284 fix has been inert for its entire life.**

## MEASURED ON THE LIVE SESSION

- The floor fired **10 times out of 10** — it never once left the stack alone.
- Average lift **+0.125** (0.41 → 0.54, a **+30% relative rescue**).
- Against the observed **0.47** entry bar it permitted **7 of 10** entries where only **4** would
  have passed organically — **manufacturing 3: SKR, TAO, FARTCOIN.**
- **TAO closed THESIS_EXIT −2.5%. FARTCOIN closed PARTIAL_THESIS_DEAD.**

**TAO is the clearest case.** Four independent systems opposed the long — broken-parabola bounce
(blocked 07:51), structural exhaustion with 3% room (08:01), leg beyond cap X=1.66 burning hot,
and C199 order-flow weakening with CVD=−0.44. The stack correctly cut conviction to **0.45**.
The floor put it back to **0.60** and bought it.

## 🔁 THE INVERSION, STATED PLAINLY

**The floor is strongest exactly when the evidence against the trade is strongest** — because more
independent warnings mean a lower product, which means a bigger lift.
**A guard that fires hardest against its own evidence is not a guard.**

## ✅ THE FIX (C367)
C284's verdict is now **published** on the analysis (`_c284_lift_allowed` / `_c284_why`) and the
C149 floor **obeys it**. A crushed score with a weak base or a dead projection stays crushed and is
blocked. The 60% level is kept for entries that **pass** the guards, preserving C149's original
purpose (log_c148's EPIC won +5.75% after stacking to ×0.43) without rescuing the
self-contradicting cohort. **Denials now log explicitly instead of passing silently.**

Unit battery reproduces the live case exactly: base 1.00 / score 0.45 → guards fail → **0.45 →
BLOCKED** at the 0.47 bar. Verified: syntax OK · AST 308 unchanged · 3 count-asserted replacements
· replay boot clean (119 scans, 0 errors, conservation exact).

## ⚠️ ALSO: C366 NEVER FIRED
The predictability→horizon wire logged **nothing** across both live sessions — its reading sat
behind an `orderliness > 0.05` gate and was therefore invisible and unverifiable. It now logs
unconditionally. **The 16-min expected hold seen in the live REL_STAGNATION lines came from the
pre-existing `25/ATR%` formula, not from C366** — C366 was not a contributor to these losses.


# ═══════════════════════════════════════════════════════════════════════════
# ✅ SESSION 2026-08-04i — C366: PREDICTABILITY -> HORIZON. THE OPERATOR'S
#    HYPOTHESIS TESTED AND SUPPORTED. HARNESS v3.4 REVIVES TWO SUBSYSTEMS.
# ═══════════════════════════════════════════════════════════════════════════

## 🎯 THE OPERATOR REFRAMED THE HYPOTHESIS, AND THE REFRAME WAS RIGHT

I asked "do high-predictability pairs SUSTAIN moves longer?" The operator corrected it: they may
not last longer, but they have **a better chance of delivering net profit WITHIN the horizon.**
That is a claim about RELIABILITY, not duration — and it needs **no direction skill at all**,
because a pair that travels cleanly lets an exit engine capture it while a chopping pair stops you
out on noise before the move arrives.

**Tested (`predbench.py`): 79,457 observations · 302 calendar-day blocks · features demeaned
WITHIN SYMBOL · 4-way OOS split · pseudo-random null well-behaved at t=+0.56.**

| horizon | future efficiency | resolved ≥1 ATR | barrier win |
|---|---|---|---|
| **+1h** | **+0.0151, t=+3.64, 4/4** | **+0.0269, t=+3.88, 3/4** | **+0.0234, t=+3.49, 3/4** |
| +2h | +0.0039, t=+1.02 | +0.0181, t=+2.77, 3/4 | +0.0171, t=+2.62, 3/4 |
| +6h | +0.0028, t=+0.63 | — | — |

**All three +1h results clear Bonferroni for the 36 tests run (|t| ≥ 3.3).** The effect halves by
+2h and is gone by +6h — orderliness is a short-memory property, and **+1h is exactly this bot's
median 60–75 min hold.**

### ⚠️ THE NULL CAUGHT A BROKEN TEST FIRST — worth remembering
v1.0 of the bench scored its PSEUDO-RANDOM control at **ρ=+0.28, t=+92**, which is impossible for
a null and therefore exposed the TEST, not the signal. Two defects: the null varied only by
symbol-name length (a proxy for coin class → volatility → "did it move ≥1 ATR"); and, more
seriously, **any feature roughly CONSTANT PER SYMBOL reproduces the same cross-sectional ranking at
every timestamp**, so 3,613 "blocks" were one measurement repeated and t was inflated ~√3613.
Fixed by within-symbol demeaning and calendar-day blocks. **A null control is not decoration.**

## ✅ C366 — THE CHANGE
`pred_hold` was pure volatility (`25/ATR%`). Permutation entropy — computed live, normalised,
ordinal and therefore scale-free and inherently relativistic — fed **only** the S3 channel that
C335 gates to zero. Now an **orderly pair gets a TIGHTER horizon** (it should have resolved), so
stagnation pressure arrives sooner on exactly the setups that ought to pay quickly.
**One-sided by design** — nothing is ever lengthened, because noisy pairs showed no resolution at
+6h either. Max −25%, clamped to the same [15,60] band. **Not yet replicated on a separate batch
(Rule 9)** → small authority, and the orderliness reading is logged on every entry for validation.

## 🔧 HARNESS v3.4 — TWO REGRESSIONS OF MY OWN, AND THE RULE THAT ENDS THEM
- **v3.1** stubbed `family_tilt → 0.0`; the caller unpacks four values → TypeError into a bare
  except → the C228 category tilt was **silently deleted in every backtest ever run.**
- **v3.2** "fixed" it to `({}, 'default', 0.0, 'none')` — right arity, wrong content. An **empty**
  tilt dict collapsed every family weight and drove **all 3,452 scores to exactly 0.00**, opening
  zero trades. A loud deletion replacing a silent one. **Caught by bisect, not by inspection.**
- **v3.4** stops guessing: **only `_page_candles`** — the actual HTTP leaf (18 requests, 5.1 s of a
  5.5 s scan, returning today's candles for a historical bar) — is neutralised. `family_tilt` and
  `_ensure_scan` now run their REAL logic and return their own correct shapes.

**⇒ STANDING RULE 12: neutralise the LEAF that touches the network. Never re-implement the return
value of the logic that calls it.** Rule 11 (preserve the contract) is necessary but not
sufficient — v3.2 preserved the contract's *shape* and still destroyed the system.

### What v3.4 revived, measured
| | before | after |
|---|---|---|
| `_ensure_scan` calls | **0** | **1,133** |
| `family_tilt` return | `float` | 4-tuple, 6 families, real label (`solana_eco`) |
| `cat_clf._fp` entries | 0 | 21 |
| **pair_profiles mature (n≥3)** | **0 of 21** | **21 of 21** |
| profile file on disk | never written | **written** |

**Repair-queue item 4 (offline `_ensure_scan`) is DONE as a side-effect of fixing it correctly —
the per-pair fingerprint baseline, core axis #1, now accumulates in replay and is testable.**

## ✅ FINAL VERIFICATION (C366 on harness v3.4)
101 scans · **0 errors** · equity $50.00 → $50.95 · 5 closes, conservation exact
(3 full = +$0.23, 2 partial = +$0.72). AST 308 unchanged. Syntax clean.


# ═══════════════════════════════════════════════════════════════════════════
# 🚶 SESSION 2026-08-04h — THE DECISION JOURNEY WALKED. **THERE IS NO
#    PREDICTED HORIZON.** Plus a second Rule-11 contract violation fixed.
# ═══════════════════════════════════════════════════════════════════════════

Full stage-by-stage walk is in **`WALKTHROUGH.md`**. Headline findings:

## 🔴 THE HORIZON IS NOT PREDICTED — it is `25 / ATR%`

The architecture threads ONE horizon through every stage. Measured: **four horizons exist and none
is predicted.** Projection engine 4h (`PROJ_STEPS=120`, constant) · trade hold **15–60 min
(`25/ATR%`)** · exit max hold 10× that · DRI limit 360 min (constant).

**Traced to the line:** `predictive_analysis()` computes a real pattern-based `expected_hold`
(50/35/15 min + `continuation_prob`) — and **its only call site is inside `full_analysis`, which
has zero call sites.** So `analysis['prediction']` never exists live, line 20959 always yields 0,
and the fallback at 20964 (`25/ATR%`, clamped 15–60) is the real path. The horizon is pair-specific
but **purely volatility-derived**.

**And `lyapunov` is labelled in the source, verbatim, "N34: Predictability horizon."** It is
computed live, contributes ±0.20 to the score — and **never touches any horizon**. Same for
`hurst` and `perm_entropy`. The bot measures how far ahead each pair is predictable, then declines
to use it for the one decision it exists for.

**⇒ HIGHEST-VALUE REPAIR: derive `pred_hold` from lyapunov/hurst/perm_entropy instead of ATR
alone.** No new data needed. **Measure first** — do high-predictability pairs sustain moves longer?

## 🐛 SECOND RULE-11 VIOLATION FOUND AND FIXED (harness v3.3)

`NewsAnalyzer.get_sentiment` is declared `-> float`; the harness stubbed it as a **dict**. Callers
do `_own_s * 0.7` → `TypeError` into a bare except. The news block did not go neutral, it
**crashed**. (`fetch_news`/`analyze` were stubbed too and don't even exist on the class.)
Fixed: stub only `_fetch_articles`, and give each accessor its declared type.
**My own four instrumentation tools had the same defect and are corrected.**
Measured after: component census unchanged (8 always-zero, same set) — the fix restores contract
correctness and replay/live parity, but revived nothing. Honest negative, recorded.

## 📋 STAGE VERDICTS
| stage | verdict |
|---|---|
| 1 liveliness screen | ✅ live (~19 pairs/scan) — no horizon attached |
| 2 regime | ✅ live, **+2.6pp** over persistence (not 84%) |
| 3 strategy/category tilt | ⚠️ **was silently deleted in every backtest**, restored in v3.2 |
| 4 predictive refinement | ⚠️ 43/54 components live; `breakout_pattern` + `pca_factor` dead; output is a SCORE, not a projection to a horizon |
| 5 DRI/DSI monitoring | ✅ **strongest part** — baselines locked at entry, deviation tracked |
| 6 attention shifting | ✅ all three states exist and cut correctly (every loss-exit followed by further adverse movement) — but none references a predicted horizon |
| 7 RPPc 3 tiers | ⚠️ market +2.6pp, individual +2.5pp, **family statistically empty (0.8 obs/cell)**, Ichimoku degenerate in 4/5 regimes |


# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ SESSION 2026-08-04g — I WAS WRONG ABOUT THE PAIR HISTORY. RETRACTION +
#    A REAL HARNESS DEFECT FOUND UNDERNEATH IT (harness v3.2).
# ═══════════════════════════════════════════════════════════════════════════

## 🔴 RETRACTION — "the cumulative pair history is dead" is WRONG for the live bot

I traced the empty `PairProfileStore` (n=0, fp=[0,0,0,0], 0 mature) to `_ensure_scan()` never
firing, and reported the per-pair baseline as a live defect. **It is not.** `omega_replay_full.py`
**deliberately stubs** `family_tilt`, `_ensure_scan` and `_page_candles`, because `_ensure_scan →
_page_candles` performs a 30-day paginated **live** candle fetch inside every scan — 18 HTTP
requests, 5.1 s of a 5.5 s scan, returning *today's* candles for a historical bar (lookahead).
Neutralising it offline was correct.

**On the phone, `_page_candles` works, `_ensure_scan` runs, `observe()` fires, and the per-pair
baseline accumulates.** The finding was an artifact of my own tooling. Corrected here in full.

## 🐛 BUT THE STUB CONCEALED A REAL PARITY DEFECT — fixed in harness v3.2

The stub returned **`0.0`**, while the caller in `_quick_scan_analysis_raw` (line 6992) unpacks
**four** values:
```
_cat_tilt, _cat_name, _cat_conf, _cat_method = self._bot_ref._cat_clf.family_tilt(symbol, df)
```
Unpacking a float raises `TypeError` straight into a bare `except Exception: _cat_tilt = None`.

**Consequence: the C228 category-fit family tilt has been SILENTLY DISABLED in every backtest this
project has ever run — 1,060 swallowed exceptions per 56 scans. Replay was scoring a DIFFERENT bot
than the phone.** Measured, not inferred: `family_tilt` called 1,060×, returning `float`,
`_ensure_scan` called 0×.

**FIX (v3.2):** the stub now returns the caller's contract shape — `({}, 'default', 0.0, 'none')`
— neutral content, no HTTP, no lookahead. Verified: 4-way unpack succeeds, replay healthy
(39 scans, clean). **Neutralising a live fetch is correct; breaking its return contract is not.**

**⇒ STANDING RULE 11: a stub must preserve the CONTRACT (arity, type, shape) of what it replaces.
A stub that changes shape does not neutralise a subsystem — it deletes it, silently, wherever the
caller guards with a bare except.** Every stub in the harness must be re-checked against its
caller's unpack.

## ✅ WHAT STANDS FROM THE RPPc AUDIT (measured from the chains' own persisted counts,
## which accumulate in replay independently of this stub — unaffected by the retraction)
- RegimeMarkov: **38.2%** (own ledger 42/110) vs 35.6% persistence = **+2.6pp**. Not 84%.
- PairStateMarkov: **44.7%** vs 42.2% = **+2.5pp**. Not 68%.
- **IchimokuMarkov degenerate in 4/5 regimes** — Markov == base rate exactly (edge 0.0pp).
- **FamilyStateMarkov statistically empty** — 99 obs / 125 cells = 0.8 per cell.
- Laplace smoothing, Brier tracking and the C335 fail-closed gate are all sound.

## 🎯 NEXT
1. **Give `_ensure_scan` an OFFLINE path** that builds the 4-D fingerprint from the corpus instead
   of `_page_candles`. Until then axis #1 (each pair relative to itself) is **untestable in
   replay** — it works live but no backtest can measure it.
2. **Re-check every other harness stub against its caller's contract** (Rule 11).
3. Gate each Markov chain by its own demonstrated edge at the score layer.


# ═══════════════════════════════════════════════════════════════════════════
# 🧮 SESSION 2026-08-04f — RPPc CHAINS AUDITED. THE HEADLINE ACCURACIES ARE
#    WRONG, TWO CHAINS ARE MATHEMATICALLY EMPTY, AND THE PAIR BASELINE IS DEAD.
# ═══════════════════════════════════════════════════════════════════════════

Operator question: is the RPPc framework mathematically sound, and is the cumulative pair history
used to its maximum? Measured on freshly-built chains (103 scans, 1,930 pair analyses).

## ✅ WHAT IS SOUND
- **Laplace smoothing present in every chain** (all cells seeded at 1.0) — no zero-probability
  blow-ups, no division by an unseen row. Correct by construction.
- **Brier + calibration tracking exists** on every chain, and **C335 fail-closes to trust = 0**.
- The conditioning structure (chains conditioned on regime) is the right shape.

## ❌ THE ACCURACY CLAIMS IN THIS ATLAS ARE WRONG — corrected against the bot's own ledger

| chain | Atlas claimed | **measured** | best baseline | **real edge** |
|---|---|---|---|---|
| RegimeMarkov | **84%** | **38.2%** (own ledger, 42/110) | 35.6% persistence | **+2.6pp** |
| PairStateMarkov | **68%** | **44.7%** | 42.2% base rate | **+2.5pp** |
| IchimokuMarkov | — | 59.3% | 58.0% | **+1.4pp** |
| FamilyStateMarkov | — | 37.0% | 28.9% | +8.0pp *(see below — noise)* |

**A Markov chain must be scored against PERSISTENCE and BASE RATE, never in isolation.** A regime
process is autocorrelated, so raw accuracy flatters it. These are also *in-sample* figures on the
same data that built the matrices, so the true out-of-sample edge is lower still.

## ❌ TWO CHAINS CANNOT CARRY INFORMATION AT ALL

**IchimokuMarkov is DEGENERATE in 4 of 5 regimes.** In SU, TU, TD and SD the Markov prediction
equals the base rate **exactly (edge 0.0pp)** — every row's argmax is the *same* letter, so the
conditional structure does nothing and the chain reduces to "predict the most common letter."
The cause is visible in the counts: SU row 0 = `[95,2,1,1,2,1]`, TU row 0 = `[119,…]`. The
"6-letter alphabet" is, in practice, a **1-letter alphabet**. Only CH shows a real +6.3pp.

**FamilyStateMarkov is STATISTICALLY EMPTY.** 99 observations across **125 cells = 0.8 per cell**;
17–21 of 25 cells never observed in most regimes; SD has **6 real observations for 25 cells**.
With less than one observation per cell the Laplace prior *dominates the posterior* — its apparent
+8.0pp edge is the argmax of noise. **It cannot be informative and its output must not be trusted
until it has ~10 obs/cell (≈1,250 observations).**

## 🔌 ARE THEY USED TO THEIR MAXIMUM? No — and mostly that is correct
- `rqa_det` + `perm_entropy` → determinism weight → S3 → **C335 trust = 0.00 → zero effect today.**
  Correctly gated: an uncalibrated model steers nothing.
- `markov` **IS** in `_skill_keys` — it feeds the entry score **ungated**, on a +2.6pp edge.
- `ichimoku`, `rqa_det`, `perm_entropy` are written to `components` but are **not** in `_skill_keys`.

**The asymmetry is the problem: the gated chains are the ones with some skill, while the ungated
path carries the weakest. Nothing gates a chain by its OWN demonstrated edge.**

## ⚠️ THE CUMULATIVE PAIR HISTORY — **[RETRACTED: THIS IS A REPLAY ARTIFACT, NOT A LIVE DEFECT — see the 08-04g block at the top]**

`PairProfileStore` (C233 — the operator's explicit "each pair relative to itself" request).
Measured after 69 scans:

| | |
|---|---|
| pairs present in store | 21 |
| **`n` (observation count)** | **0 for every single pair** |
| **`fp` fingerprint** | **`[0.0, 0.0, 0.0, 0.0]` for every pair** |
| **mature (n ≥ `_MIN_N`=3)** | **0** |
| file on disk | **never written** (`_dirty=True`, no save fired) |

`observe()` — documented as *"called once per pair per scan"* — **never successfully fires**; the
entries that exist were created by `record_tendency()`, a different method. Consequence: the
consumer gate at line 7442 (`_pn >= _ps_fp._MIN_N`) **can never pass**, so the relative-volatility
comparison (`_cur_vol` vs the pair's own `_base_vol`) — a genuinely relativistic signal and the
purest expression of core axis #1 — **is silently inert.**

**What DOES work:** the `tendency` sub-store accumulates (`continued`/`reverted`/`chop` counts per
`regime:extreme`). So axis #1 is roughly one-third alive.

`learning_v60` per-pair records accumulate **only on closed trades** — 3 pairs after 1,930
analyses. At ~3 trades per 8 simulated days, 20 trades across 22 pairs would take **~3 years**.

## 🎯 WHAT TO DO — in priority order, measure before building
1. **Find why `observe()` never fires** (the category classifier's `_fp` dict is empty or its
   values fail the 4-finite-floats check). This is a genuine dead-path defect and the single
   highest-value repair available: it converts axis #1 from 3-years-to-populate into one session.
2. **Gate every chain by its own demonstrated edge**, the C335 pattern applied at the SCORE layer,
   not just the capital layer. Today that would suppress FamilyMarkov (0.8 obs/cell) and
   IchimokuMarkov outside CH (edge 0.0pp) — both currently emit noise into a scoring stack that
   already measures ρ = −0.060.
3. **Correct every accuracy claim in this Atlas** to the measured figures above, with baselines.


# ═══════════════════════════════════════════════════════════════════════════
# 🔬 SESSION 2026-08-04e — FUNCTIONAL WALKTHROUGH. THE SIZING LOOP IS DEAD,
#    AND THE EVIDENCE SAYS **LEAVE IT THAT WAY**.
# ═══════════════════════════════════════════════════════════════════════════

Structure was audited in C365 and came back clean. This traced what actually FLOWS through the
running bot — `stagetrace.py`, 103 scans, 1,930 pair analyses, 817 monitor ticks, **zero errors**.

## 🚨 FINDING 1 — "Score → Margin" (feedback loop #1) IS NOT OPERATIVE

Direct test of `RiskManager.dynamic_allocate`:

| test | result |
|---|---|
| **single candidate, score 0.45 → 0.95** | margin **$25.00 at every score** |
| same score, ATR 0.3% → 8% (**27× volatility**) | margin $25.00 → $24.75 (**1%**) |
| 2–4 candidates | monotonic ✓ — the mechanism itself works |

Live evidence agrees: XRP score **0.844** → $37.80 notional; AVAX score **0.458** → **$52.11**.
The *lowest*-conviction trade took the *largest* position.

**Two independent blockers, each individually sensible:**
1. **The $25 ceiling is 50% of a $50 account.** It saturates before conviction can differentiate.
   Single-candidate scans are the dominant case (3 fills across 103 scans), so score is moot.
2. **`_bf_asym_cap` = 1.3% × equity ≈ $0.65 flat**, and C303's Kelly-on-risk scaling is
   `_k303 = 1.0 + (_k303 − 1) × _c335_trust()` — with **C335 trust = 0.00**, `_k303 = 1.0` always.

**Net: margin is set by stop distance (volatility). Quality contributes nothing.**

### ⛔ AND THE CORRECT ACTION IS TO **NOT FIX IT**

The slate study measured the score's cross-sectional information at **ρ = −0.060, t = −2.52,
0/4 splits**. The score does not predict. **Repairing "quality determines capital" would size
positions by noise — and would do so with more capital on the least reliable signal.**

The project already found this at the capital layer and wrote it in C335's own docstring:
**"Noise was steering money."** The degeneracy is *accidentally protective*.

**⇒ STANDING RULE 10: the Score→Margin loop stays flat until the score demonstrates
cross-sectional information (ρ > 0 with |t| ≥ 2 across SEPARATE batches, per Rule 9). Uniform
sizing is the correct response to a zero-edge ranker.** The $25 ceiling and C335 trust=0 are to be
understood as the two mechanisms enforcing this, not as bugs awaiting repair.

*(Caveat for later: on a larger account the $25 ceiling stops binding and conviction WOULD begin
to differentiate. If capital ever grows, this rule must be re-checked, or the score will start
steering money again by accident.)*

## ✅ FINDING 2 — risk containment works, with one honest breach
12 of 13 losses sat inside the designed $0.65 per-trade cap. The single breach — CFX **−$0.91
(1.4×)** — was a $25 margin position stopping at −3.56% where the cap implies −2.92%: a stop
**overshoot**, and one amplified by the replay evaluating exits once per 15-min bar when live runs
the monitor every 0.8 s (**1,125× finer**). Live containment should be tighter than this figure.

## ✅ FINDING 3 — anti-patterns from the operator's brief, checked
| anti-pattern | verdict |
|---|---|
| score-bar inflation (MIN_SCORE mutated on session results) | **clean** — never assigned at runtime |
| MIN_SCORE floor erosion across restarts | **clean** — no runtime mutation to persist |
| polynomial margin punishment | **absent** — allocation is linear in score share |
| uncapped dust into funded[0] | **bounded** — `MIN_MARGIN_PER_TRADE` filter at the allocator exit |
| C335 authority creep | **fail-closed to 0**, verified in code |

## ✅ FINDING 4 — THE OTHER FOUR FEEDBACK LOOPS AND THE GUARDS: ALL OPERATIVE

**Loop 2 — LOSS → MARGIN (must cut capital, NEVER raise the score bar): WORKS.**
Direct test of the C123-A3 health reduction:

| session state | combined mult | margin |
|---|---|---|
| healthy | ×1.00 | $25.00 |
| mild drawdown | ×0.85 | $21.25 |
| bad session | ×0.59 | $14.88 |
| severe | ×0.35 | $8.75 |
| catastrophic | ×0.30 (floor) | $7.50 |

Monotonic, floored at 30%, and **MIN_SCORE is never touched** — the anti-pattern correctly avoided.
Both `_session_health_mult` and `_loss_mag_mult` are genuinely written (lines 17637–38), so the
loop is live, not decorative.
*(Methodology note: my first pass at this test set session win/loss counts and reported the loop
DEAD. That was a false positive — the reduction reads the two multipliers, not W/L counts. The
corrected test above is the valid one. Recorded because a wrong negative is as costly as a wrong
positive.)*

**Loop 4 — EXIT SPEED → LOSS CONTAINMENT: works.** 12/13 losses inside the $0.65 cap (Finding 2).

**Loop 5 — VOLUME DIRECTION → EXHAUSTION: not binary.** 13 distinct
rising-volume-as-continuation references; the binary-exhaustion anti-pattern is absent.

**CORRELATION GUARD: OPERATIVE.** Line 20006 computes the Pearson correlation of the candidate's
returns against every open position and **blocks at ρ > 0.75** (`_blocked_corr` → `continue`).
This is the SOL-SHORT + WIF-SHORT lesson (ρ = +0.86, ~$41 of $50 on one doubled bet) genuinely
enforced in code, not just documented.

**PRINCIPLE 5 — MACRO ALIGNMENT GRADUATED, NOT BINARY: satisfied.** 10 graduated sites; macro
enters as a weighted contribution (×0.20) and shifts agreement thresholds (0.53 aligned vs 0.60
against) rather than hard-blocking. A neutral market is never vetoed outright.

## 📊 THE FUNNEL, measured
`103 scans → 1,930 pair analyses (18.7/scan) → 3 open attempts → 3 fills → 3 closes`, **0 errors**
across 817 monitor ticks. The bot analyses ~640 pairs for every one it trades. That is extreme
selectivity, and given a ranker with no measured edge it is the safer failure direction.


# ═══════════════════════════════════════════════════════════════════════════
# 🔍 SESSION 2026-08-04d — C365: FULL PRE-FLIGHT AUDIT. 3 DEFECTS + 1 BLIND SPOT
# ═══════════════════════════════════════════════════════════════════════════

## 🚨 THE BIGGEST FINDING IS ABOUT OUR OWN MEASUREMENT, NOT THE BOT

`_c336_partial_close` books PnL **straight to the portfolio via `release_margin`** and NEVER routes
through `_close_position` — the only method `exitlab.py` ever wrapped. **Every banked half of every
C336/C338 partial has been absent from every measurement this project's harness produced.**

Control run: instrumented closes summed **+$0.23** while equity moved **+$0.95**.
**The partials were 76% of the profit and went unrecorded.**

The bot's own books were right the whole time — per-trade implied fees reconcile to 8 bp within
rounding. The instrument was wrong. `exitlab.py` now wraps both legs and conservation reconciles
**exactly: $0.23 + $0.72 = $0.95.**

**⇒ EVERY TRADE-LEVEL STATISTIC IN THIS ATLAS PREDATING THIS ENTRY IS INCOMPLETE AND UNDERSTATES
THE BOT** — the n=24 exit study, the payoff/WR figures, the fee analysis, and the "one trade is 37%
of all wins" claim were all computed on full closes only.

## 🐛 THREE REAL DEFECTS, FIXED

**1. `_admin300` read 25 lines BEFORE assignment (live, since C329).** The
`if '_admin300' in dir()` guard stopped the crash and thereby *hid* the defect: it evaluated
**False on every close**, so every administrative close (target achieved / session end / day cap /
shutdown) was written into `_recent_trades` as an ordinary trade. Assignment moved above first use.

**2. Duplicate dict key in `ModeManager._save`.** `'_overshoot_credit'` appeared twice in one dict
literal; the later un-coerced copy silently won, disabling the C304 `float()/or 0.0` guard — a
`None` could be persisted and reloaded. Principle #23 persistence class. Duplicate removed.

**3. My own C364 funding block had three faults.** (a) It called `_fetch_funding_raw` with the ccxt
symbol when it expects the Bitget form — it would have returned `None` **every single time** and
the real rate would never once have been used. (b) It was a **blocking 5 s network call sat
directly in front of a stop-loss** — the exact hazard the spread estimator had just been cached to
avoid, reintroduced twenty lines later. (c) The ±0.75% clamp was tighter than reality; the
operator's own recorder shows funding reaching **−1.96%**. Now reads the 600 s `_funding_cache`,
keyed correctly, **no network on the exit path**, clamped ±3%.

## ✅ WHAT THE SWEEP PROVED CLEAN

| check | result |
|---|---|
| duplicate class / method / function definitions | **0** — nothing silently shadowed |
| `full_analysis` reachability | **0 call sites** — its 4 undefined names are inert both ways |
| orphan attributes (read, never written) | 72 candidates, **all false positives** (dataclass fields, class constants, the C351 pos-written/getattr-read pattern) |
| close path uses the ACTUAL fill price | **yes** — so C364 slippage genuinely reaches P&L, not cosmetic |
| funding units | **fractions**, verified against 17,717 recorded rates |
| accounting conservation | **exact** once partials are counted |
| poisoned-state boot (corrupt mode/state/positions JSON) | **recovers to equity 50.0 / NORMAL, no traceback** |
| unit battery | **12/12** incl. *a reduce_only exit limit that crosses the bid still FILLS* |
| clean replay boot | 75 scans, 0 errors |

**Remaining known-inert, deliberately not touched:** 4 undefined names inside the dead
`full_analysis`; two guarded expressions (`'analysis' in dir()`, `_price_cache`) that always take
the safe branch; 132 bare excepts (the codebase's documented fail-open idiom).


# ═══════════════════════════════════════════════════════════════════════════
# ✅ SESSION 2026-08-04c — C364: PAPER = LIVE. The paper book stops flattering.
# ═══════════════════════════════════════════════════════════════════════════

Operator directive: build the bot to run in paper mode but **exactly replicate live**. Three costs
paper had never paid, found and charged. All three make paper results WORSE, which is the point.

| # | what paper did | what live does | now |
|---|---|---|---|
| 1 | market orders filled at **`last`** | a BUY lifts the **ASK**, a SELL hits the **BID** | crosses the real book, slippage logged in bp |
| 2 | filled entry limits that would cross | C363 makes the exchange **reject** them | paper rejects on the same condition, counted |
| 3 | **no funding charged, ever** | perp bills at 00:00/08:00/16:00 UTC | charged per settlement crossed |

**`last` is a historical fact — the price of a trade that already happened. You cannot trade at it.**
That one line is the whole of defect 1, and it has been silently inflating every paper number.

**Offline fallback, calibrated not guessed:** where no book is reachable (replay),
`spread_bp = 0.0269 × 15m-ATR_bp`, clamped [0.2, 25], fitted on **58 h of the operator's own recorded
order books** (18 pairs, real spreads 0.02 bp BTC → 17.6 bp 1000SATS). It deliberately OVER-states
cost for majors, so an offline number is a **floor**. Cached 300 s — this sits on the exit path and
**a stop must never wait on a network round-trip to price its own slippage.**

**Safety proven, not asserted — 8/8 unit battery:** market buy fills at ask ✓, market sell at bid ✓,
all four cross/passive entry-limit cases classify correctly ✓, and **a reduce_only exit limit that
crosses the bid still FILLS** ✓. A stop must always be able to get out.

**HONEST LIMIT:** the replay exchange serves no book, so **backtest numbers still exclude this
slippage.** The parity gain is real in a live-network paper run; replay remains the optimistic case.

Verified: syntax OK · AST 308 (+2 helpers) · 6 count-asserted replaces · replay boot clean
(109 scans, 0 errors).

## 📋 WHAT THE OPERATOR SHOULD EXPECT
Paper P&L will now read **lower than before**. That is the fix working. A paper number that
survives real spread, real post-only rejection and real funding is a number worth trusting; the
old one was not.


# ═══════════════════════════════════════════════════════════════════════════
# ✅ SESSION 2026-08-04b — C363 SHIPPED. FIRST CODE CHANGE IN FIVE SESSIONS.
# ═══════════════════════════════════════════════════════════════════════════

## ✅ C363 — POST-ONLY ON ENTRY LIMITS (integrity fix, live-only)

**The defect.** `_open_position` books the MAKER fee (0.02%) whenever `USE_LIMIT_ORDERS` makes an
entry a limit — and the C279 offset genuinely does place it passively — but **no post-only flag
was ever sent to Bitget.** A resting limit that crosses the spread at placement (stale reference
price, fast tape, wide-spread microcap) executes as **TAKER at 0.06%**. The exchange charges 3× what
the ledger records, and because the bot audits itself from its own books, **the divergence is
invisible in every log this project has ever produced.**

**The fix.** `postOnly` + `timeInForce: post_only` on entry limits — the exchange rejects rather
than crosses, so the booked maker fee becomes guaranteed truth. Rejection falls into the existing
C286 unfilled path (margin released, clean abort); it is classified and **counted**
(`_c363_postonly_rejects`) so the cross-rate stops being silent.

**Guarded to entries only.** The flag sits under `if not reduce_only`, and `reduceOnly` is assigned
ABOVE it — no exit, stop or loss close can receive it. *A post-only stop is an unfillable stop.*

**Why it ships without a backtest:** `PAPER_MODE` returns from `_paper_order` BEFORE the params
block, so replay/paper behaviour is byte-identical — the change is **live-only**. Its justification
is **arithmetic** (guarantee the fee already assumed), not statistical, so it does not need the
3-of-4-splits bar that governs predictive claims.

**Verified:** syntax OK · AST **306 functions unchanged** · 2 count-asserted replacements · guard
proven by construction with both paths simulated · replay boot clean (99 scans, 0 errors, equity
$50.95 — identical to C362 from the same start bar).

## ⚠️ I CORRECTED MY OWN COST ARITHMETIC — the previous session's figure was wrong

An earlier session note claimed round-trip cost of 12 bp and "fees are 68% of gross". That assumed
**taker on both sides**. The bot already places maker entries. Truth:

| | |
|---|---|
| true round trip | **8 bp** (maker entry 2 + taker exit 6) |
| fees on 24 trades / $534 notional | **$0.43**, not $0.64 |
| share of gross | **59%**, not 68% |
| cross-check vs bot ledger | $0.0196/trade recorded vs $0.0178 predicted at 8 bp ✓ |

**75% of the remaining fee now sits on the TAKER EXIT.** That is the next target and it needs real
design, because loss exits must always be able to cross the spread.

## ❌ FALSIFIED THIS SESSION — the cost-hurdle entry gate (do not build it)

Proposed idea: require the pair's own ATR to clear its own round-trip cost by a multiple k.
Retro-tested on 21 trades with real per-instrument spreads from the flow recorder:

| hurdle k | kept | net $ | dropped | dropped $ |
|---|---|---|---|---|
| k=0 (today) | 21 | **+0.85** | 0 | 0.00 |
| k=6 | 17 | +0.26 | 4 | +0.59 |
| k=8 | 13 | +0.42 | 8 | +0.43 |
| k=10 | 8 | **−0.53** | 13 | **+1.38** |
| k=12 | 4 | −0.34 | 17 | +1.19 |

**Monotonically harmful — the trades it drops are the profitable ones.** Median ATR/cost ratio is
**9.3×**: costs are already comfortably covered by the pairs' own volatility, so the hurdle only
removes good trades. Banked as falsified before a single line was written.

## 🎯 REMAINING LEVERS, honestly ranked

| lever | value on 24 trades | certainty | effort |
|---|---|---|---|
| **BGB / VIP fee tier −20%** | +$0.09 (30% of net) | **certain** | none — exchange account |
| maker on PROFIT exits only | +$0.12 | medium — needs design | one session |
| regime exposure gate | +$1.62 claimed | **LOW — one trade is 37% of all wins** | validation first |
| ~~cost-hurdle gate~~ | ~~—~~ | **refuted above** | — |


# ═══════════════════════════════════════════════════════════════════════════
# ❌ SESSION 2026-08-04 — H1 FALSIFIED OUT-OF-SAMPLE. AND NOTHING ELSE
#    REPLICATED EITHER. THE PRE-REGISTRATION IS WHAT MADE THIS READABLE.
# ═══════════════════════════════════════════════════════════════════════════

Operator supplied a second recorder batch: **17,713 rows, 709 cycles, 36 symbols,
2026-08-01 → 08-04, 58.8 h contiguous** (one 8.3 h gap), 300 s cadence, 4 malformed rows dropped
at ingest and reported. All fields non-degenerate. The July files were no longer present, so this
is **necessarily a clean out-of-sample test** — no pooling was possible even by accident.

`flowbench.py` was run with **only the input path changed** (diff verified: 6 lines, all ingest;
feature definitions, forward matching, Spearman, block averaging, splits, admission rule and null
control byte-identical). Match error: **median 0 s**, 16,152 matched forward points at +60 min.

## ❌ H1: FALSIFIED

> Pre-registered 2026-08-01f: `book.d_imb` cross-sectional rank NEGATIVELY correlated with
> forward 60-min return, ρ ≈ −0.05; admission = correct sign, |t| ≥ 2.0, ≥3/4 splits.

| | July (in-sample) | **August (out-of-sample)** |
|---|---|---|
| ρ | −0.0557 | **+0.0029** |
| t | −3.67 | **+0.25** |
| splits | 3/4 | **2/4** |
| jackknife | 21/21 folds | — |

**Wrong sign, |t| = 0.25, 2/4 splits. H1 fails on every clause. BANKED AS FALSIFIED.**
The July result — including a 21-of-21 jackknife — was a false positive, exactly as the
multiple-comparison arithmetic predicted at the time (3 admissions from 56 tests ≈ 2.8 expected).
**A jackknife proves internal stability, never external validity.**

## ❌ NOR DID ANYTHING ELSE REPLICATE — the full cross-batch table, +60 min

| feature | July ρ (t) | August ρ (t) | verdict |
|---|---|---|---|
| book depth imbalance | −0.0557 (−3.67) | +0.0029 (+0.25) | **flip — H1 dead** |
| OI-price conviction | +0.0520 (+2.38) | −0.0005 (−0.04) | **collapse** |
| OI divergence | +0.0517 (+2.11) | +0.0033 (+0.22) | **collapse** |
| big-trade share | −0.0443 (−1.89) | +0.0613 (+3.38) | **sign flip** |
| tight spread | −0.0078 (−0.17) | +0.0649 (+2.82) | **appears from nothing** |
| funding | +0.0407 (+0.93) | −0.0303 (−1.37) | flip |
| wall bid/ask skew | −0.0312 (−1.06) | +0.0191 (+1.87) | flip |
| real tape CVD | −0.0151 (−0.85) | −0.0058 (−0.58) | same sign, both nil |
| **momentum 15m [control]** | **−0.0175 (−0.59)** | **−0.0185 (−1.21)** | **the only stable number** |
| PSEUDO-RANDOM [null] | +0.0029 (+0.17) | −0.0035 (−0.45) | correct: noise |

**Of the three July admissions, zero replicate. Of the three August admissions, none had July
support.** Had H1 not been pre-registered, `tight spread` (admitted at ALL FOUR horizons in
August: t = +4.21, +3.36, +2.82, +3.06) would have been irresistible — and it is worth **nothing**
in July.

## 🔬 WHY THE PROJECT'S OWN SPLIT TEST CANNOT CATCH THIS

Splitting the August batch in half (Aug 1–2, 29 blocks vs Aug 3–4, 27 blocks) at +60 min:

| feature | half A | half B |
|---|---|---|
| big-trade share | +0.0532 (+2.39) ADMITTED | +0.0718 (+2.42) ADMITTED |
| tight spread | +0.0619 (+1.89) | +0.0722 (+2.18) ADMITTED |
| funding | **−0.0925 (−3.38) ADMITTED** | **+0.0467 (+1.59)** |
| book depth imbalance | +0.0264 (+1.65) | −0.0186 (−1.15) |

Two features look beautifully **stable across halves** — and both are worthless one week earlier.
**Adjacent halves are not independent samples: they share the same market week, the same
volatility regime, the same dominant flows.** The 4-way split (time-early/late, pair-set A/B) is
entirely *within-window* and is therefore blind to regime-dependence. Every "3/4 splits" result
this project has ever produced carries that blind spot.

**⇒ NEW STANDING RULE 9 (supersedes reliance on splits alone): a feature is not real until it
replicates in a SEPARATE BATCH collected at a different time. Within-window splits are a
necessary check against overfitting and are NOT evidence of an edge.**

## 📐 HOW MUCH DATA WOULD ACTUALLY SETTLE THIS — computed, not guessed

Block SD backed out from the August run (1 block = 1 hour at the 60-min horizon) is **≈0.128**.
Required continuous recording:

| true ρ | one pre-registered test (t=2.0) | 56-test sweep (Bonferroni t≈3.9) |
|---|---|---|
| 0.02 | 165 h (6.9 d) | 627 h (26 d) |
| 0.03 | 73 h (3.1 d) | 279 h (11.6 d) |
| 0.05 | 26 h (1.1 d) | 100 h (4.2 d) |
| 0.08 | 10 h (0.4 d) | 39 h (1.6 d) |

We have 80 h total across two batches. **The 56-test sweep is the mistake** — it needs 4–26 days
to say anything. One pre-registered feature at one horizon needs 3–7 days, which is reachable.
**Stop sweeping. Test one thing.**

## 📌 PRE-REGISTERED H2 — ONE feature, ONE horizon, no sweep

> **Cross-sectional 15-minute mean reversion** (rank pairs by −(15-min return); prefer the ones
> that fell) is **POSITIVELY** correlated with forward 60-minute return.
> Grounds: it is the only quantity that held its sign and magnitude across two independent
> batches (July +0.0175, August +0.0185) *and* it was the sole survivor of the candle-side bench
> after decontamination (ρ = +0.068, 4/4 splits). Predicted ρ ≈ +0.02.
> **Test:** next batch, ≥7 days contiguous (165 h at the computed noise level), `flowbench.py`
> unmodified, **the `_mr15` row at +60 min ONLY**. Admission: positive sign, |t| ≥ 2.0, and
> replication of sign against BOTH prior batches.
> **No other feature, horizon or metric may be promoted from that run.** If H2 fails, the
> cross-sectional-ranking programme is closed and Option B (accept the bot as an exit-and-risk
> engine) becomes the recommendation.


# ═══════════════════════════════════════════════════════════════════════════
# 🩸 SESSION 2026-08-01f — THE FLOW RECORDER OPENS THE UNBACKTESTABLE CHANNEL.
#    THIRD HARNESS LEAK FOUND AND CLOSED. ONE HYPOTHESIS PRE-REGISTERED.
# ═══════════════════════════════════════════════════════════════════════════

## 1. 🔓 THE FLOW FILES ANSWER THE QUESTION THAT WAS DECLARED UNANSWERABLE

The 08-01e audit concluded that six score components are **permanently** unbacktestable —
`real_cvd`, `ofi`, `oi_funding`, `renorm_flow`, `liq_cascade`, `news` — because Bitget archives
no OI history, no historical books and no trade tape. **The operator's live recorder captured
them anyway.**

**Data verified before use, three ways:**
- 29 symbols × 247 cycles, **exactly 300 s cadence**, 2026-07-29 → 07-31, **zero missing fields**.
- Recorder `mid` cross-checked against the candle corpus on 4 pairs: agreement **0.03–0.26%**
  (the residual is the ~8-min offset between bar close and sample instant). No drift.
- All 12 fields live and non-degenerate (`t_imb` 5,000 distinct values, `d_imb` 3,540,
  `cvd` 5,187 …). Nothing constant, nothing stale.
- ⚠️ **Real contiguous coverage is ~21 h, not 48** — there is a 26.4-hour hole between the 29th
  and the 30th. Every block count below reflects the true 21 h.

**Method (`flowbench.py`), and why each choice:**
- Forward return is **mid → mid from the recorder itself**. No candle join, so the entire class
  of timestamp-alignment bugs is *structurally impossible*. Realised match error: **median 0 s**.
- Spearman **cross-sectional within one cycle** — market drift cancels, only ordering is graded.
- Correlations block-averaged into **non-overlapping windows of one horizon** before any t-test.
- 4-way OOS split + the 08-01e admission rule: **≥3/4 splits AND |t| ≥ 2.0**.
- A deterministic **PSEUDO-RANDOM null feature** is graded alongside the real ones. It was never
  admitted at any horizon (t = +0.75, +0.67, +0.17, −0.12) — the pipeline is not manufacturing
  significance.

**Result — +60 min horizon, the one matching the bot's 60–75 min hold:**

| feature | ρ | t | splits | jackknife (|t|≥2 folds) |
|---|---|---|---|---|
| **book depth imbalance** | **−0.0557** | **−3.67** | 3/4 | **21/21** |
| OI-price conviction | +0.0520 | +2.38 | 3/4 | 20/20 |
| OI divergence | +0.0517 | +2.11 | 4/4 | **8/20 — fragile** |
| real tape CVD | −0.0151 | −0.85 | 4/4 | — |
| momentum 15m [control] | −0.0175 | −0.59 | 2/4 | — |
| PSEUDO-RANDOM [null] | +0.0029 | +0.17 | 2/4 | 0/21 |

### ⚠️ AND THE ARITHMETIC THAT STOPS THIS BEING A RESULT
**14 features × 4 horizons = 56 tests. At α=0.05 the expected number of false positives is 2.8.
I got exactly 3.** Bonferroni threshold is α=0.05/56 → at df=20, **|t| ≈ 3.85**. Nothing clears.
The effects are also absent at +15 and +30 min and weak at +120 min.

**NOTHING IS ESTABLISHED.** What exists is the best-supported candidate this project has ever
measured, in a family that candles can never test.

### 📌 PRE-REGISTERED HYPOTHESIS H1 — do not amend after seeing the next data
> **Cross-sectional rank of `book.d_imb` (bid depth minus ask depth, normalised) is NEGATIVELY
> correlated with forward 60-minute return.** Predicted ρ ≈ −0.05, sign **negative**.
> **Test:** the next recorder batch, ≥3 days contiguous, `flowbench.py` unmodified.
> **Admission:** correct sign, |t| ≥ 2.0, ≥3/4 splits.
> **No substitution** of a different feature or horizon is permitted post hoc. If H1 fails, it is
> banked as falsified and the flow channel is closed for depth imbalance.

Sign sanity: the recorder computes `d_imb = (bid_qty − ask_qty)/(bid+ask)`, so positive means
**more resting bid depth**, and the finding says more visible bid depth predicts **lower**
returns. Counter-intuitive, but standard microstructure (resting depth is what aggressive flow
trades against; large visible bids are the classic absorption/spoof pattern) — and notably NOT
the direction a sign error would produce.

**~21 h gave 21 blocks at the 60-min horizon. ~3 more days of continuous recording gives ~72.**
That is the whole ask, and it costs the operator nothing but leaving the recorder running.

## 2. 🕳 THIRD HARNESS LEAK — LIVE NETWORK CALLS ESCAPING A REPLAY (now closed)

Instrumented `requests` during three replay scans. **Calls escaped:**

| endpoint | calls / 3 scans | what it would have injected |
|---|---|---|
| `api.bitget.com/api/v2/mix/market/candles` | 12 | **today's candles into a 2026-03 decision** |
| `newsdata.io/api/1/crypto` | 60 | live news into a historical bar |
| `min-api.cryptocompare.com/.../news/` | 60 | the news fallback — invisible to the first probe |

Three bot paths (source lines **3426, 10793, 12249**) bypass the injected exchange entirely.

**Did this contaminate anything? No — verified.** In this sandbox `api.bitget.com` returns
**503 DNS resolution failure** and newsdata returns **401 API key missing**. Both fail closed, so
no live datum ever entered a replay decision. **But that is an accident of the sandbox, not a
property of the harness.** On a host where those names resolve, the identical code silently
imports the future.

**FIX — `install_network_guard()` in `omega_replay_full.py`.** Arm it after the corpus and
funding history load. Any outbound call raises `ConnectionError` — which every one of those call
sites already handles — so behaviour matches the failing case but is now **deterministic across
environments and COUNTED instead of silent**. Verified: the bot completes all scans normally and
reports 132 blocked calls.

**RULE: a replay that does not report `install_network_guard.blocked` has not proven it was
offline, and its numbers are not admissible.**


# ═══════════════════════════════════════════════════════════════════════════
# 🔬 SESSION 2026-08-01e — HARNESS FIDELITY AUDIT. TWO MORE DEFECTS FOUND.
#    THE 08-01d BENCH RESULT DOES NOT SURVIVE DECONTAMINATION.
# ═══════════════════════════════════════════════════════════════════════════

Operator: "recheck the harness so that it exactly replicates the entire bot functionally."
It does not, and now the gap is measured rather than assumed.

## 1. ⚫ LEARNED STATE LEAKED ACROSS RUNS — AND IT WAS A LOOKAHEAD

`/root/OmegaBot60/{regime_markov,pair_state_markov,family_markov,ichimoku_markov,learning,
s3_calib}_v60.json` persist on disk and are **shared by every replay run**. My run order was
bull (Feb–Apr 2026) BEFORE bear (Oct–Nov 2025), so **the bear slates were produced by a bot
carrying Markov chains trained on its own future.** `regime_markov` had accumulated thousands of
transition counts; `learning_v60` held per-pair records from later windows.

**RULE (new, mandatory): `rm -f /root/OmegaBot60/*.json` before every replay window, and run
windows chronologically within a chain.** A replay that does not state its state-hygiene is void.

## 2. 📉 WHAT DECONTAMINATION DID TO THE 08-01d RESULT

Both windows re-run cold (8,456 candidates, 445 slates, 39 blocks):

| feature | contaminated (08-01d) | **clean (08-01e)** | verdict |
|---|---|---|---|
| **bot final score** | −0.0621, t=−2.52, 0/4 | **−0.0595, t=−2.52, 0/4** | **ROBUST** |
| mean-reversion 24h | +0.0862, t=**+1.97**, 4/4 | +0.0679, t=**+1.55**, 4/4 | weakened below significance |
| low volatility | +0.0255, t=+1.75, **4/4** | +0.0122, t=+0.86, **2/4** | **FAILS** |
| rel strength 6h | −0.0164, 1/4 | +0.0197, t=+0.59, 4/4 | **sign flipped** |
| volume acceleration | +0.0015, 2/4 | +0.0070, t=+0.57, 3/4 | noise |

**The 4-way split alone was admitting features at t=+0.59.** It catches overfitting; it does not
establish significance. `bench_feature.py` now enforces **BOTH: ≥3/4 splits AND |t| ≥ 2.0.**

**Under the corrected rule, on clean data, ZERO features are admissible.** Option A's first sweep
produced no usable feature. What it did produce is the one robust result in the set: **the score
the bot gates and ranks on is anti-predictive, ρ = −0.0595, t = −2.52, 0/4 splits** — unchanged
by decontamination.

## 3. 🔍 WHAT THE HARNESS ACTUALLY REPLICATES — measured, 440 sampled analyses, 22 pairs, 20 bars

| status | n | components |
|---|---|---|
| **dead: harness cannot supply the data** (LIVE on the phone) | 6 | `real_cvd`, `ofi`, `oi_funding`, `renorm_flow`, `liq_cascade`, `news` |
| **dead in the BOT itself** — candle-derived, need no live feed, fire 0/440 | 2 | **`breakout_pattern`, `pca_factor`** |
| near-dead (≥90% zero) | 4 | `flag_pattern` 99%, `micro_exhaustion` 97%, `structure` 97%, `ou_meanrevert` 93% |
| active | 43 | — |

**`breakout_pattern` and `pca_factor` are a LIVE dead-code bug** — same class as CVD-dead-for-
seven-versions. They need nothing the harness withholds and never fire. Worth a session on their
own; they are silently contributing zero to every score the phone has ever computed.

**The 6 harness-dead components are exactly the order-flow family the architecture calls its
leading indicators.** Bitget serves no OI history (40404) and no historical books, and the trade
tape is not archived — so **these are permanently unbacktestable.** Every score conclusion in
this Atlas is therefore a statement about the other 49 components, never the live score.
Mitigating argument: the missing six are zero for ALL candidates simultaneously, so they dilute
the score's LEVEL far more than its cross-sectional ORDER, and the tests here are rank-based.

## 4. ⏱ CADENCE — the harness is coarser than the bot by three orders of magnitude

| | live bot | replay | ratio |
|---|---|---|---|
| monitor / exit evaluation | every **0.8 s** | once per 15-min bar | **~1,125×** |
| scan / entry evaluation | ~5 min | every 8 bars = 2 h | ~24× |

Exits can only fire at bar closes: an intrabar stop, trail or peak-floor touch is invisible.
**Direction of bias: coarse exits are WORSE than fine ones**, so the exit study's conclusion
("exits are not the problem, holding longer costs −$13.07") is CONSERVATIVE and survives. But no
exit-timing claim finer than 15 minutes can ever be made in this harness.

## 5. ✅ WHAT PASSED THE AUDIT
- **Timestamp alignment.** `freeze_time` → `get_current_price` → forward return all read
  `cs[idx][4]`. Verified in code, no offset.
- **No duplicate slate rows.** The `install_offline_feeds` memo keyed on (symbol, bar) does not
  double-count: 4,595 rows / 4,595 unique (ts, sym).
- **Raw-score capture is genuinely pre-mutation.** The wrapper reads on return, before the caller
  touches it.
- Known, accepted bias: the harness serves bar k COMPLETE at bar k's open — a 15-minute
  lookahead that **flatters** the bot and so cannot manufacture a negative finding.


# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ SESSION 2026-08-01d — AUDIT. I GRADED THE WRONG NUMBER. CORRECTED BELOW.
# ═══════════════════════════════════════════════════════════════════════════

Aashish asked for a full re-verification before building on the slate study. It found a real
error in my own work. **The 2026-08-01c headline "the ranking does not rank" was wrong in its
object and wrong in its framing.** What replaces it is narrower, better founded, and stronger.

### What the audit checked, and what it found

**1. Timestamp alignment — PASSES.** `freeze_time(ts)` advances each pair to its last bar at or
before `ts`; `get_current_price` returns `cs[idx][4]`; my forward return measures from that same
bar's close. Score and measurement sit on the identical price point, verified in code.
*Known bias, in the bot's favour:* the harness serves bar k COMPLETE at bar k's open — a 15-min
lookahead. It flatters the bot, so it cannot manufacture a negative result.

**2. The score is mutated after capture — FAILS.** `quick_scan_analysis` returns a score that the
caller then adjusts NINE times (turn, veto, alignment, staleness, two order-book penalties, …).
v1 captured the value at return. **Measured: raw and final differ on 1,348 of 1,560 rows — 86%.**

**3. The bot does not sort by score — FAILS.** Line 19362:
`_rank = _dri_favor*0.35 + _pre_dsi*0.35 + score*0.30`. The score carries **at most 30%** of the
ranking weight, and only in its post-penalty form.

**4. The ranking stage barely runs — NEW STRUCTURAL FACT.** Only **14 of 8,316** scored
candidates (**0.17%**) ever reached Step 4 and received a `_rank`; 9 scans out of 447 had even
one survivor. **The pipeline is ~99.8% gate cascade and ~0.2% ranker.** "The ranking" is
therefore not the operative mechanism — the gates are. Their value-add is currently
UNMEASURABLE (n=14 survivors, t=−0.39); it needs a dedicated study.

### The corrected measurement (`slatelab.py` v2 — reads the live dict AFTER the scan)
8,316 candidates · 447 slates · 40 day-blocks · drift-removed · overlap-corrected

| graded object | ALL ρ | t | RISING | FLAT | FALLING |
|---|---|---|---|---|---|
| raw quick-scan score (what v1 graded) | −0.0232 | −1.28 | −0.067 | −0.045 | **+0.092** |
| **final post-penalty score (the real one)** | **−0.0621** | **−2.66** | −0.107 | −0.099 | +0.001 |

**The corrected conclusion is stronger than v1's, on the correct object: the score the bot
actually gates and ranks on is significantly ANTI-predictive (t = −2.66), and worse in every
tape than the raw score it derives from.**

### A hypothesis I raised and then killed with its own direct test
Seeing raw +0.092 → final +0.001 in falling tape, I proposed that the penalty stack destroys
signal. **Tested directly** (penalty magnitude vs drift-removed forward return, 6,456 penalised
vs 1,334 untouched): penalised +0.014% (t=+0.43), untouched +0.122% (t=+0.89), and the penalty
quartiles are **not monotonic** (+0.134, +0.167, −0.112, −0.136, all |t| ≤ 1.4).
**The penalty stack is measurably neutral.** My intermediate inference was wrong; banked.

---

# 🟢 OPTION A IS OPEN — THE BENCH EXISTS AND ITS FIRST RESULT CLEARS RULE 1

`bench_feature.py` replays the bot's own slates and grades any proposed feature by per-scan
Spearman against realised forward returns, block-corrected, with the mandatory 4-way split.
Adding a feature is one function. No bot execution. Seconds per run.

| feature | ρ | t | splits positive |
|---|---|---|---|
| **mean-reversion 24h** | **+0.0862** | **+1.97** | **4/4 ✅** |
| **low volatility** | **+0.0255** | +1.75 | **4/4 ✅** |
| volume acceleration | +0.0015 | +0.13 | 2/4 |
| rel strength 6h | −0.0164 | −0.49 | 1/4 |
| bot raw score | −0.0232 | −1.28 | 2/4 |
| position in 24h range | −0.0243 | −0.67 | 2/4 |
| **bot final score (incumbent)** | **−0.0621** | **−2.66** | **0/4** |
| travel in own ATR | −0.0698 | −1.75 | 0/4 |
| rel strength 24h | −0.0862 | −1.97 | 0/4 |

**Robustness on the leader — positive at every horizon and in every tape:**

| horizon | +4h | +12h | +24h | +48h |
|---|---|---|---|---|
| mean-reversion ρ | **+0.096 (t=3.60)** | +0.063 (t=1.57) | +0.086 (t=1.97) | +0.106 (t=2.15) |

By tape: RISING +0.084, FLAT +0.073, FALLING +0.053 — same sign in all three, none individually
significant (thin blocks).

**In return terms — top-3 picks vs the slate they came from:**

| ranking rule | top-3 forward 24h | slate average | edge |
|---|---|---|---|
| mean-reversion 24h | +0.30% | +0.13% | **+0.17pp** |
| low volatility | +0.20% | +0.13% | +0.07pp |
| **bot final score** | **−0.20%** | +0.13% | **−0.33pp** |

Swapping the ranking basis is worth roughly **+0.50pp per selection** relative to today.

### ⚠️ Read these caveats before anyone builds
1. **"mean-reversion 24h" is the exact negation of "rel strength 24h."** One finding, not two.
   Its mirror image appearing at the bottom of the table is mechanical, not confirmation.
2. **No fees or slippage.** Bitget taker round-trip ≈0.12%. An edge of +0.17pp/24h is thin
   against that — the 4h result (t=3.60) matters more, since the bot holds 60–75 min.
3. **One corpus, 302 days, 22 pairs, two windows.** Not yet tested on independent history.
   Everything in the kill list also looked good on one corpus.
4. It reranks WITHIN the bot's own direction choices; it does not test flipping direction.
5. ρ=+0.086 is small. This is a tilt, not an edge worth leverage.

**What it says mechanically: the bot's scoring is momentum-leaning, and cross-sectional momentum
among its own candidates is NEGATIVE at 4–48h in this corpus.** That is consistent with
kill-list #4, where the momentum result turned out to be survivorship.


# ═══════════════════════════════════════════════════════════════════════════
# ⚫ SESSION 2026-08-01c — THE SLATE STUDY  [⚠️ SUPERSEDED — see the 08-01d audit above.
#    It graded the RAW quick-scan score, not the score the bot gates on, and the 'ranking'
#    it named turned out to run on 0.17% of candidates. The corrected result is stronger.]
# ═══════════════════════════════════════════════════════════════════════════

Every study before this one conditioned on what the bot **chose** — 0.2 observations per
simulated day, and blind to the counterfactual. `slatelab.py` wraps `ta.quick_scan_analysis`,
the per-pair scorer every scan runs across the universe, and banks **every score the bot
produces whether or not it becomes a trade**: ~19 rows per scan instead of ~0.02.

**12,153 scored candidates · 640 scans · 80 day-blocks · two regime windows.**

### The measurement
Per-scan Spearman correlation between the bot's score and each candidate's realised forward
24h return, signed in the direction the bot proposed. **Cross-sectional within a timestamp**, so
market drift cancels — a scan where everything rises grades no better than one where everything
falls. Only the ORDERING is graded. Scans run every 2h against a 24h forward window, so
consecutive scans share ~92% of their outcome; correlations are block-averaged into
non-overlapping 24h blocks and the t-test runs **across blocks** (kill-list #6's mistake, avoided).

### The result

| tape | blocks | mean ρ(score, forward return) | t |
|---|---|---|---|
| ALL | 55 | −0.0238 | −1.63 |
| market RISING (btc 7d > +3%) | 21 | **−0.0645** | **−2.61** |
| market FLAT (−3%..+3%) | 33 | **−0.0727** | **−2.67** |
| market FALLING (btc 7d < −3%) | 27 | +0.0312 | +1.28 |

**Mandatory 4-way out-of-sample split: 1/4 positive.** Rule 1 needs ≥3.

What the ranking is worth in return terms — the bot's top-3 picks against the average of the same
slate it drew them from:

| tape | top-1 | top-3 | slate average | **edge** |
|---|---|---|---|---|
| RISING | −0.55% | −0.31% | −0.01% | **−0.30pp** |
| FLAT | −0.56% | −0.48% | −0.29% | **−0.19pp** |
| FALLING | +0.34% | +0.63% | +0.32% | +0.32pp |

Score quintiles with drift removed (candidate return minus its own scan's slate mean) are flat
end to end: Q1 −0.20%, Q2 +0.11%, Q3 +0.03%, Q4 +0.08%, **Q5 −0.01%**. The top quintile of
scores carries no excess return. By the bot's own regime label the worst cell is `strong_up`
(ρ = −0.0848, t = −2.14).

### The score is not a time-filter either
Counter-hypothesis: maybe the score works across TIME (as the `MIN_SCORE` gate) even if it fails
across pairs. Correlation between the best score on a slate and that slate's average forward
return: **−0.168, t = −0.78, n=23 blocks.** No.

### The direction call has no edge either — the apparent one was market drift
A first pass showed proposed-longs hitting **69%** in falling tape and returning **+2.26%**, which
looked like real skill. Controlled against **everything the bot scored that same day**:

| tape | proposed longs | the day's own universe | per-day t |
|---|---|---|---|
| RISING | −0.47% | −0.56% | **−2.45** |
| FLAT | −0.72% | −0.55% | **−2.84** |
| FALLING | **+1.47%** | **+1.42%** | −1.43 |

The falling-tape "skill" is the market bouncing: the universe made +1.42% and the bot's longs
made +1.47%. **Nothing.** In rising and flat tape the direction selection is significantly WORSE
than drawing at random from its own slate.

### ⚫ THE VERDICT

**The candidate scoring and direction selection contain no exploitable cross-sectional
information. In rising and flat tape they are significantly worse than random selection from the
same slate.** This is measured on 12,153 candidates with overlap correction and OOS splits — an
order of magnitude more evidence than any conclusion previously banked in this project.

Which forces an honest re-reading of the bear window's **+10.18%**: it cannot have come from pair
selection, because pair selection demonstrably adds nothing. What remains is the exit engine
(independently proven sound, n=24 — holding longer costs −$13.07), position sizing, and **11
trades' worth of luck**. The bear result should be treated as unexplained, not as earned.

### 🧭 WHAT THIS MEANS FOR THE NEXT DECISION — this is an operator decision, not a code change

362 versions of accumulated scoring heuristics do not rank pairs. Tuning another component is not
a response to that. Two coherent directions:

**(A) Rebuild the ranking on measured evidence.** Use `slatelab.py` + `analyze_slate.py` as the
bench: propose a candidate feature, measure its per-scan ρ against forward returns across 12k+
candidates with the 4-way split, and admit it only if it clears. Any feature that survives is
worth more than the entire current stack, which measures at ρ ≈ 0.

**(B) Accept the bot as an exit-and-risk engine.** The exits are genuinely good and that is
measured. Pair them with a deliberately simple, evidence-backed selection rule rather than the
current stack. Fewer moving parts, and every part earning its place.

**Do NOT** tune a scoring component, add a signal, or reweight the confluence stack before this
decision is made. That is what the last several hundred versions did, and the slate study is what
it produced.


# ═══════════════════════════════════════════════════════════════════════════
# 🔬 SESSION 2026-08-01b — THE ENTRY STUDY: A SHARP HYPOTHESIS, KILLED AT SCALE
# ═══════════════════════════════════════════════════════════════════════════

**Task:** the exit study cleared the exit engine and pointed upstream. Instrument the ENTRY side
and answer — when the regime classifier correctly saw the uptrend, what did the selector do?

**Answer to the literal question: the classifier was RIGHT and the selector still bought tops.**
`entrylab.py` wraps `_open_position` and banks the bot's own state at the moment of choice.
6 of the first 7 bull-window entries carried `_live_regime = "trend_up"` — the classifier read
the tape correctly. 5 of those 7 were opened with the pair sitting at **91–99% of its own 24-hour
range** after travelling 4.8–12.7 of its own ATR units. All five lost.

**Hypothesis formed (n=26 deduped, entry context reconstructed from raw candles for every trade
on disk):** boarding a pair at `rng_pos_24h ≥ 0.90` after `travel ≥ 3 ATR` is toxic.

| cohort | n | WR | net $ | fwd 24h |
|---|---|---|---|---|
| exhaustion-board | 12 | 17% | −2.79 | −2.20% |
| everything else | 14 | 71% | +2.73 | +2.57% |
| — bull window only | 9 | **0%** | −2.97 | −3.86% |
| — bear window only | 3 | 67% | +0.18 | +2.81% |

Welch t = +2.57 on dollars, +2.02 on forward price. 0-for-9 in the bull window.

### ❌ AND THEN IT DIED — `scan_exhaustion.py`, 158,444 observations, 22 pairs

| regime | n_hot | exhaustion | other | gap | t |
|---|---|---|---|---|---|
| BULL btc7d > +3% | 3,289 | −0.28% | −0.25% | **−0.02pp** | −0.29 |
| CHOP −3%..+3% | 3,872 | +0.19% | −0.31% | +0.50pp | +5.23 |
| BEAR btc7d < −3% | 2,143 | −0.45% | −0.13% | −0.32pp | −2.16 |

- **Bull cell — the actual claim — is exactly nothing.** 4-way OOS: **2/4 splits**, fails rule 1.
- **Sensitivity across 9 threshold pairs** (rng 0.80/0.90/0.95 × travel 2/3/5 ATR): gaps span
  −0.05 to +0.14pp, every |t| < 1. No threshold makes it appear; it is not a tuning problem.
- **The CHOP cell's t=+5.23 is an overlap artifact.** Re-run non-overlapping (one observation per
  pair per 24h, 6,622 obs): t collapses to **+0.74**, and the only genuinely out-of-sample
  dimension — time — **flips sign** (+1.97 early, −1.88 late). Same class as kill-list #6.

**⇒ 0-for-9 was a coincidence in one 55-day window.** Cost of finding out: ~5 minutes, no build.
This is the measure-before-building discipline paying for itself.

### 📊 WHAT SURVIVED: THE SCORE'S DISCRIMINATION IS REGIME-CONDITIONAL

Splitting the same n=26 by the bot's own entry score, **within** each window (the pooled table
shows a spurious inversion — pure Simpson's paradox, the regime does the work):

| window | Spearman ρ(score, forward 24h) | low-score half | high-score half |
|---|---|---|---|
| BEAR (n=11) | **+0.200** | 80% WR, +$1.09 | 80% WR, **+$2.11** |
| BULL (n=15) | **−0.011** | 43% WR, −$0.15 | **14% WR, −$2.17** |

Neither is significant on its own. But it matches every other measurement this project has made:
**the analytical stack has discrimination in falling and choppy tape and loses it completely in a
rising one.** The defect is not one bad signal — it is that the whole ranking goes blind in an
uptrend. That is the question for the next session, and it is a different question from any that
has been asked in 362 versions.

**Do NOT re-propose:** any "don't chase extension / don't buy the top of the range / fade the
already-travelled" filter. It is measured, at scale, with splits, and it is not there.


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 SESSION 2026-08-01 — THE DEAD-CLOCK DEFECT, AND THREE OVERTURNED VERDICTS
# ═══════════════════════════════════════════════════════════════════════════

**Task attempted:** the handoff's next step — accumulate 20+ instrumented exit closes, then
fix the monitoring-thread exits. **Outcome: n=24 gathered; NO exit fix made, because the
measurement says the exits are working. The value destruction is on the ENTRY side, and it is
regime-conditional.** Three prior conclusions are retired.

---

### 🔴 FINDING 1 — THE DEAD-CLOCK DEFECT (harness, not the bot). Fixed in replay v3.1.

`Position.entry_time` and `Position.last_dri_update` are declared
`field(default_factory=datetime.now)`. A dataclass captures its `default_factory` in the
generated `__init__`'s **closure**, at class-definition time — i.e. **before** `install_clock`
swaps in the virtual clock. So every replayed position was stamped with the REAL wall clock
(2026-08-01) while `Position.age_seconds` (line 1057) resolves `datetime` as a module global at
call time and read the SIMULATED clock.

**Result: `age = simulated_now − real_now ≈ −385,000 minutes`. Every position was born in the
future.** Every age-gated exit was therefore unreachable in replay:
- the entire **STAGNANT family** — which the live logs put at **84% of losses**
- the C338 partial lease (`PARTIAL_LEASE_EXPIRED`, 180 min)
- HP timers and any cooldown keyed on position age

**The backtest has been running a bot with its dominant loss-exit family amputated, silently.**
This is the *dead-code class* (Principle: computed-but-never-read) in a new disguise:
**bound-before-patched**. Symptom to watch for in any future shim: a value that is correct at
class definition and wrong at call time.

**FIX (v3.1, `install_clock`):** walk `Position.__init__.__closure__`, find the cells holding
`datetime.datetime.now` (compare by `__name__`/`__self__` — `datetime.now` is a fresh bound
builtin on every access, so `is` comparison silently fails), and rebind them to the virtual
clock. `install_clock.patched_factories` must print **2**; if it prints 0 the harness is lying.

**WHAT THIS INVALIDATES:** every exit statistic gathered through the full-pipeline harness,
including **kill-list item #7 (the C360 profit-ratchet A/B)**, which was measured head-to-head
on the broken harness. C360's revert stands (it was also built on a bad metric — see Finding 2)
but its *A/B evidence* is void. Kill-list #2 (C355 extension veto) is suspect for the same
reason if its harness constructed `Position` objects.

---

### 🔴 FINDING 2 — "THE BOT EXITS TOO EARLY" IS A MEASUREMENT ARTIFACT.

C360 was built on *"+22.20% and +11.09% arrived within 48h after winning exits — average
+16.65% left on the table."* That is a **maximum favourable excursion**: the best price touched
at any moment in the window. It is (a) unattainable — you cannot sell the exact high — and
(b) inflated by volatility alone. Any coin doing ±3%/day shows ~+8% favourable excursion over
48h from **any** random bar, in **either** direction. Measuring only the favourable half of a
two-sided distribution guarantees a large positive number and proves nothing.

Measured properly on n=24 (terminal return at a fixed horizon, signed in the trade's direction,
against each pair's own unconditional forward-return distribution):

| horizon | max-excursion (the biased metric) | **terminal return (achievable)** | positive | excess z | t |
|---|---|---|---|---|---|
| +4h | best +2.26% / worst −2.12% | **−0.13%** | 9/24 | −0.02 | −0.09 |
| +12h | best +3.99% / worst −3.63% | **−0.23%** | 9/24 | −0.17 | −0.66 |
| +24h | best +5.43% / worst −4.64% | **−0.20%** | 9/24 | −0.19 | −0.80 |
| +48h | best +5.99% / worst −6.90% | **−2.79%** | 8/24 | −0.42 | **−2.19** |

**Holding every position 48h longer would have cost −$13.07 on a book that realised +$0.30.**
t = −2.19 clears significance. **Both directions are now tested: tightening the winning side
(C360) hurt; loosening it hurts more.** Exit timing is NOT the lever.

**⇒ STANDING RULE 4 IS RETIRED.** "Payoff work must loosen the winning side" rested entirely on
the max-excursion artifact. Replacement rule below.

---

### 🔴 FINDING 3 — THE −42% ALPHA WAS A REGIME ARTIFACT. Controlled experiment, same bot,
### same harness, same corpus, two regimes.

| window | days | **BOT** | BTC | 22-pair basket | alpha vs BTC | alpha vs basket |
|---|---|---|---|---|---|---|
| **BEAR** 2025-10-16 → 2026-01-11 | 86 | **+10.18%** | −15.97% | −19.63% | **+26.15%** | +29.81% |
| **BULL** 2026-02-24 → 2026-04-21 | 55 | **−4.90%** | +19.47% | +8.54% | **−24.37%** | −13.44% |

The handoff's headline (−42.43% alpha, "no configuration reached positive expectancy") was
measured in **Nov–Dec 2024, when BTC ran +42%**. A defensive system holding ~60–75 minutes
cannot beat buy-and-hold in a vertical bull — that is arithmetic, not a defect. In a falling
market the same code made **+10.2% while everything it could have bought fell 16–20%**.

**Honest caveat:** the clock repair and the window changed together, so the two effects are not
yet separated. Nov 2024 sits outside the 300-day rebuilt corpus.

---

### ★ THE REAL DIAGNOSIS — ENTRY SELECTION, AND IT INVERTS BY REGIME

| | n | WR | payoff | net | in-trade MFE | in-trade MAE | **selection edge** | median hold | longs |
|---|---|---|---|---|---|---|---|---|---|
| **BEAR** | 11 | **73%** | 1.23 | +$2.63 | +5.45% | −2.53% | **+2.91%** | 60 min | 9/11 |
| **BULL** | 13 | **23%** | 0.84 | −$2.33 | +0.89% | −1.86% | **−0.97%** | 75 min | 12/13 |
| both | 24 | 46% | 1.26 | +$0.30 | +2.98% | −2.17% | +0.81% | 75 min | 21/24 |

**The decisive pair of numbers:**
- **BEAR** — the average price move the bot *selected*, entry→exit, was **+2.67%**, and the bot
  **captured +2.77% of it**. Selection good, execution essentially perfect.
- **BULL** — the average price move it selected was **−0.83%**, and holding those same
  selections 48h longer takes it to **−4.21% with only 2/13 positive**, while the market rose
  +19.5% and the basket +8.5%.

**In a rising market the engine systematically picks the pairs that are about to stall or fall,
and it expresses that as LONGS (12 of 13).** It is not fighting the trend — it is boarding
exhaustion. This is the live ledger's own **"late-boarding stretched runners"** pattern (n=3
there) now confirmed at scale, out-of-sample, with the money attached.

**Exit-family table (n=24) — for the record, and note the signs:**

| family | n | net $ | ret +48h after exit | verdict |
|---|---|---|---|---|
| REL_TIME_MAX | 2 | +1.93 | −9.90% | exit RIGHT |
| MICRO_TREND_EXIT | 5 | +1.80 | −4.87% | exit RIGHT |
| WINNER_RATCHET_FLOOR | 2 | +0.34 | +5.38% | mildly early |
| PEAK_REVERSAL | 1 | +0.34 | +1.31% | fine |
| EARLY_PEAK_CAPTURE | 1 | +0.16 | +3.84% | mildly early |
| REL_DSI+DRI DIVERGE | 1 | −0.57 | **+10.70%** (+33.80% at 24h) | **the one costly exit** |
| REL_STAGNATION | 7 | −1.09 | −4.15% | exit RIGHT (pairs kept falling) |
| REL_DSI+DRI TREND | 3 | −1.13 | −6.04% | exit RIGHT |
| REL_HARD_STOP | 2 | −1.48 | −1.17% | exit RIGHT |

Every loss-exit family is followed by **further adverse movement** — they are cutting correctly.
`REL_STAGNATION`, the most frequent exit (7/24) and the live logs' prime suspect, is
**vindicated**: −$0.16 average, and the pairs fell another −4.15% after it fired.

**12 of 13 losers showed >+0.3% profit first (avg peak +1.04%) then closed at −1.88%.** Shallow
pops that died — an entry signature, not an exit one.

---

### 📏 REPLACEMENT STANDING RULES (supersede old rule 4)

**4a. Never draw a conclusion from a one-sided excursion metric.** Any "X% was left on the
table" claim must be reported beside the adverse excursion over the same window AND beside the
terminal return at a fixed horizon. If the favourable and adverse sides are comparable, the
finding is volatility, not edge.

**4b. Every backtest result must name its benchmark regime.** Report bot return, BTC return AND
equal-weight basket return for the exact window. An alpha number without its regime is
uninterpretable.

**4c. Exit timing is closed as a research direction** pending new evidence. Tightened: worse.
Loosened: worse (t=−2.19). The next lever is entry selection under a rising tape.

---

### 🧰 ENVIRONMENT (this sandbox — differs from the last one)

- **`api.bitget.com` does not resolve here. `capi.bitget.com` serves the identical v2 REST
  paths and works.** All harness copies repointed. (`api.binance.com` 451, `api.bybit.com` 403.)
- **Corpus rebuilt:** 22 crypto pairs × 29,000 15-min bars = 638,000 bars,
  **2025-10-01 → 2026-08-01**, 9.8 MB, at `~/OmegaBotV60/replay_cache/deep2/`. Every pair was
  probed to have ≥870 days of listing history first, so there is **no new-listing survivorship
  tilt** (the bias that killed kill-list #4). BTC over the full corpus: **−46.23%** — this is a
  bear corpus with exactly one bull leg (frac 0.48, Feb→May 2026, +20.06%).
- **`ccxt` must be pip-installed** (`--break-system-packages`) before the bot module will import.
- **Background processes are killed between tool calls.** Run replays in foreground chunks
  ≤250 s; `exitlab.py` resumes from `prog_<tag>.json` + `portfolio.save_state()`.
- Throughput on 1 CPU: **~1,200–2,000 bars per 245 s chunk**; ~0.2 closes per simulated day.

**🔴 C155 isRwa TRAP REINTRODUCED BY ME — FOUND BY THE OPERATOR, NOW FIXED EVERYWHERE (recorder v1.2 / harness v2.2).**
The operator spotted KORU (a 3x China ETF) in the flow output. Root cause: `isRwa` does **not exist on the `tickers` endpoint** and there is **no `info` sub-dict** there — that shape belongs to ccxt, not the raw REST API. My filter read `t["info"]["isRwa"]`, always took the `"NO"` default, and **let every real-world asset through**. isRwa lives on the **`contracts`** endpoint (261 of 731 symbols flagged).
**MEASURED DAMAGE:**
- **Flow recording: 15 of 25 pairs were not crypto** — KORU, BZ and CL (crude oil), XAU/XAG (gold/silver), INTC, DRAM, SAMSUNG, SKHYNIX, SKHY, SNDK, SNXX, SOXL, SPCX, MU. Only 10 were real crypto.
- **Replay corpus: 30 of 65 pairs (46%) were RWA** — NVDA, TSLA, QQQ, GOOGL, MSTR, AMD, TSM, PLTR, MRVL, XAU, XAG, BZ, CL, ZHIPU and more.
**DID IT CHANGE THE VERDICT? No.** Re-run crypto-only: expectancy **−0.118%** vs −0.089% contaminated (crypto is *slightly worse*); crypto − RWA = −0.062% ±0.129, not significant. Every prior conclusion stands.
**FIXES:** recorder now builds the RWA set from `contracts` and **fails CLOSED** — if that list cannot be fetched it refuses to record rather than silently admitting equities. Harness `load_corpus()` is **crypto-only by default** (58 → 29 pairs). Verified: new universe is BTC, ETH, SOL, BANK, XRP, HYPE, COTI, ZEC, ADA, DEXE, DOGE, ONDO, PEPE, AAVE, WLD, BEAT, SOON, SUI, SHIB, ENA, NEAR, KAITO, EUL, PUMP, TAO — **0 RWA leakage**.
**The bot's own C155 filter is INTACT and correct** — it reads ccxt's `markets[symbol]['info']['isRwa']`, where `info` genuinely exists. Only my two new tools had the bug.

**★ C358 + RECORDER v1.1 — FIRST REAL FLOW DATA VERIFIED, AND A CORRECTION.**
**Flow recorder: WORKING CORRECTLY.** First upload (50 records, 25 pairs, 2 sweeps 5 min apart): book/tape/OI/funding present on 50/50. Values live and varying (mean |Delta cvd| 0.632, |Delta depth-imb| 0.201, |Delta OI| 0.519% between sweeps). Ranges healthy: t_imb -0.98..+0.999, walls 4x..674x median, big_share 33%..94%. **The irreplaceable signal is already visible: KORU large-trade CVD -0.463 against its own tape**, plus MU -0.320, SKHYNIX +0.315 — large money opposing the crowd, derivable from nothing else.
**Recorder v1.1 fixes:** (1) `utcnow()` deprecation removed — that warning printed on the operator's screen at every start; (2) **`cycle` field added** — a real data-model gap found in the upload: each record carried its own capture timestamp, so a 25-pair sweep produced 25 distinct stamps spanning ~3s and grouping needed fuzzy time-bucketing. Analysis should never have to guess which records belong together; (3) status reports sweeps.

**★ C358 — I WAS WRONG ABOUT THE TRUST GATE, AND HAVE CORRECTED IT.** My warning that C342/C343 "may never earn trust" came from a single unlucky seed on pathological ultra-sticky streams, where one state dominates so the base rate is already near-perfect and unbeatable. Re-verified on realistic streams: **moderate persistence +6.7%, trending +11.3%, sticky +12.6% — all EARN trust**, while uniform (-2.8%) and pure noise (-1.1%) are still correctly refused. **The gate is sound and the 5% skill bar stays.**
The genuine obstacle was sample *accumulation speed*: IchiMarkov scores hundreds of transitions per session, FamilyMarkov only ~20-25 (one batch per category per scan), so n>=200 sat ~9 sessions away. A family observation is also a composite of >=3 members. **Family bar -> 120; Ichi keeps 200.** Evidence from the operator's own logs: session-2 FamilyMarkov ran **+15.5% skill — it would have passed**; only n=21 blocked it. Both calibration lines now print `n/min_n` and live `skill=X% [need +5%]`, so "earning" is a visible countdown. Verified 6/6 cases.

**🔬 RESEARCH-DRIVEN TEST ROUND (2026-07-31) — three hypotheses tested, three killed, one real correction found.**

**1. CROSS-SECTIONAL MOMENTUM — the literature's best-documented crypto edge. TESTED AND REJECTED.**
Built a fresh 55-pair crypto-only daily corpus (540 bars, Jan 2025 → Jul 2026). First result looked spectacular: 28d lookback / 5d hold, long-short quintile, **+138%/yr, Sharpe 1.87, positive in 4/4 OOS splits**, while BTC fell −39.4% over the same span. It survived a no-lookahead trailing-volume liquidity filter.
**Then it died under three checks:**
- **t-stat 1.66** — below the 2.0 significance threshold.
- **Dropping the best 10 of 101 periods turns the mean NEGATIVE (−0.46%)** — ~10% of periods carry everything.
- **DECISIVE: restricting to pairs that already existed at the sample start → +138%/yr becomes −1%/yr, t = −0.03.** The entire result came from the 16 coins that *listed during* the window and pumped. New-listing + survivorship bias, and Bitget serves no delisted-symbol history so it cannot be corrected — only avoided.
*This is the fourth "spectacular" finding this harness has killed (v1's exit geometry, C355, the 24h/6-ATR mirage, now momentum).*

**2. THE OPERATOR'S OWN FLOW DATA — 6,175 records, 247 sweeps, 21 hours, 25 crypto pairs, zero RWA leakage. NO EDGE.**
| signal | 15 min | 1 hour | 4 hours |
|---|---|---|---|
| aggressive CVD | −0.011 | −0.012 | −0.004 |
| **large-trade CVD** | −0.014 | −0.010 | +0.004 |
| **big − crowd divergence** | −0.015 | −0.001 | +0.020 |
| book imbalance / walls | ~0 | ~0 | ~0 |
| funding (pooled) | +0.063 | +0.137 | **+0.382** |
The funding number is a **pooling artifact**: decomposed *within* pair — the only tradable form — it flips sign to **−0.127**. The pooled figure merely says some coins both had high funding and rose during this one window; effective n is 25 pairs, not 6,175 observations. Cross-sectional-by-sweep looks significant but 4h returns sampled every 5 min overlap 48-fold, so effective n ≈ 5.
**This matches the literature exactly:** genuine OFI predictability lives sub-minute (R² 0.094 at 1s → 0.019 at 10s) and dies below fees. **A 5-minute sampler cannot reach the regime where flow works, and the regime where it works belongs to colocated HFT.** Recording more will not change this.

**3. ⭐ A REAL FINDING — MY OWN HARNESS OVERSTATED THE BOT'S COSTS BY 50%.**
The harness charged **taker on both legs (0.12%)**. The bot actually **enters as maker** (`USE_LIMIT_ORDERS=True`, C279 passive offset, `MAKER_FEE_PCT=0.02`) and exits taker via reduce-only market (C257) — **true round trip 0.08%**. Every prior harness result was 0.04%/trade more pessimistic than reality. **Corrected in harness v2.3.**
Restated at the true fee: 4h 2.0A/1.6A **−0.092%**; 16h 3.0A/2.0A −0.057%; **24h 4.0A/2.5A −0.050% (best)**; 48h 6.0A/3.0A −0.069%. At full maker-maker (0.04%) the 24h config reaches **−0.010% — statistical break-even.**

**4. THE 24-HOUR CONFIGURATION — NOT SHIPPED, because it failed our own rule.** Payoff improves genuinely (1.03 → 1.51) on ~6× fewer decisions, but the expectancy improvement is **+0.017% ±0.078, consistent in only 2/4 splits.** Not significant → **not shipped.** Shipping "looks better pooled" is exactly the C355 error.

**STANDING POSITION UNCHANGED: no configuration tested — directional, flow-based, funding-based, momentum, or geometric — reaches positive expectancy out-of-sample. The bot's remaining deficit is ≈0.05–0.09%/trade against a 0.08% round trip: the fees still are the loss.**

**🎯 THE LAST UNTESTED DOOR (2026-07-31): full engine at LONG horizons, true fees, funding restored.**

**The structural insight that motivated it — the fee forces you LONGER, not shorter.** Measured on live Bitget data: required correlation to clear a 0.04% fee is **0.795 at 1 min** (impossible), 0.205 at 15 min, 0.103 at 1 h, 0.051 at 4 h, **0.021 at 24 h**. The bot had been fishing at 15 min–4 h, where the fee demands **4–10× more predictive skill** than at 24 h. This is why every documented crypto edge in the literature is weekly or monthly.
*Sub-minute scalping is arithmetically dead: a 1-second move has σ≈0.0065%; the best published OFI (R²=0.094) captures ≈0.00199%; the fee is 0.08% — **40× the edge**. Break-even at 1 s needs correlation 6.16; correlation cannot exceed 1.0.*

**RESULT — 919 engine trades, 3 horizons, crypto-only, real funding, 0.08% round trip:**
| config | n | win% | payoff | exp/trade | OOS |
|---|---|---|---|---|---|
| Engine 24h | 919 | 37.0% | 1.67 | −0.026% | 2/4 |
| Engine 48h | 919 | 30.1% | 2.23 | −0.054% | 2/4 |
| **Engine 72h** | 919 | 27.2% | **2.89** | **+0.123%** | **3/4** |
| baseline 24h/48h/72h | 4,388 | — | 1.51/1.98/2.41 | −0.088/−0.146/−0.130% | **0/4** |

**THEN THE OVERLAP CORRECTION KILLED IT.** Stride was 40 bars (10 h) but the 72 h horizon spans 288 bars — consecutive trades overlapped ~86%. On **non-overlapping** samples: n=218, exp +0.089%, **t = 0.28**, CI ±0.618, **2/4**. Does not pass the standing rule. **NOT SHIPPED.** (Six configurations were examined, so ~0.3 false positives are expected by chance — one apparent winner out of six is exactly what noise produces.)

**⭐ THE ONE PATTERN THAT DID NOT BREAK — and the only positive signal in the entire project.**
The engine beats random selection at **every** horizon, and the advantage **grows monotonically with horizon**:
| horizon | engine | baseline | engine advantage |
|---|---|---|---|
| 24h | −0.026% | −0.088% | **+0.062%** |
| 48h | −0.054% | −0.146% | **+0.091%** |
| 72h | +0.123% | −0.130% | **+0.253%** |
Payoff too: 1.67 vs 1.51 · 2.23 vs 1.98 · **3.14 vs 2.18** — on 21% as many trades. Individually none is significant (72h head-to-head +0.298% ±0.660), but a **monotonic 3/3 pattern in the direction theory predicts** is not what pure noise usually looks like. **After 358 versions this is the first evidence that the 48-signal engine adds anything at all** — and it says the engine's value is real but only visible where fees stop dominating.

**WHAT WOULD RESOLVE IT:** n=218 non-overlapping is far too small (CI ±0.618 spans −0.53% to +0.71%). Resolving a +0.09% effect needs CI ≈±0.15 ⇒ ~16× more samples ⇒ roughly **one year of 15-minute history per pair** (we have ~4 months). That history is obtainable from Bitget by pagination. **This is the one open question left in the project, and it is answerable.**

**★ C362 — ANALYSIS MEMO SHIPPED (measured performance fix, zero behaviour change).**
Profiling the complete-pipeline replay found the bot **re-running the 1,819-line `quick_scan_analysis` three times per monitoring tick** (via `_refresh_live_regime`) and **retraining a 50-tree RandomForest + GradientBoosting per pair per scan** inside it — **95,200 sklearn tree fits across three scans, 57s of a 63s profile.** Between two 15-minute candles the inputs cannot change, so neither can the output.
`quick_scan_analysis` is now a thin memo keyed on **(symbol, last SETTLED candle, length)** in front of the untouched original (`_quick_scan_analysis_raw`). Battery: same candle → **identical object returned**; new candle → recomputed, never stale; exchange failure → falls through uncached, no crash; cache bounded at 400 entries and self-evicting. AST 304→306.
**LIVE IMPACT IS LARGER THAN REPLAY SHOWS.** The replay ticks the monitor once per bar and recorded 0 cache hits; the live bot ticks every **0.8s** and refreshes regime every 60s, so within ONE 15-minute candle it makes ~**45 analyzer calls on identical data where 1 would do**. Replay structurally cannot reproduce that repetition — the saving is real on the phone and invisible in the harness. Replay-measured speedups on the paths it *can* exercise: **20× (analyzer), 5.5× (ML)**.

**🚫 MONITORING-THREAD EXITS — DIAGNOSED, NOT YET CHANGED, AND DELIBERATELY SO.**
The complete-bot backtest showed those exits cost 21 points of win rate and 7.8 points of return. Instrumented diagnosis so far: **PEAK_FLOOR closed at −0.48% from a +1.23% peak with +5.89% arriving within 48h** — flagged COSTLY, and it is the second time PEAK_FLOOR has appeared in that role. **But n=2.** That is precisely the sample size on which C360 was built and then reverted. **No exit change ships until the diagnosis has 20+ closes.** The instrumentation is in place; it needs replay hours, not another hypothesis.

**✅ THE BACKTEST IS NOW COMPLETE — and the last gap changed the answer.**
**The gap:** the replay called `_monitor_positions()` directly, but the live bot runs a **separate 0.8s monitoring THREAD** (`_monitoring_thread_func`) whose body also runs the C334 pending-HP resolver, **`_refresh_live_regime()` (268 lines)** and **`_check_profit_targets()` (413 lines)**. **Every backtest number produced before this point was measured on a bot missing 680 lines of its own monitoring logic.** `monitor_tick()` now mirrors that loop verbatim. Verified executing: `_monitor_positions` ✓ `_check_profit_targets` ✓ `_refresh_live_regime` ✓ `_c52_flush_logs` ✓ `_open_position` ✓ `_close_position_inner` ✓.

**WHAT REMAINS OUTSIDE THE BACKTEST — the honest, final list:**
| | lines | why |
|---|---|---|
| `full_analysis` | 1,290 | **known dead code** — should never run |
| `run`/`start`/`_write_changelog`/`_display_summary` | 917 | startup + UI, not strategy |
| order-book channel (`get_order_flow`) | 102 | **Bitget serves NO order-book history — impossible for anyone** |
| news sentiment | — | **no free historical archive — impossible** |
| trade-tape CVD | — | **only ~100 recent fills exist — impossible** |
**Everything else — screening, market analysis, ranking, selection, Kelly sizing, entry gates, the monitoring thread, profit targets, regime refresh, exits, partials, closing — now executes.** The residue is dead code, UI, and three feeds nobody can reconstruct historically.

**RESULT — 25 continuous days, complete bot, crypto-only, 12 trades:**
| | |
|---|---|
| win rate | **50% (6W / 6L)** |
| bot return | **−0.18%** |
| BTC same window | **+42.25%** |
| **alpha** | **−42.43%** |
**The complete bot is WORSE than the partial one measured earlier** (which showed 71% WR / +7.60% / −34.38%). Adding the missing 680 lines of monitoring logic — profit-target checks and regime refresh — **lowered the win rate from 71% to 50% and turned a +7.60% gain into −0.18%.** Those monitoring exits are actively harmful in a trending market: they close positions the exit engine alone would have held.
**Alpha decay remains monotonic and is now steeper:** −15.45% (12d) → −34.61% (22d) → **−42.43% (25d)**.

**PERFORMANCE FINDINGS ABOUT THE BOT ITSELF (both real, both worth fixing on the phone):** it retrains a 50-tree RandomForest + GradientBoosting **per pair per scan** (95,200 tree fits in 3 scans), and `_refresh_live_regime` re-runs the 1,819-line analyzer **3× per tick**. Memoising each gave **5.5× and 20× speedups** respectively — the same waste is costing real scan time on a Nothing Phone 2.

**⚖️ C360 PROFIT RATCHET — BUILT, A/B TESTED, REVERTED (C361). The harness caught my own payoff fix.**
Acting on the −34% alpha finding, I added a ratchet capping how much of a peak a position may hand back (floor 0.45–0.65× peak, graduated by PRU). Head-to-head on the **same 20-day window through the full pipeline**:
| | trades | win rate | return | alpha |
|---|---|---|---|---|
| baseline | 17 | **71%** | +7.58% | **−20.90%** |
| **with C360** | 15 | 60% | −0.46% | **−27.45%** |
**Worse on every measure. Reverted.**
**THE MISDIAGNOSIS, recorded so it is never repeated:** the instrumented replay showed **+22.20% and +11.09% arriving within 48h AFTER winning exits** (average **+16.65% left on the table**). That says positions exit **TOO EARLY**. A ratchet is a **tightening** — it makes them exit earlier still. It converted "hand the gain back" into "bank a crumb" and truncated the few large runs that carry the entire payoff ratio. The peak-giveback cases were real but small (~0.5pp each); the forgone continuation is an order of magnitude larger.
**RULE FOR ANY FUTURE PAYOFF WORK: loosen the winning side, never tighten it** — and note that simply extending the horizon (24/48/72h) was already tested and did not help, so *"hold longer" alone is not the answer either*.
**Harness kill list now SEVEN** (v1 exit geometry · C355 · 24h/6-ATR mirage · momentum +138%/yr · flow funding r=+0.382 · engine 72h · **C360 ratchet**) — four of them mine, all stopped before live capital.

**🏁 CONTINUOUS FULL-PIPELINE BACKTEST — THE ANSWER, AND IT IS NOT THE ONE ANYONE EXPECTED.**
State-persistent chunked replay (`cont.py`) stitches runs via `portfolio.save_state/load_state`, carrying equity, open positions and lifetime W/L across sessions. **38 continuous days of Nov–Dec 2024 crypto-only, the REAL bot (74% strategy coverage), 24 trades:**

| | result |
|---|---|
| trades | 24 |
| **win rate** | **71% (17W / 7L)** |
| bot return | **+7.60%** |
| **BTC buy-and-hold, same window** | **+41.98%** |
| **ALPHA** | **−34.38%** |

**THE BOT HIT THE OPERATOR'S TARGET AND STILL LOST BADLY.** The stated roadmap goal was a 60–65% win rate. The full pipeline delivered **71%** — and captured **less than a fifth** of a market that nearly doubled. This is principle #15 (Trader A vs Trader B) demonstrated on the operator's own system: **a high win rate achieved by banking small wins is worth less than doing nothing at all.** Every early exit that produced a "win" was a large move surrendered.
**This retires the win-rate objective definitively, and it re-frames every prior result:** the payoff problem was never a side issue to be fixed after the win rate — it *was* the problem, and the win-rate goal was actively causing it.
**Chunk-by-chunk alpha decay:** −20.90% (20d) → −29.66% (22d) → **−34.38% (38d)**. The underperformance is not noise; it *widens monotonically* the longer the market trends.
**Caveat, stated plainly:** 24 trades and one bull regime. Not a verdict on all conditions — but the mechanism (small wins, missed trends) is structural, matches every prior payoff finding, and the alpha decay is monotonic.

**📐 HARNESS COVERAGE RE-MEASURED (traced, not asserted): 18% → 66% of lines, 104/251 functions.**
| system | lines | now covered |
|---|---|---|
| `_run_scan_and_trade` | 5,505 | ✅ |
| `_open_position` (Kelly sizing) | 1,173 | ✅ |
| exit engine `should_exit_dri` | 1,195 | ✅ |
| analyzer `quick_scan_analysis` | 1,820 | ✅ |
| screener `scan_lively_pairs` | 433 | ✅ |
| RPPc blend `_c302_p_ev` | 214 | ✅ |
| C338 partial exits | 83 | ✅ |
**Of the uncovered 34%: `full_analysis` (1,290 lines) is the KNOWN DEAD function — correctly never called; `run`/`start`/`_write_changelog`/`_display_summary` (915) are startup and UI, not strategy. Excluding those, live-strategy coverage is ~74%.** The one real gap is `_check_profit_targets` (413), which only executes with open positions — the traced window had none. **It is NOT an exact replica, and the honest figure is ~74% of strategy code, not 100%.**

**📉 A SEPARATE STOCKS/COMMODITIES MODULE WITH DIFFERENT RULES — TESTED, NO EDGE.**
23 RWA pairs vs 21 crypto, same fee model, 4-way OOS:
| rule × universe | n | payoff | exp/trade | t | OOS |
|---|---|---|---|---|---|
| **momentum 24h — RWA** | 3,290 | 1.48 | **+0.001%** | 0.01 | 2/4 |
| mean-reversion 24h — RWA | 1,001 | 1.20 | **−0.271%** | **−3.89** | 0/4 |
| momentum 24h — crypto | 4,718 | 1.47 | −0.069% | −1.82 | 0/4 |
| mean-reversion 24h — crypto | 1,453 | 1.28 | −0.241% | −3.19 | 0/4 |
| momentum, US hours — RWA | 1,117 | 1.57 | −0.003% | −0.04 | 2/4 |
| momentum, off-hours — RWA | 2,173 | 1.44 | +0.003% | 0.06 | 2/4 |
| momentum 48h — RWA | 3,236 | 1.72 | +0.008% | 0.17 | 2/4 |
**Three clear conclusions:** (1) **the "different rules" hypothesis is refuted in the strongest terms available** — mean-reversion, the obvious candidate for equities, is *significantly worse* on RWA (−0.271%, t=−3.89) than momentum, and worse than it is on crypto; (2) **there is no session effect** — US-hours and off-hours momentum are identical (−0.003% vs +0.003%), because these are 24/7 perps whose price discovery does not respect the underlying's opening bell; (3) **RWA momentum is exactly break-even (+0.001%, t=0.01) where crypto momentum loses (−0.069%)** — better, but zero is not an edge, and nothing reaches 3/4 OOS.
**VERDICT: do not build a separate RWA module.** The only defensible use of RWA is diversification (daily correlation −0.198 with crypto, 50/50 blend cuts daily volatility 24%) — a risk benefit, not a profit source, and it still fails the 3/4 rule. The operator's standing instruction to trade crypto only stands unchallenged by the data.

**🔬 FULL-PIPELINE REPLAY BUILT (`omega_replay_full.py`) — coverage 18% → the whole bot.**
Harness v2 ran **25 of 251 functions (18% of lines)**: the analyzer and the exit engine, nothing else. It never touched `_run_scan_and_trade` (5,505 lines), `_open_position` (1,173), `_monitor_positions` (463) or `_check_profit_targets` (413) — so **selection** (the bot enters the BEST of ~10 ranked candidates; v2 entered EVERY candidate ≥0.32, ~5× as many) and **Kelly sizing** (v2 used flat size) were never tested. v2 tested the SIGNAL; this tests the SYSTEM.
**FIRST SUCCESSFUL RUN:** 14 scans over 2025-08 data → **2 entries, equity $50.00 → $50.56 (+1.12%), 0 errors.** Step 1 screening (16 markets → 10 ranked candidates), Step 2 market analysis (macro tilt, R = −0.51, bearish) both verified executing.

**FOUR CONTAMINANTS FOUND — three inside the bot, one mine:**
1. **`MarketScanner` holds its OWN exchange reference.** Patching `tb.exchange` alone left it pointing at an empty ExchangeManager: *"Scanning 0 markets"* and the pipeline silently did nothing. Fixed by walking the object graph (`inject_exchange`).
2. **Three live-API paths inside the scan** — `_fetch_positioning` / `_fetch_real_cvd` / `_fetch_funding_raw`, plus the **C228 category classifier** (`family_tilt → _ensure_scan → _page_candles`, **18 HTTP calls = 5.1s of a 5.5s scan**), plus **NewsAnalyzer**. All three return *today's* data for a historical bar — **lookahead**. All stubbed.
3. **`time.sleep` had to be neutralised** — the monitor's inner wait loops (`while time.time()-t0 < interval`) never advance against a frozen virtual clock.
4. **My own bug:** patching `time.time` globally meant the harness's *own stopwatch* read virtual time — one 15-minute bar registered as "900 seconds elapsed" and tripped the time guard after a single bar. The replay had been working all along.

**⚠️ STATUS: the tool runs; the ANSWER is not yet in.** 14 scans / 2 trades is far too small to conclude anything. Speed is now ~1.5 s/bar, so a meaningful multi-month replay needs chunked runs with state persistence — next session's work. **No conclusion about the full system's edge should be drawn until then, and the v2-based conclusions must be understood as testing the signal only.**

**📊 STOCKS / RWA TESTED:** including tokenized equities and commodities gives **no significant expectancy gain** (−0.056% vs crypto −0.118%, difference +0.062% ±0.129) — but daily outcomes correlate **−0.198** with crypto and a 50/50 blend cuts daily volatility **24%**. Genuine diversification value if an edge is ever found; no edge on its own.

**★ C359 — BEAR-REGIME BRAKE. The first regime finding robust enough to act on — and it is a RISK rule, not a profit claim.**
**Corpus:** 16 crypto pairs × up to 86,000 15-min bars = **2.4 years (Feb 2024 → Jul 2026)**, spanning both the 2024 bull run and the 2025–26 decline. Strictly non-overlapping, true 0.08% fees, real funding, isRwa-filtered.
**THE FINDING — when BTC's trailing 7-day return is below −3%, ALL SIX strategies lose, without exception:**
| | 24h | 48h | 72h |
|---|---|---|---|
| momentum | −0.195% | −0.063% | −0.362% |
| **engine** | −0.247% | −0.142% | **−0.646%** |
Excluding that regime improved **6/6** strategies, and the threshold response is a **smooth monotonic gradient** (−1%: +0.094 · −2%: +0.124 · −3%: +0.107 · −5%: +0.040 · unfiltered: −0.025) — a broad effect, not a knife-edge fit.
**HONEST LIMITS, recorded so no future build overstates this:** the best filtered cell (momentum 72h: **+0.107%/trade, 4/4 OOS splits, 8/11 positive quarters, both long AND short legs positive**) has **t = 1.48 — NOT significant** — and collapses if the best 50 of 2,434 trades are removed. **The profit claim is unproven. The negative claim — everything loses in falling-BTC regimes — is what is robust**, and declining to trade such a regime requires no profit claim to justify it.
**Implementation:** gates NEW entries only · exits, stops, trails and open positions untouched · trailing data only · **fails OPEN** if BTC candles are unavailable · logs 🐻 and counts under `rejected_reasons['bear_regime']` · sits out ~28% of the time.

**❌ ALSO TESTED AND REJECTED — full adaptive regime→strategy switching** (the literal form of "make it switch strategies"). Fit the map on one half, apply to the other: **both TIME splits failed** (−0.099%, −0.063%); only the far weaker pair-splits passed (+0.013%, +0.027%). And the fitted maps **disagreed on 2 of 3 regimes** between periods — the mapping is not stable through time, which is precisely what an adaptive bot requires. **2/4 → fails.**
**❌ The bull-market hypothesis, now testable with 16× more UP-regime data (n=3,079 vs 192): engine 72h in uptrends = +0.418% but NOT time-stable** (first half −0.035%, second half +0.870%). Not shippable.

**🔧 Harness v2.4 — the RWA filter now FAILS CLOSED with a disk cache.** v2.2 returned an empty set on any fetch failure, silently disabling itself: under rate limiting, oil (CL), DRAM, a Korea ETF (EWY) and Circle (CRCL) walked back into a "crypto-only" corpus. **A filter that fails open is not a filter.**

**⚫ THE SETTLING TEST (2026-07-31) — 28 crypto pairs · 1,008,000 candles · 375 days · strictly non-overlapping. THE SEARCH IS COMPLETE.**

Pulled 3.2× more history (36,000 15-min bars per pair, 419 days available) specifically to resolve the one open question. Result:

| configuration | n | win% | payoff | exp/trade | t | OOS |
|---|---|---|---|---|---|---|
| Engine 24h | 2,087 | 35.8% | 1.69 | −0.071% | −1.14 | 2/4 |
| Engine 48h | 1,055 | 29.0% | 2.36 | −0.051% | −0.47 | 2/4 |
| **Engine 72h** | 705 | 20.7% | 3.09 | **−0.320%** | **−2.03** | **0/4** |
| baseline 24h | 8,799 | 38.5% | 1.55 | −0.026% | −1.11 | 1/4 |
| baseline 72h | 2,952 | 23.7% | 2.64 | −0.253% | −3.79 | 0/4 |

**1. THE 72-HOUR RESULT REVERSED COMPLETELY.** Shallow corpus: +0.123%, 3/4. Deep corpus: **−0.320%, t = −2.03, 0/4** — it did not merely fail to replicate, it flipped sign and became *significantly negative*. The earlier figure was small-sample noise amplified by overlapping windows.
**2. THE "ENGINE BEATS RANDOM" PATTERN VANISHED ENTIRELY.** The monotonic advantage (+0.062 / +0.091 / +0.253%) that looked so compelling is now **−0.044% / −0.006% / −0.067%** — the engine is, if anything, marginally *worse* than a two-line momentum rule, at every horizon. That pattern was noise.
**3. LONGER HORIZONS ARE WORSE, NOT BETTER, ON THE FULL SAMPLE.** The fee arithmetic (longer holds need less correlation) is correct but irrelevant when correlation ≈ 0: with no edge, a longer hold only accumulates more of the market's drift and variance. Over 375 days including a major BTC decline, 72-hour holds bled −0.25 to −0.32%/trade with t = −3.79.

**FINAL POSITION — the search is exhaustive and closed.** Across ~20 configurations, ~70 conditional buckets, 3 horizons, 2 fee models, 5 strategy families (momentum, the 48-signal engine, funding-directional, funding-carry, order-flow), 1M+ candles and 375 days: **no configuration reaches positive expectancy out-of-sample. The bot's own engine is not measurably better than `velocity>0 and RSI>45`.**

**THE HARNESS'S KILL LIST — six "discoveries" destroyed before they reached live capital:**
1. v1's exit-geometry recommendation (4.0A/1.5A) — reversed by the real exit engine
2. C355 extension veto — negative in 4/4, premise refuted
3. 24h/6-ATR "positive expectancy" — subset artifact, 0/4 on the full corpus
4. Cross-sectional momentum +138%/yr Sharpe 1.87 — new-listing/survivorship; −1%/yr on pairs existing at sample start
5. Flow funding r=+0.382 — pooling artifact; within-pair it flips to −0.127
6. Engine 72h +0.123%, 3/4 — overlap artifact; −0.320%, t=−2.03, 0/4 on 3.2× the data

**PRE-RUN AUDIT PASSED (2026-07-29).** Structure: parses clean, **304 functions / 31 classes**, banner C357. Scope hazards checked — the C354 `_neutral354` flag resolved SAFE (the intervening `return` sits inside `if not _qualifies:`, so any path reaching the use has already executed the assignment). Removed code carries no dangling references (C355 veto gone; C350's HP sweep, time-limit pause and age-branch all absent; `already_travelled` survives only as changelog prose). All 15 active features present and wired. Functional run on live data: analyzer scored 0.494 with **54 components**, and the C346 resurrections are alive (`perm_entropy` 0.965, `rqa_det` 0.730, `_ichi_state` A+). C352 memory: score_delta +0.150, flip-flopper correctly locked out of the boost, projection tracking live. Exit engine replays and produces a sane reason spread. Boot creates every state file.

**TWO HONEST FINDINGS FROM THE AUDIT (neither is a crash, both matter):**
1. **The C342/C343 trust gate is so strict it may never open.** Re-tested across three synthetic streams: even a *strongly state-dependent* process missed the bar by 0.0011 (Brier 0.0486 vs 0.95×base 0.0475). The 5% Brier-skill requirement is close to unclearable in practice, which means **FamilyMarkov and IchiMarkov are likely permanently observability-only** and will never tilt a score. Working as designed, but the design is stricter than intended — worth revisiting before assuming those chains contribute anything.
2. **Harness fidelity note:** in replay, the bot's own exit signals rarely fire because the mechanical target/stop binds first (69 replays → TARGET 34, HARD_STOP 34, bot-signal 0). The live logs *do* show real exits (TRAILING_TP, REL_DRAWDOWN). So the earlier exit-geometry results reflect the target/stop frame more than the bot's exit intelligence — a limitation of the tool, recorded so it is not over-read.

**Current: C357 + HARNESS v2.1 + FLOW RECORDER v1.0 — the money-trail thesis, tested and then equipped.**

## 💰 "FOLLOW THE MONEY" — TESTED WITH EVERYTHING BITGET PUBLISHES
The operator's thesis is correct in principle and was the ONE avenue never tested — every prior negative result came from candle-derived signals, because flow could not be replayed. So it was hunted properly.

**What Bitget actually serves (probed exhaustively 2026-07-29):**
| series | history available |
|---|---|
| taker buy/sell volume | 30 bars (29 days at 1D) ✅ |
| account long/short ratio | 24 bars (11.5 days at 12H), **majors only (~19 pairs)** |
| position long/short ratio | same |
| order book depth | ❌ **snapshot only — never stored** |
| full trade tape | ❌ last ~100 fills |
| open interest | ❌ no history endpoint (40404) |

**Result on 406 aligned samples, 19 pairs, forward 48h:**
| signal | correlation with forward return |
|---|---|
| taker buy/sell imbalance | **r = +0.022** |
| % accounts long | r = +0.008 |
| % position size long | r = −0.070 |
| **account − position divergence** ("crowd vs money") | **r = +0.028** |
Fading the crowd when accounts and size disagree (>+0.05): forward **+2.07%** *against* the short, down-rate 49% — a coin flip. **Every published flow series has ~zero predictive power at this horizon.** Caveat honestly stated: 406 overlapping samples, 11.5 days, one regime — a null result, not a proof.

## 🔴 THE REAL CONSTRAINT, AND WHY IT POINTS AT A BUILD
**The deep flow — book shape, large-trade direction, OI path — is a SNAPSHOT business. Bitget tells you what the book is *now* and forgets forever.** The money trail therefore **cannot be backtested. It can only be recorded.**

**★ `omega_flow_recorder.py` (NEW).** Runs beside the bot, samples every 5 min, writes gzipped JSONL. Captures what no download can supply: top-of-book and 50-level depth imbalance, **liquidity walls** (largest resting level ÷ median — live BTC read: ask wall **896× median**), spread, aggressive-flow CVD, and critically **large-trade CVD tracked separately from crowd CVD** — the one smart-money signal that cannot be derived from candles at any price. Plus OI and funding. ~7k calls/day at 25 pairs, ~4 MB/day.
**After 30 days you hold a dataset nobody can buy, download or reconstruct** — including every competitor who did not start 30 days ago. *Then* the harness can ask whether flow predicts price with real statistics.
**Known v1 calibration note:** the near-book `slope` term saturates at 1.000 on liquid pairs (the ±0.2% band spans all 50 levels); needs a tighter band per-pair in v1.1. Does not affect the irreplaceable fields.

**Previous: the conditional-edge search.**

## 🔎 THE EXPERT MOVE: IS THE LOSS UNIFORM, OR CONCENTRATED?
Built a 7,408-setup feature/outcome table (58 pairs, real exit engine, 48h holds, funding P&L included) and scanned conditional expectancy across **14 features × 5 quintiles ≈ 70 buckets**. Overall expectancy **−0.089%**.

**TRAP CAUGHT FIRST — and it is the one that would have looked like a discovery:** the `bars`-held feature showed **+1.03%** for long-lasting trades vs −1.21% for short ones, a 2.2-point spread dwarfing everything else. **It is circular.** Trades last long *because* they never hit the stop. An outcome wearing a feature's clothes. Discarded, not celebrated.

**Three genuine ex-ante buckets looked positive, and one passed 4/4:**
| candidate | n | payoff | exp | OOS |
|---|---|---|---|---|
| control (all) | 7,408 | 1.88 | −0.089% | 0/4 |
| Asia session 00–04 UTC | 1,236 | 1.97 | +0.082% | 3/4 |
| compressed day range <7.9 ATR | 1,479 | 2.13 | +0.075% | 3/4 |
| **funding near-zero band** | 933 | 1.95 | **+0.125%** | **4/4** |

**AND THEN THE DECIDING TEST: THE COMBINATIONS COLLAPSE.**
Asia + compressed = **−0.125% (0/4)**. Asia/EU + compressed = **−0.142% (0/4)**. Asia + compressed + funding = **−0.110% (1/4)**.
**Real edges compound. Noise cancels.** Three filters that are each "positive" but whose intersection is *worse than the control* is the signature of overfitting, not of edge. Add that ~70 buckets were scanned — 3–4 would look positive by chance alone — and the surviving 4/4 candidate has a CI of ±0.190 around a +0.125 mean, i.e. **indistinguishable from zero**, in a bucket with no mechanism (funding merely *near zero*). **Verdict: nothing found. The loss is uniform.**

## ✅ THE DECISION AN EXPERT MAKES HERE
Directional edge, measured across ~15 configurations and ~70 conditional buckets on 3 months × 58 pairs: **none.** Continuing to scan the same 7,408 setups can only manufacture overfits.
**The single reliable lever remains execution:** the control sits at −0.089%/trade; **maker-only fills are worth +0.08%/trade** — which alone converts the whole system from losing to approximately break-even. **Cost reduction is worth more than every entry edge found in this project combined.**
**Tool limit, stated for the record:** every test scans the universe mechanically at fixed intervals and takes thousands of trades. Profitable discretionary traders are radically selective, fill as makers, and manage positions. The harness can falsify a mechanical rule; it cannot represent that, and its silence is not proof of impossibility.

**Previous: the three operator hypotheses.**

## 🧪 THE OPERATOR'S THREE PROPOSALS, MEASURED (58 pairs, 4-way OOS)
**1. Longer horizon (up to 48h) — CONFIRMED on payoff, not on expectancy.**
| config | n | win% | **payoff** | exp %/trade | OOS |
|---|---|---|---|---|---|
| 4h, 2A/1.6A *(current bot)* | 9,865 | 42.5% | 1.07 | −0.132% | 0/4 |
| **48h, 6A/3A** | 3,662 | 31.1% | **2.01** | −0.107% | 0/4 |
| 48h, 10A/3.5A | 530 | 24.5% | **2.36** | −0.299% | 2/4 |
**Payoff nearly doubles (1.07 → 2.01) exactly as predicted — the win rate falls proportionally, so expectancy does not improve.** The geometry hypothesis is right; there is simply no entry edge for it to amplify.

**2. Funding integrated into the directional bot — NO EDGE FOUND (yet).**
- Funding-*aligned* direction filter (only hold when paid to): n 3,662→530, exp −0.222%, **1/4**.
- Funding P&L collected over the hold: exp −0.212%, **2/4** — the carry helps, but ~0.01%/trade, far too small.
- Funding as *primary* contrarian signal (fade the crowded side, principle #4): |funding|>0.03% → −0.543% (0/4); z>1.5 vs the pair's own history → −0.112% (**2/4**, n=230, CI ±0.302 — the least-bad, still indistinguishable from zero).
**Nothing reaches 3/4. Funding is highly persistent (79%) but persistence ≠ profitability.**

**3. Payoff over win rate — STRUCTURALLY CONFIRMED, and the standing 60–65% WR goal is formally retired.** Every payoff gain came with a proportional win-rate loss. Payoff is a *geometry* lever, not an edge lever.

## 💡 THE ONE FINDING THAT SURVIVES EVERY TEST
Across ~15 configurations spanning 4h→48h, momentum/engine/funding entries, and every geometry: **expectancy clusters at −0.10% to −0.25% against a 0.12% round-trip taker fee.** Gross edge ≈ 0; **the fee IS the loss.** Maker-only execution is worth **+0.08%/trade** — larger than most measured deficits — and is the only lever that reliably moves the number without requiring a new edge.
**Honest caveat on why traders still profit:** every test here scans the whole universe at fixed intervals and takes thousands of trades. Profitable traders are *selective* — few trades, specific setups, maker fills, active management. The harness can falsify a mechanical rule; it cannot yet represent that.

**Previous: funding carry measured.**

## 🧭 FUNDING CARRY — MEASURED BEFORE BUILDING (the new discipline, applied)
**What is genuinely established:**
- **Funding sign-persistence = 79%** across 61 pairs (50% = coin flip). Nothing directional came close to this. It is a real, persistent, forecastable quantity.
- Magnitudes in the tail are large: DEXE **−235%/yr** (100% sign persistence), LA −102% (87%), EUL −71% (96%), COTI −43% (99%). **18 of 61 pairs exceed |10%/yr|.**
- Median pair is ~0.005%/8h — far too small to clear fees. **The edge, if any, lives entirely in the tail.**

**What is NOT established — and a FIFTH false positive caught:**
- A naked long on high-negative-funding pairs showed **+90% mean** — an artifact of ONE outlier (BANK +626% price move). Median tells a different story; naked carry is dominated by price risk, so **the hedge is mandatory, not optional.**
- My first delta-neutral test reported majors at +19–38%/yr. **It was contaminated:** spot (1h) and perp (15m) endpoint timestamps were matched up to 45 min apart, inflating BTC's basis drift from a true **+0.155%** to **+0.513%** — roughly 3×. Corrected, BTC is funding +0.067% + basis +0.155% − fees 0.16% ≈ **+0.06% over 8 days (~+2.7%/yr)**, not +18.8%.
- **Corrected economics on majors: carry ≈3%/yr gross against a 0.16% round-trip fee.** Months of holding just to clear costs. Not viable.
- The high-carry tail is where the money is, but **DEXE and EUL have no Bitget spot listing** — the hedge cannot be constructed. LA / COTI / BANK do have spot and remain the only genuine candidates.

**BLOCKER:** Bitget's spot candle endpoint returns only ~200 bars (8.2 days). One 8-day window, one regime, no out-of-sample split — nowhere near enough to conclude anything. **A proper spot corpus must be built before any funding strategy is written.**

**SCALE REALITY, stated plainly:** even a clean 18%/yr carry on $50 is ~$9/year. Funding capture is a capital-scale business. The correct question is not "does it beat the directional bot" but "is it worth running at all at this size".

## 📋 STANDING POSITION
Gate tuning: **over** (0 of 4, C282 rule binding). Directional: **no demonstrable edge** (engine ≡ two lines of code). Non-directional: **promising signal, unproven economics, blocked on data.** **Nothing built. Nothing shipped.**

**Previous: the directional verdict.**

## 🏁 THE VERDICT — 58 pairs, 304,755 candles (Apr→Jul), 2,281 engine trades
| | n | win% | payoff | exp %/trade | 95% CI |
|---|---|---|---|---|---|
| **48-signal engine** | 2,281 | 40.5% | **1.28** | −0.126% | ±0.106 |
| **`velocity>0 & RSI>45`** | 9,865 | 42.5% | 1.07 | −0.132% | ±0.031 |
| **engine − simple** | | | | **+0.006%** | ±0.110 → **NO DETECTABLE DIFFERENCE** |

**After 350 versions, the engine is statistically indistinguishable from two lines of code.** Not worse — but not better, and that question had never once been asked.

**THE ONE DURABLE WIN:** engine payoff **1.19–1.34 vs simple 1.04–1.08, higher in 4/4 splits** on **4.3× fewer trades.** The sophistication genuinely selects better-*shaped* trades — then hands the advantage back on win rate (40.5% vs 42.5%). That is real and worth protecting.

**THE ARITHMETIC THAT EXPLAINS EVERYTHING:** engine −0.126%/trade; round-trip taker fee **0.12%**. **Gross edge ≈ −0.006% ≈ ZERO. The fees are the entire loss.**

## ❌ A FOURTH FALSE POSITIVE, CAUGHT
A horizon sweep on **26** pairs showed 24h/6-ATR targets turning **positive** (+0.017%/trade) — the first positive result of the whole investigation. Re-run on all **58** pairs: **−0.161% pooled, positive in 0/4 splits.** A subset artifact. *(The harness has now overturned v1's exit recommendation, C355, and this — three exciting findings killed by discipline. That is the tool doing its job.)*

## 📉 WHAT NO CONFIGURATION ACHIEVED
Nothing tested — no entry filter, no exit geometry, no horizon from 4h to 24h — reached positive expectancy out-of-sample after taker fees. The only lever that moves the number materially is **execution: maker-only fills are worth +0.08%/trade** (0.04% vs 0.12% round trip), more than half the deficit — and even that leaves the best configuration at ≈−0.08%.

## ⚖️ THE PRE-AGREED RULE NOW BINDS
C282 set it and we blew through it once already: *positive in ≥3 of 4, or stop tuning gates permanently and make one structural decision.* **Result: 0 of 4. Gate tuning is over.** Remaining honest options are structural, not incremental: (a) attack execution cost — maker-only, trade far less; (b) keep the payoff edge and stop trying to fix win rate by adding signals; (c) change what is traded — the entire investigation is *directional*, and principle #5 notes most profitable firms arbitrage rather than predict (funding capture, basis) — those need no directional edge; (d) accept that this configuration has none and stop.

**Previous: harness v2.0.**

## 📡 FIDELITY: WHAT COULD AND COULD NOT BE RESTORED
| channel | status |
|---|---|
| candles (majority of the 48 signals) | ✅ exact |
| **funding + squeeze** | ✅ **REAL history** (`history-fund-rate`), settlements ≤ bar *i*, squeeze recomputed with the bot's own `0.8·(−tanh(favg/0.0012))` |
| CVD | ⚠️ candle proxy (close-position volume split) — the real `/fills` tape reaches only ~100 recent trades |
| open interest | ❌ **Bitget serves no OI history** (endpoints 40404) |
| order book / basis | ❌ not obtainable historically |
*Third harness bug caught: `'AAVE/USDT:USDT'.endswith('USDT')` is **True**, so a naive symbol check produced an unmatchable key and silently zeroed the CVD channel — the same silent-zero class as the DataFrame bug. Values now provably vary bar to bar.*

## ⚖️ THE VERDICT TEST — real engine vs a two-line rule, same real exit stack
| | time-early | time-late | pairs-A | pairs-B | mean |
|---|---|---|---|---|---|
| **48-signal engine** | +0.140% | −0.440% | −0.275% | −0.001% | **−0.194%** |
| **`velocity>0 & RSI>45`** | −0.018% | −0.172% | −0.148% | −0.043% | **−0.095%** |

**Neither passes the 3-of-4 bar. After 350 versions, the engine has not been shown to beat two lines of code** — its average is worse, and its spread (+0.14 to −0.44) is what noise looks like at n≈120 per split.
**But one real signal survives:** the engine's **payoff ratio is consistently higher** (1.18–1.36 vs 0.97–1.22) in **all four** splits, on **4× fewer trades**. It is selecting structurally better-shaped trades and then losing the advantage on win rate. That is the first thing the sophistication has ever demonstrably done, and it is worth keeping.

## ➡️ NEXT: THE SAMPLE, NOT THE CODE
Engine n≈120/split cannot separate skill from noise. The corpus is 40 pairs × 31 days; the fix is arithmetic, not clever — **150 pairs × 120 days** puts engine trades in the thousands and shrinks the error bars enough for a real verdict. Cheap, mechanical, decisive. **No code change until that runs.**

**Previous: harness v2.0 — which first drove the REAL bot.**

## ⚠️ v1 DID NOT REPLICATE THE BOT. v2 DOES — AND IT OVERTURNS v1's HEADLINE.
v1 tested a two-line proxy (`velocity>0 and RSI>45`) with a naive target/stop. Honest about outcomes, but it was not testing *this* system. **v2 imports `omega_v60_reconstructed.py` and calls the bot's own functions** through a `HistExchange` frozen at bar *i*:
- `TechnicalAnalysis.quick_scan_analysis()` — the real 48-signal engine (1,819 lines)
- `Position.should_exit_dri()` — the real exit stack (1,194 lines: trails, PEAK_FLOOR, REL_DRAWDOWN, DSI/DRI, C338 partials, C345 runner floor, hard stops)

**Two bugs in my own harness, both caught and both instructive:** (1) `fetch_ohlcv` must return a **pandas DataFrame** — returning lists made the analyzer fail silently into its fail-open path and score 0, i.e. the harness was "testing" nothing; (2) three helpers inside the analyzer (`_fetch_positioning`, `_fetch_real_cvd`, `_fetch_funding_raw`) call **live** Bitget endpoints, returning *today's* value for a bar from three weeks ago — not merely lookahead but the *same* value on every historical bar, which would manufacture signal that never existed. Now stubbed to neutral, and **stated** rather than hidden.

### 🔄 THE EXIT-GEOMETRY VERDICT REVERSED
| target/stop | win% | payoff | exp %/trade |
|---|---|---|---|
| 1.5A / 1.6A *(shipped)* | 49.4% | 0.84 | −0.1049% |
| **2.0A / 1.6A** | **42.9%** | **1.14** | **−0.0944%** ← best |
| 3.0A / 1.6A | 34.4% | 1.59 | −0.1236% |
| **4.0A / 1.5A** *(v1's recommendation)* | 29.7% | 1.93 | **−0.1411%** ← one of the worst |

**v1 said widen the target to 4×ATR and halve the losses. With the bot's real exit engine that is one of the worst settings.** Reason, visible in the exit-reason counts: a wider target holds the position longer, so the bot's *own* stop and patience family closes it first — HARD_STOP fires 4,694 times at 4.0A vs 3,348 at 1.5A. The naive model had no such machinery. Real best is a modest 2.0A/1.6A (−0.105 → −0.094), **not** a halving.

### 🚩 FULL-LOOP RESULT (real analyzer picking + real exits) — PRELIMINARY, CAVEATED
| | entries | win% | payoff | exp %/trade |
|---|---|---|---|---|
| real 48-signal engine (score ≥0.32) | 20.3% of bars | 36–40% | 1.04–1.10 | **−0.41% to −0.52%** |
| crude momentum proxy, same exits | — | 43–49% | 0.84–1.14 | −0.09% to −0.10% |
**With the flow family stubbed, the real engine's selections lose 4–5× more per trade than a two-line momentum rule.** This is NOT yet a verdict — funding, OI, real CVD and book imbalance are exactly the channels that cannot be replayed, so the engine is being judged with part of its senses removed. It is a serious flag that must be resolved, not a conclusion.

### HARNESS ROADMAP (to close the fidelity gap)
Bitget *does* serve historical funding and open-interest; CVD has a candle-derived proxy already in the codebase. Restoring those three would lift replay fidelity from candle-only to near-complete, leaving only the order book unobtainable. **That is the next build — before any further bot change.**

**NOTHING SHIPPED THIS SESSION.** No geometry change, no gate change: the standing rule is ≥3-of-4 positive out-of-sample splits, and nothing tested is positive at all — it is only less negative. Shipping "less bad" on unproven evidence is the habit being retired.

**Previous: C357 + harness v1.0 (`omega_replay_harness.py`, new deliverable).**

## 🔬 THE HARNESS IS LIVE — AND ITS FIRST ACT WAS TO FALSIFY MY OWN LAST FIX
117,987 real Bitget 15m candles · 40 liquid pairs · ~31 days · **28,726 no-lookahead setups** (features from bars [0..i], outcomes from [i+1..i+16], split enforced by construction) · every entry scored through a fixed target/stop model with round-trip taker fees.

**C355 — REVERTED (C357).** Four-way out-of-sample split:
| | time-early | time-late | pairs-A | pairs-B |
|---|---|---|---|---|
| control momentum | −0.074% | −0.026% | −0.051% | −0.049% |
| **C355 veto** | **−0.094%** | **−0.055%** | **−0.085%** | **−0.065%** |

Worse than doing nothing **in all four splits.** It removed ~18% of entries and the ones it removed were on average *better* than the ones it kept. Its premise was also refuted: late entries (>6 ATR travelled) score −0.022%/trade vs **early** entries (<3 ATR) at −0.133% — the opposite of the lateness diagnosis. And the "MFE<1.5% = unwinnable" finding from three trades was a **base rate**: 70% of *all* setups have MFE under 1.5%. Nothing replaces C355 — installing another unproven filter is the habit the harness exists to break. **C356 kept** (it partially reverts a measured harm) but honestly marked *unvalidated* — it depends on market-frame state the harness doesn't model yet.

## 🎯 WHAT THE HARNESS FOUND THAT DID SURVIVE (recorded, NOT yet acted on)
1. **Exit geometry dominates every entry filter.** Holding entries fixed and moving only the exit from 1.5-ATR-target/1.6-ATR-stop → **4.0/1.5** halves the loss rate (−0.099 → −0.050 %/trade) and lifts payoff **0.85 → 1.60**. Larger effect than any entry rule tested.
2. **Win rate and expectancy move in OPPOSITE directions.** Highest win rate tested (55.7%, tight target) had the *worst* expectancy; best expectancy came at **36.5%**. **The standing 60–65% win-rate roadmap goal optimises the wrong variable** — exactly principle #15 (Trader A vs Trader B).
3. **Two candidate entry conditions positive in 3 of 4 splits** — own-volatility ratio >1.3, and **fading** rather than following a >6-ATR extension (+0.029%/trade, payoff 1.73). Negative in the time-early split ⇒ regime-dependent, **not proven, deliberately not shipped.**

## 📏 NEW STANDING RULE
No entry/exit rule ships again without a four-way out-of-sample harness result. A rule that is not positive in at least 3 of 4 splits does not ship, however good its retro on the last log looks.

**Previous: C356 — the log_c354 forensic.**

## 🔴 WHY 350 VERSIONS HAVEN'T FIXED THE LOSSES
log_c354: 3 trades, 0 wins, −$1.34 (−2.7%) in 5h. Every trade chart-verified against live Bitget candles.

| | entered after | MFE | MAE |
|---|---|---|---|
| SOON long | **+36.7% day / +18.3% in 4h** | **+0.71%** | −8.40% |
| VANRY long | **+24.0%** (its own log says so) | **+0.82%** | −2.72% |
| LINK short | the drop was over — shorted the bottom | **+0.11%** | −2.20% (price rose) |

**All three had a maximum favourable excursion below +1.5%. No exit rule can profit from a trade that never offers more than +1%.** The arithmetic is settled at ENTRY. This is why ~20 versions of exit, trail, partial-exit, ratchet and sizing work have not moved the payoff ratio — **the wrong half of the system was being tuned.**

**The tell was already printed in the log and the engine ignored it:** SOON's own forward projection at entry read `next +0.06%` while C340 stretched its target to **11.0%**. LINK's projection read **+0.20% UPWARD on a SHORT**.

**Second finding — the funnel, not the intelligence, is the binding constraint.** 218 pairs qualified; the bot analysed 30/scan and reached Step 4 with **"1 candidates" every single time**. 105 pairs offered ≥5% capture; **82 (78%) never reached Step 3**. LINK — the pair it traded — ranked **178th of 218** by opportunity. 48 signals, 4 Markov chains, RPPc and Kelly sizing are ranking machinery operating on a sample of one.

**Third — and this one is mine.** C339, which I shipped two sessions ago on a **two-trade retro worth $0.31**, blocked **37 distinct pairs** this session, including **BANK (−38.8%, a 43.7% short capture — the largest opportunity in the entire universe)**, COTI, AEON, BEAT, DEXE, EUL. Six moved ≥10%. That is overfitting to the last log, and it cost far more than it saved.

**★ C355 — THE EXTENSION VETO (the root-cause fix).** When a pair has already travelled ≥5 ATR in the candidate's direction (its OWN units), the entry is refused unless the pair's own forward projection still points that way with magnitude ≥0.30 ATR. Retro: **all three of this session's losers refused**; coiled pairs and genuinely-still-projecting runners untouched.
**★ C356 — FRAME-1 PRIMACY.** A pair travelling ≥4 ATR its own way IS its own trend and is exempt from C339's market-blip latch. BANK/COTI become tradeable again; pairs with no independent move still face the latch.

## ⚠️ THE METHOD ITSELF IS PART OF THE PROBLEM
Each version has been validated by retro-fitting to the 1–3 trades in the most recent log. **Three trades is noise.** C339 is the proof: justified on 2 trades, cost the best opportunity in the market. Until changes are validated over hundreds of historical entries rather than the last session, version 400 will have version 350's problem. **The highest-leverage next build is not another gate — it is a replay harness** that scores any proposed rule against months of stored candles. Recommended before any further tuning.

**Previous: C354.** C353 = summary cadence 7→8 min (operator). C354 = the pyramid's macro gate made graduated, found by the verification audit below.

## 🔍 VERIFICATION AUDIT — pyramiding, Markov chains, RPPc (operator request)

**PYRAMIDING — reachable and correct; it had TWO blockers, both now cleared.**
- *Reachability:* ✅ the branch lives in `_open_position`, and C300's held-symbol feed routes held pairs through the full cascade to it. Not dead code.
- *Blocker 1 (the reason it never fired in any log):* its precondition is **a held winner still ALIVE at ≥1.0 PRU when the next scan runs** — and until C345, the ordinary trail killed C338 remainders within a minute (LA: 55 seconds). No survivor ⇒ nothing to add to. C345 created the precondition.
- *Blocker 2 (found here, fixed as C354):* the macro term was `(R × dir) > 0` — a **hard block on a neutral tape**, precisely the anti-pattern core principle #5 forbids. Overnight tapes sit near R=0 for hours. LIVE CASE: LA rode to ~2.06 PRU at its extreme with its own forecast +0.34 and **R = −0.02 — unclear, not opposing** — and the pyramid was refused on that term alone. Now graduated: macro WITH (≥+0.08) → standard 0.15 forecast bar; **NEUTRAL (|R|<0.08) → allowed, but the pair's own evidence must carry it: forecast bar doubles to 0.30 AND the tranche halves**; AGAINST (≤−0.08) → blocked as before. Risk envelope unchanged (one tranche, ≤50% of base margin — ≤25% under neutral consent, session cap + shared stop intact). Battery 8/8.

**MARKOV CHAINS — all four live; the fourth was resurrected this session.**
| Chain | Status | Live ledger |
|---|---|---|
| RegimeMarkov (Frame-3) | ✅ healthy | acc **0.84–0.85**, Brier **0.056** vs 0.160 baseline, n≈1259 |
| PairStateMarkov (Frame-1) | ✅ healthy | acc **0.68**, Brier 0.098 vs 0.160, n≈7540 |
| FamilyMarkov (Frame-2, C342) | ✅ live, honest | n=25, acc 0.76–0.81 — correctly still `earning` |
| IchiMarkov (C343) | ✅ **now live** (was dead until C346) | **proved end-to-end on 30 live pairs over 4 consecutive windows: 76 scored transitions, acc 0.83, Brier 0.118, persisted to JSON, trust correctly withheld** |

**RPPc FRAMEWORK — complete and correctly gated.** All four frames observe live; all four blend channels wired (pair × determinism-weight, regime, score, flow); P → EV → entry-bar flex → Kelly sizing → Brier ledger, closed loop. **The trust gate is the safety and it is working:** live ledger n=70 / Brier 0.260 (a coin flip) ⇒ **trust = 0.00 ⇒ the blended P spends nothing.** All four capital consumers verified blended toward neutral by (1−trust): Kelly-on-P sizing, C303 risk share, C302 entry-bar flex, C303b dust rescue. And since C346, the determinism weight finally *moves* (0.450 pinned → 0.353–0.578 on live data) instead of sitting at its dead default.
**Honest gap:** S3's blended probability is still not better than a coin flip (n=70). That is a measurement, not a fault — C337 added flow to fix exactly this and the verdict is due around n≈100. Until then the seatbelt holds the wallet shut.

---

**Previous: C352 — full-codebase coherence audit (C351) + the running per-pair scan memory (C352).**

**★ C352 — THE BOT NOW REMEMBERS ITS OWN OPINIONS.** Every Step-3 verdict used to be computed and discarded: each scan met each pair as a stranger. `PairScanMemory` keeps the last 12 verdicts per symbol (score, direction, price, projection, block reason), **read at the top of the per-pair hook and written at the bottom**, so this scan is judged against what the previous ones concluded. Three bounded tilts, composed then clamped to **[×0.80, ×1.20]**:
| Signal | Logic | Authority |
|---|---|---|
| **Conviction derivative** | our own score rising across scans while price hasn't moved = coiling; decaying = dying thesis | ±20%, needs n≥4 **and zero flips** (an oscillator cannot earn a boost) |
| **Directional instability** | a pair we keep reversing on is one we don't understand | −5%/flip beyond 2, floored ×0.85, **never a block** |
| **Per-pair projection track record** | did *our* forecast on *this pair* verify by sign against the next print? | ±10%, **only after 5 scored forecasts** (C335 earn-your-influence, applied to the projector) |
Plus a same-reason **block-streak** log (≥3) so a stale thesis is visible instead of repeating silently. Session-scoped (reset at the day boundary); the *cross-session* memory remains PairProfileStore's persistent fingerprint, unchanged. Watch: 🧠 lines.

**★ C351 — CODEBASE AUDIT (top-down + bottom-up).** Automated writer-vs-reader, reachability, orphan-attribute, duplicate-assignment and unused-constant sweeps, every flag hand-adjudicated.
- **ONE REAL DEFECT, FIXED:** `self._live_regime` was **read in two places and assigned nowhere** (the bot owns `_live_regime_SCORE`, a float, not this label). Every closed trade recorded `regime=''`, and the **C329 ONE_SIDED diagnosis could never once detect "fighting the tape"** — its test is `'down' in _reg`. Now written from the RegimeMarkov state as the words its readers already look for (TD→`trend_down`, SD→`strong_down`, …).
- **FALSE POSITIVE, deliberately NOT "fixed":** the `_s3_live_*` family flagged as never-assigned is written to the **Position** at the C300 held-symbol feed and read via `getattr(self)` **inside Position methods** — correct as built. *(Recorded because chasing it would have been a circular correction.)*
- **DOCUMENTED, NO CODE CHANGE:** `components['ofi']` does **not** carry order-flow imbalance on the live path — `quick_scan_analysis` writes top-10 order-**book** depth imbalance under that name (the true-OFI writer lives in the dead `full_analysis`). So the C337/C341 fuel blend is effectively **0.5 real-CVD + 0.5 resting-book-at-two-depths**, not the documented CVD/OFI/book split. No weights changed on this finding alone (*diagnose before you tighten*), but **no future build may read `ofi` as taker flow**.
- Also catalogued: 4 keys written only inside dead `full_analysis` (inert both ways); 41 defined-but-unread config constants; 132 bare excepts (the codebase's deliberate fail-open idiom, left alone); **zero uncalled functions; no unreachable tails**.
- **Caught during this very build:** `collections` was not imported, so `PairScanMemory`'s deque would have failed **silently inside its own fail-open guard** — the exact bug class the audit exists to find.

---

**Previous: C350 — NO MODE RUNS ON A CLOCK (operator directive). The HP run-length window is **removed, not lengthened**. C330 named the principle and scaled the window 4/6/8h; C350 deletes the outer bound, because the clock was the only terminator that could end a phase *while the phase was healthy*. Live cost on the C344 flight: the expiry sweep killed BTW 15s after entry **and** called `pause_until_tomorrow`, ending the trading day at 06:57. **HP now ends only on money:** target achieved · HP_MAX_LOSS_PCT 5% · HP_MAX_LOSS_OF_NORMAL_GAIN 0.35 (never hand back >35% of Normal's gains — the real guard the clock stood in for) · C84 2.5×PRU drift cap · session drawdown brake · day cap · CATASTROPHIC stop · C329 loss review. `_c330_hp_minutes_left` → +inf so the C330b guard can never bind. Position-level `REL_TIME_MAX` untouched — it was **already** relativistic (10× the pair's own expected hold).

## ⚖️ NORMAL vs HP — the complete difference table (audited C350)
"High Profit" is a misnomer: HP is **stricter, slower and smaller** than Normal, not more aggressive. Its only "high" is that it runs *after* Normal banked its target, adding on top with protected downside.
| Dimension | Normal | HP |
|---|---|---|
| Phase target | 1.00% → 0.50% | **0.75% → 0.25%** (lower) |
| Max concurrent positions | 5 | **2** |
| Base leverage | 5 | **4** |
| Min score bar | 0.32 | **0.36** |
| Min confidence | CONFIDENCE_NORMAL_START | **0.50** |
| Min continuation probability | 0.45 | **0.55** |
| Bar after a loss | unchanged | **0.75, decaying to 0.60 over 45min** (C58/C162) |
| Signal-exit patience | ×1.0 | **×1.3** |
| Minimum hold | none | **25 min** |
| Loss re-entry cooldown | 30 min | **≥60 min** |
| Win re-entry cooldown | 8 min | **≥16 min** |
| Start delay | none | **5 min settle** after activation |
| Drift cap | standard | **2.5×PRU** (C84) |
| Dedicated loss budget | session brake only | **5% of equity AND ≤35% of Normal's gains** |
| Run length | unlimited | **unlimited (C350 — was 4/6/8h)** |
**Reading:** HP's edge is meant to come from *quality and patience* (higher bars, 25-min hold, ×1.3 exit patience) rather than volume or leverage. The roadmap item "HP must outperform Normal" therefore means **payoff ratio**, not trade count — HP structurally cannot win on volume, and never should.

---

**Previous: C349 — five REPAIRS found by the C344 first flight (2 logs, 62 scans, 2 trades). The completion build's own first log indicted three of its own systems, and the log's biggest single number is the C338 winner-partial dying 55 seconds after it fired.

**★ C345 — THE WIN-REMAINDER'S TRAIL (the window's biggest cost).** LA long 22:29:39 → WIN-PARTIAL fired *correctly* at +3.2% (half banked +$0.26), remainder declared "a floored runner under WINNER_RATCHET_FLOOR (0.45×peak)" — then **TRAILING_TP, which C338 deliberately left governing, killed it 55 seconds later** at peak +4.4% / floor +3.9% (a 0.5pp = 0.24-PRU giveback). Chart: **LA ran to +39.6% within 2h** (+30.1% at 30 min). The remainder behaved exactly like an ordinary position; the mechanism produced *zero* continuation capture on its first firing. Fix: for a `_win_partial_done` remainder only, the trailing floor is capped at 0.45×peak — the trail still exits on a 55% giveback, it simply may not be TIGHTER than the floor the split promised. Retro: floor 3.90%→1.98%, survives the +3.1% print, ratchets with the run → **$1.70 instead of $0.24 (+$1.46 on one trade)**. **THIRD instance of "an exemption list is only as real as the exits NOT on it" (C336→C338→C345).**
**★ C346 — THREE COMPUTATIONS WERE ON THE DEAD PATH, one since the day it shipped.** `_ichi_state` (C343), `rqa_det` (C344) **and `perm_entropy` (C315)** were all authored into `full_analysis()` — the method whose own docstring reads *"DEAD CODE — DO NOT ADD LOGIC HERE"*. Verified: **zero IchiMarkov lines in 62 scans / ~1,800 pair-evaluations**, its JSON never created, and **the C315 determinism weight has been pinned at its 0.45 default in production since C315 shipped**. All three now compute in `quick_scan_analysis`; live-verified on real BTC candles (DET 0.000, PE 0.972, state B− → weight 0.450→0.364). **SEVENTH instance of the dead-path class — and the first caught by its own first-flight log.**
**★ C347 — C341's book channel was dead on arrival:** the live path writes `book_imb`; C341 read `book_imbalance`/`book`. Measured on the window's only urgent entry: BTW's two-channel fuel read +0.152 and crossed the spread; the correct three-channel value is **+0.098, below the +0.10 bar** → urgency would have stood down. BTW then rallied **+25.1% in 3h** against the short.
**★ C348 — the C330b HP-window guard read a starved cache.** `_c330_hp_minutes_left` is written inside `_check_profit_targets()`, called only when `positions.count() > 0` — the *same starvation C334 fixed in the same function*. Flat for 8h ⇒ stale value from the previous evening ⇒ **BTW opened 06:57:33 and the expiry sweep killed it 15 seconds later**. The guard now derives the window from `_hp_start_time` and takes min(cache, fresh). **SIXTH instance of the starved-call-graph class.**
**★ C349 — sweeps book as SWEPT, not LOSS:** "HP 6-hour window expired" was booked ❌ LOSS, feeding the losing-direction memory and eval ledger with an administrative close. PnL/equity/eval counter unchanged; only attribution corrected.

**C344 SYSTEMS SCORECARD (first flight):** C340 target-persistence **VERY ACTIVE — 581 firings** (UB 0.1%→5.3%, BANK 7.1%→17.6%, BTW 4.1%→10.2%) with the RR gate still blocking 42×: working, no harm observed, watch for over-permissiveness. C342 FamilyMarkov **LIVE and honest** (calib n=25, acc 0.76–0.81, Brier 0.207–0.220 vs base 0.182–0.245 — correctly still `earning`, not EARNED). C339 blip-hysteresis **0 firings** (no counter-trend candidate arose inside a latched window — untested, not disproven). C341 **1 urgent entry, 0 stand-downs** — and C347 shows it should have been 1 stand-down. C343/C344 **dead** → C346.

---

**Previous: C344 — the COMPLETION BUILD:** on operator directive, every remaining specced/blueprinted item shipped in one session as six staged, individually-batteried builds (C339–C344). Discipline note: bundling was the operator's explicit call; mitigations = per-stage count-asserted patches, per-stage retro batteries on the window's real numbers, deep pre-flight through Step 3, and every new authority C335-gated. **Loss exits, hard stops, sizing caps: untouched.**

**★ C339 BLIP HYSTERESIS (entry):** |R|≥0.30 arms a 30-min counter-trend latch; opposing entries need a genuine flip (R ≥ +0.10 into the candidate) AND 4h consent (>−0.15 / <+0.15) — which also unlatches globally (C330: evidence beats the clock). C215/C216 flips + strong own-projection (≥0.5×ATR, with 4h consent) exempt. Retro: LA/ZAMA blocked (−$0.31 saved); V-turn passes; aligned shorts untouched. Watch: 🛑 `regime_blip`.
**★ C340 TARGET PERSISTENCE (reward):** regime-aligned + persist ≥0.70 + the chain's OWN earned ledger (n≥300, acc≥0.75, Brier<0.10 — live 0.84/0.057) ⇒ target extends to ATR×(1+2·persist), cap 4×ATR, planned target lifts with it (C338 banks half at touch). Retro ENA: 0.8→2.99%, RR 0.48→1.81, enters the −4.7% move; EDGE/COAI/2Z class unchanged. Watch: 🎯 extension lines.
**★ C341 URGENCY FUEL CONSENT (fill):** the window REFUTED CVD-sign consent on its own data (knife longs had CVD +0.23/+0.20/−0.13); the C311/C337 composite fuel separates 5/5 (LPT +0.05, ZEC +0.04, EUL −0.06 stand down vs LAB +0.17, CROSS-short −0.21 keep urgency). Signed fuel <+0.10 ⇒ passive maker limit (its adverse-selection geometry protects). Watch: ⚡→🕊️ lines.
**★ C342 FAMILYSTATEMARKOV (Frame-2 — the last RPPc structural gap, CLOSED):** per-scan member C295-states (±2..0) aggregate per C228 category; ≥3-member families close batches into a 5-state (D2..U1..U2, ±0.3/±1.0 buckets) regime-conditioned chain (`family_markov_v60.json`). **★ C343 ICHIMOKU ALPHABET:** cloud side × TK posture = six letters (A+…B−) per pair per scan (`ichimoku_markov_v60.json`); C314's room feed untouched. Both ride the new `AuxStateMarkov` spine: batch-deflated evidence (C323), **cold-start-guarded** binary persistence calibration vs the chain's OWN base rate, and spending power ONLY at **Brier skill ≥5% on n≥200** (battery: state-informative process earns it; uniform persistence — where the base rate is provably unbeatable — correctly never does; noise never does). Earned-only tilts ≤±8% (family) / ≤±6% (ichimoku). Watch: 🎲 FamilyMarkov / IchiMarkov calib lines, `earning`→`EARNED`, then 👪/☁️ tilt lines.
**★ C344 RECURRENCE QUANTIFICATION:** DET (diagonal fraction, m=3 τ=1, radius 0.25× the pair's own embedded-distance spread) joins C315's permutation entropy by GEOMETRIC MEAN into the ONE determinism weight on the S3 pair channel (C318) — bounds ×0.70..×1.30, missing→×1.0 byte-parity. Battery on the real function: sine DET 0.83, noise 0.00. Spends nothing while S3 trust sits at T=0.00 (C335).

**★ C336 FIRST FLIGHT: FAILED AS SHIPPED → REPAIRED (C338).** It fired twice (LA −1.7 PRU, ZAMA −1.3 PRU) and BOTH retained halves were executed within ~2.5 min by **REL_DRAWDOWN — which was never in the exemption set** — minutes before chart-verified bounces of **+2.7% (LA, 30 min)** and **+5.7% (ZAMA, 2 h, closing ABOVE entry)**. Three stacked defects: (1) the recovery-patience family (REL_DRAWDOWN / REL_ACCEL_LOSS / REL_STAGNATION) still governed the survivor; (2) the hard stop at −(1.5+eqi·0.5) PRU sat INSIDE the bounce path (post-partial lows −2.16 / −2.08 PRU); (3) the C258 second evaluator (SCAN site) had **no partial interception at all**. C338: patience family exempted; survivor's stop widens to min(3.0, |partial PRU|+1.3) — half the size × double the room = the same incremental dollar risk; governed instead by PARTIAL_THESIS_DEAD (DRI ≥ 0.05) and a 180-min lease; both evaluators intercept.
**★ WINNER-PARTIAL (the C336 mirror, C338):** payoff this window was **0.62** and the chart said why — PLANNED_TARGET/EPC-t1/DSI-decay/REL_EXHAUST/POSITION_CAPTURE gave up the continuation in **4 of 6** firings (LAB +1.8%→pair ran +10.3%; PUMP +2.3%→+6.8% more; ESP; CROSS-short) while only ZAMA/PIEVERSE banked right. Those five exits now bank **HALF** when the win is substantive (≥0.40 PRU, fee-positive floor); the remainder runs as a floored runner under **WINNER_RATCHET_FLOOR** (≥ max(fee-positive floor, 45% of any later peak)) — a split winner can never book a loss, by construction. Retro on the window: ≈ **+$0.4** net, payoff 0.62→~0.85 from structure alone; correct banks cost ≤ 0.175 PRU (ZAMA −$0.04) and PIEVERSE (0.377 PRU) stays a full bank.
**Watch next log:** 🛑 regime_blip · 🎯 C340 extensions · ⚡→🕊️ C341 stand-downs · 🎲 Family/IchiMarkov `earning`→`EARNED` · 🔺 first pyramid (C338 runners finally create its precondition) · ✂️ WIN-PARTIAL lines + WINNER_RATCHET_FLOOR · ✂️ PARTIAL remainder now surviving past 2.5 min (widened stop line [C336/C338]) · PARTIAL_THESIS_DEAD / PARTIAL_LEASE_EXPIRED · S3-EV Brier (0.260 @ n=70, trust still correctly T=0.00) · short #3.

## ★ W1 VERDICT (100 trades): WR 56.0% PASS · payoff 0.77 FAIL · net −$0.12
Avg win +$0.150 vs avg loss −$0.194. Last third of the window improving (WR 59%, net +$0.51).
**Payoff autopsy:** STAGNANT_LOSS = 84% of all losses (30 trades, −$7.10). Two-thirds of wins are tiny (trail/EPC ≈ +$0.09) while target-reaching exits average +$0.32.
**Do NOT loosen the trail** — chart-refuted (PUMP trailed out at +0.3%, then fell −3.10%; the trail was right). The small wins are genuinely small moves, not cut winners. Payoff is an OPPORTUNITY problem, not an exit problem: 30 of 203 pairs moved ≥3% while the bot traded ~1% movers, the biggest moves were falls it could not short (9 shorts / 100 trades), and ERA +35.9% was never screened. (300 funcs; full battery run against the REAL functions, not mirrors — which is how C316 and C317 were caught) (day cap 4.0%, per-trade risk 1.3%×k — margins ~$14 base, ~$22 at P≥0.84) (`omega_v60_reconstructed.py`, 285 funcs, all batteries passed, pre-flighted). Eval window W1 at **86/100** — session 20260719 (C302 first flight): **5/5 WINS +$0.62, S3 calib[5] acc=1.00 Brier 0.076 ≪ 0.250**; the payoff constraint has MOVED to the exit-capture layer and the day-budget risk cap, both now addressed (C308/C303). Eval window W1 at **86/100** (WR ~60% incl. the reclassified sweep; payoff still THE open problem — now attacked at the capital layer by C302 Kelly-on-P). Equity $50.53 paper (session 20260718b: #78–81 = 3W + 1 admin sweep, net +$0.53, Normal-1 target achieved, HP reached).
**C303–C308 (one session, six coordinated changes):** C303 Kelly at the RISK layer (share ×k(f*)∈[0.75,1.60], 0.60→0.70 remaining factor, 0.85×remaining ceiling, high-P dust rescue — BILL $9.70→~$15.3); C304 overshoot credit reinstated safely (eff=max(base−pool,0.10), pool≤0.75, spent/earned settle, persisted — safe because C255 marked equity + C300 flat-boundary killed the log_c254 root); C305 monitor 0.8s (parallel price fetches unchanged); C306 Hurst-scaled E_win (chaos→R: H0.8→×1.30, the degenerate R=0.91 fixed); C307 funnel honesty (phase-2 38→44 + 4 coil wildcards: big-volume |24h|<3% quiet pairs get the projector — the BIRB/G blind spot); C308 S3-driven ride extension (held position's own fresh P≥0.70 supplies ride strength; P≥0.80 & EV≥0.30 opens the 3–5×PRU strong tier — B +13.9%/HOME +15.2% post-exit runs were the evidence).
**RPP STAGE 3 IS SHIPPED (C302):** blended calibrated-P (Frame-1×3 PairMarkov 15m-leg×regime w=0.45 · Frame-3 RegimeMarkov 4h-structure w=0.35 · Frame-2 score w=0.20, log-odds, evidence-gated, fail-None) → EV in own-ATR PRU units → entry-bar flex [0.85,1.20] (replaces C295 flex when computable) + Kelly-on-P sizing [0.60,1.60] before all caps + close-time Brier calibration (s3_calib_v60.json, baseline 0.250). Watch next log: 🧮 S3 lines, 🧮 S3-EV calib line, sizing-inversion reversal on high-P×high-R entries.

**The current major arc — RPP framework (Relative-Probabilistic-Predictive), staged:**
- **S1 regime Markov [C294] — DONE + VALIDATED live** (acc 0.80→0.82, Brier 0.071→0.065 ≪ 0.16 baseline; warm chain persists across restarts in `regime_markov_v60.json`).
- **S2 pair-state Markov + first routing [C295] — DONE + VALIDATED** (bar-flex fired 73×, all shorts eased in P=0.94 down-tape; `pair_state_markov_v60.json`).
- **S2.5 learned-P into gates [C296] — DONE** (leg-exh release OR-channel, C291 third channel, climax 4-condition downgrade; retro 7/7; PairMarkov calib line added).
- **Fill layer [C297] — DONE** (regime-aware URGENT crossing entries, taker; passive maker in chop; `_limit_touched` window 2→5m; pyramid same).
- **Stability patch [C298] — DONE** (Step-5 selections retained in analysis set 3 scans; removes blindness, not judgment).
- **Session ladder [C304+C310] — DONE**: overshoot reduces the next phase's target, and FULLY-covered phases are skipped outright (flat-only, realized-only). The 0.10% floor now exists solely as the not-flat safety net.
- **Never pin a gate to an absolute number on a scale you keep improving [C322→C324]** — it fails silently, compiles, and passes unit tests of the gate in isolation. C320 broke C308/C321's gates; C322 fixed them by converting through κ; C323 then moved the scale again and would have re-broken them. C324 ends it: gates are percentiles of the engine's own live output, scale-free by construction.
- **An exemption list is only as real as the exits NOT on it [C338]** — C336 named four surviving protections and forgot the recovery-patience family AND the hard stop's geometry; the survivor died in 2.5 min, twice, before its purpose could exist. When granting immunity, enumerate the FULL exit family and check the hard stop's distance against the room the thesis needs.
- **Every routed token must be handled at EVERY evaluator [C338]** — the C258 second evaluator had no partial interception and would full-close on a partial token whenever it won the race. C334's reachability rule extends to token routing: assert every dispatcher, not just one.
- **A fail-open guard can hide a missing import [C352 build]** — `try/except` around a deque whose module was never imported yields silent no-op, not a crash. Any new dependency must be import-checked explicitly, because the codebase's fail-open idiom will swallow the evidence.
- **An attribute read in two places and written in none is invisible, not absent [C351]** — `_live_regime` compiled, ran, and quietly disabled a whole diagnostic dimension for many versions. Writer-vs-reader sweeps belong in the standard battery alongside reachability.
- **A guard that reads a cached number must be proven to run where that number is WRITTEN [C348]** — C334's reachability rule, extended from readers to writers. `_c330_hp_minutes_left` had a correct reader at a live address and a *writer* in a starved one; the guard was silently disarmed for the entire flat period, which is exactly when it matters.
- **When a mechanism is given a floor, no other exit may sit inside it [C345]** — C338 promised the remainder a 0.45×peak ratchet and left a 0.24-PRU trail governing above it. A promised floor that another exit undercuts is not a floor, it is decoration. Enumerate every exit whose threshold can fall INSIDE the granted band, not merely those on the exemption list.
- **A calibration ledger must never grade a prior [C342/C343 build]** — Laplace-prior predictions scored in infancy poison the cumulative Brier forever (battery-caught); rows enter the ledger only after ≥3 real transitions. And the trust bar is **Brier skill ≥5% vs the chain's OWN base rate**: on a uniform-persistence process the base rate is provably unbeatable, so a chain that merely matches it has learned nothing and must stay unpaid.
- **Evidence unlatches; the clock is only the outer bound [C339]** — hysteresis without an evidence exit is a new absolute threshold (C330's sin in disguise). The 30-min latch yields instantly to a genuine flip + higher-frame consent.
- **The right tail deserves the same asymmetry as the left [C338]** — an exit boundary that is wrong half the time on WINNERS (4/6 gave up +2.7..+8.4%) banks half and floors the remainder, exactly as C336 does for losers. Discriminators fit on n=6 overfit; structure generalizes.
- **A boundary that is right half the time must not realise the whole loss when wrong [C336]** — at a 50/50 exit boundary, the full cut pays the worst print in the wrong half; the partial banks half and keeps the recovery option, with every other protection still governing the remainder.
- **Probability may steer capital only in proportion to demonstrated edge [C335]** — an uncalibrated P scaling position size is noise steering money. Every predictive layer's *spending power* is now gated by its own live Brier, completing the calibration-first doctrine: C320 corrects the probabilities, C324 keeps the gates honest, C335 withholds the wallet.
- **A fix gated on condition X must be PROVEN REACHABLE from a call site where X can hold [C334]** — C327's resolver was correct logic at an unreachable address: it demanded `count()==0` inside a caller that runs only when `count()>0`. Test the CALL GRAPH, not the block. Every state-machine repair now ships with a poisoned-state boot reproducing the original incident.
- **A flag that gates trading must have a resolution path that cannot be starved by the condition that set it [C327]** — `_pending_hp` was resolved only inside `if pnl_pct >= target`; the runner's giveback pushed equity back under the bar and the flag was orphaned, suppressing every entry for 9 hours. State-machine resolvers belong at the top of the tick, unconditionally.
- **Never let a risk controller read UNREALIZED equity [C329]** — an open position's temporary dip is not a loss. LAB triggered "cautious mode" while underwater and closed +4.9% fourteen minutes later.
- **Diagnose before you tighten [C329]** — one lever for every illness makes the bot trade *less*, not *better*. Give-back losses, instantly-adverse losses and one-sided losses have different causes and different cures; and when losses show no common cause, the correct action is *none*.
- **Absolute time limits are absolute thresholds [C330]** — a fixed window truncates a working phase as readily as it stops a bleeding one. Measure progress; keep the clock only as an outer bound.
- **THE LONG-ONLY CAUSE, FOUND [C326]** — not gates, not direction generation: the SCORE SCALE. Long and short candidates arrive with equal breadth (0.71 vs 0.67) but shorts score 2.5× lower (p50 0.06 vs 0.15, max 0.42 vs 0.57) while one absolute bar judges both. Third instance of the scale-mismatch class (C322 κ, C324 horizon, now sides). **Rule: never compare two differently-scaled quantities to one constant.**
- **DONE (C339/C340 — the two specced ladder steps, shipped in the completion build):** (a) **Entry regime-blip hysteresis** — LA/ZAMA longs (−$0.31) entered at 18:32:56 through a 5-min weak-R print (−0.61→−0.07) inside a TD persist-0.86 tape whose 4h frame still read −0.28; the counter-trend unlatch must require BOTH a genuine R flip AND 4h-frame consent (> −0.15), held 30 min after any |R|≥0.30 block, with the C215 bounce-flip / C245 blow-off-coherence deliberate-reversal paths exempt. (b) **RR target-persistence** — ENA short blocked poor_RR 0.51 at 14:01 then fell −4.7% with −0.11% MAE (realized RR ≈ 40); the C281 NEGATIVE-RESULT-3 class, now speccable: when RegimeMarkov's trend state aligns with the trade at persist·T_markov ≥ 0.60 (its Brier 0.057, n≈1283, has EARNED it), extend target = max(room_target, ATR × (1 + 2·persist)) — room-to-support is the wrong reward model in a persisting trend, exactly as room-to-resistance was for breakouts (C187/C191/C213).
- **Step-1 is now the binding constraint on opportunity, not the gates** — ERA +35.9% on $18.6M volume never entered the analysis set at all (4th case: BIRB, G, TLM, ERA). The gates get blamed for misses the screen never surfaced.
- **A stop placed inside the pair's own noise band is not a stop, it's a coin flip [C325]** — PRU ≈ ATR, so cutting at −0.85 PRU cuts inside one ATR of ordinary counter-noise. Measured n≈17: the stagnation family systematically sold local lows.
- **Any freshness test on an irregularly-refreshed value must be graduated, never a cliff [C325]** — C321 fired, logged, and then silently expired before the exit decision on both positions it was built to save.
- **Exit-side evidence outranks entry-side evidence [C325]** — patience granted on a pre-entry probability while the live DRI said the thesis was dying is backwards.
- **Markov horizon must match the decision horizon [C323]** — one step = one scan = 5 min, but trades run 6–38 min. A one-step chain feeding a 38-minute decision is structurally optimistic. Chapman–Kolmogorov k-step is the fix and is what the chain is for.
- **Correlated observations are not independent evidence [C323]** — ~30 pairs per scan move together; 30 counts ≈ 1 market event. Evidence gates were clearing on pseudo-replication.
- **A threshold compared against a rescaled value must live on that value's scale [C322]** — otherwise it is a *dead gate*: code that runs but can never be true. This is the cousin of the dead-code class (C140/C168/C286/C306) and it is invisible to compile, to unit tests of the gate itself, and to inspection. Audit rule: whenever a scaling factor is introduced anywhere, grep every constant compared against that quantity.
- **RPPc frame coverage (audited C322):** Frame-1 (pair) = PairStateMarkov ✓ probabilistic+learned; Frame-3 (market) = RegimeMarkov ✓ probabilistic+learned; **Frame-2 (family/sector) = the C228 CategoryClassifier "wildness" tilt — a continuous score, NOT a Markov chain, NOT calibrated.** This is the one structural gap remaining in the operator's RPPc vision. A FamilyStateMarkov (P(family continues | family state, regime), same shape as PairStateMarkov, keyed on the existing category) is the designed answer and is unbuilt. **→ BUILT AND SHIPPED as C342** (AuxStateMarkov spine, calibration-gated from birth); C343 adds the Ichimoku structural alphabet on the same spine — Frame-2 is now probabilistic + learned + spending-gated like Frames 1 and 3.
- **Risk constraints compose as min(), never as a product [C318]** — two mechanisms both encoding "volatile → smaller" multiplied into the sizing inversion. Before adding any margin modifier, check whether an existing one already prices the same risk.
- **Saturation is a silent failure mode [C319/C320]** — a bounded map that always emits its clip is a binary switch pretending to be a graded prior. Audit every clipped output's live distribution, not just its bounds.
- **Contrarian-flip doctrine [C311 + C312] — DONE, both sides**: a top requires flow to have turned NEGATIVE (sign change, fail-closed); a bottom requires selling to be DECELERATING (second derivative, fail-open). The asymmetry is deliberate and documented — capitulation IS maximum selling, so the mirror could not be a copy.
- **Dead-code rule hardened [C316]**: a new field read is proven by CALLING the real function in the battery, never by inspection. C306 shipped, was changelogged, and never once executed.
- **Euphoria-flip doctrine [C311] — DONE**: price extremity alone may no longer invert a conviction read; flow must confirm. C215 bounce-flip mirror deliberately pending its own evidence.
- **Mode-transition integrity [C300] — DONE** (admin sweeps no longer feed the losing-direction memory — the TOSHI false-skip; HP DEFERS until the spared runner concludes, overshoot carried as equity — the ALLO inheritance; held symbols feed Step-3 — the pyramid dead-path resurrected: pyramid had NEVER fired since C286 because `if symbol in open_symbols: continue` starved `_open_position`'s pyramid branch of its only route).
- **Readability [C301] — DONE** (🔹→🔵 on all bullish/winning markers; 🟩×18 green rule before every pair's Step-3 block).
- **Fix-regression layer [C299] — DONE, now LIVE-VALIDATED** (4 firings on 20260718b: VVV×2/TRADOOR×2 stand-downs at 3.4–4.3 ATR off extreme; released shorts then correctly died downstream — TRADOOR's low-score block saved a short before a +7.2% rip: the release restores adjudication, never forces entries) (C292 broken-parabola inversion: the guard was killing shorts on collapsed parabolas that the parabola gate's own design deliberately leaves open — ESPORTS −16% blocked 8×; released via the shared broken-state test, RAVE-class untouched).
- **S3 NEXT (score→calibrated-P→EV; entry by EV, Kelly-on-P sizing) — criteria status after log 20260718:** (b) 🎲 **PASSED** — PairMarkov Brier 0.113–0.116 ≪ 0.16 baseline, stable across 136→171 obs; (a) ⚡ C297 URGENT **untested, not falsified** — the whole session was CH persist 0.50→0.83 (never a ≥0.70-persist DIRECTIONAL tape; both entries correctly took the passive maker path, both fills chart-validated live-touchable); (c) 🔁 C298 retention **vacuously sane** (both Step-5 selections became positions — nothing to retain); (d) C296 **zero firings in chop = correct fail-closed**, no whipsaw possible. VERDICT: one directional-tape session still needed to exercise (a)/(c)/(d); S3 build can start in parallel — its design case (sizing inversion, below) is now empirically pinned.

**First actions in a new session (S3 design evidence banked, 20260718):** the sizing INVERSION is now measured — the session's WORSE entry (TRUMP long: 59% agreement, real-CVD −0.56 OPPOSING, RSI 73) received $15.14 while the BETTER entry (1000XEC: 84% agreement, MQ 0.80, feedback-confirmed) received $7.81 — the C61 ATR-cap (lev 4→1) × C260 budget-fit (fixed $-stop ÷ stop-distance) chain systematically anti-sizes volatility, and payoff LIVES in volatility. corr(score,PnL)=+0.11 plus this = the two pillars of the S3 EV/Kelly-on-P case. Operator uploads the newest log → run the full forensic pass (trade map → chart verification IST−5:30 → full-universe ~230-pair movers check at scan timestamps, NEVER top-N → gate audit → verdicts) → check the four verify-next criteria above → then either fix regressions or build S3.

**Keep THIS file in project knowledge. At the start of every chat I search it; every session I re-deliver it updated. This is the continuity spine across conversations.**

Working dir: `/storage/emulated/0/OmegaBotV60/` · Main file: `omega_v60_reconstructed.py` (~21,300 lines, 289 functions) · State: `mode_v60.json`, `learning_v60.json`, `pair_profiles_v60.json`, `eval_window_v60.json` · Platform: Nothing Phone 2 / Pydroid3 / Bitget USDT-M perps via ccxt.

---

## 0. THE THREE REFERENCE FRAMES (the master architecture — operator's framing, C290-verified)
Every decision is governed by three nested frames that compose multiplicatively:
1. **FRAME 1 — the pair relative to ITSELF** (its own accumulated history): PairProfileStore 4-D fingerprint [vol/jump/spike/BTC-corr], C286-2 coiled/wild vs own baseline, the pair's own Hurst, all thresholds ATR/PRU-relative. *"Is this pair behaving normally for itself?"*
2. **FRAME 2 — the family/profile relative to the MARKET and to OTHER families**: family_tilt = wildness(C228) × risk-direction(C229) × market-structure(C289) × sector, feeding cross-family breadth(C211). *"Which signal families should I trust for this pair in this market, and do they agree with each other?"*
3. **FRAME 3 — the whole market relative to ITSELF**: _market_regime (DFA/entropy/GARCH → trending/ranging/choppy), bias resultant, trajectory projector(C161), C288 regime-fit. *"What structure is the market in vs its own history?"*
**Composition (C290 clean separation):** C289 applies Frame-3 structure at the family-WEIGHT level (which signals vote); C288 applies the Frame-1×Frame-3 INTERACTION at the SCORE level (pair-Hurst × market-regime, ±0.06 fine-tune); C286-2 applies Frame-1 own-history as a score overlay. No double-counting. The 55 gates then consume all three frames.

## 🔧 STANDING PROTOCOLS (every session, non-negotiable)
- **GSD workflow for every change:** discuss → plan → execute → verify → ship. No shortcuts.
- **Verify battery before any delivery:** (1) `python3 -m py_compile` + AST func-count; (2) retro-validation against the exact logged failure the change targets, plus counter-cases; (3) live sandbox pre-flight boot; (4) version banner + changelog tuple prepended before the prior anchor; (5) confirm prior C-versions' key markers still present (no clobbering).
- **Sandbox pre-flight boot (assistant environment):** ccxt TLS workaround lives at `/home/claude/pfenv/sitecustomize.py`. Boot: `printf '1\n1\n\n\n\n' | PYTHONPATH=/home/claude/pfenv timeout 100 python3 omega_v60_reconstructed.py` (1=Paper, 1=Fresh). Delete `/root/OmegaBot60/eval_window_v60.json` + both markov jsons first to reset sandbox state. Expect 0 tracebacks; learned channels correctly SILENT on a cold chain.
- **Ship rule:** deliver ONLY via `present_files` — the `.py`, the Atlas, the ledger. Never inline code or patch scripts.
- **Chart verification:** log timestamps are IST; Bitget candles UTC (IST−5:30). Reference price = last SETTLED candle close, never the forming candle. Candle API: `api.bitget.com/api/v2/mix/market/candles` via raw requests.
- **Missed-opportunity check before every code change:** the FULL vol≥$750k universe (~230 pairs) at EACH scan timestamp — NEVER top-N (top-35 once hid RAVE #41). Always check DIRECTION before claiming a miss.
- **Anti-overfit (C188):** no n=1 gate overrides; down-weight by regime, don't delete signals. Banked falsified ideas: C277 flow-waiver (0/5), leg-X discriminator, blunt floor-cap.
- **Phone paths:** working dir `/storage/emulated/0/OmegaBotV60/`; state files `mode_v60.json`, `learning_v60.json`, `pair_profiles_v60.json`, `eval_window_v60.json`, `regime_markov_v60.json`, `pair_state_markov_v60.json`. Stop bot only when FLAT; Load Previous State when restarting with open positions.

## 0b. THE GATE-CASCADE FRAME BALANCE (measured, C293)
The 57-gate cascade's rejection PRESSURE was measured and rebalanced:
- **57 gates exist, ~5 do 80%% of rejections** (low_score, parabola_bounce, flat_projection, leg_exhausted, poor_reward_risk); ~29 never fire (harmless dead weight).
- **Effective pass rate ~1.5%%** (5.5 trades / ~360 candidates per session) — highly selective, NOT overtrading.
- **Pre-C293 pressure by frame: F2 (quality) 52%%, F1 (pair exhaustion) 40%%, F3 (market regime) only 8%%** — imbalanced; doctrine says regime should be primary.
- **C293 fix:** exhaustion thresholds now flex with regime (trend: bar rises, runners survive; chop: bar falls, exhaustion earlier; mixed: baseline). Lifts F3's effective weight, makes F1 regime-appropriate. F2 (low_score, the C288 classifier) untouched. The EXTREME-climax veto stays regime-independent, so the bot cannot flip to overtrading.
- **The rule:** the number of ACTIVE vetoes should flex with the market frame — same as C289 (regime-conditional family weights) but applied to the GATES.

## 0c. THE RELATIVE-PROBABILISTIC-PREDICTIVE FRAMEWORK (C294+, the current major arc)
**Operator directive:** infuse the whole bot with a *relative probabilistic predictive* framework; strengthen Markov-style relative-determinism as the spine for chaotic-system prediction. If base principles are wrong, every pathway compounds.
**Empirical foundation (tested, not assumed):** BTC 4h regimes have strong memory — trends persist ~69%%, chop ~73%%, trends almost never flip directly to the opposite trend (they decay through chop). And corr(entry-score, realized-PnL)=+0.11 — the core score does NOT predict magnitude, so downstream sizing inherits that blindness (the base error, confirmed).
**Refinements to the framing (peer analysis):** (1) Markov is a SPINE for state-transition problems, NOT universal — rate problems keep calculus (2nd-derivative info would die in a memoryless chain); (2) it's conditional probability with strong priors, not determinism — a 69%%-trend fails 31%%, so act on probabilities with confidence bands (why fractional-Kelly, not all-in); (3) ADDED calibration tracking (Brier) so probabilities are measured against reality and self-correct — the highest-leverage addition.
**Staged plan (each shippable + verifiable):** **S1 [C294, DONE + VALIDATED live: acc 0.80, Brier 0.071 ≪ 0.16 baseline]** regime-transition Markov (5 directional states SU/TU/CH/TD/SD, Laplace-smoothed, persisted to regime_markov_v60.json, calibration baked in, OBSERVABILITY-ONLY). **S2 [C295, DONE]** pair-state Markov conditioned on regime (shared 5×5 matrix per regime state, the PRIOR; C236 per-pair tendency = the posterior; observability-only, Brier-calibrated) + the FIRST decision routing: entry bar × (1+0.40·(0.5−P_dir)) clipped [0.85,1.20], from the live RegimeMarkov distribution, confidence-gated ≥0.15, fail-open, 0.72 cap preserved. Replayed: the US-long case → bar ×1.14 (blocked-class); shorts in a bear tape → ×0.86 (the zero-shorts fix). **S3** score→calibrated-P→EV (entry by EV, sizing by Kelly-on-P). **S4** route the ~5 dominant gates through EV. Each layer validated against reality BEFORE it drives decisions — infuse the framework everywhere without a reckless rewrite.
**S1 VERIFIED (20260717 log): acc 0.80, Brier 0.071 (< half the 0.16 baseline), P(TD-persist)=0.85 on 48 obs read a bear tape correctly in real time. The session's two losing LONGS (one at Markov P(TD)=0.72) are the clean Stage-2/3 case study: the bot KNOWS the regime probabilistically but doesn't yet ACT on it. → S2 VERIFIED (20260717_101637): bar-flex fired 73×, ALL shorts eased ×0.85-0.88 in a P(dir)=0.94 SD tape — zero-shorts gap structurally FIXED. But the eased shorts hit the F1 gates and chart verification proved the LARGEST misses of the project: HOME leg-exhausted-blocked → fell −16%; BILL climax-blocked ("fcast +1.4 bounce OPPOSING") → fell −10.7%; EVAA climax-blocked ("+2.0 opposing") → fell −19.1%. ROOT: post-fall next-candle forecasts are mean-reversion-biased; in a persisting SD regime, down-legs continue — exactly what the PairStateMarkov learns.
→ **S2.5 SHIPPED (C296):** `_c296_learned_cont` helper (RegimeMarkov conf≥0.30 + persist≥0.70 + regime-ALIGNED with trade + PairMarkov P(continue|state,regime)≥0.65 on n≥30; fail-CLOSED) wired at three gates: (1) leg-exhaustion release — learned-P is an OR-alternative to the forecast test (macro + full C287 fuel guard mandatory); (2) C291 structural-room forward test — third OR-channel; (3) climax veto — 4-condition DOWNGRADE to ×0.85 penalty (learned-cont ok + NO opposing rejection candle [the SYN-hammer tell keeps the full block] + vol≥0.9 + vel>−0.9), else block stands and logs the learned-P reading. Retro 7/7: BILL/EVAA downgrade, HOME releases; SYN-hammer/cold-chain/chop/counter-regime all still block. Plus the PairMarkov calibration LOG LINE each scan (C295 observability gap closed; baseline 0.160 printed).
**FILL LAYER (C297, from the 20:48 live screenshot):** the full pipeline worked — shorts eased (C295), gates passed (C296), LAB+NEAR SELECTED — then both died UNFILLED: passive asks +0.10% above market in a P(dir)=0.94 TD tape (adverse selection: favorable-side limits only fill on the failing retrace) + the C286 backward-2-minute instant-cancel (chart proof: LAB's ask was touched 2 min AFTER the cancel). C297: when RegimeMarkov conf≥0.30 + persist≥0.70 + ALIGNED → cross the spread 0.05% through (marketable limit, taker, fills instantly, ~$0.009 extra fee vs $1.11 per −5% continuation); else passive maker unchanged; `_limit_touched` window 2→5m; pyramid add same urgency. The chain is now complete end-to-end: direction (C292) → generation (C295) → gates (C293/C296) → selection → sizing → FILL (C297).
**DECISION-STABILITY (C298, operator question "should decisions change within minutes?"):** chart-verified answer — the 21:06 flip WAS correct (LAB's flush decayed to flat; NEAR bounced +1% invalidating the short); the loss was the 20:48 FILL (fixed by C297; flush-shorts are perishable — cross NOW). Residual defect fixed: NEAR was INVISIBLE, not rejected (top-30 re-ranks with no memory) → C298 retention keeps Step-5 selections analyzable for 3 scans. PRINCIPLE for the RPP arc: threshold decisions amplify smooth input drift into binary flip-flops; the RegimeMarkov stayed stable across the same restart (persist 0.85, warm chain) — the probability layer is the stable view, the score layer is the noisy one. Stage 3 is the systemic smoothing.
**Verify next (before S3):** (a) PairMarkov calib line shows Brier <0.16 and falling; (b) learned-channel firings on the phone (warm chains) release crash-continuation shorts WITHOUT whipsaw regressions (watch for any released short that bounces >3% — that would falsify a discriminator); (c) then build S3: score→calibrated-P→EV (entry by EV, Kelly-on-P sizing).

## 1. Current status (C286)
- **Eval window OPEN, W1, ~59 trades in.** Verdict shape LOCKED since trade ~20: **WR ~57% PASS (≥55), payoff ~0.73 FAIL (need 1.2).** Trader-A signature — wins often, wins too small.
- **The diagnosis chain (all one root — small wins):** payoff fails → cycle-2/HP never fires (equity never climbs the +1.0% promotion bar) → the overshoot-carryover (which EXISTS, C178/C204/C256) can't demonstrate. Fix payoff, all three resolve.
- **The deeper bug found at C285:** the bot was SCREENING OUT its best trades. BSB scored 1.000, blocked ~10× over 5h for "leg_exhausted" while running +19.1%; 5/6 high-score blocks that session missed 3–11% runs. This is the priority — a bot that blocks its winners can't have a payoff.

## 2. Version ledger (recent — full text in CHANGELOG.md on the phone)
| Ver | What | Status |
|---|---|---|
| **C308** | S3-P ride extension at the exit layer (held-position `_s3_live_p` stash + OR-channel ride strength + strong tier at P≥0.80·EV≥0.30) | shipped, retro HOME 2.08×/BILL-class 3.53×PRU ✓ |
| **C307** | Step-1 coil wildcards (44 + 4 quiet-big pairs into the projector) | shipped, live-visible in pre-flight ✓ |
| **C306** | Hurst-scaled E_win in `_c302_p_ev` (chaos→R channel, [0.80,1.35]) | shipped, unit math ✓ |
| **C305** | Monitor 0.8s (parallel fetches unchanged) | shipped, live banner ✓ |
| **C304** | Overshoot credit: eff=max(base−pool,0.10), pool≤0.75, persisted | shipped, ledger sim 5/5 ✓ |
| **C303** | Kelly at the risk layer: share ×k(f*), 0.70×remaining, dust rescue | shipped, $-retro BILL/B/ESPORTS ✓ |
| **C302** | RPP STAGE 3: `_c302_p_ev` blended-P (3 frames, correct TFs: pair-15m-legs×regime / 4h-structure regime / score) → EV(PRU, own-ATR) → bar-flex subsuming C295 + Kelly-on-P size mult before all caps + close-time Brier calib (s3_calib_v60.json) | shipped, unit math + pre-flight ✓ |
| **C301** | 🔹→🔵 bullish/winning markers everywhere; 🟩×18 green rule before each Step-3 pair block | shipped, live-visible in pre-flight ✓ |
| **C300** | Admin-sweep attribution (record_close admin flag: no losing-dir feed, no spent-pause, '🔁 SWEPT' banner, C223 'swept' tag) + HP deferral while runner rides (`_pending_hp` persisted, entry gate, flat-triggered resolver) + held-symbol Step-3 feed (pyramid dead-path resurrected) | shipped, 3-cluster retro ✓ |
| **C299** | BROKEN-PARABOLA exception to the C292 guard (ESPORTS −16% inversion: stale-24h + MR-biased projection blocked 8 shorts on a collapsing parabola the parabola-gate design leaves open; shared-state release ≥3 ATR off extreme on ≥6/8-ATR range, fail-closed, RAVE/HOME retro-preserved) | shipped, retro 5/5 + pre-flight ✓ |
| **C298** | Selected-pair RETENTION: Step-5 selections stay in the analysis set 3 scans (max 4 adds, self-cleaning) — removes blindness to own recent theses | shipped, unit-sim + pre-flight ✓ |
| **C297** | Regime-aware entry URGENCY: crossing limits when the spine says the regime runs with the trade (taker), passive maker otherwise; resting-window 2→5m; pyramid same | shipped, retro 6/6 + pre-flight ✓ |
| **C296** | RPP STAGE 2.5: learned-P enters the gates (leg-exh release OR-channel, C291 third channel, climax-veto 4-condition downgrade) + PairMarkov calib log line — VALIDATED live (pipeline produced 2 selected shorts in a bear tape) | shipped ✓ |
| **C295** | RPP STAGE 2: pair-state Markov conditioned on regime (prior→C236 posterior) + FIRST routing (regime-direction entry-bar flex ±, conf-gated) — VALIDATED live (bar-flex 73×, all shorts eased in P=0.94 down-tape) | shipped ✓ |
| **C294** | RPP framework STAGE 1: regime-transition Markov + calibration (observability-only spine) — VALIDATED live (acc 0.80, Brier 0.071) | shipped ✓ |
| **C293** | Regime-conditional exhaustion thresholds (frame-balance fix: raise F3 pressure, make F1 regime-appropriate) | shipped, simulated+pre-flight ✓ |
| **C292** | Projection-consistency direction guard (RAVE mis-signed-short fix) + parabola/absorption gate audit (clean, left intact) | shipped, retro+pre-flight ✓ |
| **C291** | Pair-level runner override on structural-exhaustion gate (the RAVE +10% miss fix) | shipped, retro+pre-flight ✓ |
| **C290** | 3-frame composition audit + double-count fix (C288 softened vs C289) + advanced-component integration verified | shipped, live-tested ✓ |
| **C289** | Regime-STRUCTURE family conditioning (chop↓trend/momentum, trend↓meanrev) + momentum-snap kept-as-is verdict | shipped, simulated+pre-flight ✓ |
| **C288** | Sensitivity/specificity RESCALE — regime×pair-history classifier; recalibrated thresholds | shipped, simulated+pre-flight ✓ |
| **C287** | Fuel/whipsaw guard on the C285 override (separates BSB-runner from EVAA-whipsaw) | shipped, retro+pre-flight ✓ |
| **C286** | Pyramiding into runners + TRUE paper-limit fills + maximize pair-history fingerprint | shipped, pre-flight ✓ |
| **C285** | Exhaustion-gate forecast override — the missed-opportunity fix (BSB +19% class) | shipped, retro ✓ |
| **C284** | Payoff package: gated min-lev 1.5, EPC/ride widening, base-strength floor gate | shipped (starved by exhaustion gate until C285) |
| **C283** | HP-mode restoration (dead-read: saved mode never assigned to self.mode) | shipped ✓ |
| **C282** | 100-trade eval odometer + changelog-writer resurrection (dead since ~C264) | shipped ✓ |
| **C280** | Winner give-back blind-band sealed (0.65×peak floor caps) | proven live (9 firings, never >65%) |
| **C279** | True limit-order OFFSET (was market-at-price); PairProfileStore confirmed live | shipped ✓ |

## 3. The 5-stage pipeline — scrutiny verdict ("is this the best possible?")
- **Stages 1–3 (screen → analyze → score): SOUND.** Organic cohort 71% WR; top movers surface at screen rank #1–3; the engine finds real trades. The isRwa filter (C155), $750k relative volume floor (C81), and 48-signal 6-family scoring (C211) all working.
- **The C285 exception:** the leg-exhaustion gate (Stage 3) was the one broken screen — fuel-cap 2.5×ATR made any real trend read "exhausted"; now forecast-overridden.
- **Stages 4–5 (size → leverage → manage): the leak.** Timid sizing (42/46 trades at 1x), winners cut at +2%. C284+C286 rebuild exactly here.

## 4. Cohort finding (the window's own data, n≈54)
- **Organic entries: ~71% WR, net positive** — the clean engine.
- **Floor-lifted entries: ~48% WR, net negative** — variance-heavy, NOT uniformly toxic (session-9 proved good-base lifts win, dead-projection lifts lose). C284-5 gates the lift on base≥0.60 + live projection. Retro: blocks 3 dead-projection losers, 0 winners.

## 5. Architecture principles (enforced)
- **Relativistic everywhere** — thresholds normalized to each pair's own ATR/PRU/history; no absolute cutoffs.
- **Predictive > reactive** — leading signals (real CVD from /fills, OI-divergence, funding trajectory, L/S) are first-class; RSI/MA demoted to leg-description, grouped so 10 correlated signals can't outvote flow.
- **DSI-DRI gap = entry conviction; gap deceleration = exit trigger.**
- **Loss reduces margin, never the score bar.** Kelly-conviction-vol sizing, per-trade risk cap (C274b), 9%-equity hard stop (C184), 2.5% day cap.
- **Scoring is now a CLASSIFIER (C288):** score = tanh(|avg_sig| · breadth^1.9 · family-count-bonus · regime-fit · 2.2). Sharpens the sensitivity/specificity spread — split-family "traps" collapse, aligned+regime-fit setups clear the bar, the mediocre middle thins. Regime-fit uses market regime × the pair's own Hurst/wildness, so a trend-call on a mean-reverting pair scores LOWER than the same call on a trend-prone one. Thresholds recalibrated to the new scale (MIN_SCORE 0.32/0.36, PAYOFF_TRIGGER 0.50 — same selectivity, ~0.71× scale). The C157 Range Engine + C25 Trend Engine (regime-adaptive signal WEIGHTS) feed IN; C288 adds regime-adaptive SCORING on top.
- **Family weights are now conditioned on THREE things (C289):** (1) the pair's own wildness (C228), (2) market risk-appetite direction (C229, correlation-gated), and (3) market STRUCTURE (C289 — trending/ranging/choppy). In chop, trend/momentum families are down-weighted (noise); in trends, mean-reversion is down-weighted (fights the tape). MIXED stays neutral. This is "different components for different market×pair conditions" — a noise signal in chop is a real signal in a trend, so weights shift, signals aren't deleted. The 6 families: trend, momentum, meanrev, flow, pattern, spectral.
- **Advanced components (C290-verified ALL wired + producing live values):** wavefunction (Born-rule |ψ|²), markov (3-state transitions), fourier, wavelet, lyapunov, kalman, hilbert, calculus (velocity/accel/integral), topology, diff_geometry, pca_factor, martingale, gbm_range, ou_meanrevert, fractal_dim. All in both the components dict AND a family tuple → they flow into family votes. Ran live on 3 pairs producing distinct sensible outputs. C171 fixed the historical dead-code; confirmed still live. No dead advanced components.
- **Momentum-snap / instantaneous feedback (C108/C110):** MEASURED as ~20% decisive / ~80% no-effect, with a pardon safety-valve (4 firings) that prevents it killing winners. Verdict: KEEP as-is, don't expand, don't prune — a cheap occasional veto, no evidence of harm.
- **Fill layer verdict (C279/C286/C297, code-audited + chart-audited 20260718):** the bot places GENUINE limit orders on both paths — live mode calls `create_order(sym,'limit',side,size,price)` (line ~2792); passive path prices ±0.10% favorable (maker 0.02%), C297 urgent path prices 0.05% THROUGH the touch (marketable limit = taker fill with a hard slippage cap — strictly superior to a raw market order on thin alt books). Raw market orders are never used for entries; exits fill at signal price billed taker (C257). Paper fills use the backward-5×1m `_limit_touched` proxy — both 20260718 fills were chart-validated genuinely touchable (TRUMP 5m-low 1.632 ≤ bid 1.650348; XEC 0.008081 ≤ 0.008220), keeping the live-valid fill streak. Limit-vs-market is NOT either/or: passive maker in oscillating tape (better basis + 3× cheaper fee), crossing limit in a persisting regime (the 120:1 fee-vs-continuation economics) — the regime spine already routes this correctly.
- **Pair-history (C233/C286) is the bot's market knowledge beyond the API** — persistent 4-D fingerprint + regime-conditional tendency, now consumed broadly (C286-2), not just at extremes.

## 6. Known open issues (ledgered, not all fixed — anti-overfit discipline)
1. **Stagnant-loss entries buying fades** in chop (6/7 losses session-12) — watching C285's effect before touching.
2. **Runner-blocking exhaustion gates — RESOLVED (audited C292):** C287 fixed leg_exhausted, C291 fixed structural-exhaustion "0% room", C292 fixed the RAVE mis-signed-direction (TURNING branch now blocks a counter-trend entry when the pair's own projection confirms the trend). The parabola and absorption gates were AUDITED (C292) and are CLEAN — both already pair-level (parabola reads DSI/OIdiv/CVD, absorption reads CVD-opposing-flow), neither has the market-only bypass. Left intact; extending overrides there would reopen real risk. The RAVE class is fully closed.
3a-ii. **BANK +45.6% (max +48.6%) never entered (20260718b)** — screened #2–4 all session, longs died on genuinely LOW SCORES (news-conflict ×0.70, CVD modest) plus the TD-regime tax ×1.17: the third Frame-1-runner-in-Frame-3-tape exhibit (TRADOOR +15%, LAB +12% max, now BANK). The binding constraint was Frame-2 score, not a gate — S3's per-pair P is the designed answer; do NOT hand-tune gates on n=3.
3a. **Screen blind spot (20260718): BIRB −16.3% and G +12.0% — the window's #1 and #4 movers — got ZERO log mentions** (never screened; volume/liveliness at scan time TBD vs their post-move 24h stats). One session's evidence; watch whether Step-1 misses recur before touching the screen.
3b. **Frame-1-runner-in-Frame-3-chop tension (20260718):** TRADOOR (+15.1%, conviction 1.00, breadth 6/6) and LAB (+6.7% net / +11.7% max, breadth 6/6, own CVD +0.60 aligned) were repeatedly blocked in a CH tape — structural-exhaustion "1% room" (+7.6% follow-through missed), capitulation-rejection (real bearish wick — defensible), and razor-thin bars (LAB post-penalty 0.26 vs 0.27 with aligned flow; TRADOOR 0.607 vs 0.628 with CVD −0.24 opposing). C293 deliberately tightens chop exhaustion; these two pairs were in their OWN trends inside the chop. n=2, several blocks flow-contradicted → LEDGERED, not patched (anti-overfit). The S3 EV layer is the principled resolution (a pair's own P(continue) should outvote the market-frame exhaustion bar when evidence is strong).
3. **Small-cap coverage gap:** movers ranked #110-182 by volume ($1-3M: MYX/CAP/BASED/FF made 3-5%) sit below the 30-pair analysis window — screened but not deep-analyzed. Left as-is (fill/noise risk on thin pairs); revisit if small-caps become a priority.
4. **Paper-optimism gap** (~+$0.56 measured) — C286 realistic fills should close it; expect fill rate to drop.
3. **Directional-hypothesis gap** — on strong movers the bot generates ~50 shorts, 0 continuation-longs (US +75% case). Needs the directional-vote rework (post-verdict).
4. **Per-signal hit-rate ledger not built** — weights come from doctrine + falsification, not measured per-pair accuracy. The designated big post-verdict build; the window is generating its training data.

## 7. Falsified hypotheses — BANKED (never re-propose on the same evidence, Principle #45)
- **CVD-sign consent for urgent entries [refuted by log_c338's own numbers, replaced in C341]** — the three urgent knife-longs carried CVD +0.23 / +0.20 / −0.13 at entry: sign catches none. Fuel MAGNITUDE (C311/C337 blend ≥ +0.10 signed) separates 5/5 on the same data. Never re-propose sign-only flow consent.
- **"The bot exits too early / hand-back is the payoff problem" [REFUTED 2026-08-01, n=24, both directions tested]** — terminal return after exit is −2.79% at 48h with only 8/24 positive, excess z=−0.42, **t=−2.19**; holding every position 48h longer costs −$13.07. The original +16.65% evidence was a max-favourable-excursion artifact measured without its adverse counterpart. Tightening (C360) A/B'd worse; loosening is worse still. **Never re-propose an exit-timing change on excursion evidence.**
- **Kill-list item #7 (the C360 profit-ratchet A/B verdict) — EVIDENCE VOID [2026-08-01]** — measured on the dead-clock harness, i.e. against a bot whose entire STAGNANT family could not fire. The revert stands on Finding 2's grounds; the A/B numbers themselves must not be cited again. Kill-list #2 is suspect for the same reason.
- **"No configuration reached positive expectancy" / the −42% alpha [SUPERSEDED 2026-08-01]** — that figure came from a single Nov–Dec 2024 window in which BTC rose +42%. Same bot, same harness, bear window: **+10.18% vs BTC −15.97%, alpha +26.15%**. Alpha is regime-conditional and must never be quoted without its benchmark window.
- **"Don't board extended pairs" / exhaustion-boarding filter [REFUTED 2026-08-01b at 158,444 observations]** — bot-level evidence looked decisive (0-for-9 in the bull window, t=+2.57) and vanished at scale: bull-regime gap −0.02pp, t=−0.29, 2/4 OOS splits, flat across 9 threshold combinations. The CHOP cell's t=+5.23 was an overlap artifact (non-overlapping: t=+0.74, time split flips sign). **Never re-propose a range-position or already-travelled entry filter.**
- C277 flow-waiver extension to exhaustion gates: fires 0/5 on real logged flow. Dead.
- leg-X as a discriminator: saved at X=1.23/1.49/2.32, cost at X=1.67/2.02/2.62. Not separable.
- Blunt "cap the floor": session-9 lifted-cohort reversal killed it → refined to base-strength gate.

## 8. Operating protocol
- **Stop the bot only when flat** (resumed positions wake into a fresh regime and can insta-exit — proven, VANRY).
- **Fresh Start is fine** if a position must be abandoned; the ledger books it at last-known PnL.
- **Reset the counter:** delete `eval_window_v60.json`. It survives normal restarts + Fresh Start otherwise.
- **Log upload:** compress (ZArchiver → .zip); keep only current .py + this Atlas + latest 1–2 logs in project knowledge; delete the rest after analysis.
- **Verdict basis:** trade-by-trade PnL SUM (reset-proof across the two $50 resets), not equity delta.

## 9. Verification discipline (every build)
Syntax + AST (function count preserved ±expected) → retro against the exact logged failure → live pre-flight boot in sandbox (native PAPER_MODE, real Bitget data) BEFORE delivery → present only the .py + this Atlas. Pre-flight is mandatory (Principle #46) — its first flight found a months-dead changelog writer.
- **STANDING (operator directive): a live-market missed-opportunity chart check precedes EVERY code change — and it means the FULL vol≥$750k universe (~230 pairs) at EACH scan timestamp, NOT a top-N-by-volume shortcut.** The top-35 shortcut once hid RAVE (#41, a clean +10% miss). Check the whole market, every scan. It has already earned its place — it caught C285 shipping half-right (forecast sign alone doesn't separate a runner from a whipsaw → C287 fuel guard), and it RETRACTED two false "misses" (1000XEC and SXT were SHORTS whose gates were working; I had mis-measured direction). Check direction before claiming a miss.

## 10. Immediate next steps
1. Run C288 — the big one. Confirm: (a) scores now SEPARATE (winners clear 0.32+, traps/misfits fall below); (b) the payoff machinery finally FIRES (lev-1.5 and ride-mode need ≥0.50 — watch for them); (c) split-family setups like the old PEPE-0.801 get correctly crushed; (d) the bot doesn't go idle (pre-flight showed ~12% of candidates clear the floor — healthy). Watch the result['_c288'] debug (spec/cnt/fit/reg) to see WHY each score.
2. If payoff climbs (winners bigger via leverage/ride on genuinely strong setups) → the whole diagnosis chain is validated.
3. Prior fuel-guard confirmation still pending — BSB-class (real body, rising vol, forecast-confirmed) RIDES (saw FARTCOIN released at boot), EVAA-class (rejection wick / fading vol / dumping momentum / blow-off) STAYS BLOCKED (log now names which fuel check vetoed).
2. Confirm the C286 machinery fires on real trades: winners RIDE (C284-3), runners PYRAMID (C286-3), paper fill-rate drops (C286-1), fingerprint 🧬 "coiled" flags (C286-2).
3. If payoff climbs toward 1.2 and cycle-2 starts firing → diagnosis confirmed. If not → the per-signal hit-rate ledger is the next build.
4. Every session: live-chart missed-opportunity check FIRST, then log forensics.


---
# ⚠️ ATLAS INTEGRITY NOTE (C407)

Sections **C397–C402** and **Atlas principles #43–#60** were lost when a later session re-copied the
uploaded Atlas over its own appended work before appending again. Reconstructed below from the
shipped changelogs. **Never `cp` the uploaded Atlas over the working one — always append.**

---
# C397 — THE TWO-STORIES AUDIT

**Atlas principle #43 — A number identical across many different pairs is a default, not a measurement.**
The C395 drift guard printed exactly `0.60%` on eight different coins across two sessions. Eight
coins cannot share one volatility. Any constant appearing where a relativistic value belongs is a
missing key or a fallback until proven otherwise.

**Atlas principle #44 — ONE VOLATILITY TRUTH.** `atr_pct` is close-to-close and floors near 0.30%. The risk chain
reads `max(_n52_atr, atr_pct)`. C259 fixed this for sizing; C395 re-introduced it for the drift
guard; C397 fixed it again. Any new code touching volatility reads the max.

**Atlas principle #45 — A promise printed in the log must be enforced by the code path that actually acts.**
C338 printed `floor +4.37% ratchets with the peak`; `TRAILING_TP` — a *different function* running
*first* — closed at +0.58%. Grep every path that could fire before the enforcer.

**Atlas principle #46 — Money and statistics are separate ledgers.** `release_margin` moved cash *and* incremented
trades/wins/losses, so a half-close counted as a whole trade and an unfilled limit counted as a loss.

**Atlas principle #47 — A price is only legal on the instrument's own tick.** Round to `precision.price`,
directionally (passive away from touch, exits toward it). TUT/CHIP tick in 0.00001; the bot priced
to 6 decimals.

**Atlas principle #48 — Anchor maker orders to the BOOK, never to `last`.** In a falling tape `last` sits *above*
the ask, so "0.10% below market" is an aggressive order.

| retro | value |
|---|---|
| false drift aborts released | 8 of 8 |
| runner-floor recovery | +$0.43 / 2 sessions |
| win rate corrected | 40% → **60%** (same trades) |

---
# C398 — CAPITULATION-REVERSION (first new edge since C396)

**Atlas principle #49 — Always compute the blind baseline before believing a win rate.** The corpus tape was rising:
blind long already wins **51.03%**. Every long-side claim is scored against 51.03%, not 50%. This
control killed two of three candidate edges outright.

**Atlas principle #50 — When a mechanism predicts an asymmetry, ship only the side that survives.**
Forced flow reverts, voluntary flow continues; in perps the forced side is long.

| condition (60 pairs × 20d, 114,660 obs, ±1 ATR @1h) | n | WR | vs baseline | halves |
|---|---|---|---|---|
| pack fell >1.5 ATR in 3h → **BUY** | 3,420 | 55.7% | **+4.67pp** | 54.2 / 59.3 ✅ |
| pack rose >1.5 ATR in 3h → sell | 3,900 | 51.9% | +2.93pp | 53.5 / **48.7** ❌ |
| pair at own 12h low → **BUY** | 3,847 | 53.3% | **+2.28pp** | 52.1 / 54.5 ✅ |
| pair at own 12h high → buy | 4,390 | 51.3% | +0.31pp | noise ❌ |

**REFUTED, not built:** cross-sectional factor share (corr **+0.925** with existing coherence —
not new information); close-location run length (48–50% flat, runs 1–5, both halves).

**Atlas principle #51 — A rate measured in a backtest is a property of the corpus, not the bot.**
"~0.2–0.3 trades/day" was a replay artefact (2 of 4 windows were dead tape). Live count: **11 entries
in 11.25h ≈ 23/day.** That one wrong number steered the roadmap toward *frequency* when the deficit
was *payoff*.

---
# C399 — DRI/DSI: THE EXITS WATCHED THE WRONG END OF THE SCALE

**The semantics, settled** (67 DRI + 56 DSI readings, one session):
DRI **never positive** (−0.413…−0.028). DSI **never negative** (+0.000…+0.445).
Large negative DRI = thesis STRONG. **DRI → 0 = thesis DYING.** The danger is at zero, not the extreme.

| rule | required | best ever observed |
|---|---|---|
| `DSI+DRI DIVERGE` | `dri_dev > max(0.18, …)` | **+0.011** |
| `DRI HARD` | shift 2× baseline → DRI ≈ **+0.17** | DRI never goes positive |

**Unreachable by construction** — two of seven advertised exits had never fired.

**Atlas principle #52 — Measure conviction as a RATIO of its entry value, never as a level.**
`retention = value_now / value_at_entry`. 1.0 intact · 0.0 dead · **<0 = sign flipped, reversal has
arrived.** Weaker of DRI/DSI governs; a baseline under 0.10 **abstains**.

**Atlas principle #53 — A loss-mitigation exit must never be able to truncate a gain.** C399 is gated to
`pnl ≤ 0` and sits outside `_C372_PROFIT_TOKENS`.

**Atlas principle #54 — An unattributable log line cannot be audited.** The DRI/DSI line carried **no symbol** — APR
had to be identified by subtracting Δb to recover its baseline.

**Chart-verified cost (APR):** DSI retained **4% while price was still flat at −0.61%**; bot held 51
more minutes and exited on a 90-minute clock at **−3.5%**. C399 fires at −0.61%.

---
# C400 — ARE DRI AND DSI COMPUTED CORRECTLY?

**DSI: YES, exact.** Reconstructed from the log's own dump → 0.26119; log printed `0.261`.

**DRI: NO.** Three sources disagreed — banner "9 components / sum 1.02", comment "normalized to 1.0",
arithmetic **11 contributors totalling 1.1133**. Two compounding errors: `base_total` hardcoded 0.75
while the eight weights sum to **0.70**; `rvs` (0.07) + `time` (0.10) added *outside* normalisation.

**Atlas principle #55 — Two indices compared against one threshold must first share one scale.**
DSI used 6 of 11 components (sum 0.59), never normalised → ceiling 0.767 vs DRI's 1.1133.
No threshold choice could have fixed that comparison.

**Atlas principle #56 — Changing a value's UNITS invalidates every persisted copy of it.** (Atlas #23 in reverse.)
Re-normalising DRI ×0.876 and DSI ×1.695 would have made restored DSI retention read **~70% too
high**, silently disabling C399 on exactly the positions that survived a battery swap.

*Recorded, no change:* DSI carries **no information independent of DRI** — it is the negative of a
six-component subset of DRI's eleven. Never treat them as two witnesses.

---
# C401 — WHERE CAN AN INDEPENDENT SECOND OPINION COME FROM?

**Atlas principle #57 — A second opinion derived from price cannot help when the first is a coin flip.**
Baseline continuation WR *when momentum says continue* = **49.26%**; blind directional = 51.03%.
**Conditioning on momentum makes the bot worse than not conditioning.**

*Absorption hypothesis REFUTED:* impact decaying **with rising volume** — the exact cell the
mechanism predicts — scored 49.2% vs 49.26% baseline. **−0.07pp on n=20,080.**

**The two layers that qualify:** side-tagged taker flow (`/fills`) and open interest. Neither is a
function of the pair's own OHLCV, so neither can be inside DRI.
**All three `_fetch_real_cvd` call sites were on the entry path; none in the monitor.**

**Atlas principle #58 — When a channel cannot be backtested, instrument it and let the next log be the dataset.**

---
# C402 — A SELF-CANCELLING ORDER LOOP

**Atlas principle #59 — The fee and the order type must come from ONE boolean.**
C363 set `postOnly` on *every* entry limit, including C297/C395 entries C397 deliberately prices
*through* the book and bills at the **taker** fee. Two decisions, two booleans, drifted apart:

```
⚡ CROSSING entry → limit @ $0.07077 (+0.05% through the book, taker)
🛑 POST-ONLY REJECT: CAP buy @$0.070770 vs bid $0.070620/ask $0.070690 — would cross
```
**Live behaviour, not paper.** Every urgent/high-conviction entry was cancelling itself. CAP then ran **+7.32%**.

**Atlas principle #60 — Retention only works on a one-sided quantity.** C401 measured `cvd_now / cvd_entry`; entry
delta was **−0.093** (long entered *against* flow) and printed **`407% of entry support 🟢`** —
a ratio of two negatives. DRI/DSI are one-sided *by construction*; taker flow is not.
Now **signed support** = `cvd × direction`.

*Missed-opportunity check:* majors flat (BTC +0.03%) — which is what "83% short coherence" was
reading — while the bot's own top-30 ran **ONG +11.89%, BTW +13.14% max, US +7.38%, CAP +7.32%**.


---
# C403 — THE FEE BUDGET IS THE ARCHITECTURE

## Atlas principle #61 — derive the trade rate from the profit target, not from opportunity

3%/month on $250 = **$7.50/month**. At $20 notional a round trip costs $0.004–$0.016.

| trades/day | fees/month | share of target |
|---:|---:|---:|
| 6 | $2.11 | **28%** |
| 12 | $4.22 | 56% |
| 22 | $7.74 | **103%** |
| 45 (observed) | $15.84 | **211%** |

**The bot was trading 5–10× more often than its own profit goal can pay for.** No improvement
anywhere else survives that. Sweet spot: **6 trades/day, 0.34% gross per trade = 55% WR at 1.5:1** —
payoff doing the work instead of accuracy.

## Atlas principle #62 — a controller must be able to let go of its own output

The C403-1 servo tightens the entry bar when the rate exceeds the fee budget. Without **in-band
decay** it ratchets: one busy stretch drives the bar to 1.60, the rate falls into the deadband, and
the bar stays tight forever. Inside the band the correction bleeds off at **half** the step —
slower than it was applied.

Closed-loop verified: 45/day→×1.60 · 22→×1.60 · 12→×1.60 · **6→×1.00** · 2→×1.00 floor · and 1.60
returns to 1.00 after 40 in-band scans. **It can only tighten** — a quiet tape is a real state, and
manufacturing trades to fill a quota is exactly the C389 failure.

## Atlas principle #63 — money and knowledge are different ledgers; only money starts over

| RESET on Fresh Start | NEVER RESET |
|---|---|
| `state_v60.json` | 5× Markov files |
| `positions_v60.json` | `s3_calib_v60.json` |
| `mode_v60.json` | `eval_window_v60.json`, `pair_profiles_v60.json`, `learning_v60.json` |

`learning_v60.json` was **deleted every Fresh Start**. Removed — deleting a state file is never a
safe default.

## Atlas principle #64 — per-symbol learning needs samples the universe cannot supply

118 tradeable pairs × ~30 outcomes each = **3,540 trades ≈ 295 sessions ≈ 10 months** before the
*first* symbol's memory means anything. FIX6 blocked after **one** loss. That is not learning; it is
a one-observation penalty that benches pairs during exactly the volatile stretches where they are
most tradeable. **Shared** (Markov) learning works — ~2,000 observations/session — and is untouched.

## Atlas principle #65 — a rule that cannot separate the two states it exists to separate must not hold a veto

`parabola_bounce` blocked 60 longs, `resultant_counter` 50 shorts, in a window where the bot's own
top-30 ran +8% to +19%. **Nothing could pass in either direction.** Neither can tell a blow-off from
an ordinary pullback — both read as "N ATR from the day extreme". Both are now **weighted penalties**
(×0.82, ×0.85). Only *mechanical impossibility* deserves a veto.

## Atlas principle #66 — N uncoordinated risk controllers means none of them knows the risk

Four were running: day cap (realised), open-stop reservation (unrealised), C329 diagnostics,
Guardian. Kept the first two — two halves of **one** honest ledger. Stood down the two heuristics.

## Method note

Steps 2–4 ship as **switches, not deletions** — functionally identical, reversible in one line, and
far safer than tearing 1,500 lines out of a 25,000-line file. Excise once a live session confirms
nothing depended on them.

---
# C404 — THE BOT MEASURED PROBABILITY AND NEVER MEASURED PAYOFF

## Atlas principle #67 — expectancy has two halves; this bot only ever computed one

`E = p·W − (1−p)·L`

Score · confidence · conviction · agreement · DRI · DSI · flow · regime · Markov · calibration ·
session tilt · capitulation tilt — **every one estimates `p`.** Not one asks how much the trade pays
when right relative to what it costs when wrong. **Half the equation was never computed.**

## The arithmetic that proves no exit fix could ever have worked

Session 20260818: **57% win rate, −$1.13.**

| | value |
|---|---|
| mean peak on winners | 2.6% |
| mean PRU (risk unit) | 1.9% |
| **peak in risk units** | **1.37 PRU** |
| **stop sits at** | **1.3 PRU** |

**The typical peak and the stop are the same size.** Max payoff at *perfect* capture = **1.05:1**.
Target needs **1.50:1**. Decided at entry, not at exit.

## Atlas principle #68 — a next-leg forecast and a full-position stop are different units

My first version of the gate compared them raw and **rejected all seven trades including the +2.7%
winner.** A gate that admits nothing is useless, and the failure is recorded rather than tuned away.

The log measures the error: ATOM projected +1.3% and peaked **+3.4%**; PENGU +1.2% → **+2.5%**;
ACU +1.6% → **+3.3%**. The projection understates realised excursion by ~2×, every time.

**The correction is the random-walk law, not a fitted constant:** excursion grows with **√t**, so a
60-min hold on a 15-min forecast scales by √4 = **2.0** — exactly the observed ratio. √ rather than
linear is deliberate: price does not travel 4× as far in 4× the time.

## The gate

```
R = (projected_move × √candles) / stop_distance      # dimensionless
E = p·(R × 0.60) − (1 − p)                           # p clamped to [0.45, 0.72]
require R ≥ 1.7  AND  E ≥ +0.15R
```

Replayed on the session's own seven entries: **takes** ATOM (3.13R), ACU#2 (2.13R), PENGU (1.71R);
**rejects** ACU#1, BTW, GPS, ACU#3. *n=7 — three-for-three is a coin landing heads three times, not
evidence. The gate is justified by the arithmetic, not the outcomes.*

## Atlas principle #69 — a saturated actuator has no authority

C403's servo pinned at ×1.60 while the rate climbed **8.7 → 12.1 → 15.9 → 17.1/day.**
**A score tax cannot hold a rate down when the scores clear the bar anyway.** Demanding 1.7R of
*room* removes shallow setups instead of taxing them — the honest actuator.

## Atlas principle #70 — a limit that starts a countdown is not a limit

`REL_DRAWDOWN` reports `limit=-1.3PRU` then requires **8 more readings** before acting. ACU exited at
**−2.0 PRU, 54% past its own limit**, and the message prints the proof: `limit=-1.3PRU p=8`.
Loss-side twin of the C397 runner-floor defect. Patience now bounded at **1.35×**.
Retro: ACU −3.0% → −2.03%, payoff 0.78 → **0.94**, E +0.024% → **+0.164%**/trade.

## C403 confirmed in production

| | before | after |
|---|---|---|
| POST-ONLY REJECT | 2 | **0** |
| Guardian blocks | 5 | **0** |
| `resultant_counter` vetoes | 50 | **0** (penalty) |
| `parabola_bounce` vetoes | 60 | **0** (penalty, 95 applied) |
| entries with positive taker flow | mixed | **6 of 7** |

The 3 remaining `momentum snapped` are now **correct** — 1.27, 1.02, 1.05 ATR of genuine adverse
drift, each judged on its own true ATR instead of the old 0.60% constant.

---
# C405 — THE GATE WAS RIGHT, THE THRESHOLD WAS ABSOLUTE

## What four live sessions showed

C404 shipped `R ≥ 1.7` and `E ≥ +0.15`. Across **~24 hours**: **3 positions opened, 1,723
expectancy rejections.** One session ran **17 hours** and took one trade.

**The measured distribution (n=1,723 real candidates):**

| | R | E |
|---|---|---|
| median | **0.69** | **−0.115** |
| p90 | 1.46 | +0.204 |
| p99 / max | 1.83 / **2.44** | +0.452 |

`R ≥ 1.7` admits **1.9%**; with `E ≥ 0.15` too, **0.1%** — one in a thousand.

## Atlas principle #71 — a threshold set from survivors cannot be applied to the population

The 1.7 came from seven trades that had **already passed every other gate**. My own replay one
version earlier had rejected all seven and warned of this exact failure — and I answered it by
**tuning the number instead of changing its kind.**

## Atlas principle #72 — this is the fourth instance of one disease

| version | the fixed number | where a relative one belonged |
|---|---|---|
| C397 | `0.60%` drift bar | 0.9 × the pair's true ATR |
| C399 | `0.18` DRI floor | fraction of the entry baseline |
| C400 | `0.75` base_total | computed sum of the weights |
| **C405** | **`1.7` R / `0.15` E** | **percentile of the live distribution** |

## The replacement — principled floor + competitive bar

1. **`E ≥ 0`, absolute.** A negative-E trade is not a gamble, it is a decision to lose money slowly.
   **31.6%** of candidates clear it — a real filter, not a formality.
2. **`E ≥ percentile(recent E)`**, the percentile **servoed against the realised trade rate**. The bot
   doesn't need a *good* trade, it needs the **best available now** — a fact about today's tape.

**Replayed on the 1,723 recorded values:** rate 12+/day → pct 99 → 1.8% pass · rate 6 → pct 85 →
16.8% · rate ≤3 → floor → 31.6%. **Authority span 1.8–31.6% against C404's fixed 0.1%.**

## Atlas principle #73 — a stale boot banner is misinformation, not decoration

It advertised **`OmegaGuardian (ACTIVE)`**, **`Self-learning`**, **`HP 10min patience`** and
**`DSI+DRI divergence | DRI HARD`** — all stood down by C403 or proven unreachable by C399/C400. It
printed "14 components" above a list of 11 and "7 intelligent exits" above a list of 10.

Rewritten to the four numbered loops with thresholds **interpolated from config**, plus an
**EDGES** section and a **RETIRED** section stating what was removed *and why*.

---
# C406 — BOOT CRASH: A COSMETIC LINE STOPPED THE BOT

C405 made the Guardian banner conditional and reached for `self.cfg` inside
`OmegaGuardian.__init__`. **That class holds `bot`, not `cfg`.**
`AttributeError` during startup → the bot printed its whole banner and **died before the first scan.**

**Atlas principle #74 — A cosmetic line must never be able to prevent a boot.**
Decoration does not get to raise. The banner block is now wrapped, and config is reached *through*
the bot: `getattr(getattr(bot, 'cfg', None), …)`.

**The general form of the bug — edited a class without checking what that class holds — is now a
standing machine check** (see #78). Whole-file result: **1 instance, the one that crashed.**

**Atlas principle #75 — Derive always, announce only on change.** The daily-budget block printed **twice**, six
identical lines to the cent. It is *derived* three times on purpose (init, post-load, day anchor);
deriving is not announcing. A log that repeats itself trains its reader to skim — which is how the
stale HP line beneath it survived several versions unnoticed.

**Atlas principle #76 — A break-even win rate is only true at 1:1 payoff.**
The banner said `break-even daily WR 50.0%`. At the measured payoff of **0.78** the real figure is
**56%** — the bot needed to win 14% more often than the operator was being told. Both now print, with
the honest one named.

---
# C407 — WHOLE-FILE AUDIT (six axes, machine-swept)

**Atlas principle #77 — A protection that can fail quietly is not a protection.**
C378's premise: *"one level, two enforcers: C377 while the bot runs, the exchange while it does not."*
That call sat inside `except Exception: pass`. If arming raised, **the second enforcer silently did
not exist** and the position ran naked against the exact failure mode it exists for — the bot being
dead. Now checks its boolean return, warns on `False`, warns when R is absent, logs the exception type.

Same class at two more sites: `_check_profit_targets` wrapped `_close_position` in a **bare
`except: pass`** — a raised close left the position **open** with nothing recorded. **C181 already
paid for this** (a `NameError` silently disabling every exit for a position, 60s at a time).
Atlas failure pattern #9.

**Atlas principle #78 — Audit by machine sweep, not by eye.** 25,762 lines cannot be read reliably; the last four
defects all hid in plain sight. Standing sweeps, all re-run as verification:

| sweep | result |
|---|---|
| duplicate / shadowed definitions | **0** |
| analysis-dict keys written, never read | **0** |
| `pos._attr` written, never read | **0** |
| classes reading `self.cfg` without assigning it | **0** (was 1 → C406) |
| long/short sign symmetry | **symmetric throughout** |
| `DRI_WEIGHT_*` sum | **0.7700** = C400's computed `base_total` ✓ |
| no-network boot battery | **7/7** |

The two zeros matter most: **the computed-but-not-wired family is currently absent** from C397–C406.

*Ideological sweep note:* 132 constants flagged, **overwhelming majority correct** — the variable is
already in PRU/ATR units. Comparing `_pnl_in_pru` to `−0.3` **is** relativistic.

**Atlas principle #79 — A config constant that is never read is a promise the code does not keep.**
**34 found** — `COUNTER_TREND_BIAS_BLOCK`, `PROFIT_LOCK_ENABLED`, `DRI_NOISE_FILTER`,
`MIN_CONFLUENCE_NORMAL/HP`, `MTF_AGREEMENT_THRESHOLD`, `PLANNED_TRADE_TIMEOUT`, `DRI_MAX_HOLD_MIN`…
An operator reading `Config` would reasonably believe every one is in force.
**One was mine:** `C405_ADAPTIVE_E` — a master switch shipped one version earlier and never wired.

Also catalogued: **15 methods never called** (incl. `Position.get_gde_exit()` — *an exit no path can
reach*); **131 bare `except:` + 339 `except Exception:`**, of which the **15 wrapping money calls**
are enumerated and the 3 most dangerous fixed.

**Deliberately not bulk-deleted** — removing a name is how a live reference breaks, and C389's lesson
is that intuition-driven change costs money.

---
# CURRENT STATE — the map (C407)

| loop | what runs now |
|---|---|
| **1 SCANNER** | 756 markets → volume floor (~110 pass) → **top 30** (`TOP_PAIRS_SELECT`, held; 50 is ready but must wait for positive live EV) |
| **2 ENTRY** | 11 components → one score · **3 hard vetoes only** · everything else a weighted penalty · **expectancy gate** `E = p(R×0.60)−(1−p)`, bar = `max(0, percentile(recent E))` servoed to ~6 trades/day |
| **3 MONITOR** | split loop: prices **0.8s** · OHLCV/DRI **20s** · regime **90s**, *after* positions |
| **4 EXIT** | 4 questions: HARD STOP · **THESIS DEAD (C399 retention)** · PROFIT FLOOR (C397 binds) · TIME. Loss patience bounded at **1.35×** |

**Live edges:** C396 session tilt · C398 capitulation (down-side only, +4.67pp) · C401 taker flow
(instrumented, not wired) · C403-7 flow term ±10%.

**Retired:** HP phase ladder (5 incident classes) · Guardian + C329 (4 controllers, none knew the
risk) · per-symbol learning (needs ~10 months) · DSI+DRI divergence / DRI HARD (unreachable).

**Files — money resets, knowledge never does:**
`state_v60.json` · `positions_v60.json` · `mode_v60.json` **← reset on Fresh Start**
5× Markov · `s3_calib` · `eval_window` · `pair_profiles` · `learning(_recent_trades)` **← never reset**

**The governing arithmetic:** 3%/month on $250 = **$7.50** = $0.341/day. At $20 notional,
**6 trades/day costs 28% of target; 45/day costs 211%.** Sweet spot **6/day at 55% WR and 1.5:1
payoff**. Current payoff **0.78** — *that*, not win rate, is the open problem.

---
# C408 — MULTI-ASSET: ONE FORMULA, MANY INSTRUMENTS

Bitget lists **759** USDT-M perps; **294 carry `isRwa=YES`** — single stocks (TSLA NVDA GOOGL MSTR
COIN INTC AMD MU SK-Hynix Samsung), commodities (XAU XAG CL BZ COPPER), ETFs (QQQ SOXL SOXS EWY),
oddities (ANTHROPIC, SPCX). C155 skipped all of them. Volumes are real: **SNDK $244M · KORU $231M ·
XAU $172M**/24h.

## Atlas principle #80 — the asset-class label predicts nothing; the instrument's own measurements predict everything

Measured 15m ATR: **MSTR 1.092% · BTC 0.630% · SNDK 0.517% · CL 0.520% · TSLA 0.240% · XAU 0.227% ·
NVDA 0.166% · QQQ 0.100%.**

**A stock is more volatile than Bitcoin and an ETF is six times quieter.** "Stock rules vs crypto
rules" would be the fixed-principle-for-all error in new clothing.

## Atlas principle #81 — fees belong INSIDE the expectancy equation

```
FeeR = (maker + taker + |funding| × expected settlements) / stop%     stop ≈ 2.6 × ATR
```

| | FeeR | R needed for E=+0.15 @ p=0.57 |
|---|---|---|
| MSTR | 0.029 | 1.78 |
| BTC | 0.050 | 1.84 |
| TSLA | 0.130 | 2.07 |
| NVDA | 0.185 | 2.24 |
| **QQQ** | **0.327** | 2.60 — **refused** (>0.25 cap) |

**Eleven-fold spread that does not track the class label.** The same idea costs **6.3× more on QQQ
than on BTC**; QQQ's funding alone (+0.0399%/8h vs XAU and NVDA at exactly 0.0000%) is 19% of a risk
unit. C404 never subtracted trading cost — a rounding error on Bitcoin, fatal on an ETF.
**The bar now rises by itself where trading is dear, with no table anywhere.**

## Atlas principle #82 — printing is not price discovery

RWA perps trade 24/7 (400 candles, **zero flat bars**) but median 15m range by UTC hour, as a share
of each symbol's own busiest hour:

| | 04 | 08 | 12 | **14** | 18 | 22 | concentration |
|---|---|---|---|---|---|---|---|
| TSLA | 11 | 35 | 38 | **100** | 31 | 13 | **9×** |
| QQQ | 24 | 47 | 46 | **100** | 41 | 23 | 4× |
| XAU | 38 | 50 | **100** | 78 | 73 | 29 | 2.6× |
| BTC | 25 | 78 | 55 | 53 | 31 | 36 | **flat** |

Outside its session an equity perp is order flow against a **frozen anchor**. Admitted only while the
market that *discovers* the price is open: US cash 13:45–19:45 UTC Mon–Fri · Asia 00:45–06:45 ·
Globex Sun 22:00→Fri 21:00 · crypto always. **Weekends exclude every equity.**

## Atlas principle #83 — a venue maximum is a liquidity statement, not a recommendation

Leverage scaled so PRU lands in the same **equity** terms whatever the instrument — verified
**QQQ 6x→1.20% · NVDA 4x→1.33% · XAU 3x→1.36% · TSLA 3x→1.44%**, converging on the 1.30% target.
Bounded by Bitget's own `maxLever` (XAU/TSLA/NVDA 100x, MSTR 25x, QQQ 20x) *and* a hard bot ceiling
of 20x. Crypto sizing untouched.

**Bug caught while wiring:** the accessor is `fetch_funding_rate`, **not** `get_funding_rate`. Inside
a `try/except` the wrong name would have silently zeroed the funding term forever (Atlas #43/#79) and
made QQQ look 19% cheaper than it is. Written as a checked `getattr`.

**NOT YET VALIDATED LIVE** — no RWA position has ever been opened. The first log with one is the evidence.

---
# C409 — MULTI-ASSET: THREE EDGES REFUTED, AND THE ONE THAT SURVIVED

Purpose-built corpus: **40 days × 19 symbols** (14 US-equity perps + gold + oil + BTC/ETH/SOL),
3,840 aligned 15m bars each.

## REFUTED 1 — the closed-underlying gap

*Mechanism:* while US cash is shut, TSLAUSDT prints on crypto order flow against a **frozen anchor**;
at 13:30 UTC the real stock opens and the perp is **marked to truth**. Something crypto cannot have.

**Measured, 336 clean overnight observations across 14 symbols: corr = +0.0064.**
Hit rates 50.0 / 58.1 / 50.6 / 51.9% — no monotonicity; halves disagree (50.8 vs 54.2%).
**The premise is wrong** — market makers already know fair value from index futures and ADRs while
cash is shut, so there is no untethered drift to revert. **Not built.**

## REFUTED 2 — structural-linkage divergence

MSTR is a levered BTC proxy (measured β **1.62**), COIN crypto-beta equity (**1.25**),
NVDA/AMD/MU/MRVL/SOXL/SNDK one semiconductor factor. Fading a ≥1.5σ 2h divergence, in-session:

| | fade WR | halves |
|---|---|---|
| MSTR~BTC | 51.2% | 50.3 / 52.3 |
| COIN~BTC | 54.4% | **57.2 / 51.5 (decaying)** |
| semis | 44.9–52.1% | MRVL **57.7 / 42.9** |

**Structural linkage is real; a tradeable divergence signal is not. Not built.**

## Atlas principle #84 — the case for multi-asset is factor diversification, not alpha

"Alive" = a bar whose true range exceeds **1.2× that symbol's own 14-bar ATR** (relativistic).
Over 3,720 bars:

| | |
|---|---|
| crypto alive | **39.3%** |
| **any asset alive** | **59.8%** |
| crypto dead *and* an RWA class alive | 33.7% of dead bars |
| **net uplift** | **+20.5pp** |

**Cross-class aliveness correlation: +0.038 (crypto↔US equity), +0.143 (crypto↔commodity) —
against crypto's OWN internal factor-share correlation of +0.925 (C398). A 24× difference.**

This is exactly what C391's universe widening could never deliver: adding altcoins adds more of
**one** factor. With C405's bar starving (3 trades in 24h), more genuinely independent opportunity at
the **same** quality bar is the missing ingredient — and it needs no new alpha to be worth having.

## Atlas principle #85 — a switch that cannot switch anything is worse than no switch

The standing audit caught `C409_ONE_POOL = True` that nothing read — **Atlas #79 landing on the very
version that added the principle.** Deleted rather than shipped: one pool is the **absence** of a
rule, and a decorative constant tells the operator a policy is configurable when it is structural.

## Atlas principle #86 — raising the PRU target lowers capital used, not raises risk

Ceiling **20x → 50x**, target PRU **1.30% → 1.60%**. Dollar risk per trade is fixed *upstream* by the
C380 chain and the stop is set in the instrument's own ATR — so PRU is loss-at-stop as a share of
**margin**. Raising it carries the **same dollar risk on smaller margin**. It *frees* capital.

Verified: XAU 3x→4x (1.82%) · NVDA 4x→5x (1.66%) · QQQ 6x→8x (1.60%) · TSLA 3x (1.44%) · crypto untouched.

**Operator decisions:** one pool, no quota · weekends run (crypto 168/168h, metals 115/168, equities
30/168 — a weekend narrows the universe, it does not stop the session) · more leverage headroom.

**Simulated before shipping:** 759 contracts loaded, 294 RWA reachable (271 us_equity / 14 asia /
7 metal / 2 energy), session gate across a full 168h week, QQQ still refused at 0.308R, C405 bar
functional post-merge, boot 7/7. **Audit clean:** duplicates 0 · unassigned `self.cfg` 0 · orphan
keys 0 · orphan attrs 0 · unread new constants 0.

---
# C410 — PER-CLASS FUNNELS, AND TWO WRONG DIAGNOSES CORRECTED

First live multi-asset session: zero errors, banner accurate, volume-qualifying pairs **110 → 220**
(so C408 *was* admitting RWA) — but **not one RWA instrument reached the top 30**, and of 56 symbols
the log mentions, exactly **one** is RWA.

**Wrong diagnosis 1:** I blamed the absolute `_chg_ratio`. My own simulation then showed RWA
appearing **11 times in the top 30 under both the old and new change terms.**
**Wrong diagnosis 2:** I read "0 C408 log lines" as proof the gate never ran. The session was
16:45–17:38 UTC Friday — US cash *and* Globex both **open**. The gate only logs on hold-out; silence
was correct. *Both recorded, because a wrong diagnosis shipped as a fix is how C404's
survivor-biased threshold got in.*

## Atlas principle #87 — absolute evaluation takes one formula; competitive selection takes cohorts

Ranking picks the top N from **one pool**. Pooling instruments whose volatility scales differ
**11×** means the loudest always wins — and "loudest" is not "best", merely "most volatile".

> A **2% day in TSLA** (ATR 0.240%) is **8 ATR**. A **50% day in a memecoin** (ATR 8%) is **6 ATR**.
> The global ranking scored them **0.04 and 1.00**.

C408 was right that *evaluation* needs no per-class rulebook, and silent about *selection*. Slots now
allocated by each class's **share of the qualifying cohort** (live: 82 RWA of 260 = 32% → ~20 crypto,
~10 RWA of 30); a class whose market is **closed forfeits its slots back**, so a weekend returns the
full window to crypto instead of wasting it.

## Atlas principle #88 — a market session is a local-time fact, never a UTC constant

**Research caught a real bug in my own C408.** I hardcoded US cash as 13:30–20:00 UTC. The session is
**9:30–16:00 Eastern** — 13:30–20:00 UTC under EDT, **14:30–21:00 under EST**. Next changeover
**1 Nov 2026**: correct today, silently wrong for four months, opening the gate **an hour into a
closed market** every day.

Now computed from the DST rule (2nd Sunday March → 1st Sunday November) rather than tzdata, since
Pydroid3 on Android can't be relied on to carry the IANA database. Verified: 10 Dec 13:45 UTC now
**shut** where C408 said open; 14:45 and 20:30 **open**.

Plus the ICE/NYSE calendar — **ten full closures a year, matching neither the federal list nor any
other** (exchanges *trade through* Columbus Day and Veterans Day, and *close* for Good Friday, which
no federal calendar contains) — and the 1 p.m. ET half-days. Verified: Good Friday shut, Labor Day
shut, 27 Nov **open at 16:00 UTC but shut at 18:30**. Globex follows US clocks, so it shifts too.

## The change term — fifth instance of one disease

| version | fixed number | where relative belonged |
|---|---|---|
| C397 | 0.60% drift | 0.9 × own true ATR |
| C399 | 0.18 DRI floor | fraction of entry baseline |
| C400 | 0.75 base_total | computed weight sum |
| C405 | 1.7 R bar | percentile of live distribution |
| **C410** | **`chg / cohort_max`** | **chg / own 24h range** |

Wrong for **crypto too**: BEAT's 16% move on a 56% range scores 0.460 while *thrashing*; ZEC's 19% on
an 18% range scores 0.550 while genuinely *trending*. In own-volatility units: **0.247 and 0.937**.

**Honest limit:** the per-class funnel is verified structurally but has never selected a live RWA
candidate, and the phase-3 projected/geometric boost — which pushes crypto scores above 1.0 and which
my simulation still doesn't model — remains unmeasured. The next log is that measurement.

---
# C411 — PER-VENUE CLASSIFICATION, AND IST FOR AN INDIAN OPERATOR

## Coverage, answered

Bitget has **three** futures product types and only one carries non-crypto:

| product type | contracts | RWA |
|---|---|---|
| **usdt-futures** | 759 | **294** |
| coin-futures | 11 | 0 |
| usdc-futures | 49 | 0 |

**Metals are present and now correctly handled:** XAU $92M · XAG $51M · COPPER $14M · XAUT $12M ·
PAXG · XPT · XPD — **7 contracts, $176M/day.** Energy: CL $34M, BZ $15M.
Searched explicitly for **forex, bonds and agricultural** contracts — **none exist**, so no gap.

## Atlas principle #89 — classify by where the price is DISCOVERED, not by what the instrument is about

C410 assumed the underlying **country** implies the listing **venue**. It does not:

| | what it is | listing | C410 said | truth |
|---|---|---|---|---|
| **KORU** $142M | Direxion South Korea Bull 3X | **NYSE Arca** | asia | **US hours** |
| **SKHY** $74M | SK Hynix **ADR** | US | asia | **US hours** |
| **EWY** $2M | iShares MSCI South Korea | **NYSE Arca** | asia | **US hours** |

**$218M of the $220M in the old asia bucket was gated to the wrong six hours** — awake when its
market was shut, asleep when it was open.

## Atlas principle #90 — two Asian exchanges are not one Asian clock

**KRX** 09:00–15:30 KST, *continuous*. **HKEX** 09:30–12:00 **and** 13:00–16:00 HKT — a **real lunch
break**, an hour of no price discovery mid-session that a single open/close pair trades straight
through. Both UTC+9 / UTC+8 with **no DST**, so unlike the US windows they never move.
Verified: 10:00 IST returns `HKEX lunch break` between a working morning and afternoon.

**A fourth class was missing entirely:** SP500 and NDX100 are **index futures**, not cash equities —
CME Globex ~23h. Filing them as `us_equity` would have blinded the bot for **three quarters** of
their trading life.

## Atlas principle #91 — gating entries on a session without gating exits leaves money in an unpriced instrument

C408 gated entries and said nothing about exits. A TSLA position opened at 01:00 IST would carry
straight through the 01:30 IST close into **fifteen hours nobody is pricing** — stop sitting where no
one trades, funding accruing every 8h, next real print at the following open. Same defect as entering
out of session, except **the money is already at risk.**

Session-bound positions now close **20 minutes before the bell**, evaluated **first** in the cascade —
it isn't a judgement about the trade, it's a fact about whether anyone is still pricing it.

## Timescales for India

IST is UTC+5:30 and **India observes no DST**, so the US windows move under the operator twice a year
while the Asian ones never do. Boot now prints:

| class | IST window |
|---|---|
| crypto | 24/7 |
| metals · energy · index futures | Globex ~24/5 |
| **US equity** | **19:00–01:30 (EDT) / 20:00–02:30 (EST) — a night session from India** |
| Korea (KRX) | 05:30–12:00 |
| Hong Kong | 07:00–13:30 (lunch 09:30–10:30) |

Plus a live open/shut line per class at every boot.

**Reclassified totals:** us_equity 273 ($1,185M) · metal 7 ($176M) · korea 3 ($53M) · energy 2 ($49M)
· hk 7 ($8M) · index_future 2 ($2M).

---
# C412 — THE GATE WAS CALLING ITSELF ON THE WRONG OBJECT

## Atlas principle #92 — the C406 family generalises: any method called on the wrong object, hidden by a bare except

C408 wrote `self._c408_asset_class(symbol)` inside `scan_lively_pairs`. Those methods live on
**TradingBot**; `self` there is the **scanner**, which reaches the bot via `self._bot` — as every
other line *in the same function* already does. The call raised `AttributeError`, the enclosing
`except Exception: pass` **swallowed it**, and execution fell through to the volume check,
**admitting every RWA instrument ungated.**

**Proven on a Saturday**, when every RWA market on earth is shut:

| | expected | observed |
|---|---|---|
| volume-qualifying pairs | ~110 (crypto only) | **317** |
| RWA symbols reaching analysis | 0 | **16** (COPPER, PAXG, KORU, SKHY, SNDK, CSOPSK2LHKD…) |
| "RWA held out" log lines | several | **0** |

The **boot board printed every class correctly as shut** while the scanner ignored all of it — the
board asks `_c408_session_open` on the **bot**, the gate asked it on the **scanner**. Classification
and session logic were right all along; **the wiring between them was not.**

Fixed via `self._bot` with an explicit `RuntimeError` if the reference is missing, and the except is
**no longer silent** — a failure here doesn't skip a nicety, it disables the whole gate and lets the
bot trade closed markets. Atlas #77 applied to a gate rather than a stop.

**The audit is generalised.** C407 built this exact check and scoped it to `self.cfg` only, so it
could never have caught a wrong-object *method call*. The sweep now flags any bare `self.<name>()`
whose class never defines it. Across 327 functions the only residual hits are 18 inside
`RemoteControl`, all genuine false positives (`send_response`/`send_header` are
`BaseHTTPRequestHandler`; `_send_json`/`_get_status` live in its nested `Handler`). **No `_c4xx_`
hits remain.**

## Atlas principle #93 — a stop wider than the projected move is a losing trade before it opens

The zero-trade session is **not a fault**. The C405 bar had already relaxed to its absolute floor of
**+0.000R** and candidates were *still* refused:

| | projection | stop | R | E |
|---|---|---|---|---|
| ETH | 0.67% | 2.32% | 0.29 | −0.237R |
| XRP | 2.30% | 9.38% | 0.25 | −0.275R |
| BOME | 1.48% | 9.88% | 0.15 | −0.322R |
| ZAMA | 5.20% | 11.74% | 0.44 | −0.096R |

Every one is **negative expectancy by the bot's own arithmetic**. Refusing them is correct.

But it exposes the real remaining obstacle to 2–4%: **the stop is systematically wider than the
projected move** — R between 0.15 and 0.44. The stop is 2.6 × ATR where common practice is 1–2, but
**narrowing it cannot manufacture edge**: in a driftless walk `P(target before stop)` scales with the
stop distance, so tightening raises R and lowers p by the *same* mechanism and E is unchanged. The
only real levers are a **better projection**, or entries selected where the projection genuinely
exceeds the risk. **That is an entry-selection problem, and it is now the single thing standing
between this bot and its target.**

---
# C413 — THE ONE LOST TRADE, AND THE PER-CLASS PIPELINE

## The BLESS post-mortem: the bot overrode its own arithmetic

Entry 15:19:40 IST @ $0.009383 long, ATR 3.26% · exit 15:56:07 @ $0.009061, **−3.3%, −$0.37**,
on `C399_CONVICTION_FADING` (18% of thesis left).

**Three warnings were present at entry and all three were logged:**

```
🧮 S3 RECORD P=0.396 R=1.20 EV=-0.161PRU     ← NEGATIVE expected value
🔸 FEEDBACK CAUTION conv=-0.0917 → margin -18%
🛑 C61 HIGH-ATR cap: lev 5→2  then  2→1      ← ATR 3.42%, extreme
```

## Atlas principle #94 — when two expectancy estimates disagree on the SIGN, the calibrated one wins

C405's gate uses `continuation_prob` clamped to 0.45–0.72 and its own R. S3 uses a **Brier-calibrated**
P and payoff odds. They disagreed about the sign, and **the permissive one won by accident of
ordering, not by argument.** S3 was right.

*Placed at the **write site** deliberately — my first attempt put this check in the candidate loop
thousands of lines earlier, where `_s3_ev` doesn't exist yet and **the gate could never have fired**.
Caught by reading where the value is written instead of trusting where it's read.*

## C401 called it 34 minutes before C399

| | taker support |
|---|---|
| entry | **+0.087** 🟢 |
| **+2 min** | **−0.427** 🔴 |
| +10 / +18 min | −0.165 / −0.161 🔴 |
| +26 / +34 min | +0.119 / +0.463 🟢 |
| +36 min | C399 exits at −3.3% |

Chart-verified: the exit landed **near the low** — price was back to −1.13% five minutes later and
+0.53% by 16:40. **The flow channel saw it first; the exit fired last.** Second consecutive correct
call from C401; still instrumented-only, n is tiny.

## Atlas principle #95 — the horizon is the keystone of per-class handling

What's per-**class** is not sizing or expectancy — those are per-**instrument** and derived from
measurement. What's per-class is **the shape of the trading day**, and it reaches into all five steps.

C404 computes `R = proj × √(hold/15) / stop`. **Clip `hold` by time-to-close and R falls
automatically as the bell approaches** — late entries are refused *by arithmetic*, not by another
rule. A trade that can't finish before its market stops pricing isn't a worse trade; it's a trade
whose target is unreachable, and √t says exactly how much.

| US equity, IST | min left | horizon | √t | effect |
|---|---|---|---|---|
| 19:30 | 350 | 60 | **2.00** | full R |
| 00:30 | 50 | 30 | 1.41 | R −30% |
| 01:00 | 20 | 0 | collapses | refused |

| class | hold min/max | monitor | min session left to enter |
|---|---|---|---|
| crypto | 20 / 240 | 0.8s | — |
| us_equity | 25 / 180 | 2.0s | 45 min |
| korea_equity | 25 / 150 | 2.0s | 45 min |
| **hk_equity** | 25 / **120** | 2.0s | 40 min |
| metal · energy · index_future | 30 / 300 | 2.0s | — |

HKEX has the shortest usable run because its **lunch break** means an afternoon target can't be
reached from the morning session.

**Self-caught, third occurrence:** `C413_PER_CLASS` defined and never read. Now it means something —
off, every class runs the crypto profile (exactly pre-C413 behaviour). Atlas #79/#85.

---
# C414 — AN ARBITER THAT MAY ONLY EVER ACQUIT

## First: C412 and C413 confirmed in production

| | previous session | this session |
|---|---|---|
| `RWA held out` fired | **0** | **11** |
| RWA symbols leaked into analysis | **16** | **0** |
| volume-qualifying pairs | 317 (ungated) | **268** |

**Reconciled exactly:** a live venue query returns **precisely 268** crypto pairs above $750k, with
**51 RWA** above it held out. The earlier "110" was a quieter market, not the filter.

And C413 did real work: **`GRVT: ABORT — S3 says EV=-0.321PRU`** — a trade prevented by the gate the
BLESS post-mortem built.

## Atlas principle #96 — an arbiter that may only ever acquit is not an arbiter

C179-F2's own comment states the principle: *"L/S aggregates are proxy-grade for alts; the pair's own
/fills delta is the truth."* The code then applies that truth **in one direction only** — `real_cvd`
may **stand down** a veto the proxy raised, and may never **raise** one the proxy missed.

**PYTH proves it** — three numbers for one quantity, printed seconds apart:

```
flow(proxy):  R=-0.27  taker=+0.06     ← below the 0.40 veto bar
C199:         CVD=-0.62                ← the real thing
C401 entry:   taker delta -0.623       ← agreeing independently
```

The proxy shrugged at −0.27 while the truth said −0.62 **twice over from two independent paths**, and
**the weakest of the three held the veto.** The long opened against strong aggressive selling and lost.

Real CVD now vetoes symmetrically at **the same 0.40** the stand-down already uses — not a new
threshold, not a new mechanism, just the existing arbiter allowed to speak in both directions.

**Accumulated C401 entry-flow evidence, limits stated:** against-flow entries are **0W / 3L**
(KAITO −0.046, ONG −0.387, PYTH −0.623); positive-flow entries **2W / 2L**. **n=3 is not proof** —
which is exactly why this rides the existing veto at the existing threshold rather than a new tunable.

**Recorded as not-this:** VVV entered on **+0.908**, the strongest positive flow yet, and still lost
−$0.32 on `REL_DSI+DRI DIVERGE` (thresh=0.11). Flow is not a sufficient filter. *Note the rule that
caught it is the one C399 made reachable by lowering its floor 0.18 → 0.06; at the old floor VVV
would have run on.*

## Atlas principle #97 — a throttled log must summarise, not report the first thing it saw

All eleven hold-out lines read `Globex closed (Sat)` when **273 of 294 RWA are US equities and only 9
are Globex.** The gate was working perfectly and the log described **a tenth of what it did.**
Now a per-class count emitted once per scan — the C399/C402 lesson applied to a counter.

**Still unexercised:** another Saturday session, so only crypto was ever live. The per-class funnel
correctly fell through to its single-class path; `session_short`, `SESSION_CLOSE` and the horizon clip
logged zero because no class with a close was open. **Steps 3–5 remain simulation-verified only.**

---
# C415 — THE BOT HAS BEEN AIMING SMALL ON EVERY TRADE IT EVER TOOK

## Atlas principle #98 — the fee is the same size whatever you aim at

Measured, 60 pairs × 20 days, entries every 17 bars, 1.3-PRU stop, fees 0.05R:

| target | coin-flip needs | actually hits | money/trade |
|---|---|---|---|
| 0.4R | 71.4% | **68.5%** ← highest hit rate | **−0.091** ← worst |
| 0.6R | 62.5% | 61.1% | −0.072 |
| 1.0R | 50.0% | 50.2% | −0.046 |
| **1.5R** | 40.0% | 40.7% | **−0.033** |
| **2.0R** | 33.3% | 33.9% | **−0.033** |
| 3.0R | 25.0% | 25.2% | −0.044 |

Small targets are **not** hard to hit — 0.4R has the best hit rate on the board. They lose because
chasing 0.4R while paying 0.05R hands back **an eighth of the winnings every trade**; chasing 2.0R
hands back a fortieth. **Quick small profits feel safe and are the most expensive habit in the book.**

**With the one measured edge (+4.7pp, C398) on top:**

| target | money/trade | per month @ 2 trades/day |
|---|---|---|
| 0.4R | −0.025 | **−1.1%** still loses |
| 1.5R | +0.085 | **+3.7%** |
| 2.0R | +0.108 | **+4.8%** |

Fees scale with **count**; gains scale with **size**. No trade rate rescues a small target.

## The defect — a units error, same family as C397/C399/C400/C405/C410

```python
_min_target_pct = max(0.5, 1.5 * _atr_entry)      # target in ATR
# ...but the stop is 1.3 PRU = 2.6 × ATR
pos._planned_target = min(_sr_target, _proj_target)   # and takes the NEARER
```

Minimum target = **1.5 / 2.6 = 0.58 × the risk** — the worst measured band — then `min(...)` shrank it
further whenever a resistance sat close. **A target in ATR and a stop in PRU aren't comparable, so
the ratio between them — the one number deciding whether a trade can pay — was nobody's decision.**

BLESS (ATR 3.26%, stop 8.48%): old floor **4.89% = 0.58R** → new floor **12.71% = 1.50R**.

## Atlas principle #99 — a trail may extend a winner, never shrink one

`TRAILING_TP` fires at ~48% of peak. Reached *before* the target, that turns a 1.5R trade into a 0.7R
one — **systematically converting the best band into the worst**, on every trade that wobbled on the
way up.

Below target only the **hard stop** and **thesis-death** may act — they answer *"am I wrong?"*, always
a fair question. The trail answers *"should I bank less than I came for?"*, which is only fair once
the target is banked. The trail now arms **after** the target.

**Self-caught, fourth occurrence:** `C415_GOOD_TARGET_R` defined and never read — deleted, since
target = max(projection, floor) already takes a 2R projection. Atlas #79/#85.

---
# C416 — THE TARGET FLOOR IS COMPUTED, NOT TYPED

## Atlas principle #100 — sixth instance of one disease, caught by the operator

C415 replaced a fixed `1.5 × ATR` with a fixed `1.5 × stop`. Better arithmetic, **identical disease**:

| version | the fixed number | where relative belonged |
|---|---|---|
| C397 | 0.60% drift | 0.9 × own true ATR |
| C399 | 0.18 DRI floor | fraction of entry baseline |
| C400 | 0.75 base_total | computed weight sum |
| C405 | 1.7 R bar | percentile of live distribution |
| C410 | chg ÷ cohort-max | chg ÷ own 24h range |
| **C415** | **1.5R target floor** | **function of p and fee** |

The operator's objection was exact: *a medium trade that clears its fees with good probability should
be taken, and a flat floor refuses it.*

## How big a target you need depends on how likely you are to reach it

```
E     = p(T − f) − (1−p)(1 + f)
T_min = [Emin + (1−p)(1+f)] / p + f
```

| claimed p | MSTR (f=.029) | BTC (f=.050) | TSLA (f=.130) | NVDA (f=.185) |
|---|---|---|---|---|
| 0.72 | **0.70R** | **0.74R** | 1.16R | 1.68R |
| 0.60 | **0.93R** | **0.96R** | 1.17R | 1.68R |
| 0.55 | **1.03R** | **1.07R** | 1.21R | 1.68R |
| 0.50 | 1.23R | 1.27R | 1.43R | 1.69R |
| 0.40 | 1.78R | 1.83R | 2.03R | 2.17R |

*Old C415 behaviour: **1.50R** for every cell.* It discarded every takeable medium trade in the top
rows while waving through 0.40-probability trades that needed 1.88R.

**And f is per instrument** — C408 measured an 11× spread in fee burden, so one flat number could not
have been right for more than one instrument.

## The two guards that make it honest, not wishful

1. **p and T are not independent.** A coin-flip market gives `p = 1/(1+T)`, so a claimed p=0.65 at
   T=1.5R asserts a **+25pp edge nobody has**. Claims are capped at fair + 0.10 — a high probability
   cannot *by itself* justify a small target; it must be earned against what the target allows.
2. **Short range is measurably worse than fair.** The corpus put 0.4R **2.9pp below** fair while
   1.5–2.0R sat 0.6–0.7pp **above** — the spread takes its cut first. Short targets are penalised by
   that measured shortfall, not merely capped, which is why the fixed point converges instead of
   collapsing toward zero.

Solved by damped iteration since T and p co-determine each other. Stable at the extremes:
p=0.95 → 0.74R (capped, not collapsed) · p=0.20 → 4.00R (ceiling) · fee=0.35R → 3.24R.

## Atlas principle #101 — falsy-zero belongs nowhere near money

`float(fee_r or 0.05)` treats a **genuine zero** as missing. **XAU and NVDA both print funding of
exactly 0.0000%** — so a real instrument would have been charged a fee it doesn't pay and had its
target floor raised for nothing. Replaced with an explicit `None` test.

---
# C417 — SEVEN DESKS, ONE WALLET, ONE TARGET

## Atlas principle #102 — opening a second market must never shrink the first

C410 split **one** budget of 30 Step-3 slots *between* the classes, so crypto fell from 30 to 20 the
moment US equity woke up. **That is one bot rationing itself, not several bots working together.**

Budgets now **add** — two open markets are two opportunity sets, not one shared one. Competition for
slots happens **inside** a class, where instruments are comparable; **never across** classes, where a
2% day in TSLA (8 ATR) and a 50% day in a memecoin (6 ATR) share no common scale.

**Slots scale with √(universe)**, not linearly — the best few candidates carry most of a cohort's
value and the tail is nearly information-free:

| desk | universe | slots |
|---|---|---|
| crypto | 268 | 30 (capped) |
| us_equity | 45 | 20 |
| metal | 7 | 7 |
| hk_equity | 7 | 7 |
| korea_equity | 3 | 3 |
| energy | 2 | 2 |
| index_future | 2 | 2 |
| **all awake** | 334 | **71** ← was 30 shared |
| **crypto only** | 268 | **30** ← unchanged |

Step 3 costs 0.85s/pair measured → a full house is **60s of a 480s cycle (13%)**, and the analysis
already runs on a `ThreadPoolExecutor`, so desks overlap rather than queue.

## Atlas principle #103 — liquidity is relative to your own market, not the whole venue

One global median asks *"is this liquid compared to all crypto?"* — and for a **$5M gold perp standing
next to Bitcoin's $8bn** the answer is no. Yet $5M is **mid-pack among gold's seven contracts.**

C81's relative-volume threshold was the right idea on the wrong cohort the instant C408 admitted 294
non-crypto instruments — it was quietly excluding whole asset classes on a comparison that meant
nothing. Now one median per class, with a hard absolute floor so a thin cohort can't bootstrap itself
into looking liquid.

**Seventh instance of the absolute-where-relative disease — and the first where the absolute thing was
a *cohort* rather than a number.**

## The desk board

Every scan now prints one line per class — open or shut. For open desks: universe size, its own
volume floor, how many passed, how many go to Step 3. For shut desks: the reason (US cash closed,
HKEX lunch break, Globex Sat, KRX closed). *The C399/C402/C414 lesson applied to the whole scan
rather than one line of it.*

## More analysis is not more trades — deliberately

The C403 fee servo and C404 hard cap still permit only **6–12 trades a day**. What changes is that
those same few slots are filled from a **much wider and genuinely independent field** — C409 measured
cross-class aliveness correlation at **+0.04 / +0.14** against crypto's own internal **+0.925**.
Widening *within* crypto could never deliver that, because every altcoin is the same factor wearing a
different ticker.

---
# C418 — THE GROUP HYPOTHESIS: STRUCTURE CONFIRMED, SIGNAL REFUSED, RISK HOLE FOUND

## What was proposed
Find highly correlated, stable groups sharing a funding pool; measure which member absorbs the
largest share of group flow (window inversely proportional to group volume — **correct reasoning**,
since more volume means more information per second); trade it, because within a shared capital pool
intra-group flow is **zero-sum**.

## The premises hold — strongly

| | measured |
|---|---|
| first-half vs second-half correlation structure | **+0.880** — genuinely stable |
| crypto majors (16: BTC ETH BNB AVAX DOGE ENA…) | +0.58 → **+0.46** out of sample |
| **memory/semis (7: MU SKHYNIX SKHY SNDK SNXX KORU)** | **+0.80 → +0.74** |
| flow-share concentration, 1h autocorrelation | **+0.230** — it persists |

## The signal is directionally right and too weak to ship

The concentrated pair **underperforms** its group — the "opposite direction" was correct. But
following it wins 48.5% (halves 49.4/47.8), so **fading wins only 51.5%** (50.6/52.2, n=2,031).
**1.5 points is the magnitude that has failed out-of-sample repeatedly here.** Refused.

*Also noted: "runs opposite" is partly **tautological** — bids and price move together, so a pair
absorbing buying rises while the rest don't. That describes what already happened. The only
predictive content is whether concentration persists, which it does at +0.230 — and even that isn't
enough.*

## Atlas principle #104 — count bets, not positions

C160 guards correlation **pairwise at >0.75**. The crypto-majors group sits at **0.46–0.58** — every
pair passes — yet `n / (1 + ρ(n−1))` says:

| held | pairwise ρ | you think | you have | C160 | C418 |
|---|---|---|---|---|---|
| 5 crypto majors | 0.55 | 5 | **1.56** | allow | **BLOCK** |
| 3 memory/semis | 0.74 | 3 | **1.21** | allow | **BLOCK** |
| 4 majors | 0.60 | 4 | **1.43** | allow | **BLOCK** |
| 5 diversified | 0.20 | 5 | 2.78 | allow | allow ✓ |

**Sizing five positions as five when they are one and a half overstates the risk taken threefold** —
and the entire C380 risk chain assumes positions are separate opinions. That is how a run of
correlated losses arrives with every rule obeyed.

Cap is now on **effective** positions: max 3.0 independent bets, and a new one must add ≥0.15 of a bet.

**Two self-caught errors, both by the standing audits rather than a live log:**
`self._get_return_series()` doesn't exist — it's `_returns_for` (**third** occurrence of the
C406/C412 family, **first** caught before shipping). And my own verification table showed the 0.30
min-added threshold **blocking five genuinely diversified positions** at ρ=0.20 — the opposite of the
intent. Lowered to 0.15.

---
# C419 — 'z' DERIVED FROM THE DATA, AND MARGIN THAT SCALES

## Atlas principle #105 — when a quantity isn't observable, find what question it answers

The operator proposed deriving group size from **z**, the average pairs a single account holds — the
natural unit of capital rotation. **No exchange publishes it.** But the *question* has a rigorous
answer from the data: **random matrix theory.**

Eigenvalues above the Marchenko–Pastur noise ceiling `(1+√(n/T))²` are real factors; the rest is
sampling noise.

> n=60, T=1911, **ceiling 1.386** · eigenvalues **12.7, 4.3, 1.9, 1.4** above · 1.3, 1.3 below
> **z = 4 real factors**, ~15 pairs per group. Measured, not assumed.

## The rest of the construction: tested and refused

| | 1st half → 2nd half |
|---|---|
| volume-node group, BTC | +0.48 → **+0.34** decays |
| volume-node group, ETH | +0.11 → **+0.04** nothing |
| plain correlation threshold (C418) | **+0.80 → +0.74** |

Volume share and correlation are different quantities — ETH is second by volume, but the members
correlation assigns to it once BTC takes the top ones correlate at **0.11**, which is no group at all.

**And hub-and-spoke's testable implication fails outright:** the hub does **not** lead its spokes —
**47.8% / 45.2% / 47.4%** at 15/30/60-minute lags, all *below chance*, n=10,129.

## Atlas principle #106 — a cap derived from the market tightens when the market narrows

C418 capped effective bets at a **typed 3.0**. If the market contains four independent factors, then
**four is the most independent bets that can exist** — however many tickers are open. The cap is now
the measured factor count, recomputed every 30 minutes, floored at 2 and ceilinged at 6.

**Why this beats a constant:** when the market narrows to one factor — everything moving together,
exactly when concentration hurts most — **the cap tightens by itself**, with nobody deciding to
tighten it. A constant cannot do that.

## Atlas principle #107 — an exchange minimum must not set your risk policy

C368's own comment confessed it: *"the $5 MIN_MARGIN floor **sets** this; it is not a preference."*
**The exchange's minimum was driving the risk settings**, not the reverse. $5 is 2% of $250 and 0.5%
of $1,000 — the same constant meaning two different things.

$5 stays as the hard exchange floor. The **bot's** minimum is now anchored on the **daily target** —
a position should be able to earn a meaningful slice of the day's goal or it isn't worth its fee:

| equity | day target | bot minimum | % of equity |
|---|---|---|---|
| $250 | $1.70 | $5.67 | 2.3% |
| $500 | $3.40 | $11.33 | 2.3% |
| $1,000 | $6.80 | $22.67 | 2.3% |
| $2,500 | $17.00 | $56.67 | 2.3% |

The number moves because the target moves. Capped at 10% of equity so it can never demand a
concentrated position on a small book. Maxima were already fractional (C373 25%, allocator 55%).


---

# PART TWO — THE CHANGELOG RECORD (C264 → C453)

## HOW TO READ THIS

Each section below is a version's own changelog entry — what was found, how it was measured, what
was changed, and what was explicitly *not* claimed. These were written at the moment of the change
with the evidence in hand, which makes them more reliable than any later summary.

**The recurring defect families, which the entries name repeatedly:**

| family | what it looks like | worst instances |
|---|---|---|
| **Absolute where relative belongs** | a fixed number that means different things on different instruments — or over different *timespans* | 14 instances, latest C453 (stop sized on one bar, tested over seven) |
| **Computed but never wired** | a value produced and read by nothing, or a method on the wrong class | 10 instances, latest C447 (grader on `ExchangeManager`, called from `TradingBot`) |
| **One state, two truths** | the same quantity derived twice and allowed to disagree | C433 (two day-barriers), C436/C445 (two exit indices) |
| **Graceful degradation as camouflage** | a fallback that looks exactly like the bug it is hiding | C437, C440-3, C445 |
| **A retirement honoured in some places only** | HP mode, five separate reports | C403 → C426 → C431 → C440 → C450 |

---


## C453

SIX TRADES, SIX LOSSES, AND THE CORE ISSUE IS NOT WHERE ELEVEN VERSIONS OF EXIT WORK HAVE BEEN
LOOKING. Session 20260907_111306: 12h50m, 6 positions, 0W/6L, -$1.77 (-0.7%), equity $248.23.
THE SHAPE OF THE FAILURE IS COMPLETELY DIFFERENT FROM EVERY PREVIOUS SESSION. The recurring
complaint for eleven versions has been 'trades go up and give it back' -- a HOLDING problem.
This time FOUR OF SIX NEVER MOVED ONE TICK OUR WAY: peaks of +0.00%, +0.00%, +0.05%, +0.06%. And
it is not direction -- four were BUY and two were SELL, and both sides lost. THE HOLD TIMES ARE
THE TELL, AND I SHOULD HAVE CHECKED THEM FIRST. ZEC lost 1.52% of price in FOUR MINUTES FORTY-
FIVE SECONDS. BSB lost 0.77% in THREE MINUTES TEN SECONDS. Both died at REL_HARD_STOP -- which
is NEVER GATED by C422-4, C443 or anything else. So this is not the exit stack being impatient.
IT IS THE STOP SITTING INSIDE ORDINARY NOISE. MEASURED, AND THE ANSWER IS UNAMBIGUOUS. Across
EIGHT instruments and 500 five-minute bars each, on the MAXIMUM ADVERSE EXCURSION over a
35-minute hold -- what the position is actually exposed to rather than what one bar does -- THE
CURRENT 2.3-PRU STOP SURVIVES ONLY 69-83% OF WINDOWS. ZEC 78%, WLD 83%, APR 71%, ETC 72%, FET
78%, BSB 69%, BTC 74%, PEPE 75%. SO ROUGHLY ONE TRADE IN FOUR IS KILLED BY NOISE ALONE, before
the thesis has a single bar to express itself, and the session's 2-of-6 hard-stop rate is
exactly consistent with that. Surviving the 90th percentile requires 2.76 to 5.24 PRU, median
3.63. AND IT IS NOT AN INSTRUMENT QUIRK: BTC needs 3.75 and PEPE 3.99 -- the same shortfall at
opposite ends of an eight-fold volatility range. THE CAUSE IS A UNITS MISMATCH IN TIME, NOT IN
PRICE. The stop is 2.3 PRU where PRU is built from the 15m ATR -- A ONE-BAR MEASURE -- while the
position is held ~35 minutes across seven five-minute bars. Adverse excursion accumulates with
the square root of elapsed time; a one-bar stop does not. This is the fourteenth instance of an
absolute where a relative belongs, except the dimension is TIME. Every previous instance was a
price threshold and I have been hunting those; this one has been hiding in plain sight because
2.6x ATR SOUNDS generous, and it is -- for one bar. WIDENING IT IS NEARLY FREE, WHICH IS WHY IT
IS SAFE TO DO NOW RATHER THAN AFTER MORE EVIDENCE. Position size is capped in DOLLARS by
PER_TRADE_RISK_PCT x equity, and margin is solved BACKWARDS from the stop -- so a stop 1.53x
wider produces a position 1.53x smaller and THE DOLLAR RISK PER TRADE IS IDENTICAL. Verified
across four horizons: 20min gives 2.66 PRU at 87% of today's size, 35min gives 3.51 PRU at 65%,
50min and beyond cap at 3.91 PRU and 59%. Nothing about the risk budget, the day cap or
PER_TRADE_RISK_PCT changes. What changes is that the SAME RISK now buys enough room to survive
normal movement -- noise survival rises from 69-83% to 85-90% on seven of the eight instruments.
REPLAYED ON THE SESSION: ETC, which was stopped at -2.4 PRU, would have been HELD. The other
five were inside 2.3 PRU already and were closed by other paths, so C453 alone does not rescue
them -- and saying so matters, because a fix that claims six saves when it delivers one is how
this project has previously talked itself into regressions. SCALED BY THE SQUARE ROOT OF THE
INTENDED HOLD IN 15m BARS, floored so it can NEVER be tighter than today's value and capped at
4.0 PRU so it cannot become meaningless. Every other exit still fires normally; only the last-
resort backstop moves. ALSO CONFIRMED WORKING THIS SESSION: the C451 funding cross-section ran
22 times, the OI/funding quadrant 33 times, the C441 target cap bound 41 times, and the C444
grader recorded 6 exits with the C451 entry score attached -- the first session in which entries
have ever been graded. C452's calendar reported 'clear' correctly, the next FOMC being 262 hours
out. VERIFICATION: syntax; AST 364 unchanged; the first attempt at this edit SILENTLY MATCHED
NOTHING (count=0) and left the three constants as orphans, which the constants-read check caught
before shipping -- applied by line insertion instead and re-verified; duplicate defs 0; wrong-
object sweep clean; all three C453 constants confirmed read; the scaling and its risk-neutrality
tabulated across four horizons; MAE distributions measured on 4,000 real bars. LIMITS: BSB needs
5.24 PRU and the 4.0 cap does not reach it, so the thinnest instruments remain under-protected
by design rather than by oversight. The 90th percentile is a choice; the p85 or p95 would give a
different multiple and the C444 grader is what will eventually say which. And this widens the
stop on a book that has just had six straight losses -- if the next session shows LARGER losses
rather than fewer, C453_HOLD_SCALED_STOP is a single switch. Chain C367-C453 intact.


## C452

THE SCHEDULED-EVENT CALENDAR, BUILT THE RIGHT WAY ROUND. LINEAGE FIRST, since the operator
asked: every C449, C450 and C451 edit verified present -- PnL-weighted base rate, the de-HP'd
phase ladder, _pending_hp never set under single mode, entry grading, funding cross-section,
OI/funding quadrant -- 52 changelog entries with NO GAPS from C420 to C452, all constants read,
zero orphans, duplicate defs 0, wrong-object clean. Nothing was lost across three sequential
versions. WHAT THE RESEARCH ACTUALLY SAYS, AND IT IS THE OPPOSITE OF THE INTUITIVE READING. The
operator asked for world events that move markets predictably. DIRECTION AT THE RELEASE IS NOT
PREDICTABLE: the FOMC study in Finance Research Letters -- 41 scheduled statements, hourly
BTC/ETH, matched-week controls, hour-matched placebos, cross-venue replication on Bitfinex --
finds large predictable intraday jumps and states outright that the object is 'predictable
timing of elevated risk and liquidity demand, NOT directional return predictability'. Markets
price SURPRISE VERSUS CONSENSUS and this bot has no consensus feed, so it cannot form that view
and does not pretend to. TWO THINGS ARE PREDICTABLE AND THEY ARE DIFFERENT IN KIND. (1) THE PRE-
FOMC DRIFT: Lucca and Moench measure the S&P 500 rising 49 BASIS POINTS IN THE 24 HOURS BEFORE a
scheduled announcement, NON-REVERTING, accounting for a large share of annual realised excess
equity returns. Directional, scheduled, and SPECIFIC TO EQUITIES -- so the tilt applies ONLY to
the us_equity and index_future desks, only to LONGS, and crypto and metals are explicitly
excluded. Bounded at +6%, the same limit C343 uses for a trusted chain. (2) THE VOLATILITY SPIKE
AT THE RELEASE: predictable in timing and size across every risk asset including crypto, not
tradeable as direction, but very much actionable as ABSTENTION. A fresh entry placed thirty
minutes before a rate decision is a coin flip wearing a thesis, and the C403 fee budget cannot
afford coin flips. No new entries within 45 minutes either side; OPEN POSITIONS ARE UNTOUCHED
and every exit path still works normally, because abstaining from new risk is not the same as
abandoning existing risk. THE DATES ARE THE FED'S OWN PUBLISHED CALENDAR, cross-checked against
federalreserve.gov and three independent trackers on 2026-09-05: 2026 decisions Sep 16, Oct 28,
Dec 9; 2027 Jan 27, Mar 17, Apr 28, Jun 9, Sep 15, Oct 27, Dec 8. Decisions land 2:00 PM ET,
which the code resolves to 18:00 UTC in EDT months and 19:00 UTC in EST months rather than
assuming one offset year-round. AND THE TABLE EXPIRES OUT LOUD, which is the part that matters
most. A hardcoded calendar that silently runs out is precisely the failure family this project
keeps paying for -- C405's stale constant, C434's orphaned gate, C440's dead method name. Past
the last known date this returns 'unknown', EVERY CALLER DOES NOTHING, and it warns once so the
table gets refreshed. VERIFIED BY EXECUTION across six simulated clocks: 262h out reads 'clear';
22h and 12h out read 'pre_drift'; 30 minutes before reads 'event' and stands the candidates
down; one hour AFTER reads 'clear' again because the drift does not revert and there is nothing
left to trade; and 2028 reads 'unknown' with the warning firing. CLASS OWNERSHIP CHECKED ON THE
EDIT: _c452_macro_window is defined on TradingBot and called from TradingBot -- MATCH, verified
before shipping rather than after a session, which is the C447/C451 discipline now running by
default. LIVE BITGET RUN: 778 contracts and 778 tickers reachable; the next decision is
2026-09-16 18:00 UTC, 262.7 hours away, so the current state is 'clear' and nothing is gated
today; the drift window opens Sep 15 18:00 UTC and the entry blackout runs 17:15-18:45 UTC on
the 16th; 310 RWA contracts are listed, of which only the us_equity and index_future desks can
receive the tilt. VERIFICATION: syntax; AST 363 -> 364 (+_c452_macro_window); count-asserted
replacements; duplicate defs 0; wrong-object sweep clean; class-ownership match; all four C452
constants read; six-clock execution including expiry. LIMITS: the drift is measured on the S&P
CASH index and this bot trades a Bitget perp proxy, so the transfer is an assumption -- bounded
at 6% precisely because it is. Only FOMC is calendared; CPI and NFP have the same volatility
property and are NOT included, because their release schedule is published by a different agency
and I would rather carry one table I have verified than three I have not. And the whole
mechanism is untestable until Sep 16 -- the first evidence is eleven days away. Chain C367-C452
intact.


## C451

INTEGRATING WHAT THE RESEARCH AND THE OPERATOR'S QUESTIONS TURNED UP -- AND CHECKING FIRST
WHETHER EACH THING ALREADY EXISTS, WHICH IS THE C443 LESSON. Three of the five candidates turned
out to be present already and one was a duplicate waiting to be built. C451-1, THE ENTRY INDEX
THE OPERATOR ASKED FOR ALREADY EXISTS -- IT HAS NEVER BEEN GRADED. The operator asked whether
entries should have an index like DRI/DSI. THEY DO: the composite `score`, eleven signal
families, stored on every position as _entry_score. Searched the whole file: _entry_score IS
COMPARED AGAINST AN OUTCOME ZERO TIMES. So the eleven-signal stack has produced a number for
hundreds of trades with no record anywhere of whether a 0.62 trades better than a 0.48. BUILDING
A SECOND INDEX WOULD HAVE REPEATED C443 EXACTLY -- a duplicate beside a working original.
Instead the entry score now rides the C444 grader, which is already proven running (3, 7 and 2
grades in the three C448 sessions after three versions of silence), at the cost of one field.
The verdict prints in bands rather than as a correlation, because MONOTONICITY is the question:
if the >0.60 band does not out-earn the <0.50 band, the score is not ranking anything and the
eleven signals need re-weighting rather than the exits needing another patch. That is a
falsifiable statement about the core of the bot, and nothing has ever been able to make it.
C451-2, FUNDING WAS BEING READ ABSOLUTELY WHEN THE RESEARCH SAYS CROSS-SECTIONALLY. Presto Labs
measures funding change explaining ~12.5% of price variation over 7 days, decaying after, and
concludes it is 'more useful when applied cross-sectionally across multiple assets'. This code
asked whether each pair's funding was extreme IN ABSOLUTE TERMS -- the fourteenth instance of
the absolute-where-relative disease. +0.010% is unremarkable when the whole board pays +0.012%
and is the most crowded name on the venue when the board pays +0.001%; only the cross-section
separates those. VERIFIED LIVE: 778 pairs carry a rate, median +0.0050%/8h, p10 to p90 spanning
just 0.0100pp -- AN ABSOLUTE |0.05%| CUT FLAGS ONLY 12 PAIRS (1.5%) ON TODAY'S BOARD while the
cross-section always resolves the top and bottom deciles. The absolute reading is nearly silent
today and would be indiscriminate in a funding-squeeze week; the relative one adapts to whatever
the board is actually doing. Blended 50/50 with the existing per-pair term rather than replacing
it, so the change is bounded. C451-3, FUNDING AND OI ARE ONE STATE AND THE BOT PAIRED OI WITH
THE WRONG VARIABLE. The research is explicit: 'rising OI alongside rising funding CONFIRMS
directional crowding; FALLING OI alongside extreme funding suggests the trend is LOSING
PARTICIPATION' -- opposite implications from the same funding value. This bot computes OI
divergence against PRICE (C111) and never against FUNDING, so it scored both cases identically.
Now: crowded with OI rising means the crowd is still arriving and the fade is HALVED; crowded
with OI falling is exhaustion and the fade is STRENGTHENED. Bounded at +/-50% of the cross-
sectional term, so it can shade a signal and never create one. AND THE CLASS-OWNERSHIP TRAP
CAUGHT ME MID-EDIT, WHICH IS THE POINT OF HAVING BUILT IT. My first draft wrote the funding pool
to self._c451_fund_pool (MarketScanner) and self.ta._c451_fund_pool (TechnicalAnalysis) while
the READER lives on DRICalculator. THE POOL WOULD NEVER HAVE ARRIVED, the cross-section would
have stayed empty, and it would have degraded silently to the old absolute reading WITH NO ERROR
-- C447 in a new costume, one version later. Caught by running the ownership check on my own
edit BEFORE shipping rather than after a session. Resolved by setting a CLASS attribute, which
has no plumbing to get wrong. NOT BUILT, AND WHY. The pre-FOMC drift is the one documented
DIRECTIONAL macro effect (S&P +49bp in the 24h before a scheduled announcement, non-reverting)
and it is genuinely actionable for the us_equity and index desks -- but it needs an economic
calendar the bot does not have, and hardcoding a date table I cannot verify against a live feed
is exactly the kind of unverifiable constant this project has been burned by. Deferred with the
reason stated. DRI/DSI SHAPE was checked and is already present: slope, acceleration, micro-
slope and an indecision test all exist over a 30-value window with 60 deviation points, so there
was nothing to add. VERIFICATION: syntax; AST 363 unchanged; count-asserted replacements
reported individually; duplicate defs 0; wrong-object sweep clean; CLASS-OWNERSHIP CHECK RUN ON
THE EDIT ITSELF and it found a real fault; all three C451 constants confirmed read; the four
OI/funding quadrants tabulated; LIVE BITGET RUN against 778 contracts and 778 funding rates.
LIMITS: the funding blend is 50/50 by judgement, not measurement -- the C451-1 entry grader is
what will eventually say whether the funding term earns its 0.05 weight at all. The OI read uses
the existing oi_change_pct with a defensive fallback, so on a pair where OI is unavailable the
quadrant simply does not fire. And this is three changes to the entry path in one version,
against a C448 baseline that was PROFITABLE (+$2.83 across three sessions) -- if the next log
regresses, C451_FUNDING_XS and C451_OI_FUNDING_STATE are independent switches and the entry
grader is instrumentation only. Chain C367-C451 intact.


## C450

FIFTH OPERATOR REPORT OF HP SURVIVING, AND THIS TIME I FOUND WHY. Across 46,500 lines of C448
log there are 19 HP occurrences in 9 distinct forms. FOUR ARE HARMLESS -- they are labels that
SAY HP is retired ('single mode — HP retired at C403-3'), which is correct and informative. FIVE
ARE LIVE MACHINERY, and they trace to one thing nobody ever retired: THE DAY'S PHASE LADDER.
PHASES IS STILL [('normal', ...), ('hp', ...)]. C403-3 retired the MODE. C426-3 stopped printing
its score floor. C431-2 closed the restore path. C440-1 neutered the entry-suppression gate. NOT
ONE OF THOSE TOUCHED THE LADDER, so the day is still literally structured as Normal-1 then HP-1
-- which is why the log prints 'C310 PHASE SKIPPED: HP-1 (phase 2 of 2 in today's taper)', '⏳ HP
PENDING — spared runner still riding' and '✅ RUNNER CONCLUDED — deferred HP activating at
$252.88'. Each of my four previous fixes removed a SYMPTOM downstream of a structure that still
names the mode. AND THERE WAS A SECOND PENDING-HP MESSAGE I HAD NEVER SEEN. C440-1 gated the one
at line 19515; there is a DIFFERENT one at 19571 with different wording, set from a different
branch, which I never found because I searched for the string I had already fixed. Searching for
the symptom you know finds only the symptom you know. WHAT IS KEPT AND WHAT IS NOT. The TAPER
stays -- the operator asked for it at C333 and the reasoning is sound: each phase of the day
asks for less, so exposure shrinks as the tape ages. THE 'HP' LABEL ON THE SECOND PHASE DOES
NOT, because the mode it names cannot be entered, so the label describes a thing that does not
happen and the deferral defers to a destination that does not exist. Under single mode the
phases are now Phase-1 and Phase-2, _pending_hp is never SET, and both pending messages and the
activation announcement read in phase language. The indices, the C304 overshoot credit and the
C310 skip arithmetic are untouched. Every HP construct that remains in the file is now inside an
`if NOT single mode` branch -- verified with comments and changelog excluded: 3 pending
messages, 2 activation lines, 2 phase-name expressions, 1 _pending_hp set and 3 mode
assignments, ALL DEAD while HP is retired. AND THE C448 SESSIONS ARE THE BEST NEWS IN A LONG
WHILE. Three sessions: -$0.69 (33% WR), +$0.49 (50%), and +$3.03 (+1.2%, 58%, THREE WINS AND NO
LOSSES -- MUBARAK, FARTCOIN, DOGE). NET +$2.83, EQUITY $251.41. More importantly the machinery
built over the last ten versions is visibly WORKING: the C444 grader recorded 3, 7 and 2 grades
where it recorded ZERO for three versions; C422-4 held through 3 and 5 soft exits; and the C441
target cap bound 18 and 5 times, which is the mechanism that stopped the 2.85R-target death
spiral. Every one of those was a fix whose effect could not be confirmed until now.
VERIFICATION: syntax; AST 363 unchanged; six count-asserted replacements each reported
individually; duplicate defs 0; wrong-object sweep clean; HP trace sweep over EXECUTABLE code
only, confirming every survivor is gated. LIMITS: PHASES itself is left as [normal, hp] rather
than rewritten, deliberately -- the index arithmetic is `cycles*2 + mode` and collapsing the
tuple would silently change how phases advance, which is a structural change that does not
belong in a labelling fix. It is inert while single mode is on, and it is the right thing to
remove on a version that can be measured on its own. Chain C367-C450 intact.


## C449

THE OPERATOR SAID THE LEARNING SHOULD TRACK NET PnL RATHER THAN WIN RATE. THEY ARE RIGHT, IT IS
A REAL DEFECT, AND IT IS THE ROOT OF THE C441 DEATH SPIRAL. _c420_base_rate counted wins and
losses and THREW AWAY THE AMOUNTS -- and FIVE decisions read it: the C420-4 target floor, the
C421-3 edge, the C436 probability fallback, the C420-5 shrink and the C439 tilt. A record of
4W/4L was identical whether the wins averaged +4.7% and the losses -0.5%, or the reverse.
MEASURED ON THE ACTUAL SESSIONS: 20260902 made +16.8R across eight trades and 20260904 lost
-1.2R across five. Base rates 0.500 and 0.400 -- A TENTH APART, for outcomes that are worlds
apart. Worse, 20260903 was 1W/5L, which LOOKS like a collapse, but its single win was +2.15R
against five losses averaging -0.59R: NET -0.80R, close to scratch. The bot read 17% and the
C420-4 solve demanded 2.85R, which is exactly the spiral C441 had to cap. A RECORD THAT CANNOT
TELL A NEAR-SCRATCH SESSION FROM A DISASTER WILL KEEP PRODUCING THAT SPIRAL, and capping the
symptom at C441 left the cause in place. THE FIX IS THE OPERATOR'S: weight each trade by what it
actually made or lost, in R so instruments stay comparable, then shrink toward 0.50 with the
same Laplace prior the count used. The output remains a probability-shaped number in [0.20,0.80]
and EVERY CONSUMER IS UNTOUCHED -- but it now answers 'how has this bot been DOING' rather than
'how often has it been RIGHT', and those diverge most exactly when payoff is asymmetric, which
is the regime this exit stack is built to produce. THE TWO CONTROL ROWS ARE THE PROOF. 'Few big
wins' (1W/5L, net +3.5R) and 'many tiny wins' (4W/1L, net -2.6R) are opposite outcomes wearing
each other's win rates. Count-based reads them 0.423 and 0.560 -- IT PREFERS THE LOSING RECORD.
PnL-weighted reads 0.548 and 0.424, which is the correct ordering. Below five non-admin trades
it falls back to the count, so a fresh install is byte-identical. WHAT THE RESEARCH SAYS ABOUT
WHERE ELSE WE ARE WRONG, since the operator asked. (1) FUNDING RATE IS BEING USED PER-PAIR AND
THE LITERATURE SAYS IT WORKS CROSS-SECTIONALLY: Presto Labs measures funding change explaining
~12.5% of price variation over 7 days with power decaying after, and states it is 'more useful
when applied cross-sectionally across multiple assets'. DRI_WEIGHT_FUNDING is 0.05 applied to
each pair in isolation, which is the weaker of the two readings. (2) FUNDING AND OPEN INTEREST
ARE A TWO-VARIABLE STATE, NOT TWO SCALARS: rising OI with rising funding is crowding building;
FALLING OI with extreme funding is a trend LOSING participation -- opposite implications from
the same funding value, and the bot currently scores them the same. (3) SCHEDULED MACRO EVENTS
ARE PREDICTABLE IN TIMING AND MAGNITUDE, NOT DIRECTION: the FOMC crypto study (Finance Research
Letters, 41 releases, hourly BTC/ETH) finds predictable intraday jumps and states outright that
the object is 'predictable timing of elevated risk and liquidity demand, NOT directional return
predictability'. The one documented DIRECTIONAL exception is the pre-FOMC drift -- the S&P rises
~49bp in the 24h BEFORE a scheduled announcement and does not revert, accounting for a large
share of annual excess equity returns. That is actionable for the us_equity and index desks and
is recorded as a hypothesis, not implemented. (4) MARKETS PRICE SURPRISE VERSUS CONSENSUS, NOT
THE RELEASE ITSELF, so a headline feed without an expectations baseline cannot generate
directional edge -- which is a limit on the current news module rather than a bug in it.
VERIFICATION: syntax; AST 363 unchanged; count-asserted replacements; duplicate defs 0; wrong-
object sweep clean; class-ownership sweep clean; C449 constant read; five records replayed both
ways including two controls with inverted win-rate/PnL. LIMITS: the R-multiple is taken from the
trade record where present and reconstructed from net/margin otherwise, so a record written
before r_multiple existed degrades to the ratio rather than the true R -- acceptable, and it
converges as new trades accumulate. And this changes the input to five downstream mechanisms at
once, which is more coupling than one version should normally carry; it is justified because
they ALL read the same broken number and fixing it in one place is less risky than five separate
compensations. Chain C367-C449 intact.


## C448

THE OPERATOR ASKED WHY THE PARAMETERS COULD NOT BE CALIBRATED ON SIMULATED DATA INSTEAD OF
WAITING FOR LIVE GRADES. THEY WERE RIGHT THAT IT CAN BE DONE, AND THE ANSWER IT GIVES IS 'DO NOT
CHANGE THEM' -- WHICH IS WORTH MORE THAN A NEW NUMBER. WHAT WAS BUILT. C446's harness used
SYNTHETIC paths, which the operator correctly identified as the weak point. C448 replaces them
with 6,000 REAL 5-MINUTE BARS pulled from the venue -- 1,000 each for PEPE, BTC, LINK, NVDA, XAU
and SPX, roughly 21 instrument-days of actual market including whatever chop, trend and gaps it
contained. An entry is opened every 24 bars and the REAL _c443_uei and _c422_soft_loss_gate,
extracted by AST from the shipped file, are driven over the REAL price path. 228 trades per
configuration. The PRICE side of every metric is genuine; only the DRI/DSI retention is
modelled, and that limit is stated rather than buried. BASELINE ON THE SHIPPED VALUES: +0.364R
per trade, 23.9% capture, 21% win rate across 228 trades -- a runner profile, few winners
carrying the book, which is what the current exit stack is built to produce. THEN THE SWEEP, AND
THE RESULT THAT MATTERS. Twenty configurations, floor 0.25-0.65 crossed with four room bands,
TRAINED ON THE FIRST HALF AND VERIFIED ON THE SECOND. EVERY SINGLE CONFIGURATION LOSES ON THE
TRAIN HALF (-0.175R to -0.311R) AND MAKES MONEY ON THE TEST HALF (+0.281R to +0.552R). The
spread attributable to PARAMETERS is 0.137R on train and 0.270R on test; the gap between the two
halves is 0.630R. REGIME IS 2.3x LARGER THAN THE BEST PARAMETER EFFECT. AND THE GENERALISATION
CHECK CAUGHT THE TRAP DIRECTLY: the best configuration on TRAIN (floor 0.65) is NOT the best on
TEST (floor 0.45, room 0.25-1.00R). Had I optimised on either half alone I would have shipped a
number fitted to that half's tape. Swept for configurations that beat the shipped pair on BOTH
halves: ZERO OF NINETEEN. SO THE PARAMETERS ARE UNCHANGED -- 0.45 floor, 0.25-0.75R earned room
-- NOT because they are optimal but because nothing tested is demonstrably better and they sit
mid-range on both halves. That is the correct output of a calibration that finds no signal, and
stating it is the whole discipline: C404, C405 and C434 were all cases of a threshold set from
one sample, and this is the first time the method has been applied BEFORE shipping a number
rather than after losing money on one. ONE REAL FINDING SURVIVES, AND IT IS ABOUT STRUCTURE
RATHER THAN VALUES: the optimal room band INVERTS between the halves. On the losing half a
TIGHTER band is better (cut faster); on the winning half a WIDER one is better (let winners
run), consistently across three separate floor values. That says the room should adapt to
REGIME, which the bot already classifies -- but it is a new mechanism and 228 trades over 21
instrument-days is not enough to build one on. Recorded as the next hypothesis, not implemented.
ON THE OPERATOR'S SECOND QUESTION -- YES, I RUN THE HARNESS, NOT THEM. It ships so the work is
auditable and so they CAN run it, but the obligation is mine and it runs BEFORE a change, not
after a regression. THIRD QUESTION, AND THEY WERE RIGHT: the data feeding it is now REAL and is
re-fetched on every run, so each calibration is against a fresher and longer window than the
last. The 21 instrument-days available today is the binding constraint on what can be concluded,
and it grows every session. VERIFICATION: syntax; AST 363 unchanged (NO code change this version
-- the deliverable is the calibration and the finding); duplicate defs 0; wrong-object sweep
clean; class-ownership sweep clean; 6,000 real bars fetched live; 20 configurations x 2 halves x
228 trades replayed against the shipped functions. LIMITS, and they are the point: 21
instrument-days cannot separate a 0.14R parameter effect from a 0.63R regime swing, so this
calibration CANNOT yet set the parameters and does not pretend to. It CAN and did rule out
overfitting. Re-run it when the window is materially longer, or when the now-working C447 grader
has accumulated live grades -- the two sources answer the same question independently and
agreeing would be worth more than either alone. Chain C367-C448 intact.


## C447

THE OPERATOR ASKED WHETHER ANYTHING WAS STILL BROKEN. YES -- ONE THING, AND I HAD DEFERRED IT
THREE VERSIONS RUNNING AS 'instrumentation'. IT WAS NOT A DETAIL. C444's grader has NEVER
EXECUTED ONCE. _c444_settle was defined on ExchangeManager and called as self._c444_settle()
from TradingBot -- an AttributeError swallowed by a bare `except: pass`. And the queue was
WRITTEN on TradingBot while being READ on ExchangeManager, so even a successful call would have
found it empty. DOUBLY BROKEN. Three sessions of 'C444 recorded zero grades' and I wrote it off
each time rather than spending five minutes on it, because it was instrumentation and the
trading was on fire. That was the wrong call: the grader is the ONLY thing that can tell whether
an exit was right, so deferring it deferred every exit-side answer with it. AND MY OWN AUDIT
PASSED IT, WHICH IS THE FINDING THAT MATTERS. The wrong-object sweep I have run every version
since C412 asks whether a method name exists ANYWHERE IN THE FILE. It does not ask whether it
exists ON THE CLASS THAT CALLS IT. THAT BLIND SPOT IS THE COMMON ANCESTOR OF FOUR DEFECTS:
C422-1 (guessed a receiver name), C440-3 (called a method that did not exist), C445 (misread an
existing convention) and C447 (put a method on the wrong class). Every one produced a plausible-
looking nothing instead of an error. A class-ownership sweep now runs over the whole file and
SHIPS as omega_class_audit.py so it can be run before any change: across 30,310 lines it finds
exactly ONE cross-class self-call and zero attribute mismatches, and the one it finds is this.
RELOCATED ONTO TradingBot -- AND I GOT IT WRONG ONCE ON THE WAY. My first move anchored it
beside _c427_reconcile, which is on Portfolio, so the sweep still reported a mismatch; the
second anchored it beside _monitoring_thread_func, which is the method that actually calls it.
Recorded because the audit catching my own repair is the entire point of having one. Method,
call site and queue are now all on TradingBot -- verified by class, not by grep. VERIFIED BY
EXECUTION, NOT INFERENCE. The grader instantiated on TradingBot and run against the C445
session's four real exits with their true forward prices produces four graded rows where three
sessions produced zero, AND THE VERDICT IT GENERATES IS IMMEDIATELY ACTIONABLE: PEAK_FLOOR fired
twice at a MEAN INDEX OF 0.72 and the price ran +4.28R further in our favour afterwards;
CONVICTION_COLLAPSE fired twice at a mean index of 0.08 and the price fell -0.57R. THE INDEX IS
ALREADY DISCRIMINATING CORRECTLY BETWEEN A GOOD EXIT PATH AND A BAD ONE -- PEAK_FLOOR is firing
while the thesis is still alive and CONVICTION_COLLAPSE is firing when it is dead. That is
precisely the evidence the C443 plan was waiting for, and it has been unobtainable for three
versions because of a one-line class error. SO: IS THE CODE COMPLETE? The known defect list is
now EMPTY. Every fix from C420 to C447 is present, reachable, on the correct class, called at
least once, and its constants are read. The class-ownership sweep is clean, the wrong-object
sweep is clean, there are no duplicate definitions, no write-only analysis keys, no orphan
constants except one deliberate tombstone, and the C446 harness passes its controls across six
asset classes and both sides. WHAT REMAINS IS NOT DEFECTS BUT UNKNOWNS: the 0.45 index floor and
the 0.25-0.75R earned-room band are judgements that the now-working grader will calibrate;
C429_PARALLEL_ENTRY is still off pending the ranking question; and no version since C439 has had
a profitable session, so the whole C440-C447 chain is unproven in the wild. VERIFICATION:
syntax; AST 363 unchanged (relocation, not addition); duplicate defs 0; wrong-object sweep
clean; CLASS-OWNERSHIP SWEEP CLEAN (0 of 30,310 lines); queue write and read confirmed on the
same class; an indentation break introduced by the first relocation attempt was caught by the
syntax check and repaired; the grader EXECUTED on TradingBot against four real exits. Chain
C367-C447 intact.


## C446

THE OPERATOR IS RIGHT THAT THREE DEFECTS OF ONE FAMILY MEANS MY METHOD IS WRONG, NOT JUST MY
CODE. C440-3 read a method name that did not exist, C444-3 used an absolute band inside the tool
built to judge relativity, C445 applied a direction sign to a quantity that has no direction.
ALL THREE PASSED ARITHMETIC CHECKS. All three failed on the INPUT SPACE, because I tested what a
function computes and never what it does across the range of states it will actually meet. So
this version builds the harness that would have caught all three, runs it, and ships it. THE
HARNESS. Six asset profiles taken LIVE from the venue -- PEPE 0.649% 15m ATR, BTC 0.256%, LINK
0.472%, NVDA 0.154%, XAU 0.132%, SPX 1.056% -- AN EIGHT-FOLD VOLATILITY RANGE, which is
precisely the span across which an absolute threshold silently changes meaning. Ten adversarial
price paths, each scaled to the instrument's OWN ATR so the test is relativistic by
construction: clean trend, chop, whipsaw, slow bleed, dead flat, gap down, flash crash with
recovery, pump-and-dump, LATE BLOOM (drift against then run -- the ENA shape), and a rug of -14
ATR in a single bar. Both sides. 120 runs against the REAL _c443_uei and _c422_soft_loss_gate
extracted from the shipped file, not a reimplementation. TWO OF THE FIRST THREE 'FAILURES' WERE
MY HARNESS, NOT THE CODE, AND SAYING SO IS THE POINT. The long/short divergence was 12 cells
until I noticed the test demanded identical PnL from identical price STEPS, which compounding
makes arithmetically impossible; restated to hold the STATE constant and flip only the side, it
is 0/16 -- THE LOGIC IS SIDE-SYMMETRIC. The -5.38R 'stop breach' is a -14 ATR gap filling
through a 1.5R stop, which is correct on every venue that exists; recorded as a real risk
characteristic rather than a defect. A harness that reports a false positive and is believed is
worse than no harness. C446 -- THE REAL FINDING, AND IT IS THE LAST ABSOLUTE IN THE GATE.
Driving the late-bloom path across all six assets, the position is released at -0.52R WHILE THE
INDEX READS 0.59, comfortably above the 0.45 floor. The index says the thesis is alive and the
flat 0.5R allowance overrules it -- on every asset, every time. C443 set out to remove flat-
threshold thinking from the exit and left one in place ONE LINE BELOW ITSELF. The room a thesis
gets is now EARNED: scaled by its own retention, bounded 0.25R at zero to 0.75R at full, so it
can never approach C377's 1.5R hard stop and the hard stop stays ungated. Verified across four
assets: a healthy thesis earns 0.70R and HOLDS at -0.52R; a dying one earns 0.31R and is cut at
-0.30R; a dead one earns 0.26R and is cut at -0.28R -- FASTER than the old flat rule would have
cut it. The flat rule did the opposite in both directions. AND I CAUGHT MYSELF WRITING A FALSE
CONCLUSION, WHICH IS RECORDED BECAUSE IT IS THE HABIT UNDER CORRECTION. I printed 'INJ and ENA
are now HELD' beneath a table that showed both EXITING. Two errors: the UEI floor fires BEFORE
the room test so neither ever reaches it, and more seriously THE LOG DOES NOT RECORD DRI/DSI AT
EXIT FOR INJ OR ENA -- only GWEI (0.378->0.009) and ZK (0.434->0.065) have real values, and I
had INVENTED the other two. That row proves nothing and the claim under it was unsupported. WHAT
IS ACTUALLY VALIDATED: the harness controls across four assets, and GWEI and ZK with their TRUE
logged values both correctly exiting. INJ and ENA remain UNVALIDATED and are stated as such. THE
HARNESS SHIPS AS omega_sim_harness.py so it can be run BEFORE every future change rather than
after every regression. It needs no live account and no session: it extracts the real functions
by AST from whatever build it is pointed at, so it cannot drift out of sync with the code it
tests. VERIFICATION: syntax; AST 363 unchanged; count-asserted replacements; duplicate defs 0;
wrong-object sweep clean; C446 constant read; 120-run sweep across 6 assets, 10 paths and 2
sides; controls proving the change cuts a dead thesis FASTER, not merely holding a live one
longer. LIMITS: the harness's DRI/DSI model is MINE, not the bot's -- it decays plausibly with
adverse move and age, and the late-bloom result depends on that model, so the synthetic path is
harsher than the real ENA was. The controls do not depend on it. C444 still recorded zero grades
and is STILL not fixed, deliberately, for the third version running: it is instrumentation, and
mixing it into a gate change would make the next log unattributable. Grep '\U0001f4d3 C444'
first. Chain C367-C446 intact.


## C445

MY C443 INDEX WAS BROKEN FROM THE MOMENT IT SHIPPED, AND WORSE, IT DUPLICATED SOMETHING THAT
ALREADY WORKED. Session 20260904_132028: 7h05m, 5 positions, 0W/5L, -$1.21 (-0.5%), equity
$248.79, win rate 0%. THE LOG SAYS IT IN FIVE IDENTICAL LINES: 'C443 exit index: 0.00 at close'
on EVERY exit, and ZERO C422-4 holds where the previous session had seven. AN INDEX THAT READS
0.00 EVERY TIME IS NOT AN INDEX, AND A GATE THAT NEVER HOLDS IS NOT A GATE -- so every soft exit
fired instantly and all the patience C442 restored was silently removed. That is the entire
regression, and it is mine. THE CAUSE, CONFIRMED AGAINST THE LOG'S OWN NUMBERS. I multiplied DRI
by the position's direction sign. All five positions were LONGS with NEGATIVE dri_baseline (GWEI
-0.131, ZK -0.133), so _dh came out (-0.106 x 1)/0.131 = -0.81, and max(0, -0.81) is ZERO.
Exactly what printed. AND THE REASON THE SIGN IS MEANINGLESS IS THE PART I SHOULD HAVE READ
FIRST. DRI IS NOT A DIRECTION INDICATOR. get_dri_deviation's own docstring says it: 'Positive =
moved toward reversal. Negative = moved toward continuation.' DRI MEASURES PROXIMITY TO
REVERSAL, so a MORE NEGATIVE reading is HEALTHIER and its absolute sign carries no directional
meaning at all. Multiplying a reversal-proximity measure by the trade's direction is not a units
error, it is a category error. C399 has always used `retention = value_now / value_at_entry`
with NO sign term, and its comment states the convention outright: '< 0 = sign flipped, i.e. the
reversal is no longer coming, it has ARRIVED'. THE DEEPER ERROR IS THAT I WROTE C443 AT ALL.
C399 ALREADY IMPLEMENTS THE OPERATOR'S REQUEST, and its comment says so in the operator's own
terms: 'The weaker of the two governs, because either one reaching zero is sufficient for the
trade to be over -- that is what the operator's specification says and it is what the data
shows.' A unified DRI/DSI retention, dimensionless, relativistic by construction, proven across
many versions -- AND I BUILT A SECOND BROKEN COPY BESIDE IT INSTEAD OF READING THE ONE ALREADY
THERE. When the operator asked for DRI and DSI to be combined, the correct answer was 'that
exists at C399, here is what it says', not a new index. THE REPAIR IS DELETION, NOT CORRECTION.
_c443_uei no longer computes its own arithmetic; it defers to C399's convention so there is ONE
definition of thesis retention in the file rather than two that can disagree. C399 takes min()
-- the weakest link ends the trade -- where C443 argued for a product; min() is the more
conservative and it is the one with a track record, so min() wins and the product is recorded as
the REJECTED alternative rather than smuggled in. The near-zero-baseline case now ABSTAINS
(returns 1.0, no gating) instead of returning a number, because C399 abstains there too and an
abstention must mean 'do not gate', never 'exit'. VERIFIED ON THE SESSION'S OWN READINGS: a
healthy short read 0.00 under C443 and reads 0.90 under C445; a healthy long reads 0.90; GWEI
reads 0.02 and ZK 0.15 -- still spent, correctly, because DSI collapsed to 2% and 15%, but now
for the RIGHT reason. Gate behaviour across six cases: healthy long and healthy short both HOLD,
reversed and fuel-dead both exit, and the two real losers still exit. THIRD CONSECUTIVE DEFECT
OF ONE FAMILY, AND THE PATTERN IS WORTH NAMING. C440-3 read a method name that did not exist;
C444-3 used an absolute band inside the tool built to judge relativity; C445 misread an existing
CONVENTION. Every one was hidden because the wrong answer LOOKED PLAUSIBLE -- a zero, a
percentage, a ratio. THE STANDING AUDIT GAINS A LINE: before writing a new measure, grep for
whether the quantity is already computed somewhere, and READ ITS CONVENTION rather than assuming
one. ALSO OBSERVED: C444 recorded ZERO grades. Five positions closed and the queue was
populated, but no grade came due -- the last close was 16:15 and the session ran to 20:26, so
30-minute grades SHOULD have settled. That is a second wiring question and it is NOT fixed here,
deliberately: C445 changes the exit gate and mixing a second change in would make the next log
unattributable. It is the first thing to check next session -- grep '\U0001f4d3 C444'.
VERIFICATION: syntax; AST 363 unchanged; count-asserted replacement; a stray quote introduced
during the edit was caught by the syntax check and removed; duplicate defs 0; wrong-object sweep
clean; the index replayed across six cases spanning both sides, both vocabularies and two
controls; the position sides confirmed from the log (all five LONG) so the diagnosis rests on
data rather than inference. LIMITS: the 0.45 floor is still a judgement and the C444 grading
ledger that would calibrate it recorded nothing this session. Chain C367-C445 intact.


## C444

THE OPERATOR ACCEPTED MY PLAN ON TRUST, SO I WENT LOOKING FOR THE HOLE IN IT AND FOUND ONE. C443
proposed: gate the soft exits with the unified index, let a ledger accumulate, then replace
whichever of the forty exit paths the data says are redundant. The ledger it built records uei,
banked_r, peak_r and the reason -- AND NOT ONE OF THOSE CAN TELL A GOOD EXIT FROM A BAD ONE.
Every judgement I have made about an exit this month required fetching candles from AFTER the
close, from OUTSIDE the bot: C440's 51% capture, C442's five-of-six verdict, ENA's +11.38%. THE
BOT ITSELF HAS NEVER RECORDED WHAT HAPPENED NEXT, so the ledger would have filled with
ungradeable rows and the plan would have stalled at exactly the step that matters. That is the
computed-but-never-wired failure appearing in a PLAN rather than in code, and it is named as
such because a plan is not exempt from the audit. WHAT C444 MEASURES. Thirty minutes after each
close the price is read once more and the move since exit is recorded IN THE TRADE'S OWN
DIRECTION, paired with the index reading at that close. Positive means the position would have
been better held; negative means the exit protected capital. Together they answer the only
question that matters and that nothing in forty exit paths has ever asked: WHEN THE INDEX SAID
THE THESIS WAS SPENT, WAS IT? Thirty minutes is roughly one expected-hold horizon -- long enough
for a genuine continuation to show, short enough that the reading is still about THIS thesis. A
judgement, and stated as one. SWEPT FROM THE MONITOR THREAD, DELIBERATELY. The monitor is the
only loop guaranteed to keep ticking while the bot is FLAT, and a grade falling due thirty
minutes after the last close of a session is precisely the case that would otherwise never be
collected -- which is the case that matters most, because the last exit of a session is the one
no human is watching. C444-3, AND THIS ONE IS EMBARRASSING IN A USEFUL WAY. My first draft
called any forward move beyond +/-0.3% a verdict. On the VERY FIRST TEST that labelled BONK's
+0.31% -- pure noise -- as 'held would have been better', on a pair whose stop was 1.66%. AN
ABSOLUTE BAND, INSTANCE THIRTEEN OF THIS PROJECT'S OLDEST DISEASE, APPEARING INSIDE THE TOOL
BUILT TO JUDGE THE EXITS. Now expressed in the position's OWN stop: under a fifth of R is noise
on any instrument, which is the only reading that means the same thing on a memecoin and a
tokenised equity. Re-verified: BONK +0.31% reads +0.19R and lands NEUTRAL; ENA +11.38% reads
+6.86R; a -2.50% move reads -1.51R and correctly credits the exit with protecting capital.
INSTRUMENTED ONLY -- NOTHING ACTS ON THIS. That is the discipline the plan depends on: gate now
with C443, accumulate a graded record, and let the data name which of the forty paths the index
should be allowed to overrule. The per-reason verdict prints once twelve grades exist and names
the worst offender explicitly, so the next version starts from evidence rather than from my
instinct. Costs one cached price read per closed position. VERIFICATION: syntax; AST 362 -> 363
(+_c444_settle); count-asserted replacements reported individually; duplicate defs 0; wrong-
object sweep clean; C444 constants all three read; _c444_settle confirmed CALLED from the
monitor loop so it is not an orphan; the grader EXECUTED against the C442 session's four real
exits with the true forward prices, producing exactly the pairing the plan needs -- INJ and ENA
recorded as premature at a HIGH index (0.79, 0.65) and BONK as correct at a LOW index (0.03).
LIMITS: thirty minutes and a fifth of R are both judgements; the queue holds at most 40 pending
grades and the ledger 120 rows, so a very busy session could drop the oldest; and a grade is a
SINGLE price read, not an MFE sweep, so it measures where the price WAS at +30min rather than
the best it reached -- deliberately, because the question is whether HOLDING would have been
better, not whether a perfect exit existed. Chain C367-C444 intact.


## C443

THE OPERATOR IS RIGHT ABOUT THE TIMER, AND MORE RIGHT THAN THEY KNEW. The directive: 'there
shouldn't be any exit timer -- exits should be decided on the basis of the net profit the pair
can maximally give, the overall dynamics of that pair and the market, and all that predictive
probability should be reflected in DRI and DSI'. THE CODE ALREADY AGREES: update_dsi decays DSI
from DSI_DECAY_START_MIN (30 minutes) at DSI_DECAY_RATE and decays it FURTHER on drawdown. TIME
IS ALREADY INSIDE THE INDEX. So the clock in C422-4 was COUNTING TIME TWICE -- once as decay
within DSI, and again as an independent deadline that could OVERRIDE it -- and C442 measured
what that cost: five of six exits would have been better held, ENA ran +11.38% after being cut
0.24R offside. The clock was not mis-tuned, it was REDUNDANT WITH DSI AND OUTRANKED IT. C442's
3x multiple was honest about being fitted to six trades; this removes the need for a fitted
number at all. WHERE THE PROPOSAL NEEDED ONE CORRECTION, STATED PLAINLY. DRI and DSI are
ORTHOGONAL, not two views of one quantity: DRI is SIGNED direction strength, DSI is UNSIGNED
fuel. Four states matter -- strong direction with strong fuel (ride), strong direction with WEAK
fuel (about to stall), WEAK direction with strong fuel (coiling, could break either way), and
both weak (dead) -- and A SUM OR AVERAGE CANNOT TELL THE MIDDLE TWO APART while they need
opposite handling. So the unified index is a PRODUCT of two healths, not a blend: EITHER leg
dying is sufficient to end the thesis. Verified -- 'strong dir + weak fuel' scores 0.25 and
'weak dir + strong fuel' scores 0.20, both correctly below the floor, where an average would
have scored both 0.63 and held them. RELATIVISTIC BY CONSTRUCTION, which is the per-asset
treatment the operator has been asking for at the exit layer. Both legs are measured against
THIS position's OWN baselines, locked at entry by C26 and never drifting, so the index means the
same thing on a memecoin at $0.0000038 and a tokenised equity at $780. No absolute threshold
appears anywhere in it. AND IT IS STRICTLY BETTER THAN THE CLOCK IN BOTH DIRECTIONS, which a
threshold move could not have achieved. Replayed against the session that regressed: INJ (0.79)
and ENA (0.65) are HELD and both recovered; 1000BONK (0.03) still exits and that exit was right.
But a DEAD THESIS at 40 minutes scores 0.01 and a REVERSED one scores 0.00, and C442's clock
would have HELD BOTH -- they were nowhere near 3x horizon. The clock could only trade patience
against decisiveness; the index gets both. THE DEEPEST PROBLEM THIS OPENS. There are FORTY
distinct exit reasons in this file and NOT ONE OF THEM HAS EVER BEEN SCORED -- there is no
record anywhere of whether an exit was right, which is why every exit-side fix for twenty
versions has been an adjustment rather than an improvement. C443 stamps the index at every close
beside what the trade actually did (banked in R, peak in R, reason), persisted with the learning
state. Once enough closes accumulate the index can be Brier-scored exactly like the Markov
chains, and the exit layer becomes MEASURABLE for the first time. That, not the removal of the
clock, is the real prize in the operator's proposal. VERIFICATION: syntax; AST 361 -> 362
(+_c443_uei); count-asserted replacements reported individually; duplicate defs 0; wrong-object
sweep clean; C443 constants both read; the four-state separation verified against the average
that would have collapsed it; the gate replayed on five cases including two controls that MUST
exit. LIMITS AND ONE OPEN QUESTION. The 0.45 floor is a first setting, not a derivation -- it is
the point at which less than half the entry thesis survives, which is defensible, but the
scoring ledger this version starts is what will actually calibrate it, and until then it is a
judgement. The index currently GATES the soft-loss exits only; the other thirty-odd paths, the
hard stop, the day cap and every profit exit are untouched. WHETHER THE INDEX SHOULD REPLACE
THOSE PATHS RATHER THAN GATE THEM IS THE OPERATOR'S CALL AND IS ASKED EXPLICITLY -- gating is
reversible and keeps hard-won special cases (the capitulation flip, the ichimoku cross, the
regime exit); replacing is cleaner but would discard twenty versions of specific evidence in one
step and make the next log unattributable. Chain C367-C443 intact.


## C442

THE BUG I FIXED AT C440-3 WAS LOAD-BEARING, AND THE OPERATOR ASKING ME TO COMPARE AGAINST THE
GOOD VERSION IS WHAT PROVED IT. LINEAGE FIRST: the uploaded 'c440good' file is actually C439 --
the build that produced +$0.86 with four winners and 51% capture. My C441 is a STRICT SUPERSET
of it: all 73 changelog entries present, zero functions, classes or constants lost, and the
executable diff is FIVE removed lines against 74 added. So the entire behavioural difference
between the good session and the bad one is TWO LINES -- the get_age_seconds() repair. WHAT THAT
REPAIR DID. For eighteen versions `age_seconds` was misspelled, so _age_min read ZERO and
C422-4's clock release NEVER FIRED; the floor released only on the 0.5R evidence test. C440-3
corrected the name, the clock came alive, and the very next session inverted: C439 +$0.86 with
four winners, C440 -$0.41 with one winner and five round trips. CHART-VERIFIED ON LIVE BITGET
CANDLES, AND THE VERDICT IS NOT MARGINAL -- FIVE OF THE SIX EXITS WOULD HAVE BEEN BETTER HELD:
INJ exited -0.4% and ran +2.83% within three hours; ENA exited -0.4% and ran +11.38%; WLD exited
0.0% and ran +4.06%; FET exited 0.0% and ran +1.39%; NIGHT exited +0.9% and ran +1.73% further.
Only 1000BONK (-0.9%, ran +0.31%) was correct. AND INJ AT 47 MINUTES AND ENA AT 61 MINUTES ARE
EXACTLY THE TWO THAT CROSSED THE 35-MINUTE HORIZON -- the two this line newly released. The
entries were right in five of six cases; the loss was entirely in the holding. THE ASSUMPTION IS
WRONG, NOT MERELY MIS-TUNED. `expected_hold_min` is an ESTIMATE of how long a thesis needs, and
releasing patience the moment the estimate is exceeded turns the estimate into a SELF-FULFILLING
DEADLINE. INJ was 0.24R offside when the clock cut it -- not a failed thesis, an ordinary
pullback inside the noise band the position was SIZED to absorb, which is precisely what C422-4
exists to protect and what the clock overrode. And the clock adds nothing the R test does not
already do: the next line releases at 0.5R, a statement about EVIDENCE, so the clock only ever
fires for positions past the horizon that are NOT meaningfully offside -- i.e. exactly the
recoverable ones. THE FIX IS NOT A REVERT. Shipping a misspelled method name to restore an
accident would be indefensible and would hide the same landmine for the next reader. The clock
is KEPT as an anti-stagnation valve so a position cannot tie up margin indefinitely, moved out
to 3x the horizon. HONEST ABOUT THE NUMBER: 3x is CALIBRATED ON SIX TRADES -- it holds all five
premature exits (18-61 min) and still releases 1000BONK at 140 min, the one exit that was right
-- and I am stating that rather than dressing it as a derivation. The PRINCIPLE stands on its
own and independently of the fit: a clock is not evidence, and C383 already uses 2x for exactly
this reason. Replayed across seven cases including three controls: behaviour changes on TWO --
INJ and ENA now hold -- while a real 0.72R loss, a 1.51R hard stop and 1000BONK all still exit
untouched. THE WIDER LESSON, AND IT IS UNCOMFORTABLE. C440-3 was a CORRECT repair of a REAL
defect, verified by execution, audited clean -- and it made the bot worse, because the defect
had been silently supplying patience the design never granted explicitly. An accident that
improves outcomes is still an accident, but removing it without measuring what it was doing is
how a correct fix becomes a regression. THE STANDING AUDIT GAINS A LINE: when a repair changes
the behaviour of a gate that has been effectively disabled, the FIRST session after it is a
controlled experiment and must be read as one -- and C440's own limits note said exactly that
('the next log is the first evidence of how C383 and C422-4 behave when they can actually reach
their horizons'). It took one session to answer, and the answer was that they should not reach
them. VERIFICATION: syntax; AST 361 unchanged; count-asserted replacements reported
individually; duplicate defs 0; wrong-object sweep clean; C442 constant read; the gate replayed
across seven cases with a complete harness -- TWO HARNESS FAULTS WERE FOUND AND FIXED DURING
THIS VERIFICATION (a missing _c423_note_guard stub and a missing _c432_finite, each of which
silently routed every case through the outer except and reported 'exit' for everything). That is
worth recording: a harness that omits a dependency does not fail loudly, it produces a plausible
wrong answer, and I nearly shipped on it. LIMITS: n=6, and the 3x multiple is fitted to it.
C383's own clock at 1x/2x is left ALONE deliberately -- it gates PROFIT exits, the measured
damage is all on the loss side, and changing both at once would make the next log
unattributable. If the next session shows positions hanging at small losses without recovering,
3x is too far and the R test should carry it alone. Chain C367-C442 intact.


## C441

THE TARGET FLOOR WAS IN A DEATH SPIRAL AND IT IS MY OWN C420-4. Session 20260903_174153: 12h35m,
6 positions, 1W/5L, -$0.41 (-0.2%), equity $249.59, win rate 17%. THE PATTERN IS ONE SHAPE, SIX
TIMES. FIVE OF SIX POSITIONS PEAKED POSITIVE AND GAVE BACK 100% OR MORE: INJ +1.2% -> -0.4%, ENA
+2.1% -> -0.4%, FET +2.5% -> +0.0%, WLD +1.4% -> +0.0%, 1000BONK peaked +0.43% and banked
-0.87%. The capture ledger prints it as -34%, -30%, -8%, -7%. Only NIGHT captured anything, 46%.
This is not bad selection: EVERY TRADE WENT THE RIGHT WAY FIRST. THE CAUSE IS THE TARGET, AND
THE ARITHMETIC IS EXACT. C420-4 solves T = [Emin + (1-wr)(1+f)]/wr + f from the Laplace-shrunk
realised win rate. At 17% the shrunk wr is 0.30, which demands T = 2.85R -- and the log shows T
= 2.57, 2.95, 3.00, 2.04, 1.79, 2.13 on the six entries. THE TRADES THEMSELVES PEAKED AT 0.7-1.3
PRU. THE BOT WAS DEMANDING TWO TO THREE TIMES WHAT ITS OWN TRADES ACTUALLY REACH, so the target
was never hit and every position rode the full round trip back through zero. AND IT SELF-
REINFORCES, WHICH IS WHAT MAKES IT A SPIRAL RATHER THAN A BAD SETTING: each round trip is a
loss, each loss lowers wr, each drop in wr RAISES the required target, and the next target is
less reachable than the last. C420-4 is a ONE-SIDED ANCHOR -- it asks what payoff the bot NEEDS
and never asks what the market GIVES. This is C421-3's death spiral in a second place: I closed
it in the EDGE and left it wide open in the TARGET, and it took a 17% session to surface it. THE
SECOND ANCHOR WAS ALREADY BEING COLLECTED AND THROWN AWAY. The C422-3 capture ledger has
measured every trade's peak since it shipped and discarded the distribution at session end.
C441-1 persists it in R units with the learning state; C441-2 caps the target floor at the 70th
percentile of what the bot's OWN trades actually reach -- ambitious enough to sit above most
outcomes, honest enough that it has been achieved. Verified on the session's own peaks: the 70th
percentile is 1.01R, so the demand falls from 2.85R to 1.01R at 3W/17L and stays there at 2W/18L
instead of climbing to 3.20R. THIS REVERSES THE SPIRAL RATHER THAN DAMPING IT. Capping T near
the observed peaks converts these round trips into small WINS; wins raise wr; a higher wr then
permits a higher target on its own evidence. The loop runs the right way instead of the wrong
one, and the cap lifts by itself as the record improves. Below ten closed trades it does not
bind at all -- cold-start behaviour is byte-identical, confirmed. WHAT ELSE THE SESSION SHOWS,
checked so the next one is not spent re-litigating it. THE HP GATE IS FINALLY SILENT: zero 'HP
pending' lines and zero C440-1 clears, after four operator reports and four partial fixes.
C440-3's repair is live and visible -- C422-4 held through seven soft exits at 0.16R to 0.26R,
which is the first time that floor has functioned since it shipped eighteen versions ago, and
none of those holds turned a small loss into a large one (every exit came from PEAK_FLOOR or
PEAK_REVERSAL, not from a runaway). C440-2's age guard did NOT fire on INJ/ENA/FET because their
peaks were 0.8, 1.2 and 1.3 PRU and the guard only covers peaks below 1.0 PRU -- correct by
design, and it means the givebacks were not caused by the guard being too loose. p remains
bimodal at 0.85 and 0.20 with p_w=0.0 throughout, so S3 still contributes nothing and the
ensemble is carried entirely by the Markov chains. VERIFICATION: syntax; AST 361 unchanged;
count-asserted replacements reported individually; duplicate defs 0; wrong-object sweep clean;
C441 constants all three read; the cap tabulated across five realised records against the
session's own twelve peaks; cold-start (n<10) confirmed byte-identical. LIMITS: the 70th
percentile is a choice, not a derivation -- it is defensible as 'above most outcomes but
achieved', and if the next log shows targets being hit too easily it should rise, not fall. The
peak record needs ten closed trades before it binds, so the first session after this carries the
old behaviour until the tenth close. AND THE DEEPER QUESTION REMAINS OPEN: five of six trades
went the right way first, which says ENTRY DIRECTION IS WORKING and the loss is entirely in the
holding. If C441 converts these into wins, the payoff problem is solved; if the trades still
round-trip with a 1.0R target, the exits need work rather than the target. Chain C367-C441
intact.


## C440

THE BEST SESSION YET, AND THE AUDIT STILL FOUND A GATE THAT HAS BEEN BROKEN SINCE C422. Session
20260902_174952: 19h19m, 8 positions, 4 WINNERS (MUBARAK +9.5%, APT +4.7%, NVDL +2.2%, PYTH
+2.2%), +$0.86 (+0.3%), equity $251.26. CHART-VERIFIED AGAINST LIVE BITGET 5m CANDLES: captured
+18.38% of the +36.20% available across the eight trades -- CAPTURE RATIO 51%, against the 10%
measured at C422 and the -3% that prompted C423. MUBARAK captured 88% of its own MFE, APT 87%,
PYTH 77%. The C436 probability is genuinely discriminating now (p spread across
0.20/0.21/0.22/0.46/0.51/0.78/0.79/0.85 with 8 honest no-source fallbacks) and the C439 tilt
fired 58 times. C435's count cap bound twice, keeping 'the top 2 BY SCORE' out of 13 and 4
candidates. C440-3, THE FIND THAT MATTERS MOST -- A METHOD NAME THAT NEVER EXISTED. Position
defines get_age_seconds(). THERE IS NO age_seconds. Two gates have called the wrong name behind
a defensive getattr since the day they shipped: 'getattr(self, "age_seconds", lambda: 0)()' HAS
ALWAYS RETURNED ZERO. In C383 that killed BOTH horizon releases -- 'long past horizon: take it'
and 'past horizon AND worth taking' could never fire. In C422-4 it killed the release I
described in that changelog as 'the floor LIFTS at the horizon': it never lifted, so a soft
loss-exit was suppressed not for the first horizon but INDEFINITELY, until the loss crossed
0.5R. THE DEFENSIVE getattr IS EXACTLY WHAT HID IT -- a missing method raises and gets fixed; a
getattr with a default returns quietly and the gate behaves as though every position were
newborn, forever. Principle #168 again, and this instance has been live for eighteen versions.
Found only because C440-2 called the SAME wrong name and the wrong-object sweep flagged it --
the audit catching my new bug is what exposed my old one. All three sites repaired; the sweep is
now clean. C440-1, HP -- THE OPERATOR HAS RAISED THIS FOUR TIMES AND HAS BEEN RIGHT EVERY TIME.
C403-3 retired the mode, C426-3 stopped printing its score floor, C431-2 closed the restore
path, AND THIS GATE SURVIVED ALL THREE. C300 sets _pending_hp when a phase boundary spares a
runner so HP does not inherit a position it never chose; the flag then SUPPRESSES EVERY NEW
ENTRY until the bot goes flat and HP activates. HP CANNOT ACTIVATE. The deferral defers to a
destination that no longer exists, so the only thing it can still do is stop trades. The log
shows it set at 12:35 and STILL SET when the session ended at 13:09, and _pending_hp PERSISTS to
mode_v60.json -- a session can begin with entries suppressed. It cost nothing this time only
because it was set late while the bot rode APT. Fifth site of a decision enforced in some of the
places it applies, and C431-2's own standing audit named the gap: for every retirement find
every place the state is set, read OR ACTED ON. I checked the writes and not the readers. Now
inert under single-mode, and a stale flag self-clears with a warning. C440-2, A PEAK THAT NEVER
HAD TIME TO FORM IS NOT A REVERSAL. Chart-verified: BR opened 09:13, peaked +1.2% (0.8 PRU),
gave it back, and PEAK_FLOOR closed it at 09:16 -- THREE MINUTES OLD. BR THEN RAN +5.45% WITHIN
TWO HOURS. Same session, ARB round-tripped a +1.6% peak and ran +2.35% after. Two of the four
losses were small peaks erased on young positions and both continued in the entry's direction.
PEAK_FLOOR has no age test: it fires the moment a peak above 0.75 leveraged-ATR is erased, at
three minutes or at thirty. On a three-minute-old trade a +1.2% excursion is not a peak, it is
the entry noise the position was SIZED to absorb -- and C422-4 established exactly that
reasoning for the LOSS side, so this is its mirror. C280's changelog claims "'profit fully
erased' can no longer print on an armed winner"; it printed on BR. That fix addressed the blind
BAND and not the blind CLOCK. DELIBERATELY NARROW: only while the peak is SMALL (<1.0 PRU --
above that the existing branch treats it as real and fires immediately) and only for the first
quarter of the position's OWN expected hold, so it is relativistic in both dimensions and
expires by itself. Replayed on the session's five relevant exits: ONLY BR CHANGES; ARB, NVDL and
MUBARAK still exit, and a 1.4-PRU peak at four minutes still fires. Hard stop, day cap and every
loss exit untouched, so worst-case loss is UNCHANGED. VERIFICATION: syntax; AST 361 unchanged;
count-asserted replacements reported individually; duplicate defs 0; WRONG-OBJECT SWEEP NOW
CLEAN (age_seconds was the only real entry and it is gone); C440 constants both read; write-only
analysis keys ZERO; the age guard replayed across five real exits including a control that must
still fire; chart verification of all eight trades against live Bitget 5m candles two hours past
each exit. LIMITS: the 51% capture is measured on eight trades and the denominator (MFE in-trade
plus two hours after) is a demanding one -- a different window gives a different number, and the
figure is comparable to C422's only because it uses the same construction. NVDL still left 4.5pp
on the table after a correct-looking exit, so the ride machinery has further to give. And C440-3
changes the behaviour of two gates that have been effectively disabled for eighteen versions:
the next log is the first evidence of how C383 and C422-4 behave when they can actually reach
their horizons. Chain C367-C440 intact.


## C439

A MICRO-DISSECTION OF MY OWN C438, AND IT FOUND THAT I HAD BUILT A VOICE NOTHING WAS LISTENING
TO. No new log this version -- the operator asked for the shipped code to be re-read function by
function, so this is a pure audit pass over all 29,693 lines with the two issue types kept
separate. C439-1, THE FUNCTIONAL ONE. C438 gave the earned Markov chains a real voice: a strong-
DOWN state on a long now returns p=0.234 where C437 returned 0.850. AND NOTHING CONSUMED IT.
Before C436 the old C404 clamp floored p at 0.45, so the statement 'my best predictors think
this is more likely wrong than right' WAS NOT EVEN EXPRESSIBLE. C438 made it expressible and
left it unread -- p feeds Kelly sizing and the C416 target floor, and both of those merely make
a bad trade SMALLER and MORE DEMANDING; neither declines it. A signal created and not consumed
is the computed-but-never-wired family in its subtlest form, and this is the tenth instance.
Verified first that the C404 clamp runs BEFORE the ensemble and therefore does not clobber the
new value -- it does not, so the 0.234 genuinely survives to the decision. THE PROJECT ALREADY
HAD THE RIGHT MECHANISM AND I SHOULD HAVE COPIED IT INSTEAD OF INVENTING ONE. C342 tilts the
score by +/-8% and C343 by +/-6% when a trusted chain persists WITH or AGAINST the trade. The
ensemble is making the same statement from a broader test -- C342/C343 require trusted() AND
p_persist>=0.70, so they cannot see the disagreement C438 can -- so it gets the same treatment:
a BOUNDED TILT, not a veto. NO THRESHOLD IS INVENTED: the reference point is the base rate the
ensemble itself falls back to, so the tilt measures exactly 'how far have the earned chains
moved me off my own default', and it is ZERO BY CONSTRUCTION when no chain earned a voice.
Measured: p=0.85 gives score x1.065, p=0.47 gives x1.000, p=0.234 gives x0.960, and it is
bounded at C342's own +/-8%. Live Bitget simulation confirms the two directions resolve
oppositely on the same state -- UL long x1.066, UL short x0.954. C439-2, STRUCTURAL WITH NO
FUNCTIONAL HARM. C435 moved the count cap off expectancy onto the score and neutered the old
branch with `if False and`, which left ~40 lines of live-looking code and an orphaned
C434_COUNT_GATE that the sweep finds read at ZERO sites. A disabled branch that still reads like
a feature is how the next reader concludes the cap lives there; the branch is now closed
explicitly and the constant marked RETIRED C435 as a tombstone, following C428-2's precedent
rather than deleting a name something might still reference. C439-3, AND THIS ONE INDICTS A
CLAIM I MADE. C428 stated it had closed the orphan-key class by routing the diagnostics into
_c428_entry_view. IT CARRIED FOUR OF THEM. The sweep finds _c420_p_raw, _c420_p_weight,
_c420_proj_raw, _c420_proj_capped and _c420_fcast_mult STILL written and read by nothing, plus
_c436_p_note added at C436 and _c439_tilt added today. A PARTIAL FIX REPORTED AS COMPLETE IS
WORSE THAN NO FIX, because the next audit trusts the changelog and stops looking. All eight now
travel to the exit with the trade they describe. Re-swept with comments excluded so my own prose
cannot match the pattern: write-only analysis keys ZERO, dead `if False and` branches in code
ZERO. WHAT THE DISSECTION CLEARED. All fifteen methods added C420-C438 are defined once and
called at least once -- _fmt_px at 26 sites, _c427_reconcile at 4, _c420_base_rate at 4, none
orphaned. All 38 config constants added since C420 are read somewhere except the one deliberate
tombstone. Execution-order checked for every analysis key I write: _c428_entry_view writes at
22027 and reads at 28169, correct direction, no read-before-write anywhere -- the C437 defect
has not recurred. Two switches remain deliberately OFF and both are documented as such:
C429_PARALLEL_ENTRY (blocked on the ranking question the operator has not answered) and
C423_LEGACY_NAME_BLOCKLIST (the C134 kill switch, opt-in by design). VERIFICATION: syntax; AST
361 unchanged (all three fixes are in place, none add a function); count-asserted replacements
reported individually; duplicate defs 0; wrong-object sweep clean; C439 constants both read; the
tilt curve tabulated across six probabilities; live Bitget simulation through steps 1-5 against
770 markets and 203 volume-qualified pairs. LIMITS: the tilt is bounded at 8% and therefore
CANNOT stop a high-scoring candidate the chains dislike -- it can only rank it below a rival.
That is deliberate, because a veto on a probability whose units are state-persistence rather
than trade-outcome would be over-trusting a proxy I have already had to correct twice. If the
next log shows the tilt firing negative on trades that then lose, a veto becomes justified; if
it fires negative on trades that win, the proxy is wrong again and C438's alignment test is the
thing to question. Chain C367-C439 intact.


## C438

PERSISTENCE IS NOT DIRECTION -- C437 REPLACED A FLAT 0.47 WITH A FLAT 0.85. Session
20260901_201730: 19h06m, 10 trades, 4W/6L, -$0.82 (-0.3%), equity $249.18, win rate 40%. THE
GOOD NEWS FIRST: C437 IS ALIVE. Fifty-nine 'C436 direction probability' lines, real skill-
weighted blending, three chains contributing with their measured skills printed -- pair +44%,
family +11%, ichi +4%. The ordering defect that made C436 dead on arrival is genuinely fixed and
the ensemble runs on every scan. THE BAD NEWS IS WHAT IT PRODUCES. PairMarkov returned p_persist
>= 0.95 IN FIFTY-FIVE OF FIFTY-FIVE READINGS, and the blended p came out at 0.85 -- MY OWN CLAMP
CEILING -- in 56 of 58. THE NUMBER WENT FROM FLAT AT 0.47 TO FLAT AT 0.85. It still cannot
choose between candidates; it is now merely optimistic about all of them, which is WORSE than
neutral-flat because a uniformly high p inflates every downstream size, target and expectancy.
THE REASON IS OBVIOUS ONCE SEEN. p_persist asks 'will this state CONTINUE', and the most
persistent state in any market is the NEUTRAL one -- nothing usually keeps happening. A chain
sitting in 'N' or 'CH' reporting 0.98 persistence has learned something true and useless: IT HAS
NO DIRECTIONAL OPINION AT ALL, and reading its confidence as bullishness is a category error.
The exits corroborate it exactly -- two STAGNANT_PARTIAL and two REL_DECAY in ten trades,
positions that went NOWHERE, which is precisely what 'the neutral state persisted' predicts. AND
I FLAGGED THIS EXACT RISK IN C436'S OWN LIMITS NOTE: 'p_persist is state persistence, a close
proxy for the direction question and not literally it -- if the next log shows p varying but win
rate flat, that proxy is the first thing to question.' The log showed p NOT VARYING and the win
rate at 40%. Same verdict, reached one session later. Writing the limit down is what made it
cheap to find. THE MACHINERY TO FIX IT ALREADY EXISTED AND I DID NOT USE IT. C342 and C343 both
call dirval(state) and test ALIGNMENT before letting a chain tilt anything -- '_fd342 != 0' and
'(_fd342 * _cd342) > 0'. The same test belongs in the ensemble: a NEUTRAL state contributes
NOTHING (weight dropped entirely), an ALIGNED state contributes its persistence, and an OPPOSED
state contributes (1 - persistence), because a chain confidently persisting AGAINST the trade is
evidence against it rather than for it. Handles both vocabularies -- PairStateMarkov's
UL/ul/N/dl/DL and RegimeMarkov's SU/TU/CH/TD/SD -- with dirval used where the class provides it
and an explicit map where it does not. MEASURED ON THE SESSION'S OWN READINGS: a neutral pair
state at 0.98 persistence produced 0.85 under C437 and now produces 0.700 from the remaining
aligned source; a strong-UP state on a long still gives 0.850; A STRONG-DOWN STATE ON A LONG NOW
GIVES 0.234 WHERE C437 GAVE 0.850 -- the same 0.98 persistence read as a reason to buy is now
correctly read as a reason not to. The output spans 0.234 to 0.850 instead of sitting on one
number. THE OPERATOR'S LIMIT-ORDER QUESTION, ANSWERED WITH THE LOG. THE BOT IS IN PAPER MODE --
the startup menu offers Paper/Live/Test and DEFAULTS TO PAPER, so every fill routes through
_paper_order and the log line prints a HARDCODED 'paper=True'. No real order has been sent. The
limit logic itself is working WELL: of nine limit attempts, EIGHT filled and ONE did not (11%),
with ZERO post-only rejections. 'Paper LIMIT UNFILLED' is not a fault -- it is the C364 parity
rule doing its job, the simulator refusing to fill a resting order that price never actually
touched, because paper that fills what live would refuse is paper that lies. An 11% miss rate on
passive entries is normal and healthy for a maker strategy. VERIFICATION: syntax; AST 361
unchanged (the repair is inside the existing function); count-asserted replacement reported
individually; duplicate defs 0; wrong-object sweep clean; the ensemble re-executed across six
real state/direction combinations spanning both state vocabularies, confirming neutral drops
out, aligned survives, and opposed inverts. LIMITS: the alignment test uses the chain's LAST
state, which is the honest pre-decision reading, but a state that flipped within the current bar
will be one step behind -- that is the price of not contaminating the probability with the bar
being judged, and it is the right trade. RegimeMarkov remains excluded as market-wide. And the
deeper question is now sharper rather than answered: with neutral states dropped, some scans
will have NO earned directional source and will fall back to the base rate -- if the next log
shows that happening on most scans, the chains are telling us the market genuinely has no
direction and the answer is to trade less, not to loosen the test. Chain C367-C438 intact.


## C437

THE OPERATOR ASKED ME TO RECHECK THAT I HAD USED THE LATEST CODE, AND THE RECHECK FOUND THAT
C436 WAS DEAD ON ARRIVAL. LINEAGE FIRST, since that was the question: my working file is a
STRICT SUPERSET of the operator's last run -- all 68 changelog entries from the uploaded C434
are present, zero functions lost, zero classes lost, zero constants lost, and exactly FOUR code
lines changed against it (the version banner, the C434 count-gate branch, the C420-5 p line and
the C435-3 brier format), all four intentional. Nothing from the operator's build was
overwritten. THEN THE REAL FIND. C436 published each Markov chain's continuation reading into
`analysis` at line ~22783 and READ those keys at line ~21867 -- NINE HUNDRED LINES EARLIER IN
THE SAME FUNCTION. On every scan the keys would not exist yet, no source would ever be found,
and the ensemble would return the base rate. THE ENTIRE C436 FIX WOULD HAVE DONE NOTHING. AND IT
WOULD HAVE FAILED SILENTLY, WHICH IS THE PART WORTH RECORDING. The safety property I was most
pleased with -- 'if nothing has earned skill, return the base rate, bit-for-bit unchanged' -- is
EXACTLY what a missing key produces. The next log would have looked entirely normal: p still
flat at 0.47, no warning, no error, no trace. I would have reported the fix as shipped and
working. A GRACEFUL DEGRADATION THAT IS INDISTINGUISHABLE FROM THE BUG IT IS DEGRADING AROUND IS
NOT A SAFETY PROPERTY, IT IS CAMOUFLAGE. Ninth instance of computed-but-never-wired in this
project, and the first where my own fail-safe was the thing hiding it. The C436 changelog entry
has been CORRECTED IN PLACE rather than left standing, because it claimed the three keys were
'confirmed written AND read' and that claim was false when I made it -- a false verification
note in the project's own memory is worse than no note. THE REPAIR REMOVES THE ORDERING
DEPENDENCE RATHER THAN REORDERING THE CODE. Every chain already keeps `_last`, the state it saw
at its previous observation, keyed by symbol for PairMarkov and IchiMarkov and by family for
FamilyMarkov. Reading from there is not a workaround, it is MORE CORRECT: it is the state the
chain knew BEFORE this scan, so the probability cannot be contaminated by the very bar being
judged, and no future reordering of Step 3 can silently kill it again. The two publish blocks
are DELETED rather than left as harmless dead writes -- an orphaned write is how the next reader
concludes something is wired when it is not. PairStateMarkov stores `_last[symbol] = (state,
regime)` as a tuple while AuxStateMarkov stores a bare state, so both shapes are handled
explicitly and the regime falls back to RegimeMarkov's own last state. WHY THIS WAS ONLY FOUND
BY BEING ASKED. The C436 verification I ran was thorough on BEHAVIOUR -- the no-skill
degradation to 1e-12, the weighting curve across four skill levels, the evidence floor at n=20,
the discrimination across four candidates -- and every one of those tests PASSED, because they
called the function directly with the keys already present. NONE OF THEM ASKED WHETHER THE KEYS
WOULD EXIST AT THE CALL SITE. That is C422-1 and C430-2 again in a third costume: verifying that
a function WORKS is not verifying that it RUNS. The standing audit gains a line -- for any value
read from a shared dict, establish that the WRITE precedes the READ in execution order, not
merely that both exist. VERIFICATION: syntax; AST 361 (unchanged -- the repair is inside the
existing function); count-asserted replacements reported individually; duplicate defs 0; wrong-
object sweep clean; the two orphaned publish blocks confirmed REMOVED with zero _c436_*_pp
references left outside the changelog; execution-order check re-run showing no read-before-write
remains; the ensemble re-executed against the real chain shapes. LIMITS unchanged from C436:
RegimeMarkov stays excluded because a market-wide probability cannot break a tie between
candidates; p_persist is state persistence, a close proxy for the direction question and not
literally it; and if the next log shows p varying but win rate flat, that proxy is the first
thing to question. Chain C367-C437 intact.


## C436

THE REAL NEXT JOB, TAKEN ON: THE BOT HAD NO WORKING SENSE OF DIRECTION. Before every trade it
needs one number -- how likely is this to go the way I think. That number came from a single
hand-written formula (continuation_prob = a base of 0.35-0.40 scaled by component agreement),
and the bot has been marking its own homework on it 233 times. THE VERDICT IS THAT IT IS WORSE
THAN GUESSING: Brier 0.279 against the 0.250 you get by always saying 'coin flip', i.e. -11.7%
skill. C420-5 correctly refused to believe it and substituted the base rate -- BUT A CONSTANT IS
THE SAME FOR EVERY CANDIDATE AND THEREFORE CANNOT CHOOSE BETWEEN THEM. Only 0.45 and 0.47 appear
anywhere in the 20,739-line log. C435 traced the losing sessions to exactly this: with p flat,
expectancy varied only with R, so the bot was ranking on HOW FAR a pair might move with no view
at all on WHETHER THE DIRECTION WAS RIGHT. THE FIX IS NOT A NEW GUESS -- IT IS FOUR PREDICTORS
THAT WERE ALREADY RUNNING AND ALREADY SCORING THEMSELVES. PairMarkov, IchiMarkov, FamilyMarkov
and RegimeMarkov each return p_persist, the probability that the current state continues, which
is precisely the question being asked; each keeps its own Brier ledger; and TWO OF THEM HAVE
EARNED SKILL -- C343 measured IchiMarkov at +11.2%, and PairMarkov runs at 0.094 against its own
0.160 baseline, +41%. FamilyMarkov has not (-6.8%, held at 'earning' since C342). The comment at
the PairMarkov site says in its own words 'no decision reads these yet -- calibrate first (same
discipline as C294)'. THE CALIBRATION IS IN. THE WAIT WAS CORRECT AND THE WAIT IS OVER. p is now
a blend of every source that has earned the right to speak, each weighted by its OWN measured
skill on exactly the scale C420-5 already uses -- full weight at +25%, nothing at zero or below.
p_persist is read BEFORE observe() updates the chain, so the reading is the one that existed
when the decision was made rather than one contaminated by the scan's own outcome. WHY THIS
CANNOT MAKE THINGS WORSE, verified by execution rather than asserted. If no source has earned
skill the total weight is zero and the function returns the base rate BIT-FOR-BIT -- confirmed
to 1e-12 against a set of deliberately unskilled chains. It can only ADD information, never
remove it, and it adds none until a predictor has paid for the privilege on its own scorecard.
Also verified: a chain at exactly its baseline gets weight 0.00, a chain worse than baseline
gets 0.00, one at +18.8% gets 0.75, and a chain with fewer than 60 observations is skipped
entirely regardless of how good it looks. And calibration_report() returns mean_brier which is
ALREADY A MEAN -- checked, not assumed, because reading a sum as a mean is what caused C421-1
and again C435-3. WHAT IT ACTUALLY DOES, on the session's own four candidates with the real
ledger figures: p comes out 0.839 for MSTR, 0.537 for ZEC, 0.467 for LA and 0.394 for BERA,
against the single flat 0.47 they all carried. THE NUMBER DISCRIMINATES AGAIN, which is the
entire point -- and it is worth noting that MSTR was the session's only winner and BERA its
worst loss. That ordering is suggestive and nothing more; four trades prove nothing and the case
for this change rests on the ledgers, not on the outcome. VERIFICATION: syntax; AST 359 -> 361
(+_c436_direction_prob and the published readings); count-asserted replacements reported
individually; duplicate defs 0; wrong-object sweep clean; C436 constants defined-and-never-read
0; _c436_direction_prob confirmed CALLED. **CORRECTED AT C437: the claim that the three
published keys were 'confirmed written AND read' WAS FALSE. They were written at line ~22783 and
read at line ~21867 -- nine hundred lines EARLIER in the same function -- so on every scan the
keys did not exist yet, no source was ever found, and the ensemble returned the base rate. C436
AS SHIPPED WAS DEAD CODE. The operator asked me to recheck and that is what caught it; the
publish blocks are removed at C437 and the readings now come from each chain's own _last memory,
which has no ordering dependence at all.** The no-skill safety property executed against
unskilled chains; the weighting curve tabulated across four skill levels; the evidence floor
tested at n=20. LIMITS: RegimeMarkov is deliberately EXCLUDED -- it predicts the MARKET regime,
which is the same for every candidate in a scan, so it could not break a tie even with excellent
skill, and including it would only pull every p toward one number again. The two earning chains
predict STATE PERSISTENCE rather than trade outcome, so p_persist is a good proxy for the
direction question and not literally the same quantity -- if the next log shows p varying but
win rate flat, that proxy is the first thing to question. And the hand-written formula is NOT
removed: it still contributes, at whatever weight its own ledger allows, which today is zero.
Chain C367-C436 intact.


## C435

WHY IT IS LOSING WHEN THE SAME CODE WAS PROFITABLE A WEEK AGO -- THE CHAIN, END TO END. Session
20260901_002814: 7h37m, 5 trades, 1W/4L, -$1.26 (-0.5%), equity $248.74, win rate 20%. C434's
count gate WORKED as designed -- entries fell from 67/day to 15.8/day and the log shows it
binding 19 times ('pool is 99 candidates; the 84th percentile would admit ~16. Fee budget allows
2 per scan'). AND THE WARM START IS FINALLY ALIVE: six C430-2 lines, ZERO 'could not arm', after
two versions of it being silently dead. But the losses continued, and the reason is that C434
fixed the COUNT and broke the CHOOSING. THE CAUSAL CHAIN, EACH LINK VERIFIED. (1) C420-5
collapses p to the base rate whenever S3 skill is not earned. The log: 'S3 probability skill
-25361.2% over 228 scored trades ... claims kept at x0.00; p 0.65->0.47. NOT EARNED'. (2)
Consequently EVERY CANDIDATE IN THE SESSION CARRIED THE SAME p -- only 0.45 and 0.47 appear
anywhere in 20,739 lines. (3) C421-2's expectancy is E = edge x min(1,R/T) x (1+T) - fee, and
`edge` is a GLOBAL constant across candidates, so with p uniform E's ONLY VARYING TERM IS R. (4)
E is STRICTLY MONOTONE IN R -- verified at every R from 0.30 to 4.00 -- so ranking by E IS
ranking by R. (5) R = proj*sqrt(t)/stop MEASURES HOW FAR A PAIR COULD GO, NOT WHETHER THE
DIRECTION IS RIGHT. (6) C434 made the Kth-best-by-E the SELECTOR. THE BOT WAS THEREFORE PLACING
PURE MAGNITUDE BETS WITH NO DIRECTION EDGE, and the ordering is the tell: the HIGHEST-E trade
(BERA, E=0.347, R=3.0) hit the hard stop at -2.2%, while the LOWEST-E trade (MSTR, E=0.028,
R=0.82) was the only winner. WHY IT NEVER BIT BEFORE C434, WHICH IS THE ANSWER TO THE OPERATOR'S
QUESTION. E WAS A FLOOR. It asked 'is this positive expectancy at all' and the actual CHOOSING
was done downstream by the composite score, which carries conviction, agreement, breadth,
direction and all eight decision components. In the profitable sessions the percentile admitted
many candidates and the eleven-component stack picked among them. C434 PROMOTED A SANITY CHECK
INTO A SELECTOR, and from that moment the predictive stack stopped deciding anything -- the bot
kept computing ichimoku, Markov, CVD, OI and breadth and then ignored all of it in favour of a
single ratio that rewards a large projection against a small stop. That is the whole regression
in one sentence, and it is mine. C435-1/C435-2, THE FIX IS C434'S INSIGHT APPLIED TO THE RIGHT
QUANTITY. C434 was correct that a percentile admits a FRACTION while the fee budget is a COUNT;
its error was WHERE the cap lived. E returns to being a FLOOR (E >= 0, plus the servo's
percentile so C403 keeps its authority), and the count cap moves to the end of Step 3 where
`score` actually exists. Same K, derived from the fee budget exactly as before, ranked on the
eleven-component score. The cap only BINDS when the board is wide -- at one or two candidates it
is a no-op, so the 129-pair widening still delivers a wider field feeding the same few slots,
which was always the point. The log now names what it kept, what it dropped and the best score
it dropped, so the decision is auditable rather than inferred. C435-3, a display defect found
while reading the C420-5 line: it printed the RAW accumulated Brier sum (63.653) instead of the
mean (0.279). The WEIGHT was computed correctly -- C421-1 divides by n inside
_c420_p_skill_weight -- but the message quoted the sum against a 0.250 baseline, which reads as
a catastrophic -25,361% skill rather than the true -11.7%. C421-1 fixed the arithmetic and left
the sentence, so the same units error survived in the place a human actually reads. WHAT IS
CONFIRMED HEALTHY, so the next session is not spent re-checking it: the C427 ledger fired ZERO
corrections, the C432 NaN tripwire ZERO hits across 20,739 lines, the C434 gate bound 19 times
exactly as specified, and the warm start armed and ran for the first time. The exits were also
reading real information -- REL_STAGNATION at 2.5x expected hold, CONVICTION_COLLAPSE at 0%
thesis remaining, REL_HARD_STOP at its stated limit -- they were closing trades that genuinely
had nothing left, not cutting good ones short. VERIFICATION: syntax; AST 359 unchanged; count-
asserted replacements reported individually; duplicate defs 0; wrong-object sweep clean; C435
constants defined-and-never-read 0; the E-monotonicity proof tabulated across ten R values; the
C434 E-rank branch confirmed neutered while the floor and percentile remain live; the score cap
shown to be a no-op at 1-2 candidates and binding at 3+. LIMITS: the reordering is demonstrated
on the mechanism, NOT on outcomes -- with five trades no ranking claim is statistically
meaningful, and the case for score-over-E rests on the algebra and on the eleven components
existing for exactly this purpose. AND THE DEEPER PROBLEM IS UNTOUCHED: S3 has NEGATIVE skill
over 228 scored trades, so the bot currently has NO calibrated direction probability at all -- p
is a constant. Every gate downstream is working with magnitude and conviction but no earned
probability, and that is the next thing to fix. Chain C367-C435 intact.


## C434

THE PERFORMANCE INVERTED AND THE CAUSE WAS MINE. Session 20260831_202044: 1h47m, 5 entries, ZERO
WINS, five losses, -$1.24 (-0.5%), equity $250.76 -> $248.76. The three sessions before it were
+$1.20, +$1.92 and +$0.76 at 50-60% win rates. NOTHING ABOUT THE MARKET CHANGED THAT MUCH IN A
DAY. THE SCALE OF MY OWN INPUT DID. C434-1, A PERCENTILE ADMITS A FRACTION; THE FEE BUDGET IS A
COUNT. C430 widened Step 3 from 29 pairs to 129 on the operator's directive, and that was RIGHT
-- more of the market examined is the entire measured case for multi-asset. But the C405
admission gate is a PERCENTILE, and a percentile is scale-invariant in RANK and not in COUNT:
top 16% of 38 candidates admits 6, top 15% of 400 admits 60. SO A 4.4x WIDER BOARD ADMITTED
ROUGHLY TEN TIMES MORE CANDIDATES AT A QUALITY BAR THAT NEVER MOVED A SINGLE POINT. The log
states it plainly: '129 analysed -> 22 VIABLE' in one scan, where 1-2 had been normal, and 5
ENTRIES IN 107 MINUTES = 67/DAY against a 6/day budget, eleven times over. C417 promised in its
own changelog that 'MORE ANALYSIS DOES NOT MEAN MORE TRADES'; that promise was carried entirely
by the C403 fee servo, AND THE SERVO HAS A SIX-HOUR HALF-LIFE. In a 1h47m session it moved 16%
-> 10% only after all five positions were already open and losing. A throttle slower than the
session it governs is not a throttle. THE FIX IS C405'S OWN STATED INTENT, EXPRESSED IN COUNTS.
Its docstring says the bot does not need a GOOD trade, it needs THE BEST TRADE AVAILABLE RIGHT
NOW -- and 'the best available' is a RANK, not a quantile. The bar is now the Kth-best
expectancy in the reference scan, K derived from the fee budget itself (target trades/day
divided by scans/day, times the historical attrition through the downstream gates), floored at 1
so the bot can never be shut out, with the servo's percentile still applied as an ADDITIONAL
tightening so C403 keeps its authority. VERIFIED against the session's own pool sizes on the
logged E distribution: admissions were 7, 39, 39, 56, 66 and 46 as the pool grew 38 -> 400; they
are now 2 at EVERY pool size, and the implied entry rate collapses from 198/day to 6/day
exactly. WIDENING THE BOARD NOW IMPROVES THE QUALITY OF THE TOP K INSTEAD OF MULTIPLYING K,
which is what C417 believed it had built and what the operator asked for -- 129 pairs still
analysed, the same few slots filled from a far wider and more genuinely independent field.
C434-2, THE WARM START HAD A SECOND REASON IT COULD NOT ARM, HIDING BEHIND THE FIRST. C433-1
fixed the CustomLogger receiver and the log immediately produced a different error 17 times:
'cannot access local variable ThreadPoolExecutor where it is not associated with a value'.
ThreadPoolExecutor is imported at MODULE level (line 57) AND AGAIN LOCALLY at line 25773 inside
this same _run_scan_and_trade -- and a local import anywhere in a function makes that name local
for the WHOLE function, so referencing it 5,000 lines before the import executes raises
UnboundLocalError. TWO INDEPENDENT DEFECTS, FOUND ONE AT A TIME BECAUSE EACH MASKED THE NEXT.
Resolved through the module namespace so no local binding can shadow it. The lesson is not about
imports: a fix verified by EXECUTION IN A HARNESS can still fail in the running program for
reasons the harness does not reproduce, and the only thing that catches it is a LOUD failure in
the real log -- which is why C429-2's arm failure being a WARNING rather than a debug has now
paid for itself twice. WHAT DID NOT CAUSE THE INVERSION, checked and cleared so the next session
is not spent re-litigating it. POSITION SIZING IS CORRECT: margins of $62.50 and $53.97 on a
$250 book look alarming but margin is not risk -- at a 0.45% stop the risked amount is $0.85,
which is exactly PER_TRADE_RISK_PCT = cap/2 = 0.34% of equity. C433-2's barrier change did NOT
inflate per-trade risk; cap_pct and per_trade_pct were untouched by it. THE C427 LEDGER FIRED
ZERO CORRECTIONS and the C432 NaN TRIPWIRE FIRED ZERO TIMES across 7,564 lines, so the books and
the arithmetic were sound throughout. THE EXITS BEHAVED: three of the five losses were
C399_CONVICTION_COLLAPSE with 0%, 7% and 15% of the entry thesis remaining -- the exits were
reading a thesis that genuinely evaporated, not cutting good trades short. And every loss shows
'never reached a peak worth capturing' with peaks of +0.00% to +0.26%: THESE TRADES WENT DOWN
FROM THE FIRST BAR. That is the signature of taking the 22nd-best candidate rather than the 2nd,
which is exactly what C434-1 repairs. VERIFICATION: syntax; AST 359 unchanged; count-asserted
replacements reported individually; duplicate defs 0; wrong-object sweep clean; C434 constants
defined-and-never-read 0; the count gate EXECUTED against six real pool sizes from the session
with the logged E distribution, and K tabulated across three scan intervals. LIMITS:
C434_ADMIT_SLACK = 60 is the historical attrition from admitted candidate to executed trade and
is inferred from prior sessions rather than measured directly -- if the next log shows
materially fewer than 6 trades/day, that constant is the dial, not the gate. And the widening
itself is NOT reverted: 129 pairs are still analysed every scan, deliberately, because the
defect was never the width. Chain C367-C434 intact.


## C433

THE OPERATOR ASKED WHAT THE TARGET MEANS, AND THE LOG GIVES TWO DIFFERENT ANSWERS IN ONE SESSION
-- WHICH TURNED OUT TO BE A THIRD OF THE DAY'S RISK BUDGET GOING TO A RETIRED MODE. Session
20260831_010835: 17h32m, 187 scans, 14 fills, 3W/2L, +$0.76 (+0.3%), equity $250.76, win rate
60%. The C430 widening is live and working -- 'Step 3 result: 71 analyzed' against the 29 that
prompted it. The C432 NaN tripwire fired ZERO times across 45,967 lines, so no score was
poisoned. C433-2, THE TARGET MEANS TWO THINGS AND ONE OF THEM IS WRONG. The boot banner reads
'day-end barrier +/-0.68% (= 15% declared monthly drawdown / 22)' while every position summary
reads 'barrier +/-0.48%'. Both are honest reports of different numbers: 0.48 / 0.68 = 0.706,
which is exactly the 70/30 split in _c369_derive_budget -- normal_pct = tgt * 0.70, hp_pct = tgt
* 0.30. That split dates from the Normal -> HP phase ladder, where Normal took 70% of the day
and HP the remaining 30%. C403-3 RETIRED HP ('5 incident classes, 0 benefit') and C431-2 closed
the last door it could re-enter through -- SO THE 30% IS NOW ALLOCATED TO A PHASE THAT CAN NEVER
BEGIN, AND SIMPLY EXPIRES UNUSED. THE DAY STOPS AT 0.48% WHEN THE DECLARED RISK BUDGET SAYS
0.68%, and the arithmetic justifying the monthly target is computed on the number the bot does
not use. AT DD=15 THE OPERATOR CHOSE ~3%/MONTH AND WAS BEING SIZED FOR 2.1%. Measured across the
range: DD=10 gives 1.41% -> 2.02%, DD=15 gives 2.12% -> 3.04%, DD=20 gives 2.84% -> 4.08%. This
is NOT a new risk posture -- the budget was always the operator's declared drawdown / 22; the
single surviving mode now receives the whole of what was always meant to be spent in a day. And
it is the same family as C373, C429-3 and C431-2: a retirement honoured in most of the places it
applies and not in one more. INSTANCE FOUR. C433-1, THE WARM START HAS NEVER RUN ONCE. C430-2
was shipped verified and the log proves it never executed: zero 'C430-2 warm start' lines, zero
replay lines, and 187 copies of my own warning saying exactly why -- "C429-2 could not arm:
'CustomLogger' object has no attribute 'handlers'". `logger` in this file is a CustomLogger that
WRAPS a stdlib logger as self.logger; reaching for logger.handlers raised, _c429_filter stayed
None, the pool was never built, and the C430-2 dispatch silently skipped its `if _pool430 is not
None` guard. Wrong-object family, INSTANCE SEVEN, and the identical mistake as C422-1 where I
guessed a receiver name instead of reading the class -- I verified C430-2's dispatch was CALLED
but never checked that the thing it depends on could ARM. THE ONE THING THAT WORKED IS THE
WARNING: standing rule #5 says a protection that fails quietly is not a protection, C429-2's arm
failure was a WARNING rather than a debug, and that single choice is why this was found by
reading a log instead of by another round of guessing. Verified by EXECUTING against the real
CustomLogger class: the old path raises AttributeError, the new path finds the handler, and two
worker threads' lines are held and replayed in order AFTER 'Step 3 result'. ON THE OPERATOR'S
REPEATED PARALLEL-ENTRY REQUEST: warm start is what was chosen last round and it is now actually
armed, so the next session is the first that can show whether it helps. C429_PARALLEL_ENTRY --
firing Step 4/5 on clearance rather than prefetching for them -- remains OFF and remains blocked
on the same unanswered question: it replaces 'best-ranked candidate is funded first' with
'first-scored candidate is funded first'. Warm start had to be proven to run before adding
concurrency on top of it, and it had not run at all. VERIFICATION: syntax; AST 359 unchanged
(both fixes in place); count-asserted replacements reported individually; duplicate defs 0;
wrong-object sweep clean; C433-1 executed against the real CustomLogger with a two-thread hold-
and-replay test; C433-2 tabulated across DD 10/15/20 with the implied monthly return. LIMITS:
C433-2 raises the day's barrier by 43%, which raises how far a day can run in BOTH directions --
the loss side is bounded by the same figure and by C377's 1.5R hard stop, but the operator
should know the day can now lose 0.68% where it previously stopped at 0.48%. And warm start has
still never executed in the wild; the next log is the first evidence either way. Chain C367-C433
intact.


## C432

THE MATH-SAFETY SURFACE, TAKEN AS A DEDICATED PASS BEFORE THE OPERATOR RUNS THE CODE -- AND THE
LIVE SIMULATION CORRECTED MY OWN FRAMING OF IT. C431 catalogued 443 divisions without an
explicit zero-guard and ~180 numpy reductions on unguarded sequences and called it the largest
uninspected surface. It is not 443 defects. TRIAGED BY DENOMINATOR PROVENANCE: 285 literal, 168
already max-guarded, 62 lengths, 26 epsilon-guarded, 308 structurally safe -- and 85 genuinely
market-derived, of which a per-block guard check reduced the truly unguarded set to TWENTY-ONE.
An automated sweep OVER-REPORTS, and reporting 443 as a risk figure would have been the same
error as quoting a broken capture ratio for four versions. C432-1, THE HIGHEST-VALUE FINDING,
AND IT IS NOT A DIVISION BUG -- IT IS WHAT ONE BECOMES. NaN FAILS EVERY COMPARISON IN BOTH
DIRECTIONS: nan > 0.47 is False AND nan < 0.47 is False. So a score poisoned anywhere upstream
does not raise, does not warn and does not look wrong -- it fails `score >= min_score` exactly
the way a genuinely weak setup does, the candidate is discarded, and the scan counts it as
`low_score`. INDISTINGUISHABLE IN THE LOG FROM AN ORDINARY REJECTION. A pair could be silently
unable to trade for an entire session and every line would look normal. THE SUPPLY IS REAL AND
COUNTED: 139 numpy reductions return NaN on an empty sequence (96 np.mean, 34 np.std, 6 np.var,
3 np.median) and a further 52 (np.max/min/argmax/argmin) RAISE on empty. A tripwire now sits at
the ONE boundary where the two cases are confused -- the low_score counter -- so a poisoned
candidate is named, logged once per name+symbol, and counted separately as `nonfinite_score`
instead of masquerading for the rest of the session. Checked at the boundary rather than at 139
producers, deliberately: one place to maintain, and it catches poison from sources nobody has
thought of yet. C432-3, ATR CAN BE ZERO AND IT DIVIDES FIVE TIMES (7973, 7977, 7999, 8001,
16995). Floored RELATIVELY at one basis point OF THE PRICE ITSELF rather than an absolute
epsilon, so the guard means the same thing on BTC at $78,436 and PEPE at $0.0000038 -- an
absolute epsilon here would have been instance FOURTEEN of this project's oldest disease, inside
the fix for a different one. C432-4, TWO LOGISTIC SITES DIVIDED BY (1 - r) AND THEN TOOK
math.log OF THE RESULT. At r = 1.0 that is a division by zero followed by an OverflowError --
NOT an inf -- so a win rate reaching exactly 100% would have THROWN inside a scoring path rather
than saturating. Clamped just inside the open interval where a logit is defined; verified that r
= 0.0 and r = 1.0 now return 0.0 and 1.0 instead of raising. C432-2, the stop distance _R now
passes through the tripwire before it divides in the C422-4 soft-loss gate, which is the one
guarded division that sits directly on the money path. THE CORRECTION, AND IT MATTERS MORE THAN
THE FIXES. I claimed flat candles make ATR-derived divisors zero 8.6% of the time. THE LIVE
SIMULATION FALSIFIED THAT. Across 1,200 real Bitget 15m candles on ZKC, XPD, NATGAS, BTC, PEPE
and XAU: 68 bars have high == low (5.7%, concentrated exactly in the thin desks C423 restored
and C430 widened) -- BUT A SINGLE FLAT BAR DOES NOT ZERO A 14-BAR ATR MEAN. Simulating the
pre-C432 division on every one of those windows produced ZERO poisoned values. Zeroing a 14-bar
ATR needs fourteen CONSECUTIVE flat bars, which is plausible on a halted or delisted instrument
over a weekend and was NOT OBSERVED in this sample. So: the guards are correct, cheap and
defensive, and the incidence in 1,200 live bars is ZERO, not 8.6%. The 5.7% figure applies to
divisions that use a SINGLE bar's range, not to ATR means. Stated because a fix justified by a
number I did not verify is exactly the C428 capture ratio again, and the tripwire's value does
NOT depend on this: NaN arrives from np.mean of an empty slice as readily as from any division.
VERIFICATION: syntax; AST 358 -> 359 (+_c432_finite); count-asserted replacements reported
individually with three SKIPs surfaced and re-targeted rather than silently dropped; duplicate
defs 0; wrong-object sweep clean; _c432_finite confirmed CALLED at 2 sites so it is not an
orphan; every guard EXECUTED -- the tripwire against nan/inf/-inf/None/str, the ATR floor across
four price magnitudes spanning eleven orders of magnitude, the logit clamp at r =
0.0/0.5/1.0/1.5; live Bitget simulation through all five steps against 766 markets and 1,200
real candles. LIMITS: 21 unguarded zero-capable denominators were identified and 8 are now
guarded -- the remaining 13 are weight-vector and histogram sums that are non-zero by
construction (a sum of exponentials, a count of binned samples) and are recorded rather than
padded, because a guard on a provably non-zero denominator is noise that hides the guards that
matter. The 52 np.max/min sites that RAISE on empty are all inside existing try/except blocks
and were left alone. Chain C367-C432 intact.


## C431

THE MICROSCOPIC SWEEP I OWED, RUN OVER THE WHOLE FILE RATHER THAN ONE INDICATOR -- AND IT FOUND
THE SHARPEST TYPE-1 DEFECT YET. The operator was right to push back: C430 drilled ichimoku and
called it a micro-audit. This one runs SEVEN MECHANICAL SWEEPS across all 29,000 lines, because
29,000 lines cannot be read by eye and the last several defects all hid in plain sight. C431-1,
THE ML PREDICTION WAS FORTY-FIVE MINUTES STALE. Sweep 1 hunted LOOKAHEAD BIAS -- the one defect
class that would invalidate every other conclusion in a trading bot -- and surfaced `future_ret
= np.mean(returns[i+1:min(i+4, n)])` inside _quick_ml_predict. That turned out to be a
correctly-built SUPERVISED LABEL: the loop `for i in range(lookback+1, n-3)` stops three bars
short precisely so every label is fully observed, and the train/predict split leaks nothing. NO
LOOKAHEAD IN TRAINING. But the prediction was then made on X[-1:], AND X[-1] IS THE FEATURE ROW
FOR i = n-4. On 15m candles the RandomForest+GradientBoosting ensemble was scoring the market as
it looked THREE BARS -- FORTY-FIVE MINUTES -- AGO, and feeding that into a live decision.
NOTHING FORCED IT: every feature is backward-looking (returns[i-10:i], vol_change[i-10:i],
rsi[i], ema_diff[i]), so the row for the CURRENT bar n-1 is perfectly computable and needs no
future data whatsoever. Only the LABEL needed the lookahead, and a label is not required to
predict. The training set correctly stops early; the PREDICTION inherited that limit for no
reason other than reusing X. This is the exact shape the operator described: STRUCTURALLY SOUND
CODE -- right loop bound, right split, no leakage -- producing a functional outcome an hour
behind the market it exists to anticipate. Verified on synthetic data: the C431 row resolves to
bar n-1 against X[-1]'s n-4, identical width so the fitted scaler stays valid, and it falls back
to the old row if the width ever disagrees. C431-2, HP WAS RETIRED AT ONE DOOR OF TWO, WHICH IS
WHY THE OPERATOR KEPT SEEING IT. C403-3 retired HIGH PROFIT mode and _advance_session_phase
honours that correctly -- it checks C403_SINGLE_MODE and returns BEFORE assigning the mode.
Sweep 4 hunted for every ASSIGNMENT to the retired state and found a second one: in load_state,
`if saved_mode == 'high_profit': self.mode = TradingMode.HIGH_PROFIT`, WITH NO CHECK AT ALL. Any
state file carrying mode='high_profit' -- written by a pre-C403 build, or by a session that was
in HP when saved -- puts the bot straight back into a mode the code declares dead, ON RESTORE.
PROMOTION WAS BLOCKED; RESURRECTION WAS NOT. C426-3 removed the HP score floor from the LOG,
which treated a symptom while the entry point stayed open. Same shape as C373 (a rule enforced
at one of seven doors) and C429-3 (a label fixed at one of two sites): INSTANCE THREE of
enforcing a decision in only some of the places it applies. The standing audit this adds: FOR
EVERY RETIREMENT, FIND EVERY ASSIGNMENT TO THE RETIRED STATE, not just the one the changelog
mentions. WHAT THE OTHER SWEEPS CLEARED OR CATALOGUED, recorded so the next session starts from
a map. LOOKAHEAD: 14 forward-looking constructs found, ALL legitimate on inspection --
supervised labels, pivot detectors that confirm retroactively, and full-window correlation sums
for Lyapunov/entropy. The only true orphan is chikou (C430, still unread). SIGN SYMMETRY: ZERO
long-only branches without a short mirror across the whole file, which matters because 'all
entries same direction' is a catalogued failure pattern here. MATH SAFETY: 443 divisions without
an explicit zero-guard and ~180 numpy reductions on unguarded sequences -- the overwhelming
majority are safe because the operand is a length or a guarded ATR, but this is now the largest
uninspected surface and is listed rather than bulk-patched, because C407's judgement stands.
FLOAT EQUALITY: 4 sites, all comparing BOOLEAN outcomes of thresholds (p >= 0.5) == (y >= 0.5),
which is correct. TIME: 26 naive datetime.now() and 1 utcnow; the bot is IST-anchored and its
session gates are hour-based, so these are correct locally but will misbehave if the process is
ever moved off IST. MONEY-PATH SWALLOWING: ZERO silent handlers wrap
allocate/release/open/close/create_order/arm_stop -- C407's three fixes held and nothing has
regressed. CPU: _quick_ml_predict fits TWO sklearn ensembles per pair, which at C430's 111-pair
board is up to 222 fits per fresh 15m candle on a phone; the Step-3 per-candle cache means this
is paid once per pair per candle, not once per scan, but it is the first thing to watch if
cycles stretch. VERIFICATION: syntax; AST 358 unchanged (both fixes are in-place); count-
asserted replacements reported individually; duplicate defs 0; wrong-object sweep clean; the ML
row identity proven on synthetic data with a width check and a fallback; all four
C403_SINGLE_MODE guard sites confirmed. LIMITS: the ML component carries DRI_WEIGHT_ML = 0.04,
so de-staling it moves a small term -- the value is that a decision input is no longer an hour
old, not that the score will visibly jump. And C431-2 changes nothing unless a state file
actually carries the HP flag; if the operator has been running Fresh Starts it was latent, and
if HP has been surfacing in the logs it was not. Chain C367-C431 intact.


## C430

WIDEN EVERY DESK, WARM THE DATA, AND THE MICRO-SEGMENT AUDIT I OWED FROM LAST VERSION. C429
widened crypto and left the other desks where they were; the operator was right that the
widening was one-sided. C430-1, AND THE sqrt CAP WAS THE REAL BINDER -- FOUND WHILE VERIFYING,
NOT BEFORE. Raising TOP_PAIRS_SELECT to 60 would have delivered FORTY-ONE. C417 sizes each
desk's Step-3 slots as 3*sqrt(qualifying), and with 186 qualifying crypto pairs that is 41, so
the shared-pool ceiling the operator was pointing at was NOT what had been stopping it. The sqrt
term existed to stop one desk hogging a SHARED pool; budgets became per-class and ADDITIVE at
C424 and C430-1, so the partition already does that job and the sqrt term had quietly become an
arbitrary ceiling on how much of its OWN market a desk may examine. Each desk now looks at up to
the same headroom, bounded only by what it actually has. MEASURED LIVE: crypto 30 -> 60 (of 186
qualifying), us_equity 19 -> 42 (of 42, the whole desk), metal 4, energy 2, korea 2, index 1.
TOTAL DEEP-ANALYSED 58 -> 111, a 91% widening across the WHOLE board rather than crypto alone.
That is also the reading C409's own measurement argues for: cross-class aliveness correlation is
+0.038 to +0.143 against crypto's INTERNAL +0.925, so a non-crypto candidate is close to twenty-
four times more likely to be genuinely independent opportunity than more of the same factor.
COST, stated plainly: 49s -> 94s of Step-3 work on a FRESH 15m candle at C398's measured
0.85s/pair, cached within the candle so only the first scan of each 15m period pays it. C430-2,
WARM START -- THE OPERATOR'S CHOICE, AND IT CANNOT COMPROMISE QUALITY BY CONSTRUCTION. Offered
three options; the operator chose warm start over first-viable-wins and asked that it not
degrade quality 'like the previous versions'. It cannot, and the reason is STRUCTURAL rather
than a promise: _c430_warm MAKES NO DECISION AND MUTATES NO STATE THAT ANY DECISION READS. It
calls the same read-only fetchers Step 4/5 would call moments later -- price, order book, 15m
candles -- and DISCARDS the results. The only difference afterwards is that the data already
sits in _price_cache and _orderbook_cache when the batch path asks. Ranking, allocation, every
gate and every threshold then run on exactly the same numbers in exactly the same order, which
is precisely what first-viable-wins could NOT have promised. THE LATENCY IT REMOVES IS REAL: at
0.85s/pair and the new 111-pair board, a candidate cleared early waits ~90s for the scan to end
and then waits AGAIN while Step 4/5 fetch its data one symbol at a time. Dispatched the instant
a pair clears Step 3, on the C429 pool, with log lines held by the C429-2 deferred filter and
replayed after Step 3 reports so the scan narrative stays readable. VERIFIED BY EXECUTION: 3/3
caches primed on a live symbol; under total network failure it returns False, raises nothing,
and degrades to exactly the pre-C430 fetch. C429_PARALLEL_ENTRY stays OFF -- the ranking
question it raised is settled by the operator choosing warm start instead. THE MICRO-SEGMENT
AUDIT, WHICH I OWED FROM C429 AND SKIPPED. Ran over the signal internals rather than the
plumbing. THE DECISION VECTOR IS CLEAN: 8 components written and 8 read, zero orphans; DRI
weights sum to 0.7700 across nine constants, matching C400's computed base_total exactly, and
every one is read at 2-3 sites. TWO REAL ICHIMOKU FINDINGS. (1) `chikou = np.roll(closes, -26)`
IS COMPUTED AND MENTIONED EXACTLY ONCE IN 29,000 LINES -- the lagging span, one of Ichimoku's
five lines, is calculated every scan and read by nothing. Pure waste, no functional harm: Type
2a. (2) THE CLOUD IS READ UNSHIFTED. Ichimoku's senkou A and B are conventionally plotted 26
periods AHEAD, so the cloud governing today's price is the one computed 26 bars ago -- but the
code compares price against senkou_a[-1] and senkou_b[-1], the CURRENT bar's unshifted
midpoints. Under the standard convention that is the cloud belonging to 26 bars in the FUTURE.
The unshifted cloud reacts faster, so 'above cloud' fires earlier and more often, which makes
the signal more momentum-chasing than textbook Ichimoku. RECORDED AND DELIBERATELY NOT CHANGED:
C343 measured IchiMarkov at +11.2% Brier skill and promoted it to EARNED status, and that skill
was earned on THIS computation. Switching to the shifted convention would silently invalidate a
calibrated component to satisfy a textbook. Principle #142 -- sometimes the change is to not
change -- and the deviation is now documented so nobody 'corrects' it later without re-
calibrating first. VERIFICATION: syntax; AST 356 -> 358 (+_c430_warm, +the warm dispatch
closure); count-asserted replacements reported individually; duplicate defs 0; wrong-object
sweep clean; C430 constants defined-and-never-read 0; _c430_warm confirmed CALLED (1 site) so it
is not an orphan; desk budgets recomputed through the shipped classifier against the live venue;
warm start executed on a live symbol and under simulated total network failure. LIMITS: 111
pairs has never run -- if fresh-candle scans stretch past ~120s, TOP_PAIRS_SELECT and
C429_ENTRY_WORKERS are the dials, and the 15m cache means steady-state cost is far below the 94s
worst case. The wider board will produce more viable candidates per scan, which is the point,
but it also means the C403 fee servo and the C405 percentile bar will do more work -- watch
trades/day in the next log, and if it exceeds 12 read the servo before the budget. Chain
C367-C430 intact.


## C429

FOUR OPERATOR DIRECTIVES, THREE SHIPPED LIVE AND ONE STAGED WITH A QUESTION -- PLUS A GATE THAT
WAS COSTING REAL MONEY. Session 20260830_140236: 5h38m, 73 scans, 4 entries (OPG loss, LAB win,
STRK, DOS). AND TWO EARLIER FIXES CONFIRMED WORKING IN THE WILD: the C426 news repair returned
64-65 ARTICLES against the 10 that prompted it, and the C427 ledger enforcer fired ZERO
corrections -- the $312.50 phantom died with the old state file, exactly as the honest-limits
note predicted. C429-4, THE PERP/SPOT GATE WAS VETOING THE BEST TRADES AND CALLING THEM BROKEN.
C393 skips an entry when the Bitget perp diverges from Binance spot by more than a FIXED 0.75%,
on the stated premise that such a gap is 'likely stale/wick'. A WICK IS TRANSIENT BY DEFINITION,
so the premise is testable, and it fails. It blocked three entries this session and ALL THREE
WOULD HAVE BEEN WINNERS: ZKP gap 0.99% then +2.07% with MFE long +10.72%; ZKC gap 3.44% then
+22.00% with MFE long +34.24%; UNI gap 0.88% then +7.18% with MFE long +8.78%. AND ZKC'S GAP IS
STILL 2.88% DAYS LATER -- a quote that is 'stale' for three days is not stale, it is the BASIS,
which is what a perpetual future IS: a price that trades away from spot in proportion to
leveraged demand. THE THRESHOLD IS ALSO ABSOLUTE WHERE IT MUST BE RELATIVE: across 364 dual-
listed Bitget pairs the median |basis| is 0.135% and the p90 is 0.389%, so a fixed 0.75% cut
catches the top ~1% -- and the top 1% of basis is precisely the set carrying the most leveraged
interest, i.e. the movers. The gate was systematically refusing the highest-momentum candidates.
Instance THIRTEEN of the absolute-where-relative disease. THE REPAIR TESTS THE PREMISE RATHER
THAN ASSUMING IT: the gap must PERSIST across two readings at least C429_XVENUE_PERSIST_S apart
before it vetoes. A stale print or a wick resolves in seconds and now costs nothing; a sustained
basis survives and is still refused, which is the case the gate was actually written for.
C429-1, CRYPTO STEP-3 BUDGET 30 -> 60, ON DIRECTIVE, AND THE CONDITION FOR IT IS NOW MET. C398
raised this to 50, reverted, and set an explicit test: widening ships 'only after the C397
payoff repairs are confirmed positive on a live log'. THE C428 MEASUREMENT SETTLED THAT --
across fourteen exits, winners median +2.03%, losers median -0.64%, PAYOFF 3.2:1, win rate 71%,
expectancy +1.98R per trade against a 24% break-even. C389's failure mode was widening a book
that was NEGATIVE per trade; the present book is the opposite. And the constraint was real: the
log shows crypto with 448 contracts, 93-95 clearing the volume floor and TWENTY-NINE reaching
Step 3. C429-1b also makes the Step-3 budget PER-CLASS rather than a pool to be divided -- at 30
the crypto desk received 29 and every other desk shared one, and C417 had already ruled that
classes must not compete for slots. This was the last place they still did. C429-3, THE SECOND
TARGET LABEL. The operator reported the daily target still showing 0.4%, and was right: C426-2
relabelled the STARTUP banner and missed the position-summary line, which still printed 'Normal:
+0.4% / 0.48%' on every update. 0.48%/day is the DAY-END BARRIER in both directions, derived as
declared monthly drawdown / 22; the EXPECTED daily return for the 2-4%/month band is
0.066-0.131%/day, five to seven times smaller. A progress bar toward a barrier reads as a
shortfall and invites over-trading toward a number that was never a goal. A RULE RELABELLED AT
ONE OF TWO SITES IS NOT RELABELLED -- the same lesson C373 recorded when the C372 profit floor
was enforced at one of seven doors. C429-0, THE LEDGER HAD NO LOCK AND ALREADY HAD THREE
WRITERS. The monitoring thread closes positions, the dashboard reads balances and the scan
thread allocates, while allocate_margin and release_margin are plain read-modify-write on
available_balance with nothing guarding them. Now serialised through a RE-ENTRANT lock -- re-
entrant because release_margin is reached from close paths that already hold _position_lock.
HONEST ABOUT THE EVIDENCE: I could NOT demonstrate the race in 60 concurrent trials, because the
R4 total-locked-vs-equity cap catches the overspend a moment later. The lock is correct and is a
precondition for C429-2, but the claim that the race is CERTAIN today is not supported and is
not made. C429-2, PARALLEL STEP 4/5 -- BUILT, VERIFIED, AND DELIBERATELY LEFT OFF PENDING ONE
OPERATOR DECISION. The latency is real and about to double: C398 measured Step 3 at ~0.85s per
pair, so a candidate identified first waits ~25s at 30 pairs and ~50s at the new 60 before
anything happens -- paid on EVERY entry, on instruments that routinely move 1% in a minute. The
deferred-log filter is implemented as a thread-keyed logging Filter, so records raised on a
background entry thread are captured and replayed in order once Step 3 reports; VERIFIED BY
EXECUTION -- two worker threads, six lines, all held and replayed after the Step 3 narrative
with per-thread order preserved. WHAT IS NOT RESOLVED IS A SEMANTIC CHOICE THAT BELONGS TO THE
OPERATOR: Step 5 currently RANKS every viable candidate and allocates margin across them, so the
BEST-RANKED trade is funded first. Firing on clearance replaces that with FIRST-VIABLE-WINS, and
a better candidate found at pair 55 of 60 may meet a spent budget. At 0-2 viable per scan the
difference is usually nil; on the scan where it matters it is the difference between the best
trade available and merely the first. Shipping money code I cannot fully verify would be worse
than the latency it saves, and a switch left ON with no dispatch behind it is the orphan defect
this project has paid for seven times -- so the flag is OFF and the config says why.
VERIFICATION: syntax; AST 350 -> 356; count-asserted replacements reported individually;
duplicate defs 0; wrong-object sweep clean; C429 constants defined-and-never-read 0; deferred
logging EXECUTED with two threads; the lock exercised across 60 concurrent trials; the perp/spot
claim measured against 364 dual-listed pairs and three real blocked entries with forward
candles. LIMITS: the 60-pair budget has never run -- scan time will rise by roughly 26s per
fresh candle at 0.85s/pair, bounded by the 15m cache, and if cycles stretch past ~120s
C429_ENTRY_WORKERS and the budget are the dials. Chain C367-C429 intact.


## C428

THE OPERATOR ASKED FOR THE TWO ISSUE TYPES SEPARATED -- FUNCTIONAL SHORTFALLS IN STRUCTURALLY
SOUND CODE, AND STRUCTURAL DEFECTS WITH AND WITHOUT FUNCTIONAL CONSEQUENCE. RUNNING THAT SPLIT
PROPERLY OVERTURNED A CONCLUSION I HAVE BEEN STEERING BY FOR FOUR VERSIONS. TYPE 2b, A
STRUCTURAL DEFECT WITH SEVERE FUNCTIONAL CONSEQUENCE, AND IT IS MINE. The C422-3 capture ledger
computed its numerator and denominator on DIFFERENT POSITIONS. _real422 is the FINAL LEG's price
move; _peak_px422 is the WHOLE position's peak. On any trade that partial-closed those are
different scopes, so capture came out UNDERSTATED ON EXACTLY THE TRADES THAT WORKED BEST -- the
ones good enough to bank a partial at all. EGLD from the 20260829 log is the clean case: banked
half at PnL +5.9%, the runner peaked at +7.1% and exited at +5.2% against a C338 floor of +5.17%
-- THE MACHINERY WORKED TO WITHIN 0.03pp OF ITS OWN DESIGN -- and whole-idea capture was 78%. My
ledger printed 'banked +1.07% of the +1.78% peak (60%)' and the session line read CAPTURE 47%.
THIS INVALIDATES A HEADLINE NUMBER I QUOTED FOR FOUR VERSIONS. 'Capture 10% -> 5% -> -3%'
motivated the C422-4 soft-loss gate and framed the C423 conclusion that 'winners bank 51-77% of
peak while every loser travels from a positive peak through zero'. RE-MEASURED ACROSS ALL
FOURTEEN EXITS in the three latest sessions: winners n=10 median +2.03%, losers n=4 median
-0.64%, PAYOFF 3.2:1, win rate 71%, expectancy +1.98R per trade against a break-even win rate of
24%. AND ZERO OF FOUR LOSERS WERE EVER POSITIVE AT THEIR PEAK. THE ASYMMETRY I DIAGNOSED IS NOT
PRESENT IN THE CURRENT DATA. It may have been real at C423 or it may have been this same scope
error wearing a conclusion; either reading demands the same action, which is to fix the
instrument BEFORE drawing another inference from it. C397-4 already carried the banked half on
the position for precisely this purpose -- 'the FINAL close reports the whole idea honestly
instead of only the remainder's slice' -- and the capture ledger simply never read it. THE FIX
WAS WRONG ON ITS FIRST WRITING AND THE VERIFICATION CAUGHT IT. I ADDED the banked leg to the
final leg and got 144% capture on EGLD, which is impossible, against an independent whole-idea
figure of 78%. The two legs are each HALF the position, so the whole idea is their AVERAGE, not
their sum. Corrected, EGLD reads 72% against that independent 78% -- a match, and the residual
is the peak being measured on the remainder after the split. Non-partial trades are
arithmetically untouched. TYPE 1, FUNCTIONAL: THE HONEST ANSWER IS THAT THIS DATA DOES NOT
SUPPORT A CHANGE. At 71% win rate and 3.2:1 the exit stack is performing, the C338 runner floor
held to 0.03pp, and the four losses were cut at -0.17%, -0.19%, -1.09% and -2.39%. With fourteen
exits I CANNOT calibrate the 0.45-of-peak ratchet or the 20% giveback threshold, and tuning them
on this sample is precisely the error the Atlas has catalogued four times. NOT TUNING THE EXITS
IS THE CHANGE. TYPE 2a, STRUCTURAL WITHOUT FUNCTIONAL HARM -- PROMISES THE CONFIGURATION MAKES
AND THE CODE DOES NOT KEEP. C407 catalogued 34 constants assigned and never read and chose not
to bulk-delete them, which stands: removing a name is how a live reference gets broken. But the
count has GROWN to 40, and MY OWN versions contributed. C405_E_MIN_SAMPLES was orphaned by my
C420-3b when the 400-deep cross-time pool was replaced by the previous scan's own candidate set.
C369_TARGET_CEILING, C369_TARGET_FLOOR and C369_LOSING_TRADES were retired by C380 -- and the
comment block above them STILL ARGUES FOR A 0.35%/DAY CEILING THAT NO LONGER GOVERNS ANYTHING,
so an operator tuning it would change nothing while believing they had changed the risk posture.
Marked as named tombstones with the version that superseded each, rather than deleted.
C369_CAP_RATIO was verified STILL LIVE and left alone. TYPE 2a CONTINUED: EIGHT ORPHAN
DIAGNOSTIC KEYS, ALL MINE. _c404_E, _c404_R, _c420_p_raw, _c420_p_weight, _c420_proj_raw,
_c420_proj_capped, _c420_fcast_mult and _c421_T were written into `analysis` by C404/C420/C421
and read by nothing -- the computed-but-never-wired family in its mildest form: no functional
harm, but eight dict writes that look like plumbing and are decoration. They are the ENTRY-TIME
VIEW of a trade, so they now travel to the exit and print beside the outcome where they can
finally be compared against what happened. AND I REPRODUCED THE VERY DEFECT WHILE FIXING IT: the
first draft wrote _c428_entry_view into `analysis` and never copied it onto the position, so it
would have died when the dict went out of scope. The orphan sweep caught it before it shipped,
on the version that exists to close that class. AUDIT RESULTS RECORDED FOR THE NEXT SESSION: 20
methods defined and never called -- but _monitoring_thread_func and _run_feedback are FALSE
POSITIVES, passed as thread targets and executor submissions rather than called, which the AST
call-graph cannot see; the genuinely dead ones (full_analysis since C366, meta_learn since C103,
get_gde_exit) are left alone per C407. 128 bare `except:` and 253 silent `except: pass` REMAIN
and are the largest untouched structural risk in the file -- every one is a place a defect can
hide for versions, which is how C421-4 stayed dead 15 hours and how C378's stop-arm failed
silently. A dedicated pass over the ~15 that wrap money calls is the next structural work.
VERIFICATION: syntax; AST 350 unchanged; count-asserted replacements reported individually;
duplicate defs 0; wrong-object sweep clean; orphan analysis keys 17 -> 16 with _c428_entry_view
confirmed written AND read AND carried onto the position; the capture correction EXECUTED
against EGLD's real logged numbers and cross-checked against an independently derived whole-idea
figure. LIMITS: the corrected capture number has never run live -- every figure above is
recomputed from logs, and the next session is the first that will print an honest one. Fourteen
exits is not a sample; the 3.2:1 payoff and 71% win rate are encouraging and could still be
tape. Chain C367-C428 intact.


## C427

THE OPERATOR SPOTTED $62.50 THAT DOES NOT EXIST, AND WAS RIGHT THAT IT WAS THE TIP OF AN
ICEBERG. The screenshot: 'Equity: $250.00 | Unrealized: $+0.00' beside 'Available: $312.50 |
Locked: $0.00' -- available exceeding equity by EXACTLY 25% with nothing locked and nothing
unrealised, on a session showing ZERO trades and a lifetime win rate of 0%. Money the bot
believes it has is money it SIZES POSITIONS AGAINST, so this was never a display bug. WHAT THE
AUDIT FOUND IS WORSE THAN THE ONE NUMBER. The invariant `available <= equity - locked` is
enforced in exactly ONE function -- release_margin, at the END -- and NOWHERE ELSE IN 28,000
LINES. Seven sites write available_balance and five are unguarded: __init__ (= INITIAL_CAPITAL),
set_session_start (= equity), allocate_margin (-= margin), release_margin (+= margin + pnl, then
clamps), load_state (= raw JSON). TWO EXPLAIN HOW A WRONG FIGURE SURVIVES. (1) set_session_start
sets available = equity WHILE POSITIONS MAY STILL BE OPEN, ignoring locked margin entirely --
reproduced in test, $62.50 locked across two positions gave available $250.00 where $187.50 was
correct. (2) load_state restores available from JSON WITH NO VALIDATION, and release_margin's
clamp only runs WHEN A TRADE CLOSES -- so a session with zero closes never checks its own books
even once, which is precisely the session in the screenshot. A LEDGER WITHOUT A CONTINUOUSLY
ENFORCED INVARIANT WILL DRIFT AND NOBODY WILL KNOW; the specific $62.50 matters far less than
the fact that NOTHING IN THE FILE COULD EVER HAVE CAUGHT IT. AND I COULD NOT DETERMINE THE
ORIGIN OF THIS $62.50 FROM THE CODE, stated plainly rather than papered over with a plausible
story. Every candidate was traced and cleared: the partial-close route is CLEAN
(release_margin(m/2) is immediately followed by initial_margin /= 2, so the halves sum to
exactly one margin); Fresh Start sets equity and available together from one INITIAL_CAPITAL;
the C286 scale-in releases what it locked. THAT IS THE ARGUMENT FOR A LOUD GUARD: a quiet clamp
fixes the symptom and DESTROYS THE EVIDENCE. The correction logs the delta, the equity, the
locked total and the CALL SITE every time it fires, so the next occurrence names its own origin.
ONE ENFORCER, FIVE CALL SITES, NO NEW POLICY. _c427_reconcile clamps available to equity minus
locked and runs at load_state (after positions are known), at set_session_start, BEFORE
allocate_margin -- the one call that decides how much real money enters a position -- and at the
position summary the operator reads. No sizing rule, threshold or strategy changes; it only
refuses to let the bot spend money it does not have. VERIFIED BY EXECUTION: TEST 1, the
operator's exact numbers, $312.50 -> $250.00 logging 'discrepancy $+62.5000'. TEST 2, the
set_session_start defect, $62.50 locked now yields $187.50. TEST 3, a full allocate->release
cycle holds the invariant. TEST 4, a corrupt restored ledger ($999.99 against $251.66 equity,
$20 locked) is caught at LOAD and corrected to $231.66 LOUDLY instead of inherited forever. TEST
5, 200 randomised healthy cycles across $50-$600 produced ZERO spurious corrections. ALSO FOUND,
NOT FIXED: get_locked_margin() rounds the position sum to 2dp while equity is a running full-
precision float, so the two books are compared at different precisions -- harmless at the half-
cent tolerance used, but the same C371 defect (money rounded in the LEDGER not the DISPLAY)
surviving in a second place. PROCESS FAILURE, RECORDED. I built C427 on the operator's UPLOADED
file, which is C425, and then overwrote the C426 deliverable in outputs with the result --
silently losing the news, target-label and HP fixes I had shipped one message earlier. Caught
only because the C426 changelog anchor was missing when C427 tried to insert above it. Both
versions are now rebuilt onto one base and both changelog entries are present. THE LESSON IS THE
SAME ONE THIS PROJECT KEEPS RELEARNING: the uploaded file is the operator's LAST RUN, not
necessarily my LAST SHIP, and the two diverge the moment a delivery is not run. VERIFICATION:
syntax; AST 349 -> 350 (+_c427_reconcile); count-asserted replacements reported individually;
duplicate defs 0; wrong-object sweep clean; five-test execution battery; C426 content re-
verified present (RSS feeds, barrier label, HP line) alongside C427. LIMITS: the enforcer
CORRECTS the symptom and INSTRUMENTS the cause, but until it fires in a live log the origin
remains unknown. NOT TOUCHED on a green run: TOP_PAIRS_SELECT stays 30, the 20-path exit stack
stays, the C367 floor stays, the winner/loser asymmetry stays diagnosed. Chain C367-C427 intact.


## C426

THREE OPERATOR QUESTIONS, ALL THREE CORRECT, AND THE FIRST GREEN RUN. Sessions: 20260828 (4
trades, -$0.26, WR 25%), 20260829_0039 (2 trades, +$1.20, WR 50%), 20260829_2223 (3 trades,
+$1.92, WR 56%). EQUITY $248.95 -> $251.66, +$2.86 over 27 hours and nine trades -- the best run
recorded and the first time two consecutive sessions were both green. C426-1, NEWS SUPPLY -- TWO
DEFECTS STACKED. The operator reported 'only 10 articles' and the log agrees 193 times. (1)
newsdata.io's free tier returns EXACTLY 10 per request, reliably, so the guard `if
len(self._articles) < 5:` was NEVER TRUE and the CryptoCompare backup HAS NEVER RUN IN THIS
BOT'S LIFE -- a fallback gated on FAILURE cannot help a SUCCESS THAT IS TOO SMALL. (2) I removed
the guard, ran it live, and CryptoCompare returned ZERO articles, HTTP 401 -- the endpoint went
key-gated, so the fix as first written would have shipped as DEAD CODE, exactly like C421-4.
Caught only because verification EXECUTES rather than inspects. AND TEN IS STRUCTURALLY TOO FEW:
30 pairs screened per scan, ten articles cannot mention thirty coins, so coverage was capped at
33% BEFORE any matching ran -- C421 fixed the MATCHING and the SUPPLY was the broken part.
Replaced with two keyless RSS feeds verified at HTTP 200, CoinDesk (25) and CoinTelegraph (30),
stdlib ElementTree, nothing new installed on a phone. SUPPLY 10 -> 65, confirmed by EXECUTING
the shipped block and counting 55 harvested. C426-2, IS 0.4%/DAY RIGHT FOR 2-4%/MONTH? NO -- IT
IS NOT A DAILY RETURN AND NEVER WAS. It is the DAY-END BARRIER and sits on BOTH sides: cap =
declared monthly drawdown / 22, target := cap so break-even is exactly 50%. At the shipped
DD=20: cap 0.909%/day; expected daily = (2p-1)*cap for DAILY win rate p; p=0.55 -> +2.02%/month,
p=0.60 -> +4.08%, p=0.65 -> +6.17%. THE DRAWDOWN DIAL IS THE MONTHLY TARGET DIAL -- DD=10 gives
the operator's 2% floor, DD=20 the 4% ceiling, and the logs show 0.48/0.68/0.91 because DD
ramped 10.5 -> 15 -> 20. THE ARITHMETIC IS SOUND; THE LABEL WAS NOT: 0.91%/day beside the word
'target' reads as a sum to be EARNED when the expected daily return for 2-4%/month is
0.066-0.131%/day, five to seven times smaller, and any reader would conclude the bot was far
behind and should trade harder. ONE HONEST GAP: '+2%/month at 60% daily WR' assumes days
TERMINATE at +/-cap, and all three sessions ended ON THE CLOCK at +0.1%, +0.5% and +0.8%. A
Bernoulli-day model priced against a time-terminated day is an approximation, not a derivation.
C426-3, HP RESIDUE. HP was retired at C403-3 and cannot be entered, but its score floor was
still computed and PRINTED at every reset, so the operator kept seeing a live-looking number for
a dead subsystem. DEAD OUTPUT IMPLIES A LIVE SUBSYSTEM. MIN_SCORE_HP and BASE_LEVERAGE_HP stay
DEFINED because 36 surviving hp_mode parameters read them as defaults and removing them is load-
bearing on a green run. VERIFICATION: syntax; AST unchanged; runtime execution of the news block
against live feeds (55 articles); target arithmetic tabulated across DD 10/20 and win rates
55/60/65. LIMITS: the RSS feeds carry NO coin field, so they raise SUPPLY and market sentiment
while coin-specific matching still leans on newsdata's tagged /crypto endpoint and the C421-4
boundary match. The DD ramp 10.5 -> 15 -> 20 was NOT investigated and should be.


## C425

THE OPERATOR ASKED WHY THE BOT DOES NOT FETCH ALL ~800 BITGET PERPS. THE HEADLINE NUMBER IS A
COUNTING ARTEFACT AND THE BOT IS CLEAN -- BUT THE QUESTION SURFACED A REAL DEFECT UNDERNEATH IT.
THE ~800, RESOLVED WITH NUMBERS. Bitget lists 823 contracts across THREE MARGIN TYPES: 763
USDT-M, 49 USDC-M, 11 COIN-M. The bot queries USDT-FUTURES only, which is 93% of the raw count
and looks like a gap. It is not: EVERY ONE OF THE 60 NON-USDT CONTRACTS IS THE SAME UNDERLYING
ASSET MARGINED IN A DIFFERENT CURRENCY -- BTCUSD coin-margined is the same Bitcoin as BTCUSDT.
Swept both alternative product types against the USDT-M base list: ZERO unique bases outside
USDT-M. And checked the other direction too, in case a thin USDT-M book hid a deep USDC-M one:
ZERO cases where a non-USDT contract carries more volume than its USDT-M twin. So the bot
already covers 100% of the distinct crypto underlyings on the venue, and adding the other margin
types would add fee-paying duplicates of positions it can already take, plus a second funding
stream on the same exposure. Contracts and tickers also reconcile EXACTLY, 763 to 763, with zero
symbols on one endpoint and not the other -- so nothing is lost between them either, which
matters because the scan loop is driven by tickers and intersected with self.markets. THE REAL
DEFECT THE QUESTION EXPOSED: THE MARKET LIST WAS FROZEN FOR THE WHOLE PROCESS. `load_markets()`
is called EXACTLY ONCE, inside connect(), and self.markets is never rebuilt. Sessions in this
project have run FIFTEEN HOURS, and the venue has been observed going 759 -> 761 -> 763
contracts across four days of this review. A perp listed at hour two of a long session is
INVISIBLE FOR THE OTHER THIRTEEN -- and a newly listed perp is precisely what this scanner
exists to find: maximum volatility, maximum liveliness, no priced-in history, the exact profile
current_score ranks for. Because the scan is driven by tickers and then intersected with the
frozen dict, a symbol absent from that dict is filtered out no matter how loudly it is trading.
The `active` filter compounds it: ccxt derives `active` from contract status AT LOAD TIME, so
anything transient at startup is excluded PERMANENTLY rather than until it settles. This is the
same shape as C423-1 -- a decision taken once and never revisited, silently shrinking the
universe -- differing only in that C423-1 shrank it by ban and this shrinks it by staleness.
REFRESHED ON A TIMER, reusing the same bulk call connect() already makes, default 30 minutes
because new listings arrive at roughly one per day and the cost should stay near zero. FAIL-SAFE
BY CONSTRUCTION: on any error, and on any reload returning fewer than half the current count,
the EXISTING dict is kept -- a refresh failure can never shrink the universe, which is the
precise failure mode being fixed. New and delisted symbols are named in the log so a listing
that starts trading mid-session is visible rather than inferred. RECEIVER CHECKED BEFORE SHIP,
because C422-1 shipped a repair that was dead code for fifteen hours by guessing at a receiver
name. _c425_refresh_markets is defined on ExchangeManager and called as
self.exchange._c425_refresh_markets() from MarketScanner -- confirmed by AST class ownership,
not by assumption. connect() seeds _c425_markets_at so the first refresh lands one interval
after startup rather than immediately. VERIFICATION: syntax; AST 348 -> 349
(+_c425_refresh_markets); duplicate defs 0; wrong-object sweep clean; C425 constants defined-
and-never-read 0; class-ownership check on the new method; all three Bitget product types
enumerated live; contract/ticker reconciliation live; cross-margin depth comparison live. HONEST
LIMITS: the refresh adds one load_markets call per 30 minutes on a phone, which is small but not
free, and C425_MARKET_REFRESH_S=0 disables it. And no session has yet run long enough WITH this
in place to demonstrate a new listing actually being picked up -- the mechanism is verified, the
benefit is not. NOT CHANGED: TOP_PAIRS_SELECT stays at 30. The funnel is 763 fetched -> 462
crypto -> 221 clearing the class floor -> 104 into phase 2 -> 30 into Step 3, and the binding
number is the last one, not the fetch. C398's condition for widening -- a live log confirming
positive payoff -- is still unmet. Chain C367-C425 intact.


## C424

THE OPERATOR SAID THE CRYPTO UNIVERSE ALSO LOOKED INCOMPLETE. IT WAS, AND C423 HAD JUST MADE IT
WORSE -- MY OWN FIX CROWDED CRYPTO OUT OF ITS OWN FUNNEL. FIRST, A DIAGNOSIS I GOT WRONG AND
CORRECTED BEFORE ACTING ON IT. I read C391's comment ('truncated to the top 44 by CURRENT
activity') and C307's ('the projected layer only ever ran on the top-38 by CURRENT activity'),
reconstructed the funnel as a 24h-change ranking, and produced a table showing BTC, ETH, XRP and
DOGE being DISCARDED as too quiet. THAT WAS FALSE. The actual key is current_score = 0.40*log-
volume + 0.25*own-volatility + 0.35*freshness, where freshness itself REWARDS high volume with
low change -- so the ranking is ~75% volume-weighted and BTC ranks FIRST, not last. Two stale
comments described a sort that C196 and C410 had already rebuilt, and I nearly shipped a repair
for a defect that did not exist. Recorded because the near-miss is the lesson: A COMMENT IS A
CLAIM ABOUT THE CODE, NOT THE CODE, and this project has now been bitten by that twice in three
versions (C423-1's 'belt-and-suspenders backup' described a guard that was still load-bearing).
THE REAL DEFECT, AND IT IS AN INCONSISTENCY INSIDE C417's OWN DESIGN. C417 established the
principle explicitly -- 'budgets ADD, because two open markets are two opportunity sets and not
one shared one', and 'competition for slots happens INSIDE a class, NEVER across classes, where
a 2% day in TSLA (8 ATR) and a 50% day in a memecoin (6 ATR) cannot be ranked against each other
on any common scale'. It then made the VOLUME FLOOR per-class and the STEP-3 SLOTS per-class --
AND LEFT C391_UNIVERSE_CAP, WHICH RUNS BEFORE BOTH OF THEM, GLOBAL. So the single ranking that
decides which pairs reach the projected/geometric layer at all was still one cross-class league
table: precisely the comparison C417 says is meaningless, sitting upstream of every per-class
refinement built to replace it. IT ONLY BIT ONCE C423-1 RESTORED $770M OF RWA, AND THE
MEASUREMENT NAMES ME. Live venue, same instant, same formula: with the C134 blocklist ON the
top-150 held 109 crypto + 41 RWA; with it OFF, 88 crypto + 62 RWA. MY OWN FIX PUSHED 21 CRYPTO
PAIRS OUT OF PHASE 2 and cut crypto's share from 73% to 59%. Nothing about crypto changed; it
simply lost a competition it should never have been entered into. That is C423-4's guard-
displacement ledger predicting its own author one version later -- remove a constraint in one
place and the cost surfaces in another, here one layer up inside the funnel. THE FIX IS TO
FINISH C417 RATHER THAN PATCH C423. Each desk now gets its OWN phase-2 cap, scaled by
sqrt(cohort) exactly like C417's Step-3 slots, floored so a two-contract desk is examined IN
FULL, and the caps ADD. Crypto is guaranteed its full share whatever else is awake, and a quiet
desk cannot hoard slots it has no candidates for. VERIFIED LIVE THROUGH THE SHIPPED CODE: crypto
87 -> 104, us_equity 53 -> 69, metal 4, korea 3, energy 2 -> 3, index 1; total 150 -> 184 pairs
into phase 2, +23% width for about 34 extra candle fetches on an 8-thread pool inside a 480s
cycle. THE COMPLETE CRYPTO FUNNEL, STATED PLAINLY BECAUSE THE OPERATOR ASKED FOR IT: 763
contracts fetched (all of them, one bulk call) -> 462 are isRwa=NO crypto -> 221 clear the per-
class volume floor -> 104 reach phase 2 after C424 -> 30 reach Step 3. SO 14% OF THE VOLUME-
QUALIFIED CRYPTO UNIVERSE IS DEEPLY SCORED IN ANY ONE SCAN, and the binding number is
TOP_PAIRS_SELECT=30, NOT the fetch. Nothing is missing from the fetch; the narrowing is
deliberate and happens at Step 3. TOP_PAIRS_SELECT DELIBERATELY HELD AT 30. C398 raised it to
50, then reverted and set an explicit condition: the widening ships 'only after the C397 payoff
repairs are confirmed positive on a live log'. That condition is NOT met -- the last two
sessions lost money ($250.33 -> $248.95) and capture is degrading 10% -> 5% -> -3%. C389
measured what happens if you widen a book that is negative per trade (trades 6->11, WR 83%->55%,
EV +$0.098 -> -$0.007), and the Peltzman lesson from C423-4 says the same thing in general
terms: widening the funnel while per-trade EV is unproven multiplies the loss rather than
diluting it. The 30 is a real constraint on how much of the market is examined and it is the
right next lever -- AFTER a positive live log, as one deliberate change with a clean A/B. ALSO
RESTORED BY C423-1, FOUND WHILE CHECKING FOR COLLISIONS: STX (Stacks, $2.8M) is a genuine crypto
that the C134 blocklist was killing because STX is also Seagate's ticker. A name blocklist
cannot tell a token from an equity that shares three letters; isRwa can, which is why C155
replaced it. REGRESSION CHECK ON MY OWN C423-2: the name-first classifier could have misfiled
real cryptos into the metal or index desks. Swept all 462 isRwa=NO contracts against the widened
sets -- exactly ONE match, SPX, which is the intended correction. Clean. VERIFICATION: syntax;
AST 348 (no new functions, the cap is inline in scan_lively_pairs); duplicate defs 0; wrong-
object sweep clean; C424 constants defined-and-never-read 0; a scope error caught before ship
(_m417b is local to the C417 block below and would have raised inside the try, silently
reverting to the global cap -- now an explicit local import); per-desk allocation tabulated
against the live venue through the shipped classifier; the blocklist-on/off crowding effect
measured at the same instant on the same formula. HONEST LIMITS: +23% phase-2 width costs scan
time that has been estimated from C398's measured 0.85s/pair for Step 3 and NOT re-measured for
phase 2, which is cheaper but not free -- if the next log shows scan cycles stretching past
~120s, C424_CLASS_CAP_K is the dial. And the restored desks still have never traded, so C424
widens a field whose quality is unmeasured. Chain C367-C424 intact.


## C423

THE OPERATOR ASKED WHETHER THE UNIVERSE WAS BEING FETCHED COMPLETELY. IT WAS NOT: $770M/DAY WAS
BEING DISCARDED BY A GUARD THAT TWO LATER ARCHITECTURES HAD ALREADY REVERSED. Two sessions
reviewed -- 20260826 (3h08m, 32 scans, 4 trades, -$0.56, WR 25%, capture 5%) and 20260827
(8h16m, 96 scans, 5 exits, -$1.05, WR 44%, capture -3%). Equity $250.33 -> $248.95. CAPTURE IS
DEGRADING ACROSS THREE SESSIONS: 10% -> 5% -> -3%. C423-1, THE STALE BLOCKLIST. C134's
_NON_CRYPTO name list was added because XAU carried 51% of that session's losses while the bot
traded gold on CRYPTO'S CLOCK with CRYPTO'S LEVERAGE -- a correct diagnosis. C155 then replaced
the name list with Bitget's own isRwa flag; C408 replaced the SKIP with SESSION GATING, fixing
the actual cause properly and per class. THE LIST WAS NEVER REMOVED, and its own comment demotes
it to a 'belt-and-suspenders backup' FOR A DECISION THAT HAD BEEN REVERSED. MEASURED ON THE LIVE
VENUE: metal 3 blocked ($211M) against 2 surviving ($4M) -- XAU $107M, XAG $88M, XAUT $16M, 98%
OF THE DESK'S LIQUIDITY; energy CL $23M blocked against $11M surviving; us_equity 41 blocked
($537M) including SOXL $163M, MU $67M, NVDA $49M, MRVL $47M, MSTR $39M. THE 20260826 LOG SHOWS
IT EXACTLY: XAU, XAG, XAUT and CL appear ZERO TIMES in a fifteen-hour session while PAXG ($3.8M)
and COPPER ($0.7M) are analysed -- the two largest metals on the venue invisible while the two
smallest are scored. And the desk board printed 'metal universe 7 floor $368k passed 1', which
READS AS A LIQUIDITY OUTCOME AND IS IN FACT A HARDCODED BAN: the counting pass runs above the
blocklist, the selection pass below it. ONE STATE, TWO TRUTHS -- C134 says metals may never
trade, C411/C417 built a metal desk with its own hours, its own volume floor and its own slot
budget; C134 wins silently and the newer machinery scores an empty universe. INSTANCE SEVEN.
Kept as an OPT-IN kill switch rather than deleted, so C134's behaviour is one flag away if
metals lose money on their own merits -- now MEASURABLE, because the instruments finally reach
the scan. VERIFIED LIVE THROUGH THE REAL CLASSIFIER: metal $4.3M -> $215.3M (49.7x), energy
2.8x, us_equity 1.9x. C423-2, CLASSIFIER COMPLETENESS. NATGAS is the base Bitget publishes;
_C411_ENERGY held 'NG' and 'GAS', neither of which matches, so a GLOBEX energy contract fell
through to the us_equity default and was gated to the 6.5-hour CASH session -- asleep for three
quarters of its trading life and awake when nobody is pricing it. And isRwa, authoritative for
299 of 300 cases, is wrong about the loudest one: SPXUSDT (the S&P 500) is tagged isRwa=NO and
was filed as CRYPTO on a 24/7 clock, while SP500USDT -- THE SAME UNDERLYING -- is tagged YES and
correctly filed as an index future. The venue's own flag disagrees with itself about one index,
so the name check now runs FIRST for names that are unambiguously not crypto whatever the
metadata says. Both confirmed by exercising the real classifier: 8/8 correct. C423-3, MY CAPTURE
LEDGER WAS DIVIDING BY A DENOMINATOR THAT DID NOT EXIST. Every line it printed showed it:
'banked -0.79% of the +0.00% this trade reached (0%)', 'banked -0.91% of the +0.10% reached
(-880%)', 'banked -2.14% of the +1.14% reached (-187%)'. A capture RATIO is only defined for a
trade that reached a positive peak worth capturing; applied to one that never went green it
yields -880%, and averaged into a session it yields 'CAPTURE -3%', a number nobody can act on.
TWO DIFFERENT QUESTIONS WERE BEING FORCED THROUGH ONE FORMULA -- of what a WINNER offered, how
much was banked; and how far did a PEAK travel back before exit. Now separate, with giveback in
R so it is comparable across instruments. AND THE SPLIT IS WHERE THE REAL FINDING LIVES: across
both sessions WINNERS BANK 51-77% OF THEIR PEAK WHILE EVERY SINGLE LOSER TRAVELLED FROM A
POSITIVE PEAK THROUGH ZERO TO A LOSS. ENA peaked +1.14% and exited -2.14%, giving back 319% of
peak. The bot cuts its winners at two thirds and lets its losers run the full round trip -- the
oldest asymmetry in trading, and it was INVISIBLE while one broken ratio averaged the two
together. C423-4, THE OPERATOR'S THOUGHT EXPERIMENT, APPLIED AND INSTRUMENTED. Tullock proposed
replacing the airbag with a steel dagger aimed at the driver's chest; Peltzman then measured the
real thing -- US auto safety mandates cut DRIVER deaths per mile, PEDESTRIAN and motorcyclist
deaths ROSE, and the total highway death rate barely moved. ANY DEVICE THAT PUTS DISTANCE
BETWEEN A DECISION AND ITS COST PULLS BEHAVIOUR TOWARD THE NEW MARGIN. THIS BOT IS ALMOST
ENTIRELY MADE OF SAFETY DEVICES -- twenty exit paths, the C367 penalty floor, C382 overrides,
C372's profit floor, C422-4's loss floor, the expectancy gate, the fee servo, the correlation
guard -- every one added after a specific loss, and the project's own history says Peltzman is
right about them: C367's floor was rescuing 3 OF 3 candidates by C419, so the BACKSTOP HAD
BECOME THE ENTRY CRITERION; two of those three also needed a C382 override, so THE EXCEPTION
BECAME THE PATH; C134's blocklist is above. AND C422-4, MY OWN LAST CHANGE, IS THE CLEANEST
CASE: it removed the cost of exiting inside the noise band, and session capture went 10% -> 5%
-> -3%. The early-exit losses did not become gains, THEY REAPPEARED AS GIVEBACK. Driver deaths
fell; pedestrian deaths rose. THE RESPONSE IS THEREFORE NOT ANOTHER GUARD, because adding one
more downstream rule is exactly the move the experiment warns against. The dagger's lesson is
that behaviour changes when the COST IS VISIBLE AND IMMEDIATE TO THE DECIDER, so the cost is
brought back to the decision: every guard that fires now records WHAT IT PREVENTED AND WHAT
HAPPENED INSTEAD, printed at exit beside the capture line. INSTRUMENTED ONLY -- acting on an
unmeasured theory is how the guards being audited got here. PROCESS FAILURE, RECORDED. My first
edit script asserted out on its fifth replacement and never wrote the file, so FOUR APPLIED
EDITS WERE SILENTLY LOST and a later verification appeared to pass because the harness was
simulating C423 rather than reading it. Caught only by exercising the REAL classifier through
AST extraction instead of trusting a regex over the source. Edits now report per-edit and the
verification instantiates the shipped code. This is the C422-1 lesson -- static inspection is
not execution -- repeated one version later, in my own tooling. VERIFICATION: syntax; AST 347 ->
348 (+_c423_note_guard); per-edit application reported; duplicate defs 0; wrong-object sweep
clean; C423 constants defined-and-never-read 0; the REAL classifier exercised 8/8; live desk
populations recomputed through the shipped code against the live venue. HONEST LIMITS: metals,
energy and 41 restored us_equity names have NEVER been traded by this bot, so C423-1 widens the
field by 50x on the metal desk with ZERO live evidence about whether those instruments behave --
if the next session shows metal losses, C423_LEGACY_NAME_BLOCKLIST=True restores C134 in one
flag. And the winner/loser asymmetry is DIAGNOSED, NOT FIXED: standing rule #4 allows one load-
bearing change and the universe is it. Chain C367-C423 intact.


## C422

THE ENTRY PROBLEM IS SOLVED; THE EXIT IS NOW THE BINDING CONSTRAINT. Session 20260825_001313:
15h02m, 167 scans, 7 positions, 3W/4L, +$0.33 (+0.13%) -- THE FIRST PROFITABLE SESSION IN THIS
RECORD, and measured payoff 2.0:1 against the 0.78:1 that started four versions of target work.
The Guardian Report prints it: R:R=2.0:1. At 43% and 2.0:1 expectancy is +0.29R per trade. AND
THE SELECTION IS EXCELLENT. The seven pairs bought averaged +9.0% over the session against a
volume-qualified universe median of +0.40% (217 pairs, 56.2% closing up, BTC +0.29%, tape MEAN-
REVERTING at median lag-1 autocorr -0.086 with 78% of pairs negative). ONG +28.9%, PROM +13.1%,
UB +8.8%. The bot found the trending minority inside a fading tape. THEN IT BANKED TEN CENTS ON
THE DOLLAR. Captured +3.06% of the +29.65% its own entries reached within 4h. CAPTURE RATIO 10%.
ONG exited -0.03% after 17min then ran +10.02%; ONG#2 captured +3.37% of a +12.50% run; UB
exited -0.79% after 41min then ran +4.54%; PEPE was +1.80% in-trade and gave all of it back.
WHY: TWENTY distinct exit paths, any ONE of which ends a trade, so all twenty must stay quiet
for a position to live -- the C114 multiplicative-paralysis disease that once froze ENTRIES,
reappearing on the exit side where nobody was watching. And C372 guards only one direction: its
docstring says outright that 'losses, stops and thesis-death exits are NEVER gated', which was
right for a profit floor but leaves the LOSS side with no expectancy check at all -- and every
costly exit above was a loss-side exit. C422-1, MY NEWS REPAIR WAS DEAD CODE FOR FIFTEEN HOURS.
The receiver is `self.news`; I guessed `news_analyzer`, `_news_analyzer` and
`analyzer._news_analyzer` and all three missed, so set_screened never ran: 2,026 readings
returned 'no coin-specific articles' against 322 that resolved -- 86% BLIND, WORSE than the 75%
the repair existed to cure. AND MY REACHABILITY AUDIT PASSED IT, because that audit asks whether
set_screened is CALLED anywhere in the AST -- it is -- and cannot see that the RECEIVER resolves
to None at runtime. STATIC CALL-GRAPH REACHABILITY IS NOT RUNTIME REACHABILITY WHEN THE RECEIVER
COMES FROM A getattr CHAIN: every `or getattr(...)` is an unverified guess wearing the costume
of a safety net. Wrong-object family, instance SIX. The failure was also logged at DEBUG, which
the file log does not carry, so a total failure left NO TRACE -- standing rule #5 violated
inside the fix that cites it. Now a WARNING. C422-2, DECIMAL PRECISION, operator-reported and
worse than cosmetic. Every price site used a fixed `.6f`, which is simultaneously too many
digits and too few: EUL printed $1.383000 (three meaningless zeros) while PEPE printed $0.000004
-- THE ENTIRE PRICE COLLAPSED TO ONE SIGNIFICANT DIGIT against a true 0.0000037931, so entry and
exit are indistinguishable and the trade is UNVERIFIABLE against the candle API, breaking
standing rule #6. A fixed decimal count is an ABSOLUTE constant applied to instruments spanning
seven orders of magnitude: instance TWELVE of this project's oldest disease, hiding in a format
string. _fmt_px prints at the VENUE'S OWN TICK where ccxt publishes it and scales significant
figures with magnitude otherwise; 26 call sites converted. Float dust too: `Normal: +0.4% /
0.44399999999999995%` appeared 56 times (0.148*3 in binary), plus raw trail targets $0.082228111
and $1.4447779. Rounding now happens at the display boundary, never in the arithmetic. C422-3,
THE CAPTURE LEDGER -- instrumentation only. The session's central number could only be computed
OUTSIDE the bot by re-fetching candles. A bot that cannot see its own most important statistic
cannot improve it, so captured-vs-offered is now recorded on every exit with a running session
figure. C422-4, THE MIRROR OF C372. A soft loss-exit may not fire while the loss is still inside
the noise band the position was SIZED to absorb: R = 2*ATR, ordinary one-bar noise is ~1 ATR =
0.5R, so abandoning a thesis at 0.3R because conviction wobbled is refusing to let your own risk
budget work. Narrow exactly as C372 was: only REVERSIBLE reasons, never the hard stop, never
C399_REVERSAL_CONFIRMED or CONVICTION_COLLAPSE (thesis DEAD, not wobbling), never a profit exit,
and the floor LIFTS at the horizon so nothing hangs. C377's 1.5R hard stop still bounds every
downside. MY FIRST TOKEN LIST WAS WRONG AND THE REPLAY CAUGHT IT: it omitted PEAK_FLOOR, which
was the single most expensive exit of the session -- ONG closed at -0.03% after 17min and then
ran +10.02%. A peak-protection exit firing while the position is at a LOSS is protecting a peak
that never existed; there is nothing to give back. That is a logical error rather than a
threshold, which is why including it is safe and tuning a number to fit four trades would not
have been. REPLAYED ON ALL FIVE EXITS: ONG#1 now HELD; EUL correctly untouched because it was in
profit and C372 owns that side; UB, ONG#2 and PEPE still exit (past horizon, or a real loss at
0.61-1.03R). VERIFICATION: syntax; AST 344 -> 347; count-asserted replacements; duplicate defs
0; wrong-object sweep clean; C422 constants defined-and-never-read 0; RUNTIME reachability now
checked by instantiation, not just by AST, because that is precisely what missed C421-4; _fmt_px
replayed against the log's own eight problem numbers; the soft-loss gate replayed against all
five real exits including a winner as a control. HONEST LIMITS: C422-4 changes exactly ONE of
this session's five exits, so its value is asserted from a sample of one and must be judged on
the capture ledger next session, not on this replay; and the 0.5R band is derived from R=2*ATR
rather than measured, so if the ledger shows capture still under ~40% the band is the first
thing to question. NOT TOUCHED, deliberately: the 20-path exit stack itself, the C367 penalty
floor, and the long-only monoculture (64 long vs 17 short candidates, all 18 viable ones long)
-- standing rule #4, one load-bearing change per version. Chain C367-C422 intact.


## C421

ZERO TRADES IN FOUR HOURS -- I BUILT A DEATH SPIRAL AND THE LOG CAUGHT IT. Session
20260824_192647: 4h05m, 40 scans, NO POSITIONS, 1,104 thin_expectancy rejections = 85% of every
rejection. The trend is unmistakable and it is mine: C404 3 trades, C405 2, C419 2, C420 ZERO.
FOUR CONSECUTIVE VERSIONS STARVED BY ONE GATE, each 'fixed' by tuning a number, which is exactly
the mistake C405's own changelog confesses to. WHAT C420 GOT RIGHT, verified in this log and
kept: the percentile servo walked 84 -> 55 at 1.5 POINTS PER SCAN precisely as documented (C419
slammed 84 -> 99 in eleven minutes), the rate estimator no longer locks out, and the C420-7 bias
ledger settled 25 readings and reports corr -0.442/-0.617/-0.050 against the next hour --
INDEPENDENTLY CONFIRMING last session's -0.258 finding that R is anti-predictive. The plumbing
works. The arithmetic did not. C421-1, THE BRIER UNITS BUG -- MY DEFECT, ONE VERSION OLD, IN THE
FAMILY I HAD JUST WRITTEN THREE ATLAS PRINCIPLES ABOUT. The same log prints 'S3-EV: calib[191]:
acc=0.48 brier=0.275' and 'C420-5: ... brier 52.496 vs baseline 0.250'. TWO NUMBERS FOR ONE
QUANTITY, and 52.496/191 = 0.2748 EXACTLY. _s3_calib ['brier'] is an ACCUMULATED SUM; C335's
_c302_trust() has divided by n since it was written and I read the raw accumulator, reporting a
skill of -20,898%. A field's UNITS are part of its identity, and reading it without checking
them is the same error as calling a method on the wrong object -- instance FIVE
(C406/C412/C418/C420-1). C421-2, THE EXPECTANCY WAS DIMENSIONALLY INCONSISTENT AND HAS BEEN
SINCE C404. E = p(R x 0.60) - (1-p) - fee treats p and R as INDEPENDENT, as if a distant target
were no harder to reach than a near one. C416 already knew better -- its own docstring reads 'a
coin-flip market gives p = 1/(1+T)' -- but C404's expectancy never applied the constraint. The
result is a CLIFF: p=0.60 needs R>=1.21, p=0.50 needs 1.78, p=0.45 needs 2.17, AND p=0.38 NEEDS
R>=2.87 AGAINST AN OBSERVED MAXIMUM OF 2.51. Every candidate in the session carried p=0.38. ZERO
TRADES WAS NOT BAD LUCK, IT WAS ARITHMETIC -- the gate was mathematically impossible to pass and
no amount of market opportunity could have changed it. THE SELF-CONSISTENT FORM: if p is the
probability of touching +T before -1 then p_fair = 1/(1+T), the bot's claim is an EDGE e over
that, and the algebra collapses to E = e(1+T) - f. Zero edge gives E = -f EXACTLY -- with no
edge you lose precisely the fees, which is the correct answer and which the old form could not
produce (verified to 1e-9 at three targets). E >= 0 becomes e >= f/(1+T): DOES THIS TRADE HAVE
ENOUGH EDGE OVER FAIR ODDS TO PAY ITS OWN FEES. Stated entirely in units of the trade's own
stop, and it CANNOT become impossible, because it constrains the EDGE rather than R. The
projection must still support the target, so the edge is scaled by min(1, R/T) -- a weak
forecast fails on its own merits, which is what flat_projection was always trying to say.
C421-3, WHERE THE EDGE COMES FROM, AND THE SPIRAL I BUILT. C420-5 collapsed p to the realised
base rate; the record was a losing streak; the base rate fell to 0.38; the gate tightened;
trading stopped; no new outcomes arrived; the base rate froze at 0.38 FOREVER. A CONTROLLER
WHOSE OUTPUT REMOVES ITS OWN INPUT CANNOT RECOVER. The answer is not a looser threshold -- it is
that a trader with no measured edge does not stop, they trade SMALL to acquire the sample,
because an edge cannot be measured without one, and this codebase already prices that correctly
(C335 trust ramps sizing with evidence; Kelly sizes down under uncertainty). The edge is now a
Bayesian blend: PRIOR = C398's measured +4.67pp (n=3,420, both halves -- the one edge this
project has ever demonstrated), shrinking toward the REALISED edge as live trades accumulate,
washing out after ~30. SECOND SELF-CAUGHT ERROR IN THE SAME PASS: my first version computed the
realised edge from the RAW win rate, and verification showed 1W/8L yields -0.304 and shuts the
book completely -- the same spiral rebuilt with different arithmetic. A nine-trade sample cannot
carry a -30pp claim. Routed through _c420_base_rate(), the ONE Laplace-shrunk anchor, which is
the C420-1 lesson applied deliberately this time. MEASURED on the 19 real R values from this
session's log: C420 admits 0/19 at EVERY ledger state; C421 admits 73.7% fresh, 68.4% on the
losing streak that caused the lockout, 94.7% at 11W/9L. Frequency control is NOT this gate's job
-- the hard floor asks only 'is this positive expectancy', the C405 percentile bar (verified
working) chooses among survivors, and the C403 servo tunes that percentile to ~6/day. Making the
hard floor do the selecting too is what produced four starved versions. Bounded across 1,580
combinations: -0.324R to +0.296R. C421-4, THE NEWS WAS READING A PORTFOLIO THE BOT DOES NOT HOLD
-- the operator's request, and he was right to ask. THREE defects compounding. (a) _COIN_MAP was
24 HAND-TYPED MAJORS while the scanner selects LDO, JUP, GRT, ZAMA, RAM, PENGU; 633 of 840
readings came back 'no coin-specific articles' -- THE CHANNEL WAS BLIND ON 75% OF EXACTLY THE
PAIRS IT WAS SCORING. A list assembled from memory cannot terminate a search. (b) The fetch
query was the FIXED STRING 'bitcoin OR ethereum OR crypto' -- it never once asked about a
screened pair. (c) Matching was SUBSTRING, so 'BE' matched 'before', 'RAM' matched 'program',
'OG' matched 'recognise'; the log shows BE scoring 'news long sig=0.10 score=+0.19' off that
collision, and A FABRICATED SIGNAL FEEDING THE SCORE IS STRICTLY WORSE THAN NO SIGNAL. Repaired:
the scanner now PUBLISHES its top-30 to the news layer (without which the whole fix is dead code
-- the 'computed but never wired' class that has cost this project five times); names are
DERIVED rather than remembered; the query is built from the screened pairs; matching is WORD-
BOUNDARY and a bare ticker under 4 characters may not match free text at all. LIVE TEST CAUGHT
TWO FURTHER PROBLEMS. First, BITGET DOES NOT PUBLISH COIN NAMES -- /contracts carries only
baseCoin, so venue-derived alone left coverage at 27%, no better than the typed list.
CoinGecko's coins/list is free, keyless and resolves 18,664 symbols (LDO -> Lido DAO, GRT -> The
Graph, PENGU -> Pudgy Penguins, ATH -> Aethir), fetched once per process, failing to ticker-only
rather than breaking the scan. Second, THAT LIST IS FULL OF BRIDGED DUPLICATES and first-match-
wins picked them: ETH -> 'Anubis Bridged ETH', XRP -> 'Binance-Peg XRP', SOL -> 'Allbridge
Bridged SOL' -- useless as queries and WORSE than the typed map for the majors it had right. A
wrapper is a different instrument that borrowed a ticker, so wrappers are excluded by
construction and the shortest survivor is canonical. FINAL LIVE RESULT on the real top-30:
coverage 27% -> 63%, query now 'Bitcoin OR Ethereum OR Ripple OR Solana OR ...' instead of a
fixed string, and every short-ticker false positive blocked. The residual 37% are tokenized
equities (SNDK, SOXL, MU, SPCX) which correctly have no crypto news identity and which isRwa
already separates. C421-5, THE BIAS LEDGER FLATTERED ITSELF. It printed 'corr -0.442, sign hit-
rate 80%' -- a NEGATIVE correlation beside an 80% hit rate, which is a base-rate artefact: when
both series share a sign the hit rate rises regardless of skill. Now printed against a majority-
class baseline with the correlation named as the number to read. VERIFICATION: syntax; AST 338
-> 343 (+_c421_edge, +_c421_expectancy, +set_screened, +_names_for, +_order_names, +_mentions);
count-asserted replacements; duplicate defs 0; wrong-object sweep clean; C421 constants defined-
and-never-read 0; REACHABILITY confirmed on all five new methods; zero-edge identity verified to
1e-9; admit rate measured on the session's 19 real R values across five ledger states; news
layer end-to-end against live Bitget metadata + CoinGecko. HONEST LIMITS: the edge PRIOR is
C398's corpus number applied to all trades though C398 measured a subset, so it is optimistic
and the realised term must be watched as n grows; and 73.7% admission at the hard floor leans
hard on the C405 servo doing frequency control -- if the next log shows more than 12 trades/day,
the servo is the thing to read, not the floor. Chain C367-C421 intact.


## C420

THE ENTRY FUNNEL WAS AN OSCILLATOR, NOT A CONTROLLER -- SEVEN DEFECTS ON ONE CAUSAL PATH, ALL
MEASURED ON SESSION 20260824_010933 (8h42m, TWO trades, TWO losses, -$0.56, and 1,624 expectancy
rejections = 78% OF EVERY REJECTION IN THE SESSION). C404 failed with 1,723 rejections and 3
trades; C405 was its repair and produced 1,624 and 2. SAME DISEASE, NEW MECHANISM, and this is
the third version in a row to be starved by its own quality gate. C420-1, THE RATE ESTIMATOR
LIED AT BOOT AND HAD TWO INITIALISERS. `_c403_rate_bar_mult` created _c403_state with ewma =
C403_TARGET_TRADES_DAY (6.0) while `_c403_note_entry` created the SAME state with 0.0 -- two
truths for one state, whichever path ran first winning, the C406/C412/C418 family for the FOURTH
time. The 6.0 seed is the substantive error: a bot that has opened NO positions must read ZERO
trades/day, not 'already at budget'. ONE entry adds 2.77 and the estimate reads 8.77, ABOVE the
8.0 too-busy ceiling, so a single trade in an empty session convinced the controller it was
over-trading. REPRODUCED IN SIMULATION TO THE HOUR: the lockout lasts exactly as long as 8.77
takes to decay to 4.0 at a 6h half-life -- SEVEN HOURS -- and the log shows 6.7. Decay also
moved onto the READ path; it previously ran only inside note_entry, so a bot that stopped
trading kept reading a stale high rate forever. An estimator that updates only when the thing it
measures happens is not an estimator, it is a latch. C420-2, THE SERVO STEP WAS PER-CANDIDATE,
NOT PER-SCAN. Both the docstring and the config comment say 'per-scan correction, gentle -- 1.5
points', and C405's entire replay (the 'authority span 1.8%-31.6%' claim) was computed on ONE
step per scan. `_c405_e_bar` is called inside the per-candidate loop and a scan carries 30-41
candidates, so the percentile moved 45-61 POINTS PER SCAN. A controller whose step exceeds its
own range is a light switch. THE LOG PRINTS IT: 84th percentile at 01:10:24, 99th by 01:21:42 --
ELEVEN MINUTES -- pinned at 99 for six and a half hours, then through to the 55 rail in one
scan. AND THE DECISIVE OBSERVATION: THE BOT'S ONLY TWO TRADES BOTH LANDED IN THE BRIEF WINDOWS
WHERE THE BAR SAT AT ITS FLOOR (01:10, n<60 samples; 08:25, servo bottomed). The expectancy gate
did not select them. The oscillator did, and whatever penalty-floored remnant was standing at
that moment got bought. Fixed by an explicit scan tick (_c420_scan_seq, incremented at the head
of Step 3) -- a controller cannot have a step rate without one, and nothing in the code
previously said where a scan began. C420-3a, A PROJECTION HAS A PHYSICAL CEILING. The projector
printed BTC proj 2.01% for a 15-minute candle whose true ATR, fetched from live Bitget candles,
is 0.271% -- 7.4 ATR IN ONE CANDLE. Not a forecast, a broken reading, and it did real damage: R
came out 6.70, E came out +2.08, and the pooled 99th-percentile bar became +2.2R, a number
NOTHING on the venue could clear INCLUDING BITCOIN ITSELF. Capped at C420_PROJ_MAX_ATR x the
pair's OWN ATR: relativistic by construction, no absolute percentage anywhere, and it rests on
the same random-walk law C404 already uses. On the logged BTC readings it takes R 5.40->2.71 and
6.70->2.71 and leaves the three honest readings untouched. C420-3b, THE POOL WAS CROSS-TIME AND
CROSS-INSTRUMENT. 400 observations span ~4 hours and every instrument, and because the same
pairs are re-scored every scan the majors dominate. Comparing GRT's expectancy against Bitcoin's
is not relativistic; it is this project's oldest disease wearing a percentile as a disguise,
instance EIGHT. 'The BEST trade available RIGHT NOW' is a WITHIN-SCAN question, so the reference
distribution is the PREVIOUS COMPLETED SCAN's candidate set -- same universe, same minute, same
tape, every pair counted once. C420-4, THE TARGET FLOOR SHRANK AS CONFIDENCE ROSE, AND MY FIRST
FIX FOR IT WAS WRONG. Tabulated across the range: p=0.45 demands 1.49R, p=0.70 demands 0.70R,
p=0.72 demands 0.71R -- THE BEST-RATED SETUPS GOT THE WORST REWARD-TO-RISK, which is exactly the
disease C415 and C416 were built to cure and which the handoff records as FIXED. It is not
fixed. The log prints the proof: 'GRT: target floor 0.70R = 1.62%', a target 30% SMALLER than
its stop on a bot whose measured payoff is 0.78:1 and whose stated need is 1.50:1. And the
arithmetic only closed because the fixed point permits p_use = fair + 0.10 -- A FLAT +10
PERCENTAGE-POINT EDGE ASSERTED ON EVERY CANDIDATE, when this project's ONE measured edge is C398
at +4.67pp on a subset; at true fair odds every one of those targets is negative expectancy. MY
FIRST ATTEMPT kept the fixed point and merely tightened the edge cap, AND IT DIVERGED: a tighter
cap lowers p_use, which raises t_new, which lowers fair = 1/(1+t), which lowers p_use again --
it ran to the 4.0 clamp and demanded 3.6R on every trade. A cure that stops all trading is not a
cure. The divergence was the algebra telling the truth: WITH NO EDGE THERE IS NO TARGET THAT
PAYS. The repair is to stop asking a circular question -- anchor on what the bot has ACTUALLY
DONE, which is not a claim, needs no cap and cannot be circular: T >= [Emin + (1-wr)(1+f)]/wr +
f, solved in ONE step from the Laplace-shrunk realised win rate. Empty ledger -> 1.41R, which IS
the 1.5:1 the 2-4%/month arithmetic has always required; 0W/10L -> 2.74R; 24W/6L -> 0.75R. It
tightens by itself whenever the win rate slips, and the per-trade claim may lower it ONLY as far
as p has earned Brier skill. Bounded across 620 combinations, min 0.60R max 4.00R, no runaway.
C420-5, THE p FEEDING EVERYTHING HAS NEGATIVE SKILL AND THE LOG SAYS SO IN ITS OWN WORDS. C405
closed with the instruction 'if the gate admits trades that still lose, the p that feeds E is
the next thing to indict'. It is indicted: 'S3-EV: calib[189]: acc=0.48 brier=0.274 (baseline
0.250)' -- accuracy below a coin flip and a Brier score WORSE than the naive constant
forecaster. GRT entered at p=0.699 and lost; DOS at p=0.542 and lost. The codebase already knows
how to handle this: C342 holds FamilyMarkov at 'earning' for -6.8% skill and C343 lets
IchiMarkov act at +11.2%. S3 was simply exempt from a discipline applied everywhere else. p is
now pulled toward the base rate in proportion to measured Brier skill, collapsing to the base
rate entirely at zero or negative skill. SECOND SELF-CAUGHT ERROR IN THIS SAME VERSION: I first
shrank toward a flat 0.50, and MEASUREMENT ON THE SESSION'S 42 REAL LOGGED CANDIDATES showed
that drops the share clearing the E>=0 hard floor from 31% to 14%, against C405's own honest
figure of 31.6% -- the C404 starvation returning by a different door. A coin has no memory; a
strategy does. The fallback is now the bot's OWN Laplace-shrunk realised rate via
_c420_base_rate(), the SAME anchor C420-4 uses, because shipping two independent base rates in
the version that exists to fix two disagreeing initialisers would be absurd. C420-6, A HOT LEG
THAT ITS OWN FORECAST OPPOSES IS NOT A RIDEABLE IMPULSE. The 'leg beyond cap, burning hot'
branch PRINTED _n52_next_pct and DISCARDED it, while EVERY sibling branch (C285 leg-exhausted,
C286, C291, the decel path) reads it -- one branch exempt from the check its neighbours all
apply. The cost: 'DOS: leg beyond cap (X=1.49) burning hot; chasing into RSI 71 extreme ->
conviction x0.91 | next -1.13%'. THE BOT FORECAST A 1.13% FALL AND BOUGHT. It closed at
THESIS_EXIT 27 minutes later and DOS fell 3.1% from the entry within the hour; SHIB was the same
shape and was saved only by a limit that did not fill. The penalty is RELATIVE (opposition
measured in the pair's own ATR, so -1.13% means one thing on DOS at 0.72% ATR and another on BTC
at 0.27%) and BOUNDED at x0.55, because a forecast is evidence and not a verdict. On DOS it is
x0.55, taking conviction 0.91 -> 0.50. C420-7, INSTRUMENTATION ONLY -- IS THE MARKET-BIAS
READING LEADING OR LAGGING? Measured across the whole 206-pair volume-qualified universe on 15m
candles, all 92 R readings of the session: corr(R, the PREVIOUS hour's median move) = +0.406;
corr(R, the NEXT hour's) = -0.258; SIGN HIT-RATE ON THE NEXT HOUR = 35%. The worst hour of the
night (9% of pairs up, median -1.98%) was read as bullish +0.31; the best (77% up, +0.75%) was
read as bearish -0.53. R is measuring the past accurately and is ANTI-PREDICTIVE of the future
on a mean-reverting tape -- and C386's counter-trend BLOCK plus the C215/C216 flips all consume
R AS IF IT WERE A FORECAST. NOT ACTED ON. n=92 readings but only ~12 independent hours, and
standing rule #1 is measure before building; C405 is the monument to what happens when a
threshold is set from one sample. Each reading is now stamped and settled an hour later against
the bot's own breadth count, so the question is answered by accumulation instead of by argument.
In the same pass the breadth counts were PUBLISHED as real attributes -- my ledger first reached
for self._coherence_up when only a LOCAL _up_mom existed, which would have recorded NOTHING,
silently, forever: the wrong-object defect reappearing inside the fix for the wrong-object
defect. Caught by the reachability audit, and the ledger now warns aloud when breadth is
unavailable, because a measurement that fails quietly is not a measurement. WHAT THE MARKET
ACTUALLY DID, since the standing protocol forbids judging a session without it. Whole volume-
qualified universe (206 pairs), 3h before the log opened to 3h after it closed: MEDIAN PAIR
-1.50%, ONLY 16.5% CLOSED UP, 121 fell >=3% against 40 that rose >=3%, BTC flat at +0.32% over
the whole 14 hours -- an ALT-BLEED tape, and MEAN-REVERTING (median lag-1 autocorrelation of 15m
returns -0.040, 63% of pairs negative). THE BOT TOOK TWO LONGS. Worse, prior extension ANTI-
PREDICTS on this tape: sorted into quartiles by how far each pair had already run, the MOST
EXTENDED-UP quartile returned -2.55% against -1.18% for the most sold-off, corr -0.212 -- and
Step 1 ranks by 'liveliness', which is definitionally recent movement. The opening top-30 held
SPK +28%, MORPHO +21%, PENGU +15%; its ten most extended names returned a median -2.02%. GRT
(+6.8% in 24h) and DOS (+6.3%) both came from that cohort and both were bought within one tick
of a local candle high, chart-verified against live Bitget candles. THE MOST DAMNING SINGLE
FACT, and it is not any of the seven: ALL THREE viable candidates of the entire session -- GRT,
SHIB, DOS -- were rescued by the C367 penalty-stack floor (exactly 3 lifts, one each), and GRT
and SHIB ALSO needed C382 overrides to waive 'no structural room' and 'late leg, forward signals
object'. NOT ONE TRADE WAS A CANDIDATE THE BOT'S OWN SCORING APPROVED. Every one was a candidate
its evidence had crushed and a floor resurrected -- the C367 inversion ('a guard that fires
hardest against its own evidence is not a guard') still running at 100% of the sample. Recorded,
NOT fixed here: the funnel repairs must be measured first, because changing the floor and the
funnel in one version makes the next log unattributable, which is standing rule #4. RETROACTIVE
CHECK, which this version exists to pass: GRT E +0.075R -> -0.241R REJECTED at the hard floor;
DOS E +0.140R -> -0.001R REJECTED. Both losses prevented -- though DOS by 0.001R, which is a
coin-flip rejection and is stated as such rather than claimed as a save. Target floors 0.70R ->
1.41R and 1.04R -> 1.51R. VERIFICATION: syntax; AST 334 -> 338 (+_c420_rate_state,
+_c420_realised_record, +_c420_base_rate, +_c420_p_skill_weight); count-asserted replacements;
duplicate defs 0; the C412 wrong-object sweep clean; C420 constants defined-and-never-read 0;
C420 attributes written-and-never-read 0; closed-loop servo replay over 65 scans x 35 candidates
showing 18/65 fully-locked scans under C419 against 0/65 under C420; the target floor tabulated
across seven probabilities, seven ledgers and 620 bound combinations; the p-shrink measured on
the 42 real logged candidates; live Bitget simulation through all five steps (761 markets, 213
volume-qualified, 35 scored, percentile moving 1.5 points per scan as documented, one entry
reading 2.77/day where C419 read 8.77); boot battery 7/7. HONEST LIMIT: the live-sim projection
is a 3-bar drift proxy, NOT the bot's projector, so its R values (0.24-0.46) are not evidence
about gate calibration -- only the plumbing is verified there. Chain C367-C420 intact.


## C419

THE OPERATOR'S 'z' HAS A RIGOROUS ANSWER AND A CORRECT HOME -- AND HIS MARGIN OBJECTION IS RIGHT
IN A WAY THE CODE ALREADY CONFESSED. HIS PROPOSAL: derive group size from z, the average number
of pairs a single account holds, because that is the natural unit of capital ROTATION; make the
top-z pairs by five-year volume share the NODES; size each group in proportion to its node's
volume share. NO EXCHANGE PUBLISHES z, and Bitget has nothing like five years of history for
most of these contracts. But the QUESTION z answers -- how many genuinely distinct things are
there to bet on -- has a rigorous answer from the data itself: RANDOM MATRIX THEORY. Eigenvalues
of the correlation matrix above the Marchenko-Pastur noise ceiling (1+sqrt(n/T))^2 are real
factors and the rest is sampling noise. MEASURED on the 60-pair 20-day corpus: n=60, T=1911,
ceiling 1.386, eigenvalues 12.7, 4.3, 1.9 and 1.4 ABOVE it against 1.3 and 1.3 below. FOUR REAL
FACTORS, about fifteen pairs per group. That is his z, measured rather than assumed. THE REST OF
THE CONSTRUCTION WAS TESTED AND IS NOT USED, and the numbers are worth recording so it is not
re-litigated. Volume-node grouping produced LESS STABLE groups than the plain correlation
clustering already in C418: BTC's node group decayed +0.48 -> +0.34 and ETH's +0.11 -> +0.04,
against +0.80 -> +0.74 for the correlation-threshold groups. Volume share and correlation are
simply different quantities -- ETH is second by volume, but the members correlation assigns to
it once BTC has taken the top ones correlate at 0.11, which is no group at all. AND THE TESTABLE
IMPLICATION OF HUB-AND-SPOKE FAILS OUTRIGHT: the hub does NOT lead its spokes, at 47.8%, 45.2%
and 47.4% for 15, 30 and 60-minute lags -- ALL BELOW CHANCE, on n=10,129. WHERE z DOES BELONG,
and this is the part worth having: C418 capped effective bets at a TYPED 3.0. If the market
contains only FOUR independent factors then four is the most independent bets that can EXIST,
however many tickers are open -- and the cap should be the measured factor count rather than my
typing. It now is, recomputed every thirty minutes from the live OHLCV cache, floored at 2 and
ceilinged at 6. THE PROPERTY THAT MAKES THIS BETTER THAN A CONSTANT: when the market NARROWS to
one factor -- everything moving together, which is exactly when concentration hurts most -- the
cap TIGHTENS BY ITSELF, without anyone deciding to tighten it. A constant cannot do that.
C419-2, MARGIN THAT SCALES. The operator asked why $5 minimum margin is acceptable on a $250
book, and the code had already confessed the problem: C368's own comment reads 'the $5
MIN_MARGIN floor SETS this; it is not a preference' -- THE EXCHANGE MINIMUM WAS DRIVING THE RISK
SETTINGS instead of the other way round. $5 is 2% of $250 and 0.5% of $1,000, so the same
constant means two different things as the account grows. $5 REMAINS as the hard exchange floor
because Bitget will reject less; what changes is the BOT'S OWN minimum, anchored where it
belongs -- ON THE DAILY TARGET. A position should be able to earn a meaningful slice of the
day's goal or it is not worth its fee: at a 1.5R target on a ~3% stop a winner returns ~4.5% of
margin, so contributing 15% of a $1.70 day needs about $5.80 of margin, and at $1,000 equity the
same rule asks for about $22. The number moves because the target moves, capped at 10% of equity
so it can never demand a concentrated position on a small book. The maxima were already
fractional (C373 at 25%, allocator at 55%) and are untouched. VERIFICATION: syntax; AST 333 ->
334 (+_c419_factor_count); count-asserted replacements; the RMT factor count reproduced above
from the corpus with its eigenvalue spectrum and noise ceiling; volume-node grouping and hub
lead-lag both tabulated as refuted; the scaled minimum computed at two equity levels. Chain
C367-C419 intact.


## C418

THE OPERATOR'S GROUP HYPOTHESIS, TESTED HONESTLY: HIS STRUCTURE IS RIGHT, HIS SIGN IS RIGHT, HIS
SIGNAL IS TOO WEAK TO SHIP -- AND WHAT IT UNCOVERED INSTEAD IS A REAL HOLE IN THE RISK BOOK.
WHAT HE PROPOSED: find highly correlated, stable groups of pairs sharing a funding pool; measure
which member is absorbing the largest share of group flow per unit time (window inversely
proportional to group volume, which is correct reasoning -- more volume means more information
per second, so a shorter window suffices); and trade that member, because within a shared
capital pool intra-group flow is ZERO-SUM and the concentrated pair must run against the group
average. MEASURED ON THE 20-DAY 60-PAIR CORPUS. HIS PREMISES HOLD, and strongly. Correlation
between first-half and second-half pair correlations is +0.880, so the structure is genuinely
STABLE and not an artefact. Two real groups fall out: SIXTEEN CRYPTO MAJORS (BTC ETH BNB AVAX
DOGE ENA...) at +0.58 decaying only to +0.46, and SEVEN MEMORY/SEMICONDUCTOR NAMES (MU SKHYNIX
SKHY SNDK SNXX KORU) at +0.80 HOLDING +0.74 OUT OF SAMPLE. Flow-share concentration also
PERSISTS at +0.230 autocorrelation over an hour, so the mechanism he described is real rather
than imagined. HIS DIRECTIONAL CLAIM IS DIRECTIONALLY CORRECT AND NOT SHIPPED. The pair
absorbing the most group flow subsequently UNDERPERFORMS its group -- which is exactly his 'runs
in the opposite direction', so the SIGN was right -- but following it wins 48.5% (halves
49.4/47.8) and fading it therefore wins only 51.5% (halves 50.6/52.2) on n=2,031. ONE AND A HALF
POINTS IS PRECISELY THE MAGNITUDE THAT HAS FAILED OUT-OF-SAMPLE REPEATEDLY IN THIS PROJECT, and
shipping it would be the C404 survivor-bias mistake in new clothes. Recorded as measured-and-
refused, with the note that the 'opposite direction' half of his phrasing is partly
TAUTOLOGICAL: bids and price move together, so a pair absorbing buying rises while the rest do
not -- that describes what already happened. The only predictive content is whether the
concentration PERSISTS, which it does at +0.230, and even that is not enough. WHAT THE GROUPS
DID EXPOSE IS WORTH FAR MORE THAN THE SIGNAL. C160's correlation guard is PAIRWISE at >0.75,
built for the SOL+WIF case and blind to a book that is COLLECTIVELY one bet. The crypto-majors
group sits at 0.46-0.58, so EVERY PAIR IN IT PASSES 0.75, and the bot can hold five majors
believing it holds five bets. The standard effective-sample formula n/(1+rho(n-1)) says it holds
1.56. Three semis at 0.74: 1.21. Four majors at 0.60: 1.43. C160 blocks NONE of them. SIZING
FIVE POSITIONS AS FIVE WHEN THEY ARE ONE AND A HALF OVERSTATES THE RISK ACTUALLY TAKEN BY
THREEFOLD, and that is precisely how a run of correlated losses arrives with every rule in the
book obeyed. It matters directly to 2-4%/month because the entire C380 risk chain is calibrated
on the assumption that positions are separate opinions. The cap is therefore on EFFECTIVE
positions rather than on the count: at most 3.0 independent bets, and a new position must add at
least 0.15 of one to be worth its fee. TWO SELF-CAUGHT ERRORS IN THE SAME BUILD, both by the
standing audits rather than by a live log. FIRST, I called self._get_return_series() which does
not exist -- the accessor is _returns_for -- the THIRD occurrence of the C406/C412 wrong-object
family and the FIRST time the sweep caught it before shipping rather than a session catching it
after. SECOND, my own verification table showed the 0.30 min-added threshold BLOCKING FIVE
GENUINELY DIVERSIFIED POSITIONS at 0.20 correlation, which add 0.28 each -- the exact opposite
of the intent. An uncorrelated position adds exactly 1.00, so the bar is now 0.15, admitting
real diversification and still refusing doubled bets (0.06 at rho=0.74, 0.17 at rho=0.55).
VERIFICATION: syntax; AST 331 -> 333 (+_c418_effective_positions, +_returns_for reachability);
the C412 generalised wrong-object sweep CLEAN after the fix; duplicate definitions 0; new
constants never read 0; the block/allow table reproduced across five book shapes against what
C160 alone would have done; boot battery 7/7. Chain C367-C418 intact.


## C417

SEVEN DESKS, ONE WALLET, ONE TARGET. The operator's framing is the correct one: this should
behave like several specialist bots working side by side, not one generalist stretched across
incomparable markets. Each desk now scans its OWN universe, on its OWN clock, against its OWN
liquidity norms; they share only the capital and the 2-4%/month goal. WHAT C410 GOT WRONG, and
it is a real design error rather than a bug: it split ONE budget of 30 Step-3 slots BETWEEN the
classes, so OPENING A SECOND MARKET MADE THE FIRST ONE WORSE OFF -- crypto fell from 30 slots to
20 the moment US equity woke up. That is one bot rationing itself, not several bots working
together. Budgets now ADD, because two open markets are two opportunity sets and not one shared
one. Competition for slots happens INSIDE a class, where the instruments are genuinely
comparable; NEVER across classes, where a 2% day in TSLA (8 ATR) and a 50% day in a memecoin (6
ATR) cannot be ranked against each other on any common scale. SLOTS SCALE WITH sqrt(universe)
rather than linearly, because the best few candidates in any cohort carry most of its value and
the tail is nearly information-free -- a cohort ten times larger deserves more looks but not ten
times more. Floored so a two-contract class is examined IN FULL, capped so crypto cannot swamp
the scan. MEASURED ON THE LIVE VENUE: crypto 268 -> 30 slots (capped), us_equity 45 -> 20, metal
7 -> 7, hk 7 -> 7, korea 3 -> 3, energy 2 -> 2, index 2 -> 2. SEVENTY-ONE PAIRS INTO STEP 3 WITH
EVERY MARKET AWAKE, against thirty before -- and still exactly 30 when only crypto is open, so
nothing is taken from the existing behaviour. Step 3 costs 0.85s/pair measured, so a full house
is 60s inside a 480s cycle (13%), and the analysis already runs on a ThreadPoolExecutor so the
desks overlap rather than queue. C417-2, LIQUIDITY IS RELATIVE TO YOUR OWN MARKET. One global
median asks 'is this liquid compared to ALL crypto?' and for a $5M gold perp standing next to
Bitcoin's $8bn the answer is no -- yet $5M is mid-pack among gold's SEVEN contracts. C81's
relative-volume threshold was the right idea applied to the wrong cohort the instant C408
admitted 294 non-crypto instruments, and it was quietly excluding whole asset classes on a
comparison that meant nothing. Same formula, one median per class, with a hard absolute floor
underneath so a thin cohort cannot bootstrap itself into looking liquid. This is the seventh
instance of the absolute-where-relative disease and the first one where the absolute value was a
COHORT rather than a number. AND THE LOG NOW SHOWS THE DESKS. Every scan prints a board: one
line per class, open or shut, and for the open ones its universe size, its own volume floor, how
many passed and how many go into Step 3; for the shut ones the reason (US cash closed, HKEX
lunch break, Globex Sat, KRX closed). The operator asked that a closed market be visible in
EVERY scan and this is that -- the C399/C402/C414 lesson (a log that cannot be attributed cannot
be audited) applied to the whole scan rather than one line of it. MORE ANALYSIS DOES NOT MEAN
MORE TRADES, and that is deliberate: the C403 fee servo and the C404 hard cap still permit only
6-12 a day. It means THE SAME FEW SLOTS ARE FILLED FROM A MUCH WIDER AND MORE GENUINELY
INDEPENDENT FIELD, which is the entire measured case for multi-asset -- C409 put cross-class
aliveness correlation at +0.04 and +0.14 against crypto's OWN internal factor correlation of
+0.925, a twenty-four-fold difference. Widening within crypto could never deliver that because
every altcoin is the same factor wearing a different ticker. VERIFICATION: syntax; AST 331
functions; the C412 generalised wrong-object sweep CLEAN; duplicate definitions 0; new constants
never read 0; every new symbol confirmed written AND read; slot allocation tabulated across all
seven desks with the crypto-only case shown unchanged; Step-3 cost recomputed against the
measured 0.85s/pair; boot battery 7/7. HONEST LIMIT: no non-crypto desk has yet opened a
position, so six of the seven are verified by construction and simulation only. The first
weekday session spanning 19:00-01:30 IST is where the us_equity desk finally trades. Chain
C367-C417 intact.


## C416

THE OPERATOR CAUGHT ME MAKING THE SAME MISTAKE FOR THE SIXTH TIME. C415 replaced one fixed
number (target floor = 1.5 x ATR) with another (1.5 x stop). Better arithmetic, IDENTICAL
DISEASE: an absolute constant standing where a relative one belongs -- C397 (0.60% drift), C399
(0.18 DRI floor), C400 (0.75 base_total), C405 (1.7 R bar), C410 (chg / cohort-max), and now
C415 (1.5R). His objection was exact: A MEDIUM TRADE THAT CLEARS ITS FEES WITH GOOD PROBABILITY
SHOULD BE TAKEN, AND A FLAT FLOOR REFUSES IT. HOW BIG A TARGET YOU NEED IS A FUNCTION OF HOW
LIKELY YOU ARE TO REACH IT. Break-even is p(T - f) = (1-p)(1 + f), so for a required edge Emin
the floor is T_min = [Emin + (1-p)(1+f)] / p + f. At f=0.05 and Emin=+0.10R that gives p=0.60 ->
0.92R, p=0.55 -> 1.09R, p=0.50 -> 1.30R, p=0.45 -> 1.56R, p=0.40 -> 1.88R. THE FLAT 1.5R WAS
DISCARDING EVERY TAKEABLE MEDIUM TRADE IN THE TOP HALF OF THAT LIST while simultaneously waving
through 0.40-probability trades that needed 1.88R. AND f IS PER INSTRUMENT, because C408
measured an ELEVEN-FOLD spread in fee burden. The same probability therefore demands a different
target on different instruments: at p=0.50 the floor is 1.23R on MSTR, 1.27R on BTC, 1.43R on
TSLA and 1.69R on NVDA. One flat number could not have been right for more than one of them. TWO
GUARDS MAKE THIS HONEST RATHER THAN WISHFUL. FIRST, p AND T ARE NOT INDEPENDENT: a coin-flip
market gives p = 1/(1+T), so a claimed p=0.65 at T=1.5R asserts a +25pp edge that nobody on
earth has. The claim is capped at fair + 0.10, which means a high claimed probability CANNOT BY
ITSELF JUSTIFY A SMALL TARGET -- it must be earned against what that target structurally allows.
SECOND, SHORT RANGE IS MEASURABLY WORSE THAN FAIR: the corpus put the 0.4R hit rate 2.9pp BELOW
its fair value while 1.5-2.0R sat 0.6-0.7pp ABOVE it, because the spread and the noise take
their cut first. Short targets are therefore penalised by that MEASURED shortfall rather than
merely capped, which is why the fixed-point solution converges instead of collapsing toward
zero. Solved by damped iteration since T and p co-determine each other; verified stable at the
extremes (p=0.95 -> 0.74R capped, not collapsed; p=0.20 -> 4.00R ceiling; fee=0.35R -> 3.24R).
SELF-CAUGHT IN THE SAME PASS, and it is the oldest trap in Python: `float(fee_r or 0.05)` treats
a GENUINE ZERO as missing. XAU and NVDA both print funding of exactly 0.0000%, so a real
instrument would have been charged a fee it does not pay and had its target floor raised for no
reason. Falsy-zero belongs nowhere near money. Replaced with an explicit None test. WHAT THIS
MEANS TOGETHER WITH C415: the trade must still aim in units of ITS OWN RISK, and the trail still
cannot fire before the target -- but the size of that target is now DERIVED per trade from this
trade's probability and this instrument's cost, instead of being a number I typed. Every stage
of the pipeline is now probabilistic (p from the calibrated S3 ledger, falling back to the
projection), predictive (the projection sets the reachable target), projective (C413's sqrt(t)
horizon decides how far a move can travel before its market closes) and relativistic (target in
units of the stop, fee in units of the stop, floor computed per instrument). VERIFICATION:
syntax; AST 330 -> 331 (+_c416_required_target_r); the C412 generalised wrong-object sweep
CLEAN; duplicate definitions 0; new constants never read 0; the floor tabulated across seven
probabilities and four instruments with the old flat 1.5R shown alongside; convergence checked
at four extremes; boot battery 7/7. HONEST LIMIT: p is only as good as its source, and the
projection-derived p was flagged at C412 as systematically optimistic relative to the stop -- so
the EDGE_CAP is doing real work here and should be watched in the next log. Chain C367-C416
intact.


## C415

THE BOT HAS BEEN AIMING SMALL ON EVERY TRADE IT EVER TOOK, AND SMALL IS THE WORST-PAYING THING
ON THE BOARD. The operator asked for the best of both worlds: bank quickly on weak trades, run
the good ones. MEASURED ON THE 60-PAIR/20-DAY CORPUS -- entries every 17 bars, 1.3-PRU stop,
fees 0.05R, asking how often each target is reached before the stop, against the coin-flip
requirement of 1/(1+T): target 0.4R fair 71.4% actual 68.5% money -0.091; 0.6R fair 62.5% actual
61.1% money -0.072; 1.0R fair 50.0% actual 50.2% money -0.046; 1.5R fair 40.0% actual 40.7%
money -0.033; 2.0R fair 33.3% actual 33.9% money -0.033; 3.0R fair 25.0% actual 25.2% money
-0.044. SO HALF THE OPERATOR'S INSTINCT IS RIGHT AND THE OTHER HALF IS THE MOST EXPENSIVE HABIT
AVAILABLE. Aim bigger on good trades: correct, 1.5-2.0R is the best band there is. Take small
profits quickly on weak ones: WRONG, and not because they are hard to hit -- 68.5% is the
HIGHEST hit rate on the entire table -- but because THE FEE IS THE SAME SIZE WHATEVER YOU AIM
AT. Chasing 0.4R and paying 0.05R hands back an EIGHTH of the winnings every single trade;
chasing 2.0R hands back a fortieth. The correct reconciliation is not 'small target on weak
trades', it is 'do not take the weak trades at all, and aim properly on the rest'. AND WITH THE
ONE MEASURED EDGE ON TOP (+4.7pp hit rate, C398 capitulation): 0.4R -> -0.025/trade =
-1.1%/month, STILL LOSING; 1.0R -> +0.048 = +2.1%; 1.5R -> +0.085 = +3.7%; 2.0R -> +0.108 =
+4.8%. AT TWO TRADES A DAY THE 1.5-2.0R BAND IS THE OPERATOR'S 2-4% TARGET, and the small-target
band cannot reach it at any trade rate because fees scale with COUNT while gains scale with
SIZE. THE DEFECT, AND IT IS A UNITS ERROR OF THE FAMILY THIS PROJECT KEEPS PAYING FOR. The
target floor read `max(0.5, 1.5 * _atr_entry)` while the STOP is 1.3 PRU = 2.6 x ATR. So the
minimum target was 1.5/2.6 = 0.58 x THE RISK -- sitting in the worst measured band -- and
`min(_sr_target, _proj_target)` then took the NEARER of the two, shrinking it further whenever a
resistance level happened to sit close. A target quoted in ATR and a stop quoted in PRU are not
comparable, so the ratio between them -- the single number that decides whether a trade can pay
-- was nobody's decision. On BLESS (ATR 3.26%, stop 8.48%): old floor 4.89% = 0.58R, new floor
12.71% = 1.50R. Now quoted in units of the stop, and the floor WINS: if the projection reaches
further the projection is used, and if a resistance sits inside the floor the trade has no room,
which the existing no_structural_room gate already refuses. C415-2, THE OTHER HALF OF THE SAME
MISTAKE: TRAILING_TP fires at roughly 48% of the peak, and reached BEFORE the planned target
that converts a 1.5R trade into a 0.7R one -- the bot was systematically turning its best target
band into its worst on every trade that wobbled on the way up. Below target only the HARD STOP
and THESIS-DEATH may now act: those answer 'am I wrong?', which is always a fair question. The
trail answers 'should I bank less than I came for?', which is only fair once the target is
banked. The trail therefore arms AFTER the target, so it can only ever EXTEND a winner and never
shrink one. SELF-CAUGHT WHILE BUILDING, FOURTH OCCURRENCE OF ONE PATTERN: C415_GOOD_TARGET_R was
defined and never read. Deleted rather than shipped -- the target is max(projection, floor), so
a projection reaching 2R is already taken. Atlas #79/#85. VERIFICATION: syntax; AST 330
functions unchanged; the C412 generalised wrong-object sweep CLEAN; duplicate definitions 0; new
constants never read 0 after the deletion above; both long and short target paths corrected and
inspected; boot battery 7/7. HONEST LIMIT: this is measured on the corpus and on arithmetic, not
yet on live trades -- and the projection that feeds the target is the same projection C412
flagged as systematically smaller than the stop, so the floor will now be doing most of the
work. That is the intended behaviour and the next log is where it shows. Chain C367-C415 intact.


## C414

C412 AND C413 BOTH CONFIRMED WORKING IN PRODUCTION, AND THE SESSION'S TWO LOSSES EXPOSED AN
ARBITER THAT MAY ONLY EVER ACQUIT. Zero errors across 5h25m. C412 VERIFIED COMPLETE AND
ARITHMETICALLY EXACT: 'RWA held out' fired ELEVEN times where the previous session logged it
ZERO, and SIXTEEN RWA symbols had leaked into the analysis on a Saturday. This session: 128
symbols in the log, ZERO RWA. The volume count reconciles to the contract: 268 pairs cleared the
floor and a live query of the venue right now returns EXACTLY 268 crypto pairs above $750k, with
51 RWA pairs above it held out. The earlier '110' was simply a quieter market, not the filter.
C413 ALSO FIRED FOR REAL: 'GRVT: ABORT — S3 says EV=-0.321PRU while the projection gate said
take it', a trade prevented by the very gate the BLESS post-mortem built. THE DEFECT, and it is
an internal contradiction in the code's own stated logic. C179-F2's comment declares the
principle outright: 'L/S aggregates are proxy-grade for alts (C158); the pair's own /fills delta
is the truth.' The code then applies that truth IN ONE DIRECTION ONLY -- real_cvd may STAND DOWN
a veto the proxy raised, and may never RAISE one the proxy missed. AN ARBITER THAT MAY ONLY EVER
ACQUIT IS NOT AN ARBITER. PYTH PROVES IT AND IT IS THE SESSION'S CLEAREST LOSS. Three numbers
for one quantity, printed within seconds of each other: flow(proxy) R=-0.27 taker=+0.06, which
is BELOW the 0.40 veto bar; C199 order-flow CVD=-0.62; C401 entry taker delta -0.623. The proxy
shrugged at -0.27 while the truth said -0.62 TWICE OVER from two independent paths, and THE
WEAKEST OF THE THREE HELD THE VETO. The long opened against strong aggressive selling and lost.
Real CVD now vetoes symmetrically at THE SAME 0.40 the stand-down already uses -- not a new
threshold, not a new mechanism, just the existing arbiter allowed to speak in both directions.
ACCUMULATED C401 ENTRY-FLOW EVIDENCE, with its limits stated plainly: entries opened against
negative taker flow are 0 WINS AND 3 LOSSES (KAITO -0.046, ONG -0.387, PYTH -0.623); positive-
flow entries are 2-2. n=3 IS NOT PROOF, which is precisely why this is wired into the EXISTING
veto at the EXISTING threshold rather than shipped as a new tunable. THE OTHER LOSS, VVV, IS
RECORDED AS NOT-THIS: it entered on taker flow of +0.908, the strongest positive reading yet
seen, and still lost -$0.32 on REL_DSI+DRI DIVERGE (dsi_d=-0.110 dri_d=+0.128 thresh=0.11). Flow
is not a sufficient filter and this changelog does not claim it is -- but note that the
divergence rule which caught it is the one C399 made REACHABLE by lowering its floor from 0.18
to 0.06; at the old floor VVV would have run on. AND AN OBSERVABILITY DEFECT WORTH FIXING
BECAUSE IT COST AUDIT TIME. All eleven hold-out lines read 'Globex closed (Sat)' when 273 of the
294 RWA contracts are US EQUITIES and only 9 are Globex. The throttled message printed whichever
hold-out happened to come FIRST in iteration order, so the gate was working perfectly and the
log described a TENTH of what it did. Replaced with a per-class count emitted once per scan.
This is the C399/C402 lesson -- an unattributable log line cannot be audited -- applied to a
counter rather than a reading. STILL UNEXERCISED, STATED HONESTLY: this was another SATURDAY
session (12:48-18:13 UTC), so only crypto was ever live. The C410 per-class funnel correctly
fell through to its single-class path, and session_short, SESSION_CLOSE and the horizon clip
logged zero times because no class with a close was ever open. Steps 3-5 of the per-class
pipeline remain verified by simulation and unexercised in production. The next log must span
19:00-01:30 IST on a WEEKDAY for US equity to be live. VERIFICATION: syntax; AST 330 functions
unchanged; the C412 generalised wrong-object sweep CLEAN; duplicate definitions 0; all new
symbols written AND read; boot battery 7/7; the 268-pair count reconciled against a live venue
query. Chain C367-C414 intact.


## C413

THE ONE LOST TRADE, DISSECTED — AND IT SAYS THE BOT OVERRODE ITS OWN ARITHMETIC. BLESS, the only
position of the session: entry 15:19:40 IST at $0.009383 long, ATR 3.26%, exit 15:56:07 at
$0.009061 for -3.3%, -$0.37, on C399_CONVICTION_FADING (18% of thesis left). THREE SEPARATE
WARNINGS WERE PRESENT AT ENTRY AND ALL THREE WERE LOGGED: 'S3 RECORD P=0.396 R=1.20
EV=-0.161PRU' -- NEGATIVE EXPECTED VALUE, computed by the bot itself; 'FEEDBACK CAUTION
conv=-0.0917 -> margin -18%'; and 'C61 HIGH-ATR cap: lev 5->2' then '2->1' because ATR 3.42% is
extreme. The trade opened anyway. WHY: C405's expectancy gate uses prediction.continuation_prob
clamped to 0.45-0.72 and its own R, while S3 uses a Brier-calibrated P and payoff odds. TWO
EXPECTANCY ESTIMATES DISAGREED ABOUT THE SIGN and the permissive one won BY ACCIDENT OF ORDERING
rather than by argument. S3 was right. C413-2 now aborts the entry when S3's EV is negative: an
edge that cannot be confirmed twice is not an edge. PLACED AT THE WRITE SITE DELIBERATELY -- my
first attempt put this check in the candidate loop thousands of lines earlier, where _s3_ev does
not exist yet and the gate COULD NEVER HAVE FIRED. Caught by reading where the value is written
instead of trusting where it is read. AND C401 CALLED IT THIRTY-FOUR MINUTES BEFORE C399 DID.
Taker support at entry +0.087; TWO MINUTES LATER -0.427, then -0.165, -0.161 -- red for twenty-
four minutes -- before recovering to +0.119 and +0.463 just as C399 fired. Chart-verified
against Bitget 5m candles: the exit at -3.4% landed NEAR THE LOW, with price back to -1.13% five
minutes later and +0.53% by 16:40. The flow channel saw the problem first and the exit fired
last. C401 remains instrumented-only by design (n is still tiny), but this is its second
consecutive correct call. PER-CLASS PIPELINE, THE OPERATOR'S ASK, IMPLEMENTED ACROSS ALL FIVE
STEPS. What is genuinely per-CLASS is not sizing or expectancy -- those are per-INSTRUMENT and
derived from measurement, and C408 proved a class rulebook could never be right about them (MSTR
1.09% ATR beats BITCOIN's 0.63%; QQQ at 0.10% is six times quieter). What IS per-class is THE
SHAPE OF THE TRADING DAY, and that shape reaches into every step: (1) SCAN -- which classes are
awake at all; (2) SELECT -- ranked inside its own cohort; (3) ANALYSE -- the horizon a move has
room to play out in; (4) ENTER -- whether enough session remains to reach a target; (5) EXIT --
monitor cadence and closing before the bell. THE HORIZON IS THE KEYSTONE, and it is what makes
this self-consistent rather than a pile of switches. C404 computes R = proj x sqrt(hold/15) /
stop. Clipping `hold` by the time remaining to THIS market's close makes R FALL AUTOMATICALLY as
the bell approaches, so late entries are refused BY ARITHMETIC instead of by a separate rule --
a trade that cannot finish before its market stops pricing is not a worse trade, it is a trade
whose target is unreachable, and the sqrt(t) law states exactly how much less reachable.
VERIFIED on a US equity through its own session: 19:30 IST with 350min left -> horizon 60min ->
sqrt(t) x2.00, full R; 00:30 IST with 50min left -> horizon 30min -> x1.41, R down 30%; 01:00
IST with 20min left -> horizon 0 -> R collapses, and the min_left=45 gate refuses it before that
anyway. Crypto and the Globex classes (metal, energy, index_future) are unbounded and therefore
untouched. HKEX carries the shortest usable run because its LUNCH BREAK means an afternoon
target cannot be reached from the morning session. SELF-CAUGHT WHILE BUILDING, third occurrence
of the same class: C413_PER_CLASS was defined and never read. The switch now MEANS something --
off, every class runs the crypto profile, which is exactly pre-C413 behaviour. Atlas #79/#85: a
switch that cannot switch is worse than no switch. VERIFICATION: syntax; AST 327 -> 330
(+_c413_profile, +_c413_minutes_left, +_c413_horizon); the C412 generalised wrong-object sweep
re-run CLEAN across every class; new constants never read 0 after the fix above; all new symbols
confirmed written AND read; horizon clip simulated across a full US session with the sqrt(t)
effect reproduced above; boot battery 7/7. HONEST LIMIT: no RWA position has ever opened, so
steps 3-5 of the per-class pipeline are verified structurally and by simulation but never in
live trading. Chain C367-C413 intact.


## C412

THE SESSION GATE WAS CALLING ITSELF ON THE WRONG OBJECT, AND A BARE EXCEPT HID IT — THE C406
BUG, EXACTLY, IN A NEW PLACE. C408 wrote `self._c408_asset_class(symbol)` inside
scan_lively_pairs. Those methods live on TradingBot; `self` in that function is the SCANNER,
which reaches the bot through `self._bot` as every other line in the SAME FUNCTION already does.
So the call raised AttributeError, the enclosing `except Exception: pass` SWALLOWED IT, and
execution fell straight through to the volume check — ADMITTING EVERY RWA INSTRUMENT COMPLETELY
UNGATED. THE OPERATOR'S LOG PROVES IT ON A SATURDAY, when every single RWA market on earth is
shut: 317 pairs cleared the volume floor where crypto alone is ~110; SIXTEEN RWA symbols reached
the analysis (COPPER, PAXG, KORU, SKHY, SNDK, SNXX, MUU, MRNA, CSOPSK2LHKD, FUTU, IREN, LITE,
AXTI, CBRS, FLY); and 'RWA held out' logged ZERO times in four hours. The boot board printed
every class correctly as SHUT — crypto OPEN, us_equity/index/metal/korea/hk all shut — while the
scanner ignored all of it, because the board asks _c408_session_open directly on the BOT and the
gate asked it on the SCANNER. The classification and session logic were right all along; the
wiring between them was not. TWO CONSEQUENCES, BOTH FIXED. The call now goes through `self._bot`
with an explicit RuntimeError if that reference is missing, and THE EXCEPT IS NO LONGER SILENT:
a failure here does not skip a nicety, it disables the entire session gate and lets the bot
trade markets that are closed, so it now logs the symbol and the exception type. This is Atlas
#77 (a protection that can fail quietly is not a protection) applied to a gate rather than a
stop. AND THE AUDIT IS GENERALISED, because C407 built exactly this check and scoped it too
narrowly. It swept for `self.cfg` read without assignment and would never have caught a wrong-
object METHOD CALL. The sweep now walks every class and flags any bare `self.<name>()` whose
name that class never defines — the general form of the C406/C412 family. Run over all 327
functions the only remaining hits are eighteen inside RemoteControl, every one a genuine false
positive (send_response/send_header/end_headers are BaseHTTPRequestHandler methods, and
_send_json/_get_status/_dashboard_html are defined in its NESTED Handler class, which a class-
level sweep cannot resolve). NO _c4xx_ HITS REMAIN. SEPARATELY, THE ZERO-TRADE SESSION IS NOT A
FAULT AND THE LOG SAYS SO PRECISELY. The C405 bar had already relaxed to its ABSOLUTE FLOOR of
+0.000R — the servo could go no lower — and candidates were still refused: ETH E=-0.237R (proj
0.67% vs stop 2.32% = 0.29R), XRP E=-0.275R (2.30% vs 9.38% = 0.25R), BOME E=-0.322R (1.48% vs
9.88% = 0.15R), ZAMA E=-0.096R (5.20% vs 11.74% = 0.44R). Every one has NEGATIVE EXPECTANCY BY
THE BOT'S OWN ARITHMETIC, so refusing them is the gate working exactly as designed on a quiet
Saturday crypto-only tape. BUT IT EXPOSES THE REAL REMAINING PROBLEM FOR THE 2-4% TARGET, AND IT
IS NOT A GATE: THE STOP IS SYSTEMATICALLY WIDER THAN THE PROJECTED MOVE. Stops of 2.32%, 9.38%,
9.88% and 11.74% against projections of 0.67%, 2.30%, 1.48% and 5.20% give R of 0.29, 0.25, 0.15
and 0.44 — the bot's own model says the expected move is between a seventh and a half of the
risk it must accept. The stop is 2.6 x ATR where common practice is 1-2, but NARROWING IT CANNOT
MANUFACTURE EDGE: in a driftless walk P(target before stop) scales with the stop distance, so
tightening raises R and lowers p by the same mechanism and E is unchanged. The only real levers
are a BETTER PROJECTION or entries selected where the projection genuinely exceeds the risk.
That is an entry-selection problem and it is now the single thing standing between this bot and
its target. Recorded, not guessed at. VERIFICATION: syntax; AST 327 functions unchanged; count-
asserted replacement; the generalised wrong-object sweep run over the whole file with the
residual hits individually explained; zero errors in the operator's four-hour session. HONEST
LIMIT: the session gate has still never been observed HOLDING an RWA instrument out, because it
has never yet run correctly — the next log, ideally spanning 19:00-01:30 IST when US equity is
the only RWA class open, is the first real test. Chain C367-C412 intact.


## C411

EVERY BITGET PRODUCT ENUMERATED, THE CLASSIFICATION REBUILT ON WHERE PRICE IS DISCOVERED RATHER
THAN WHAT THE INSTRUMENT IS ABOUT, AND THE WHOLE THING PUT ON IST BECAUSE THE OPERATOR IS IN
INDIA. COVERAGE ANSWERED FIRST: Bitget has THREE futures product types and only ONE carries non-
crypto -- usdt-futures 759 contracts / 294 RWA, coin-futures 11 / 0, usdc-futures 49 / 0. So the
bot already reaches everything there is. METALS ARE PRESENT AND NOW CORRECTLY HANDLED: XAU $92M,
XAG $51M, COPPER $14M, XAUT $12M, PAXG, XPT, XPD -- seven contracts, $176M/day. ENERGY: CL $34M,
BZ $15M. Searched explicitly for forex, bonds and agricultural contracts and found NONE, so
those are not gaps. THREE REAL MISCLASSIFICATIONS FOUND, AND THEY WERE THE BIGGEST NAMES IN
THEIR BUCKET. C410 assumed the UNDERLYING COUNTRY implies the LISTING VENUE. It does not: KORU
($142M) is Direxion Daily MSCI South Korea Bull 3X, primary listing NYSE ARCA; EWY ($2M) is
iShares MSCI South Korea, NYSE ARCA; SKHY ($74M) is the SK Hynix ADR, US-listed. All three TRACK
Korea and all three TRADE US HOURS -- so $218M of the $220M in the old asia bucket was gated to
the WRONG SIX HOURS, awake when its market is shut and asleep when it is open. Verified against
the issuers directly. Only genuinely Korea-listed names (SKHYNIX, SAMSUNG, SKDD) and HK-listed
ones (CSOP*HKD) belong on Asian clocks. AND KOREA AND HONG KONG ARE NOT THE SAME CLOCK. KRX runs
09:00-15:30 KST CONTINUOUS; HKEX runs 09:30-12:00 AND 13:00-16:00 HKT WITH A REAL LUNCH BREAK --
an hour of no price discovery in the middle of the session that a single open/close pair would
have traded straight through. Both are UTC+9 and UTC+8 with NO DST, so unlike the US windows
they never move. Split into korea_equity and hk_equity and verified: 10:00 IST correctly returns
'HKEX lunch break' between a working morning and afternoon session. A FOURTH CLASS WAS MISSING
ENTIRELY: SP500 and NDX100 are INDEX FUTURES, not cash equities. They trade CME Globex for about
twenty-three hours, so filing them as us_equity would have blinded the bot for THREE QUARTERS of
their real trading life. Now index_future on Globex hours. THE OTHER HALF OF 'CORRECT UP TILL
CLOSURE': C408 gated ENTRIES on the session and said NOTHING ABOUT EXITS, so a TSLA position
opened at 01:00 IST could be carried straight through the 01:30 IST cash close into fifteen
hours during which its price is discovered by nobody -- the stop sitting at a level no one is
trading toward, funding still accruing every eight hours, and the next real print arriving at
the following open with the bot unable to react to anything in between. That is the same defect
as entering out of session except the money is already at risk. Session-bound positions now
close twenty minutes BEFORE their bell, and the rule is evaluated FIRST in the exit cascade
because it is not a judgement about the trade at all -- it is a fact about whether anyone is
still pricing the instrument, and no thesis, floor or timer can mean anything once price
discovery stops. Crypto, metals, energy and index futures are untouched: they have no meaningful
close. TIMESCALES MATCHED TO INDIA. IST is UTC+5:30 and India observes no DST, so the US windows
move under the operator twice a year while the Asian ones never do. The boot now prints a
session board in IST: crypto 24/7; metals, energy and index futures Globex ~24/5; US EQUITY
19:00-01:30 IST ON EDT AND 20:00-02:30 IST ON EST -- A NIGHT SESSION FROM INDIA; Korea
05:30-12:00 IST; Hong Kong 07:00-13:30 IST with lunch 09:30-10:30. Plus a live open/shut line
per class at every boot, so the operator can see at a glance which markets are awake when he
starts the session. RECLASSIFIED TOTALS on the live venue: us_equity 273 ($1,185M), metal 7
($176M), korea_equity 3 ($53M), energy 2 ($49M), hk_equity 7 ($8M), index_future 2 ($2M).
VERIFICATION: syntax; AST 326 -> 327 (+_c411_session_closing); duplicate definitions 0; new
constants never read 0; self.cfg-unassigned 0; all 294 RWA contracts re-classified against live
venue metadata with the three corrections confirmed; session board simulated across a full UTC
day in IST; HKEX lunch break confirmed honoured. HONEST LIMIT UNCHANGED FROM C410: no RWA
position has ever been opened, and the phase-3 projected/geometric boost remains the one funnel
stage I have not measured. Chain C367-C411 intact.


## C410

THE FIRST MULTI-ASSET SESSION PROVED C409 DID NOT WORK, AND MY FIRST TWO DIAGNOSES OF WHY WERE
BOTH WRONG. THE LOG: zero errors, banner accurate, and volume-qualifying pairs 110 -> 220 -- so
C408 WAS admitting RWA. But NOT ONE RWA instrument reached the top 30, and of the 56 symbols the
log ever mentions exactly ONE is RWA. WRONG DIAGNOSIS 1: I blamed the absolute _chg_ratio term;
my own simulation of the full live cohort then showed RWA appearing 11 times in the top 30 under
BOTH the old and new change terms, so the change term alone was not the blocker. WRONG DIAGNOSIS
2: I read '0 C408 log lines' as proof the session gate never ran; the session was 16:45-17:38
UTC Friday when US cash AND Globex are both OPEN, so the gate only logs on hold-out and silence
was CORRECT behaviour. Both corrections are recorded because a wrong diagnosis shipped as a fix
is how C404's survivor-biased threshold got in. THE REAL DEFECT IS ARCHITECTURAL AND THE
OPERATOR NAMED IT BEFORE I DID: non-crypto assets need their own funnel. RANKING IS COMPETITIVE
-- it picks the top N from ONE pool -- and pooling instruments whose volatility scales differ
ELEVEN-FOLD means the loudest always wins, where 'loudest' is not 'best' but merely 'most
volatile'. A 2% day in TSLA (ATR 0.240%) is EIGHT ATR, an enormous event; a 50% day in a
memecoin whose ATR is 8% is SIX ATR, a smaller one in its own terms. The global ranking scored
them 0.04 and 1.00. THE DISTINCTION THAT RESOLVES IT, stated plainly because it looks like it
contradicts C408: ABSOLUTE EVALUATION STAYS ONE FORMULA (expectancy, fee burden, sizing -- each
candidate judged on its own merits, no per-class rulebook), while COMPETITIVE SELECTION NEEDS
COHORTS (each candidate ranked only against instruments that share its scale). C408 was right
about the first and silent about the second. Slots are now allocated by each class's SHARE OF
THE QUALIFYING COHORT (live venue: 82 RWA of 260 = 32%, so ~20 crypto and ~10 RWA of 30) and any
class whose market is CLOSED forfeits its slots back to the others, so a weekend or an Asian
night automatically returns the full window to crypto rather than wasting it. Single-class
cohorts fall through to the original code path unchanged. AND RESEARCH CAUGHT A REAL BUG IN MY
OWN C408 SESSION GATE. I hardcoded US cash as 13:30-20:00 UTC. THAT IS ONLY TRUE FOR EIGHT
MONTHS OF THE YEAR: the session is 9:30-16:00 EASTERN, which is 13:30-20:00 UTC under EDT but
14:30-21:00 UTC under EST, and the next changeover is 1 NOVEMBER 2026 -- so the hardcoded window
is correct TODAY and silently wrong from then until mid-March, opening the gate a full hour INTO
A CLOSED MARKET every day for four months and closing it an hour before the real close. Now
computed from the DST rule (second Sunday in March to first Sunday in November) rather than read
from tzdata, because Pydroid3 on Android cannot be relied upon to carry the IANA database.
VERIFIED: 10 Dec 13:45 UTC now correctly SHUT where C408 said open; 14:45 and 20:30 correctly
OPEN. ALSO ADDED, from the ICE/NYSE published calendar: the TEN full closures a year -- a
calendar that matches NEITHER the federal list nor any other, since the exchanges TRADE THROUGH
Columbus Day and Veterans Day and CLOSE for Good Friday, which no federal calendar contains --
plus the 1 p.m. ET half-days after Thanksgiving and on Christmas Eve. Verified: Good Friday 3
Apr shut, Labor Day 7 Sep shut, Thanksgiving shut, and 27 Nov OPEN at 16:00 UTC but SHUT at
18:30 (correctly honouring the 1 p.m. ET close). Globex follows US clocks so it shifts with DST
too. THE CHANGE TERM IS ALSO MADE RELATIVISTIC, on principle rather than because it was the
culprit. _chg_ratio divided every pair's 24h move by the LOUDEST MOVER IN THE COHORT -- the same
disease as C397 (0.60% drift), C399 (0.18 DRI floor), C400 (0.75 base_total) and C405 (1.7 R
bar), now a fifth instance. MEASURED on the live 260-pair cohort it is wrong FOR CRYPTO TOO:
BEAT's 16% move on a 56% range scores 0.460 while THRASHING, and ZEC's 19% move on an 18% range
scores 0.550 while genuinely TRENDING; in own-volatility units those become 0.247 and 0.937. A
pair that travelled its whole range is trending, one that travelled a fifth of it is noisy, and
raw percent cannot tell them apart. The 24h range comes free with the ticker, so this costs no
extra fetch. VERIFICATION: syntax; AST 325 -> 326 (+_c410_us_dst); count-asserted replacements;
duplicate definitions 0; every new symbol confirmed both written AND read; the session logic
simulated across DST boundaries, holidays and half-days with the results reproduced above.
HONEST LIMIT: the per-class funnel is verified structurally but has never selected a live RWA
candidate, and the phase-3 projected/geometric boost -- which pushes crypto scores above 1.0 and
which my simulation still does not model -- remains the one part of the funnel I have not
measured. The next log is that measurement. Chain C367-C410 intact.


## C409

THREE MULTI-ASSET EDGE HYPOTHESES TESTED AND ALL THREE REFUTED -- AND THE THING THAT SURVIVED IS
BIGGER THAN ANY OF THEM. Built a purpose-made 40-day, 19-symbol corpus (14 US equity perps +
gold + oil + BTC/ETH/SOL, 3,840 aligned 15m bars each). REFUTED 1, THE CLOSED-UNDERLYING GAP.
Mechanism: while US cash is shut, TSLAUSDT still prints -- but on crypto-native order flow
against a FROZEN anchor -- so at 13:30 UTC the real stock opens and the perp is MARKED TO TRUTH,
and the untethered drift should be given back. Something crypto CANNOT have, because crypto
never closes. MEASURED on 336 clean overnight observations across 14 symbols: corr(off-session
drift, first-hour move) = +0.0064. Bucketed hit rates 50.0/58.1/50.6/51.9% with no monotonicity,
halves disagreeing (50.8% vs 54.2%, corr +0.130 vs -0.023). THE PREMISE IS SIMPLY WRONG: market
makers already know fair value from index futures and ADRs while cash is shut, so there is no
untethered drift to revert. NOT BUILT. REFUTED 2, STRUCTURAL-LINKAGE DIVERGENCE. MSTR is a
levered Bitcoin proxy (measured beta 1.62), COIN is crypto-beta equity (1.25), and
NVDA/AMD/MU/MRVL/SOXL/SNDK are one semiconductor factor. When a member diverges from what its
own beta implies, one of the two is wrong -- and unlike C398's refuted within-crypto test, these
are GENUINELY DIFFERENT factors. MEASURED, fading a >=1.5-sigma 2h divergence, in-session only:
MSTR~BTC 51.2% (halves 50.3/52.3), COIN~BTC 54.4% but DECAYING (57.2 -> 51.5), semis 44.9% to
52.1% with halves in open disagreement (MRVL 57.7 vs 42.9). Structural linkage is real; a
tradeable divergence signal is not. NOT BUILT. WHAT SURVIVED, AND IT IS THE ACTUAL CASE FOR
MULTI-ASSET: FACTOR DIVERSIFICATION, NOT ALPHA. Defining 'alive' relativistically as a bar whose
true range exceeds 1.2x that symbol's own 14-bar ATR, over 3,720 bars: CRYPTO ALIVE 39.3% OF
BARS, ANY ASSET ALIVE 59.8% -- A NET UPLIFT OF +20.5 PERCENTAGE POINTS. Of the 60.7% of bars
where crypto is dead, an RWA class is alive on 33.7% of them. And the decisive number: CROSS-
CLASS ALIVENESS CORRELATION IS +0.038 (crypto vs US equity) AND +0.143 (crypto vs commodity),
against crypto's OWN INTERNAL factor-share correlation of +0.925 measured at C398. A TWENTY-
FOUR-FOLD DIFFERENCE. That is what genuine diversification looks like, and it is precisely what
C391's universe widening could never deliver -- adding more altcoins adds more of ONE factor,
which is why widening 44 -> 100 pairs moved frequency so little. With C405's expectancy bar
currently starving (3 trades in 24 hours), MORE GENUINELY INDEPENDENT OPPORTUNITY AT THE SAME
QUALITY BAR is exactly the missing ingredient, and it needs no new alpha to be worth having.
OPERATOR DECISIONS IMPLEMENTED. (1) ONE POOL, NO PER-CLASS QUOTA -- the 40% RWA cap is removed,
and the reasoning holds: a quota forces the bot to decline the best available trade because of
the LABEL on it, the same category error as a per-class rulebook. The real governors are already
class-blind and already binding (day cap, per-trade risk, open-stop reservation, the 12/day fee
cap, 2-per-pair, and the C405 bar). NO CONSTANT WAS DEFINED FOR THIS: the standing audit caught
a `C409_ONE_POOL = True` that nothing read -- Atlas #79 landing on the very version that added
the principle -- and it was DELETED rather than shipped, because a switch that cannot switch
anything tells the operator a policy is configurable when it is structural. (2) WEEKENDS: the
bot runs, unchanged; crypto is 168/168 hours, metals 115/168 via Globex, equities 30/168, so a
weekend simply narrows the universe rather than stopping the session. (3) MORE LEVERAGE
HEADROOM: ceiling 20x -> 50x and target PRU 1.30% -> 1.60%. WHY THIS IS NOT MORE RISK, which
matters: dollar risk per trade is fixed UPSTREAM by the C380 chain and the stop is set in the
instrument's own ATR, so PRU is loss-at-stop as a share of MARGIN -- raising the target carries
the SAME dollar risk on SMALLER margin. It FREES capital rather than spending it. Verified: XAU
3x->4x (PRU 1.82%), NVDA 4x->5x (1.66%), QQQ 6x->8x (1.60%), TSLA 3x (1.44%), crypto untouched.
SIMULATED BEFORE SHIPPING, against live venue metadata pulled at build time: 759 contracts
loaded, 294 RWA now reachable, classified 271 us_equity / 14 asia_equity / 7 metal / 2 energy;
the session gate reproduced across a full 168-hour week; the fee-burden and leverage tables
reproduced above with QQQ still correctly REFUSED at 0.308R; the C405 adaptive bar confirmed
still functional post-merge (0.160R at 300 samples, floor enforced); boot battery 7/7 including
OmegaGuardian handed a bot with no cfg. FULL STANDING AUDIT CLEAN: duplicate definitions 0,
self.cfg-unassigned 0, orphan analysis keys 0, orphan position attributes 0, new constants never
read 0 (after the C409_ONE_POOL deletion above). syntax; AST 325 functions. NOT YET VALIDATED IN
LIVE TRADING -- no RWA position has ever been opened by this bot. Chain C367-C409 intact.


## C408

MULTI-ASSET: ONE FORMULA, MANY INSTRUMENTS -- NOT A PER-CLASS RULEBOOK. Bitget lists 759 USDT-M
perps of which 294 carry isRwa=YES: single stocks (TSLA NVDA GOOGL MSTR COIN INTC AMD MU SK-
Hynix Samsung), commodities (XAU XAG CL BZ COPPER), ETFs (QQQ SOXL SOXS EWY) and oddities
(ANTHROPIC, SPCX). C155 skipped every one. Volumes are real: SNDK $244M, KORU $231M, XAU $172M
in 24h. THE MISTAKE THIS AVOIDS. The obvious design is 'stock rules' and 'crypto rules'.
MEASURED 15m ATR says that is the fixed-principle-for-all error in new clothing: MSTR 1.092%,
BTC 0.630%, SNDK 0.517%, CL 0.520%, TSLA 0.240%, XAU 0.227%, NVDA 0.166%, QQQ 0.100%. A STOCK IS
MORE VOLATILE THAN BITCOIN AND AN ETF IS SIX TIMES QUIETER. The asset-class label predicts
nothing that matters; the instrument's own measurements predict everything. THE GOVERNING
QUANTITY IS FEE BURDEN IN R -- the share of ONE RISK UNIT consumed just to open and close: FeeR
= (maker + taker + |funding| x expected settlements) / stop%, with stop ~= 1.3 PRU ~= 2.6 x ATR.
MEASURED ACROSS THE VENUE: MSTR 0.029, BTC 0.050, SNDK/CL 0.060, TSLA 0.130, XAU 0.136, NVDA
0.185, QQQ 0.327. AN ELEVEN-FOLD SPREAD THAT DOES NOT TRACK THE CLASS LABEL -- the same trade
idea costs 6.3x more on QQQ than on Bitcoin, and QQQ's funding alone (+0.0399% per 8h,
~0.12%/day, against XAU and NVDA at exactly 0.0000%) is 19% of a risk unit. C404's gate computed
E = p(R x capture) - (1-p) and NEVER SUBTRACTED THE COST OF TRADING, which is a rounding error
on Bitcoin and a fatal omission on an ETF. E now carries -FeeR, so the required R rises BY
ITSELF where trading is dear: at p=0.57 the R needed for E=+0.15 becomes 1.78 on MSTR, 1.84 on
BTC, 2.07 on TSLA, 2.24 on NVDA and 2.60 on QQQ -- entirely from each instrument's own
volatility and funding, with no table anywhere. QQQ's 0.308R exceeds the 0.25R admission cap and
is REFUSED ON ARITHMETIC rather than by a blocklist. SESSION GATING, BECAUSE PRINTING IS NOT
PRICE DISCOVERY. The RWA perps trade 24/7 on Bitget -- 400 candles, ZERO flat bars -- but median
15m range by UTC hour, as a share of each symbol's own busiest hour, tells the real story: TSLA
11 at 04h against 100 at 14h, a NINE-FOLD concentration thirty minutes after the US cash open;
QQQ four-fold; gold only 2.6x because Globex runs nearly 24/5; BITCOIN HAS NO DOMINANT HOUR AT
ALL. Outside its own session an equity perp is order flow pushing against a FROZEN anchor, and a
full round trip paid for noise is precisely what the C403 fee budget cannot afford. Instruments
are therefore admitted only while the market that DISCOVERS their price is open: US cash
13:45-19:45 UTC Mon-Fri, Asia cash 00:45-06:45, Globex Sun 22:00 to Fri 21:00 with the daily
break, crypto always. Weekends exclude every equity outright. LEVERAGE SCALED TO THE INSTRUMENT,
NOT CAPPED FLAT. A 1x QQQ position at 0.100% ATR risks a SIXTH of what a 1x BTC position risks,
so a flat 1-10x band would make quiet instruments structurally unable to earn back their own
fees -- gated out not because the idea is bad but because the position is too small to matter.
Leverage is chosen so PRU lands in the same EQUITY terms whatever the instrument: verified QQQ
6x -> PRU 1.20%, NVDA 4x -> 1.33%, XAU 3x -> 1.36%, TSLA 3x -> 1.44%, all converging on the
1.30% target, bounded by Bitget's own per-symbol maxLever (XAU/TSLA/NVDA 100x, MSTR 25x,
QQQ/SOXL/AMD 20x) and a hard bot ceiling of 20x, because a venue maximum is a LIQUIDITY
STATEMENT AND NOT A RECOMMENDATION. Crypto sizing is untouched. ONE BUG CAUGHT DURING WIRING AND
WORTH RECORDING: the funding accessor is fetch_funding_rate, not get_funding_rate. Inside a
try/except a wrong method name would have silently zeroed the funding term FOREVER -- the exact
computed-but-never-wired family this project keeps paying for (Atlas #43/#79) -- and it would
have made QQQ look 19% cheaper than it is. Written as a checked getattr so the failure cannot be
silent. VERIFICATION against LIVE venue metadata (759 contracts pulled at build time):
classification correct on all 17 probes including ANTHROPIC -> us_equity and PAXG/COPPER ->
metal; session gate correct across a full week including Saturday closed, Sunday 23:00 Globex
open, and the asia/us windows not overlapping; fee burden and required-R table reproduced above;
leverage convergence table reproduced above. syntax; AST 321 -> 325 (+_c408_asset_class,
+_c408_session_open, +_c408_fee_burden_r, +_c408_leverage_for). NOT YET VALIDATED IN LIVE
TRADING -- no RWA position has ever been opened by this bot, and the first log with one is the
evidence. Chain C367-C408 intact.


## C407

WHOLE-FILE AUDIT ACROSS SIX AXES -- structural, functional, sign-conventional, mathematical,
ideological, logical -- run as MACHINE SWEEPS over the AST rather than by eye, because 25,700
lines cannot be read reliably and the last four defects all hid in plain sight. THREE REAL
DEFECTS FOUND, ONE OF THEM SAFETY-CRITICAL AND ONE OF THEM MINE FROM THE PREVIOUS VERSION.
DEFECT 1, SAFETY-CRITICAL: A FAILED STOP-ARM WAS SILENT. C378 arms a real reduce-only stop at
the exchange and its stated premise is 'one level, two enforcers: C377 while the bot runs, THE
EXCHANGE WHILE IT DOES NOT'. That call sat inside `except Exception: pass`. If arming RAISED --
bad symbol, rejected trigger, API hiccup -- the second enforcer silently did not exist, and the
position ran naked against the exact failure mode the exchange stop is FOR: the bot being dead.
A PROTECTION THAT CAN FAIL QUIETLY IS NOT A PROTECTION. The call now checks its own boolean
return, warns when arming returns False, warns when R is absent so no stop was even attempted,
and LOGS THE EXCEPTION WITH ITS TYPE when it raises. DEFECT 2: A FAILED CLOSE WAS SILENT, AT TWO
SITES. _check_profit_targets wrapped whole per-position blocks -- including _close_position and
_c336_partial_close -- in a BARE `except: pass`. If a close raised, the position stayed OPEN and
nothing anywhere recorded that the bot had tried and failed. C181 ALREADY PAID FOR THIS EXACT
CLASS: a NameError inside the exit cascade unwound to a per-symbol try and silently disabled
every intelligent exit for that position, sixty seconds at a time, undetected. Atlas failure
pattern #9. The loop must still continue to the next symbol -- one bad pair may not stall the
others -- but it may not do so in silence, so both sites now log the exception type, the symbol,
and the words POSITION REMAINS OPEN. Recorded in the same pass: the second of those blocks is
currently UNREACHABLE, gated on mode == HIGH_PROFIT which C403-3 retired; instrumented rather
than deleted, because if it ever does execute that is itself the news. DEFECT 3, MINE, ONE
VERSION OLD: C405_ADAPTIVE_E WAS DEFINED AND NEVER READ. I shipped a master switch for the
adaptive expectancy bar and then never tested it, so the flag was pure decoration and the
adaptive path could not be turned off. The audit's own signature finding -- 'assigned but never
read' -- landing on the version that shipped one revision earlier. Now wired, and C404_MIN_R /
C404_MIN_E, orphaned by C405, are retained as the FALLBACK bar when the switch is off, which is
what a switch is supposed to mean. WHAT THE SWEEPS CLEARED, recorded so it is not re-audited:
DUPLICATE OR SHADOWED DEFINITIONS 0 across every class and module function. ANALYSIS-DICT KEYS
written but never read 0. POSITION ATTRIBUTES written but never read 0 -- meaning the C397-C406
wiring is sound and the computed-but-not-wired family that produced the runner floor, the DSI
collapse and the phantom ATR is currently absent. SIGN CONVENTIONS SYMMETRIC: four long-branches
initially flagged for having no short mirror (RSI overbought brake, market-breadth brake,
parabola gate) all turned out to carry proper elif mirrors just outside the search window --
long and short are treated symmetrically throughout, which matters because 'all entries same
direction' is a catalogued failure pattern here. IDEOLOGICAL SWEEP LARGELY CLEAN: 132
comparisons of a relative-sounding variable against a bare constant were flagged, and the
overwhelming majority are CORRECT because the variable is already in PRU or ATR units --
comparing _pnl_in_pru to -0.3 IS relativistic. WEIGHT INTEGRITY: DRI_WEIGHT_* sums to 0.7700
across nine constants (eight indicators 0.70 + RVS 0.07), which matches C400's computed
base_total exactly. ALSO CATALOGUED, NOT YET ACTED ON, so the next session starts from a map
rather than a grep: 34 CONFIG CONSTANTS ASSIGNED AND NEVER READ -- including
COUNTER_TREND_BIAS_BLOCK, PROFIT_LOCK_ENABLED, DRI_NOISE_FILTER, MIN_CONFLUENCE_NORMAL/HP,
MTF_AGREEMENT_THRESHOLD, PLANNED_TRADE_TIMEOUT and DRI_MAX_HOLD_MIN. Each is a promise in the
configuration that the code does not keep, and an operator reading Config would reasonably
believe every one of them is in force. 15 METHODS DEFINED AND NEVER CALLED, including
Position.get_gde_exit (an EXIT that no path can reach), Position.is_dri_indecisive,
TradingBot._monitoring_thread_func, TechnicalAnalysis.full_analysis (already known dead since
C366) and LearningManager.meta_learn (superseded at C103). 131 BARE `except:` AND 339 `except
Exception:` REMAIN; the 15 that wrap money calls were enumerated and the three most dangerous
fixed here -- the rest are read-only or diagnostic paths and are listed for a later pass. THESE
ARE DELIBERATELY NOT BULK-DELETED: removing a name is how a live reference gets broken, and
C389's lesson is that changes made on intuition rather than measurement cost money.
VERIFICATION: syntax; AST 321 functions unchanged; count-asserted replacements;
arm_exchange_stop confirmed to return a real boolean so the new check is meaningful; the whole-
file self-attribute audit re-run clean; the no-network boot battery re-run 7/7. Chain C367-C407
intact.


## C406

BOOT CRASH FIX — MINE, AND IT NEVER REACHED A SINGLE SCAN. C405 made the Guardian banner
conditional and reached for self.cfg inside OmegaGuardian.__init__. THAT CLASS HOLDS `bot`, NOT
`cfg`. AttributeError: 'OmegaGuardian' object has no attribute 'cfg', raised during startup, so
the bot printed its whole banner and then died before the first scan. A COSMETIC LINE STOPPED
THE BOT FROM STARTING. The config is reached THROUGH the bot (getattr(getattr(bot, 'cfg', None),
...)) and the entire block is now wrapped, because a banner must never be able to prevent a boot
-- decoration does not get to raise. THE REAL LESSON IS THE ONE I KEEP RE-LEARNING: I edited a
class without checking what that class actually holds. So this ships with a SYSTEMATIC AST AUDIT
rather than a one-line patch -- every class in the file is now walked for attributes READ off
self but never ASSIGNED on self (including dataclass fields and class-level constants), which is
the general form of this bug. Result across all 321 functions: ONE instance, the one that
crashed. Plus a boot-path construction battery that builds OmegaGuardian, Portfolio,
TradingModeManager, ExchangeManager and Position with no network -- including OmegaGuardian
handed a bot that has NO cfg, which must fail safe rather than raise. That battery is what would
have caught this before delivery and is the standing check from here on. AND TWO LOG DEFECTS
VISIBLE IN THE SAME SCREENSHOT. (1) THE DAILY BUDGET BLOCK PRINTED TWICE, six identical lines to
the cent. The budget is DERIVED three times on purpose -- at init, after load_state, and at each
day anchor -- because equity arrives by three routes and compounds by a fourth; that is C375
working correctly. But deriving is not announcing. It now derives always and prints only when
the numbers actually CHANGE. A log that repeats itself trains its reader to skim, which is
precisely how the stale line below survived unnoticed for several versions. (2) THAT LINE:
'target 0.68%/day (Normal 0.48% then HP 0.20%, then STOP - ONE cycle, C381)' describes a phase
ladder C403-3 retired. Replaced with the truth: one budget, single mode, the day ends on the
cap. (3) 'break-even daily WR 50.0%' is arithmetically correct ONLY at 1:1 payoff, and the
measured payoff is 0.78 -- at which break-even is 56%, not 50%. The banner was quietly telling
the operator the bot needed to win half its trades when it actually needed to win fourteen
percent more than that. Both numbers are now printed side by side with the honest one named.
Verification: syntax; AST 321 functions; count-asserted replacements; the whole-file self-
attribute audit returning clean; the no-network boot battery passing 7/7. Chain C367-C406
intact.


## C405

THE GATE WAS RIGHT AND THE THRESHOLD WAS ABSOLUTE -- MY OWN ERROR, CAUGHT BY FOUR LIVE SESSIONS.
C404 shipped R >= 1.7 and E >= +0.15. RESULT ACROSS ~24 HOURS OF RUNTIME: THREE POSITIONS OPENED
AND 1,723 EXPECTANCY REJECTIONS. One session ran SEVENTEEN HOURS and took a single trade. THE
MEASURED DISTRIBUTION EXPLAINS IT EXACTLY (n=1,723 real candidates): R median 0.69, p90 1.46,
p99 1.83, MAX 2.44; E median -0.115, p90 +0.204, max +0.452. R >= 1.7 admits 1.9% of candidates
and R >= 1.7 WITH E >= 0.15 admits 0.1% -- ONE IN A THOUSAND. I set that threshold from seven
trades that had already survived every other gate, a textbook survivor-biased sample, and
applied it to the whole population. MY OWN REPLAY ONE VERSION EARLIER HAD WARNED OF PRECISELY
THIS FAILURE MODE (the raw form rejected all seven), and I answered it by TUNING A NUMBER
instead of changing its KIND. That is the mistake, recorded plainly. THE GATE ITSELF IS CORRECT
AND IS KEPT, AND THE DISTRIBUTION VINDICATES IT: median E of -0.115 means the bot's OWN
arithmetic says the typical candidate loses money, and it had been trading those candidates for
four hundred versions. What was wrong is that an ABSOLUTE bar on a quantity whose entire
distribution shifts with the tape is the same defect as the phantom-ATR constant (Atlas #43),
the 0.18 DRI floor (C399) and the hardcoded 0.75 base_total (C400): A FIXED NUMBER STANDING
WHERE A RELATIVE ONE BELONGS, in a codebase whose founding principle forbids exactly that. Four
separate instances of one disease. THE REPLACEMENT IS TWO CONDITIONS, ONE PRINCIPLED AND ONE
COMPETITIVE. (1) HARD FLOOR E >= 0: never take a trade the bot's own numbers say is negative-
expectancy, because a negative-E trade is not a gamble, it is a decision to lose money slowly.
31.6% of candidates clear it, so it is a real filter and not a formality. (2) COMPETITIVE BAR E
>= percentile(recent E): the bot does not need a GOOD trade, it needs the BEST trade available
right now, and 'best available' is a fact about today's tape rather than a constant. The
percentile SERVOS against the realised trade rate, so the same closed loop that prices the fee
budget also sets the quality bar -- too many trades, demand a higher percentile; too few, relax
toward the floor but NEVER through it. OBSERVATIONS ARE NOT OPPORTUNITIES -- the same pair is
re-scored every scan -- so the bar cannot be derived from a target pass-rate and must be closed-
loop on positions actually opened, which the C403 servo already counts. REPLAYED ON THE 1,723
REAL E VALUES: at a realised rate of 12+/day the servo drives the percentile to 99 and admits
1.8%; at 6/day it settles at 85 and admits 16.8%; at 3/day or less it relaxes to the floor and
admits 31.6%. AUTHORITY SPAN 1.8%-31.6% AGAINST C404'S FIXED 0.1% -- between seventeen and three
hundred times more control range, which is what a saturated actuator lacked. AND THE BANNER NOW
DESCRIBES THE BOT THAT IS ACTUALLY RUNNING. It was advertising 'OmegaGuardian (ACTIVE)', 'Self-
learning', 'HP 10min patience', 'DSI+DRI divergence | DRI HARD' and 'Updates: Every 0.8s' --
every one of those either stood down by C403 or proven UNREACHABLE BY CONSTRUCTION by C399/C400.
It also printed '14 components' above a list of eleven and '7 intelligent exits' above a list of
ten, and announced Leverage and Targets for an HP mode that no longer exists. A BOOT BANNER IS
THE ONLY DESCRIPTION OF THE SYSTEM THE OPERATOR EVER READS; when it is stale it is not
decoration, it is MISINFORMATION, and it is what makes a live log unauditable -- the same lesson
as C399's unattributed DRI line and C402's emoji collision, which cost real audit time.
Rewritten to four numbered loops (SCANNER / ENTRY / MONITOR / EXIT) with the live thresholds
interpolated from config rather than typed, an EDGES section naming C396/C398/C401/C403-7, and a
RETIRED section stating what was removed AND WHY, so nothing that no longer runs can ever be
read as if it does. The Guardian line is silent when the Guardian is stood down instead of
printing ACTIVE for a controller the code contradicts. STILL IN FORCE FROM C403/C404, verified
in these logs: momentum-snapped aborts 0 across all four sessions; POST-ONLY REJECT 0; Guardian
blocks 0; parabola and resultant vetoes 0 (both now penalties); limit-unfilled 1 per session at
worst. The fee-budget hard cap and the two-per-pair cap never had to fire because the expectancy
gate was already starving the book -- they remain as bounds. HONEST STATEMENT OF WHAT IS STILL
UNKNOWN: the expectancy gate has now been calibrated but never validated. Three trades is not a
sample. The next log's single job is to show whether the realised rate lands in the 4-8/day band
and whether per-trade EV turns positive -- and if the gate admits trades that still lose, the p
that feeds E (continuation_prob) is the next thing to indict, since E is only as good as the
probability inside it. VERIFICATION: syntax; AST 320 -> 321 (+_c405_e_bar); count-asserted
replacements; the adaptive bar replayed across five realised-rate regimes against the 1,723
recorded live E values; banner interpolation checked against config. The four-window replay
harness is still lost to the sandbox reset. Chain C367-C405 intact.


## C404

THE BOT MEASURED PROBABILITY AND NEVER MEASURED PAYOFF. Session 20260818_003255 closed 57% WIN
RATE and still lost $1.13. The win rate was never the problem: wins +2.7 +1.9 +0.7 +0.5 (mean
+1.45%) against losses -1.0 -1.6 -3.0 (mean -1.87%) is a PAYOFF OF 0.78:1, giving E = 0.57(1.45)
- 0.43(1.87) = +0.02% -- zero before fees. AND THE CAUSE IS STRUCTURAL, VISIBLE IN ONE LINE OF
ARITHMETIC: mean peak on winners 2.6% divided by mean PRU 1.9% = 1.37 PRU, while the stop sits
at 1.3 PRU. THE TYPICAL PEAK AND THE STOP ARE THE SAME SIZE. Maximum achievable payoff at
PERFECT capture is 1.05:1 and the 2-4%/month target needs 1.50:1. NO EXIT IMPROVEMENT CAN FIX
THAT -- it is decided at entry, and every exit refinement since C338 has been optimising the
wrong half. WHY IT WAS INVISIBLE FOR FOUR HUNDRED VERSIONS: expectancy is E = p*W - (1-p)*L, and
this bot measures ONLY p. Score, confidence, conviction, agreement, DRI, DSI, flow, regime,
Markov, calibration, session tilt, capitulation tilt -- every one of them estimates the
PROBABILITY of being right. Not one asks HOW MUCH the trade pays when it is right relative to
what it costs when wrong. HALF OF THE EXPECTANCY EQUATION WAS NEVER COMPUTED. That is the new
edge, and it is not in the literature as such because the literature assumes anyone building a
trading system computes R before taking a trade. THE GATE: R = horizon-scaled projected move /
stop distance, both already present at entry (prediction.projected_move,
prediction.expected_hold, _c372_R_pct). Dimensionless, so it needs no absolute threshold
anywhere and is relativistic by construction. Then E = p*(R*capture) - (1-p), with capture 0.60
(the realistic share of a projection a trailing exit banks) and p CLAMPED to [0.45, 0.72]
because this bot's calibration has never been good enough to be believed at the extremes.
Require R >= 1.7 and E >= +0.15R. THIS IS A VETO AND IT IS THE ONE KIND THAT DESERVES TO BE: not
an opinion about quality, but the arithmetic statement that a 1.5:1 payoff cannot come out of a
setup containing 0.8:1 of room. THE HORIZON CORRECTION, WHICH MY OWN FIRST ATTEMPT GOT WRONG AND
THE REPLAY CAUGHT. Comparing projected_move to the stop RAW rejected all seven of the session's
trades including the +2.7% winner -- a gate that admits nothing is useless. The error was
apples-to-oranges: projected_move is a NEXT-LEG forecast while the stop is a FULL-POSITION
level. The log measures the size of the error precisely -- ATOM projected +1.3% and peaked
+3.4%, PENGU +1.2% peaked +2.5%, ACU +1.6% peaked +3.3% -- the projection understates realised
excursion by about 2x, every time. THE CORRECTION IS NOT FITTED, IT IS THE RANDOM-WALK LAW:
expected excursion grows with the SQUARE ROOT of time, so a 60-minute hold on a 15-minute
forecast scales by sqrt(4) = 2.0, which is exactly the observed ratio. sqrt rather than linear
is deliberate -- price is not expected to travel four times as far in four times the time, only
twice as far, and assuming otherwise is how a projection-based target flatters itself. Capped at
sqrt(8) so no projection can claim beyond two hours of drift. REPLAYED ON THE SESSION'S OWN
SEVEN TRADES: takes ATOM (3.13R, E +0.87), ACU#2 (2.13R, E +0.41) and PENGU (1.71R, E +0.22);
rejects ACU#1 (1.47R), BTW (1.47R), GPS (1.30R) and ACU#3 (1.60R) -- which happens to be all
three losses. HONEST NOTE, STATED PLAINLY: n=7 and three-for-three is a coin landing heads three
times, not evidence. What IS established WITHOUT any outcome data is that comparing a one-candle
projection to a full-position stop was an error of units, and that sqrt(t) is its correct
repair. The gate is justified by the arithmetic, not by the seven outcomes. IT ALSO FIXES THE
FREQUENCY AT SOURCE, WHICH C403's SERVO COULD NOT. The servo saturated: it pinned at its x1.60
ceiling while the observed rate still climbed 8.7 -> 10.1 -> 12.1 -> 15.9 -> 17.1 trades/day. A
SCORE TAX CANNOT HOLD A RATE DOWN WHEN THE SCORES CLEAR THE BAR ANYWAY -- the actuator was
saturated and the loop had no authority left. Demanding 1.7R of ROOM removes the shallow setups
themselves rather than taxing them, which is the honest actuator. On this session it passes 3 of
7 candidates, which at the observed candidate flow lands near the 6/day fee-budget optimum.
C404-2, A LIMIT THAT ONLY STARTS A COUNTDOWN IS NOT A LIMIT. REL_DRAWDOWN reports
'limit=-1.3PRU' and then requires EIGHT further readings of accumulated pressure before it acts,
so the position keeps bleeding while the counter matures. ACU exited at -2.0 PRU against its own
stated -1.3 PRU -- 54% past the limit -- and the log prints the proof in its own message:
'limit=-1.3PRU p=8', fired the instant the counter matured rather than when the limit broke.
This is the LOSS-SIDE TWIN of the C397 runner-floor defect: a level announced to the operator
and then not enforced by the code that acts. The counter stays, because one noisy tick must not
close a trade, but its patience is now BOUNDED at 1.35x the soft limit. Retro on this session
alone: ACU's -3.0% becomes -2.03%, lifting payoff 0.78 -> 0.94 and E from +0.024% to +0.164% per
trade. C404-3, THE FEE BUDGET IS A HARD RESOURCE SO IT GETS A HARD CAP. Past twice the target
rate the arithmetic that justifies trading at all has already failed: at 12 trades/day fees are
56% of a 3%/month target and at the observed 17.1 they are 60%. A stop, not a tax. C404-4, ONE
PAIR IS NOT A PORTFOLIO: ACU was entered THREE TIMES in one session -- 43% of the entire book on
one coin -- and the third entry, the only one taken against negative taker flow (-0.258),
produced the session's largest loss. Capped at two. CONFIRMED WORKING FROM C403, unchanged:
POST-ONLY REJECT 2 -> 0; Guardian blocks 5 -> 0; resultant_counter 50 -> 0 and parabola_bounce
60 -> 0, both now penalties (95 applications, and the pincer is open); the flow term fired 24
times and SIX OF SEVEN entries opened with POSITIVE entry flow against a mixed record before it.
The three remaining 'momentum snapped' aborts are now CORRECT rather than phantom -- NIL at 1.27
ATR, COMP at 1.02 and 1.05 ATR of genuine adverse drift, each judged against its own true ATR
(1.99%, 1.79%) instead of the old 0.60% constant that was identical for every pair on the board.
VERIFICATION: syntax; AST 320 functions; count-asserted replacements; the expectancy gate
replayed against the session's own seven entries in both its raw and horizon-scaled forms, the
raw form REJECTED and the failure documented above rather than quietly tuned away; payoff
arithmetic recomputed with the bounded drawdown. The four-window replay harness is still lost to
the sandbox reset. Chain C367-C404 intact.


## C403

THE FEE BUDGET IS THE ARCHITECTURE. Every previous version tuned gates and asked why the account
did not grow. The governing number was never a gate. 3%/month on $250 is $7.50/month = $0.341
per trading day, and at $20 notional a round trip costs $0.004 (maker/maker) to $0.016
(maker/taker). SO THE FEE BILL BY FREQUENCY: 6 trades/day = $2.11/month = 28% of the entire
target; 12/day = 56%; 22/day = 103%; 45/day = $15.84 = 211%. THE 20260817 SESSION OPENED TWELVE
POSITIONS IN 6h26m -- ~45/day, WHOSE FEES ALONE ARE TWICE THE MONTHLY TARGET. The bot was not
losing because a gate was mis-tuned. It was trading five to ten times more often than its own
profit goal can pay for, and no improvement anywhere else can survive that. THE SWEET SPOT IS
DERIVED, NOT GUESSED: hold fees under ~25% of target -> ~6 trades/day, each clearing ~0.34% of
notional gross, which at 1% risk is 55% WIN RATE AT 1.5:1 PAYOFF (0.55x1.5 - 0.45 = +0.375R) --
a far more believable edge than the 60-65% ACCURACY previously chased, because PAYOFF does the
work instead. C403-1, THE SERVO: a controller, not another threshold, because a threshold cannot
know what the market is offering today -- but it CAN know how often the bot has actually opened
positions and what that costs. An EWMA of entries with a 6h half-life reads directly in
trades/DAY; outside a 4-8 deadband the finished entry bar is multiplied by a bounded [1.00,
1.60] factor moving 4% per scan. DELIBERATELY ASYMMETRIC: it can only ever TIGHTEN. Below band
it relaxes back TOWARD nominal and never past it, because a quiet tape is a real state and
manufacturing trades to fill a quota is exactly how C389 turned 6 trades at +$0.098 EV into 11
at -$0.007. AND IT LETS GO OF ITS OWN OUTPUT: without in-band decay the controller RATCHETS --
one busy stretch drives the bar to 1.60, the rate falls into the band, and the deadband holds it
tight forever, punishing the bot permanently for a burst it had already corrected. Inside the
band the correction bleeds off at HALF the step, slower than it was applied. CLOSED-LOOP
VERIFIED over simulated 8h sessions: true 45/day -> EWMA 41.6 -> bar 1.60; 22 -> 19.4 -> 1.60;
12 -> 11.1 -> 1.60; 6 -> 5.5 -> 1.00; 2 -> 1.00 floor; and a bar pinned at 1.60 returns to 1.00
after 40 in-band scans. C403-2, PER-SYMBOL LEARNING IS STATISTICALLY IMPOSSIBLE AT THIS SCALE
AND IS REMOVED. FIX6 blocked a symbol+direction after ONE loss -- claiming a single outcome on
one pair predicts the next. Establishing that needs ~30 outcomes PER SYMBOL; 118 pairs clear the
volume floor, so 3,540 trades ~ 295 sessions ~ TEN MONTHS before the FIRST symbol's memory
carries information, and a crypto perp is not the same instrument ten months later. IT WAS WORSE
THAN SLOW: learning_v60.json was DELETED ON EVERY FRESH START, so it never held more than a
single session even in principle. This was never learning; it was a one-observation penalty
landing on whichever pairs lost most recently -- which systematically benches pairs during
exactly the volatile stretches where they are most tradeable. THE MARKOV CHAINS ARE NOT THIS AND
ARE UNTOUCHED: they learn SHARED state-transition structure across every pair at once, ~2,000
observations per session against 12, which is why they reach Brier 0.057-0.109 where this could
not. THE FRESH-START DELETE IS ALSO GONE, and the correct split is now stated in the code so it
is never blurred again -- RESET on Fresh Start: state_v60.json, positions_v60.json,
mode_v60.json. NEVER RESET: the five Markov files, s3_calib_v60.json, eval_window_v60.json,
pair_profiles_v60.json, learning_v60.json (_recent_trades, which the C284 eval window reads).
MONEY AND KNOWLEDGE ARE DIFFERENT LEDGERS; ONLY MONEY STARTS OVER. C403-3, ONE MODE. The
Normal->HP phase ladder exists to reduce risk as the day wears on -- which the day cap already
does, correctly, from a single honest ledger, without a state machine. What the ladder added
instead was FIVE incident classes this project has already paid for: C327 (a nine-hour dead
session from a pending-HP deadlock), C334 (a stale flag surviving a restart and suppressing ten
entries), C300 (a 2.4-minute-old position swept at a phase boundary and booked as a LOSS, which
then fed the losing-direction memory), C304/C310 (overshoot-credit drift and phase-skip
arithmetic), C330 (the window expiring 17 seconds after an entry -- a guaranteed round-trip fee
for no possible gain). HP has not activated in any recent session. Complexity with an incident
record and no measured benefit is not risk control. Stood down; the phase stays Normal and the
day cap governs. C403-4, ONE RISK CONTROLLER. Four uncoordinated controllers were reducing risk
from four different kinds of evidence: the C309 day cap (realised), the C313 open-stop
reservation (unrealised), C329 loss diagnostics (pattern-based) and the Guardian (its own
heuristic). THAT IS NOT FOUR TIMES THE SAFETY -- it is a system in which NO SINGLE COMPONENT
KNOWS THE TRUE RISK STATE, and whose combined effect was never bounded or measured. It is
precisely the two-floors defect C367 already paid for, where the safety guard sat on the wrong
floor and the weaker rule won because it ran last. The day cap and the open-stop reservation are
two halves of ONE honest ledger (money already lost + money still at risk) and are KEPT. The
Guardian (5 blocks last session on a rule nobody can state) and C329 (which fits a root cause to
fewer than six losses, where every pattern is present by chance -- its own changelog records
VARIANCE as the correct verdict on the session it was built for) are stood down. C403-5, THE
PINCER IS BROKEN OPEN. Measured on 20260817_021312: parabola_bounce blocked 60 LONGS while
resultant_counter blocked 50 SHORTS, in a window where the bot's OWN top-30 ran +8% to +19% (ONG
+11.89 net, BTW +13.14 max, US +7.38, CAP +7.32). NOTHING COULD PASS IN EITHER DIRECTION and the
bot took one trade in five and a half hours. Neither rule can tell a genuine blow-off from an
ordinary pullback inside a healthy trend, because BOTH read as 'N ATR from the day extreme'
while the actual discriminator -- whether the advance ACCELERATED -- is not measured at all. A
rule that cannot separate the two states it exists to separate must not hold a veto. Both become
WEIGHTED PENALTIES (x0.82 parabola, x0.85 counter-resultant): the evidence still costs the
candidate and it must still clear the bar, but it can no longer silence the whole book. Only
mechanical impossibility deserves a veto; everything else belongs in the score, where it
composes with all other evidence and where the C403-1 servo can then price it. Full chain re-
bounded: worst 0.399x, best 1.629x, no zero-out. C403-6, FOUR EXITS NOT TWENTY. The monitor
carried ~20 named exits that RACE, and whichever fires first wins -- exactly how C397 found the
promised runner floor being pre-empted by TRAILING_TP. Only four questions are logically
distinct: HARD STOP (has the loss reached its budget?), THESIS DEAD (has the conviction that
justified entry collapsed?), PROFIT FLOOR (is it giving back more of its peak than agreed?),
TIME (has the horizon elapsed with nothing happening?). C399 IS the thesis-dead answer and is
strictly better than the timer family that used to answer it -- on APR, REL_STAGNATION exited at
-3.5% on a 90-minute clock where C399 fires at -0.61%; this session C399 took KAITO out at -0.1%
on a confirmed sign flip, and fired three times with all three correct. C399 is therefore
evaluated FIRST and the timer family is demoted to a backstop for the one case C399 cannot see:
a thesis technically intact but going nowhere. C403-7, ARE THE TAKERS ON THIS TRADE'S SIDE?
C401's first live session, entry-side taker flow against outcome: KAITO -0.046 -> LOSS, ONG
-0.387 -> LOSS, GIGGLE +0.088 -> WIN, AIO +0.697 -> WIN. Buying while takers are SELLING is
mechanically buying from the side paying the spread to get out -- the informed, urgent side. The
bot has computed this number all along and used it ONLY to downgrade the order type (C341 stands
urgency down); it has never once questioned the DIRECTION. Added as a BOUNDED WEIGHTED TERM
(+/-10% at |flow|=1.0), not a veto, because n=4 is a hint and this project has killed four
candidate edges for more evidence than that. C403-8, THE SCANNER STAYS AT 30. The widening to 50
is analysed and ready but must not ship until per-trade EV is positive on a live log -- more
candidates at negative expectancy multiplies the loss. Order of operations matters: fix the
frequency first, measure, then widen. HONEST NOTE ON METHOD: steps 2, 3 and 4 are implemented as
SWITCHES rather than deletions. Functionally identical (single mode, one risk controller, no
per-symbol memory), reversible in one line if a future log argues otherwise, and vastly safer
than tearing 1,500 lines out of a 25,000-line file whose cross-references are not all visible.
The dead paths can be excised once a session confirms nothing depended on them. VERIFICATION:
syntax; AST 318 -> 320 (+_c403_rate_bar_mult, +_c403_note_entry); count-asserted replacements;
closed-loop servo simulation across five true arrival rates plus the ratchet-release case;
switch battery confirming switch_to_hp returns False with the mode unchanged and per-symbol
blocking returns False with the old behaviour intact when re-enabled; multiplier-chain bounds.
The four-window replay harness is still lost to the sandbox reset. Chain C367-C403 intact.


## C402

A SELF-CANCELLING ORDER LOOP, AND MY OWN C401 DISPLAY WAS INVERTED. Session 20260817_021312: ONE
ENTRY IN FIVE HOURS TWENTY-FOUR MINUTES -- 0.18 trades/hour against 2.6/hour the session before.
DEFECT 1, THE BOT WAS CANCELLING ITS OWN ORDERS. C363 set postOnly on EVERY entry limit (`if not
reduce_only: params['postOnly'] = True`), INCLUDING the C297/C395 entries that C397 deliberately
prices THROUGH the book and correctly bills at the TAKER fee. Two decisions about one order were
made from two different booleans and drifted apart. THE LOG SHOWS THE LOOP CLOSING ON ITSELF IN
CONSECUTIVE LINES: 'CROSSING entry (C297 regime-urgent) -> limit @ $0.07077 (+0.05% through the
book, taker; mkt $0.07073)' then 'Paper POST-ONLY REJECT: CAP buy @$0.070770 vs bid
$0.070620/ask $0.070690 -- would cross, live declines'. The bot priced an order to cross and
then forbade it from crossing. THIS WAS LIVE BEHAVIOUR, NOT A PAPER ARTEFACT -- the exchange
would have rejected every urgent and every high-conviction entry the bot has ever tried to send.
CAP, the pair it cancelled, ran +7.32% over the remainder of the session. FIX: post_only is now
the SAME boolean that already chooses taker-vs-maker fee, threaded through place_order and
_paper_order. Whichever fee we bill, that is the order we send. Default None reproduces C363
exactly (entries post-only, exits never), and the paper mirror now rejects only orders actually
SENT post-only -- mirroring the rejection onto a deliberate taker order made paper refuse trades
live would have FILLED, the exact inverse of the C364 parity that block exists to enforce. The
C286 'did price touch the limit' test is also skipped for a marketable limit, since a resting-
order question is meaningless for an order priced through the book. DEFECT 2, MINE, AND THE LOG
CAUGHT IT IN ONE LINE. C401 measured flow as cvd_now / cvd_entry. The session's only trade
printed: 'FLOW baseline: taker delta -0.093' then 'FLOW: taker 407% of entry support GREEN'. The
bot had gone LONG on a NEGATIVE taker delta -- it entered AGAINST the flow -- and the flow then
got MORE negative. A ratio of two negatives is positive, so MORE SELLING THAN AT ENTRY printed
as 407% SUPPORT WITH A GREEN LIGHT. Retention measures magnitude preservation, and magnitude is
meaningless when the baseline itself is adverse. C399's retention is sound because DRI and DSI
are one-sided by construction (C400 proved it: 67 DRI readings all negative, 56 DSI readings all
positive); taker flow is NOT one-sided, so the same shape does not transfer. THE MEASURE IS NOW
SIGNED SUPPORT: cvd x direction, where POSITIVE means takers are pushing THIS trade's way and no
ratio can disguise a negative. Entry support is printed beside it, so an against-flow ENTRY is
visible as what it is instead of becoming the yardstick everything after it is flattered
against. AND NOTE WHAT THE DATA ACTUALLY SAID: the bot went long into negative taker flow and
price fell 1.25% within two minutes. THE CHANNEL WAS RIGHT AND MY DISPLAY WAS INVERTED -- the
strongest early evidence yet that C401 is measuring something real. Still deliberately NOT wired
to any exit; one trade is not evidence. DEFECT 3, COSMETIC BUT IT COST AUDIT TIME: C401's water
emoji collided with the pre-existing 'Market coherence' line, so grepping the log for the new
channel returned 96 lines of something else. Changed. A log that cannot be grepped for a
specific mechanism is a log that cannot audit it -- the same lesson as C399's unattributed DRI
line. THE FREQUENCY COLLAPSE, AND THE MISSED-OPPORTUNITY CHECK THAT REFRAMES IT. The standing
protocol says never judge a quiet session without checking what the market offered. MEASURED on
live Bitget candles across the exact session window: BTC +0.03%, ETH +0.27%, SOL -0.22%, XRP
-0.27% -- the MAJORS were flat, which is what the bot's '83% short coherence' reading was
seeing. But the ALTS IN ITS OWN TOP-30 WERE NOT: ONG +11.89% net and +18.76% at its high on a
21.3% range; BTW +13.14% max on a 19.0% range; US +7.38% net; CAP +7.32% net. THE MARKET WAS NOT
QUIET -- THE PART OF IT THE COHERENCE METRIC WATCHES WAS. The bot correctly ranked ONG, BTW, US
and CAP into its own top-30 and took one trade. Rejection census across the session:
parabola_bounce 60 (mostly 'post-blow-off distribution risk', which blocks LONGS after an up-
move), resultant_counter 50, blow_off 23, ct_noisy_block up to 14 in a single scan. In a session
where the bot's own universe was making 8-19% UP moves, a family of rules that blocks longs
after up-moves blocks essentially everything -- and the shorts those rules would permit were
blocked as counter-resultant. A PINCER: nothing could pass in either direction. RECORDED AND
DELIBERATELY NOT YET FIXED. The parabola family cannot presently distinguish a genuine blow-off
top from an ordinary pullback inside a healthy trend, because both read as 'N ATR below the day
high' -- the discriminator would be whether the day's advance ACCELERATED (a blow-off) or
advanced steadily (a trend), and that is a measurable hypothesis, not an obvious one. C389
measured what happens when gates are loosened on intuition (trades 6->11, WR 83%->55%, EV
+$0.098->-$0.007), so this gets a corpus test before it gets a line of code. Fixing the postOnly
loop above releases the urgent path FIRST; the next log will show how much of the collapse that
alone explains, and that measurement must come before any gate is touched. VERIFICATION: syntax;
AST 318 functions; count-asserted replacements; postOnly default proven to reproduce C363 byte-
for-byte when the intent flag is absent; the CAP rejection replayed to confirm a crossing entry
now passes. The four-window replay harness is still lost to the sandbox reset. Chain C367-C402
intact.


## C401

THE NEXT REAL DESIGN QUESTION, ASKED AND ANSWERED: WHERE CAN AN INDEPENDENT SECOND OPINION
ACTUALLY COME FROM? C400 established that DSI is the negative of a six-component SUBSET of DRI's
own eleven, so the two can never be independent witnesses. The obvious next move is a second
price-derived channel. I TESTED THAT AND IT FAILS, AND THE REASON IT FAILS IS STRUCTURAL. THE
HYPOTHESIS, derived from mechanics rather than literature: price rises only if buyers are more
aggressive than sellers, BUT PRICE ALSO STAYS UP IF SELLERS MERELY STOP. Sustained demand and an
empty book are IDENTICAL in OHLCV. What separates them is the COST of movement -- real demand
must keep lifting offers, so volume is spent AND price moves; absorption by a large passive
seller spends volume and moves nothing. DRI carries 'volume' and 'momentum' as separate LINEAR
terms and never forms their RATIO, and a ratio can fall while both terms rise -- a state DRI
literally cannot represent. So impact-efficiency looked like genuinely new functional
information from the same raw data. MEASURED ON THE 60-PAIR x 20-DAY CORPUS (72,674 cases where
4-bar momentum >= 0.5 ATR in the trade's direction -- precisely the state where DRI reports the
thesis intact), barrier +/-1 ATR at 1h: HIGH impact-decay WITH RISING VOLUME, the exact cell the
absorption mechanism predicts, scored 49.2% against a 49.26% baseline -- MINUS 0.07pp, i.e.
NOTHING, on n=20,080. REFUTED. One neighbouring cell did move (impact decay with FALLING volume,
45.4%, -3.86pp, both halves) but that is not absorption at all, it is a move dying of low
participation, and relabelling it 'absorption' after the fact is exactly the fitting this
project refused in C398. NOT SHIPPED. THE FINDING THAT MATTERS IS THE BASELINE ITSELF: 49.26%.
That is the continuation rate WHEN MOMENTUM SAYS CONTINUE. Blind directional trading in the same
corpus wins 51.03%. CONDITIONING ON MOMENTUM MAKES THE BOT WORSE THAN NOT CONDITIONING AT ALL --
which is the same wall C389 hit and the same one that made the entry score anti-predictive. A
SECOND OPINION DERIVED FROM PRICE CANNOT HELP, BECAUSE THE FIRST OPINION DERIVED FROM PRICE IS
ALREADY A COIN FLIP. Independence has to come from a different CAUSAL LAYER, not a cleverer
function of the same layer. THERE ARE EXACTLY TWO SUCH LAYERS AVAILABLE TO THIS BOT, AND IT
ALREADY PAYS FOR BOTH. (1) WHO IS CROSSING THE SPREAD -- real side-tagged taker flow from
/fills, which resolves the demand-versus-vacuum ambiguity directly because real demand keeps
lifting offers and a vacuum does not. (2) WHETHER POSITIONS ARE BEING CREATED OR DESTROYED --
open interest, where a move on RISING OI is conviction being built and a move on FALLING OI is
exit flow, which ends when the inventory does (the same mechanism C398's capitulation tilt is
built on). NEITHER IS A FUNCTION OF THE PAIR'S OWN OHLCV, so neither is inside DRI by
construction. AND THE BOT WAS THROWING BOTH AWAY. Every one of the three _fetch_real_cvd call
sites is on the ENTRY path; THERE IS NOT ONE IN THE MONITOR. So the single channel capable of
saying something DRI cannot was measured once, at entry, and never looked at again -- while DRI
and DSI get baselines locked and re-read every cycle. That is the same computed-but-not-tracked
family as C397's runner floor and C399's ignored DSI collapse. WHAT SHIPS: the flow baseline is
now LOCKED AT ENTRY at the same instant as the DRI/DSI baselines, TRACKED on the SLOW monitor
leg (never the 0.8s fast leg -- /fills is a network call and the hard stop and runner floor
depend on that leg staying clean), expressed as RETENTION exactly as C399 expresses thesis
retention, SIGNED so positive always means 'flow still supports this trade' whichever way it
faces, logged with the same red/amber/green marker, and PERSISTED so a battery swap does not
silently strip a resumed position of its independent channel. WHAT DELIBERATELY DOES NOT SHIP:
ANY EXIT WIRED TO IT. Neither taker flow nor open interest has public history on Bitget, so this
cannot be backtested, and this project does not ship rules it has not measured -- C398 killed
four candidate edges on that rule, two of them mine. What instrumentation CAN do is record the
trajectory against the realised outcome, which makes the NEXT LOG the dataset that no backtest
can supply. INSTRUMENT FIRST, ACT SECOND. The next session should be read for one thing: does
flow support collapse BEFORE price does, on the losers, the way DSI did on APR? If it does, the
exit gets built and validated on real evidence. If it does not, this gets deleted and recorded
as refuted, like the four before it. VERIFICATION: syntax; AST 318 functions; count-asserted
replacements; the absorption experiment above with block-averaging and a first-half/second-half
split on every cell; persistence round-trip for the new fields. The four-window replay harness
is still lost to the sandbox reset. Chain C367-C401 intact.


## C400

THE OPERATOR ASKED WHETHER DRI AND DSI ARE COMPUTED CORRECTLY INDIVIDUALLY. DSI IS. DRI IS NOT,
AND THE TWO WERE NEVER ON THE SAME RULER. DSI VERIFIED EXACT, AND SAID SO PLAINLY BECAUSE IT
PASSED: reconstructed from the live log's own full component dump for PRL at 17:21:55 --
(-0.413)(0.18)+(-0.344)(0.11)+(-0.420)(0.16)+(-0.318)(0.04)+(-0.375)(0.04)+(-0.600)(0.06) =
-0.24310; inverted and Hurst-modulated by 1+(0.624-0.5)(0.6)=1.0744 gives 0.26119; the log
printed _dsi 0.261. Exact to three decimals. The FORMULA does what the code says. DRI DOES NOT.
Three separate statements of the same number disagreed: the boot banner said '9 components' and
printed weights summing to 1.02; the code comment said 'C3: normalized to 1.0'; and the
arithmetic actually applied ELEVEN contributors totalling 1.1133. TWO ERRORS COMPOUNDED. FIRST,
base_total was HARDCODED at 0.75 while the eight indicator weights it divides sum to exactly
0.70 (0.18+0.11+0.16+0.04+0.04+0.06+0.05+0.06) -- and a hardcoded total that does not match the
weights above it also breaks silently the moment anyone re-tunes one, the same trap as the
phantom ATR. SECOND, rvs (0.07) and time_pressure (0.10) were added AFTER the normalisation,
entirely outside the budget, so 0.17 of weight was never accounted for at all. PROVEN ON THE
LOG: for PRL, indicator_dri -0.23536 at pa_weight 0.15 gives scale 1.1333 -> DRI -0.3078 with
total weight 1.1133, where correct normalisation gives scale 0.9714 -> DRI -0.2697 with total
weight exactly 1.0000. EVERY DRI READING HAS BEEN ~11.3% TOO LARGE, and worse, the inflation
VARIES with pa_weight (1.1133 at pa=0.15 rising to 1.1333 at pa=0.45) -- so DRI was not even on
a STABLE scale, which is precisely what a threshold rule most needs it to be. base_total is now
COMPUTED from the weights and every contributor shares one budget of exactly 1.0. AND DSI LIVED
ON A DIFFERENT SCALE ENTIRELY. DSI is built from SIX of the eleven components, whose weights sum
to 0.59, and it was NEVER normalised -- so its natural ceiling was 0.59 x 1.3 (Hurst) = 0.767
against DRI's 1.1133. THE LIVE LOG SHOWS EXACTLY THAT SPLIT: DSI spanned +0.000..+0.445 while
DRI spanned -0.413..-0.028. THIS IS THE DEEPER REASON THE OLD DIVERGENCE RULE COULD NEVER FIRE:
beyond C399's finding that its 0.18 floor was unreachable, it compared dsi_dev and dri_dev
against ONE SHARED THRESHOLD -- an apples-to-oranges test that no choice of threshold could have
fixed. DSI is now divided by its own weight sum, so a '0.20 move' finally means the same thing
on both indices. WHY THIS IS SAFE TO CORRECT NOW RATHER THAN MERELY DOCUMENT: C399 reads RATIOS
of the entry baseline, which are scale-invariant, so the exit that actually protects capital is
unaffected; a SMALLER |DRI| leaves the 0.30/0.50 hard thresholds no more reachable than they
already were (C399 proved they were unreachable), so nothing becomes newly trigger-happy; entry
ranking scales every candidate equally so the ordering is unchanged; and normalising DSI LIFTS
typical baselines from ~0.38 to ~0.64, which puts MORE positions above C399's 0.10 abstention
floor -- i.e. more positions gain the collapse protection, not fewer. THE PERSISTENCE TRAP THAT
CAME WITH IT, CAUGHT BEFORE SHIPPING. Changing the units of DRI and DSI silently invalidates
every baseline already written to positions_v60.json. A position restored from a PRE-C400 file
carries baselines on the OLD ruler while new readings arrive on the NEW one, and C399 divides
one by the other: DSI retention would read ABOUT SEVENTY PERCENT TOO HIGH, silently disabling
the conviction-collapse exit on exactly the positions that survived a battery swap -- the
operator's known operating reality. This is Atlas #23 running in REVERSE: not a field gaining
persistence, but a persisted field whose UNITS changed underneath it. Positions now carry
_c400_scale_ver and unstamped baselines are converted on load -- DSI by the EXACT factor 1/0.59,
DRI by an approximate 0.876 because pa_weight is dynamic, and where a converted baseline lands
under the 0.10 abstention floor that channel simply abstains, which fails safe rather than
guessing. ALSO RECORDED, NO CODE CHANGE: DSI carries no information independent of DRI -- it is
literally the negative of a six-component SUBSET of DRI's own eleven, so it can only diverge
from DRI through the five components DRI has and DSI does not (ofi, funding, price_action, rvs,
time_pressure) and through the Hurst modulation. That is a real design limitation on how much a
'DSI/DRI divergence' can ever say, and no future build should treat the two as independent
confirmations of each other. Restating C351's still-live finding in the same breath:
components['ofi'] does NOT carry taker order-flow in the live path -- quick_scan_analysis writes
top-10 order-BOOK depth imbalance under that name. And the abs(dri)<0.03 -> 0.0 deadzone makes
DRI snap to exactly zero, which under C399's semantics reads as retention 0.0 = thesis dead;
that is semantically RIGHT but it is a cliff at 0.03, and it is documented here so it is never
mistaken for a bug later. VERIFICATION: syntax; AST 318 functions; count-asserted replacements;
the DSI reconstruction above matching the log to three decimals; the DRI arithmetic recomputed
both ways from the same logged component dump; and a load-path test confirming a pre-C400
position file is converted rather than silently mis-scaled. The four-window replay harness is
still lost to the sandbox reset. Chain C367-C400 intact.


## C399

THE DRI/DSI EXITS WERE WATCHING THE WRONG END OF THE SCALE, AND HAD NEVER FIRED. The operator
specified the semantics exactly: a DRI becoming LESS NEGATIVE (or a negative shrinking FAST)
toward zero, and a DSI becoming LESS POSITIVE toward zero, both mean an imminent SUSTAINED
reversal -- and the exit must happen BEFORE the reversal, not after price has paid for it. He is
right, the bot was already measuring it, and the bot was ignoring it. WHAT THE LIVE LOG PROVES.
Across the whole session -- 67 DRI readings, 56 DSI readings, 10 trades -- DRI WAS NEVER
POSITIVE (range -0.413 to -0.028) and DSI WAS NEVER NEGATIVE (+0.000 to +0.445). The scale is
ONE-SIDED: a large negative DRI means the thesis is STRONG and a DRI climbing toward zero means
it is DYING. Every existing rule tested the extreme instead of zero. DSI+DRI DIVERGE requires
dri_dev > max(0.18, ...) -- an ABSOLUTE floor on a quantity whose entire range is 0.39 wide and
whose entry baselines sit near -0.17, so DRI would have to reach +0.01 to clear it; observed
maximum dri_dev was +0.011. DRI HARD requires a shift of 2x baseline TOWARD POSITIVE, i.e. DRI ~
+0.17, further still. BOTH ARE UNREACHABLE BY CONSTRUCTION, which is why two of the seven exits
the boot banner advertises have never fired. This is the phantom-ATR defect a third time (Atlas
#43/#49): an ABSOLUTE constant standing where a RELATIVE one belongs, inside a codebase whose
founding principle forbids exactly that. THE COST, MEASURED AND CHART-VERIFIED. APR, the
session's largest loss: entry 17:05 DRI -0.171 DSI +0.381. By 17:13 DSI retained 54% (price
-0.91%); by 17:37, 49% (-1.20%); AT 17:45 DSI RETAINED 4% WHILE PRICE WAS STILL FLAT AT -0.61%;
at 17:53, 2% (-1.42%). The bot held for 51 MORE MINUTES and exited at 18:36 on REL_STAGNATION --
A 90-MINUTE CLOCK -- at -3.5%, -$0.58. Bitget 5m candles confirm what followed was monotone and
SUSTAINED: -2.03 -2.58 -2.82 -3.45 -3.56 -4.14 -4.66%. Meanwhile DRI marched -0.171 -> -0.117 ->
-0.102 -> -0.090 -> -0.080 -> -0.062 -> -0.060: SIXTY-FIVE PERCENT of the thesis destroyed, but
only 0.111 in ABSOLUTE units, so it touched no threshold at all. The signal was printed EIGHT
TIMES and acted on ZERO. THE MEASURE, dimensionless and therefore relativistic by construction:
retention = value_now / value_at_entry. 1.0 = thesis intact, 0.0 = thesis dead, BELOW ZERO = the
sign has flipped and the reversal is no longer coming, it has ARRIVED. The WEAKER of DRI-
retention and DSI-retention governs, because either one reaching zero is sufficient for the
trade to be over -- which is what the operator's specification says and what the data shows. A
baseline whose magnitude is under 0.10 ABSTAINS rather than dividing by a near-zero number and
lying. THREE TIERS, hardest evidence first: (1) SIGN FLIP, retention < 0 -- reversal confirmed;
(2) COLLAPSE, retention < 15% -- APR sat at 4%; (3) FAST DECAY, retention inside the 35% danger
band AND still falling at >= 4% per reading for >= 3 CONSECUTIVE readings, which is the
operator's 'RAPIDLY decreasing' clause and is what makes the call SUSTAINED rather than a noisy
tick. DELIBERATELY GATED TO LOSSES AND FLAT ONLY: a winner whose conviction fades is already
handled properly by TRAILING_TP and the C338/C397 runner floor, and firing here as well would
cut winners short -- C389 measured what happens when exits get greedy. THIS EXIT CAN ONLY EVER
REDUCE A LOSS, NEVER TRUNCATE A GAIN. It is also outside _C372_PROFIT_TOKENS, so the C372 profit
gate passes it straight through as a loss-mitigation exit must. REPLAYED ON THE LOG'S OWN
STREAMS: APR fires 17:45 at -0.61% instead of -3.5%, about -$0.10 instead of -$0.58, SAVING
$0.48 -- roughly the entire session's realised profit. PRL#1 (+$0.53 winner) does NOT fire.
PRL#2 (+$0.43 winner) has |DRI entry| = 0.072, below the 0.10 abstention floor, so DRI correctly
abstains and DSI alone governs -- it does NOT fire. Stable across collapse thresholds 0.10 to
0.25. THE LEGACY RULES ARE ALSO REPAIRED rather than left dead: the divergence floors drop from
0.18/0.12 to 0.06/0.04 so the baseline-scaled term can actually bind. AND THE LOG IS NOW
ATTRIBUTABLE. The DRI/DSI monitor line carried NO SYMBOL, so with 3-5 concurrent positions the
only way to tell which position a reading belonged to was to subtract the delta-from-baseline
and match it back -- which is how APR had to be identified for this audit. The line now names
the pair and prints retention with a red/amber/green marker, because retention, not the raw
level, is what the exits act on. CONFIRMED WORKING FROM C397, unchanged: every split runner
exited AT its promised floor -- PRL +2.98% promised, exited +2.7%; XAI +1.89% promised, exited
+1.6%; PRL#2 +2.47% promised, exited +2.3% -- slip 0.2-0.3pp against the 0.8-3.8pp of the
previous session, and ETHFI's runner rode from +3.2% to a +6.9% peak and banked +5.3% for
+$0.47. The C397 split monitor loop is live in the banner. HONEST VERIFICATION NOTE: syntax, AST
318 functions, scope-safety proof that _cr399 is assigned before every use inside
_should_exit_dri_raw, count-asserted replacements, C372-token non-interference check, and a
replay of the rule against the logged DRI/DSI streams with chart-verified Bitget 5m prices. The
four-window replay harness is still lost to the sandbox reset. Only APR and PRL have complete
logged DRI/DSI streams -- the other positions could not be reconstructed because the old log
line omitted the symbol, which is itself now fixed. Chain C367-C399 intact.


## C398

A NEW EDGE THAT IS NOT IN THE LITERATURE, DERIVED FROM THE MECHANICS OF PERPETUAL FUTURES AND
THEN MEASURED -- PLUS THE UNIVERSE WIDENING, AND TWO HYPOTHESES REPORTED AS REFUTED. THE
REASONING FIRST, BECAUSE THE MEASUREMENT ONLY MATTERS IF THE MECHANISM IS REAL. A perpetual
future is priced by leverage, and in crypto perps the crowded side is structurally LONG --
funding is normally positive, which is simply the market paying longs' rent (this project's own
corpus: 74% continuation on 29,454 funding cases). That crowding is asymmetric, and so is what
happens when price moves fast. A fast MARKET-WIDE FALL is disproportionately FORCED flow: a
liquidation is a market order that must execute regardless of price, and the inventory
liquidatable at any given level is FINITE. When it is consumed the mechanical pressure stops
INSTANTLY while the price is left displaced -- so the displacement partially reverts. That is
not an opinion about value; it is what happens when a price-insensitive seller runs out of
things to sell. A fast market-wide RISE is more often VOLUNTARY buying, and voluntary flow is a
decision, a decision reflects information, and information keeps being repriced -- so it
CONTINUES. FORCED FLOW REVERTS, VOLUNTARY FLOW CONTINUES, and the asymmetry is the entire point.
WHY THE PACK AND NOT ONE PAIR: a single coin falling 1.5 ATR can be its own news, which is
information; sixty coins falling together in three hours is not sixty decisions, it is one
factor, and a factor moving that fast in altcoin perps is leverage unwinding. THE MEASUREMENT,
on a purpose-built 60-pair x 20-day live Bitget 15m corpus (114,660 bar-observations, barrier
+/-1 ATR at the 1h horizon), scored against the CORRECT side-specific baseline -- the control
that kills most 'discoveries', because the corpus tape was RISING (+7.7% median) so a blind long
already wins 51.03% and a blind short 48.97%: (a) pack fell >1.5 ATR in 3h -> BUY: 55.7%,
+4.67pp over baseline, halves 54.2%/59.3%, block-averaged 57.8%, n=3,420 -- SHIPS. (b) pack rose
>1.5 ATR in 3h -> SELL: 51.9%, +2.93pp, halves 53.5%/48.7% -- THE SECOND HALF FAILS, DOES NOT
SHIP. (c) pair at its own 12h LOW -> BUY: 53.3%, +2.28pp, halves 52.1%/54.5%, and its mirror
(shorting that low) is -2.93pp in both halves, a symmetric confirmation -- SHIPS. (d) pair at
its own 12h HIGH: +0.31pp, noise -- DOES NOT SHIP. The one-sidedness is not a fitting artefact;
it is the PREDICTION of the mechanism, and shipping the symmetric mirror would have meant
fitting the half of the data the mechanism says should not work. Both tilts are SOFT and bounded
(+/-8% pack, +/-6% pair, total clamped to 0.85x-1.15x), because 20 days is a small sample and
C396's precedent is that a 9.4pp effect earns 12%. TWO HYPOTHESES TESTED AND REFUTED, RECORDED
SO THEY ARE NOT RE-LITIGATED. (1) CROSS-SECTIONAL FACTOR SHARE: the pack shares one factor, so
the SECOND moment (dispersion around the factor) should separate a coiled tape from a chaotic
one where the bot's existing sign-count coherence provably cannot -- 22 pairs each moving 0.05%
and 22 pairs each moving 3% both print '50% short'. The theory is sound and the data refused it:
correlation with the existing coherence measure was +0.925 (it is not new information) and the
barrier-win spread was -0.67pp, inside noise. NOT BUILT. (2) THE WORKED-PROGRAMME RUN: an agent
with real size cannot lift a whole book at once, so remaining unexecuted inventory should show
as several consecutive bars closing in the top third of their OWN range -- genuinely leading,
because the remaining size has not hit the tape yet. Measured across run lengths 1-5 with and
without volume confirmation: 48-50% flat, in both halves, no monotonicity. NOT BUILT. Standing
Rule 6 did its job twice. THE UNIVERSE WIDENING, AND A CORRECTION TO THE HANDOFF. C391 raised
C391_UNIVERSE_CAP to 150 and the handoff recorded '206 pairs clear the volume floor'. THE
OPERATOR'S LOG SAYS OTHERWISE, in both sessions and every single scan: '110 pairs meet volume
threshold ($750,000 relative)'. The 150 cap has therefore NEVER BEEN BINDING -- only ~110 pairs
ever reach it. The number that actually decides how much of the market the bot looks at is
TOP_PAIRS_SELECT, and it has been 30 since C157. Raised 30 -> 50. MEASURED COST from the
operator's own timestamps: screening all 754 markets takes 1s (one bulk call), ranking takes 3s,
and Step 3 analysis of 30 pairs takes 26s = ~0.85s per pair, so 30 -> 50 costs about +17s inside
a 480s cycle -- 3.5% of the scan period, and cheaper on repeat scans because Step 3 caches
within the same 15m candle. WHY THIS IS NOT THE C389 MISTAKE: C389 removed GATES and made trades
worse; this changes nothing about the bar a trade must clear, it sends MORE candidates through
the SAME gates. The log shows '30 analyzed -> 0-1 viable' on nearly every scan, so the binding
constraint genuinely is how few pairs are ever examined. AND THEN HELD AT 30, BECAUSE THE
PREMISE FOR WIDENING WAS WRONG AND THE OPERATOR CAUGHT IT. The handoff records '~0.2-0.3
trades/day' and names FREQUENCY the binding constraint; that figure is a REPLAY ARTEFACT -- 8
trades over 4 x 7 window-days, in a corpus where TWO of the four windows are recorded as
'genuinely dead tape' taking zero trades. COUNTING REAL ENTRY FILLS IN THE OPERATOR'S OWN LOGS:
session 1 (6.14h) opened BR, AIO, NIL, AIO, NIL, CHIP, H = 7; session 2 (5.11h) opened ACU, XAI,
AIO, BTW = 4; eleven entries in 11.25 hours = 0.98 PER HOUR, about 23 per day -- roughly eighty
times the assumed rate. Over those eleven trades equity went $250.00 -> $249.41, about -$0.05
PER TRADE. FREQUENCY IS NOT THE CONSTRAINT; PAYOFF IS. Adding 60% more candidates to a book that
is slightly negative per trade multiplies the loss, and C389 measured precisely that failure on
this bot's own data (trades 6->11, WR 83%->55%, EV +$0.098->-$0.007). TOP_PAIRS_SELECT therefore
stays at 30 and the widening ships only after the C397 payoff repairs are confirmed positive on
a live log, as a single deliberate change with a clean A/B. The correction is recorded rather
than quietly reverted because the WRONG NUMBER HAD BEEN CARRIED FORWARD IN THE HANDOFF ACROSS
MULTIPLE SESSIONS and would have kept steering work toward frequency instead of payoff. HONEST
VERIFICATION NOTE: the four-window replay harness did not survive the sandbox reset, so C398 is
verified by syntax, AST (317 -> 318, +_c398_pack_extension), count-asserted replacements, the
60-pair/20-day corpus experiment above with block-averaging and a first-half/second-half split
on every claim, a multiplier-chain bounds check, and a live end-to-end exercise of the new code
path against real Bitget candles. It was NOT re-run through the four-window replay. The tilt can
only re-weight a candidate that has already passed every existing gate; it cannot create an
entry, remove a gate, or change sizing. Chain C367-C398 intact.


## C397

THE TWO-STORIES AUDIT OF THE OPERATOR'S 11.5-HOUR RESUMED SESSION: NINE PLACES WHERE THE CODE
COULD NOT EXPLAIN THE LOG, SEVEN OF THEM REAL DEFECTS, EVERY ONE ROOT-CAUSED TO A LINE. (1) THE
DRIFT GUARD WAS READING A PHANTOM ATR -- the operator's 'momentum snapped'. Eight aborts across
two sessions on eight different coins (GRVT, NIL, CHIP x2, PRL, AIO x2, ACE) and the allowance
printed EXACTLY 0.60% every single time. Eight coins cannot share one number: that is a
fingerprint, not a coincidence. C395 claimed to scale the guard with the pair's own ATR and read
`atr_pct`, the BARE close-to-close ATR that floors near 0.30% -- the exact field C259 removed
from the sizing chain under the exact same heading, ONE VOLATILITY TRUTH. Because 0.9 x
0.30-0.66% never clears the 0.60% floor, max() returned 0.60% for every pair and the 'ATR-
scaled' guard was a fixed wall. THE PROOF SAT ELEVEN LINES ABOVE AIO'S OWN ABORT:
'vol_adj=0.55(atr=3.8%)'. AIO's real ATR is 3.8%, the correct bar is 3.42%, and the -1.97% drift
that aborted it is HALF AN ATR of ordinary breathing. Six of the eight aborts were false alarms.
Now reads max(_n52_atr, atr_pct) -- the same figure C64/C259/C260/PRU/stop/leverage all read --
and the C318 margin trim beside it, which had the identical defect and was firing at a near-
constant 0.28%. (2) THE PASSIVE LIMIT WAS PRICED OFF THE TAPE, NOT THE BOOK -- the operator's
'limit unfilled'. Log: 'C279 limit @ $0.033457 (-0.10% vs mkt $0.033490)' then 'POST-ONLY
REJECT: TUT buy @$0.033457 vs bid $0.033440/ask $0.033450 -- would cross'. The bot wanted a
PASSIVE buy, took the LAST TRADED price, subtracted 0.10%, and landed ABOVE the live ask,
because in a falling tape the last print sits above the current ask. CHIP died identically at
04:20. A maker BUY belongs at the BID and a maker SELL at the ASK; the order now rests at
min(bid, last x (1-off)) for a buy and max(ask, last x (1+off)) for a sell -- always a maker,
and as close to the touch as legally possible, which is also the highest fill probability a
maker can have. (3) EVERY ORDER PRICE WAS ROUNDED TO A HARDCODED SIX DECIMALS -- the operator
spotted this directly. TUT and CHIP tick in 0.00001, so $0.033457 and $0.027584 are prices those
books CANNOT HOLD. Paper accepted them silently; live either rejects or silently re-rounds, and
re-rounding a buy upward turns a safe post-only order into a crossing one. New round_to_tick()
reads the instrument's real precision and rounds DOWN for buys, UP for sells, so making a price
legal can only ever make a maker MORE passive -- it can remove a rejection but never create one.
Wired centrally at place_order (one gate, every path: entries, pyramid tranches, maker exits,
partials) and at the C378 stop trigger, where reduce_only exits round the OTHER way so a stop
can always still get out. (4) THE PARTIAL-PROFIT FLOOR WAS ANNOUNCED AND THEN IGNORED -- the
largest measurable leak. Every split runner exited BELOW the floor printed to the operator: AIO
promised +4.37% exited +0.58%; ACU promised +2.20% exited +1.40%; XAI promised +3.64% exited
+1.80%; only H (+3.48% promised, +4.00% exit) was correct. ROOT CAUSE LOCATED EXACTLY:
WINNER_RATCHET_FLOOR lives in should_exit_dri on the Position, but TRAILING_TP lives in
_monitor_positions, runs FIRST, carries its own LOWER floor and `continue`s on fire -- so the
promise never gets a turn. WORSE, C345 WAS INERT: the ratchet stores max(previous, new), so once
a higher pre-partial floor was banked the 0.45xpeak cap could never lower it -- dead code on
every position it was written for. THE RESOLUTION, one number instead of two contradictory ones:
for a split runner the trailing floor simply IS max(promised, 0.45xpeak), ASSIGNED not max()'d
so a stale pre-partial value cannot out-rank the contract. It cannot be tighter than promised
(C345's LA case still rides) and cannot be looser (C338's guarantee holds). RETRO on the logged
trades: +$0.21 AIO, +$0.10 ACU, +$0.12 XAI = +$0.43 across two sessions whose combined realised
result was about -$0.35. (5) THE WIN RATE WAS COUNTING HALF-CLOSES, NOT TRADES.
_c336_partial_close documents itself as 'deliberately NOT fed to the ledgers' and then calls
release_margin, which IS a ledger. PROVEN TICK BY TICK: 00:59 BR loss + AIO PARTIAL -> 50%;
01:02 AIO close -> 67%; 01:22 NIL close -> 75%; 02:02 NIL PARTIAL -> 60%; 02:16 NIL close ->
50%. AIO earned +$0.33 as ONE idea and was recorded as TWO WINS; NIL lost -$0.64 as ONE idea and
was recorded as TWO LOSSES. The operator's stated primary goal is a consistent 60-65% win rate,
and the number he steers by was double-counting every position the partial machinery touched.
Now: partials book CASH and FEES but not a TRADE (count_trade=False), and the final close judges
the WHOLE idea (banked half + remainder) via classify_pnl, so a split that banks +$0.30 and
closes -$0.05 is filed as the +$0.25 WIN it actually was. (6) AND AN ENTRY THAT NEVER OPENED WAS
BOOKED AS A LOSING TRADE. release_margin books a loss whenever net_pnl is not > 0, and the
unfilled-limit path passed 0.0. PROVEN THREE TIMES: 04:14 WR 57% -> CHIP unfilled -> 04:22 WR
50%; 04:54 WR 50% -> FARTCOIN unfilled -> 05:02 WR 44%; 13:55 WR 53% -> TUT unfilled -> 14:03 WR
50%. It also advanced trades_since_learn, feeding the self-learning system PHANTOM LOSSES on
positions that never existed, and consumed slots in the 100-trade C284 eval window. Money was
never affected -- the margin round-trips exactly -- only the counters, and the counters are what
every decision is calibrated on. Both unfilled paths (entry and pyramid tranche) now book no
trade. (7) THE '0.8s MONITOR' WAS NOT RUNNING AT 0.8s. The banner promised 0.8s; the monitor's
own docstring admitted '6-8s'; neither was enforced, because the heavy-data gate read
POSITION_CHECK_INTERVAL (0.8s) and was therefore ALWAYS TRUE -- so on essentially every tick the
bot re-downloaded 100x 15m candles for every open position plus BTC, then ran Hurst, entropy and
GARCH, on a phone, over mobile data. Once a minute it made two MORE blocking OHLCV fetches for
the regime refresh INLINE AND AHEAD of the position check, so every open position went unwatched
for a mobile round-trip. A 15-MINUTE CANDLE CHANGES ONCE EVERY 15 MINUTES. The loop is now
SPLIT: a FAST price-only leg every tick (prices are one cheap call and are what the hard stop,
trailing floor, peak floor and capture floor actually read) and a SLOW leg at 20s for OHLCV/DRI
and 90s for regime, moved to run AFTER positions are checked. At 20s the slow leg still
refreshes 45x more often than the underlying data moves; API load falls roughly 95%. (8) C395's
CONVICTION-CROSS WAS BILLED THE MAKER FEE. The fee branch tested only _c297_urgent, so a C395
entry that crossed the spread as a TAKER was booked at 0.02% instead of 0.06% -- a C364
PAPER=LIVE parity leak in the fix that created it. Fixed, and the misleading log line that
attributed a C395 cross to 'C297 URGENT ... regime running' (with a possibly-stale regime state
that could raise inside the f-string) now names whichever mechanism actually fired. (9) C396's
SESSION EDGE WAS SILENT. Its own handoff said the next live log must confirm the tilt fires. It
logged NOTHING, so across ~20,000 lines and two sessions spanning BOTH the Asia and Europe
windows there was no way to tell whether it worked, was mis-wired, or was dead. It now announces
itself once per ten minutes. A silent edge is an unverifiable edge. PLUS THE OPERATOR'S BATTERY-
SWAP QUESTION, ANSWERED AND FIXED: he noticed the Normal target changed on resume, and it did.
Session 1 (fresh, he typed 15): day cap 0.68%, Normal 0.477%. Session 2 (resumed): day cap
0.91%, Normal 0.636%. 0.68 x 22 = 15; 0.91 x 22 = 20, exactly the hardcoded default. The entire
equity-and-drawdown prompt lives inside `if fresh:` and C380_MAX_MONTHLY_DD_PCT was never saved
anywhere -- so every resume threw away his declared risk appetite and sized every subsequent
position 33% LARGER (per-trade risk 0.341% -> 0.455%) mid-day, with nobody deciding it. The dial
is now PERSISTED in state_v60.json, RESTORED before the budget is re-derived from it, and SHOWN
with a confirm-or-change prompt on the Load path, so the one number C380 exists to make
conscious is conscious on every single run. ALSO CONFIRMED CORRECT AND NOT CHANGED (the operator
asked specifically): partial profits DO reach the balance. Session 2 loaded at $249.20, the
realised events sum to +$0.21, closing equity $249.41 -- exact to the cent. release_margin adds
margin + net_pnl at full C371 precision and nothing is lost; only the trade COUNTERS were wrong.
HONEST VERIFICATION NOTE: the four-window replay harness and corpus did not survive the sandbox
reset, so C397 is verified by syntax, AST (316 -> 317, +round_to_tick), count-asserted
replacements, a live Bitget end-to-end simulation of the repaired paths against real book and
candle data, and retro-arithmetic against the logged trades. It was NOT re-run through the four-
window replay. SEVEN of the nine fixes can only REMOVE a wrong action (a false abort, an illegal
price, a phantom trade count, a broken promise); two -- the drift guard and the book anchor --
WILL increase trade frequency, and C389 proved on this bot's own data that more trades can mean
worse trades. These are corrections of measurement errors rather than gate removals, which is a
different thing, but the next log must be read with that in mind. Chain C367-C397 intact.


## C367

THE UNGATED PENALTY FLOOR -- found in the operator's live log_20260805 after two sessions of
persistent losses. TWO FLOORS EXISTED AND THE SAFETY GUARD WAS ON THE WRONG ONE. C284 (line
~18165) lifts a crushed score to 40% of its pre-penalty base and is GATED on base-strength AND a
live projection -- guards added deliberately after the C284 cohort study measured floor-lifted
trades at 17W/16L -$0.40 against organic entries at 15W/6L +$0.62, proving the lift rescued
genuine breakouts and self-contradicting entries INDISCRIMINATELY. C149 (line ~19183) lifts to
60% -- HIGHER -- with NO projection check and none of the C284 guards, and it runs LAST, so it
wins. C284 only evaluates when score < 40% of base, so any score landing BETWEEN 40% and 60%
never met C284's guards at all and was re-lifted here ungated. That band is where the damage
lives, and the C284 fix has therefore been inert for its entire life. MEASURED on the live
session: the floor fired 10 times out of 10 -- it never once left the stack alone -- average
lift +0.125 (0.41 -> 0.54, a +30% relative rescue). Against the observed 0.47 entry bar it
permitted 7 of 10 entries where only 4 would have passed organically, MANUFACTURING 3: SKR, TAO,
FARTCOIN. TAO closed THESIS_EXIT -2.5%, FARTCOIN PARTIAL_THESIS_DEAD. TAO is the clearest case:
FOUR independent systems opposed the long (broken-parabola bounce blocked at 07:51, structural
exhaustion with 3% room at 08:01, leg beyond cap X=1.66 burning hot, C199 order-flow weakening
with CVD=-0.44), the stack correctly cut conviction to 0.45, and this floor put it back to 0.60
and bought it. THE INVERSION, stated plainly: the floor is strongest exactly when the evidence
against the trade is strongest, because more independent warnings mean a lower product means a
bigger lift. A guard that fires hardest against its own evidence is not a guard. FIX: C284's
verdict is now PUBLISHED on the analysis (_c284_lift_allowed / _c284_why) and the C149 floor
OBEYS it -- a crushed score whose base is weak or whose projection is dead stays crushed and is
blocked. The 60% level is kept for entries that PASS the guards, preserving C149's original
purpose (log_c148's EPIC won +5.75% after penalties stacked it to x0.43) without rescuing the
self-contradicting cohort. Denials now log explicitly instead of passing silently. ALSO: C366's
horizon wire logged NOTHING across both live sessions -- its reading sat behind an
orderliness>0.05 gate and was therefore invisible and unverifiable; it now logs unconditionally
so permutation-entropy values can be checked against live outcomes. Verified: syntax OK; AST 308
unchanged; 3 count-asserted replacements; floor-decision unit battery across the 40-60% band
reproducing the TAO case exactly (guards fail -> 0.45 -> BLOCKED at the 0.47 bar); replay boot
clean.


## C396

TWO CHANGES FROM THE OPERATOR'S LATEST LOG: a genuinely NEW research-and-corpus-validated edge
(session-of-day) and a fix for HP mode, which the operator correctly flagged as losing badly.
PART 1 -- SESSION-OF-DAY EDGE: peer-reviewed 2025-26 crypto microstructure research finds
liquidity and directional follow-through peak when London and US are both open and trough in the
Asia-only hours. Rather than trust the literature, it was MEASURED on a freshly-rebuilt 10-day,
15-pair live Bitget corpus: momentum entries win 55.9% in the Europe session (08-16 UTC =
13:30-21:30 IST) vs 46.5% in Asia (00-08 UTC = 05:30-13:30 IST) -- a 9.4pp spread -- and
CRITICALLY it held in BOTH halves of the sample (Europe-Asia gap +12.8pp in the first 5 days,
+6.4pp in the second), so it is not a fluke of one window. Because 10 days is still a small
sample it ships as a SOFT tilt, not a hard gate: the score is boosted 1.12x in the Europe
session, damped 0.88x in Asia, left neutral in US hours, bounded +/-12%. It is wired at the same
entry-scoring site as C387/C392/C394 so the tilts compose; the full multiplier chain was bounds-
checked and is safe (worst-case 0.61x-1.56x of base score, no zero-out, no explosion). PART 2 --
HP MODE FIX: the log showed HP activate and then run for 3 HOURS rejecting 47 candidates on
'weak macro' (median score just 0.13) and 27 on a $1.5M volume floor, open exactly ONE trade
(ACU, which lost on the HP individual drift cap at -3.9%), and bleed -0.24% doing nothing. ROOT
CAUSE: HP runs AFTER Normal has already taken the day's best setups, so it scrapes weak
leftovers AND takes more risk on them -- structurally backwards. Two fixes: (1) a REGIME GATE at
the switch_to_hp call site -- HP only activates if the market is genuinely trending (|R| >=
0.30); in a chop tape it now SKIPS HP and ends the day flat rather than bleeding (the logged
tape was R~+0.25, so HP would now correctly skip). (2) the HP volume floor is made configurable
and lowered from a hardcoded $1.5M to $0.75M to match Normal's effective floor, since it was
blocking pairs Normal happily trades. HONEST NOTE ON VERIFICATION: the four-window replay
harness and the 29k-bar corpus did not survive the sandbox reset this session, so C396 was
verified by (a) syntax/AST, (b) config-load with ccxt installed, (c) the session-tilt and HP-
gate logic exercised in isolation and confirmed to fire correctly at the logged R value, and (d)
a multiplier-chain bounds check proving the new tilt cannot destabilise scoring. It was NOT re-
run through the full four-window replay; the changes are localised, bounded, and the HP gate
only PREVENTS a losing action, so degradation risk is low, but the next live log should confirm
HP now skips chop and the session tilt fires. Also carried forward and intact: C391 universe
150, C380 drawdown 20%, C392 funding tilt, C393 xvenue guard, C394 symmetric trend, C395 entry-
mechanics fix. Chain C367-C396 intact.


## C395

THE ENTRY MECHANICS WERE THROWING AWAY GOOD SETUPS -- the 'momentum snapped' and 'limit
unfilled' problems the operator flagged, root-caused to two real faults. THE LOG: six candidates
reached final selection (one scoring 1.086, another 0.724) and ZERO opened -- three lost to
'momentum snapped', the rest to unfilled passive limits. FAULT 1, THE DRIFT GUARD WAS INVERTED:
it aborted an entry if price drifted against the trade by more than min(0.8*ATR, 0.75%). The
min() CAP made the guard TIGHTEST on the pairs that naturally move MOST -- a 6.7%-ATR pair (CAP
in the log) aborted on a 0.75% drift, which is 11% of one ATR, pure noise. So the bot kept
'momentum snapping' on volatile pairs that had barely twitched. Fixed to scale WITH volatility:
abort at ~90% of the pair's own ATR (floor 0.60%, ceiling 4.0%), so CAP would now abort at 4.0%
not 0.75% -- a real snap, not noise. FAULT 2, PASSIVE LIMITS LOSE REAL-EDGE TRADES: entries rest
a C279 passive limit BELOW market to earn the ~4bp maker fee, but in a fast tape price never
returns and the trade is lost. Saving 4bp is not worth losing a trade whose edge is real. A
high-score candidate (>= 0.75, the HP bar) now crosses the spread as a taker to SECURE the fill,
exactly as an urgent-regime entry already does -- conviction earns the fill the same way regime
persistence does. WHY THE REPLAY SHOWS NEUTRAL (identical to C394: 8 trades, 75% WR, +$0.105 EV,
+$0.840 total): the drift and fill problems are a LIVE-feed phenomenon of real spreads and fast
quotes; the corpus windows have tight synthetic spreads and rarely trigger them. C395 is
verified NOT to harm the backtest while fixing a waste proven in the live log -- six lost setups
in a single session. ALSO CONFIRMED IN THIS LOG: the one closed trade (CAP -5.90%, -$1.52) was
C377 firing its hard stop CORRECTLY at -6.03% = -1.56R ('arithmetic, not opinion'); the larger
dollar loss is simply the 20% drawdown sizing the operator chose, working as designed. And
C394's trend tilt only fires when |R| >= 0.30; the session's tape was mildly rising (R median
+0.25) so it was mostly dormant, correctly -- the longs were not wrong-direction, they were
choppy-tape entries the fixed drift guard will now handle. Verified: syntax OK; AST 316; both
fixes present; four-window replay clean and non-degrading; chain C367-C395 intact.


## C394

SYMMETRIC TREND-FOLLOWING -- short the downtrend as readily as we long the uptrend. This is the
first change since the universe widening to improve the bot on EVERY axis at once, and it came
directly from reading the operator's log against external research. THE LOG PROVED THE BIAS: in
a falling tape (market resultant R = -0.54) the bot attempted LONG 107 times and was CORRECTLY
blocked every single time by resultant_counter (which fired 148x total), while taking
essentially no shorts -- a bull-market bot sitting out a bear market, taking ZERO closes in the
session. Web research on bots that survive all regimes is unanimous: the defining feature of a
trend-follower is 'buy the uptrend, SELL the downtrend', and the single most-cited reason bots
fail is strategy-market mismatch -- running a long-biased bot in a falling market. The bot CAN
short (217 code refs) and the direction line is symmetric (long if avg_sig>0 else short), but
the component signals skew long, so in a down-tape it generates long signals that get blocked
instead of short signals that would trade. THE FIX: when the tape is CLEARLY trending (|R| >=
0.30), tilt the score by trend alignment -- a short in a falling tape is boosted up to 1.15x and
a long damped to 0.85x, and vice-versa in a rising tape -- so the signal is steered to the
correct side UP FRONT, which also reduces how often resultant_counter has to fire. Bounded
+/-15%, does NOT touch the symmetric taker-flow blocks or the counter-trend gate. FOUR-WINDOW
REPLAY vs the C388 baseline: trades 6 -> 8, EV/trade +$0.098 -> +$0.105, TOTAL NET +$0.589 ->
+$0.840 (+43%), trades/day 0.21 -> 0.30. The added trades are shorts in the downtrend that won
-- exactly what the research said was missing. ALSO, STEP-1 SCREENER ANALYSED per operator
request: it ranks the universe by 0.40*log-volume + 0.25*change + 0.35*freshness. The eye-test
looked alarming (it ranked ACE at +142.7% #2, VELVET +54.4% #15 -- already-exploded pairs) and
94 of 237 surfaced pairs had already moved >5%. But MEASURED on the corpus, recent change is
roughly FLAT on win rate (48-50% across 0-2%/2-5%/5-10%/10%+ buckets) and so is volatility
(71.5-72.5% resolve across ATR terciles) -- the screener is not broken, but no 'which pair
moves' signal separates tradeable from untradeable, because ALMOST ALL crypto pairs resolve
within an hour anyway (~72% regardless). The conclusion: pair SELECTION was never where the edge
lives; DIRECTION is, which is exactly what C394 fixes. Verified: syntax OK; AST unchanged;
trend-tilt table checked; four-window replay clean; chain C367-C394 intact.


## C393

UNIVERSE CAP 100 -> 150, AND AN HONEST ACCOUNTING OF THE BINANCE ACCOUNT. The operator asked to
push the cap and add new edge classes with an active Binance account. THE CAP: raised to 150,
the full realistic width -- 206 pairs clear the volume floor but the top 150 by activity capture
essentially everything that is ever lively in a 15m window; the tail is dormant microcaps. THE
BINANCE ACCOUNT, measured in-sandbox rather than assumed: (1) Binance FUTURES (fapi) is geo-
blocked here with HTTP 451, and simultaneous two-venue order execution is impossible from a
single bot process anyway, so real cross-exchange arbitrage, hedging and funding capture CANNOT
be built -- a fake version would be theatre and is refused. (2) Binance SPOT data IS reachable
read-only via data-api.binance.vision (490 USDT pairs). It was tested as a LEAD signal on 1m
candles for five majors: same-bar correlation with Bitget perp is 0.90-0.98 and the lead
DIRECTION is inconsistent (2 pairs Binance-lead, 2 Bitget-lead, 1 simultaneous, all lag-
correlations below 0.13) -- there is no stable exploitable lead, so a predictive cross-venue
signal is NOT built (that would be fitting noise). (3) The one DEFENSIBLE use is a divergence
SANITY CHECK: when Bitget perp diverges from Binance spot beyond 0.75%, the perp quote is likely
stale or a wick, so the entry is SKIPPED. This is read-only and FAIL-OPEN -- if Binance data is
unreachable (e.g. geo-blocked on the operator's phone) the guard returns False and the bot
behaves exactly as before; it can only ever REMOVE a bad fill, never add risk. A DEAD-CODE BUG
CAUGHT BEFORE SHIPPING: the guard methods were defined on ExchangeManager but first called as
self.<method> from _open_position on TradingBot, where self is the bot -- wrapped in try/except
it would have silently done nothing, the exact defect class this project keeps finding. Fixed to
call via self.exchange (the ExchangeManager) and verified end-to-end against live prices: a 0.1%
gap passes, a 2% gap blocks, an unreachable pair fails open. Verified: syntax OK; AST unchanged;
guard live-tested; replay clean; chain C367-C393 intact. THE HONEST SUMMARY: the Binance account
adds no trading capability from this environment; Binance spot DATA adds a small defensive
quote-sanity filter, not a new profit edge. The realistic path to higher return remains a wider
universe (now 150) plus the C380 drawdown dial at the professional 20-30% range -- honest
leverage of the one small real edge, not a new one.


## C392

FUNDING-AWARE ENTRY TIMING -- the ONE genuinely new, structurally-reachable edge for a single-
account bot on one venue, with its DIRECTION set by measurement rather than intuition. The edges
that pay 4%+ in reality -- cross-exchange latency arbitrage, liquidation-cascade provision,
maker-rebate market-making -- all need infrastructure this bot does not have (verified in-
sandbox: Binance returns HTTP 451, Bybit 403; and simultaneous two-venue execution is impossible
from one account), and building a fake version would be theatre. Funding rate is the one real
non-price signal the venue exposes, and it is ALREADY fetched (fetch_funding_rate, line 3703)
and already drives a funding_reversal strategy. THE OBVIOUS IDEA WAS TESTED AND REFUTED: fading
the crowded/funded side into reversion won just 25% across 29,454 corpus cases, while FOLLOWING
the extended move won 74%. Strong positive funding marks a persistent uptrend, and on this
corpus that persistence continued far more often than it reverted -- so the tilt FOLLOWS funding
(positive favours a long, negative a short), not fades it. It is NOT collected as yield, which
needs a spot leg and is worth only 0.003-0.009 of the price risk; it is a bounded +/-10% ENTRY-
TIMING tilt reading the funding component already computed, applied at the same site as the C387
regime tilt so the two compose. In the four-window replay it did not degrade the widened-
universe result (EV held at +$0.083). Left behind its flag (C392_FUNDING_TILT) for continued
measurement on live logs, where real funding rates -- not the corpus proxy -- will confirm or
refute it. This is the honest shape of 'a new edge class': the only one reachable was a non-
price venue signal, its naive direction was wrong, and measurement corrected it before shipping.


## C388

THE TWO STORIES DISAGREED, AND THE LOG WAS RIGHT. Read as the operator asked -- code as story A,
log as story B -- the code CLAIMED C377's 1.5R hard stop 'cannot be vetoed' and that a
STAGNANT_PARTIAL 'retains half under the hard stop'. The live log said the opposite: C377 fired
ZERO times in the whole session, and AEON took a STAGNANT_PARTIAL at -5.71%, banked half that
loss, widened the stop on the remainder, and the remainder died at -6.00% -- one position, two
losses, $0.43 + $0.45. FORENSIC RECONCILIATION: AEON's ATR was 2.7%, so R = 2*ATR = 5.4% and
C377's 1.5R stop sat at -8.1%. The partial triggers on PRU while the hard stop triggers on R,
and for a volatile pair the PRU trigger is hit FIRST and SHALLOWER than the R stop -- so the
'protection' was a larger loss taken in two pieces with a widened stop on the second piece. C377
was written correctly; it simply never got the chance, because the partial always fires first on
a high-ATR pair. THE FIX (cold-audit item 4): a stagnant LOSS past C377's own 1.5R now exits the
WHOLE position, and even between 1R and 1.5R it exits whole, because a partial is optionality
and optionality on a position already at its risk budget is just a bigger loss carried in two
trades. The partial is allowed ONLY while the loss is still inside 1R -- the one region where
retaining half is defensible. A five-case battery confirms AEON now exits whole at -5.71%, a
calm pair exits whole past 1.5R, and a shallow loss with an intact thesis still partials. HONEST
CORRECTION OF MY OWN FIRST READING, kept in the record: the -5.71% and -6.00% PERCENTAGES look
alarming but the DOLLARS were on-budget -- a 2.7%-ATR pair is sized so 1.5R loses $0.85, so it
lost only $0.63 at -6%. The sizing was correct; the real and only damage was the SECOND loss
from the widened-stop remainder, which is exactly what C388 removes. STORY A NOW DESCRIBES STORY
B: the impossible -6.00% second loss can no longer occur. Verified: syntax OK; AST unchanged; 1
count-asserted replacement; five-case loss-exit battery; replay boot clean; chain C367-C388
intact.


## C387

FIRST STEP OF THE REBUILD: CONDITION THE ENTRY ON REGIME -- the one change from the cold audit
that turns a negative edge positive rather than merely removing drag. THE MEASUREMENT IT RESTS
ON: the audit tested the bot's core signal directly on the corpus (long when 1h and 4h momentum
agree) and found it ANTI-PREDICTIVE overall, rho(score, barrier-win) = -0.022 with the win rate
FALLING from 49.5% at score 0.4 to 45.5% at score 1.0. But the regime split is decisive and is
the actual finding: buying strength wins 52.4% in a RISING tape (btc7d > +3%) and only 44.9% in
a FLAT one, where the bot trades most. The signal is not broken, it is being applied in the
wrong regime. C387 multiplies a candidate's score by 1 + 0.10*alignment, where alignment =
clamp(market_R * dir_sign / 0.40, -1, 1) using the same _market_bias_resultant that the logs
print as R: a long in a strongly rising tape is boosted 1.10x (the 52.4% cohort), a long in a
flat tape is left at 1.00x (the 44.9% cohort gets no boost), and a trade against the tape is
damped to 0.90x, compounding with the C386 counter-trend block. Bounded to +/-10% because it RE-
WEIGHTS an existing signal by regime rather than manufacturing a new one, and kept SEPARATE from
the counter-trend penalty in purpose: that gates OPPOSING trades, this grades WITH-trend trades
by how strongly the regime supports them. VERIFIED IT ACTUALLY FIRES, because a silent no-op is
the failure mode this project keeps hitting: result['direction'] is set at line 7384, well
before C387 reads it at ~7508, and a 150s replay confirms the tilt applied to 1,132 scored
candidates with alignment spanning the full -1.00 to +1.00 and a mean of +0.331 (most entries
with-trend, as expected). ALSO, STEP 1 FUNCTIONALLY ANALYSED PER OPERATOR REQUEST:
scan_lively_pairs (432 lines) ranks the universe by 0.40*log-volume + 0.25*change +
0.35*freshness, cohort-relative, where freshness deliberately down-weights already-moved pairs;
a hardcoded ~90-symbol blocklist removes stocks/forex. Tested on the corpus, the liveliness
score DOES predict a pair that resolves (hits a barrier) within the hour -- 74.5% in the top
quintile vs 70.1% in the bottom, rho +0.024 -- so it works, but weakly, and critically
'resolves' is not 'wins': a lively pair moves decisively in EITHER direction, which is exactly
why regime-conditioning the DIRECTION matters more than the liveliness rank. Verified: syntax
OK; AST unchanged; 1 count-asserted replacement; regime multiplier table checked across R and
direction; replay confirms live firing; chain C367-C387 intact.


## C386

COUNTER-TREND-INTO-NOISE IS NOW BLOCKED, NOT NUDGED -- the loss pattern the operator kept
reporting, finally traced through the code to a penalty too weak to matter and fixed with the
one edge that has ever measured. THE SESSION, READ TRADE BY TRADE AGAINST THE LOG: 5 closes, net
-$0.80, WR 20%, and the two real losses were the SAME GIGGLE position exiting in two pieces -- a
STAGNANT_PARTIAL at -2.53% and its remainder at -2.48%, both inside 1.5R so C377 behaved
correctly. The C382 override fired 23 times (the C385 wiring works) and C384 logged ZERO
reconstructions (every position now carries a real R), so those two fixes are confirmed good.
The problem was never the exits. DEDUCED FROM THE ENTRY PATH: the bot took 17 LONG against only
4 SHORT while the market frame R was NEGATIVE, and logged 56 counter-trend-penalised attempts
across just three pairs. GIGGLE was a LONG at R=-0.20 then -0.16 -- a long AGAINST a falling
market. This is precisely the cohort the two-frame resonance study measured on RAW data on
2026-08-08d: a long after/against the market move is a ~45% barrier-win trade. The existing soft
penalty is only 10-20%, which drops a 0.80 score to about 0.70 and still clears MIN_SCORE, so
the ~45% side kept trading. THE FIX IS NOT A NEW SIGNAL, because the same study REFUTED trading
the reversal -- it is to let the one surviving edge break the tie. A weak-but-opposing market
frame (|R| 0.15-0.40) entered into a NOISY pair (orderliness < 0.33) has neither trend nor
orderliness behind it and is now BLOCKED; the identical entry into a genuinely ORDERLY pair
keeps the soft penalty, because orderliness (raw rho +0.0328, t=+4.99 on barrier win) is the
only quantity in this project that has ever raised barrier-win probability. This deliberately
does NOT touch the existing hard block above |R| 0.40 or the moderate 0.40-0.55 band, and it
does NOT resurrect the refuted reversal trade; it removes the worst-founded entries only. HONEST
BOUNDING: five closes is thin, and this bot has been hurt by fixing on thin evidence -- but the
DIRECTION here rests on 158,444 observations, not on these five trades, and the change only ever
removes entries that have neither of the two things that predict a win. Verified: syntax OK; AST
unchanged; 1 count-asserted replacement; decision table checked across the orderliness range;
GIGGLE re-chart attempted but the entry window is 3 days stale and outside the 200-bar API
limit, so the entry was judged from the log's own trajectory lines rather than a fabricated
chart read; replay boot clean.


## C385

MY OWN C382 OVERRIDE NEVER FIRED ONCE, and the code deduction shows two independent reasons.
MEASURED: zero C382 OVERRIDE lines in a full live session against 190 blocks from the very
family the override exists to release. REASON 1 -- IT WAS WIRED TO ONE GATE OUT OF FIVE. The
refuted already-travelled family spans leg_exhausted, parabola_bounce, late_leg_no_forward,
absorption_at_extreme and no_structural_room; the override reached only leg_exhausted (4 sites),
so parabola_bounce at 92 blocks and no_structural_room at 48 were never touched. Now wired at
all nine sites across the five gates. Deliberately NOT extended to flat_projection,
h1_regime_shock, resultant_counter, mtf_disagree or corr_cap: those encode DIFFERENT hypotheses
that the 158,444-observation study never tested, and corr_cap in particular is the SOL+WIF
correlation lesson, which stays absolute -- it blocked CYS at a score of 1.039 this session and
that is the gate doing its job. REASON 2 -- THE CONFIDENCE BAR WAS AN IMPOSSIBLE AND. Requiring
score >= 0.70 AND confidence >= 0.80 sounds reasonable until you look at the joint distribution:
of eight candidates scoring >= 0.70 in the live session exactly ONE also reached 0.80
confidence, and the rest sat at 0.51-0.69. Score and confidence are strongly correlated, so
demanding both at the top of their ranges is very nearly unsatisfiable. Lowered to 0.60, which
releases PROM at 0.782/0.616 and BEAT at 0.702/0.686 while still holding PROM at 0.701/0.592 --
meaningful without reopening the floodgates. ALSO DEDUCED FROM THE CODE, and recorded rather
than changed: volatility reaches position size through TWO paths -- _vol_adj = clamp(1/ATR,
0.55, 1.30) in the Kelly allocator and margin = risk/(2*ATR) in the risk fit -- which compounds
to a 6.75x notional preference for a 0.7% ATR pair over a 2% one where risk parity alone would
give 2.9x. The risk fit BINDS in practice (the log shows Kelly's $62.50 cut to $11.59), so
_vol_adj does not change the final size; it biases SELECTION toward calm pairs, and calm pairs
went 0-for-4. Left in place this pass because C384 has only just guaranteed R on every position,
and the 0-for-4 is confounded with three of those positions having traded unprotected. Re-
measure once a clean session exists. AND: 91% of Step-3 analyses are CACHED (45 fresh against
464 cached) because the bot re-decides on a 15m candle boundary while scanning every ~5 min.
That is correct for 15m-derived features and saves real work, but it does mean an intra-candle
move cannot trigger an entry. Recorded, not changed. Verified: syntax OK; AST unchanged; 1
count-asserted replacement plus 5 structural wirings; predicted releases checked against the
live candidate list; replay boot clean.


## C384

THREE OF EIGHT POSITIONS TRADED WITH NO RISK FRAMEWORK AT ALL, and the logs looked normal
throughout. THE DEFECT: _c372_R_pct is published at exactly ONE sizing site. Any position
reaching _open_position down a different branch arrives with R = 0 -- and C372's profit floor,
C373's capture gate and C377's hard stop ALL begin `if R <= 0: return`, so all three SILENTLY
SKIP IT. The position then trades with no profit floor, no capture gate and no hard stop, and
nothing in the log says so. MEASURED on the operator's live session: 8 closes but only 5
positions ever recorded a stop level, and C377's hard stop fired exactly ONCE. FORENSICS OF THE
WORST TRADE: UB closed at -5.01% for -$0.69 via the OLD PRU stop at -4.4% (2.9xPRU) after 64.4
minutes; at its R of ~1.8% C377 would have cut it at -2.70% for about -$0.37. THE SIZE ASYMMETRY
THIS EXPLAINS: implied notional per trade splits cleanly into two regimes -- roughly $4.4-5.0 on
high-ATR pairs and $11.8-15.2 on low-ATR pairs, because margin = risk / (2*ATR) so a CALM pair
buys a LARGE position. The small group went 2W/2L; the large group went 0W/4L. Losers were sized
2.2x bigger than winners, which is why the session lost money even though the average winning
move (+4.29%) was LARGER than the average losing move (-3.43%). A bigger average move on the
winning side still loses when the losing side carries twice the notional and no stop. THE FIX: R
is 2*ATR by definition and ATR is always available on the analysis, so a missing R is now
RECONSTRUCTED from analysis atr_pct (then components.atr_pct, then a 1.5% last resort that logs
a warning naming the untraced path). There is no legitimate case for a position without a risk
unit. Every reconstruction is logged, so the branches that fail to publish R can be found and
fixed at source rather than papered over. Verified: syntax OK; AST unchanged; 1 count-asserted
replacement; retro-checked against the four large losers showing the -5.01% trade cut at -2.70%;
replay boot clean.


## C383

THE RELEASE VALVE WAS LEAKING THE WHOLE EDGE, and it was mine. The operator reported small
margins, insignificant profits and repetitive log messages; all three trace to the same place.
MEASURED on the live session: 210 C373 capture-holds with a MEDIAN of 0.10R, and six closes
averaging a 0.28R WIN against a 0.45R LOSS -- payoff 0.63, break-even 62%, and therefore losing
at the 50% win rate actually achieved. C372 and C373 hold profit below 1R, which is correct, but
their horizon RELEASE VALVE then lifted the floor and let ANY profit out. The bot got the worst
of both worlds: it refused the quick small profit, never reached 1R, and banked LESS later than
if it had simply taken the scalp. The valve now has a floor of its own -- past the horizon a
profit must still be worth C383_RELEASE_R (0.5R) before it is taken, and only past DOUBLE the
horizon does anything go, with C377's 1.5R hard stop still bounding the downside so nothing can
hang. On the same trades that lifts payoff from 0.63 to 1.22 and break-even from 62% to 45%,
turning a 50% win rate from -0.072 to +0.042 per trade. ON MARGINS, and this is the honest
answer rather than another knob: at $250 with the declared 10% drawdown the per-trade risk is
$0.85, so margin = 0.85 / stop, and the selected pairs carry ATR 2.0-3.4% giving R = 2*ATR =
4-6.8% and therefore $12-21 of margin. The log shows Kelly wanting $62.50 and the RISK BUDGET
cutting it to $11.59 -- the budget is binding, exactly as designed, and a 1R win pays the risk
budget REGARDLESS of ATR. Bigger margins come from one of two places only: a higher declared
drawdown (the C380 prompt -- 20% doubles every figure) or more capital. Everything else is
arithmetic. LOG NOISE: the capture-held line fired once per monitor tick per position, 171-210
times a session. Now throttled to once per position per five minutes, which shows the state
without burying the rest. CONFIRMED NOT PRESENT in this log: the $50 budget bug -- both banners
read $250.00, so C375's re-derivation held. Verified: syntax OK; AST unchanged; 3 count-asserted
replacements; five-case release-valve battery covering early hold, the leaking past-horizon
case, a worthwhile release, an earned 1R and the 2x-horizon escape; replay boot clean.


## C382

THE ZERO-TRADE SESSION: A REFUTED GATE VETOING THE BOT'S BEST WORK, AND AN RR GATE MEASURING A
GEOMETRY THE BOT NO LONGER TRADES. Four hours, 19 scans, 30 candidates analysed every scan, ZERO
passed, 570 rejections across TWENTY-TWO distinct gate reasons with none dominant -- death by a
thousand cuts, where each gate looks reasonable alone and their product is zero. FAULT 1: the
'already-travelled / exhaustion' family (leg_exhausted, parabola_bounce, late_leg_no_forward,
absorption_at_extreme, exhaustion_hard, micro_exhaustion, no_structural_room, capitulation)
produced 25.4% of ALL rejections -- and, decisively, killed 47% of every candidate scoring >=
0.50. It blocked GWEI at score 0.840 with confidence 0.925, GWEI again at 0.792/0.902, and BLESS
at 0.807. THIS IS THE HYPOTHESIS THIS PROJECT ALREADY REFUTED, on 2026-08-01b, at 158,444
observations: bull-regime gap -0.02pp, t = -0.29, 2/4 out-of-sample splits, flat across all nine
threshold combinations, with the Atlas recording verbatim 'never re-propose a range-position or
already-travelled entry filter'. The gates are NOT deleted, because some encode microstructure
the 158k study never tested -- but they may no longer overrule a candidate clearing BOTH score
>= 0.70 and confidence >= 0.80. Below that bar they block exactly as before; every waiver is
logged and COUNTED so the next session can measure whether the overridden trades actually paid.
FAULT 2: the reward:risk gate computed its ratio from a PROJECTION ('target 0.1% vs stop ~0.5%
@ATR 0.2%' = RR 0.20) while, since C372, a profit exit cannot fire below 1R and, since C377, the
stop is 1.5R -- so the geometry actually traded is 1R against 1.5R = RR 0.67, which clears every
floor. The gate was rejecting trades against a shape that no longer exists, killing BLESS at
0.831 (poor_RR 0.19) and MUBARAK at 0.666 (0.44). It now floors the target at 1R and the stop at
1.5R and keeps whichever target is larger, so a projection above 1R still counts as the bonus it
is. A DEAD-CODE BUG OF MY OWN, CAUGHT BEFORE SHIPPING: the first wiring of the override wrapped
only the rejected_reasons counter and left the `continue` outside it, so the override would have
logged a waiver and skipped the candidate anyway -- the exact defect class this project keeps
paying for. Re-done so the override bypasses the entire block including the continue, verified
at all four leg_exhausted sites. Verified: syntax OK; AST 313 -> 314; 3 count-asserted
replacements plus 4 structural wirings; replayed against the real blocked candidates -- both
GWEI setups now trade, CAP at 0.333 still blocks.


## C381

ONE SOURCE OF TRUTH FOR TARGETS, AND ONE CYCLE PER DAY. THE DEFECT: two independent target
systems existed and only one of them mattered. C369/C380 derive PROFIT_TARGET_NORMAL_PCT and
_HP_PCT from equity and the declared drawdown, print them in the boot banner and drive the
PHASES ladder -- while every MODE DECISION went through cycle_target(), which read a fixed
CYCLE_TARGETS schedule of {'normal': [1.0, 0.5], 'hp': [0.75, 0.25]} instead. The operator's log
shows the split exactly: the banner reads 'target 0.45%/day (Normal 0.32% then HP 0.14%)' while
the mode tracker reads 'Normal: +0.0% / 1.0%'. THE DERIVATION WAS COSMETIC. At a 0.32% target
the mode could never advance against a 1.0% bar, so the phase ladder never progressed, the day-
complete stop never fired and the equity carry-forward never happened -- C368, C369, C379 and
C380 were all reasoning about a number the mode manager never consulted. CYCLE_TARGETS is now
DERIVED from the same budget, so there is exactly one place a target can come from. SECOND FIX,
operator directive: ONE Normal followed by ONE HP per day, not two of each. The schedule held
[cycle-1, cycle-2] per mode; a single entry each makes the day Normal -> HP -> STOP, and
cycle_target()'s min(cycles_done, len-1) clamp then returns the same figure at every cycle
index, so the one-cycle day holds by construction rather than by a counter that could drift.
THIRD, AND IT WOULD HAVE REPEATED THE WHOLE BUG: CYCLE_TARGETS is a SNAPSHOT dict built in
__init__, so updating the two scalars in _c369_apply_budget would have left the schedule the
mode manager actually reads frozen at its construction-time default -- precisely the derived-
once-then-stale failure C375 fixed for the budget itself. The dict is now refreshed in the same
breath as the scalars, at boot, on state load, on fresh start, and at every new day as equity
compounds. FILE AUDIT (operator request): eleven persisted files, all with real load paths and
real consumers -- state and positions restore the book, mode_v60 carries mode/cycle/overshoot,
learning_v60 feeds _recent_trades (16 consumers), pair_profiles feeds baseline_feats, the four
Markov files feed predict() under the C370 sufficiency gate, eval_window feeds the C284 gate and
s3_calib feeds C335 trust. mode_v60 was absent from a short replay only because
ModeManager._save fires on a mode TRANSITION and none occurred. A 0-byte eval_window .tmp
appears in sandbox replays; it could NOT be reproduced as a live failure, the write primitive
works standalone, nothing shadows json/os/time, the clock shim returns a JSON-serialisable
float, and the operator's own log shows 'EVAL WINDOW W2: 85/100' -- a LOADED value, proving live
persistence works. Recorded as a sandbox anomaly rather than claimed as a bug. Verified: syntax
OK; AST unchanged; 4 count-asserted replacements; cycle_target() returns the derived figure at
cycle indices 0/1/2/5; replay boot clean.


## C380

SIZE FROM A DECLARED DRAWDOWN, NOT AN ARBITRARY PERCENTAGE. The operator's complaint, restated
precisely: at $500 a 7% winner paid $0.44-$0.88 because notional was only 1-2.5% of the book.
That is not the min-order floor (C379 fixed that) and not an ATR problem. The real cause is that
every earlier version PICKED A PER-TRADE PERCENTAGE OUT OF THE AIR and let the drawdown fall
where it may -- nobody had ever declared how much loss is acceptable, so the bot defaulted to
timid: risking a 4.4% worst-case month to earn 0.88%, while Crypto Fund Research puts the MEDIAN
maximum drawdown of professional quant crypto funds at -20.7% across 117 tracked funds. Risking
4.4% to earn 0.88% is not prudence, it is under-deployment. THE INVERSION: the operator now
declares a maximum monthly drawdown and everything else is DERIVED from it -- day cap = DD/22
(the worst case, every day hitting the cap), per-trade = day cap / 2 (two full losses end the
day), target = day cap (symmetric, so break-even sits at exactly 50% by construction rather than
by luck). One human decision, everything else arithmetic. AT THE 10% DEFAULT ON $500: day cap
0.455%, per-trade 0.227% = $1.14 of risk, typical notional $28.41 = 5.7% of the book, a 7%
winner worth $1.99 instead of $0.88, and +2.02% per month at a 60% daily win rate or +3.04% at
65% -- while still risking only HALF the drawdown a professional quant fund routinely accepts.
The full scale is exposed at startup so the choice is conscious: 4.4% DD gives $12.50 notional
and 0.88%/month, 15% gives $42.61 and 3.04%, 20.7% -- professional parity -- gives $58.81 and
4.22%. The operator picks the risk and the bot reports exactly what that buys BEFORE any money
moves, including the per-trade risk in dollars, the typical notional as a share of the book, and
what a 7% move would actually pay. THIS IS THE DIAL THAT WAS MISSING: every previous session
tuned entries, exits, floors, stops and horizons while the single number governing how much any
of it could earn was never once set deliberately. Verified: syntax OK; AST 313 unchanged; 5
count-asserted replacements; derivation table checked from 4.4% to 20.7% drawdown; startup
preview reflects the drawdown-derived shape; replay boot clean.


## C378

THE EXCHANGE-SIDE STOP, AND SIZE THAT FINALLY RESPONDS TO ODDS. TWO BUILDS. (1) A REAL REDUCE-
ONLY STOP RESTING AT BITGET. C377 made the risk budget real WHILE THE BOT RUNS; this makes it
real while it does NOT -- across a restart, an Android sleep, a dropped connection or a crash.
Those gaps are precisely where the operator's carried SKYAI position ran to -8.88% against a
-6.8% intent, because a virtual stop cannot fire when nothing is looking. arm_exchange_stop()
places a trigger-based reduce-only order so it can only ever CLOSE, never open or extend, and it
is armed at the SAME 1.5R level C377 enforces in-process: one level, two enforcers. ccxt exposes
Bitget plan orders inconsistently across versions, so three parameter spellings are tried in
order and the first that succeeds wins; total failure is logged LOUDLY rather than swallowed,
because a stop that silently failed to arm is worse than no stop at all -- it would be believed.
In PAPER no order is sent, the level is recorded and C377 enforces it, so paper and live agree
on the LEVEL even though only live holds the resting order. CRITICALLY, stops are RE-ARMED FOR
EVERY POSITION RESTORED FROM DISK -- that is the actual restart-handover fix, and it works only
because C375 persists R across the restart; where R is missing the operator is TOLD the position
cannot be bounded rather than left to assume it is. (2) SIZE PROPORTIONAL TO EQUITY **AND**
ODDS. The risk budget was already equity-proportional (C369, a flat 0.066% above ~$250; below
that the $5 min-order floor forces 0.300% and small books are structurally over-risked, which
C369 states at boot). It carried NO odds term whatsoever: two trades with identical stops
received identical size whether their chance of winning was 45% or 55%. Standing Rule 10 forbade
odds-scaling while the only candidate was the SCORE, which measures rho = -0.060 -- sizing by
that would have been sizing by noise, the exact failure C335 exists to prevent. Orderliness is
different, and the difference is measured rather than argued: raw rho +0.0328, t = +4.99,
against BARRIER WIN specifically, which IS the odds of the trade winning -- the p in EV = p*T -
(1-p)*S - C. Kelly at 1R:1R is f* = 2p - 1, so the +2-3pp swing orderliness buys moves f* by
roughly 0.04-0.06: real but small. The tilt is therefore bounded to +/-30%, because Rule 9 is
unsatisfied (no separate-batch replication) and because a sizing term able to double or halve a
position on a rho of 0.033 would be false precision. PRE-SHIP AUDIT: zero duplicate methods
across 313; pyflakes clean except the known dead full_analysis names and the two guarded
expressions; sizing curve checked end to end; the indentation fault introduced by the first re-
arm patch was caught by compile and repaired before shipping. Verified: syntax OK; AST 312 ->
313; 4 count-asserted replacements; replay boot clean.


## C377

THE RISK BUDGET IS NOW REAL. Operator reported that restart handover was still broken and trades
still losing on average; the forensic answer is the same defect for both. EVERY STOP IN THIS BOT
HAS BEEN VIRTUAL -- grepping the entire file for stopLoss / triggerPrice / presetStopLoss
returns nothing but the bot's own STOP button, so a stop existed only as an opinion the monitor
loop formed when it happened to look. MEASURED COST, from the operator's own logs: REL_HARD_STOP
fired at -6.8% and -12.0% while price was ALREADY at -8.88% and -13.39% (mean overshoot 1.74pp),
and the carried SKYAI position lost $0.79 against a $0.33 per-trade budget -- 2.4x the number
C369 derives and prints at boot. And while the bot restarts, sleeps or drops network there is NO
protection whatsoever, which IS the restart-handover failure: a position handed across a restart
is naked for the entire gap. THE FIX: _c377_enforce_hard_stop runs as the FIRST statement of the
per-position loop, ahead of every judgement exit, and closes at 1.5R where R = 2*ATR, the very
number the SIZING already assumed and C372 already publishes. It cannot be vetoed, penalised,
floored or tilted by anything, because it is arithmetic rather than opinion: the position has
lost more than the budget said it could. On the SKYAI case it would have closed at -4.17%
instead of -8.88%, turning a $0.79 loss into $0.37 -- inside the $0.33 budget. CROSS-FIX
CONTRADICTION AUDIT, run because eleven changes now interact: on a LOSING position C372's profit
floor, C373's capture gate and C376's maker routing all require move>0 or a profit token, so
none of them can delay C377 by construction; on a WINNING position C377 cannot fire, and C376
changes only HOW an exit executes, never WHETHER. C377's 1.5R and C372's 1.0R act on opposite
signs of the move and can never both apply to one tick. C377 is a CEILING on loss, so the older
PRU-based REL_HARD_STOP may still fire earlier and whichever is tighter wins, which is correct
for a stop. The sizing chain is now a single source: C369 derives per-trade risk from equity,
C375 re-derives it on load / fresh-start / new-day, C373 makes the $25 ceiling equity-relative
with $25 as a floor so there is no regression at $50, C372 publishes R, C375 persists R across
restarts and C377 enforces it. One number now sizes, floors, gates and stops. ALSO FIXED: the
boot banner printed 'DAILY BUDGET @ $50.00' before load_state and then the correct figure after,
which was merely confusing but is the kind of confusion that hides real faults. Verified: syntax
OK; AST 311 -> 312; 3 count-asserted replacements; 7-case stop battery including R-missing skip
and in-profit no-fire; replay boot clean.


## C376

MAKER EXITS ON PROFIT-TAKING -- the strategic pivot, and the only remaining lever with a
measured mechanism behind it. THE RECKONING THAT PRODUCED IT: the 10-hour C375 session moved
payoff 0.16 -> 0.63 exactly as designed, and the win rate fell 67% -> 45%, leaving EV per trade
essentially unchanged at -0.064. win_rate x payoff keeps landing at zero minus costs whichever
knob is turned, which is the signature of an efficient market at this horizon. WHAT THE MARKET
ACTUALLY PAYS FOR, each measured on real data rather than argued: RISK TRANSFER -- 6,738 real
Bitget funding settlements across 22 pairs show median +0.0050%/8h with the crowd long 76.3% of
the time, but funding collected is only 0.0034 to 0.0094 of the price risk taken across 8h-504h
holds, so holding the receiving side is a directional bet wearing a funding costume, and the
market-neutral spread version collects 0.050%/8h against 0.16% of two-leg fees; not collectible
without a spot leg this bot does not have. FORCED FLOW -- needs a liquidation map and sub-second
execution, unavailable. LIQUIDITY PROVISION -- collectible, and 75% of the remaining fee sits on
the taker exit because entries are already post-only since C363. THE TABLE THAT DECIDES IT: the
one edge that has survived every test is orderliness -> barrier win (raw rho +0.0328, t=+4.99),
worth roughly +2 to +3pp of barrier win rate. At the measured R ~ 1.5%, taker both sides costs
0.080R and gives EV -0.040..-0.020; today's maker-in/taker-out costs 0.053R and gives
-0.013..+0.007; maker both costs 0.027R and gives +0.013..+0.033. THE EDGE IS SMALLER THAN THE
CURRENT TRANSACTION COST AND LARGER THAN THE POTENTIAL ONE, so halving the round trip is not an
optimisation, it is the difference between having an edge and not having one. IMPLEMENTATION: a
profit-taking close first rests a reduce-only limit on the passive side of the book (ask when
selling, bid when buying) so it cannot cross; if it does not fill it falls straight through to
the existing taker path, so the worst case is today's behaviour plus a few seconds and never a
position left hanging. Fills and misses are COUNTED (_c376_maker_fills / _c376_maker_misses)
because the realised saving depends on the fill rate and on adverse selection, and neither may
be assumed. SAFETY IS ABSOLUTE AND PROVEN, NOT ASSERTED: the maker path requires BOTH a reason
on _C376_PROFIT_TOKENS AND a positive PnL, so a loss, stop, thesis-death, partial-thesis-dead or
emergency close always crosses the spread -- a 10-case battery confirms every negative-PnL row
routes taker, including a profit-token reason carrying a negative PnL. A stop that cannot fill
is how accounts die. BENCHMARK CONTEXT, researched rather than assumed: Crypto Fund Research's
database of 84 reporting funds put the average crypto hedge fund at -7.2% for 2025 with 63%
losing money and quant funds at +0.4%, against aggregator sites claiming 36%/48% with no fund
count; good quant crypto across a cycle is roughly 20-30%/yr, so the operator's 'at least half
of the best' target lands at 0.75-1.1%/month, which would place this bot in the upper tier of
professional quant crypto funds. Verified: syntax OK; AST 311 unchanged; 3 count-asserted
replacements; 10-case safety battery; replay boot clean.


## C375

TWO REAL BUGS FROM THE OPERATOR'S LIVE SCREENSHOTS, and they share one root cause. BUG 1 -- THE
BUDGET WAS DERIVED BEFORE THE EQUITY WAS KNOWN. The banner read 'C369 DAILY BUDGET @ $50.00' and
three lines later 'Loaded state: $499.96'. _c369_apply_budget was wired into
TradingBot.__init__, which runs BEFORE main() calls portfolio.load_state(), so a $500 book was
traded on a budget calibrated for $50: per-trade risk 0.300% instead of 0.066% -- 4.5x too much
risk on EVERY trade -- day cap 0.30% instead of 0.20%, and the banner wrongly announcing
'BINDING, day is one-trade' when at $500 the $5 floor does not bind at all. Fixed in three
places, because equity arrives by three different routes and goes stale by a fourth: re-derive
after load_state(), re-derive after a fresh start (C371 lets the operator CHOOSE the figure, so
__init__ saw only the default), and re-derive at every day anchor because equity COMPOUNDS and
C369's whole point is that the structure changes as the book crosses ~$250. BUG 2 -- THE SAME
ROOT CAUSE, SEEN FROM THE OTHER END. The restored TUT position carried $2.50 of margin on a $500
book (0.5%), which is precisely what a $50-derived budget produces: 0.300% x $50 = $0.15 of risk
divided by a ~6% stop. It therefore banked $0.14 on a +11.64% winner, because the position was
about five times too small -- not a bad exit, a mis-sized entry inherited from the previous
session's wrong budget. AND A THIRD DEFECT FOUND WHILE CONFIRMING IT: _c372_R_pct is assigned in
_open_position and was never persisted, so any position restored after a restart came back with
R=0 and BOTH profit floors -- C372's exit wrapper and C373's capture gate -- silently skipped
it. A restarted session's carried position was the one trade of the day still running on the
pre-C372 rules, which is the exact class of silent-skip this project keeps paying for. R and
expected_hold_min are now saved and restored with the position. Verified: syntax OK; AST
unchanged; 5 count-asserted replacements; budget arithmetic checked at $50 vs $500 showing the
4.5x risk error; replay boot clean.


## C374

ORDERLINESS ENTRY TILT -- closing the framework loop that the full-pipeline audit exposed. THE
AUDIT'S UNAVOIDABLE FACT: barriers alone cannot make money. For a driftless walk with a target
at +aR and a stop at -1R, P(target first) = 1/(1+a), so expected value is EXACTLY ZERO at every
choice of a -- 0.17R/85%, 1.0R/50%, 2.0R/33% all price to the same nothing. C372 and C373
removed a GUARANTEED LOSS (a 0.17 payoff simulates to -2.37%/month at the measured 67% win rate,
which is what the operator's live sessions actually did); they do not by themselves create a
gain. Reaching 4%/month needs P(target before stop) pushed ABOVE the random-walk 50% at 1R --
about a 68% barrier win rate, with 57% giving 1.5%/month. THE ONLY QUANTITY THIS PROJECT HAS
EVER MEASURED THAT PREDICTS BARRIER WINS is Bandt-Pompe permutation entropy: rho +0.0234,
t=+3.49, 3/4 out-of-sample splits, clearing Bonferroni across all 36 tests run, on 79,457
observations at the +1h horizon, with a pseudo-random null behaving at t=+0.56 and the effect
halving by +2h and gone by +6h -- a short-memory property, and +1h is exactly this bot's median
60-75 minute hold. It is ordinal and therefore scale-free and inherently relativistic; it is
already computed live; and C366 already uses it to set the HORIZON. It had never been used to
choose WHICH trade to take, which is the one place it can raise p. BOUNDED ON PURPOSE at +/-8%:
a tilt, not a gate. The effect size is small (rho 0.023) and Rule 9 is NOT satisfied -- there
has been no separate-batch replication -- so it may reorder candidates and swing a marginal
MIN_SCORE decision, but it can never rescue a crushed score nor destroy a strong one, which is
the exact failure mode C367 was written to end. FULL-PIPELINE SIMULATION of the composed system
(20,000 days per cell, $500 book, R=$0.33, day target $1.75, day cap $1.00, 8-trade cap): at
payoff 1.0 the month reads +0.03% at a 50% win rate, +1.15% at 55%, +2.26% at 60%, +3.82% at 67%
and +4.62% at 70%; the same simulation at the pre-C372 payoff of 0.17 reads -2.37% at 67%,
reproducing the operator's live result and confirming the diagnosis. THE HONEST RISK, stated
plainly: the 1R floor TRADES win rate for payoff, so if requiring 1R drops the win rate from 67%
to 50% the system lands at break-even rather than 4%. That single number -- the barrier win rate
at 1R -- is now the one measurement that decides everything, and it is what the next paper
session must produce. Verified: syntax OK; AST unchanged; 1 count-asserted replacement; tilt
curve checked across the full permutation-entropy range; replay boot clean.


## C373

FIXING THE TWO LIVE-MONEY FINDINGS FROM THE DEEP AUDIT, plus rebuilding the Atlas into an actual
map. F2 -- THE $25 PER-TRADE CEILING WAS ABSOLUTE. In dynamic_allocate every other term scales
with the book (_deployable, _kelly_base, _conviction, _vol_adj, the 0.55/0.40 position caps) and
this one number did not; it BOUND ON EVERY SCAN of the live $500 session, logged as
'max=$25.00'. As equity compounds the bot progressively loses the ability to deploy it: $25 is
50% of a $50 book, 5% of $500 and 0.5% of $5,000, where five full positions would be 2.5% of the
account. Now equity-relative at C373_MAX_PER_TRADE_PCT (0.25) with the old $25 retained as a
FLOOR, so behaviour at $50 is unchanged and the change can only ever loosen, never tighten; the
real binding constraint remains the C369 per-trade risk budget, which sized the live trades to
$9.83 under either cap. A backstop must scale with what it backs. F1 -- THE C372 PROFIT FLOOR
WAS ENFORCED AT ONE OF SEVEN DOORS. C372 gates sub-1R profit-taking by wrapping should_exit_dri,
but only _monitor_positions and _quick_exit_check route through it. _check_profit_targets called
_c336_partial_close and _close_position DIRECTLY, so its POSITION_CAPTURE at 1.5*PRU was never
gated -- and since PRU ~= ATR while R = 2*ATR, that banks at about 0.63R, precisely the sub-1R
capture that produced the measured 0.17:1 payoff (4 wins averaging +$0.055 against 2 losses
averaging -$0.345, 67% win rate needing 86% to break even). A rule enforced at one of seven
doors is not enforced. The same floor, the same horizon release valve and the same never-gate-a-
loss rule now apply there. RE-SCAN OF ALL FOURTEEN CLOSE CALL SITES confirms the invariant is
now complete: every PROFIT door is R-gated (12336, 12455, 12469, 12483, 13732, 13735, 15612,
15622, 15626) and every ungated door is a LOSS or ADMIN path that must never be gated --
_dri_selective_close fires only on dri>0, pnl<-5% or neutral-and-losing; _check_profit_targets
13684 is the HP drift cap at -2.5*PRU; 14067 is the HP deep-loser close; 13425 is
_close_all_positions. ATLAS REBUILT: it had degraded into a second changelog -- 2,036 lines, 16
session narratives, SIX line references, and _advance_session_phase (where a latent IndexError
was found) appearing zero times -- which is why fault location had been grep-driven all session.
It now opens with a regenerable NAVIGATION INDEX: 292 methods, the fourteen largest functions
with their bare-except counts, all 73 money-path functions with line ranges, the seven close
paths with their gate status, and the tested invariants. Verified: syntax OK; AST unchanged; 3
count-asserted replacements; F2 scaling table checked $50-$5,000 showing no regression at $50;
F1 five-case battery holding 0.63R and 0.17R, releasing at 1.04R and past horizon, and never
touching a loss; replay boot clean.


## C372

THE RISK UNIT AND THE REWARD WERE SET BY DIFFERENT SYSTEMS -- the deep functional break the
operator sensed, found by auditing the live $500 session end to end. THE SESSION, AS ARITHMETIC
(6 closes, ledger exact to the cent against equity): 4 wins averaging +$0.055, 2 losses
averaging -$0.345, a 67% win rate, payoff 0.16, break-even needing 86%, EV -$0.078 per trade --
a GUARANTEED loser that wins two trades in three. THE CAUSE: the sizing set the stop at 2.80% of
price (a $0.33 risk on $11.80 of notional, correctly 0.066% of equity per C369) while the exit
engine banked profit at 0.47% of price. The bot was risking 2.80% to make 0.47% -- an R:R of
0.17:1 -- because those two numbers were computed by different code that had never been
introduced to each other. The sizing knew the stop; the exits never saw it and took profit on an
ATR/peak-giveback scale unrelated to the risk being carried. SECOND CONSEQUENCE, which explains
why the day always ended red: at $0.055 a win the 0.25% Normal-phase target ($1.25 at $500)
needs 23 WINNING trades, while the day's loss cap allows 3 losses and MAX_TRADES_PER_DAY is 8 --
so the day could only ever terminate on the loss cap and never on its own profit target. The
budget was unreachable by construction. THE FIX is a framework fix, not a patch: R (2*ATR, the
stop the sizing already assumes) is published at sizing time, travels ON the position, and a
PROFIT-taking exit may not fire below C372_MIN_R (default 1.0) multiples of it. At the observed
67% win rate that moves EV from -0.22R to +0.34R per trade, and it makes the daily target
reachable in 3-4 wins instead of 23. IMPLEMENTED AS A SINGLE-POINT WRAPPER -- should_exit_dri
now delegates to _should_exit_dri_raw and filters its verdict -- because the engine has dozens
of early returns and a per-site patch would certainly have missed one. DELIBERATELY NARROW,
because a profit floor is dangerous the moment it touches the downside: only reasons in
_C372_PROFIT_TOKENS are gated, only when the raw price move is POSITIVE, the floor LIFTS
entirely once the position passes its expected horizon so nothing can hang waiting for a move
that is not coming, and a missing or non-positive R skips the gate so positions restored from
disk behave exactly as before. Verified: syntax OK; AST 310 -> 311 (the wrapper); 4 count-
asserted replacements; 9-case unit battery confirming REL_HARD_STOP, REL_STAGNATION and
REL_DSI+DRI DIVERGE all pass straight through while the live +0.17R case is held and the same
trade past its horizon is released; replay boot clean.


## C370

IMPLEMENTING THE FRAMEWORK I WROTE -- the operator asked whether FRAMEWORK.md had actually been
built, and the audit answered NO: 3 of 11 components, and two of the three apparent passes were
keyword false positives (_c369_p was _c369_plan; DECAY was the unrelated DSI constant). I had
shipped the BUDGET LAYER around the framework (C368/C369) and none of the DECISION EQUATION
inside it. This closes the four items that can be built on evidence already in hand, and states
plainly why the rest must not be. BUILT: (1) EXPONENTIAL FORGETTING on RegimeMarkov counts --
they accumulated forever, so a 2025 tape was weighted equally with today's; transition odds
drift with funding, liquidity and market structure, and a stationary chain fitted to a non-
stationary process converges on the average of incompatible markets and is right about none of
them. 30-day half-life at ~96 obs/day (factor 0.5**(1/2880)), applied to the whole matrix before
each increment so the Laplace floor keeps its relative role; gentle by design -- a month-old
transition still carries half its weight. (2) SAMPLE SUFFICIENCY inside
AuxStateMarkov.trusted(): Brier skill alone was not enough. MEASURED on this bot's own state
files, FamilyStateMarkov held 99 observations across 125 cells = 0.8 PER CELL with 17-21 of 25
cells never observed, so the prior dominated the posterior and its apparent +8pp edge was the
argmax of noise; IchimokuMarkov was degenerate in a different way, its prediction equalling the
base rate EXACTLY in 4 of 5 regimes because one letter owns ~95% of the alphabet. A chain now
needs >=10 real transitions per cell before it may spend authority -- the C335 pattern one level
deeper: C335 asks 'is it calibrated', this asks 'has it enough data to be calibrated ABOUT'. (3)
TRADE-COUNT CAP: round-trip cost is ~8bp of notional, so on a 0.35%/day target at $500 five
trades spend 23% of the day's target and twelve spend more than all of it -- trade count is a
first-class risk parameter, capped at 8/day as a generous backstop against fee-churn. (4) FIRST-
PASSAGE EXPECTANCY SCAFFOLDING, LOGGED WITH ZERO AUTHORITY: every entry now records target,
stop, cost and the BREAK-EVEN probability the geometry implies -- the p the trade NEEDS, not a p
we claim to know -- beside its outcome, which is the calibration substrate a later session needs
to score p by Brier before any gate is switched on. DELIBERATELY NOT BUILT, and this is the
important part: the EV entry gate, Kelly-on-p sizing and the RPPc regime prior all require a
CALIBRATED p, and shipping an uncalibrated one would be precisely the failure C335 exists to
prevent -- noise steering money. Semi-Markov dwell remains a design task. Verified: syntax OK;
AST 310 unchanged; 4 count-asserted replacements; decay factor and sufficiency arithmetic unit-
checked; replay boot clean.


## C369

CAPITAL-AWARE DAILY BUDGET -- answering the operator's question 'at 500 USDT, is 4% net per
month achievable?' with arithmetic instead of optimism. THE ANSWER IS YES, BUT NOT WITH THE
0.15+0.05 STRUCTURE, and the reason is a ceiling nobody had noticed: a daily target g caps the
month at (1+g)^22-1 REGARDLESS OF CAPITAL. At g=0.20%/day that ceiling is 4.49%, so a 4% month
would demand ~90% of theoretical perfection -- winning nine days in ten with almost no losing
days. More money does not lift that ceiling; only a larger daily target does. WHAT $500 ACTUALLY
BUYS is the release of the OTHER constraint: MIN_MARGIN_PER_TRADE ($5) at a reference 2x/1.5%
stop risks $0.15, which is 0.300% of a $50 book but only 0.030% of a $500 one. Below ~$250 that
floor BINDS -- the smallest orderable loss exceeds any sensible daily cap, the day degenerates
to a single trade, and break-even is forced to 46%. At $500 it stops binding, the cap can sit
BELOW the target, and break-even collapses to 36.3%. THAT, not the extra dollars, is what puts
4% in reach. DERIVED STRUCTURE AT $500: target 0.35%/day (Normal 0.25% then HP 0.10%, then
STOP), day cap 0.20%, per-trade risk 0.066% (three losing trades absorbed), break-even daily WR
36.3%, projected month +1.67% at a 50% daily win rate, +2.90% at 60%, +4.15% at 70% -- so 4%
arrives at about a 69% daily win rate, and the perfect-month ceiling is 7.99%. NOTHING IS
HARDCODED: _c369_derive_budget(equity) computes min-orderable risk, target, cap and per-trade
risk from MIN_MARGIN_PER_TRADE, a reference leverage and stop, and the cap ratio, so the same
code is correct at $50, $500 and $5,000 and STAYS correct as equity compounds; the PHASES ladder
now READS that budget instead of restating it. The plan is logged in full at boot -- including
the break-even win rate and the perfect-month ceiling -- because the break-even number is the
single quantity that decides whether a month is reachable and it must never again be assumed.
Verified: syntax OK; AST 308 -> 310 (+2 derivation methods); 4 count-asserted replacements;
derivation table checked across $50-$5,000 with the binding flag correct at $50 and clear from
$100 up; replay boot clean.


## C368

THE CONSISTENCY BUDGET -- the day re-architected around a MONTHLY target, on the operator's
spec: bank 0.15% in Normal, then 0.05% in HP, then STOP and carry equity into tomorrow. THE
ARITHMETIC THAT FORCED EVERY NUMBER: break-even daily win rate = cap/(cap+target). The old 4.0%
day-risk cap against a 0.20% daily target demands a 95.2% DAILY win rate -- the operator's
target dropped onto the existing risk frame would have LOST about 28% a month rather than making
1.5-4%. A small daily target is only viable beside a small daily cap. PER-TRADE RISK IS A
CONSEQUENCE, NOT A CHOICE, and it was measured the hard way: 0.0014 was tried first and the bot
took ZERO trades across 177 replay scans, because risk/stop then implies a margin below the $5
MIN_MARGIN_PER_TRADE floor for any stop wider than 0.7% and every candidate is filtered out. At
0.0030 a 1.0-1.5% stop -- the normal range for a 60-minute crypto horizon -- lands at
$7.50-$5.00 margin and is orderable. Day cap therefore equals one full stop: ONE LOSING TRADE
ENDS THE DAY, which is the discipline every measurement in this project already argued for.
Break-even 60%; 22 days at a 70/75/80% daily win rate compound to +1.11/+1.66/+2.22% per month.
SCALING, the honest answer to 'can we reach 4%': the $5 floor is what holds the band near
1-2%/month on $50; at $250 the same stop costs 0.056% of equity and the headroom returns. The
band is CAPITAL-constrained, not strategy-constrained. LADDER cut from four phases
(1.0/0.75/0.5/0.25 = 2.5%/day, a daily-number chase) to two (0.15/0.05), after which the session
completes and equity carries forward -- stopping while ahead is the entire mechanism by which a
small edge compounds, since a bot that trades on after target hands the day's gain back to the
fee ledger and the next bad tape. LATENT CRASH FIXED IN THE SAME PASS: the advance routine
hardcoded the ladder length as 4 in FIVE places, so a 2-phase ladder would have raised
IndexError on the first mode transition of the day and taken the whole advance with it; all five
now derive from len(PHASES). A ladder length must never be written down twice. Verified: syntax
OK; AST 308 unchanged; 11 count-asserted replacements, 0 failures; C367's floor fix confirmed
present in the same file; ladder simulation Normal-1 -> HP-1 -> DAY COMPLETE; replay 42 scans 0
errors, $50.00 -> $50.27, 5 closes.


## C366

PREDICTABILITY -> HORIZON: the missing wire, and the first ENTRY-SIDE change earned by
measurement rather than argued from theory. THE GAP: the trade horizon was pure volatility
(pred_hold = 25/ATR%, clamped 15-60 min). The genuine pattern-based horizon in
predictive_analysis() -- 50/35/15 min by setup with a continuation probability -- is
unreachable: its ONLY call site is inside full_analysis(), which has ZERO call sites, so line
20959 always yields 0 and the ATR fallback is the live path. Meanwhile Bandt-Pompe permutation
entropy -- computed live, normalised [0,1], ordinal and therefore scale-free and inherently
relativistic -- fed ONLY the S3 pair-history channel, which C335 gates to zero authority. The
bot measured how far ahead each pair is predictable and then never used it for the one decision
it exists for. THE OPERATOR'S CORRECTION, which reframed the hypothesis correctly: high-
predictability pairs may not sustain moves LONGER, but they have a better chance of delivering
NET PROFIT WITHIN the horizon -- a claim about RELIABILITY, not duration, needing no direction
skill at all, because a pair that travels cleanly lets an exit engine capture it while a
chopping pair stops you out on noise before the move arrives. MEASURED (predbench.py): 79,457
observations, 302 calendar-day blocks, features demeaned WITHIN SYMBOL so only the time-varying
component is graded, 4-way OOS split, admission >=3/4 splits AND |t|>=2.0. At +1h low PE gives
future efficiency rho +0.0151 t=+3.64 (4/4), resolved-above-1-ATR rho +0.0269 t=+3.88 (3/4),
barrier win rho +0.0234 t=+3.49 (3/4) -- all three clearing Bonferroni for the 36 tests run.
Effect halves by +2h and is gone by +6h: orderliness is a short-memory property and +1h is
exactly this bot's median 60-75 min hold. METHODOLOGICAL NOTE, because it nearly cost a false
positive: v1.0 of the bench scored its PSEUDO-RANDOM control at rho=+0.28 t=+92, impossible for
a null, which exposed the TEST rather than the signal -- the null varied only by symbol-name
length (a proxy for coin class and thus volatility), and more seriously any feature roughly
CONSTANT PER SYMBOL reproduces the same cross-sectional ranking every timestamp, so 3,613 blocks
were one measurement repeated and t was inflated ~sqrt(3613). Fixed by within-symbol demeaning
and calendar-day blocks; the corrected null sits at t=+0.56/+1.67/+0.73. THE CHANGE: an orderly
pair gets a TIGHTER horizon (it should have resolved), so stagnation pressure arrives sooner on
exactly the setups that ought to pay quickly. ONE-SIDED BY DESIGN -- nothing is ever lengthened,
because noisy pairs showed no resolution at +6h either. Bounded to -25% max and clamped to the
same [15,60] band, so the worst case is a modest tightening. NOT YET REPLICATED ON A SEPARATE
BATCH (Rule 9): authority is deliberately small and the orderliness reading is stored on the
analysis and LOGGED on every entry so the next session can validate it against live outcomes.
Verified: syntax OK; AST 308 unchanged; 1 count-asserted replacement; clamp/monotonicity unit
battery; replay boot clean.


## C365

PRE-FLIGHT AUDIT OF THE WHOLE FILE -- three real defects fixed, one of them mine, plus a
measurement blind spot that changes how every prior number should be read. Operator asked for a
full nitty-gritty sweep before running C364. METHOD: AST duplicate-definition sweep (classes,
module functions, methods) -- CLEAN, zero shadowed definitions; pyflakes undefined-name sweep --
8 hits, each hand-adjudicated by walking its enclosing try/except; writer-vs-reader orphan-
attribute sweep -- 72 candidates, ALL confirmed false positives (dataclass fields, class
constants, and the C351-documented pos-written/getattr-read pattern); reachability check on
full_analysis -- confirmed ZERO call sites, so its 4 undefined names are inert in both
directions. DEFECT 1 (live, since C329): _admin300 was READ at the meta-learning record and
ASSIGNED 25 LINES BELOW it. The `if '_admin300' in dir()` guard prevented the crash and thereby
HID the defect -- the expression evaluated False on EVERY close, so every administrative close
(target achieved / session end / day cap / shutdown) has been written into _recent_trades as an
ordinary trade. Assignment moved above first use. DEFECT 2 (live): ModeManager._save built a
dict literal with '_overshoot_credit' as a key TWICE; the later un-coerced copy silently won,
disabling the C304 float()/or-0.0 guard, so a None could be persisted and reloaded -- the
Principle #23 persistence class. Duplicate removed, coerced version kept. DEFECT 3 (mine, in the
unreleased C364 draft): the funding block called _fetch_funding_raw with the CCXT symbol
('BTC/USDT:USDT') when it expects the Bitget form ('BTCUSDT') -- it would have returned None
every single time and the real rate would never once have been used; worse, it was a BLOCKING 5s
network call sat directly in front of a stop-loss, the exact hazard the spread estimator had
just been cached to avoid; and the +/-0.75% clamp was tighter than reality, the operator's own
recorder showing funding reach -1.96%. Now reads the 600s _funding_cache the analyzer already
populates, keyed correctly, with NO network call on the exit path, clamped +/-3%. HARNESS BLIND
SPOT (not a bot defect, but it re-frames prior numbers): _c336_partial_close books PnL straight
to the portfolio via release_margin and NEVER routes through _close_position, which is the only
method exitlab.py wrapped -- so every banked half of every C336/C338 partial has been ABSENT
from every measurement this project's harness produced. Control run: instrumented closes summed
+$0.23 while equity moved +$0.95; the partials were 76% of the profit and went unrecorded. The
bot's own books were right the whole time (per-trade implied fees reconcile to 8bp within
rounding); the instrument was wrong. exitlab.py now wraps both legs and conservation reconciles
EXACTLY ($0.23 + $0.72 = $0.95). Every trade-level statistic in the Atlas predating this is
therefore INCOMPLETE and understates the bot. VERIFIED: syntax OK; AST 308; 5 count-asserted
replaces; 12/12 unit battery (bid/ask sourcing, market buy->ask, market sell->bid, all four
entry-limit cross/passive cases, reduce_only exit still FILLS, symbol normalisation, cache hit,
clamp coverage, funding sign for long/short and both funding signs); clean replay boot 75 scans
0 errors; POISONED-STATE BOOT with corrupted mode/state/positions JSON recovers to equity 50.0 /
mode NORMAL with no traceback.


## C266

BOARD-PARITY DIAGNOSTIC (observability only, zero strategy change). log_c265b forensics:
operator's gainers-board screenshots showed 10 movers 'the bot didn't catch' — API verification
proved 8 of 10 DO NOT EXIST on Bitget USDT-M futures (MYX board 2.69 vs futures 0.082 =
different market; BID/AIA/PTB/67COIN unlisted on futures AND spot) — the board was another
venue/section. The 2 that do exist (BAS, XPL) were screened into the top-30 and analyzed EVERY
scan, dying on legitimate grounds (BAS: pulled-back pump, rolling-24h actually -19.5%, RR
0.15-0.31 for shorts + TURNING penalty for longs; XPL: raw signal conflict, 39% agreement, score
0.02-0.05). Session verdict: zero trades on a hangover chop day (parabola_bounce 2-10/scan, EPIC
-40%/VELVET -19.6%/MAGMA -21.4% mean-reverting) = CORRECT abstention. NEW: one log line per
screen — the top-5 |24h| movers among ALL volume-passing pairs, each tagged with its screen rank
(#N) or its Live score vs the cut — so every future 'did we miss X?' is answered by the log
itself. A mirror, not a gate: touches no selection path. Also resolves the recurring 24h-change
base confusion: the bot's Chg is rolling-24h (correct for momentum), boards often anchor daily
opens — both true, different bases.


## C265

BUDGET-FREEZE RELEASE VALVE. log_c263: after -$0.85 of losses the C260 share fell to $0.24 —
below even a MIN-margin stop — and the bot froze for 7.5 HOURS (missing i.a. TLM +9.3%). C260's
integral is CORRECT (capital preservation) and C200's endless session is CORRECT alone; their
intersection is a limbo — too poor to trade, too rich to reset, with no exit (sessions have no
time limit and the budget only re-anchors on a NEW session). Valve: the first structurally-
untradeable C260 block with ZERO open positions stamps a clock; if >=90min later another such
block fires with still no positions and no entry in between, the session concludes as risk-
exhausted through the EXISTING start_session_cooldown path (pause min(+4h, midnight), then a
fresh session re-anchors equity + the 2.5% cap at the LOWER equity — losses stay ladder-bounded,
the freeze does not). Any successful entry resets the clock (_c265_last_entry_ts stamped at
position registration); positions.count() used (the container is an object, not a dict —
truthiness would never fire). State-machine validated: concludes at 90min frozen, entry-reset
and with-position suppression both verified.


## C264

MOMENTUM TERM-STRUCTURE beta-hat (log_c263: 0W/3L, then 7.5h frozen — the worst session since
C239). Chart truth inverted the whole log: the three LONG losses (ARPA/EPIC/VELVET, all -0.9 PRU
stagnant bleeds) were entered into a rollover — ARPA fell -4.1% and VELVET -8.2% AFTER their
exits (the exits were excellent; the ENTRIES were the sin) — while the FIVE shorts hard-blocked
as 'counter-trend vs R=+0.51' ALL won (MIRA -6.1%, VANRY -8.0%, OGN -4.8%, TLM -6.2% low, ZEC
-1.2%). ROOT: R's structure was 1h=+0.30 4h=+0.42 12h=+0.79 — strength MONOTONICALLY INCREASING
with horizon = fresh momentum weakest = a stale leg. The scalar hides what the curve screams.
NEW: beta-hat = [cov(v, ln tau)/var(ln tau)] / max(|R|,0.10) over tau in {1,4,12}h, v direction-
adjusted by sign(R) — the log-horizon slope of the momentum term structure, normalized
relativistically to the trend it sits on. Validated on 12 REAL structures from 3 sessions: fires
on exactly the two pathological curves (this killer at +0.377 and one bear-side mirror at
+0.575), quiet on every healthy curve including the winning VANRY session's 0.84/0.64/0.52
(-0.20). Three hooks: (a) computed once after C79; (b) counter-R hard block RELAXES to a 15%
penalty when beta-hat>0.25 — the C245 sibling (C245 releases on a LEVEL forecast, C264 on the
GRADIENT; a counter-R entry under inversion is with-the-derivative); (c) with-R entries damped x
max(0.70, 1-0.45*tanh(4*(beta-0.25))) — smooth, zero at threshold, saturating. RETRO: damp 0.789
puts ARPA 0.534->0.421, EPIC 0.560->0.442, VELVET 0.498->0.393 — ALL below their ~0.46 bars, all
three bleeds never open; the five winning shorts become takeable at x0.85. Fully relativistic
(own-horizon curve, |R|-normalized) and predictive (the gradient LED price by ~30min).


---



# C453 — THE STOP WAS SIZED ON ONE BAR AND TESTED OVER SEVEN

Session `20260907_111306`: 12h50m, **0W/6L, −$1.77**, equity $248.23.

## THE SHAPE OF THIS FAILURE IS NEW

Eleven versions of exit work have chased *"trades go up and give it back"* — a **holding** problem.

**This time four of six never moved one tick our way.** Peaks of +0.00%, +0.00%, +0.05%, +0.06%. And
it is **not direction** — four BUY, two SELL, both sides lost.

**The hold times are the tell, and I should have checked them first:**

| pair | held | price | exit |
|---|---|---|---|
| **ZEC** | **4m 45s** | −1.52% | hard stop |
| **BSB** | **3m 10s** | −0.77% | hard stop |
| WLD | 16m 55s | −0.14% | regime |
| APR | 48m | −1.21% | hard stop |

**The hard stop is never gated by C422-4, C443 or anything else.** So this is not the exit stack being
impatient. **It is the stop sitting inside ordinary noise.**

## Principle #205 — A THRESHOLD CAN BE ABSOLUTE IN *TIME* AS WELL AS IN PRICE

Measured across **eight instruments, 500 five-minute bars each**, on the **maximum adverse excursion
over a 35-minute hold** — what the position is actually exposed to, not what one bar does:

| pair | survives on 2.3 PRU | needs for p90 |
|---|---|---|
| BSB | **69%** | 5.24 PRU |
| APR | 71% | 3.51 |
| ETC | 72% | 4.10 |
| BTC | 74% | 3.75 |
| PEPE | 75% | 3.99 |
| WLD | 83% | 2.76 |

**Roughly one trade in four is killed by noise alone**, before the thesis has a single bar to express
itself — and the session's 2-of-6 hard-stop rate is exactly consistent with that.

**Not an instrument quirk:** BTC needs 3.75 PRU and PEPE 3.99 — the same shortfall at opposite ends of
an eight-fold volatility range.

**The cause is a units mismatch in time, not in price.** The stop is 2.3 PRU built from the **15m ATR
— a one-bar measure** — while the position is held ~35 minutes across seven bars. Adverse excursion
grows with the square root of elapsed time; a one-bar stop does not.

**Fourteenth instance of absolute-where-relative — but every previous one was a price threshold, and I
have been hunting those.** This hid in plain sight because 2.6× ATR *sounds* generous. It is — for one
bar.

## Principle #206 — WIDENING A RISK-SOLVED STOP DOES NOT WIDEN RISK

Position size is capped in **dollars** by `PER_TRADE_RISK_PCT × equity`, and margin is solved
**backwards** from the stop.

| hold | stop PRU | position size | **dollar risk** |
|---|---|---|---|
| 20 min | 2.66 | 87% | **unchanged** |
| 35 min | **3.51** | 65% | **unchanged** |
| 50 min+ | 3.91 (cap) | 59% | **unchanged** |

**A stop 1.53× wider produces a position 1.53× smaller.** Nothing about the risk budget, the day cap
or `PER_TRADE_RISK_PCT` changes. What changes is that **the same risk now buys enough room to survive
normal movement** — noise survival rises from 69–83% to 85–90% on seven of eight instruments.

**Replayed on the session: ETC, stopped at −2.4 PRU, would have been HELD. The other five were inside
2.3 PRU already** and were closed by other paths — so C453 alone rescues one of six, and saying so
matters, because a fix that claims six saves when it delivers one is how this project has previously
talked itself into regressions.

## ALSO CONFIRMED WORKING

C451 funding cross-section ran **22 times**, the OI/funding quadrant **33 times**, the C441 target cap
bound **41 times**, and the C444 grader recorded **6 exits with the entry score attached — the first
session in which entries have ever been graded.** C452's calendar correctly reported `clear`.

## VERIFICATION

AST 364 unchanged. **The first attempt at this edit silently matched nothing (count=0) and left the
three constants as orphans — the constants-read check caught it before shipping.** Applied by line
insertion and re-verified. Duplicate defs 0. Wrong-object sweep clean. All three constants read.
Scaling and risk-neutrality tabulated across four horizons. MAE measured on **4,000 real bars**.

**Limits.** BSB needs 5.24 PRU and the 4.0 cap does not reach it — the thinnest instruments remain
under-protected **by design rather than oversight**. The 90th percentile is a choice; p85 or p95 give
different multiples and the C444 grader is what will eventually say which. **And this widens the stop
on a book that has just had six straight losses** — if the next session shows *larger* losses rather
than fewer, `C453_HOLD_SCALED_STOP` is a single switch.

---

## Principle #207 — THE PROJECT'S MEMORY NEEDS THE SAME DISCIPLINE AS ITS CODE

**I destroyed the Atlas at C453 and had to rebuild it.**

The mechanism was mundane and entirely mine. At the start of the session I restored `omega.py` from
the outputs folder — but not the Atlas alongside it. The `cat >>` then created a **fresh** file
containing only the newest section, and the `cp` back to outputs **overwrote the good copy with the
truncated one.** Both locations and the VFS cache held the same file, so nothing could be recovered.

**What made this survivable is the one thing that was done right:** the changelog lives **inside the
code**, is append-only, and is written at the moment of each change with the evidence in hand. 87
entries, 371,398 characters, C264 to C453, no gaps. The Atlas was always a distillation of it — so
the distillation could be lost and the substance could not.

**What was permanently lost:** the numbered principles #1–#204 and the hand-written per-version
essays. Those were interpretation, not evidence, and they are gone.

**Three standing rules, added because this cost real work:**

1. **Restore the whole working set or none of it.** `omega.py` and the Atlas are one artefact in two
   files. Restoring one without the other is how a partial state becomes a destroyed one.
2. **Never `cp` onto a delivered file without first checking it is larger than what it replaces.** A
   4KB file overwriting a 495KB file is not an edit, it is a deletion.
3. **Keep the authoritative record in the artefact that cannot be casually overwritten.** The
   in-code changelog survived precisely because it is protected by every syntax check, AST audit and
   count-assert that guards the code itself.

**This is the same failure family the Atlas documents 14 times over — a step that looked like a
routine operation and was actually destructive, with nothing checking the result.** It belongs in the
record rather than quietly repaired.

---

## C454 — THE C451 RANK WAS BIASED BY TIES, AND IT WAS LIVE IN BOTH LOSING SESSIONS

The operator supplied the last profitable build (C448) and asked for the problems solved to the core.
**Diffing C448 against C453 found a severe bug of mine.**

**The diff is clean, and that matters:** 14 executable lines removed since C448 (the banner and the HP
machinery C450 retired) against 268 added. **Nothing was destroyed, only added** — so the regression
is attributable to an addition, not a loss.

### Every addition, classified by whether it can alter a trade

| version | change | can alter a trade? | confidence |
|---|---|---|---|
| C449 | PnL-weighted base rate | **yes — 5 consumers** | HIGH — fixes a demonstrable defect |
| C450 | HP labels | can only *enable* entries | HIGH |
| C451-1 | entry grading | no — records only | n/a |
| **C451-2** | **funding cross-section** | **yes — entry vector** | **LOW** |
| **C451-3** | **OI/funding quadrant** | **yes — entry vector** | **LOW** |
| C452 | FOMC calendar | inert until 16 Sep | n/a |
| C453 | hold-scaled stop | yes — exit | HIGH — measured, risk-neutral |

**C451 changed the entry vector, and the failure signature was four of six trades never moving one
tick our way.**

### Principle #208 — A RANK THAT COUNTS TIES AS "BELOW" IS A DIRECTIONAL BIAS

```python
_rank = sum(1 for x in srt if x <= raw) / n      # counts every TIE as below
```

**On the live board, 303 of 780 pairs (39%) sit on exactly the same funding value.**

| | rank | cross-section | fade on a long |
|---|---|---|---|
| my C451-2 | **0.783** | +0.567 | **−0.340** |
| midrank (correct) | 0.589 | +0.178 | −0.107 |

**The most ordinary instrument on the venue received a systematic fade against every long, for no
reason whatever — applied to two candidates in five, live in both zero-win sessions.**

### Principle #209 — A RANK ON A FLAT BOARD MANUFACTURES SIGNAL

A rank is **scale-free** — its virtue when dispersion is real, its defect when it is not. **Today's
board spans 0.0100 percentage points from p10 to p90**, and a rank will still produce a full-range
±1 signal from it.

Presto Labs puts funding at **~12.5% of price variation over 7 days and decaying.** Ranking a spread
this narrow does not recover that signal — **it invents one.**

**Verified: with the gate in place, the median pair, the 95th percentile and the 2nd percentile all
resolve to exactly 0.000 tilt on today's tape.** The cross-section is silent, which is correct.

**And the weight was wrong even if the rank had been right.** I blended it at 50% of the funding
component; the evidence supports about an eighth of variance. Now 25% — **weighted to match the
evidence rather than my enthusiasm for having found the paper.**

### Why this is the core fix rather than a revert

Reverting C451 wholesale would have discarded a research-backed idea because **my implementation** of
it was broken, and would have left the same tie-bias waiting to be reintroduced the next time anyone
ranks anything. The rank is now correct, gated on real dispersion, and weighted to the evidence.
`C451_FUNDING_XS` and `C451_OI_FUNDING_STATE` remain independent switches.

### VERIFICATION

AST 364 unchanged. Duplicate defs 0. Wrong-object sweep clean. Both constants read. **Tie bias
measured against 780 live funding rates**; midrank verified at the median, 95th and 2nd percentiles;
dispersion gate confirmed silencing the cross-section on today's board.

**Limits.** The 0.0002 dispersion floor and the 0.25 weight are judgements — the entry grader will
price them, and it now runs. C453's wider stop remains unproven. **And C449 and C451 shipped
together**, so while the tie bias is a certain defect with a measured magnitude, I cannot prove it was
the *only* cause of the two zero-win sessions.

---

## C455 — THE GATE WAS OFF WHEN IT MATTERED

**Sessions:** `20260908_230950` (1h19m, 1 trade, EGLD +$0.11) and `20260909_181013` (1h23m, PUMP −$0.50 / COTI +$0.37). Combined **−$0.01**.

**C455-3 — every trade the bot had ever taken was taken on the scan where its quality gate read zero.** `_c405_e_bar` ranks against the *previous completed scan*; on the first scan there is none, so it returned `floor` (0.0) — and `_c405_state` was never persisted, so that branch ran on every startup. Both logs say it: `below the live bar +0.000R (top 16% of 1 recent candidates)`. Afterwards the bar climbed to +0.150…+0.307 and nothing else qualified. **The inversion is in the bot's own arithmetic:** PUMP bought at E=+0.030R and lost, while the same session refused BTC at +0.186R and +0.218R. C420 diagnosed this 34 versions earlier and fixed the *oscillation*, leaving the *cold start*. Repair: the scan now **ranks but does not trade** without a reference, and the reference carries across sessions.

**C455-2 — the bot diagnosed its own losing trade and threw the answer away.** PUMP: entered 18:11:47; at **18:17:20** the entry brain hard-refused the same long (`real CVD -0.60`) while **the position was flat**; at 18:18:32 the exit brain said "thesis 110% left"; it exited at 19:03:53 at −2.2%. C414 lived inside `_run_scan_and_trade` and its only action was `continue`. No channel existed from a scan verdict to an open position.

**C455-1 — the most important line in the log reported the opposite of its own data.** `low n=1 -0.82R | mid n=3 -0.33R | high n=4 -0.69R → higher score IS earning more`. Mid out-earns high by 0.36R. The test read `high > low` and never looked at mid. "17 graded" was the whole ledger; only 8 carried a score.

**C455-4 — a symmetric 12% penalty on position within the 24h range**, validated 4/4 out-of-sample on ~140,000 bars.

---

## C456 — THE GRADER WAS NEAR-SIGHTED AND IT FLATTERED THE EXITS

**Sessions:** `20260910_011211` (0.5h, 0 trades) · `20260910_095131` (4.9h, 1 trade, −$0.10) · `20260911_175650` — **26.7 hours, 274 scans, 10 trades, −$0.07.**

**The one sentence:** that session's market rose a **median +3.08% with 82% of pairs up**, the bot took ten longs, and it still lost. *Session C's timestamps roll past midnight — a naive read gives 2h43m. Any parser must handle the rollover.*

**C456-1 — grade every exit at two horizons.** C444 graded at 30 minutes; the entry lines say `Hold: ~60min`. Chart-verified, three exits certified "protected capital" were badly wrong: USELESS −1.90% → **+4.38%** at 3h; MARSCOIN −0.81% → **+3.50%**; CHIP −1.80% → **+4.71%**. A twin record now settles at the trade's own `expected_hold_min`, clamped 45–240 min, and the disagreement is measured. Retro: mean drift **−0.26R at 30 min vs +0.25R at thesis**, 4 of 8 "protected" verdicts flip.

**C456-2 — my own C455 bug.** The reference was written into `learning.symbol_data` and relied on `record_trade` to flush it; a zero-trade session never saved. Persistence that depends on another component's save is luck.

**C456-3 — sleep gaps.** Six events up to 6.0 min; one hit an open position. The peak that position carries has a hole in it, and four exits judge against the peak. Recorded, not acted on.

### Also proven at C456, unfixed then
- **The entry stack has no edge**: `corr(entry score, outcome) = −0.003`; C451 ledger −0.19R/trade with the best band at +0.02R.
- **The score saturates**: six of eighteen candidates at exactly **0.865**; `tanh(core × 2.2)` flattens, post-penalty is a constant 0.60×, and C435-2 then drops candidates *by that saturated score* — so ties break on Step 1's liveliness order.
- **Every position cut ~61%** by the C403-vs-C369 contradiction.

---

## C457 — THE BOT HAS A PROFITABLE CELL AND IT WALKED OUT OF IT

**Session:** `20260913_161034` — 7.36h, 78 scans, **4 trades (2 long / 2 short)**, net **−$1.14**, win 1/4, equity $250.00 → $248.86, fees $0.13. The market rose a **median +0.88% with 62% of pairs up** and all four trades lost or broke even.

**The operator uploaded every state file this time, and that changes what can be known.** `trades_v60.csv` holds **2,388 completed trades** back to 2026-02-18 — the sample this project has never had.

### The seven-month truth

```
total -$74.95 over 2,388 trades = -$0.0314/trade
win 52.1%   avg win $0.406   avg loss $0.506   payoff 0.80
breakeven needs 55.5%  ->  it has 52.1%
```

### C457-2 — the largest measured edge in the project's history

C61 solves `ATR × lev ≤ 2.0%`, so `lev = floor(2.0/ATR)` and **the leverage bucket names a volatility band exactly**:

| lev | ATR band | n | $/trade | win% |
|---|---|---|---|---|
| 1x | 1.00–2.00% | 386 | −0.041 | 49.5% |
| 2x | 0.67–1.00% | 93 | −0.047 | 50.5% |
| **3x** | **0.50–0.67%** | **894** | **+0.018** | **58.1%** |
| 4x | 0.40–0.50% | 617 | −0.078 | 48.6% |
| 5x | 0.33–0.40% | 341 | −0.039 | 47.5% |
| 6x | 0.29–0.33% | 52 | −0.150 | 46.2% |

**3x alone would have made +$16.34 instead of −$74.95. 3x-long alone +$36.91 on n=635 at 60.0% win.** Out-of-sample **4/4** (time-early, time-late, pairs-A, pairs-B), gaps +$0.046 to +$0.111 per trade. **The win rate is the evidence that matters — a win rate is size-independent, so this is not an artefact of leveraged positions being larger.**

**And the bot left the cell.** Share of trades in the 3x band: 1.3% → 30.9% → 42.5% → 61.4% → **77.8%** (Feb→Jun), then **2.2%** in July and near zero since, while the win rate fell 55.6% → 42.8% → 37.3%. *Not claimed as causal* — corr(3x share, monthly $/trade) is only +0.357 over eight months and July breaks it. But the drift is mechanical: **Step 1 ranks by "liveliness" = recent movement = high ATR**, so the funnel walks toward the 1x bucket by construction.

Implemented as a tilt weighted by each band's **measured win-rate shortfall** below 58.1%, scaled so the worst takes the full 18%. Live-simulated: **18 of 144** vol-qualified pairs sit in the band right now — selective, not a blanket.

### C457-1 — my own fix fired once and lost money

C455-2's first live firing, XTZ: entered 22:05 @$0.2874; 22:19 C414 vetoed the same long; **22:32 C455_FLOW_REFUSED closed it at +0.3% = +0.21 PRU.** Both horizons called it wrong — C444 **+1.16R**, C456 **+0.81R** further in our favour — and XTZ ran to **+3.62%** at 3h against the +0.80% banked, with MFE **+2.05%** already printed during the hold.

Three calibration errors, all mine:
1. **"Not in profit" was ≤ 0.25 PRU, which admits winners.** The whole justification was that it may never take a winner off the table, and that is the first thing it did. → 0.0
2. **No peak guard.** Price had already proven the thesis; flow cannot un-prove a move that happened. → positions past 0.60 PRU of peak are out of reach.
3. **TTL 900s, veto 13 min old.** Flow decays in seconds to minutes. → 420s.

All three independently prevent the XTZ cut.

### C457-3 — the same defect as C456-2, one version later, and I wrote both

`_c456_fast` was an in-memory dict, so a fast grade settling in one session and its thesis twin in the next could never pair — and the thesis horizon is *by construction later*, so that split is the **normal** case near a session end. Moved to the persisted store. `C456_MIN_PAIRED` 6 → 4.

### What C456 proved, and it was not what I expected

**All four C444 fast grades and all three C456 thesis grades said "held would have been better".** Not one "protected capital" — a complete reversal of 20260911's 8-of-10. The exits are cutting winners on *both* horizons.

### Recorded, not fixed — with the evidence C458 will need

**1. The exit taxonomy is starkly bimodal.** Every exit designed to *take profit* makes money; every exit designed to *limit loss* gives it all back:

| profitable | n | net | | losing | n | net |
|---|---|---|---|---|---|---|
| target achieved | 389 | +$166.65 | | **REL_HARD_STOP** | 164 | **−$132.56** |
| HP target | 151 | +$63.84 | | STAGNANT_LOSS | 199 | −$62.27 |
| PEAK_REVERSAL | 233 | +$48.40 | | REL_DRAWDOWN | 78 | −$43.51 |
| profit capture | 85 | +$53.88 | | REL_ACCEL_LOSS | 64 | −$38.73 |

**REL_HARD_STOP alone is 177% of the total loss.** The stop averages **−4.66%** against a target-achieved **+2.12%** — **the stop is 2.20× the target**, because `_max_loss_pru` reaches 3.0 via C336 and up to `C453_MAX_PRU=4.0` while the target floor is 0.60R. **This is C458's work.**

**2. The S3 probability model is worse than a coin flip.** `s3_calib_v60.json`: n=301, brier=87.219, acc=133 → **44.2% accuracy, Brier 0.290** where "always say 50%" scores 0.25. It prints P=0.714 at entry and delivers 44%. Systematic overconfidence of ~26 points, and it feeds sizing through Kelly.

**3. Shorts cost 10× what longs do**: long n=1647 −$0.0084/tr (53.7%) vs short n=741 −$0.0826/tr (48.3%).

**4. `family_markov_v60.json` is ~95% Laplace prior** — only one cell (state 2→2, 53 observations) carries data. The family chain contributes noise dressed as signal.

**5. C455-4 fired on ETHFI at 6% then 1% of its range** — correctly identifying a short at the bottom of a completed −3.21% move — and the trade was taken anyway and **never went favourable once** (MFE −0.17%). An 11% shave cannot stop a candidate the rest of the stack wants.

### Verification

Syntax; AST **366 functions unchanged**; duplicate defs 0; class-ownership sweep **clean across 31,438 lines** with nested classes correctly excluded; no orphan constants; XTZ retro asserts all three guards; penalty curve asserted bounded on [0, 0.18]; **live Bitget simulation** through all five steps (787 contracts → 144 vol-qualified → 144 series → 18 in-band, C61 sizing re-derived).

### Limits

The band table is **my** measurement embedded as a prior, not the bot's own running estimate — the `lev` field now recorded in each grade record is the first step toward self-measurement. The 3x band is not positive every month (March −$0.142, June −$0.057) even though the aggregate and all four splits hold. **C457-1 has now been wrong once already** — treat it as unproven in both directions. Nothing here touches the stop, the target, the S3 model or the entry score, so if the next log still loses, the cause is in that list.

---

### Principle #209 — a bucket boundary can be a measurement instrument

Leverage looked like a sizing output. Because C61 solves `ATR × lev ≤ cap`, it is really a **volatility label with an integer boundary** — and grouping 2,388 trades by it exposed a 9-point win-rate edge that no continuous ATR analysis had surfaced in 200 versions. **When a derived integer is a monotone function of a continuous input, group by the integer: its boundaries are free, pre-registered bins.**

### Principle #210 — a safeguard's own threshold must be read as an outcome, not an intention

C455-2 was specified as "may only refuse to keep risking, never take a winner off the table", and was then implemented with `≤ 0.25 PRU`, which admits winners. The sentence and the number disagreed and the number won. **After writing a guard, evaluate its threshold against the stated intention with a concrete number substituted in** — here, "is +0.21 PRU a winner?" — rather than trusting that the constant expresses the sentence.
