#!/usr/bin/env python3
"""C544/C545: the operator's income statement for ITR-3 -- the Delta Exchange India + CoinDCX rent-gap trade.

    python3 omega_tax_statement.py LEDGER.json [--live] [--ty 2026-27] [--inr 85] [--out DIR] [--edition N]
                                   [--private DIR] [--profile FILE] [--xrec FILE]
    python3 omega_tax_statement.py --setup [--private DIR]          (once, on the server: your name, PAN and accounts)

LEDGER.json is the plan's ledger (data/c524_xvenue.json on the server; logs/c524_xvenue.json on the logs branch).
It writes ITR_TY<ty>_rent_gap_<PAPER|LIVE>.md, a .csv (one row per leg) and a .json (the filing figures, and the
losses carried forward, which next year's statement reads), in one fixed format of 13 sections:
  1 the assessee and the accounts       2 the nature and source of the income   3 the summary for the tax year
  4 exchange by exchange                5 month by month                        6 the register of closed positions
  7 positions open at 31 March          8 money moved between the exchanges     9 the tax computation
  10 reconciliation and year-end balances                                       11 the note for the return, records
  12 the ITR-3 filing sheet, field by field                                     13 the handover pack for the filing CA
PAPER: a rehearsal on the bot's paper ledger -- no real money, NOT FOR FILING. LIVE: the same format, started afresh
on the day real trading starts, from the real fills, rent and fees.

C545 -- complete for filing. The operator (9 Oct 2026): "make sure that the above income document is complete in the
sense that i won't have to fill in any transaction details myself or anything else ... so that ... i can hand it over
straight ... to a third party CA who will only help in filing itr". So the statement also carries every ITR-3 field
this income touches (section 12), the 31 March balances the no-accounts balance sheet asks for, losses brought and
carried forward year to year, the reconciliation with each exchange's own records (live), and a completeness check
naming who closes each open item (section 13). Identity (name, PAN, account IDs) is read from a private file on the
server (data/tax/taxpayer.json, chmod 600, never in git): the copy written there is in full; any copy written
elsewhere is masked.

Rupees: Delta India settles at a fixed Rs 85 per dollar and CoinDCX at Rs 102 per USDT. Live legs are matched in rupees
(the CoinDCX leg's USDT size = the Delta leg's dollars x 85/102), so a pair's rupee figures are its dollar figures x 85.
The paper ledger's legs are equal in dollars; the statement converts them as if rupee-matched (x 85 throughout).
Tax: the opinion in reports/2026-10-09_tax_opinion.md -- speculative business income (ITR-3, Schedule BP), both legs of
both exchanges netted in the year, no TDS, never the VDA schedule. Not a registered CA's certificate.
"""
import os, re, sys, json, csv, argparse, datetime as dt

IST = 19800
TAX = 0.312
DELTA_INR = 85.0          # Delta India's fixed rate (public /v2/settings: fiat_to_usd.asset_to_fiat_value = 85, 9 Oct 2026)
DCX_INR = 102.0           # CoinDCX's fixed rate for INR-margined futures (its support page, 8 Oct 2026)
BIZ_CODE = '21009'        # ITR business code "Speculative trading" (added for AY 2025-26; confirmed each year in the utility)
BOOKS_INCOME = 250000     # 2025 Act s.62 / Rule 46 (1961 Act s.44AA(2)): books compulsory for an individual whose business
BOOKS_TURNOVER = 2500000  # income > Rs 2.5 lakh or turnover > Rs 25 lakh in any of the three preceding years
AUDIT_TURNOVER = 100000000  # 2025 Act s.63 (1961 s.44AB): Rs 10 crore when cash is <= 5% of receipts and payments
AL_INCOME = 5000000       # Schedule AL (assets and liabilities) when total income > Rs 50 lakh
ADV_MIN = 10000           # advance tax when the year's tax not covered by TDS exceeds Rs 10,000
SPEC_CF_YEARS = 4         # a speculative loss is carried forward 4 years (1961 s.73(4); 2025 Act s.113)
HERE = os.path.dirname(os.path.abspath(__file__))
PAN_RE = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
TAXPAYER_FIELDS = (
    ('name', 'Your name, exactly as on your PAN card'),
    ('pan', 'Your PAN (10 characters, e.g. ABCDE1234F)'),
    ('delta_account', 'Delta Exchange India: the e-mail or user ID you log in with'),
    ('coindcx_account', 'CoinDCX: the e-mail or user ID you log in with'),
    ('bank', 'The bank account linked to both exchanges, as "Bank name, account ending 1234" (last 4 digits only)'))
DEFAULT_PROFILE = dict(
    business_code=BIZ_CODE, business_code_confirmed={},     # {ty: 'checked in the ITR-3 utility on <date>'}
    description='Trading in rupee-settled crypto perpetual futures on Delta Exchange India and CoinDCX (speculative)',
    due_date={},              # {ty: 'YYYY-MM-DD'}: the year's legal due date for a non-audit ITR-3, once notified
    filed={},                 # {ty: 'YYYY-MM-DD'}: when that year's return was filed (from its acknowledgement)
    expenses=[],              # other business expenses (live only), e.g. dict(what='server rent', inr_per_month=500,
                              #   frm='2027-02', to='', evidence='monthly invoice e-mail')
    exchanges=dict(delta=dict(name='Delta Exchange India', entity='', fiu=''),
                   coindcx=dict(name='CoinDCX', entity='Neblio Technologies Pvt Ltd', fiu='VA00030982')),
    started_live='',          # 'YYYY-MM-DD': the first real trade (the business commenced)
    reviews=[])               # dict(ty=, kind=, edition=, date=, note=): editions reviewed with the operator


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


def ty_add(ty, k):
    y = int(ty[:4]) + k
    return f"{y}-{str(y + 1)[2:]}"


def ty_bounds(ty):
    y = int(ty[:4])
    return dt.date(y, 4, 1), dt.date(y + 1, 3, 31)


def ty_ms(ty):
    """the tax year's first and one-past-last instant, in ms (IST midnights)"""
    y = int(ty[:4])
    a = int((dt.datetime(y, 4, 1) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - IST * 1000
    b = int((dt.datetime(y + 1, 4, 1) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - IST * 1000
    return a, b


def rs(x, inr):
    return x * inr


def fmt(x, nd=0):
    s = f"{abs(x):,.{nd}f}"
    return f"-{s}" if x < -0.5 * 10 ** -nd else s


def split_cost(n, f, g, spr):
    """a side's modelled cost on notional n: (fee, GST on the fee, half-spread)"""
    return n * f, n * f * g, n * spr


def mask(k, v):
    """what a copy outside the private folder shows of an identity field"""
    v = str(v or '')
    if not v:
        return ''
    if k == 'pan':
        return v[:2] + '******' + v[-2:]
    if k == 'name':
        return ' '.join(w[0] + '.' for w in v.split() if w)
    if '@' in v:
        a, b = v.split('@', 1)
        return a[:1] + '***@' + b
    if k == 'bank':
        return re.sub(r'\d', '*', v)
    return '***' + v[-3:] if len(v) > 3 else '***'


# ── inputs ───────────────────────────────────────────────────────────────────
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


def load_profile(path):
    p = json.loads(json.dumps(DEFAULT_PROFILE))
    if path and os.path.exists(path):
        try:
            got = json.load(open(path))
            for k, v in got.items():
                if isinstance(v, dict) and isinstance(p.get(k), dict):
                    for a, b in v.items():
                        p[k][a] = (dict(p[k].get(a) or {}, **b) if isinstance(b, dict) and isinstance(p[k].get(a), dict) else b)
                else:
                    p[k] = v
        except Exception as e:
            print(f"profile {path} unreadable ({e}); defaults used", file=sys.stderr)
    return p


def load_taxpayer(path):
    if not path or not os.path.exists(path):
        return None
    try:
        t = json.load(open(path))
        return t if isinstance(t, dict) and t.get('pan') else None
    except Exception:
        return None


def load_xrec(path):
    """the exchanges' own records for the year (live; made from each exchange's statement by the reconcile step):
    {"made": "...", "source": "...", "Delta": {"funding": Rs, "fees": Rs, "realised": Rs, "deposits": Rs,
     "withdrawals": Rs, "balance_ye": Rs}, "CoinDCX": {...}} -- all in rupees, signed as the exchange shows them"""
    if not path or not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except Exception:
        return None


def load_prior(outdir, ty, kind):
    """last year's statement: its losses still carried forward"""
    f = os.path.join(outdir, f"ITR_TY{ty_add(ty, -1)}_rent_gap_{kind}.json")
    if not os.path.exists(f):
        return None
    try:
        return json.load(open(f))
    except Exception:
        return None


def setup(path, answers=None, inp=input, out=print):
    """once, on the server: the identity the statement prints (never in git, never in a log)"""
    cur = load_taxpayer(path) or {}
    t = {}
    for k, q in TAXPAYER_FIELDS:
        if answers is not None:
            v = str(answers.get(k) or '').strip()
        else:
            keep = f" [Enter keeps {mask(k, cur[k])}]" if cur.get(k) else ''
            v = inp(f"{q}{keep}: ").strip()
        v = v or str(cur.get(k) or '')
        if k == 'pan':
            v = v.upper().replace(' ', '')
            if not PAN_RE.match(v):
                raise ValueError("a PAN is 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)")
        if k == 'bank' and re.search(r'\d{5,}', v):
            raise ValueError("only the last 4 digits of the bank account, please")
        if not v:
            raise ValueError(f"'{k}' is needed")
        t[k] = v
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    try:
        os.chmod(os.path.dirname(path) or '.', 0o700)
    except OSError:
        pass
    tmp = path + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as h:
        json.dump(t, h, indent=1)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    out(f"saved {path} (only you can read it): " + ', '.join(f"{k} {mask(k, t[k])}" for k, _ in TAXPAYER_FIELDS))
    return t


# ── the figures ──────────────────────────────────────────────────────────────
def build(d, ty, live, inr, now_ms=None, profile=None, xrec=None, prior=None):
    """everything the statement shows, in dollars (x inr for rupees), for tax year ty"""
    profile = profile or load_profile(None)
    now_ms = int(now_ms or dt.datetime.utcnow().timestamp() * 1000)
    t0, t1 = ty_ms(ty)
    past = now_ms >= t1
    J = d['journal']
    carry = next((r for r in J if r.get('t') == 'carry'), None)
    ye = next((r for r in J if r.get('t') == 'yearend' and r.get('ty') == ty), None)
    v2 = 'CoinDCX' if (d.get('venue') or 'coindcx') == 'coindcx' else (d.get('venue') or 'second').title()
    out = dict(closed=[], open=[], transfers=[], v2=v2, carry=carry, yearend=ye, checks=[], past=past, now_ms=now_ms,
               cut=f"31 Mar {int(ty[:4]) + 1}" if past else f"{ist(now_ms):%d %b %Y}")
    ven = {v: dict(price=0.0, rent_in=0.0, rent_out=0.0, rent_gst=0.0, fee=0.0, fee_gst=0.0, spread=0.0, other=0.0)
           for v in ('Delta', v2)}
    months = {}

    def mrow(m):
        return months.setdefault(m, dict(price=0.0, rent=0.0, fees=0.0, spread=0.0, other=0.0, n_closed=0))

    def costs(r8, n, which):
        f, g = (r8['fd'], r8['gd']) if which == 'd' else (r8['fb'], r8['gb'])
        return split_cost(n, f, g, r8['spr'])

    def legs_of(rec, state, pxo):
        """this tax year's part of one position, per leg. state: 'closed' (closed within the year) or 'open' (open at
        the year's cut-off, whenever it closed later); pxo: each leg's price result not yet realised, if known"""
        res = {}
        r8 = rec.get('rates')
        entry_in = bool(rec.get('opened')) and ty_of(rec['opened']) == ty and not rec.get('carry')
        exit_in = state == 'closed'
        for leg, vname in (('d', 'Delta'), ('b', v2)):
            rin = rout = rgst = 0.0
            k = 0 if leg == 'd' else 3
            for m, row in (rec.get('fm') or {}).items():
                if ty_of_month(m) == ty:
                    rin += row[k]; rout += row[k + 1]; rgst += row[k + 2]
            f_in = g_in = s_in = f_out = g_out = s_out = 0.0
            if r8 and not rec.get('carry'):              # a carried-in pair's entry cost is inside its carry-in
                f_in, g_in, s_in = costs(r8, float(rec.get('n_in') or 0.0), leg)
            if r8 and rec.get('closed') and rec.get('n_out') is not None:
                f_out, g_out, s_out = costs(r8, float(rec.get('n_out') or 0.0), leg)
            fee_total = float(rec.get('fee_' + leg) or 0.0)
            other = fee_total - (f_in + g_in + s_in) - (f_out + g_out + s_out) if r8 else fee_total
            px = float(rec.get('px_' + leg) or 0.0)
            res[leg] = dict(venue=vname, price=(px if exit_in else 0.0),
                            price_open=(float(pxo[leg]) if (state == 'open' and pxo is not None) else 0.0),
                            rent_in=rin, rent_out=rout, rent_gst=rgst,
                            fee=(f_in if entry_in else 0.0) + (f_out if exit_in else 0.0),
                            fee_gst=(g_in if entry_in else 0.0) + (g_out if exit_in else 0.0),
                            spread=(s_in if entry_in else 0.0) + (s_out if exit_in else 0.0),
                            other=(other if (entry_in or (exit_in and rec.get('carry'))) else 0.0),
                            f_in=f_in, g_in=g_in, s_in=s_in, f_out=f_out, g_out=g_out, s_out=s_out,
                            entry_in=entry_in, exit_in=exit_in)
        return res

    def ye_px(coin):
        o = ((ye or {}).get('open') or {}).get(coin)
        return dict(d=o['px_d'], b=o['px_b']) if o else None

    for rec in J:
        if rec.get('t') == 'close':
            op, cl = int(rec.get('opened') or rec['closed']), int(rec['closed'])
            if op >= t1 or cl < t0:
                continue
            if cl < t1:
                out['closed'].append(dict(rec=rec, state='closed', legs=legs_of(rec, 'closed', None)))
            else:                                        # open at 31 March, closed after it
                px = ye_px(rec.get('coin'))
                out['open'].append(dict(rec=rec, state='open', pxo=px, legs=legs_of(rec, 'open', px)))
        elif rec.get('t') == 'transfer' and t0 <= int(rec['ms']) < t1:
            out['transfers'].append(rec)
    for c, p in (d.get('pairs') or {}).items():
        jx = dict(p.get('jx') or {})
        rec = dict(jx, coin=c, side=p.get('side'), d_sym=p.get('d_sym'), d_qty=p.get('d_qty'), b_qty=p.get('b_qty'),
                   cv=p.get('cv'), d_px1=p.get('d_px'), b_px1=p.get('b_px'), pnl=p.get('pnl'), opened=jx.get('opened') or p.get('opened'))
        if rec.get('opened') and int(rec['opened']) >= t1:
            continue                                     # opened after this tax year
        px = ye_px(c) if past else dict(d=float(jx.get('px_d') or 0.0), b=float(jx.get('px_b') or 0.0))
        out['open'].append(dict(rec=rec, state='open', pxo=px, legs=legs_of(rec, 'open', px)))
    # each leg into its exchange's totals; rent by the month it was paid; fees, GST, slippage by the month they were paid
    turnover = 0.0
    for item in out['closed'] + out['open']:
        rec, L = item['rec'], item['legs']
        for m, row in (rec.get('fm') or {}).items():
            if ty_of_month(m) == ty:
                mrow(m)['rent'] += sum(row)
        if item['state'] == 'closed':
            mm = mrow(ist(rec['closed']).strftime('%Y-%m'))
            mm['n_closed'] += 1
            mm['price'] += L['d']['price'] + L['b']['price']
        for leg in ('d', 'b'):
            x = L[leg]
            v = ven[x['venue']]
            for k in ('price', 'rent_in', 'rent_out', 'rent_gst', 'fee', 'fee_gst', 'spread', 'other'):
                v[k] += x[k]
            turnover += abs(x['price'] + x['rent_in'] + x['rent_out'] + x['rent_gst'])
            if x['entry_in']:
                mm = mrow(ist(rec['opened']).strftime('%Y-%m'))
                mm['fees'] += x['f_in'] + x['g_in']; mm['spread'] += x['s_in']; mm['other'] += x['other']
            if x['exit_in']:
                mm = mrow(ist(rec['closed']).strftime('%Y-%m'))
                mm['fees'] += x['f_out'] + x['g_out']; mm['spread'] += x['s_out']
                if rec.get('carry'):
                    mm['other'] += x['other']
    for t in out['transfers']:
        mrow(ist(t['ms']).strftime('%Y-%m'))['other'] += float(t.get('fee') or 0.0)
    # other business expenses (live only: before the first real trade there is no business to charge them to)
    exp_rows, exp_usd = [], 0.0
    if live:
        last_m = (ist(min(now_ms, t1 - 1))).strftime('%Y-%m')
        for e in profile.get('expenses') or []:
            frm, to = str(e.get('frm') or ''), str(e.get('to') or '') or last_m
            ms_ = [m for m in _months(ty) if frm <= m <= min(to, last_m)]
            amt = float(e.get('inr_per_month') or 0.0) * len(ms_)
            if amt:
                exp_rows.append(dict(what=e.get('what', 'expense'), months=len(ms_), inr=amt, evidence=e.get('evidence', '')))
                exp_usd += amt / inr
                for m in ms_:
                    mrow(m)['other'] += float(e.get('inr_per_month') or 0.0) / inr
    out['expenses'] = exp_rows
    out['venue'] = ven
    out['months'] = dict(sorted(months.items()))
    tf = sum(float(t.get('fee') or 0.0) for t in out['transfers'])
    tot = {k: sum(v[k] for v in ven.values()) for k in ven['Delta']}
    gross = tot['price'] + tot['rent_in'] + tot['rent_out'] + tot['rent_gst'] - tot['spread']
    expend = tot['fee'] + tot['fee_gst'] + tot['other'] + tf + exp_usd
    out['totals'] = dict(tot, transfer_fees=tf, other_exp=exp_usd, turnover=turnover, gross=gross, expenditure=expend,
                         net=gross - expend,
                         unrealised=sum(item['legs'][l]['price_open'] for item in out['open'] for l in 'db'))
    out['unrealised_known'] = all(item.get('pxo') is not None for item in out['open'])
    # the carried-in paper result (before the journal) -- paper only, whole and unsplit
    out['carried'] = (float(carry['eq']) - float(carry['start'])) if (carry and not live and t0 <= int(carry['ms']) < t1) else 0.0
    # checks: each journaled position's own sum == the ledger's figure for it
    for item in out['closed'] + out['open']:
        rec = item['rec']
        if not rec.get('rates'):
            continue
        fm_all = sum(sum(row) for row in (rec.get('fm') or {}).values())
        mine = float(rec.get('px_d') or 0) + float(rec.get('px_b') or 0) + fm_all - float(rec.get('fee_d') or 0) - float(rec.get('fee_b') or 0)
        led = float(rec.get('pnl') or 0.0) - float(((rec.get('carry') or {}).get('pnl')) or 0.0)
        out['checks'].append((rec.get('coin'), abs(mine - led) < 1e-6, mine, led))
    out['balances'] = _balances(d, out, ye, past, xrec, inr, v2)
    out['xrec'] = _xrec_rows(out, xrec, inr, v2) if xrec else None
    # the tax year's figures in rupees, as filed (paper: the carry-in from before the journal stays outside them)
    R = lambda x: round(rs(x, inr))
    T = out['totals']
    net_inr = R(T['net'])
    out['inr'] = dict(turnover=R(T['turnover']), gross=R(T['gross']), expenditure=R(T['expenditure']), net=net_inr)
    # losses: brought forward from last year's statement, set off against this year's speculative profit, carried on
    bf = [dict(l) for l in ((prior or {}).get('losses_cf') or []) if str(l.get('last_ty')) >= ty]
    avail, setoff = max(0, net_inr), []
    for l in sorted(bf, key=lambda z: z['ty']):
        use = min(avail, int(l['amount']))
        if use:
            setoff.append(dict(ty=l['ty'], used=use))
            l['amount'] = int(l['amount']) - use
            avail -= use
    cf = [l for l in bf if int(l['amount']) > 0]
    if net_inr < 0:
        cf.append(dict(ty=ty, amount=-net_inr, last_ty=ty_add(ty, SPEC_CF_YEARS)))
    out['bf'], out['setoff'], out['cf'] = bf, setoff, cf
    out['taxable'] = max(0, net_inr) - sum(s['used'] for s in setoff)
    out['tax'] = round(out['taxable'] * TAX)
    # books (s.44AA / 2025 Act s.62): this year or any of the three before it over a limit (conservative for a new business)
    hist = [h for h in ((prior or {}).get('history') or []) if isinstance(h, dict)][:3]
    out['history'] = [dict(ty=ty, turnover=out['inr']['turnover'], net=net_inr)] + hist
    out['books'] = any(h['turnover'] > BOOKS_TURNOVER or h['net'] > BOOKS_INCOME for h in out['history'])
    out['audit'] = out['inr']['turnover'] > AUDIT_TURNOVER
    out['prior_found'] = prior is not None
    return out


def _months(ty):
    y = int(ty[:4])
    return [f"{y}-{m:02d}" for m in range(4, 13)] + [f"{y + 1}-{m:02d}" for m in range(1, 4)]


def _balances(d, o, ye, past, xrec, inr, v2):
    """money held at each exchange at the cut-off (the wallet: equity less the open positions' unrealised price result)"""
    res = dict(src=None)
    if xrec and all((xrec.get(v) or {}).get('balance_ye') is not None for v in ('Delta', v2)):
        res.update(src='exchange', d=float(xrec['Delta']['balance_ye']), b=float(xrec[v2]['balance_ye']))
    if ye:
        ud = sum(float(x.get('px_d') or 0) for x in (ye.get('open') or {}).values())
        ub = sum(float(x.get('px_b') or 0) for x in (ye.get('open') or {}).values())
        res.update(ledger=dict(d=(float(ye['d']) - ud) * inr, b=(float(ye['b']) - ub) * inr, asof=ye.get('asof')))
    elif not past and d.get('start_equity'):
        half0 = float(d['start_equity']) / 2.0
        sd = d.get('side') or {}
        ud = sum(float((p.get('jx') or {}).get('px_d') or 0) for p in (d.get('pairs') or {}).values())
        ub = sum(float((p.get('jx') or {}).get('px_b') or 0) for p in (d.get('pairs') or {}).values())
        res.update(ledger=dict(d=(half0 + float(sd.get('d') or 0) - ud) * inr, b=(half0 + float(sd.get('b') or 0) - ub) * inr,
                               asof=o['cut']))
    if res['src'] is None and res.get('ledger'):
        res.update(src='ledger', d=res['ledger']['d'], b=res['ledger']['b'])
    return res


def _xrec_rows(o, xrec, inr, v2):
    """the journal's figures beside each exchange's own, in rupees (agree = within Rs 10 a line)"""
    rows = []
    for v in ('Delta', v2):
        x = xrec.get(v) or {}
        V = o['venue'][v]
        mine = dict(funding=(V['rent_in'] + V['rent_out'] + V['rent_gst']) * inr, fees=-(V['fee'] + V['fee_gst']) * inr,
                    realised=V['price'] * inr)
        for k, lab in (('realised', 'price differences realised'), ('funding', 'funding (net, GST included)'),
                       ('fees', 'trading fees + GST')):
            if x.get(k) is None:
                continue
            ex = float(x[k])
            rows.append(dict(venue=v, what=lab, mine=mine[k], theirs=ex, ok=abs(mine[k] - ex) <= 10.0))
    return rows


# ── the statement ────────────────────────────────────────────────────────────
def completeness(o, live, ty, profile, taxpayer, kind):
    """every item a filing needs, done or not, and who closes it"""
    rev = [r for r in profile.get('reviews') or [] if r.get('ty') == ty and r.get('kind') == kind]
    sl = str(profile.get('started_live') or '')
    prev_needed = live and len(sl) >= 7 and ty_of_month(sl[:7]) < ty          # a live year before this one exists
    items = [
        ("Every position journaled and agreeing with the bot's ledger", all(c[1] for c in o['checks']), "the bot, every day"),
        ("Each exchange's own statement reconciled (section 10)",
         bool(o['xrec']) and all(r['ok'] for r in o['xrec']) if live else None, "the reconcile step (B3), daily from live day"),
        ("Balances at 31 March from the exchanges (Part A-BS)",
         (o['balances'].get('src') == 'exchange') if (live and o['past']) else None,
         "the reconcile step, on 1 April; until then the bot's own figure is shown"),
        ("Your name, PAN and account IDs on the server copy (section 1)", bool(taxpayer),
         "you, once, with --setup (about 2 minutes; optional, the portal knows your PAN)"),
        ("Business code confirmed in this year's ITR-3 utility",
         bool((profile.get('business_code_confirmed') or {}).get(ty)), "me, at the June review before filing"),
        ("This year's legal due date confirmed", bool((profile.get('due_date') or {}).get(ty)), "me, when the CBDT notifies it"),
        ("Losses brought forward from earlier years (Schedule BFLA / CFL)",
         o['prior_found'] if prev_needed else True, "this statement, from last year's .json (it must sit beside this one)"),
        ("Delta Exchange India's operating company and FIU-IND number",
         bool(((profile.get('exchanges') or {}).get('delta') or {}).get('entity')), "me, from Delta's terms page, at live day"),
        ("Reviewed with your adviser before handover", bool(rev), "you and me, in June before filing"),
    ]
    return items, rev


def write(d, o, ty, live, inr, outdir, edition, asof, profile=None, taxpayer=None, private=False):
    profile = profile or load_profile(None)
    os.makedirs(outdir, exist_ok=True)
    kind = 'LIVE' if live else 'PAPER'
    base = os.path.join(outdir, f"ITR_TY{ty}_rent_gap_{kind}")
    T, v2, I = o['totals'], o['v2'], o['inr']
    y0, y1 = ty_bounds(ty)
    R = lambda x: fmt(rs(x, inr))
    N = lambda x: fmt(x)                                   # already rupees
    due = (profile.get('due_date') or {}).get(ty)
    due_txt = (f"{dt.date.fromisoformat(due):%d %b %Y}" if due else
               f"plan **31 Jul {int(ty[:4]) + 1}** (the legal date for a non-audit ITR-3 is confirmed when notified)")
    code_ok = (profile.get('business_code_confirmed') or {}).get(ty)
    code = profile.get('business_code') or BIZ_CODE
    code_txt = f"**{code}** — Speculative trading" + ('' if code_ok else " (confirmed in the year's utility before filing)")
    bal = o['balances']
    debt = (bal['d'] + bal['b']) if bal.get('src') else None
    if bal.get('src') == 'exchange':
        bal_src = "each exchange's own statement at 31 March 23:59 IST"
    elif bal.get('src') == 'ledger':
        bal_src = (f"the bot's year-end record (its last mark, {bal['ledger']['asof']}); live, replaced by the exchanges' figure"
                   if o['past'] else f"the bot's ledger at the cut-off ({o['cut']}); at 31 March, the year-end figure")
    else:
        bal_src = "not available yet"
    items, rev = completeness(o, live, ty, profile, taxpayer, kind)
    n_done = sum(1 for _, v, _ in items if v)
    n_need = sum(1 for _, v, _ in items if v is not None)
    tp = taxpayer or {}
    idv = (lambda k: tp.get(k, '')) if private else (lambda k: mask(k, tp.get(k, '')))
    L = []
    w = L.append
    w("# Income statement for ITR-3: speculative business income from rupee-settled crypto futures")
    w("")
    w(f"**Tax year {ty}** ({y0:%d %b %Y} – {y1:%d %b %Y}) · **{kind}** · edition {edition} · prepared {asof} IST · "
      f"amounts in **₹** (Delta India's fixed rate ₹{inr:.0f} per dollar)" + ("" if o['past'] else f" · year to date, cut-off {o['cut']}"))
    w("")
    if live:
        w("> **LIVE.** Real trades only, from the day live trading started. Section 12 gives every ITR-3 field this "
          "income touches; section 13 is the handover to the CA who files the return.")
    else:
        w("> **PAPER — NOT FOR FILING.** This is a rehearsal on the bot's paper ledger: no real money moved, so there is "
          "no income to declare. It is kept in exactly the format the live statement will use. The live statement "
          "starts afresh, from zero, on the first real trade.")
    w("")
    w("### For the filing CA — at a glance")
    w("")
    w("| | |")
    w("|---|---|")
    w("| Return | **ITR-3** (business income; the trade is speculative business) |")
    w(f"| Business code | {code_txt} |")
    w(f"| P&L, no-accounts case, speculative activity | turnover **₹{N(I['turnover'])}** · gross profit **₹{N(I['gross'])}** · "
      f"expenditure **₹{N(I['expenditure'])}** · net **₹{N(I['net'])}** |")
    w(f"| Balance sheet, no-accounts case (31 March) | sundry debtors **{'₹' + N(debt) if debt is not None else 'pending'}** "
      f"(money held by the two exchanges) · creditors 0 · stock 0 · cash 0 |")
    w(f"| Books (s.44AA / 2025 Act s.62) · audit (s.44AB / s.63) | **{'required' if o['books'] else 'not required'}** · "
      f"**{'required' if o['audit'] else 'not required'}** |")
    w("| Schedule VDA · TDS on this income | **nil — do not use Schedule VDA** · **none** (check AIS) |")
    cf_txt = '; '.join(f"₹{N(l['amount'])} of {l['ty']} (usable to {l['last_ty']})" for l in o['cf']) or 'none'
    w(f"| Losses carried forward (Schedule CFL) | {cf_txt} |")
    w(f"| Due date | {due_txt} — on time keeps any loss carried forward |")
    w(f"| Complete? | **{n_done} of {n_need}** items done — the list, and who closes each, is in section 13 |")
    w("")
    w("## 1. Assessee and accounts")
    w("")
    w("| | |")
    w("|---|---|")
    if tp:
        w(f"| Name · PAN | {idv('name')} · {idv('pan')}{'' if private else ' *(masked here; in full on the server copy)*'} |")
    elif private:
        w("| Name · PAN | *not set yet: run `--setup` once on the server (optional: the portal pre-fills your name and PAN)* |")
    else:
        w("| Name · PAN | *in full on the server copy (data/tax/), never in git; the portal also pre-fills them* |")
    w("| Residential status | Resident individual |")
    dx = (profile.get('exchanges') or {}).get('delta') or {}
    cx = (profile.get('exchanges') or {}).get('coindcx') or {}
    dx_ent = f": {dx['entity']}" + (f", FIU-IND reg. {dx['fiu']}" if dx.get('fiu') else '') if dx.get('entity') else ''
    cx_ent = f": {cx.get('entity')}" + (f", FIU-IND reg. {cx['fiu']}" if cx.get('fiu') else '') if cx.get('entity') else ''
    w(f"| Accounts used | **Delta Exchange India**{dx_ent} (login: {idv('delta_account') or '*server copy*'}) · "
      f"**CoinDCX**{cx_ent} (login: {idv('coindcx_account') or '*server copy*'}) |")
    w(f"| Bank account | {idv('bank') or '*server copy*'} — the one linked to both exchanges for rupee deposits and withdrawals |")
    w(f"| Business | {profile.get('description')} · code {code} · "
      + (f"commenced {profile['started_live']} (first real trade)" if (live and profile.get('started_live')) else
         ('commenced on the first real trade' if live else 'not commenced (paper)')) + " |")
    books_txt = ("this statement (made from the bot's journal of every leg, rent payment and fee), each exchange's "
                 "statements and the bank statements; not required by law at this size" if not o['books'] else
                 "REQUIRED this year (section 12): the bot's journal, this statement and the exchanges' statements are the books")
    w(f"| Books | {books_txt} |")
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
    w("- **When income arises:** funding is income when it is credited (each payment, in the month it is paid, IST); a "
      "position's price difference is income when the position is closed. Positions open on 31 March are not income "
      "until they close (section 7).")
    w("")
    w("## 3. Summary for the tax year (₹)")
    w("")
    w("| | ₹ | ITR-3 field |")
    w("|---|---:|---|")
    w(f"| **A. Turnover** (each leg's difference, + and − alike) | {R(T['turnover'])} | P&L: speculative activity — turnover |")
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
    if abs(rs(T['other'], inr)) >= 0.5:
        w(f"| Other exchange charges | {R(-T['other'])} | |")
    for e in o['expenses']:
        w(f"| {e['what']} ({e['months']} months; evidence: {e['evidence'] or 'invoices'}) | {N(-e['inr'])} | |")
    w(f"| **C. Expenditure** | **{R(-T['expenditure'])}** | P&L: speculative activity — expenditure |")
    w(f"| **D. Net income from speculative business (B − C)** | **{R(T['net'])}** | Schedule BP: income from speculative business |")
    if not live and o['carried']:
        w(f"| *Paper result before the journal began (carried in whole, marked to market, not split)* | *{R(o['carried'])}* | *(paper only)* |")
    w(f"| *Open positions, unrealised (not income until closed)* | *{R(T['unrealised']) if o['unrealised_known'] else 'see section 7'}* | *(not reported)* |")
    w("")
    w("*Turnover method:* ICAI Guidance Note on Tax Audit — for speculative transactions, the total of favourable and "
      "unfavourable differences. Each leg of each position is one transaction; its difference is its price difference "
      "plus its funding. GST paid on fees and funding is an expense (no GST registration, so no input credit).")
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
    if bal.get('src'):
        w(f"| money held at 31 March{'' if o['past'] else ' (so far: at the cut-off)'} | {N(bal['d'])} | {N(bal['b'])} | {N(bal['d'] + bal['b'])} |")
    w("")
    w("## 5. Month by month (₹, IST months)")
    w("")
    w("| month | positions closed | price differences | funding (net) | fees + GST | slippage, transfer and other charges | net |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for m, r in o['months'].items():
        net = r['price'] + r['rent'] - r['fees'] - r['spread'] - r['other']
        w(f"| {m} | {r['n_closed']} | {R(r['price'])} | {R(r['rent'])} | {R(-r['fees'])} | {R(-(r['spread'] + r['other']))} | {R(net)} |")
    if not o['months']:
        w("| — | 0 | 0 | 0 | 0 | 0 | 0 |")
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
    if not live and o['carry'] and o['carry'].get('closed') and o['carried']:
        cl = o['carry']['closed']
        w("")
        w(f"*Paper only, before the journal: {len(cl)} positions closed with net ₹{R(sum(float(x.get('pnl') or 0) for x in cl))} "
          f"(fees included); their leg detail was not recorded.*")
    w("")
    w(f"## 7. Positions open at the cut-off ({o['cut']}) (₹) — not income until closed")
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
        later = f" *(closed {ist(r['closed']):%d %b %Y}: next year's income)*" if r.get('closed') else ''
        pu = R(Lg['d']['price_open'] + Lg['b']['price_open']) if item.get('pxo') is not None else '—'
        w(f"| {r['coin']} | {op} | {pos} | {R(rent)} | {pu}{extra}{later} |")
    if not o['open']:
        w("| — | | | | |")
    w("")
    w("## 8. Money moved between the exchanges (not income; only the charges are expenses)")
    w("")
    w("| date | from | to | amount | charge |")
    w("|---|---|---|---:|---:|")
    for t in o['transfers']:
        w(f"| {ist(t['ms']):%d %b %Y} | {t['frm']} | {t['to']} | {R(float(t['amt']))} | {R(float(t.get('fee') or 0))} |")
    if not live and o['carry'] and o['carried']:
        for t in o['carry'].get('transfers') or []:
            w(f"| {t.get('at', '')[:10]} *(paper, before the journal)* | {t.get('frm')} | {t.get('to')} | {R(float(t.get('amt') or 0))} | {R(float(t.get('fee') or 0))} |")
    if not o['transfers'] and not (not live and o['carry'] and o['carried'] and o['carry'].get('transfers')):
        w("| — | | | | |")
    w("")
    w("## 9. Tax computation")
    w("")
    w("| | ₹ |")
    w("|---|---:|")
    w(f"| Net income from speculative business | {N(I['net'])} |")
    for s in o['setoff']:
        w(f"| less: speculative loss brought forward from {s['ty']} (Schedule BFLA) | {N(-s['used'])} |")
    w(f"| Taxable speculative income | {N(o['taxable'])} |")
    w(f"| Tax at your slab rate, 30% + 4% cess = 31.2% (no surcharge) | {N(o['tax'])} |")
    if o['tax'] > ADV_MIN:
        y = int(ty[:4])
        sched = ' · '.join(f"{lab} {y + (1 if lab.endswith('Mar') else 0)}: ₹{N(round(o['tax'] * p))}" for lab, p in
                           (('15 Jun', 0.15), ('15 Sep', 0.45), ('15 Dec', 0.75), ('15 Mar', 1.0)))
        w(f"| Advance tax (cumulative by each date) | {sched} |")
        w("| Or, instead | declare this income to your employer (1961 s.192(2B)) and let salary TDS cover it |")
    else:
        w("| Advance tax | not needed (under ₹10,000); pay as self-assessment tax before filing |")
    if I['net'] < 0:
        w(f"| Loss | ₹{N(-I['net'])}: carried forward to {ty_add(ty, SPEC_CF_YEARS)} against speculative profit only — file on time |")
    if not live and o['carried']:
        w(f"| *Paper result before the journal (₹{R(o['carried'])}): not split into legs, so left out of every figure above* | *(paper only)* |")
    w("")
    w("## 10. Reconciliation, and the year-end balances")
    w("")
    ok = all(c[1] for c in o['checks'])
    w(f"- **Bot's ledger:** every journaled position's own figures (price + funding − fees) equal the ledger's result for "
      f"it: **{'yes' if ok else 'NO'}** ({sum(1 for c in o['checks'] if c[1])} of {len(o['checks'])}).")
    if not live and o['carry'] and o['carried']:
        c = o['carry']
        w(f"- Paper ledger at the start of the journal ({ist(c['ms']):%d %b %Y %H:%M} IST): equity ₹{R(float(c['eq']))} "
          f"from ₹{R(float(c['start']))}; fees ₹{R(float(c['fees']))}, funding ₹{R(float(c['funding']))}, "
          f"price ₹{R(float(c['price']))}, transfer charges ₹{R(float(c['transfer_fees']))}.")
    if not live:
        w(f"- Paper ledger now: equity ₹{R(float(d.get('eq') or 0))} (start ₹{R(float(d.get('start_equity') or 0))}).")
    if o['xrec']:
        w("- **Each exchange's own records** (from its statement, read-only):")
        w("")
        w("| exchange | what | this statement | the exchange's | agrees |")
        w("|---|---|---:|---:|---|")
        for r in o['xrec']:
            w(f"| {r['venue']} | {r['what']} | {N(r['mine'])} | {N(r['theirs'])} | {'yes' if r['ok'] else '**NO — explained below**'} |")
        w("")
    elif live:
        w("- **Each exchange's own records:** not reconciled yet — the reconcile step (B3) adds this table.")
    else:
        w("- **Each exchange's own records:** not applicable (paper). Live, each exchange's funding, fees and realised "
          "results are set beside this statement's, line by line.")
    w(f"- **Money held at the exchanges** ({bal_src}): "
      + (f"Delta ₹{N(bal['d'])} · {v2} ₹{N(bal['b'])} · total **₹{N(bal['d'] + bal['b'])}**. This is the no-accounts "
         "balance sheet's *sundry debtors* (section 12): money the exchanges hold for you, not cash." if bal.get('src')
         else "pending."))
    if bal.get('src') == 'exchange' and bal.get('ledger'):
        w(f"  The bot's own figure: Delta ₹{N(bal['ledger']['d'])} · {v2} ₹{N(bal['ledger']['b'])}.")
    w("")
    w("## 11. Note for the return, and the records to keep")
    w("")
    w("**Suggested note** (keep with your records; add to the return where a remarks field exists):")
    w("")
    w("> Income from trading in cash-settled, INR-margined crypto perpetual futures on Delta Exchange India and CoinDCX, "
      "offered as speculative business income. No virtual digital asset was transferred by the assessee; margin, "
      "profit and loss were settled in rupees. Exchange fees and GST thereon claimed as business expenditure.")
    w("")
    w("**Keep (8 years):**")
    w("- this statement (every edition), with its .csv and .json;")
    w("- each exchange's statements for the year: trades, funding and fees;")
    w("- the bank statements showing deposits to and withdrawals from the exchanges;")
    w("- your AIS / Form 26AS, checked before filing.")
    w("")
    w("**Risk:** if the department treated these contracts as virtual digital assets, the tax would be computed "
      "differently, and much higher. The figures and the reasoning are in `reports/2026-10-09_tax_opinion.md`. That "
      "is the position this statement files on, disclosed openly.")
    w("")
    # ── 12: the filing sheet ──
    w("## 12. ITR-3 filing sheet — every field this income touches (₹, whole rupees)")
    w("")
    w("Field names are the AY 2025-26 ITR-3's. The tax year 2026-27 forms (the first under the 2025 Act) are checked in "
      "June before filing, and this sheet is updated if a name or number moves.")
    w("")
    w("| where | field | enter | why |")
    w("|---|---|---:|---|")
    w(f"| Part A-GEN | Nature of business: code · trade name · description | {code} · — · {profile.get('description')} | "
      f"{'confirmed in the utility' if code_ok else 'code 21009 = Speculative trading; confirmed in the year’s utility before filing'} |")
    w(f"| Part A-GEN | Liable to maintain accounts u/s 44AA (2025 Act s.62)? | **{'Yes' if o['books'] else 'No'}** | "
      f"income ₹{N(max(0, I['net']))} (limit ₹2,50,000) · turnover ₹{N(I['turnover'])} (limit ₹25,00,000), this and the 3 preceding years |")
    w(f"| Part A-GEN | Liable to audit u/s 44AB (2025 Act s.63)? | **{'Yes' if o['audit'] else 'No'}** | "
      f"turnover ₹{N(I['turnover'])} (limit ₹10 crore; all money moves by bank); presumptive income (44AD) never opted |")
    w("| Part A-GEN | Income declared under presumptive sections 44AD / 44ADA / 44AE? | **No** | declared at actual; "
      "do not opt for 44AD (opting out later locks it for 5 years) |")
    w("| Part A-P&L, no-accounts case | Business other than speculative: gross receipts · gross profit · expenses · net | "
      "0 · 0 · 0 · 0 | this trade is entirely speculative |")
    w(f"| Part A-P&L, no-accounts case | **Speculative activity: turnover** | **{N(I['turnover'])}** | section 3, line A |")
    w(f"| Part A-P&L, no-accounts case | **Speculative activity: gross profit** | **{N(I['gross'])}** | section 3, line B |")
    w(f"| Part A-P&L, no-accounts case | **Speculative activity: expenditure** | **{N(I['expenditure'])}** | section 3, line C |")
    w(f"| Part A-P&L, no-accounts case | **Speculative activity: net income** | **{N(I['net'])}** | section 3, line D |")
    w(f"| Part A-BS, no-accounts case (31 March) | Sundry debtors | **{N(debt) if debt is not None else 'pending'}** | "
      "money held by the two exchanges (section 10) |")
    w("| Part A-BS, no-accounts case | Sundry creditors · stock-in-trade · cash balance | 0 · 0 · 0 | nothing owed; "
      "futures are not stock; no cash is used |")
    w("| Part A-OI · Part A-QD | other information · quantitative details | not filled | only for audited accounts / goods |")
    w(f"| Schedule BP, speculative business | Net profit or loss from speculative business (as per P&L) | **{N(I['net'])}** | section 3, line D |")
    w("| Schedule BP, speculative business | Additions · deductions | 0 · 0 | no disallowance: fees and GST are wholly for "
      "the business; no depreciation, no STT |")
    w(f"| Schedule BP, speculative business | Income from speculative business | **{N(max(0, I['net']))}** | "
      + ("a loss goes to CFL" if I['net'] < 0 else "taxed at the slab rate") + " |")
    w(f"| Schedule CYLA | Speculative loss set off against other heads | **0** | not allowed (s.73 / 2025 Act s.113) |")
    if o['setoff']:
        for s in o['setoff']:
            w(f"| Schedule BFLA | Speculative loss of {s['ty']} set off | **{N(s['used'])}** | last year's statement |")
    else:
        w("| Schedule BFLA | Brought-forward speculative loss set off | **0** | " +
          ("none brought forward" if not o['bf'] else "no profit this year to set it against") + " |")
    if o['cf']:
        for l in o['cf']:
            fd = (profile.get('filed') or {}).get(l['ty'])
            w(f"| Schedule CFL | Speculative loss of {l['ty']} carried forward | **{N(l['amount'])}** | usable to {l['last_ty']}; "
              f"return for {l['ty']} filed {fd or 'on time (date recorded once filed)'} |")
    else:
        w("| Schedule CFL | Speculative loss carried forward | **0** | none |")
    w(f"| Schedule TDS2 · TCS | Tax deducted / collected on this income | **0** | neither exchange deducts TDS on these "
      "contracts; anything in AIS is matched first |")
    w("| Schedule IT | Advance tax and self-assessment tax | as pre-filled from Form 26AS | the challans you paid for this "
      f"income (section 9: ₹{N(o['tax'])} for the year) |")
    w("| Schedule VDA | Income from transfer of virtual digital assets | **nil — leave empty** | no VDA is transferred "
      "(section 2); filling it would itself declare a VDA |")
    w("| Schedule CG · OS · SI | capital gains · other sources · special-rate income | nothing from this trade | slab rate, "
      "business head |")
    w("| Schedule FA | Foreign assets | **nil for this trade** | both exchanges are Indian, accounts held in rupees |")
    w(f"| Schedule AL | Assets and liabilities (only if total income > ₹50 lakh) | {N(debt) if debt is not None else 'pending'} "
      "as deposits | the same exchange balances |")
    w("| Tax regime | as for your whole return | your choice | with business income, opting for the old regime needs "
      "Form 10-IEA (or its 2026 Rules successor) by the due date; switching back is allowed once |")
    w(f"| Filing | due date | {due_txt} | a loss is carried forward only if filed by the due date |")
    w("")
    # ── 13: the handover ──
    w("## 13. Handover pack for the filing CA")
    w("")
    w("**To the CA who files this return:** this statement is complete for this income. Please:")
    w("1. file **ITR-3** and enter the section 12 figures as given;")
    w("2. leave **Schedule VDA** empty, and do not opt for presumptive income (44AD);")
    w("3. if the AIS shows entries from Delta Exchange India or CoinDCX, compare them with sections 4 and 10. They "
      "should agree. If the AIS calls them VDA, give AIS feedback that the income is offered as speculative business "
      "income;")
    w("4. take the other heads (salary from Form 16; interest and the rest from the AIS) as usual. They are outside "
      "this statement;")
    w("5. file by the due date above.")
    w("")
    w("**Documents in the pack:**")
    w("- this statement (the server copy, with name and PAN) and its .csv;")
    w("- the tax opinion `reports/2026-10-09_tax_opinion.md` (why speculative business, not VDA);")
    w("- each exchange's statement for the year (trades, funding, fees);")
    w("- the bank statement for the account linked to the exchanges;")
    w("- your Form 16, AIS and Form 26AS;")
    w("- last year's ITR acknowledgement, if a loss is brought forward.")
    w("")
    w("**Completeness check:**")
    w("")
    w("| item | status | who closes it |")
    w("|---|---|---|")
    for lab, v, who in items:
        st = 'done' if v else (('due after 31 March' if (live and 'Balances' in lab) else 'not applicable (paper)')
                               if v is None else 'open')
        w(f"| {lab} | {st} | {'—' if v else who} |")
    w("")
    if rev:
        w("**Reviewed:** " + '; '.join(f"edition {r.get('edition')} on {r.get('date')}" + (f" ({r['note']})" if r.get('note') else '')
                                     for r in rev) + ".")
    else:
        w("**Reviewed:** not yet. We go through it together in June, before it goes to the CA.")
    w("")
    w("*Prepared by Claude as your tax adviser, not a registered CA. Figures come from the bot's journal and are "
      "checked against its ledger; live, also against each exchange's own statement.*")
    md = "\n".join(L) + "\n"

    def _w(path, text):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
        with os.fdopen(fd, 'w', newline='' if path.endswith('.csv') else None) as h:
            h.write(text)
        if private:
            os.chmod(path, 0o600)
    _w(base + '.md', md)
    import io
    buf = io.StringIO()
    cw = csv.writer(buf)
    cw.writerow(['kind', 'coin', 'opened_IST', 'closed_IST', 'exchange', 'qty', 'entry_price', 'exit_price',
                 'price_diff_USD', 'funding_received_USD', 'funding_paid_USD', 'gst_on_funding_USD', 'fee_USD',
                 'gst_on_fee_USD', 'slippage_USD', 'net_USD', 'net_INR'])
    for kd, its in (('closed', o['closed']), ('open', o['open'])):
        for item in its:
            r, Lg = item['rec'], item['legs']
            for l, qk, p0, p1 in (('d', 'd_qty', 'd_px0', 'd_px1'), ('b', 'b_qty', 'b_px0', 'b_px1')):
                x = Lg[l]
                pr = x['price'] if kd == 'closed' else x['price_open']
                netx = pr + x['rent_in'] + x['rent_out'] + x['rent_gst'] - x['fee'] - x['fee_gst'] - x['spread'] - x['other']
                cw.writerow([kd, r.get('coin'), f"{ist(r['opened']):%Y-%m-%d %H:%M}" if r.get('opened') else '',
                             f"{ist(r['closed']):%Y-%m-%d %H:%M}" if (kd == 'closed' and r.get('closed')) else '', x['venue'],
                             round(float(r.get(qk) or 0), 6), r.get(p0), r.get(p1), round(pr, 6), round(x['rent_in'], 6),
                             round(x['rent_out'], 6), round(x['rent_gst'], 6), round(x['fee'], 6), round(x['fee_gst'], 6),
                             round(x['spread'], 6), round(netx, 6), round(rs(netx, inr), 2)])
    _w(base + '.csv', buf.getvalue())
    js = dict(ty=ty, kind=kind, edition=str(edition), prepared=asof, inr_per_usd=inr, past=o['past'], cut=o['cut'],
              itr=dict(form='ITR-3', business_code=code, code_confirmed=bool(code_ok),
                       pl_no_accounts_speculative=dict(turnover=I['turnover'], gross_profit=I['gross'],
                                                       expenditure=I['expenditure'], net=I['net']),
                       bs_no_accounts=dict(sundry_debtors=(round(debt) if debt is not None else None), sundry_creditors=0,
                                           stock_in_trade=0, cash_balance=0, source=bal.get('src')),
                       bp_speculative=dict(net=I['net'], additions=0, deductions=0, income=max(0, I['net'])),
                       bfla=o['setoff'], books_44aa=o['books'], audit_44ab=o['audit'], presumptive=False, vda='nil', tds=0),
              taxable=o['taxable'], tax=o['tax'], losses_cf=o['cf'], history=o['history'],
              checks_ok=all(c[1] for c in o['checks']),
              complete=dict(done=n_done, of=n_need, open=[lab for lab, v, _ in items if v is False]))
    _w(base + '.json', json.dumps(js, indent=1) + "\n")
    return base + '.md', base + '.csv', all(c[1] for c in o['checks'])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('ledger', nargs='?')
    ap.add_argument('--live', action='store_true')
    ap.add_argument('--ty', default=None)
    ap.add_argument('--inr', type=float, default=DELTA_INR)
    ap.add_argument('--out', default=None, help="default: the private folder (data/tax beside the ledger)")
    ap.add_argument('--private', default=None, help="where taxpayer.json lives (default: tax/ beside the ledger)")
    ap.add_argument('--profile', default=os.path.join(HERE, 'reports', 'tax', 'profile.json'))
    ap.add_argument('--xrec', default=None)
    ap.add_argument('--edition', default='1')
    ap.add_argument('--setup', action='store_true', help="save your name, PAN and accounts (once, on the server)")
    a = ap.parse_args(argv)
    if a.setup:
        priv = a.private or os.path.join(os.environ.get('OMEGA_BASE_PATH') or os.path.join(HERE, 'data'), 'tax')
        try:
            setup(os.path.join(priv, 'taxpayer.json'))
        except ValueError as e:
            print(f"not saved: {e}")
            return 2
        return 0
    if not a.ledger:
        ap.error('the ledger file is needed (or --setup)')
    priv = a.private or os.path.join(os.path.dirname(os.path.abspath(a.ledger)), 'tax')
    outdir = a.out or priv
    private = os.path.realpath(outdir) == os.path.realpath(priv)
    d = load(a.ledger)
    now_ms = int(dt.datetime.utcnow().timestamp() * 1000)
    ty = a.ty or ty_of(now_ms)
    kind = 'LIVE' if a.live else 'PAPER'
    prof = load_profile(a.profile)
    xrec = load_xrec(a.xrec or os.path.join(priv, f"xrec_TY{ty}.json")) if a.live else None
    prior = load_prior(outdir, ty, kind)
    o = build(d, ty, a.live, a.inr, now_ms=now_ms, profile=prof, xrec=xrec, prior=prior)
    tp = load_taxpayer(os.path.join(priv, 'taxpayer.json'))
    md, cv, ok = write(d, o, ty, a.live, a.inr, outdir, a.edition, f"{ist(now_ms):%d %b %Y %H:%M}", profile=prof,
                       taxpayer=tp, private=private)
    I = o['inr']
    print(f"tax year {ty} ({kind}): net Rs {fmt(I['net'])} (gross Rs {fmt(I['gross'])}, expenditure Rs "
          f"{fmt(I['expenditure'])}, turnover Rs {fmt(I['turnover'])}); {len(o['closed'])} closed, {len(o['open'])} open; "
          f"checks {'OK' if ok else 'FAILED'}"
          f"{'; paper carry-in Rs ' + fmt(rs(o['carried'], a.inr)) if o['carried'] else ''}")
    print(md); print(cv)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
