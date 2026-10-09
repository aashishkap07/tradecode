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
- **Period:** 5 Oct 2026 → 20 Feb 2027, about 4½ months, from the plan's
  ledger in the server's logs (Delta vs Pi42 until 8 Oct, then Delta vs
  CoinDCX: the same ledger, the move's fees booked in it).
- **Pass:**
  - average **≥ +1.5% a month before tax**, after all fees and GST (the
    research's cautious case was about +2.3% before tax; its planning case
    +4.2%);
  - **no month below −4%**;
  - **neither account ever below 40%** of its half, with the even-outs.
- **Partial pass:** an average of +0.5% to +1.5% a month, or one month below
  −4% → start at **$500**, not $1,000.
- **Fail:** an average under +0.5% → **no live in March**. Write up why.

**G2. The second exchange still copies Binance's funding** (9 Oct: the second
exchange is now CoinDCX, C542; the test is unchanged; `research/c541_coindcx_check.py`;
8 Oct: 191 of 191 coins identical)
- **Pass:** every monthly check shows **≥ 80%** of coins within 0.002%.
- **Fail:** two checks under 80% → the ledger's second-exchange figures can't
  be trusted. Rethink before live.

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

**G6. Added 9 Oct 2026 (stricter only, after C542):**
- **Tax** (rewritten 9 Oct at the operator's request: "i dont have a dedicated CA..please act as an expert CA
  everytime a taxation question arises"; was "a CA confirms in writing"). All three must hold:
  - (a) the written tax opinion `reports/2026-10-09_tax_opinion.md` (Claude as the operator's tax adviser, not a
    registered CA) still concludes speculative business income for both legs, netted;
  - (b) the operator **explicitly accepts at the go/no-go** the residual risk stated there in numbers: on today's list
    +3.71% a month after tax under that reading; +0.23% if only the CoinDCX leg were a VDA; **−2.95% if both legs
    were** (about Rs 60,000-80,000 of extra tax in a full year at $1,000);
  - (c) **no adverse change by 20 Feb**: no CBDT circular or notification, and nothing in the Finance Bill 2027 (Budget
    1 Feb), treating INR-settled crypto derivatives as VDAs. If one appears, G6 fails until re-assessed.
  - This relaxes the tax part in one respect: there is no third-party signature. It is recorded here openly. The
    numbers in (b) make the risk explicit instead of hiding it.
- **One-coin jumps:** Round 23's protection is built into the order path and
  tested (BLESS +530% on 15 Oct 2025 would empty an account).
  - **Amended 10 Oct 2026 (Round 24, stricter):** the protection must be tested on **1-minute mark prices**,
    including the 10–11 Oct 2025 crash. The live accounts use **cross margin on both exchanges**, plus the C546 cap
    (at most 6 of 10 pairs facing one way).
  - The original wording was "each leg on its own (isolated) margin, the other leg closed at once". On minute data,
    isolated margin of 1/3 or 1/2 per leg would have liquidated 9–10 legs on 10 Oct 2025, while cross margin
    survived every replayed day (`reports/2026-10-10_round24_screens.md`). The change is recorded here openly.

**Go / no-go: 20–25 Feb 2027.** If G1–G6 pass, the live lock opens for the
funding trade only, on **1 March 2027**.

## 3. What gets built, and when

Every step below runs in paper or dry-run until G1–G6 pass.

| when | step | what you'll need to do |
|---|---|---|
| 5 Oct | check the first Delta-vs-Pi42 run (scheduled) | nothing |
| from 8 Oct | **B1: read-only connections. DONE 8 Oct (C540).** Signed GET requests to both exchanges that read your balance, positions, fills and funding paid; anything else refused in code. Built and tested against the docs' examples; Delta's real server checked with a fake key. Note: Delta's docs say reading wallets/positions needs its 'Trading' permission (IP-locked): try Read Data first, else by B3. | **done 8–9 Oct:** Delta's and CoinDCX's read-only keys are saved and read every 10 minutes (CoinDCX first read 9 Oct 00:04 IST) |
| 8 Oct | **Done: the second exchange is CoinDCX** (Round 22 re-checked every Indian exchange: Delta + CoinDCX is the best pair, +3.55% a month after tax at costs x5, +4.15% at normal costs; `reports/2026-10-08_c542_best_pair.md`). Pi42 is shut to every network. The plan moved to CoinDCX in paper (C542); CoinDCX answers your server (401 JSON). | make the CoinDCX read-only key (report section 8; done 9 Oct); tax: no CA, see item 5 |
| 22 Oct | **Round 23 (C547; C544-C545 are the tax journal and statement, C546 Round 24's one-way cap): protection against one coin jumping several times over in a day** (BLESS +530% on 15 Oct 2025 would empty one account): each bet on its own margin, the twin closed at once, a coin filter. Needed before real money, and before any setting bigger than 10 pairs of 10% | nothing |
| 1 Nov | monthly review, gates G1/G2 so far | nothing |
| from 15 Nov | **B2: the order path.** Open and close **both legs together**: whole Delta contracts, CoinDCX's quantity steps, **cross margin** on both exchanges (Round 24; was "isolated margin per leg"). If one leg fails, the other is undone at once. Exits are reduce-only. Plus the kill switch, and checking the exchanges' positions against the ledger every hour. | nothing |
| 28 Nov | **end-November paper review** (about 8 weeks of record) | read it |
| 1–2 Dec | monthly review + the research refresh | nothing |
| from 15 Dec | **B3: dry run on your server.** Every day the bot builds the real orders, logs them, sends none, and compares them with paper. The phone alert for "move money NOW" is set up here, and the account-health check runs **every 5 minutes** (hourly in paper; C537: deciding stays once a day, watching gets faster). | choose the alert channel (Telegram or similar) |
| 1 Jan | monthly review | nothing |
| 1 Feb | monthly review; **pilot setup** | deposit **$100 a side** (~₹10,200 on CoinDCX at its ₹102 rate); a **trading** key on each exchange, IP-locked to the server (withdrawals stay off) |
| 2–20 Feb | **B4: the pilot**, small real money | do one rupee transfer between the exchanges when the bot asks |
| 20–25 Feb | **go / no-go** against G1–G6 | decide |
| 1 Mar 2027 | **live**: $500 a side | top up to $500 a side |

**Each scheduled step fires into this session, which is in ultracode.**
- Before working, each one checks that ultracode is still on.
- If it isn't, it sends you a prompt to switch, and waits for you.

## 4. Things only you can do (no rush before the dates above)

1. **Accounts:**
   - KYC complete on **Delta Exchange India** and **CoinDCX** (done by 8 Oct;
     Pi42 is no longer needed);
   - your bank linked to both for rupee deposits and withdrawals;
   - 2FA on.
2. **Keys** (when asked): create them on each exchange's website and lock
   them to your server's IP.
   - Never enable withdrawals.
   - Never paste a key into chat or the code. Copy it onto the server into
     `data/api_keys.json` (steps will be given).
3. **Tax records** (speculative business income, ITR-3):
   - The bot journals every trade (C544), and `omega_tax_statement.py` makes the yearly statement, complete for filing
     (C545: every ITR-3 field, the 31 March balances, losses carried forward, a handover pack). A filing CA copies it
     into ITR-3; the operator fills in nothing (`reports/tax/README.md`).
   - Keep the exchanges' own statements too; from B3 the statement also checks itself against them.
4. **Money:** about **₹1 lakh** in total for March (~₹51,000 on CoinDCX at its
   ₹102 rate, and Delta's own rate for the other $500), plus ~₹20,000 for the
   February pilot.
5. **Tax (G6):** no CA (the operator's choice, 9 Oct). Claude acts as the tax adviser:
   `reports/2026-10-09_tax_opinion.md` (speculative business income, ITR-3 Schedule BP, both legs netted). The
   operator accepts or rejects its residual risk at the go/no-go. Tax dates: ITR-3 for tax year 2026-27 by 31 Jul
   2027; advance tax for 2027-28 on 15 Jun, 15 Sep, 15 Dec 2027 and 15 Mar 2028; 31.2% of each month's net profit
   set aside from the pilot on.
