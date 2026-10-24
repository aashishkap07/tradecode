# Income statement for ITR-3: speculative business income from rupee-settled crypto futures

**Tax year 2026-27** (01 Apr 2026 – 31 Mar 2027) · **PAPER** · edition 3 · prepared 23 Oct 2026 10:51 IST · amounts in **₹** (Delta India's fixed rate ₹85 per dollar) · year to date, cut-off 23 Oct 2026

> **PAPER — NOT FOR FILING.** This is a rehearsal on the bot's paper ledger: no real money moved, so there is no income to declare. It is kept in exactly the format the live statement will use. The live statement starts afresh, from zero, on the first real trade.

### For the filing CA — at a glance

| | |
|---|---|
| Return | **ITR-3** (business income; the trade is speculative business) |
| Business code | **21009** — Speculative trading (confirmed in the year's utility before filing) |
| P&L, no-accounts case, speculative activity | turnover **₹5,382** · gross profit **₹1,761** · expenditure **₹59** · net **₹1,701** |
| Balance sheet, no-accounts case (31 March) | sundry debtors **₹86,663** (money held by the two exchanges) · creditors 0 · stock 0 · cash 0 |
| Books (s.44AA / 2025 Act s.62) · audit (s.44AB / s.63) | **not required** · **not required** |
| Schedule VDA · TDS on this income | **nil — do not use Schedule VDA** · **none** (check AIS) |
| Losses carried forward (Schedule CFL) | none |
| Due date | plan **31 Jul 2027** (the legal date for a non-audit ITR-3 is confirmed when notified) — on time keeps any loss carried forward |
| Complete? | **2 of 7** items done — the list, and who closes each, is in section 13 |

## 1. Assessee and accounts

| | |
|---|---|
| Name · PAN | *in full on the server copy (data/tax/), never in git; the portal also pre-fills them* |
| Residential status | Resident individual |
| Accounts used | **Delta Exchange India** (login: *server copy*) · **CoinDCX**: Neblio Technologies Pvt Ltd, FIU-IND reg. VA00030982 (login: *server copy*) |
| Bank account | *server copy* — the one linked to both exchanges for rupee deposits and withdrawals |
| Business | Trading in rupee-settled crypto perpetual futures on Delta Exchange India and CoinDCX (speculative) · code 21009 · not commenced (paper) |
| Books | this statement (made from the bot's journal of every leg, rent payment and fee), each exchange's statements and the bank statements; not required by law at this size |

## 2. Nature and source of the income

- **What it is:** an arbitrage on perpetual futures. The same coin is held short on one Indian exchange and long on the other, so price moves largely cancel. The income is the difference in the periodic **funding payments** ("rent") the two exchanges pay or charge, less fees.
- **How it settles:** the contracts are cash-settled in rupees. Margin is deposited in rupees, profit and loss is credited in rupees, and withdrawals are in rupees. **No crypto-asset is ever bought, held or transferred** by the assessee.
- **Exchanges:** Delta Exchange India (settles at a fixed ₹85 per dollar of contract value) and CoinDCX INR-margined futures (fixed ₹102 per USDT). The two legs of each pair are sized to equal rupee value.
- **Head of income:** profits and gains of business — **speculative business** (a transaction settled other than by delivery; 1961 Act s.43(5), 2025 Act s.66(31)). Taxed at the slab rate; both exchanges' results are netted within the year; a loss can be set off only against speculative profit and carried forward 4 years if the return is filed on time (2025 Act s.113).
- **Not a VDA transfer:** no virtual digital asset is transferred (the 30% rate of 1961 Act s.115BBH / the 2025 Act, and the 1% TDS, do not apply; neither exchange deducts TDS on these contracts). This is the position taken in `reports/2026-10-09_tax_opinion.md`. It is not settled by any CBDT circular. See section 11.
- **When income arises:** funding is income when it is credited (each payment, in the month it is paid, IST); a position's price difference is income when the position is closed. Positions open on 31 March are not income until they close (section 7).

## 3. Summary for the tax year (₹)

| | ₹ | ITR-3 field |
|---|---:|---|
| **A. Turnover** (each leg's difference, + and − alike) | 5,382 | P&L: speculative activity — turnover |
| Price differences realised on closed positions | 7 | |
| Funding (rent) received | 2,036 | |
| Funding (rent) paid | -222 | |
| GST charged on funding paid | -40 | |
| Slippage (modelled in paper; live it is inside the fill prices) | -20 | |
| **B. Gross profit** | **1,761** | P&L: speculative activity — gross profit |
| Exchange fees | -50 | |
| GST on exchange fees | -9 | |
| Bank / transfer charges between the exchanges | 0 | |
| **C. Expenditure** | **-59** | P&L: speculative activity — expenditure |
| **D. Net income from speculative business (B − C)** | **1,701** | Schedule BP: income from speculative business |
| *Paper result before the journal began (carried in whole, marked to market, not split)* | *-39* | *(paper only)* |
| *Open positions, unrealised (not income until closed)* | *2* | *(not reported)* |

*Turnover method:* ICAI Guidance Note on Tax Audit — for speculative transactions, the total of favourable and unfavourable differences. Each leg of each position is one transaction; its difference is its price difference plus its funding. GST paid on fees and funding is an expense (no GST registration, so no input credit).

## 4. Exchange by exchange (₹)

| | Delta Exchange India | CoinDCX | total |
|---|---:|---:|---:|
| price differences realised | -399 | 405 | 7 |
| funding received | 1,921 | 115 | 2,036 |
| funding paid | -11 | -211 | -222 |
| GST on funding paid | -2 | -38 | -40 |
| exchange fees | -25 | -25 | -50 |
| GST on fees | -5 | -5 | -9 |
| money held at 31 March (so far: at the cut-off) | 46,803 | 39,859 | 86,663 |

## 5. Month by month (₹, IST months)

| month | positions closed | price differences | funding (net) | fees + GST | slippage, transfer and other charges | net |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10 | 3 | 7 | 1,774 | -59 | -20 | 1,701 |

## 6. Register of closed positions (₹)

Each position is one coin held on both exchanges at once. "Short Delta / long CoinDCX" means sold on Delta and bought on CoinDCX.

| # | coin | opened | closed | position | Delta: price · funding · fees | CoinDCX: price · funding · fees | net | why closed |
|---|---|---|---|---|---|---|---:|---|
| 1 | FARTCOIN | 03 Oct 2026 | 11 Oct 2026 | short Delta / long CoinDCX | -270 · 5 · -5 | 266 · -6 · -5 | -17 | spread under 10%/yr |
| 2 | IO | 03 Oct 2026 | 17 Oct 2026 | short Delta / long CoinDCX | -754 · 36 · -5 | 759 · -22 · -5 | 5 | spread under 10%/yr |
| 3 | TST | 05 Oct 2026 | 22 Oct 2026 | short Delta / long CoinDCX | 625 · 104 · -4 | -620 · -36 · -4 | 61 | spread under 10%/yr |

*Paper only, before the journal: 7 positions closed with net ₹-237 (fees included); their leg detail was not recorded.*

## 7. Positions open at the cut-off (23 Oct 2026) (₹) — not income until closed

| coin | opened | position | funding credited this year (income) | price, unrealised |
|---|---|---|---:|---:|
| KAITO | 03 Oct 2026 | short Delta / long CoinDCX | 152 | -1 *(+ ₹49 paper result before the journal)* |
| BEAT | 05 Oct 2026 | short Delta / long CoinDCX | 169 | 2 *(+ ₹43 paper result before the journal)* |
| LIT | 05 Oct 2026 | short Delta / long CoinDCX | 126 | 9 *(+ ₹53 paper result before the journal)* |
| STRK | 05 Oct 2026 | long Delta / short CoinDCX | 232 | -10 *(+ ₹14 paper result before the journal)* |
| NOT | 05 Oct 2026 | long Delta / short CoinDCX | 226 | 10 *(+ ₹53 paper result before the journal)* |
| H | 05 Oct 2026 | short Delta / long CoinDCX | 136 | -2 *(+ ₹-2 paper result before the journal)* |
| AIXBT | 05 Oct 2026 | long Delta / short CoinDCX | 217 | 2 *(+ ₹23 paper result before the journal)* |
| AUCTION | 11 Oct 2026 | long Delta / short CoinDCX | 265 | -3 |
| MEME | 17 Oct 2026 | long Delta / short CoinDCX | 147 | -6 |
| ARC | 22 Oct 2026 | short Delta / long CoinDCX | 22 | 3 |

## 8. Money moved between the exchanges (not income; only the charges are expenses)

| date | from | to | amount | charge |
|---|---|---|---:|---:|
| 2026-10-05 *(paper, before the journal)* | Pi42 | Delta | 13,861 | 85 |

## 9. Tax computation

| | ₹ |
|---|---:|
| Net income from speculative business | 1,701 |
| Taxable speculative income | 1,701 |
| Tax at your slab rate, 30% + 4% cess = 31.2% (no surcharge) | 531 |
| Advance tax | not needed (under ₹10,000); pay as self-assessment tax before filing |
| *Paper result before the journal (₹-39): not split into legs, so left out of every figure above* | *(paper only)* |

## 10. Reconciliation, and the year-end balances

- **Bot's ledger:** every journaled position's own figures (price + funding − fees) equal the ledger's result for it: **yes** (13 of 13).
- Paper ledger at the start of the journal (09 Oct 2026 19:07 IST): equity ₹84,961 from ₹85,000; fees ₹590, funding ₹764, price ₹-127, transfer charges ₹85.
- Paper ledger now: equity ₹86,665 (start ₹85,000).
- **Each exchange's own records:** not applicable (paper). Live, each exchange's funding, fees and realised results are set beside this statement's, line by line.
- **Money held at the exchanges** (the bot's ledger at the cut-off (23 Oct 2026); at 31 March, the year-end figure): Delta ₹46,803 · CoinDCX ₹39,859 · total **₹86,663**. This is the no-accounts balance sheet's *sundry debtors* (section 12): money the exchanges hold for you, not cash.

## 11. Note for the return, and the records to keep

**Suggested note** (keep with your records; add to the return where a remarks field exists):

> Income from trading in cash-settled, INR-margined crypto perpetual futures on Delta Exchange India and CoinDCX, offered as speculative business income. No virtual digital asset was transferred by the assessee; margin, profit and loss were settled in rupees. Exchange fees and GST thereon claimed as business expenditure.

**Keep (8 years):**
- this statement (every edition), with its .csv and .json;
- each exchange's statements for the year: trades, funding and fees;
- the bank statements showing deposits to and withdrawals from the exchanges;
- your AIS / Form 26AS, checked before filing.

**Risk:** if the department treated these contracts as virtual digital assets, the tax would be computed differently, and much higher. The figures and the reasoning are in `reports/2026-10-09_tax_opinion.md`. That is the position this statement files on, disclosed openly.

## 12. ITR-3 filing sheet — every field this income touches (₹, whole rupees)

Field names are the AY 2025-26 ITR-3's. The tax year 2026-27 forms (the first under the 2025 Act) are checked in June before filing, and this sheet is updated if a name or number moves.

| where | field | enter | why |
|---|---|---:|---|
| Part A-GEN | Nature of business: code · trade name · description | 21009 · — · Trading in rupee-settled crypto perpetual futures on Delta Exchange India and CoinDCX (speculative) | code 21009 = Speculative trading; confirmed in the year’s utility before filing |
| Part A-GEN | Liable to maintain accounts u/s 44AA (2025 Act s.62)? | **No** | income ₹1,701 (limit ₹2,50,000) · turnover ₹5,382 (limit ₹25,00,000), this and the 3 preceding years |
| Part A-GEN | Liable to audit u/s 44AB (2025 Act s.63)? | **No** | turnover ₹5,382 (limit ₹10 crore; all money moves by bank); presumptive income (44AD) never opted |
| Part A-GEN | Income declared under presumptive sections 44AD / 44ADA / 44AE? | **No** | declared at actual; do not opt for 44AD (opting out later locks it for 5 years) |
| Part A-P&L, no-accounts case | Business other than speculative: gross receipts · gross profit · expenses · net | 0 · 0 · 0 · 0 | this trade is entirely speculative |
| Part A-P&L, no-accounts case | **Speculative activity: turnover** | **5,382** | section 3, line A |
| Part A-P&L, no-accounts case | **Speculative activity: gross profit** | **1,761** | section 3, line B |
| Part A-P&L, no-accounts case | **Speculative activity: expenditure** | **59** | section 3, line C |
| Part A-P&L, no-accounts case | **Speculative activity: net income** | **1,701** | section 3, line D |
| Part A-BS, no-accounts case (31 March) | Sundry debtors | **86,663** | money held by the two exchanges (section 10) |
| Part A-BS, no-accounts case | Sundry creditors · stock-in-trade · cash balance | 0 · 0 · 0 | nothing owed; futures are not stock; no cash is used |
| Part A-OI · Part A-QD | other information · quantitative details | not filled | only for audited accounts / goods |
| Schedule BP, speculative business | Net profit or loss from speculative business (as per P&L) | **1,701** | section 3, line D |
| Schedule BP, speculative business | Additions · deductions | 0 · 0 | no disallowance: fees and GST are wholly for the business; no depreciation, no STT |
| Schedule BP, speculative business | Income from speculative business | **1,701** | taxed at the slab rate |
| Schedule CYLA | Speculative loss set off against other heads | **0** | not allowed (s.73 / 2025 Act s.113) |
| Schedule BFLA | Brought-forward speculative loss set off | **0** | none brought forward |
| Schedule CFL | Speculative loss carried forward | **0** | none |
| Schedule TDS2 · TCS | Tax deducted / collected on this income | **0** | neither exchange deducts TDS on these contracts; anything in AIS is matched first |
| Schedule IT | Advance tax and self-assessment tax | as pre-filled from Form 26AS | the challans you paid for this income (section 9: ₹531 for the year) |
| Schedule VDA | Income from transfer of virtual digital assets | **nil — leave empty** | no VDA is transferred (section 2); filling it would itself declare a VDA |
| Schedule CG · OS · SI | capital gains · other sources · special-rate income | nothing from this trade | slab rate, business head |
| Schedule FA | Foreign assets | **nil for this trade** | both exchanges are Indian, accounts held in rupees |
| Schedule AL | Assets and liabilities (only if total income > ₹50 lakh) | 86,663 as deposits | the same exchange balances |
| Tax regime | as for your whole return | your choice | with business income, opting for the old regime needs Form 10-IEA (or its 2026 Rules successor) by the due date; switching back is allowed once |
| Filing | due date | plan **31 Jul 2027** (the legal date for a non-audit ITR-3 is confirmed when notified) | a loss is carried forward only if filed by the due date |

## 13. Handover pack for the filing CA

**To the CA who files this return:** this statement is complete for this income. Please:
1. file **ITR-3** and enter the section 12 figures as given;
2. leave **Schedule VDA** empty, and do not opt for presumptive income (44AD);
3. if the AIS shows entries from Delta Exchange India or CoinDCX, compare them with sections 4 and 10. They should agree. If the AIS calls them VDA, give AIS feedback that the income is offered as speculative business income;
4. take the other heads (salary from Form 16; interest and the rest from the AIS) as usual. They are outside this statement;
5. file by the due date above.

**Documents in the pack:**
- this statement (the server copy, with name and PAN) and its .csv;
- the tax opinion `reports/2026-10-09_tax_opinion.md` (why speculative business, not VDA);
- each exchange's statement for the year (trades, funding, fees);
- the bank statement for the account linked to the exchanges;
- your Form 16, AIS and Form 26AS;
- last year's ITR acknowledgement, if a loss is brought forward.

**Completeness check:**

| item | status | who closes it |
|---|---|---|
| Every position journaled and agreeing with the bot's ledger | done | — |
| Each exchange's own statement reconciled (section 10) | not applicable (paper) | the reconcile step (B3), daily from live day |
| Balances at 31 March from the exchanges (Part A-BS) | not applicable (paper) | the reconcile step, on 1 April; until then the bot's own figure is shown |
| Your name, PAN and account IDs on the server copy (section 1) | open | you, once, with --setup (about 2 minutes; optional, the portal knows your PAN) |
| Business code confirmed in this year's ITR-3 utility | open | me, at the June review before filing |
| This year's legal due date confirmed | open | me, when the CBDT notifies it |
| Losses brought forward from earlier years (Schedule BFLA / CFL) | done | — |
| Delta Exchange India's operating company and FIU-IND number | open | me, from Delta's terms page, at live day |
| Reviewed with your adviser before handover | open | you and me, in June before filing |

**Reviewed:** not yet. We go through it together in June, before it goes to the CA.

*Prepared by Claude as your tax adviser, not a registered CA. Figures come from the bot's journal and are checked against its ledger; live, also against each exchange's own statement.*
