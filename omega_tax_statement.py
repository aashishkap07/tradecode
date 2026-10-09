#!/usr/bin/env python3
"""C544: the operator's income statement for ITR-3 -- the Delta Exchange India + CoinDCX rent-gap trade.

    python3 omega_tax_statement.py LEDGER.json [--live] [--ty 2026-27] [--inr 85] [--out reports/tax] [--edition N]

LEDGER.json is the plan's ledger (data/c524_xvenue.json on the server; logs/c524_xvenue.json on the logs branch).
It writes reports/tax/ITR_TY<ty>_rent_gap_<PAPER|LIVE>.md and a matching .csv, in one fixed format:
  1 the assessee and the accounts       2 the nature and source of the income   3 the summary for the tax year
  4 exchange by exchange                5 month by month                        6 the register of closed positions
  7 positions open at the cut-off       8 money moved between the exchanges     9 the tax computation (estimate)
  10 reconciliation with the ledger     11 the note for the return and the records to keep
PAPER: a rehearsal on the bot's paper ledger -- no real money, NOT FOR FILING. LIVE: the same format, started afresh
on the day real trading starts, from the real fills, rent and fees (the live journal of B2/B3).

Rupees: Delta India settles at a fixed Rs 85 per dollar and CoinDCX at Rs 102 per USDT. Live legs are matched in rupees
(the CoinDCX leg's USDT size = the Delta leg's dollars x 85/102), so a pair's rupee figures are its dollar figures x 85.
The paper ledger's legs are equal in dollars; the statement converts them as if rupee-matched (x 85 throughout).
Tax: the opinion in reports/2026-10-09_tax_opinion.md -- speculative business income (ITR-3, Schedule BP), both legs of
both exchanges netted in the year, no TDS, never the VDA schedule. Not a registered CA's certificate.
"""
import os, sys, json, csv, argparse, datetime as dt

IST = 19800
TAX = 0.312
DELTA_INR = 85.0          # Delta India's fixed rate (public /v2/settings: fiat_to_usd.asset_to_fiat_value = 85, 9 Oct 2026)
DCX_INR = 102.0           # CoinDCX's fixed rate for INR-margined futures (its support page, 8 Oct 2026)


def ist(ms):
    return dt.datetime.utcfromtimestamp(int(ms) / 1000 + IST)


def ty_of(ms):
    d = ist(ms)
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def ty_of_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    y = y if mo >= 4 else y - 1
    return f"{y}-{str(y + 1)[2:]}"


def ty_bounds(ty):
    y = int(ty[:4])
    return dt.date(y, 4, 1), dt.date(y + 1, 3, 31)


def rs(x, inr):
    return x * inr


def fmt(x, nd=0):
    s = f"{abs(x):,.{nd}f}"
    return f"-{s}" if x < -0.5 * 10 ** -nd else s


def split_cost(n, f, g, spr):
    """a side's modelled cost on notional n: (fee, GST on the fee, half-spread)"""
    return n * f, n * f * g, n * spr


def load(path):
    d = json.load(open(path))
    j = d.get('journal')
    if j is None:                                   # a ledger saved before C544: carry in its totals (as the bot does)
        now = int(dt.datetime.utcnow().timestamp() * 1000)
        j = [dict(t='carry', ms=now, eq=d.get('eq', 0.0), start=d.get('start_equity', 0.0), fees=d.get('fees', 0.0),
                  funding=d.get('funding', 0.0), price=d.get('price_pnl', 0.0), transfer_fees=d.get('transfer_fees', 0.0),
                  closed=d.get('closed') or [], transfers=d.get('transfers') or [], moves=d.get('venue_moves') or [],
                  rebased=d.get('rebased') or [],
                  open_pnl=sum(float(p.get('pnl') or 0.0) for p in (d.get('pairs') or {}).values()),
                  open_funding=sum(float(p.get('funding') or 0.0) for p in (d.get('pairs') or {}).values()))]
        for p in (d.get('pairs') or {}).values():
            p.setdefault('jx', dict(opened=p.get('opened'), d_px0=p.get('d_px'), b_px0=p.get('b_px'), n_in=p.get('notional'),
                                    fee_d=0.0, fee_b=0.0, px_d=0.0, px_b=0.0, fm={}, venue=(d.get('venue') or '').title(),
                                    rates=None, carry=dict(ms=now, pnl=p.get('pnl', 0.0), funding=p.get('funding', 0.0))))
        d['journal'] = j
        d['_pre_journal'] = True
    return d


def build(d, ty, live, inr):
    """everything the statement shows, in dollars (x inr for rupees), for tax year ty"""
    J = d['journal']
    carry = next((r for r in J if r.get('t') == 'carry'), None)
    out = dict(closed=[], open=[], transfers=[], months={}, venue={'Delta': {}, d.get('venue', 'coindcx').title(): {}},
               carry=carry, checks=[])
    v2 = 'CoinDCX' if (d.get('venue') or 'coindcx') == 'coindcx' else (d.get('venue') or 'second').title()
    out['v2'] = v2
    ven = {'Delta': dict(price=0.0, rent_in=0.0, rent_out=0.0, rent_gst=0.0, fee=0.0, fee_gst=0.0, spread=0.0, other=0.0),
           v2: dict(price=0.0, rent_in=0.0, rent_out=0.0, rent_gst=0.0, fee=0.0, fee_gst=0.0, spread=0.0, other=0.0)}
    months = {}
    turnover = 0.0

    def mrow(m):
        return months.setdefault(m, dict(price=0.0, rent=0.0, fees=0.0, spread=0.0, other=0.0, n_closed=0))

    def costs(rec, n, which, leg_fee_total=None):
        r = rec.get('rates') or dict(fd=0.0005, gd=0.18, fb=0.0005, gb=0.18, spr=0.0002)
        f, g = (r['fd'], r['gd']) if which == 'd' else (r['fb'], r['gb'])
        return split_cost(n, f, g, r['spr'])

    def legs_of(rec, is_open):
        """this tax year's part of one position, per leg"""
        res = {}
        for leg, vname in (('d', 'Delta'), ('b', v2)):
            px = float(rec.get('px_' + leg) or 0.0)
            rin = rout = rgst = 0.0
            for m, row in (rec.get('fm') or {}).items():
                if ty_of_month(m) != ty:
                    continue
                k = 0 if leg == 'd' else 3
                rin += row[k]; rout += row[k + 1]; rgst += row[k + 2]
                mm = mrow(m)
                mm['rent'] += row[k] + row[k + 1] + row[k + 2]
            n_in = float(rec.get('n_in') or 0.0)
            f_in, g_in, s_in = costs(rec, n_in, leg) if rec.get('rates') else (0.0, 0.0, 0.0)
            fee_total = float(rec.get('fee_' + leg) or 0.0)
            fee_out_total = float(rec.get(f'fee_{leg}_out') or 0.0)
            f_out = g_out = s_out = 0.0
            if not is_open and rec.get('rates'):
                f_out, g_out, s_out = costs(rec, float(rec.get('n_out') or 0.0), leg)
            other = fee_total - (f_in + g_in + s_in) - (f_out + g_out + s_out) if rec.get('rates') else fee_total
            entry_in_ty = rec.get('opened') and ty_of(rec['opened']) == ty
            exit_in_ty = (not is_open) and ty_of(rec['closed']) == ty
            res[leg] = dict(venue=vname, price=(px if exit_in_ty else 0.0), price_open=(px if is_open else 0.0),
                            rent_in=rin, rent_out=rout, rent_gst=rgst,
                            fee=(f_in if entry_in_ty else 0.0) + (f_out if exit_in_ty else 0.0),
                            fee_gst=(g_in if entry_in_ty else 0.0) + (g_out if exit_in_ty else 0.0),
                            spread=(s_in if entry_in_ty else 0.0) + (s_out if exit_in_ty else 0.0),
                            other=(other if entry_in_ty else 0.0), fee_out_total=fee_out_total)
        return res

    for rec in J:
        if rec.get('t') == 'close' and (ty_of(rec['closed']) == ty or any(ty_of_month(m) == ty for m in rec.get('fm') or {})
                                        or ty_of(rec.get('opened') or rec['closed']) == ty):
            L = legs_of(rec, False)
            out['closed'].append(dict(rec=rec, legs=L))
            if ty_of(rec['closed']) == ty:
                mm = mrow(ist(rec['closed']).strftime('%Y-%m'))
                mm['n_closed'] += 1
                mm['price'] += L['d']['price'] + L['b']['price']
        elif rec.get('t') == 'transfer' and ty_of(rec['ms']) == ty:
            out['transfers'].append(rec)
            mrow(ist(rec['ms']).strftime('%Y-%m'))['other'] += float(rec.get('fee') or 0.0)
    for c, p in (d.get('pairs') or {}).items():
        jx = dict(p.get('jx') or {})
        rec = dict(jx, coin=c, side=p.get('side'), d_sym=p.get('d_sym'), d_qty=p.get('d_qty'), b_qty=p.get('b_qty'),
                   cv=p.get('cv'), d_px1=p.get('d_px'), b_px1=p.get('b_px'), pnl=p.get('pnl'), opened=jx.get('opened') or p.get('opened'))
        out['open'].append(dict(rec=rec, legs=legs_of(rec, True)))
    # each leg into its exchange's totals; fees, GST and slippage into the month they were paid
    for item in out['closed'] + out['open']:
        rec, L = item['rec'], item['legs']
        is_open = item in out['open']
        for leg in ('d', 'b'):
            x = L[leg]
            v = ven[x['venue']]
            for k in ('price', 'rent_in', 'rent_out', 'rent_gst', 'fee', 'fee_gst', 'spread', 'other'):
                v[k] += x[k]
            turnover += abs(x['price'] + x['rent_in'] + x['rent_out'] + x['rent_gst'])
            if not rec.get('rates'):
                continue
            if rec.get('opened') and ty_of(rec['opened']) == ty:
                fi, gi, si = costs(rec, float(rec.get('n_in') or 0.0), leg)
                mm = mrow(ist(rec['opened']).strftime('%Y-%m'))
                mm['fees'] += fi + gi; mm['spread'] += si; mm['other'] += x['other']
            if not is_open and ty_of(rec['closed']) == ty:
                fo, go, so = costs(rec, float(rec.get('n_out') or 0.0), leg)
                mm = mrow(ist(rec['closed']).strftime('%Y-%m'))
                mm['fees'] += fo + go; mm['spread'] += so
    out['venue'] = ven
    out['months'] = dict(sorted(months.items()))
    tf = sum(float(t.get('fee') or 0.0) for t in out['transfers'])
    tot = {k: sum(v[k] for v in ven.values()) for k in ven['Delta']}
    gross = tot['price'] + tot['rent_in'] + tot['rent_out'] + tot['rent_gst'] - tot['spread']
    expend = tot['fee'] + tot['fee_gst'] + tot['other'] + tf
    out['totals'] = dict(tot, transfer_fees=tf, turnover=turnover, gross=gross, expenditure=expend, net=gross - expend,
                         unrealised=sum(item['legs'][l]['price_open'] for item in out['open'] for l in 'db'))
    # the carried-in paper result (before the journal) -- paper only, whole and unsplit
    out['carried'] = (float(carry['eq']) - float(carry['start'])) if (carry and not live) else 0.0
    # checks: each journaled position's own sum == the ledger's figure for it
    for item in out['closed'] + out['open']:
        rec = item['rec']
        if not rec.get('rates'):
            continue
        fm_all = sum(sum(row) for row in (rec.get('fm') or {}).values())
        mine = float(rec.get('px_d') or 0) + float(rec.get('px_b') or 0) + fm_all - float(rec.get('fee_d') or 0) - float(rec.get('fee_b') or 0)
        led = float(rec.get('pnl') or 0.0) - float(((rec.get('carry') or {}).get('pnl')) or 0.0)
        out['checks'].append((rec.get('coin'), abs(mine - led) < 1e-6, mine, led))
    return out


def write(d, o, ty, live, inr, outdir, edition, asof):
    os.makedirs(outdir, exist_ok=True)
    kind = 'LIVE' if live else 'PAPER'
    base = os.path.join(outdir, f"ITR_TY{ty}_rent_gap_{kind}")
    T, v2 = o['totals'], o['v2']
    y0, y1 = ty_bounds(ty)
    R = lambda x: fmt(rs(x, inr))
    L = []
    w = L.append
    w("# Income statement for ITR-3: speculative business income from rupee-settled crypto futures")
    w("")
    w(f"**Tax year {ty}** ({y0:%d %b %Y} – {y1:%d %b %Y}) · **{kind}** · edition {edition} · prepared {asof} IST · "
      f"amounts in **₹** (Delta India's fixed rate ₹{inr:.0f} per dollar)")
    w("")
    if live:
        w("> **LIVE.** Real trades only, from the day live trading started. Use the figures in section 3 for ITR-3.")
    else:
        w("> **PAPER — NOT FOR FILING.** This is a rehearsal on the bot's paper ledger: no real money moved, so there is "
          "no income to declare. It is kept in exactly the format the live statement will use. The live statement "
          "starts afresh, from zero, on the first real trade.")
    w("")
    w("## 1. Assessee and accounts")
    w("")
    w("| | |")
    w("|---|---|")
    w("| Name / PAN | *(as on your PAN card)* |")
    w("| Residential status | Resident individual |")
    w("| Accounts used | **Delta Exchange India** (account ID: *from your profile*) · **CoinDCX**: Neblio Technologies Pvt Ltd, "
      "FIU-IND reg. VA00030982 (account ID: *from your profile*) |")
    w("| Bank account | the one linked to both exchanges for rupee deposits and withdrawals |")
    w("| Books | this statement + each exchange's own statements + bank statements (no audit at this turnover) |")
    w("")
    w("## 2. Nature and source of the income")
    w("")
    w("- **What it is:** an arbitrage on perpetual futures. The same coin is held short on one Indian exchange and "
      "long on the other, so price moves largely cancel. The income is the difference in the periodic **funding "
      "payments** (\"rent\") the two exchanges pay or charge, less fees.")
    w("- **How it settles:** the contracts are cash-settled in rupees. Margin is deposited in rupees, profit and loss "
      "is credited in rupees, and withdrawals are in rupees. **No crypto-asset is ever bought, held or transferred** "
      "by the assessee.")
    w(f"- **Exchanges:** Delta Exchange India (settles at a fixed ₹{DELTA_INR:.0f} per dollar of contract value) and "
      f"CoinDCX INR-margined futures (fixed ₹{DCX_INR:.0f} per USDT). The two legs of each pair are sized to equal "
      "rupee value.")
    w("- **Head of income:** profits and gains of business — **speculative business** (a transaction settled other than "
      "by delivery; 1961 Act s.43(5), 2025 Act s.66(31)). Taxed at the slab rate; both exchanges' results are netted "
      "within the year; a loss can be set off only against speculative profit and carried forward 4 years if the "
      "return is filed on time (2025 Act s.113).")
    w("- **Not a VDA transfer:** no virtual digital asset is transferred (the 30% rate of 1961 Act s.115BBH / the "
      "2025 Act, and the 1% TDS, do not apply; neither exchange deducts TDS on these contracts). This is the position "
      "taken in `reports/2026-10-09_tax_opinion.md`. It is not settled by any CBDT circular. See section 11.")
    w("")
    w("## 3. Summary for the tax year (₹)")
    w("")
    w("| | ₹ | ITR-3 field |")
    w("|---|---:|---|")
    w(f"| **A. Turnover** (sum of each leg's realised differences, + and − alike) | {R(T['turnover'])} | P&L: speculative activity — turnover |")
    w(f"| Price differences realised on closed positions | {R(T['price'])} | |")
    w(f"| Funding (rent) received | {R(T['rent_in'])} | |")
    w(f"| Funding (rent) paid | {R(T['rent_out'])} | |")
    w(f"| GST charged on funding paid | {R(T['rent_gst'])} | |")
    if not live:
        w(f"| Slippage (modelled in paper; live it is inside the fill prices) | {R(-T['spread'])} | |")
    w(f"| **B. Gross profit** | **{R(T['gross'])}** | P&L: speculative activity — gross profit |")
    w(f"| Exchange fees | {R(-T['fee'])} | |")
    w(f"| GST on exchange fees | {R(-T['fee_gst'])} | |")
    w(f"| Bank / transfer charges between the exchanges | {R(-T['transfer_fees'])} | |")
    if T['other']:
        w(f"| Other exchange charges | {R(-T['other'])} | |")
    w(f"| **C. Expenditure** | **{R(-T['expenditure'])}** | P&L: speculative activity — expenditure |")
    w(f"| **D. Net income from speculative business (B − C)** | **{R(T['net'])}** | Schedule BP: income from speculative business |")
    if not live and o['carried']:
        w(f"| *Paper result before the journal began (carried in whole, marked to market, not split)* | *{R(o['carried'])}* | *(paper only)* |")
    w(f"| *Open positions, unrealised (not income until closed)* | *{R(T['unrealised'])}* | *(not reported)* |")
    w("")
    w("## 4. Exchange by exchange (₹)")
    w("")
    w(f"| | Delta Exchange India | {v2} | total |")
    w("|---|---:|---:|---:|")
    for k, lab in (('price', 'price differences realised'), ('rent_in', 'funding received'), ('rent_out', 'funding paid'),
                   ('rent_gst', 'GST on funding paid'), ('fee', 'exchange fees'), ('fee_gst', 'GST on fees')):
        sgn = -1 if k in ('fee', 'fee_gst') else 1
        a, b = o['venue']['Delta'][k] * sgn, o['venue'][v2][k] * sgn
        w(f"| {lab} | {R(a)} | {R(b)} | {R(a + b)} |")
    w("")
    w("## 5. Month by month (₹, IST months)")
    w("")
    w("| month | positions closed | price differences | funding (net) | fees + GST | net |")
    w("|---|---:|---:|---:|---:|---:|")
    for m, r in o['months'].items():
        net = r['price'] + r['rent'] - r['fees'] - r['spread'] - r['other']
        w(f"| {m} | {r['n_closed']} | {R(r['price'])} | {R(r['rent'])} | {R(-r['fees'])} | {R(net)} |")
    if not o['months']:
        w("| — | 0 | 0 | 0 | 0 | 0 |")
    w("")
    w("## 6. Register of closed positions (₹)")
    w("")
    w(f"Each position is one coin held on both exchanges at once. \"Short Delta / long {v2}\" means sold on Delta and bought on {v2}.")
    w("")
    w("| # | coin | opened | closed | position | Delta: price · funding · fees | " + v2 + ": price · funding · fees | net | why closed |")
    w("|---|---|---|---|---|---|---|---:|---|")
    for i, item in enumerate(o['closed'], 1):
        r, Lg = item['rec'], item['legs']
        pos = f"short Delta / long {v2}" if int(r.get('side') or 1) > 0 else f"long Delta / short {v2}"
        cell = lambda x: f"{R(x['price'])} · {R(x['rent_in'] + x['rent_out'] + x['rent_gst'])} · {R(-(x['fee'] + x['fee_gst']))}"
        net = sum(Lg[l]['price'] + Lg[l]['rent_in'] + Lg[l]['rent_out'] + Lg[l]['rent_gst'] - Lg[l]['fee'] - Lg[l]['fee_gst']
                  - Lg[l]['spread'] - Lg[l]['other'] for l in 'db')
        w(f"| {i} | {r['coin']} | {ist(r['opened']):%d %b %Y} | {ist(r['closed']):%d %b %Y} | {pos} | {cell(Lg['d'])} | "
          f"{cell(Lg['b'])} | {R(net)} | {r.get('why', '')} |")
    if not o['closed']:
        w("| — | none in this tax year yet | | | | | | | |")
    if not live and o['carry'] and o['carry'].get('closed'):
        cl = o['carry']['closed']
        w("")
        w(f"*Paper only, before the journal: {len(cl)} positions closed with net ₹{R(sum(float(x.get('pnl') or 0) for x in cl))} "
          f"(fees included); their leg detail was not recorded.*")
    w("")
    w("## 7. Positions open at the cut-off (₹) — not income until closed")
    w("")
    w("| coin | opened | position | funding credited this year (income) | price, unrealised |")
    w("|---|---|---|---:|---:|")
    for item in o['open']:
        r, Lg = item['rec'], item['legs']
        pos = f"short Delta / long {v2}" if int(r.get('side') or 1) > 0 else f"long Delta / short {v2}"
        rent = sum(Lg[l]['rent_in'] + Lg[l]['rent_out'] + Lg[l]['rent_gst'] for l in 'db')
        op = f"{ist(r['opened']):%d %b %Y}" if r.get('opened') else '—'
        car = r.get('carry')
        extra = f" *(+ ₹{R(float(car.get('pnl') or 0))} paper result before the journal)*" if (car and not live) else ''
        w(f"| {r['coin']} | {op} | {pos} | {R(rent)} | {R(Lg['d']['price_open'] + Lg['b']['price_open'])}{extra} |")
    if not o['open']:
        w("| — | | | | |")
    w("")
    w("## 8. Money moved between the exchanges (not income; only the charges are expenses)")
    w("")
    w("| date | from | to | amount | charge |")
    w("|---|---|---|---:|---:|")
    for t in o['transfers']:
        w(f"| {ist(t['ms']):%d %b %Y} | {t['frm']} | {t['to']} | {R(float(t['amt']))} | {R(float(t.get('fee') or 0))} |")
    if not live and o['carry']:
        for t in o['carry'].get('transfers') or []:
            w(f"| {t.get('at', '')[:10]} *(paper, before the journal)* | {t.get('frm')} | {t.get('to')} | {R(float(t.get('amt') or 0))} | {R(float(t.get('fee') or 0))} |")
    if not o['transfers'] and not (not live and o['carry'] and o['carry'].get('transfers')):
        w("| — | | | | |")
    w("")
    w("## 9. Tax computation (estimate)")
    w("")
    net = T['net'] + (o['carried'] if not live else 0.0)
    tax = max(0.0, net) * TAX
    w("| | ₹ |")
    w("|---|---:|")
    w(f"| Net income from speculative business{' (incl. the paper carry-in)' if (not live and o['carried']) else ''} | {R(net)} |")
    w(f"| Tax at your slab rate, 30% + 4% cess = 31.2% (no surcharge) | {R(tax)} |")
    w(f"| Advance tax | {'due when the year’s tax not covered by TDS exceeds ₹10,000: 15 Jun 15% · 15 Sep 45% · 15 Dec 75% · 15 Mar 100%' if rs(tax, inr) > 10000 else 'not needed (under ₹10,000); pay as self-assessment tax before filing'} |")
    if net < 0:
        w("| Loss | carried forward 4 years against speculative profit only — file on time |")
    w("")
    w("## 10. Reconciliation with the ledger")
    w("")
    ok = all(c[1] for c in o['checks'])
    w(f"- Every journaled position's own figures (price + funding − fees) equal the ledger's result for it: "
      f"**{'yes' if ok else 'NO'}** ({sum(1 for c in o['checks'] if c[1])} of {len(o['checks'])}).")
    if not live and o['carry']:
        c = o['carry']
        w(f"- Paper ledger at the start of the journal ({ist(c['ms']):%d %b %Y %H:%M} IST): equity ₹{R(float(c['eq']))} "
          f"from ₹{R(float(c['start']))}; fees ₹{R(float(c['fees']))}, funding ₹{R(float(c['funding']))}, "
          f"price ₹{R(float(c['price']))}, transfer charges ₹{R(float(c['transfer_fees']))}.")
    w(f"- Paper ledger now: equity ₹{R(float(d.get('eq') or 0))} (start ₹{R(float(d.get('start_equity') or 0))})."
      if not live else "- Live: each exchange's own statement and the bank statement must agree with sections 4 and 8.")
    w("")
    w("## 11. Note for the return, and the records to keep")
    w("")
    w("**Suggested note** (keep with your records; add to the return where a remarks field exists):")
    w("")
    w("> Income from trading in cash-settled, INR-margined crypto perpetual futures on Delta Exchange India and CoinDCX, "
      "offered as speculative business income. No virtual digital asset was transferred by the assessee; margin, "
      "profit and loss were settled in rupees. Exchange fees and GST thereon claimed as business expenditure.")
    w("")
    w("**Keep:**")
    w("- this statement (every edition);")
    w("- each exchange's monthly statements and trade, funding and fee reports;")
    w("- the bank statements showing deposits and withdrawals;")
    w("- your AIS / Form 26AS, checked before filing.")
    w("")
    w("**Risk:** if the department treated these contracts as virtual digital assets, the tax would be computed "
      "differently, and much higher. The figures and the reasoning are in `reports/2026-10-09_tax_opinion.md`. That "
      "is the position this statement files on, disclosed openly.")
    w("")
    w("*Prepared by Claude as your tax adviser, not a registered CA. Figures come from the bot's journal. The live "
      "edition is reconciled with the exchanges' own statements.*")
    md = "\n".join(L) + "\n"
    open(base + '.md', 'w').write(md)
    with open(base + '.csv', 'w', newline='') as h:
        cw = csv.writer(h)
        cw.writerow(['kind', 'coin', 'opened_IST', 'closed_IST', 'exchange', 'qty', 'entry_price', 'exit_price',
                     'price_diff_USD', 'funding_received_USD', 'funding_paid_USD', 'gst_on_funding_USD', 'fee_USD',
                     'gst_on_fee_USD', 'slippage_USD', 'net_USD', 'net_INR'])
        for kind, items in (('closed', o['closed']), ('open', o['open'])):
            for item in items:
                r, Lg = item['rec'], item['legs']
                for l, qk, p0, p1 in (('d', 'd_qty', 'd_px0', 'd_px1'), ('b', 'b_qty', 'b_px0', 'b_px1')):
                    x = Lg[l]
                    pr = x['price'] if kind == 'closed' else x['price_open']
                    netx = pr + x['rent_in'] + x['rent_out'] + x['rent_gst'] - x['fee'] - x['fee_gst'] - x['spread'] - x['other']
                    cw.writerow([kind, r.get('coin'), f"{ist(r['opened']):%Y-%m-%d %H:%M}" if r.get('opened') else '',
                                 f"{ist(r['closed']):%Y-%m-%d %H:%M}" if kind == 'closed' else '', x['venue'],
                                 round(float(r.get(qk) or 0), 6), r.get(p0), r.get(p1), round(pr, 6), round(x['rent_in'], 6),
                                 round(x['rent_out'], 6), round(x['rent_gst'], 6), round(x['fee'], 6), round(x['fee_gst'], 6),
                                 round(x['spread'], 6), round(netx, 6), round(rs(netx, inr), 2)])
    return base + '.md', base + '.csv', ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('ledger')
    ap.add_argument('--live', action='store_true')
    ap.add_argument('--ty', default=None)
    ap.add_argument('--inr', type=float, default=DELTA_INR)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'tax'))
    ap.add_argument('--edition', default='1')
    a = ap.parse_args(argv)
    d = load(a.ledger)
    now_ms = int(dt.datetime.utcnow().timestamp() * 1000)
    ty = a.ty or ty_of(now_ms)
    o = build(d, ty, a.live, a.inr)
    md, cv, ok = write(d, o, ty, a.live, a.inr, a.out, a.edition, f"{ist(now_ms):%d %b %Y %H:%M}")
    T = o['totals']
    print(f"tax year {ty} ({'LIVE' if a.live else 'PAPER'}): net Rs {fmt(rs(T['net'], a.inr))} "
          f"(gross Rs {fmt(rs(T['gross'], a.inr))}, expenditure Rs {fmt(rs(T['expenditure'], a.inr))}, turnover Rs "
          f"{fmt(rs(T['turnover'], a.inr))}); {len(o['closed'])} closed, {len(o['open'])} open; checks {'OK' if ok else 'FAILED'}"
          f"{'; paper carry-in Rs ' + fmt(rs(o['carried'], a.inr)) if o['carried'] else ''}")
    print(md); print(cv)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
