# Mudrex, CoinSwitch and every other Indian exchange, re-checked (Round 22b and 22c)

9 Oct 2026. You asked: "what about testing mudrex and coinswitch and any other exchange you might have missed ? if
the data is behind a key , i can create an api key for you to test ...". After the server check (13:06 IST) you
added: "please proceed accordingly intelligently so that the best possible combination of exchanges is selected in
terms of average monthly returns".

## 0. The result (part 2, 9 Oct afternoon)

**Delta + CoinDCX stays your plan. It is the best combination of every exchange that can be tested.**

**What your server found** (13:04 IST, one moment, 762 coins):
- **CoinSwitch's rent = Bybit's predicted rent for 100% of 762 coins.** So CoinSwitch is confirmed as a Bybit
  photocopy.
- Against Binance, only 62% match.
- CoinSwitch has 763 coins: 180 also on Delta, 457 also on CoinDCX.
- Bybit's history came down cleanly: 476 coins, 1.33 million rent payments, 0 errors.

**The test, exactly as written before** (two years, costs ×5, 10 pairs of 10%, after tax at 31.2%;
`research/c542b_pairs.txt`):

| pair | coins | a month before tax | worst month | after tax (T1) | normal costs, after tax | passes? |
|---|---|---|---|---|---|---|
| **Delta + CoinDCX (your plan)** | 72 | **+5.20%** | −2.25% | **+3.58%** | **+4.18%** | **yes** |
| Delta + Mudrex (Bybit's rent) | 66 | +4.77% | −2.16% | +3.28% | +3.85% | no: without its best coin, one month falls to −4.6% |
| Delta + CoinSwitch (Bybit's rent) | 66 | +4.73% | −2.27% | +3.25% | +3.84% | no: same reason |
| CoinDCX + Mudrex (Binance vs Bybit) | 222 | **−4.61%** | −10.3% | — | −1.37% | no: it loses every month |
| CoinDCX + CoinSwitch | 226 | **−4.77%** | −10.5% | — | −1.40% | no: it loses every month |

**The "best of both" combination** (`research/c542c_best.txt`). Each coin's second leg went to whichever of CoinDCX
or CoinSwitch paid the wider gap. Three accounts; generous, because the two rupee accounts were pooled as one:

| | a month before tax | after tax (T1) | normal costs, after tax |
|---|---|---|---|
| Delta + CoinDCX alone | **+5.25%** | **+3.61%** | **+4.21%** |
| Delta + the better of CoinDCX / CoinSwitch, coin by coin | +5.10% | +3.51% | +4.16% |
| the same with Mudrex in CoinSwitch's place | +5.12% | +3.52% | +4.17% |

**Even the generous version earns less than your plan alone,** so the three-account idea is dropped.

### Why, in plain words

1. **Binance's and Bybit's boards almost always show the same numbers.**
   - The typical gap between them is about 3.6% a year, far below the 20% the trade needs to enter.
   - Big professional traders keep those two boards in line.
   - The few big gaps appear on wild coins (H, RIVER, COAI), where the two prices also jump apart (H once differed by
     120% in a day). The price swings eat the rent.
   - **Analogy:** two shops that copy each other's prices. The only days they differ are days when one shop is on fire.
2. **Delta's board is the odd one out. It differs from Bybit's slightly more often than from Binance's** (a 27.0% a
   year typical gap vs 24.9%). Yet the Delta + Bybit-copy pairs earned less:
   - six of your plan's coins can't be paired there:
     - AIN, AIOT and TST aren't on Bybit;
     - LIT is on Bybit but not on CoinSwitch or Mudrex;
     - PUMP and SKYAI are listed under other names ("PUMPFUN", "SKYAI1"), which the test did not match. Adding PUMP
       could not close the gap: the Bybit pairs trail by about 0.3% a month after tax, and a switch needs them to lead
       by 0.5%;
   - the Bybit pairs are fragile. One coin sitting at the $100k-a-day cutoff (EDEN) moved the CoinSwitch result by 0.6%
     a month just by entering the list;
   - H, the coin with four +100% days in a year, is their biggest loser (Round 23, 22 Oct, deals with such jumps).
3. **"Pick the better board per coin" doesn't help either.**
   - Picking whichever of two noisy numbers is higher tends to pick the noise. **Analogy:** choosing the shop with the
     bigger "sale" sign; the biggest signs are often mistakes that are corrected the next day.
   - Costs and price noise then eat the small extra.

### What this means for you

- **Nothing changes** in the bot, the plan, the timeline or your CA question (it stays about CoinDCX).
- **Delete the CoinSwitch key now.** CoinSwitch did not win. Steps are in section 8.
- **No Mudrex key is needed.** Mudrex lost on the numbers, with or without a key.
- **The search is now complete for every Indian exchange a bot can use.** Delta, CoinDCX, ZebPay, Pi42 (blocked),
  Mudrex and CoinSwitch are tested. WazirX, Giottus, Cosmic, SunCrypto, Bitbns and KoinBX can't be tested (no API).
- If any of them opens an API, or Delta's or CoinDCX's fees change, the monthly review will flag it.

## 8. Removing the CoinSwitch key

1. **On the CoinSwitch PRO website:** Profile → API Trading → revoke (delete) the key.
2. **On the server**, remove it from the key file. This prints only the names of the sections left, never a key:

```
sudo -u omega python3 -c "import json,os;f='/home/omega/omega/data/api_keys.json';d=json.load(open(f));d.pop('coinswitch',None);t=f+'.tmp';fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600);os.write(fd,json.dumps(d,indent=1).encode());os.close(fd);os.replace(t,f);print('removed coinswitch; sections left:',sorted(d))"
```

**What you should see:** `removed coinswitch; sections left: ['coindcx', 'delta_india', 'pi42']`. The Pi42 key can
also go; delete it on Pi42's site whenever convenient.

---

# Part 1 (9 Oct morning): the census and the method

## 1. The short answer

**Mudrex is not a separate market. It is a shop-front on Bybit's market. I proved this from public data.**
- I compared Mudrex's public price candles with every trade Bybit published for 7 Oct.
- For LINK and AVAX, **181 of 181 minutes have the same closing price, and the volume is the same to the coin**.
- Against Binance only 30 and 12 of 181 match.

**CoinSwitch's futures almost certainly sit on Bybit too.**
- Several fingerprints match, below.
- Everything it publishes, prices included, needs a key, so I could not prove it.

**Why this matters.**
- Think of each exchange's rent rates as a notice board:
  - **Delta India writes its own board.**
  - **CoinDCX, ZebPay and Pi42 photocopy Binance's board.**
  - **Bybit writes its own board too**, a third one. Mudrex (and probably CoinSwitch) show Bybit's board.
- Your profit comes only from the difference between two boards. A third board means two new pairs that nobody has
  tested yet:
  1. **Delta vs Bybit:** Delta + Mudrex, or Delta + CoinSwitch.
  2. **Binance vs Bybit:** CoinDCX + Mudrex. Both accounts would be rupee accounts on Indian exchanges, with no Delta
     at all.

**What I cannot do from here.**
- Bybit blocks the country my research computer is in, so I can't download Bybit's rent history.
- **Your server in Mumbai can.** I wrote a small read-only script for it (section 5).
- Your keys are the only way to confirm that Mudrex's and CoinSwitch's own rent numbers are Bybit's.

**The test rules were written and pushed first** (`research/c542b_preregistration.md`):
- the same history, costs ×5 and bars as Round 22;
- **the plan moves away from Delta + CoinDCX only if a new pair beats it by at least +0.5% a month after tax.**

Until then, nothing in your plan changes.

## 2. How I found Mudrex = Bybit

**Analogy:** two shops sell the same thing at the same price, minute by minute, and their sales add up to exactly
the same amount. They are not two shops. One is a counter inside the other.

| test (7 Oct, 06:00-09:00 UTC, one-minute candles) | LINK | AVAX |
|---|---|---|
| Mudrex's close = Bybit's last trade | **181 / 181** | **181 / 181** |
| Mudrex's volume / Bybit's volume | **1.000** | **1.000** |
| Mudrex's close = Binance's | 30 / 181 | 12 / 181 |
| Mudrex's close = OKX's | 10 / 181 | 15 / 181 |

- **Mudrex lists 468 coins.** I found them through its public candles. **180 of them are also on Delta.**
  CoinDCX has 191 in common with Delta.
- **Its fee:** 0.05% + 18% GST with rupee margin, the same as CoinDCX.
- **Its rent number** (`funding_fee_perc`) is in a list that needs a key.

**CoinSwitch's fingerprints:**
- it calls itself an aggregator that trades "on third-party exchanges";
- its futures exchange code is `EXCHANGE_2`;
- its price data has exactly Bybit's fields;
- its fast-trading API sits under `/v5`, Bybit's address scheme, and replies in Bybit's error format;
- its listed fees (0.065% / 0.024%) are Bybit's 0.055% / 0.02% plus 18% GST.

## 3. Every other exchange, checked again

| exchange | rupee futures? | can a bot read its rent? | result |
|---|---|---|---|
| Delta India | yes | yes | **its own board** (your plan) |
| CoinDCX | yes | yes | Binance's board (your plan) |
| ZebPay | yes | yes | Binance's board |
| Pi42 | yes | blocked to everyone | Binance's board |
| **Mudrex** | yes (INR margin) | **key needed** | **Bybit's board** (proved from prices) |
| **CoinSwitch** | yes (INR accounts) | **key needed** | Bybit's board, very likely |
| WazirX | yes, since May 2026 | no API | cannot be tested |
| Giottus | perpetuals since Aug 2025 | no API found | cannot be tested |
| Cosmic, SunCrypto | — | no API found | cannot be tested |
| Bitbns | — | API last documented 2022 | cannot be tested |
| KoinBX | futures announced | spot API only | cannot be tested |
| Bybit, KuCoin, Binance (offshore) | USDT accounts | yes | not rupee accounts. Bybit's board is reachable in rupees through Mudrex. |

**The miss is fixed.** In Round 22, Mudrex and CoinSwitch were set aside as "rates behind a key". I should have
looked at what Mudrex does publish (its prices). That is how it turned out to be Bybit.

## 4. Tax (the same caution as CoinDCX)

- **Mudrex's fee page** lists no TDS on futures and says "taxation for INR and USDT futures remains unchanged".
- **One of Mudrex's own FAQs** says the 30% crypto-asset rule applies.
- **So it is uncertain until a CA rules**, exactly like CoinDCX.
- If Mudrex or CoinSwitch wins, your CA question simply names that exchange as well.

## 5. What I need from you

**Update, 9 Oct: you chose not to make a Mudrex key.** That is fine for now:
- Mudrex's two-year test runs on Bybit's history, which the price proof shows is Mudrex's market.
- A Mudrex key is needed **only if Mudrex wins**. It would then confirm, before any switch, that Mudrex pays exactly
  Bybit's rent. Live trading would need a key anyway. Until then, the rule "its key reads from your server" keeps
  Mudrex from replacing CoinDCX on the price proof alone.
- Only the CoinSwitch key is made now.

There are two parts. **Part B works even without the keys**: Mudrex can then be tested on the proof from its prices.
CoinSwitch can be tested only with its key.

### Part A (optional, but it confirms the rent numbers): create the two keys

**Be aware first:**
- **Neither Mudrex nor CoinSwitch offers a "read only" key, or locking a key to your server's address**, in its
  documentation. Their keys could trade.
- So:
  1. **keep no money in either account** (with no money, a key can do nothing);
  2. **delete both keys after the test**, unless one of them wins;
  3. **never paste a key into chat or a screenshot.**
- Both need KYC and an authenticator app (2FA) first.

**Mudrex** (website):
1. Log in, then: PAN and Aadhaar verified (DigiLocker), and 2FA (authenticator app) on.
2. Go to **API Trading**, give the key a name (`omega-test`), then **Generate Key**. It allows one key per account.
3. It shows the **API key** and the **secret** once. Keep that screen open for the next command.

**CoinSwitch** (CoinSwitch PRO website):
1. Log in, then go to **Profile → API Trading → generate a new key pair**. Only one pair can be active at a time.
2. It shows the **API key** and the **secret key** (long hex strings) once. Keep that screen open.

**Save each one on the server, without showing it** (Termius):

```
sudo -u omega git -C /home/omega/omega pull
sudo -u omega bash /home/omega/omega/deploy/omega-keys.sh mudrex
sudo -u omega bash /home/omega/omega/deploy/omega-keys.sh coinswitch
```

Paste the key, press Enter. Paste the secret, press Enter. Nothing appears on screen, and that is normal. It answers
only with the lengths.

### Part B: run the server check (about 5 minutes)

```
sudo -u omega git -C /home/omega/omega pull
sudo -u omega /home/omega/omega/venv/bin/python /home/omega/omega/research/c542b_server.py
sudo -u omega /usr/local/bin/omega-logpush.sh
```

**What it does** (it only reads; it cannot place an order):
- downloads Bybit's rent history and daily prices for about two years;
- reads Mudrex's and CoinSwitch's rent lists, if their keys are saved;
- compares them with Bybit's and Binance's at the same moment;
- sends the results to GitHub with your logs, keys scrubbed out.

**What you should see:**
- a line like `Mudrex (as a fraction) vs Bybit predicted: 9x% of 4xx coins within 0.002%`. That would confirm the
  photocopy.
- **"Bybit did not answer the server"**: Bybit blocks your server too. Tell me, and I'll find another way.
- **"HTTP 401"** on Mudrex or CoinSwitch: the key was typed wrong. Run that `omega-keys.sh` line again.

A screenshot of the output is enough. I'll take the files from GitHub.

## 6. What happens after you run it

**I run the test exactly as written:** `research/c542b_pairs.py`, Round 22's engine. Two years, costs ×5, and the
pairs:

| pair | the rent gap | accounts |
|---|---|---|
| **C (today's plan)** | Delta vs Binance | Delta + CoinDCX |
| **M** | Delta vs Bybit | Delta + Mudrex |
| **S** | Delta vs Bybit | Delta + CoinSwitch |
| **CM** | Binance vs Bybit | CoinDCX + Mudrex |
| **CS** | Binance vs Bybit | CoinDCX + CoinSwitch |

**A new pair replaces Delta + CoinDCX only if all of these hold:**
- it passes every Round 22 bar;
- it makes **at least +0.5% a month more after tax** than CoinDCX, at both cost levels;
- its key reads from your server;
- you agree to use that account.

**Why that margin:** switching costs a move (fees on both sides), another KYC'd account and another CA question. A
small win on old data is not worth that.

**My honest expectation, before the numbers:**
- Big traders keep Bybit's and Binance's boards close to each other, so CoinDCX + Mudrex (Binance vs Bybit) is
  probably a thin gap.
- Delta + Mudrex is the real contender. Delta's board is the odd one out, whichever board you compare it with. The
  numbers will decide.

**I tested the analysis script before you run anything.**
- I fed it Binance's history in Bybit's place. It then reproduced today's plan exactly: 75 coins, +5.42% a month
  before tax and +3.73% after.
- So the bar a new pair must clear is **+4.23% a month after tax** (+3.73% + 0.50%).
- Both engine checks pass. All 62 tests pass.

## 7. Does this change the timeline?

- **No.** This test fits before B2 (the order path, 15 Nov), which is the last point where changing the second
  exchange is cheap.
- **If a new pair wins**, the plan moves in paper the same way it moved from Pi42 to CoinDCX, and your CA question
  names that exchange too.
- **No money moves before 1 February** in any case.
