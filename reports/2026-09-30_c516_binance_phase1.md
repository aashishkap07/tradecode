# C516: phase 1 of the move to Binance (paper), 30 Sep 2026

## Your question: "$500–1,000 in each of spot and futures?"

**No. All of it goes to futures; nothing goes to spot for the bot.**
- **Where the money goes:** the bot's money sits in the **USDⓈ-M futures
  wallet**, ideally inside a Binance sub-account made just for the bot.
- **Why no spot:** on Binance, Indian users pay **1% TDS on every spot
  sale**. The spot pot sells a little every day, so it stays paper (see
  below).
- **Your own coins:** your own spot holdings are yours; the bot never reads
  or touches them.

**How much: $500 is the best starting point.**

| futures capital | on Bitget | on Binance | why |
|---|---|---|---|
| $250 | +4.0%/mo | +3.6%/mo | Binance's $50 BTC minimum (and $83 step) keeps BTC out on 89% of days |
| **$500** | +4.0%/mo | **+3.9%/mo** | about equal |
| $1,000, 20 coins | +4.0%/mo | +4.1%/mo | Binance ahead |
| $1,000, 40 coins (what the bot would actually do) | +3.5%/mo, DD 48% | +3.7%/mo, DD 48% | from $1,000 the bot widens to 40 coins, which was weaker on this data |

These are backtests on the 2020–26 Binance history, before the usual ⅓
real-life haircut (`research/c515_venue_cost.txt`).
- The 40-coin switch at $1,000 needs its own look before anyone funds
  that much. It is recorded in the Atlas.
- At $500 the book keeps the 20-coin design that has been tested.

---

## What C516 does

**One setting, `OMEGA_VENUE=binance`, moves everything to Binance's public
data.**
- **The default stays Bitget:** pulling C516 changes nothing on your
  server until you set it.
- **Live is blocked on Binance.** With this setting the bot will not trade
  live money, whatever `C488_LIVE_OK` says: live mode on Binance does not
  even connect. The Binance live order path is phase 2.

| part | on Binance |
|---|---|
| exchange connection | ccxt `binanceusdm`, no API key (paper reads public data only) |
| the book's prices | bid/ask, last price, funding rate and 24 h volume for every USDT perpetual (3 calls) |
| contract rules | market-order step, minimum and maximum; minimum order value (BTC $50, ETH/LINK/LTC/BCH/ETC $20, rest $5); trading status; index and pre-market contracts excluded |
| daily history | 330 days in one call per coin; 200 days of funding (Binance keeps all of it; Bitget kept ~90) |
| "is yesterday final?" (C512) | the day's close must equal its 23:59 minute's close, or the rebalance waits 10 min. **Checked on Binance's own archive:** equal on BTC, 1000PEPE and ZEC |
| paper fills | at Binance's best bid/ask, at Binance's taker fee of 0.05% (Bitget 0.06%) |
| funding (paper) | on each coin's Binance schedule: 8 h, or 4 h/1 h where Binance says so |
| intraday shadow | Binance's hourly candles include buyer/seller volume for every coin and every hour, so the **full model runs from day one** (Bitget served 30 h of it, so it never did) |
| carry ledger | Binance spot prices; perp cost 0.07% |
| spot pot | Binance spot prices, 0.10% fee, $5 minimum, and **1% TDS on each sale**. The TDS is shown separately as "TDS withheld $x (creditable against your tax)" |
| safety | a book built on one venue is **never** marked, traded or charged funding on the other's prices (Bitget's PEPE is Binance's 1000PEPE). The bot says to start fresh instead |

---

## How it was tested

Binance's futures API refuses my sandbox (HTTP 451), so:
- **Real Binance data where it can be reached:**
  - Binance's archive confirmed the candle columns the code reads (quote
    volume and taker-buy volume) and the day-close = 23:59-minute rule;
  - Binance's live spot data (1,374 pairs) runs through the spot pot's code.
- **A simulated Binance** in Binance's documented reply formats: 57 checks
  in `omega_c516_test.py`, including a paper rebalance, funding, the venue
  guard, ccxt's Binance market table, the shadow, the carry ledger, the TDS
  and the page in Chromium.
- **The whole bot booted on Binance against the simulation:**
  - it connected, started fresh at $500 and made its first rebalance
    (20 trades);
  - the shadow scored 39 coins on the full 16-feature model;
  - the carry ledger ran, and the spot pot bought ETH at Binance's real
    spot price;
  - no errors.
- **Your current setup is unchanged:** the full boot on Bitget with your
  server's saved state resumed cleanly. The battery: 40 of 41 (the exit
  test needs `corpusL/`, as always).

**What only your server can prove** is the real Binance futures data. That
is `deploy/omega_binance_check.py`: **read-only**, public data, no key, and
nothing of the running bot is touched. It does everything a Binance
rebalance does up to the plan, and prints the result.

---

## The steps

**Step 1, tonight (safe: the bot stays on Bitget).** In Termius:

```bash
sudo -u omega git -C /home/omega/omega pull
sudo systemctl restart omega
sleep 90
sudo journalctl -u omega -n 200 --no-pager | grep -E "OMEGA C5|venue|Traceback"
sudo -u omega /home/omega/omega/venv/bin/python /home/omega/omega/deploy/omega_binance_check.py 500
```

- **You should see:** `OMEGA C516`, `venue: BITGET`, no Traceback.
- **Then the check:** about 1–2 minutes, ending `ALL OK`. Send me a
  screenshot of the whole check.

**Tomorrow, 05:35 IST:** the Bitget book makes the rebalance that tests C512.
Paper check #3 (06:45 IST) confirms it.

**Step 2, after that and once I've read your check: the switch.**
- It is a **fresh start**: the Bitget paper ledger is closed, and a Binance
  paper account begins at $500.
- Don't run these until I confirm the check.

```bash
sudo mkdir -p /etc/systemd/system/omega.service.d
printf '[Service]\nEnvironment=OMEGA_VENUE=binance\nEnvironment=OMEGA_CAPITAL=500\n' | sudo tee /etc/systemd/system/omega.service.d/c516-venue.conf
sudo systemctl daemon-reload
sudo -u omega touch /home/omega/omega/data/FRESH_START
sudo systemctl restart omega
sleep 120
sudo journalctl -u omega -n 300 --no-pager | grep -E "venue|Connected|Fresh start|REBALANCE|C516|Traceback"
```

**To go back to Bitget at any time:**

```bash
sudo rm /etc/systemd/system/omega.service.d/c516-venue.conf
sudo systemctl daemon-reload
sudo -u omega touch /home/omega/omega/data/FRESH_START
sudo systemctl restart omega
```

**One figure to send me:** Binance's USDT **Flexible** Savings rate. In the
app: **Earn → Simple Earn → search USDT → Flexible**; it shows the APR. The
Savings ledger still uses Bitget's 7.63%.

**Phase 2 (live on Binance)** comes after the paper book has run on Binance
and its fills and funding check out against Binance's own data, as was done
on Bitget. It needs:
- the order path;
- the sub-account and its trade-only key;
- the live checklist.
