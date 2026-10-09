# Your ITR statements: how they are made and how to use them in 2027

You asked (9 Oct 2026): "build a transaction & net profit/loss summary, the details of the source of this sort of income
... so that i can present that directly while filing ITR in year 2027 ... keep updating the summary & re analysing it
everytime ... during live trading the summary will start afresh but in exactly same/correct/latest generated format".

## What is here

| file | what it is |
|---|---|
| `ITR_TY2026-27_rent_gap_PAPER.md` | **paper rehearsal**, tax year 2026-27, **not for filing**. Re-made at every review, so you can see the format filling up. |
| `ITR_TY2026-27_rent_gap_PAPER.csv` | the same, one row per leg, for a spreadsheet |
| `ITR_TY2026-27_rent_gap_LIVE.md` / `.csv` | **from your first real trade** (the February 2027 pilot): the statement you file from. Same 11 sections, started afresh at zero. |
| `ITR_TY2027-28_rent_gap_LIVE.md` / `.csv` | the next tax year (April 2027 – March 2028), and so on |

## How it is made

**The bot writes a journal** (C544, from the day you deploy it). For every position it records:
- both legs: entry and exit time, size and price;
- each leg's price result;
- rent received, rent paid and the GST on rent paid, by month;
- fees split into exchange fee, GST and slippage;
- every transfer between the exchanges.

**`omega_tax_statement.py` turns the journal into the statement:**
- in **rupees** at Delta India's fixed rate (₹85 per dollar). Live legs are matched in rupees, so this is exact;
- **by Indian tax year** (1 April – 31 March, IST dates);
- **checked against the bot's own ledger** (section 10). Live, it is also checked against both exchanges' statements.

**I re-make it and re-check it at every monthly review**, as your tax adviser, and explain anything unusual. The
reviews are on the 1st of each month, plus the end-November review. From 15 Dec (step B3) the bot also writes it itself
every morning.

## How to use it when you file (July 2027, for tax year 2026-27)

1. Open the **LIVE** statement's section 3.
2. Choose **ITR-3** (business income).
3. In the profit-and-loss part, under **speculative activity**, enter:
   - **Turnover:** line A;
   - **Gross profit:** line B;
   - **Expenditure:** line C;
   - **Net income from speculative activity:** line D.
4. In **Schedule BP**, the same net figure appears as income from speculative business.
   - If it is a loss, it is carried forward, which needs the return **on time**.
5. **Do not** use the crypto (VDA) schedule.
6. **Before filing:**
   - check your AIS / Form 26AS: no TDS is expected on these contracts;
   - pay any tax due (self-assessment);
   - keep the statement with each exchange's own statements and your bank statements.
7. Where the return has a remarks field, use the note in section 11.

The exact field names on the 2027 forms (the first under the Income-tax Act, 2025) will be checked in June 2027, and the
statement will be adjusted if any change.

*Prepared by Claude as your tax adviser. I am not a registered CA, and the position taken is explained, with its risk in
numbers, in `reports/2026-10-09_tax_opinion.md`.*
