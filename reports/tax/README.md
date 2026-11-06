# Your ITR statements: how they are made and how you hand them to the filing CA

You asked (9 Oct 2026):
- "build a transaction & net profit/loss summary, the details of the source of this sort of income ... so that i can
  present that directly while filing ITR in year 2027 ... keep updating the summary & re analysing it everytime ...
  during live trading the summary will start afresh but in exactly same/correct/latest generated format";
- then: "make sure that the above income document is complete in the sense that i won't have to fill in any transaction
  details myself or anything else ... so that ... i can hand it over straight (after of course thoroughly reviewing with
  you) to a third party CA who will only help in filing itr".

**Analogy:** the statement is a **ready-to-post parcel**. The bot packs it every day (the journal), I check what is
inside every month (the reviews), and section 13 is the packing list taped to the lid. The filing CA only has to copy
the figures onto the form, like a post-office clerk copying the address onto the label.

## What is here (in git)

| file | what it is |
|---|---|
| `ITR_TY2026-27_rent_gap_PAPER.md` | **paper rehearsal**, tax year 2026-27, **not for filing**. Re-made at every review, so you can see the format filling up |
| `ITR_TY2026-27_rent_gap_PAPER.csv` | the same, one row per leg, for a spreadsheet |
| `ITR_TY2026-27_rent_gap_PAPER.json` | the filing figures in machine form; next year's statement reads the losses carried forward from it |
| `ITR_TY2026-27_rent_gap_LIVE.*` | **from your first real trade** (the February 2027 pilot): the statement the return is filed from. Same 13 sections, started afresh at zero. The copy in git has your name and PAN **masked** |
| `ITR_TY2027-28_rent_gap_LIVE.*` | the next tax year (April 2027 – March 2028), and so on |
| `profile.json` | settings that are not secret, kept by me: the business code once checked, the year's due date, your filing dates, the editions we reviewed together, the exchanges' company details |

## What is only on your server (never in git)

| file | what it is |
|---|---|
| `data/tax/taxpayer.json` | your name, PAN, the e-mail or user ID you log in to each exchange with, and the bank account (last 4 digits only). Readable only by you (600). Made once with `--setup` |
| `data/tax/ITR_TY<year>_rent_gap_LIVE.md` + `.csv` | **the copy you hand to the filing CA**: the same statement, **in full** with your name and PAN (from B3, the bot writes it every morning) |
| `data/tax/xrec_TY<year>.json` | each exchange's own figures (from B3): funding, fees, realised results and the 31 March balances, set beside the bot's in section 10 |

The logs push never copies `data/tax/`, and it scrubs every value of `taxpayer.json` out of the logs, the same way it
scrubs your API keys.

## The 13 sections

**At a glance** (top box): the eight things the filing CA needs, on one screen.

1. you and your accounts;
2. what the income is, and why it is speculative business income, not crypto (VDA);
3. the year's summary: turnover, gross profit, expenditure, net;
4. exchange by exchange, with the money held at each on 31 March;
5. month by month;
6. every closed position, both legs;
7. positions open on 31 March (not income until they close);
8. money moved between the exchanges;
9. the tax, any loss brought forward, advance tax;
10. reconciliation: with the bot's ledger and, live, with each exchange's own records;
11. the note for the return and the records to keep;
12. **the ITR-3 filing sheet**: every field this income touches, with the figure to enter and why;
13. **the handover pack**: the instructions to the filing CA, the documents, and a completeness check that names who
    closes each open item.

## How the handover works (July 2027, for tax year 2026-27)

1. **June 2027, with me:**
   - I confirm the business code (21009, Speculative trading) in that year's ITR-3 utility and the legal due date;
   - I check the field names under the new Income-tax Act and update section 12 if any moved;
   - we go through the statement together, against your AIS;
   - the completeness check in section 13 should then read all done.
2. **You take the server copy** (`data/tax/ITR_TY2026-27_rent_gap_LIVE.md` and `.csv`) and give it to the filing CA,
   with the documents section 13 lists:
   - your Form 16, AIS and Form 26AS;
   - each exchange's statement for the year;
   - the bank statement;
   - the tax opinion.

   I'll give you the exact commands that day.
3. **The filing CA** enters section 12's figures in ITR-3, adds your salary and other income as usual, and files by
   the due date. Section 13 tells them not to use the crypto (VDA) schedule and not to opt for presumptive income.
4. **After filing**, tell me the filing date from the acknowledgement. I record it, because a loss carried forward is
   only valid if the return was on time.

**What you fill in: nothing in the statement.** The only typing you do is once, optionally:

```
sudo -u omega python3 /home/omega/omega/omega_tax_statement.py --setup
```

It asks five questions (name, PAN, the two exchange logins, bank name and last 4 digits). The answers stay on your
server. The portal pre-fills your name and PAN anyway, so this only makes the statement look like a proper CA's file.

## How it is made

**The bot writes a journal** (C544, running since 9 Oct; C545 adds two things):
- both legs of every position: entry and exit time, size and price;
- each leg's price result;
- rent received, rent paid and GST on rent paid, **each payment in the IST month it was paid** (C545). The 06:00 run
  on 1 April books the last 18 hours of March, and those belong to the year that ended;
- fees split into exchange fee, GST and slippage;
- every transfer between the exchanges;
- **a year-end record** (C545): at the first run of each new tax year, each exchange's money as the old year left it.

**`omega_tax_statement.py` turns the journal into the statement:**
- in **rupees** at Delta India's fixed rate (₹85 per dollar). Live legs are matched in rupees, so this is exact;
- **by Indian tax year** (1 April – 31 March, IST);
- a position open on 31 March is cut exactly: its rent to 31 March is this year's income, and its price result is next
  year's, when it closes;
- **checked against the bot's own ledger** (section 10). Live, it is also checked against both exchanges' own records.

**I re-make it and re-check it at every monthly review**, as your tax adviser, and explain anything unusual:
`python3 omega_tax_statement.py <logs>/c524_xvenue.json --out reports/tax --edition N`.

*Prepared by Claude as your tax adviser. I am not a registered CA. The position taken is explained, with its risk in
numbers, in `reports/2026-10-09_tax_opinion.md`.*
