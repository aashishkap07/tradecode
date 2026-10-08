# Mudrex, CoinSwitch and every other Indian exchange, re-checked (Round 22b, part 1)

9 Oct 2026. You asked: "what about testing mudrex and coinswitch and any other exchange you might have missed ? if
the data is behind a key , i can create an api key for you to test ..."

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
