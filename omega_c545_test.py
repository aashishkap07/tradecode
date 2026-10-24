#!/usr/bin/env python3
"""C545: the ITR statement complete for filing (omega_tax_statement.py), and the journal's exact year-end cut-off.

The operator, 9 Oct 2026: "make sure that the above income document is complete in the sense that i won't have to fill
in any transaction details myself or anything else ..so that when the document matching the live bot is created , i can
hand it over straight (after of course thoroughly reviewing with you ) to a third party CA who will only help in filing
itr".
1. The bot journals each rent payment in the IST month it was PAID (the 06:00 IST run on 1 April books the last 18
   hours of March: they belong to the year that ended), and the first run of a new tax year journals a 'yearend'
   record (the 31 March balances). No money changes.
2. The statement cuts a tax year exactly: a position open on 31 March is not income until it closes (its rent to
   31 March is); the next year takes its price result.
3. It carries every ITR-3 field this income touches (section 12) -- the same figures as the summary and the .json --
   the no-accounts balance sheet, losses brought and carried forward between years, the 44AA/44AB answers, and a
   completeness check (section 13).
4. Identity: a private file (chmod 600, never in git); the copy written beside it is in full, any other masked.
5. Live: each exchange's own records beside the journal's; other business expenses.
"""
import os, io, re, sys, json, stat, time, types, logging, tempfile, contextlib, importlib.util, subprocess, datetime as dt
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c545_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c545-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om545', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
lg = logging.getLogger('OmegaV60'); lg.handlers = [logging.NullHandler()]; lg.propagate = False
st_spec = importlib.util.spec_from_file_location('ts545', os.path.join(REPO, 'omega_tax_statement.py'))
TS = importlib.util.module_from_spec(st_spec); st_spec.loader.exec_module(TS)
print("=" * 66); print("C545: THE ITR STATEMENT, COMPLETE FOR FILING"); print("=" * 66)
ok("version C545 or later", int(om._OMEGA_VERSION[1:]) >= 545)


def ms(y, m, d, h=0, mi=0):
    """an IST wall-clock time, in ms"""
    return int((dt.datetime(y, m, d, h, mi) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 19800 * 1000


# ── 1. the bot ──────────────────────────────────────────────────────────────
print("\n1. THE BOT: EACH RENT PAYMENT IN ITS OWN MONTH; A YEAR-END RECORD")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 1000.0
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
x = om.C524CrossVenue(xb); x.reset()
ok("the plan's second exchange is CoinDCX (rupee venue: rent paid carries GST)", x.venue() == 'coindcx' and x.on_pi42())
p = dict(d_qty=-10.0, cv=1.0, b_qty=10.0, d_px=1.0, b_px=1.0,
         jx=dict(opened=ms(2027, 3, 30), px_d=0.0, px_b=0.0, fm={}, fee_d=0.0, fee_b=0.0))
t_mar, t_apr = ms(2027, 3, 31, 17, 30), ms(2027, 4, 1, 1, 30)      # 17:30 and 01:30 IST either side of the year-end
raw_d, raw_b = [0.30, 0.25], [-0.10, 0.05]
fu_d, fu_b = sum(x.fgst(r) for r in raw_d), sum(x.fgst(r) for r in raw_b)
x._c544_book(p, ms(2027, 4, 1, 6, 0), 1.0, 1.0, raw_d, raw_b, fu_d, fu_b, [t_mar, t_apr], [t_mar, t_apr])
fm = p['jx']['fm']
ok("a run at 06:00 IST on 1 April books the 31 March payment in 2027-03 and the 1 April one in 2027-04",
   set(fm) == {'2027-03', '2027-04'} and abs(fm['2027-03'][0] - 0.30) < 1e-12 and abs(fm['2027-04'][0] - 0.25) < 1e-12, str(fm))
ok("rent paid on CoinDCX on 31 March carries its 18% GST in March; rent received in April carries none",
   abs(fm['2027-03'][4] + 0.10) < 1e-12 and abs(fm['2027-03'][5] + 0.018) < 1e-12 and abs(fm['2027-04'][3] - 0.05) < 1e-12
   and abs(fm['2027-04'][5]) < 1e-12)
ok("the months still add up to exactly what the ledger booked", abs(sum(sum(r) for r in fm.values()) - (fu_d + fu_b)) < 1e-12)
p2 = dict(p, jx=dict(p['jx'], fm={}))
x._c544_book(p2, ms(2026, 10, 9, 6), 1.0, 1.0, [0.1], [], 0.1, 0.0)
ok("without payment times (an older caller), the run's month is used, as before", list(p2['jx']['fm']) == ['2026-10'])

x.start_equity = x.eq = 1000.0
x.side = {'d': 12.0, 'b': -3.0}
x.pairs = {'AAA': dict(jx=dict(px_d=-4.0, px_b=4.5, carry=None))}
x.journal = []
x.last_run = '2027-03-31'
r1 = x._c545_yearend(ms(2027, 4, 1, 6, 0))
ok("the first run of a new tax year journals a 'yearend' record for the year that ended, with each exchange's money",
   r1 and r1['t'] == 'yearend' and r1['ty'] == '2026-27' and abs(r1['d'] - 512.0) < 1e-9 and abs(r1['b'] - 497.0) < 1e-9
   and r1['open']['AAA']['px_d'] == -4.0 and r1['asof'] == '2027-03-31', str(r1)[:160])
x.last_run = '2027-04-01'
ok("only once a year", x._c545_yearend(ms(2027, 4, 2, 6, 0)) is None and x._c545_yearend(ms(2027, 4, 1, 6, 0)) is None
   and sum(1 for r in x.journal if r.get('t') == 'yearend') == 1)
x.last_run = '2026-10-08'
ok("no record within a year", x._c545_yearend(ms(2026, 10, 9, 6, 0)) is None)
x._c544_scale(2.0)
ye = next(r for r in x.journal if r.get('t') == 'yearend')
ok("a paper re-base scales the year-end record with everything else", abs(ye['d'] - 1024.0) < 1e-9 and ye['open']['AAA']['px_b'] == 9.0)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("the daily run calls the year-end check before it marks anything",
   SRC.index('self._c545_yearend(now_ms)') < SRC.index('# 1. mark what is held'))
ok("the daily run passes each payment's own time to the journal",
   'self._c544_book(p, now_ms, dpx, bpx, raw_d, raw_b, fu_d, fu_b, ms_d, ms_b)' in SRC)

# ── 2. a tax year cut exactly ───────────────────────────────────────────────
print("\n2. THE STATEMENT CUTS THE TAX YEAR EXACTLY")
R8 = dict(fd=0.0005, gd=0.18, fb=0.0005, gb=0.18, spr=0.0002)


def cost(n):
    return n * (0.0005 * 1.18 + 0.0002)


def close_rec(coin, op, cl, px_d, px_b, fmx, n=100.0, why='spread gone'):
    fee = cost(n) * 2
    pnl = px_d + px_b + sum(sum(r) for r in fmx.values()) - 2 * fee
    return dict(t='close', coin=coin, why=why, venue='CoinDCX', side=1, d_sym=coin + 'USD', d_qty=-n, b_qty=n, cv=1.0,
                opened=op, closed=cl, d_px0=1.0, b_px0=1.0, d_px1=1.0, b_px1=1.0, n_in=n, n_out=n, px_d=px_d, px_b=px_b,
                fee_d=fee, fee_b=fee, fee_d_out=cost(n), fee_b_out=cost(n), fm=fmx, rates=R8, carry=None, pnl=pnl)


A = close_rec('AAA', ms(2026, 11, 1, 6), ms(2027, 1, 10, 6), -5.0, 5.5,
              {'2026-11': [1.0, 0.0, 0.0, 0.0, -0.2, -0.036], '2027-01': [0.5, 0.0, 0.0, 0.0, 0.0, 0.0]})
B = close_rec('BBB', ms(2027, 3, 1, 6), ms(2027, 4, 20, 6), -2.0, 2.4,
              {'2027-03': [0.8, 0.0, 0.0, 0.0, 0.0, 0.0], '2027-04': [0.3, 0.0, 0.0, 0.0, 0.0, 0.0]})
YE = dict(t='yearend', ty='2026-27', ms=ms(2027, 4, 1, 6), asof='2027-03-31', eq=1001.0, start=1000.0, d=480.0, b=521.0,
          venue='CoinDCX', open={'BBB': dict(px_d=-1.0, px_b=1.3, carry=0.0)})
TR = dict(t='transfer', ms=ms(2027, 2, 2, 6), frm='CoinDCX', to='Delta', amt=40.0, fee=1.0, why='the monthly re-balance')
LED = dict(start_equity=1000.0, eq=1003.0, venue='coindcx', side={'d': 1.0, 'b': 2.0},
           journal=[dict(t='carry', ms=ms(2026, 10, 9, 6), eq=1000.0, start=1000.0, fees=0, funding=0, price=0, transfer_fees=0,
                         closed=[], transfers=[], moves=[], rebased=[], open_pnl=0, open_funding=0), A, TR, YE, B],
           pairs={'CCC': dict(side=1, d_sym='CCCUSD', d_qty=-100.0, b_qty=100.0, cv=1.0, d_px=1.0, b_px=1.0, pnl=-2 * cost(100),
                              jx=dict(opened=ms(2027, 5, 1, 6), d_px0=1.0, b_px0=1.0, n_in=100.0, fee_d=cost(100), fee_b=cost(100),
                                      px_d=0.0, px_b=0.0, fm={}, venue='CoinDCX', rates=R8, carry=None))})
NOW = ms(2027, 6, 15, 10)
o = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW)
T = o['totals']
ok("a past year (statement made in June): A closed in the year; B open on 31 March; C (opened in May) left out",
   [i['rec']['coin'] for i in o['closed']] == ['AAA'] and [i['rec']['coin'] for i in o['open']] == ['BBB'] and o['past'])
ok("price: only A's realised; B's is not income until it closes (its 31 March value shown from the year-end record)",
   abs(T['price'] - 0.5) < 1e-12 and abs(T['unrealised'] - 0.3) < 1e-12)
ok("rent: A's (Nov, Jan) and B's to 31 March; B's April rent is next year's",
   abs((T['rent_in'] + T['rent_out'] + T['rent_gst']) - (1.0 - 0.236 + 0.5 + 0.8)) < 1e-12)
ok("fees: A's entry and exit, B's entry (its exit is next year's); the transfer charge",
   abs(T['fee'] - 3 * 2 * 100 * 0.0005) < 1e-12 and abs(T['transfer_fees'] - 1.0) < 1e-12)
net_exp = 0.5 + 2.064 - 3 * 2 * cost(100) - 1.0
ok("net = price + rent − fees − transfer charge", abs(T['net'] - net_exp) < 1e-9, f"{T['net']:.6f} vs {net_exp:.6f}")
ok("the year-end balances come from the bot's year-end record (wallet = equity less the unrealised)",
   o['balances']['src'] == 'ledger' and abs(o['balances']['d'] - (480.0 + 1.0) * 85) < 1e-6 and abs(o['balances']['b'] - (521.0 - 1.3) * 85) < 1e-6)
o2 = TS.build(LED, '2027-28', True, 85.0, now_ms=NOW)
T2 = o2['totals']
ok("next year: B closes in April -- its whole price result, its April rent, its exit fee (not its entry fee)",
   [i['rec']['coin'] for i in o2['closed']] == ['BBB'] and abs(T2['price'] - 0.4) < 1e-12
   and abs(T2['rent_in'] - 0.3) < 1e-12 and abs(T2['fee'] - (2 * 100 * 0.0005 + 2 * 100 * 0.0005)) < 1e-12,
   f"price {T2['price']}, fee {T2['fee']}")
both = T['net'] + T2['net'] + T2['unrealised']
whole = (A['pnl'] + B['pnl'] - 1.0) + (-2 * cost(100))
ok("the two years together = the positions' whole results (nothing counted twice, nothing lost)",
   abs(both - whole) < 1e-9, f"{both:.6f} vs {whole:.6f}")

# ── 3. the filing sheet, losses, books ──────────────────────────────────────
print("\n3. EVERY ITR-3 FIELD; LOSSES BROUGHT AND CARRIED FORWARD; BOOKS AND AUDIT")
OUT = os.path.join(BASE, 'tax_live')
L1 = json.loads(json.dumps(LED))
L1['journal'][1] = close_rec('AAA', ms(2026, 11, 1, 6), ms(2027, 1, 10, 6), -60.0, 5.5, A['fm'])     # a loss year
o = TS.build(L1, '2026-27', True, 85.0, now_ms=NOW)
md, cv, good = TS.write(L1, o, '2026-27', True, 85.0, OUT, '3', 'test')
txt = open(md).read()
js = json.load(open(md[:-3] + '.json'))
I = o['inr']
ok("13 fixed sections, the at-a-glance box, the ITR-3 filing sheet and the handover pack",
   all(f"## {i}." in txt for i in range(1, 14)) and '### For the filing CA — at a glance' in txt
   and '## 12. ITR-3 filing sheet' in txt and '## 13. Handover pack for the filing CA' in txt)
glance = re.search(r"turnover \*\*₹([-\d,]+)\*\* · gross profit \*\*₹([-\d,]+)\*\* · expenditure \*\*₹([-\d,]+)\*\* · net \*\*₹([-\d,]+)\*\*", txt)
sheet = [re.search(rf"\*\*Speculative activity: {k}\*\* \| \*\*([-\d,]+)\*\*", txt) for k in ('turnover', 'gross profit', 'expenditure', 'net income')]
num = lambda s: int(s.replace(',', ''))
ok("the same four P&L figures in the box, the filing sheet and the .json",
   glance and all(sheet) and [num(g) for g in glance.groups()] == [num(m.group(1)) for m in sheet]
   == [js['itr']['pl_no_accounts_speculative'][k] for k in ('turnover', 'gross_profit', 'expenditure', 'net')])
ok("a loss year: the loss is carried forward 4 years (Schedule CFL), nothing set off against other heads, no tax",
   I['net'] < 0 and js['losses_cf'] == [dict(ty='2026-27', amount=-I['net'], last_ty='2030-31')] and js['tax'] == 0
   and 'Schedule CFL | Speculative loss of 2026-27 carried forward' in txt and 'Schedule CYLA' in txt)
ok("never Schedule VDA; no TDS; no presumptive income; books and audit not required at this size",
   'Schedule VDA | Income from transfer of virtual digital assets | **nil — leave empty**' in txt
   and js['itr']['vda'] == 'nil' and js['itr']['tds'] == 0 and js['itr']['presumptive'] is False
   and js['itr']['books_44aa'] is False and js['itr']['audit_44ab'] is False)
ok("the no-accounts balance sheet: sundry debtors = the money held at the exchanges; creditors, stock and cash 0",
   js['itr']['bs_no_accounts']['sundry_debtors'] == round(o['balances']['d'] + o['balances']['b'])
   and js['itr']['bs_no_accounts']['cash_balance'] == 0 and 'Sundry debtors' in txt)
prior = TS.load_prior(OUT, '2027-28', 'LIVE')
o2 = TS.build(L1, '2027-28', True, 85.0, now_ms=NOW, prior=prior)
L2 = json.loads(json.dumps(L1))
L2['journal'][-1] = close_rec('BBB', ms(2027, 3, 1, 6), ms(2027, 4, 20, 6), -2.0, 80.0, B['fm'])     # a profit year
o2 = TS.build(L2, '2027-28', True, 85.0, now_ms=NOW, prior=prior)
used = o2['setoff'][0]['used'] if o2['setoff'] else 0
ok("next year reads last year's .json: the loss is set off against this year's speculative profit (Schedule BFLA)",
   prior is not None and o2['inr']['net'] > 0 and used == min(o2['inr']['net'], -I['net'])
   and o2['taxable'] == o2['inr']['net'] - used and o2['tax'] == round(o2['taxable'] * 0.312), str(o2['setoff']))
md2, _, _ = TS.write(L2, o2, '2027-28', True, 85.0, OUT, '1', 'test')
ok("and says so in the filing sheet", 'Schedule BFLA | Speculative loss of 2026-27 set off' in open(md2).read())
big = json.loads(json.dumps(LED))
big['journal'][1] = close_rec('AAA', ms(2026, 11, 1, 6), ms(2027, 1, 10, 6), -20000.0, 20010.0, A['fm'], n=100.0)
ob = TS.build(big, '2026-27', True, 85.0, now_ms=NOW)
ok("turnover over Rs 25 lakh: books become compulsory (44AA / s.62) and the sheet says so; audit still not (Rs 10 crore)",
   ob['inr']['turnover'] > 2500000 and ob['books'] and not ob['audit'])

# ── 4. identity ─────────────────────────────────────────────────────────────
print("\n4. YOUR NAME AND PAN: A PRIVATE FILE; IN FULL ONLY BESIDE IT")
DATA = os.path.join(BASE, 'data'); PRIV = os.path.join(DATA, 'tax')
os.makedirs(DATA, exist_ok=True)
ans = dict(name='Test Person Name', pan='abcde1234f', delta_account='someone@example.com', coindcx_account='CDX778899',
           bank='Some Bank, account ending 4321')
for bad, why in ((dict(ans, pan='ABC123'), 'a PAN'), (dict(ans, bank='Some Bank 123456789012'), 'last 4')):
    try:
        TS.setup(os.path.join(PRIV, 'taxpayer.json'), answers=bad, out=lambda *a: None)
        ok(f"setup refuses a bad answer ({why})", False)
    except ValueError as e:
        ok(f"setup refuses a bad answer ({why})", why in str(e), str(e))
said = []
TS.setup(os.path.join(PRIV, 'taxpayer.json'), answers=ans, out=said.append)
tpf = os.path.join(PRIV, 'taxpayer.json')
ok("setup saves the file readable by its owner only (600), the PAN in capitals, and prints it masked",
   stat.S_IMODE(os.stat(tpf).st_mode) == 0o600 and json.load(open(tpf))['pan'] == 'ABCDE1234F'
   and 'ABCDE1234F' not in said[0] and 'AB******4F' in said[0])
json.dump(LED, open(os.path.join(DATA, 'c524_xvenue.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(REPO, 'omega_tax_statement.py'), os.path.join(DATA, 'c524_xvenue.json'),
                    '--live', '--ty', '2026-27'], capture_output=True, text=True)
fullmd = os.path.join(PRIV, 'ITR_TY2026-27_rent_gap_LIVE.md')
ok("by default the statement is written beside the identity file (data/tax/), in full, readable by its owner only",
   r.returncode == 0 and os.path.exists(fullmd) and 'ABCDE1234F' in open(fullmd).read()
   and 'Test Person Name' in open(fullmd).read() and stat.S_IMODE(os.stat(fullmd).st_mode) == 0o600, r.stderr[-300:])
ok("the command's own output never prints the PAN or the name (it may reach a log)",
   'ABCDE1234F' not in r.stdout + r.stderr and 'Test Person' not in r.stdout + r.stderr)
r = subprocess.run([sys.executable, os.path.join(REPO, 'omega_tax_statement.py'), os.path.join(DATA, 'c524_xvenue.json'),
                    '--live', '--ty', '2026-27', '--out', os.path.join(BASE, 'pub')], capture_output=True, text=True)
pub = open(os.path.join(BASE, 'pub', 'ITR_TY2026-27_rent_gap_LIVE.md')).read()
ok("a copy written anywhere else is masked (PAN, name, logins, bank)",
   r.returncode == 0 and 'ABCDE1234F' not in pub and 'AB******4F' in pub and 'Test Person Name' not in pub
   and 'someone@example.com' not in pub and '4321' not in pub and 'CDX778899' not in pub)
LP = open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read()
ok("the logs push scrubs every value of taxpayer.json too, and never copies data/tax/",
   'tax/taxpayer.json' in LP and 'omega-scrub-keys.py" "$TAXP_JSON"' in LP and '"$REPO"/data/tax' not in LP)
GI = open(os.path.join(REPO, '.gitignore')).read()
ok("git ignores data/tax/ (the identity file and the full copies)", '/data/tax/' in GI)

# ── 5. live: each exchange's own records, other expenses, completeness ─────
print("\n5. LIVE: THE EXCHANGES' OWN RECORDS, OTHER EXPENSES, THE COMPLETENESS CHECK")
o = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW)
V = o['venue']
xr = {v: dict(realised=V[v]['price'] * 85, funding=(V[v]['rent_in'] + V[v]['rent_out'] + V[v]['rent_gst']) * 85,
              fees=-(V[v]['fee'] + V[v]['fee_gst']) * 85, balance_ye=o['balances']['ledger'][k] + 3.0)
      for v, k in (('Delta', 'd'), ('CoinDCX', 'b'))}
ox = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW, xrec=xr)
ok("the exchanges' figures sit beside the journal's, line by line, and agree",
   ox['xrec'] and len(ox['xrec']) == 6 and all(rw['ok'] for rw in ox['xrec']))
ok("the 31 March balances are the exchanges' own (the bot's shown beside them)",
   ox['balances']['src'] == 'exchange' and abs(ox['balances']['d'] - (o['balances']['ledger']['d'] + 3.0)) < 1e-9)
xr['Delta']['funding'] += 50.0
ox2 = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW, xrec=xr)
md3, _, _ = TS.write(LED, ox2, '2026-27', True, 85.0, os.path.join(BASE, 'x2'), '1', 'test')
ok("a line off by more than Rs 10 is flagged, and the completeness check stays open",
   sum(1 for rw in ox2['xrec'] if not rw['ok']) == 1 and '**NO — explained below**' in open(md3).read()
   and "| Each exchange's own statement reconciled (section 10) | open |" in open(md3).read())
prof = TS.load_profile(None)
prof['expenses'] = [dict(what='server rent', inr_per_month=500, frm='2027-02', evidence='monthly invoice')]
oe = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW, profile=prof)
ok("other business expenses (live): Rs 500 a month from February = Rs 1,000 in the year's expenditure",
   abs((oe['totals']['expenditure'] - o['totals']['expenditure']) * 85 - 1000.0) < 1e-6 and oe['expenses'][0]['months'] == 2)
op = TS.build(LED, '2026-27', False, 85.0, now_ms=NOW, profile=prof)
ok("never in paper (there is no business before the first real trade)", not op['expenses'])
prof.update(business_code_confirmed={'2026-27': 'checked 2027-06-10'}, due_date={'2026-27': '2027-07-31'},
            started_live='2027-02-01', reviews=[dict(ty='2026-27', kind='LIVE', edition='4', date='2027-06-20')])
prof['exchanges']['delta'].update(entity='(the operating company)', fiu='(its number)')
oc = TS.build(LED, '2026-27', True, 85.0, now_ms=NOW, profile=prof, xrec=dict(xr, Delta=dict(xr['Delta'], funding=xr['Delta']['funding'] - 50.0)))
items, rev = TS.completeness(oc, True, '2026-27', prof, json.load(open(tpf)), 'LIVE')
ok("with everything in place, every completeness item is done", all(v for _, v, _ in items), str([l for l, v, _ in items if not v]))
ok("PAPER marks the live-only items 'not applicable' rather than open",
   [v for l, v, _ in TS.completeness(op, False, '2026-27', TS.load_profile(None), None, 'PAPER')[0]][1:3] == [None, None])

print("\n6. THE COMMITTED PAPER STATEMENT AND THE PROFILE")
pj = json.load(open(os.path.join(REPO, 'reports', 'tax', 'profile.json')))
ok("reports/tax/profile.json exists, holds no PAN, and names business code 21009",
   pj.get('business_code') == '21009' and not re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', json.dumps(pj)))
pm = open(os.path.join(REPO, 'reports', 'tax', 'ITR_TY2026-27_rent_gap_PAPER.md')).read()
ok("the committed paper statement is in the 13-section format, with no PAN in it",
   all(f"## {i}." in pm for i in range(1, 14)) and not re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', pm))
ok("C488_LIVE_OK stays False; no keys in the code", 'self.C488_LIVE_OK = False' in SRC)
print()
print("=" * 66)
print("C545 TEST: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
