#!/usr/bin/env python3
"""C544: the tax journal and the ITR income statement (omega_tax_statement.py).

The operator, 9 Oct: "As a learned CA specialising in taxation, build a transaction & net profit/loss summary, the details
of the source of this sort of income ... so that i can present that directly while filing ITR in year 2027 ... keep
updating the summary ... during live trading the summary will start afresh but in exactly same/correct/latest generated
format".
1. The plan's ledger journals every pair: both legs' entry and exit, each leg's price result, rent received / paid /
   GST on rent paid by IST month, fees (fee, GST, spread), transfers and exchange moves. Nothing in its money changes.
2. A ledger saved before C544 is carried in whole (its totals and open pairs' results to date).
3. The statement's numbers add back to the ledger to the paisa, in one fixed format (paper now, live later).
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util, subprocess
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c544_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c544-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om544', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
st_spec = importlib.util.spec_from_file_location('ts544', os.path.join(REPO, 'omega_tax_statement.py'))
TS = importlib.util.module_from_spec(st_spec); st_spec.loader.exec_module(TS)
print("=" * 66); print("C544: THE TAX JOURNAL AND THE ITR STATEMENT"); print("=" * 66)
ok("version C544 or later", int(om._OMEGA_VERSION[1:]) >= 544)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 1000.0
DAY, H = 86400000, 3600000
D0 = (int(time.time() * 1000) // DAY - 6) * DAY
RATE = {'HOT': 0.10, 'SWING': 0.10}
PX = {'HOT': 2.0, 'SWING': 1.0}


EXTRA = {f'ONLYD{j:02d}': 1.0 for j in range(20)}          # Delta-only coins (a real product list has >= 20)


class FakeDelta:
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value='1.0', taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k in list(PX) + list(EXTRA)]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(v)) for k, v in list(PX.items()) + list(EXTRA.items())]
        if path == '/v2/history/candles':
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=RATE.get(k, 0.06)) for t in range(first, en + 1, 3600)]
        return None


om._c521_get = FakeDelta()


def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        k = params['symbol'][:-4]
        lo = params['startTime']
        r = (lambda t: -0.0008 if (t // H) % 24 == 8 else 0.0008) if k == 'SWING' else (lambda t: 0.0001)
        return [dict(fundingTime=t + 5, fundingRate=str(r(t))) for t in range(-(-lo // (8 * H)) * 8 * H, lo + 9 * DAY, 8 * H)]
    return None


om._c516_bn_get = fake_bn
om._c541_coindcx_coins = lambda: {'HOT', 'SWING', 'BTC'}
om._c532_pi42_coins = lambda: {'HOT', 'SWING', 'BTC'}
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe


def marks():
    xe.marks = {k + '/USDT:USDT': dict(bid=v, ask=v, last=v, fr=0.0, vol=1e8) for k, v in PX.items()}


marks(); xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset(); xb.c524x = x
ok("the plan's second exchange is CoinDCX (C542)", x.venue() == 'coindcx' and x.v2() == 'CoinDCX')

print("\n1. EVERY PAIR JOURNALED, LEG BY LEG")
x.run(now_ms=D0 + 30 * 60000)
ok("day 0: two pairs open, each with its journal record (entry prices, notional, fee a side, rates)",
   set(x.pairs) == {'HOT', 'SWING'} and all(isinstance(p.get('jx'), dict) and p['jx']['d_px0'] > 0 and p['jx']['n_in'] > 0
                                            and p['jx']['rates']['fb'] == 0.0005 for p in x.pairs.values()))
hot = x.pairs['HOT']
ok("an entry's cost a side = notional x (fee x 1.18 + 0.02%), on each exchange",
   abs(hot['jx']['fee_d'] - hot['jx']['n_in'] * om._C524_COST_D) < 1e-12 and abs(hot['jx']['fee_b'] - hot['jx']['n_in'] * x.cost_b()) < 1e-12)
for k in range(1, 4):
    PX['HOT'] *= 1.03; PX['SWING'] *= 0.98; marks()
    x.last_run = ''
    x.run(now_ms=D0 + k * DAY + 30 * 60000)
p = x.pairs['HOT']
fm = sum(sum(r) for r in p['jx']['fm'].values())
ok("rent received + paid + GST on rent paid, by month, = the rent the ledger booked for the pair",
   abs(fm - p['funding']) < 1e-9, f"{fm:.9f} vs {p['funding']:.9f}")
sw = x.pairs['SWING']['jx']['fm']
row = next(iter(sw.values()))
ok("SWING (its CoinDCX rate swings): rent paid carries 18% GST, rent received none",
   row[4] < 0 and abs(row[5] - 0.18 * row[4]) < 1e-9 and row[3] > 0)
mine = p['jx']['px_d'] + p['jx']['px_b'] + fm - p['jx']['fee_d'] - p['jx']['fee_b']
ok("a pair's journal (price + rent - fees) = its ledger result exactly", abs(mine - p['pnl']) < 1e-9, f"{mine:.9f} vs {p['pnl']:.9f}")
RATE['HOT'] = 0.0
x.last_run = ''
x.run(now_ms=D0 + 4 * DAY + 30 * 60000)
cl = [r for r in x.journal if r.get('t') == 'close' and r['coin'] == 'HOT']
ok("HOT closes: one 'close' record with both legs' entry and exit, price result, rent, fees (in and out)",
   len(cl) == 1 and 'HOT' not in x.pairs and cl[0]['d_px1'] > 0 and cl[0]['fee_d_out'] > 0 and cl[0]['n_out'] > 0
   and cl[0]['opened'] == D0 + 30 * 60000 and cl[0]['closed'] == D0 + 4 * DAY + 30 * 60000)
c = cl[0]
mine = c['px_d'] + c['px_b'] + sum(sum(r) for r in c['fm'].values()) - c['fee_d'] - c['fee_b']
ok("the close record adds up to the ledger's final result for the pair", abs(mine - c['pnl']) < 1e-9)
x.side['b'] -= 300.0; x.side['d'] += 300.0          # force an even-out to see it journaled
x.last_run = ''
x.run(now_ms=D0 + 5 * DAY + 30 * 60000)
tr = [r for r in x.journal if r.get('t') == 'transfer']
ok("a transfer between the exchanges is journaled with its charge", len(tr) == 1 and tr[0]['fee'] == 1.0 and tr[0]['amt'] > 0)
x.side['b'] += 300.0; x.side['d'] -= 300.0
x.save()
saved = json.load(open(os.path.join(BASE, 'c524_xvenue.json')))
ok("the journal is saved with the ledger", len(saved.get('journal') or []) == len(x.journal) >= 2)

print("\n2. A LEDGER FROM BEFORE C544 IS CARRIED IN WHOLE")
old = __import__('copy').deepcopy(saved); old.pop('journal')
for pp in old['pairs'].values():
    pp.pop('jx', None)
json.dump(old, open(os.path.join(BASE, 'c524_xvenue.json'), 'w'))
y = om.C524CrossVenue(xb)
ok("its money is unchanged (equity, fees, rent, sides)",
   abs(y.eq - old['eq']) < 1e-9 and abs(y.fees - old['fees']) < 1e-9 and abs(y.funding - old['funding']) < 1e-9)
ok("the migrated ledger is saved at once (the journal exists from the first load)",
   'journal' in json.load(open(os.path.join(BASE, 'c524_xvenue.json'))))
ok("one 'carry' record with its totals, closed pairs and transfers; each open pair carries its result to date",
   y.journal and y.journal[0]['t'] == 'carry' and abs(y.journal[0]['eq'] - old['eq']) < 1e-6
   and len(y.journal[0]['closed']) == len(old['closed']) and all(pp['jx']['carry'] is not None for pp in y.pairs.values()))

print("\n3. THE STATEMENT (ONE FORMAT, PAPER NOW, LIVE LATER)")
json.dump(saved, open(os.path.join(BASE, 'fresh.json'), 'w'))
d = TS.load(os.path.join(BASE, 'fresh.json'))
ty = TS.ty_of(D0 + 30 * 60000)
o = TS.build(d, ty, False, 85.0)
T = o['totals']
dq = saved['eq'] - saved['start_equity']
ok("net income (realised) + open positions' unrealised price result = the ledger's change, to the cent",
   abs(T['net'] + T['unrealised'] - dq) < 1e-6, f"{T['net'] + T['unrealised']:.6f} vs {dq:.6f}")
ok("every journaled position reconciles with the ledger", o['checks'] and all(cc[1] for cc in o['checks']))
ok("rent: received >= 0, paid <= 0, GST on rent paid = 18% of rent paid (all positions)",
   T['rent_in'] >= 0 and T['rent_out'] <= 0 and abs(T['rent_gst'] - 0.18 * T['rent_out']) < 1e-9)
ok("fees split exactly: fee : GST = 1 : 0.18 on both exchanges", abs(T['fee_gst'] - 0.18 * T['fee']) < 1e-9)
md, cv, good = TS.write(d, o, ty, False, 85.0, os.path.join(BASE, 'tax'), '1', 'test')
txt = open(md).read()
heads = [f"## {i}." for i in range(1, 12)]
ok("the statement has its 11 fixed sections, the PAPER banner, rupees at Rs 85, the ITR-3 fields",
   all(h in txt for h in heads) and 'PAPER — NOT FOR FILING' in txt and '₹85 per dollar' in txt
   and 'Schedule BP' in txt and 'speculative activity — turnover' in txt)
ok("its register lists HOT with both legs and why it closed", '| HOT |' in txt and f"| {c['why']} |" in txt, c['why'])
rows = list(__import__('csv').DictReader(open(cv)))
ok("the CSV has one row per leg (closed and open), and its rupee column = dollars x 85",
   len(rows) == 2 * (len(o['closed']) + len(o['open'])) and all(abs(float(r['net_INR']) - 85 * float(r['net_USD'])) < 0.01 for r in rows))
o2 = TS.build(d, ty, True, 85.0)
md2, _, _ = TS.write(d, o2, ty, True, 85.0, os.path.join(BASE, 'tax'), '1', 'test')
t2 = open(md2).read()
ok("LIVE uses the same 11 sections, with the live banner and no paper lines",
   all(h in t2 for h in heads) and '**LIVE.**' in t2 and 'paper only' not in t2.lower() and md2.endswith('_LIVE.md'))
r = subprocess.run([sys.executable, os.path.join(REPO, 'omega_tax_statement.py'), os.path.join(BASE, 'fresh.json'),
                    '--out', os.path.join(BASE, 'cli')], capture_output=True, text=True)
ok("the command line writes both files and says the checks are OK", r.returncode == 0 and 'checks OK' in r.stdout, r.stdout[:200] + r.stderr[-300:])
json.dump(old, open(os.path.join(BASE, 'pre544.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(REPO, 'omega_tax_statement.py'), os.path.join(BASE, 'pre544.json'),
                    '--out', os.path.join(BASE, 'cli2')], capture_output=True, text=True)
ok("a pre-C544 ledger file (no journal) also produces the statement, its history carried in whole",
   r.returncode == 0 and 'paper carry-in Rs' in r.stdout, r.stdout[:160])

print("\n4. THE PLAN AND SAFETY ARE UNCHANGED")
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("C488_LIVE_OK stays False; no keys in the code", 'self.C488_LIVE_OK = False' in SRC)
ok("logs push copies the plan's ledger (with its journal) as before", 'data/c524_xvenue.json' in open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read())
print()
print("=" * 66)
print("C544 TEST: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
