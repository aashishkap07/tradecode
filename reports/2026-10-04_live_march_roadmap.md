# The road to live money by March 2027 (written 4 Oct 2026, before any of it is measured)

**Your goal:** if everything goes to plan, start live trading in **March 2027,
and no later**. This page is the plan to get there.

- It sets the tests ("gates") the paper record has to pass. They are written
  now, before the results exist, so they can't be bent later to fit the
  numbers.
- It sets the order in which the real-money code gets built.
- It lists what only you can do.

**What goes live:** only **your plan**, the Delta Exchange India vs Pi42
funding trade, $1,000 ($500 on each exchange). The books, carry, spot pot and
the other ledgers stay experiments.

---

## 1. Can it be done? Checked on 4 Oct

| need | Delta Exchange India | Pi42 |
|---|---|---|
| a trading API | yes, `api.india.delta.exchange` (HMAC keys) | yes, `fapi.pi42.com` (HMAC-SHA256); orders `POST /v1/order/place-order`, positions `GET /v1/positions/OPEN`, wallet `GET /v1/wallet/futures-wallet/details` |
| keys that can trade but not withdraw | permissions "Read Data" and "Trading" | trading permissions set per key |
| key locked to your server's IP | **required** for trading keys | IP allow-list endpoints exist |
| our $100 legs above the minimum order | 1 whole contract (already modelled) | minimum order **₹546 (~$5)** on 178 of 205 rupee perps; ETH ₹2,200; BTC ₹10,994 |
| rupee margin | rupees at Delta's own rate | **₹102 per USDT** (`conversionRates`) |

**Funding data:**
- Pi42's REST docs list no funding-history endpoint.
- Its live funding is on its public websocket.
- At every check and review I compare it with Binance's (4 Oct: 87%, then
  **91%** of 246 coins within 0.002%).
- The pilot (section 3) will show the real rupees credited.

**Answer: yes.** Both exchanges allow exactly the safe setup we use: trade-only
keys, withdrawals off, locked to your server's IP.

## 2. The gates: all must pass by 20 Feb 2027 for a 1 March start

**G1. The paper record**
- **Period:** 5 Oct 2026 → 20 Feb 2027, about 4½ months, from the
  Delta-vs-Pi42 ledger in the server's logs.
- **Pass:**
  - average **≥ +1.5% a month before tax**, after all fees and GST (the
    research's cautious case was about +2.3% before tax; its planning case
    +4.2%);
  - **no month below −4%**;
  - **neither account ever below 40%** of its half, with the even-outs.
- **Partial pass:** an average of +0.5% to +1.5% a month, or one month below
  −4% → start at **$500**, not $1,000.
- **Fail:** an average under +0.5% → **no live in March**. Write up why.

**G2. Pi42 still copies Binance's funding**
- **Pass:** every monthly check shows **≥ 80%** of coins within 0.002%.
- **Fail:** two checks under 80% → the ledger's Pi42 figures can't be trusted.
  Rethink before live.

**G3. The real-money code**
- **Pass:**
  - **4 weeks of "dry run"**: the bot builds every real order, sends none,
    and every one matches the paper ledger;
  - **0 unexplained differences** between the exchanges' positions and the
    ledger;
  - the kill switch tested;
  - the full test battery green.

**G4. The pilot: small real money, Feb 2027**
- **Setup:** $100 a side ($200), at most 2 pairs, **≥ 14 days**.
- **Pass:**
  - fills within 0.1% of the mark;
  - fees + GST within 10% of the ledger's;
  - funding credited within 10% of the ledger's;
  - **one rupee transfer** between the exchanges (bank withdraw, then
    deposit) completed within 24 h, and timed.

**G5. Safety**
- **Pass:**
  - keys are trade-only, withdrawals off, IP-locked to the server;
  - the keys live only in `data/api_keys.json` (chmod 600), never in the
    Python file;
  - port 8138 stays closed;
  - the logpush scrubber still removes them;
  - a "move money NOW" alert reaches your phone within 5 minutes (tested).

**Go / no-go: 20–25 Feb 2027.** If G1–G5 pass, the live lock opens for the
funding trade only, on **1 March 2027**.

## 3. What gets built, and when

Every step below runs in paper or dry-run until G1–G5 pass.

| when | step | what you'll need to do |
|---|---|---|
| 5 Oct | check the first Delta-vs-Pi42 run (scheduled) | nothing |
| from 8 Oct | **B1: read-only connections. DONE 8 Oct (C540).** Signed GET requests to both exchanges that read your balance, positions, fills and funding paid; anything else refused in code. Built and tested against the docs' examples; Delta's real server checked with a fake key. Note: Delta's docs say reading wallets/positions needs its 'Trading' permission (IP-locked): try Read Data first, else by B3. | by about 1 Nov: create a key on each exchange, locked to the server's IP, and save it with `deploy/omega-keys.sh` (steps: `reports/2026-10-08_b1_read_only.md`) |
| 1 Nov | monthly review, gates G1/G2 so far | nothing |
| 8 Oct | **Done: the second exchange is CoinDCX** (Round 22 re-checked every Indian exchange: Delta + CoinDCX is the best pair, +3.55% a month after tax at costs x5, +4.15% at normal costs; `reports/2026-10-08_c542_best_pair.md`). Pi42 is shut to every network. The plan moved to CoinDCX in paper (C542); CoinDCX answers your server (401 JSON). | make the CoinDCX read-only key (report section 8); ask a CA to confirm CoinDCX's rupee-margin futures are business income |
| before B2 | **Round 23: protection against one coin jumping several times over in a day** (BLESS +530% on 15 Oct 2025 would empty one account): each bet on its own margin, the twin closed at once, a coin filter. Needed before real money, and before any setting bigger than 10 pairs of 10% | nothing |
| from 15 Nov | **B2: the order path.** Open and close **both legs together**: whole Delta contracts, CoinDCX's quantity steps, each leg on its own (isolated) margin. If one leg fails, the other is undone at once. Exits are reduce-only. Plus the kill switch, and checking the exchanges' positions against the ledger every hour. | nothing |
| 28 Nov | **end-November paper review** (about 8 weeks of record) | read it |
| 1–2 Dec | monthly review + the research refresh | nothing |
| from 15 Dec | **B3: dry run on your server.** Every day the bot builds the real orders, logs them, sends none, and compares them with paper. The phone alert for "move money NOW" is set up here, and the account-health check runs **every 5 minutes** (hourly in paper; C537: deciding stays once a day, watching gets faster). | choose the alert channel (Telegram or similar) |
| 1 Jan | monthly review | nothing |
| 1 Feb | monthly review; **pilot setup** | deposit **$100 a side** (~₹10,200 on Pi42); turn on **trading** permission on both keys (withdrawals stay off) |
| 2–20 Feb | **B4: the pilot**, small real money | do one rupee transfer between the exchanges when the bot asks |
| 20–25 Feb | **go / no-go** against G1–G5 | decide |
| 1 Mar 2027 | **live**: $500 a side | top up to $500 a side |

**Each scheduled step fires into this session, which is in ultracode.**
- Before working, each one checks that ultracode is still on.
- If it isn't, it sends you a prompt to switch, and waits for you.

## 4. Things only you can do (no rush before the dates above)

1. **Accounts:**
   - KYC complete on **Delta Exchange India** and **Pi42**;
   - your bank linked to both for rupee deposits and withdrawals;
   - 2FA on.
2. **Keys** (when asked): create them on each exchange's website and lock
   them to your server's IP.
   - Never enable withdrawals.
   - Never paste a key into chat or the code. Copy it onto the server into
     `data/api_keys.json` (steps will be given).
3. **Tax records** (speculative business income, ITR-3):
   - The bot's ledger will export a yearly profit statement.
   - Keep the exchanges' own statements too.
4. **Money:** about **₹1 lakh** in total for March (~₹51,000 on Pi42 at its
   ₹102 rate, and Delta's own rate for the other $500), plus ~₹20,000 for the
   February pilot.
