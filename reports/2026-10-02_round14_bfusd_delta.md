# Round 14, BFUSD and Delta Exchange India (C521): did we test correctly, and a book that adjusts itself

2 Oct 2026. Four parts:
1. your screenshots (1 Oct, 11:52 IST) and last night's first C519/C520 rebalance, checked against Binance;
2. a fresh audit of how every earlier idea was tested, with better mathematics (round 14);
3. what the bot does differently now (C521);
4. the update and Ubuntu commands.

Pre-registration `research/c521_preregistration.md` (pushed first, 4ff6175).
Results: `research/c521_results.txt`, `research/c521_delta.txt`.

---

## 1. The screenshots and the overnight rebalance: all verified

| check | result |
|---|---|
| the 12 positions on your 11:52 screen | ✅ every price inside Binance's 06:21–06:23 UTC range; gross $335.42; open +$1.10 − $0.17 exit fee = **+$0.93**, as shown |
| Savings | ✅ reserve $191.81 = margin $66.62 + 25% of $500.75; idle $308.94 × 6.69% / 12 = $1.72/month |
| C520 boot | ✅ `OMEGA C520`, `Loaded state: $499.83`, Savings 6.69%, no 🛑 line |
| **the first C519 rebalance (2 Oct 05:35 IST)** | ✅ the plan names "ETH +11.16 < $20, LINK +6.92 < $20"; **11 targets = 11 held**, no "not held" line; one trade (ADA's target fell to $3.12: sold) |
| the plan, to the cent | ✅ replayed from the saved inputs (which now carry each coin's floor and the venue) |
| 30 Sep and 1 Oct prices | ✅ closes and volumes identical to Binance's own futures candles on **80/80** coins |
| funding on Binance | ✅ every position against Binance's published rates: 3 settlements (8-hourly coins) and 7 (HYPE, TAO: 4-hourly); total +$0.00018 vs +$0.00023 |
| the tournament's first Binance day (1 Oct) | ✅ by hand, to 4 decimals: N2+N3 −0.5383%, the old rule −0.8650%, K4 −0.6944% |
| the book | −0.34% in 0.8 days (normal noise) |
| the intraday shadow (M1) | −4.3% in a day: on Binance it runs the full model from hour one and trades a lot, and costs eat it, exactly as the research predicted. Paper only |

(I can now read Binance's futures data directly through www.binance.com, so
every Binance number can be checked the same day.)

---

## 2. Did we test correctly? The audit

You asked me to check whether the earlier ideas were judged correctly, not
just on simple data. I checked the method itself, with the tools used to
audit fund research.

| question | method | answer |
|---|---|---|
| **Survivorship bias?** (testing only coins that survived) | the archive has 24 coins delisted before its end (LUNA among them) | ✅ **no bias**: they are in. With them the Sharpe is 1.74, without 1.62: the book made money **shorting coins that later died**. Real, but partly hard to capture (exchanges restrict new shorts before a delisting), so I count it as part of the haircut |
| **Look-ahead?** (using tomorrow's data today) | code read line by line, then a deliberate cheat to prove the test can tell | ✅ **none**: cheating (trading on the same close) gives Sharpe 5.32; as traded 1.74; acting one day late still 1.40 |
| **Too many tries?** (60–120 ideas tested; one is bound to look good) | Deflated Sharpe Ratio (Bailey & López de Prado) | ✅ 1.000 (the best of 120 worthless strategies would show Sharpe ~0.3). Still ≥ 0.92 unless the earlier tries were very spread out |
| **Lucky settings?** | 135 neighbouring versions (other lookbacks, windows, horizons, sizes) | ✅ **a plateau**: all 135 make money, median Sharpe 1.54. ❌ **but the exact settings were lucky:** the probability of backtest overfitting (CSCV) is **0.93**. The best-looking setting in one period does not stay best in the next. **The honest forecast is about 1.5, not 1.74**, before the usual one-third haircut |
| **Were "safety" ideas judged fairly?** | the key correction: compare at **equal risk** (Sharpe-difference test of Ledoit & Wolf, and returns at matched volatility). Earlier rounds compared raw returns, which punishes an idea for carrying less risk | see below |

**The re-test at equal risk:**

| idea | Sharpe vs today | quarters better | 2025–26 | at equal volatility | verdict |
|---|---|---|---|---|---|
| **range-based volatility (GK)**: each coin's risk measured from the whole day's high-low range, not just its close | **+0.19 (p 0.017)** | **4 of 4** | **+0.23** | +55.6%/yr vs +50.1%; max DD 41.5% vs 41.8% | **ADMITTED.** Round 11 called it a near miss (t 1.87) because it was judged on raw return. That was the testing error |
| K4 (fast EWMA risk scaling) | +0.02 (p 0.45) | 1 of 4 | −0.18 | same return, **worst month −12.9% vs −17.4%**, max DD 36.6% vs 41.8% | not admitted; a real tail cut, scored forward |
| drawdown loop (risk × (1 − drawdown/30%)) | −0.03 | 1 of 4 | −0.24 | same return, **max DD 30% vs 42%, worst month −12.5%** | not admitted; scored forward. Round 9 called it "a lower dial in disguise": right on Sharpe, but at equal volatility it cuts the deepest losses |
| K4 + GK | +0.12 (p 0.23) | 3 of 4 | +0.05 | +53.0%/yr, worst month −12.2% | not admitted |

Note: GK passes the bar fixed in advance. With a strict correction for this
round's six tests (Bonferroni) it would not (0.017 > 0.008). It is admitted
on the rule we set before looking, and the forward tournament keeps scoring
it beside the others.

### The new "self-adjusting" ideas

| idea | the logic | result |
|---|---|---|
| **B1 a volatility clock ("proper time")**: lookbacks measured in the market's own time; fast markets shorten them, quiet markets lengthen them | subordination theory (Clark 1973): markets run on information time, not the calendar | ❌ **fails clearly**: worst month −28.9% vs −17.4%, max DD 54% vs 42%. Shortening lookbacks in fast markets whipsaws the book |
| **B2 ex-ante risk**: size by the forecast risk of the book held now (coin volatilities and correlations) instead of last 60 days' realised risk | the risk you hold, not the risk you held | Sharpe +0.00; **worst month −11.8% vs −17.4%** at equal volatility. Not admitted; scored forward |

---

## 3. What the bot does differently now (C521)

**The book is already "relativistic", and that is why it works.** Every
decision is relative:
- each coin is sized in its own volatility units;
- momentum is ranked against the other coins, net of the market's move (residual);
- carry is ranked against other coins' funding;
- the whole book is held at a volatility target.

Round 14 adds the one adaptive piece that passed:

1. **Range volatility (GK) is now how the traded book measures each coin's
   risk** (`C488_VOL_EST='gk'`). It uses the full daily range, so it is about
   five times more statistically efficient than closes alone (Garman & Klass
   1980) and reacts faster. The next rebalance (3 Oct, 05:35 IST) moves to it.
   To undo: `OMEGA_VOL_EST=close`.
2. **The tournament now scores 9 rules.** New: "range vol + drawdown loop"
   and "range vol + ex-ante risk". K4 was already there. If the forward test
   confirms their tail cut, they come up for the December refresh.
3. **BFUSD (paper).** The whole futures wallet earns Binance's BFUSD reward
   rate while the book trades, against Savings, which only earns on idle cash.
   - At $500: about **$3.19/month vs $1.72** (+0.3%/month).
   - BFUSD's rate has no public API (the page renders it in the browser), so
     it is a setting: **7.66% base** (Sep 2026; 9.51% boosted shown, not
     booked). Please read the current figure in the app monthly, as with
     Savings.
   - The 1% TDS on converting USDT is withheld once ($5, creditable); it is
     paid back in about 3 months.
   - Risks: BFUSD is not a stablecoin; its yield comes from Binance's hedged
     strategies.
4. **Delta Exchange India (paper, $500, the SAME plan).** At every rebalance
   it gets the book's raw plan and holds it on Delta's contracts, at Delta's
   prices, funding and fees (0.05% + 18% GST). It names coins Delta doesn't
   list and targets under one contract. If your server's rebalance already
   ran today, it starts within a minute of the update. What we measured
   first (last 120 days):
   - Delta lists **55 of the book's 80 candidates**.
   - **Prices track Binance closely** (median correlation 0.994; BTC, ETH,
     SOL almost perfectly; small coins 10–27%/yr of tracking noise).
   - **Funding does NOT track:** Delta's is a median +5.6%/yr dearer for a
     long, ranging from −60% to +50% by coin, correlation only 0.40.
     *(C523 correction, same day: Delta's funding value was read one
     interval late. With the value set at each exchange it is +5.7%/yr,
     correlation 0.44, the same range: the conclusion stands. See
     `reports/2026-10-02_c521_screens_c522.md` §6.)* The
     carry part of the book (ranked on Binance's funding) will earn something
     different on Delta. The paper book measures what that costs.
   - **Whole contracts hold 93% of the plan at $500** (98% at $1,000). The
     earlier "needs $1,000" was too cautious.

---

## 4. What the mathematics says about your target

- **Kelly:** at the backtest Sharpe, full Kelly would run at 174% volatility;
  dial 20% runs at 29%, **one sixth of Kelly** (one quarter at the haircut
  Sharpe). That is deliberately safe: estimation error makes anything above
  half-Kelly reckless. **No dial change.**
- **How long until the record proves anything:** about **11 months** of
  results to show the edge is real at 95% confidence if the true Sharpe is
  the backtest's, about **24 months** if it is the haircut one. Paper weeks
  and months are noise. Judge over 1–2 years.
- **Realistic expectation** (plateau median 1.5, one-third haircut, about
  1.0–1.2): averaging 2%/month over a year is likely but not certain, and
  80% of single months above 2% is not reachable by any honest strategy
  (round 13's arithmetic).

---

## 5. Update the server, then Ubuntu

Do this outside 05:30–06:00 IST (the rebalance, carry and spot runs).

**Step 1: pull C521**
```bash
sudo -u omega git -C /home/omega/omega pull
curl -s "https://api.india.delta.exchange/v2/tickers?contract_types=perpetual_futures" | head -c 150; echo
```
The second line should print the start of Delta's price list (`{"meta":...`
or `{"result":...`). That confirms your server can reach Delta.

**Step 2: Ubuntu updates** (security and package updates only; no release upgrade)
```bash
sudo apt update
sudo NEEDRESTART_MODE=a apt full-upgrade -y
sudo apt autoremove -y
cat /var/run/reboot-required 2>/dev/null || echo "no reboot needed"
```

**Step 3a: if it says a reboot is required**
```bash
sudo reboot
```
Wait about a minute, reconnect, then:
```bash
sudo systemctl status omega cloudflared-quick --no-pager | grep -E "Active|omega|cloudflared"
sudo journalctl -u cloudflared-quick | grep -o 'https://.*trycloudflare.com' | tail -1
```
**The dashboard address changes after a reboot** (a quick tunnel gets a new
one); the second line prints the new address.

**Step 3b: if no reboot is needed**
```bash
sudo systemctl restart omega
```

**Step 4: check**
```bash
sleep 90
sudo journalctl -u omega -n 300 --no-pager | grep -E "OMEGA C5|venue|Loaded state|C521|BFUSD|Delta|Traceback" | cut -c1-300
```

**What you should see:**
- `OMEGA C521`;
- `venue: BINANCE`;
- `Loaded state: $49x.xx`;
- the PAPER line ending with "BFUSD wallet at 7.66% (C521) · the same plan
  on Delta Exchange India, $500 (C521)";
- within a minute or two, `C521 Delta Exchange India (paper, same plan): N
  held ...`;
- no Traceback.

The dashboard shows two new panels, **BFUSD** and **Delta Exchange India**,
and the tournament lists 9 rules with "N2+N3, range vol (traded)".

**Not now:** `do-release-upgrade` (Ubuntu 26.04). A major upgrade changes
Python and could break the bot's environment. Plan it separately.
**Optional:** the "Expanded Security Maintenance" note can be enabled free
for personal use with an Ubuntu Pro token (`sudo pro attach <token>`).
**Harmless:** "1 zombie process".

---

## 6. Next

- **Paper check (3 Oct, after 05:35 IST):** the first rebalance on range vol;
  the Delta book's first full day (fills against Delta's real prices, funding
  at 05:30/13:30/21:30 IST); BFUSD's first day.
- **Live money** still waits for the CA's tax answer. `C488_LIVE_OK` stays False.
- **December refresh:** the forward record of K4, the drawdown loop and
  ex-ante risk; GK's first months.
