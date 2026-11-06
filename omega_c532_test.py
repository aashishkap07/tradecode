#!/usr/bin/env python3
"""C532: the operator's $600 on Indian, rupee-settled venues -- Delta vs Pi42 $550 + a $50 reserve.

1. The allocation and the tax settings (the C532 report's tax position).
2. The cross-venue ledger with Pi42 as the second venue (Binance's funding and prices standing in for
   Pi42's, as Pi42 quotes Binance's pair): only Pi42's coins enter; Pi42's fee (0.10% + GST); GST on
   funding paid; a coin Pi42 stops listing exits 'not on Pi42'; without Pi42's list, nothing new.
3. The pending funding (C527Pending) carries the same GST; the venue's name everywhere.
4. The plan: $550 + the $50 reserve = $600; the 8-minute block opens with it; the page in Chromium.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c532_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c532-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om532', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C532: THE $600 IN RUPEES -- DELTA vs PI42 $550 + A $50 RESERVE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C532 or later", int(om._OMEGA_VERSION[1:]) >= 532)

print("\n1. THE ALLOCATION AND THE TAX SETTINGS")
c0 = om.Config()
# C533 changed the operator's plan ($1000 in Delta vs Pi42, no reserve; omega_c533_test.py checks it).
# This test checks C532's mechanics at the allocation C532 set, pinned below.
C532 = dict(C524_XVENUE_EQUITY=550.0, C528_RESERVE=50.0, C528_BUDGET=600.0, C527_PLAN=('xvenue', 'reserve'))
ok("Delta vs Pi42 $550 + a $50 reserve = the operator's $600; the plan is those two",
   c0.C532_XV_VENUE in ('pi42', 'coindcx') and tuple(c0.C527_PLAN) == C532['C527_PLAN']
   and C532['C524_XVENUE_EQUITY'] + C532['C528_RESERVE'] == C532['C528_BUDGET'])
ok("  the book on Delta and the Binance book are paper experiments; Pendle off; live locked",
   c0.C521_DELTA_EQUITY == 500.0 and c0.C530_PENDLE is False and c0.C488_LIVE_OK is False)
ok("  Pi42's fee 0.10% + 18% GST; 18% GST on funding paid; the transfers between the venues on",
   c0.C532_PI42_FEE == 0.0010 and c0.C532_GST == 0.18 and c0.C532_FUNDING_GST == 0.18 and c0.C531_XV_REBALANCE is True)
ok("  tax on net profit at the slab (31.2% until the operator sets theirs; 0% under Rs 12 lakh, s.87A)",
   c0.C528_TAX_RATE == 0.312 and "0.0 if your TOTAL income is under Rs 12 lakh" in SRC)
r532 = open(os.path.join(REPO, 'research', 'c532_india_only.txt')).read()
ok("  the choice is the research's: $50 reserve + $550 cross-venue, the best split with the reserve",
   '$50     $0    $550  |     +3.79%  83%' in r532 and "87%" in r532, '')
pi = json.load(open(os.path.join(REPO, 'research', 'c532_pi42', 'pi42_vs_binance.json')))
ok("  the evidence for reading Pi42's funding from Binance is kept (246 rupee perps compared, 4 Oct)", len(pi) == 246)

print("\n2. THE CROSS-VENUE LEDGER WITH PI42 AS ITS SECOND VENUE")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
cfg.C532_XV_VENUE = 'pi42'   # C542 made CoinDCX the default; this test checks the Pi42-era plan (still supported)
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
for _k, _v in C532.items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C531_XV_REBALANCE = False          # round numbers for the arithmetic below
DAY = 86400000
today = int(time.time() * 1000) // DAY * DAY


class FakeDelta:
    def __init__(s):
        s.c = {'HOT': (0.10, 0.01, 1.0, 2.0), 'COLD': (-0.05, 0.01, 1.0, 3.0), 'MILD': (0.0080, 0.01, 1.0, 1.0)}
        for j in range(20):
            s.c[f'ONLYD{j:02d}'] = (0.01, 0.0, 1.0, 1.0)
        s.px = {k: v[3] for k, v in s.c.items()}
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value=str(v[2]), taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k, v in s.c.items()]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(s.px[k])) for k in s.c]
        if path == '/v2/history/candles':
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=s.c[k][0]) for t in range(first, en + 1, 3600)]
        return None


fdl = FakeDelta()
om._c521_get = fdl
def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        k = params['symbol'][:-4]
        lo = params['startTime']
        return [dict(fundingTime=t, fundingRate=str(fdl.c[k][1] / 100))
                for t in range(-(-lo // (8 * 3600000)) * 8 * 3600000, lo + 9 * DAY, 8 * 3600000)]
    return None
om._c516_bn_get = fake_bn
PI = {'list': {'HOT', 'MILD', 'BTC'}}
om._c532_pi42_coins = lambda: set(PI['list']) if PI['list'] is not None else None
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v[3], ask=v[3], last=v[3], fr=0.0, vol=1e8) for k, v in fdl.c.items() if not k.startswith('ONLYD')}
xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset()
cb = 0.0010 * 1.18 + 0.0002
ok("the second venue is Pi42: its name, and its cost a side 0.10% x 1.18 + 0.02% = 0.138%",
   x.on_pi42() and x.v2() == 'Pi42' and abs(x.cost_b() - cb) < 1e-12)
ok("  funding paid carries 18% GST, funding received none", abs(x.fgst(-1.0) + 1.18) < 1e-12 and x.fgst(1.0) == 1.0)
x.run(now_ms=today + 30 * 60000)
P = x.pairs
ok("only Pi42's coins enter: HOT (short Delta / long Pi42); COLD's spread is as wide but Pi42 does not list it",
   set(P) == {'HOT'} and P['HOT']['side'] == 1 and x.info['wide'] == 2 and x.info['wide_on'] == 1 and x.info['venue'] == 'Pi42',
   str(x.info))
ok("  costs: Pi42's 0.138% + Delta's 0.079% of the pair's notional", abs(x.fees - 50.0 * (cb + om._C524_COST_D)) < 1e-9,
   f"{x.fees:.6f}")
ok("  the entries and the daily log line name Pi42", 'short Delta/long Pi42' in ' '.join(x.info['entered'])
   and 'C524 cross-venue (paper, Delta vs {self.v2()})' in SRC and "({inf.get('wide_on', 0)} on {self.v2()})" in SRC)   # C542: the venue's name
x.last_run = ''
x.run(now_ms=today + DAY + 30 * 60000)
hD = sum(1 for t in range(today // 1000 + 3600, (today + DAY) // 1000 + 1800, 3600) if (t // 3600) % 4 == 0)   # C539: to the run
hB = sum(1 for t in range(today + 8 * 3600000, today + DAY + 1800000, 8 * 3600000))
fu = 25 * 2.0 * 0.10 / 100 * hD - 1.18 * 25.0 * 2.0 * 0.01 / 100 * hB
ok("the next day: HOT's short Delta collects its funding; its long Pi42 pays Binance's rate x 1.18 (GST)",
   abs(P['HOT']['funding'] - fu) < 1e-9, f"{P['HOT']['funding']:.6f} vs {fu:.6f}")
PI['list'] = {'MILD', 'BTC'}
x._pi42_at = 0
x.last_run = ''
x.run(now_ms=today + 2 * DAY + 30 * 60000)
ok("Pi42 stops listing HOT: it exits 'not on Pi42', its costs paid on both venues",
   'HOT' not in x.pairs and x.closed and x.closed[-1]['why'] == 'not on Pi42', str(x.closed[-1:]))
PI['list'] = None
x2 = om.C524CrossVenue(xb); x2.reset()
x2.run(now_ms=today + 30 * 60000)
ok("without Pi42's list (a failed read, never loaded): no new pairs, and it says so",
   not x2.pairs and x2.info.get('pi42_missing') is True)
PI['list'] = {'HOT', 'COLD'}
cfg.C532_XV_VENUE = 'binance'
x3 = om.C524CrossVenue(xb); x3.reset()
x3.run(now_ms=today + 30 * 60000)
ok("C532_XV_VENUE = 'binance' restores the C524 trade exactly: both enter at Binance's cost",
   set(x3.pairs) == {'HOT', 'COLD'} and x3.v2() == 'Binance' and x3.cost_b() == om._C524_COST_B and x3.fgst(-1.0) == -1.0)
cfg.C532_XV_VENUE = 'pi42'
ok("the pending funding (C527Pending) carries the same GST as the ledger books (C539: on each payment, both)",
   "xd = sum(xv.fgst(-p['d_qty']" in SRC and ("fu_d = sum(self.fgst(-p['d_qty']" in SRC       # C544: the payments are
                                               or "fu_d = sum(self.fgst(r) for r in raw_d)" in SRC))  # listed, then summed
ok("every label names the second venue: margins, transfers, the watch, the panel, the total, the status row, the boot line",
   "for v, name in (('d', 'Delta'), ('b', self.v2())):" in SRC and "frm=self.v2() if src == 'b' else 'Delta'" in SRC
   and "f'Delta vs {xv.v2()} funding gap'" in SRC and 'f"paper, Delta vs {_x524.v2()}"' in SRC
   and "Delta vs {self.c524x.v2()} funding spread" in SRC and "side(v2,mg.b)" in SRC)
ok("Pi42's coin list is read from its public exchange info (no key), every 6 hours",
   om._C532_PI42_INFO == 'https://api.pi42.com/v1/exchange/exchangeInfo' and "time.time() - self._pi42_at < 6 * 3600" in SRC)

print("\n3. THE PLAN, THE LOG BLOCK, THE PAGE")
cfg.C524_XVENUE_EQUITY = 550.0; cfg.C531_XV_REBALANCE = True
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
for f in ('c524_xvenue.json',):
    try:
        os.remove(os.path.join(BASE, f))
    except OSError:
        pass
shutil.copy(os.path.join(SNAP, 'c524_xvenue.json'), BASE)
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
om._c532_pi42_coins = lambda: None
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                      'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                            _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
pf.session_start_equity = 500.0; pf.positions = om.PositionsManager()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de = bot.c521d
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOW
ok("the cross-venue ledger (the 3 Oct snapshot) rebased $500 -> $550; the Delta book stays $500 (an experiment)",
   bot.c524x.start_equity == 550.0 and de.start_equity == 500.0)
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
ok("the plan = Delta vs Pi42 $550 + the $50 reserve = $600; the books are experiments",
   T['plan']['start'] == 600.0 and [r['key'] for r in T['rows'] if r['plan']] == ['xvenue', 'reserve']
   and R['reserve']['eq'] == 50.0 and 'Pi42' in R['xvenue']['label'] and not R['delta']['plan'] and not R['book']['plan'], str(T['plan']))
_se = bot.c524x.start_equity; bot.c524x.start_equity = 0.0
T0 = om._c527_total(bot, now=NOW)
bot.c524x.start_equity = _se
ok("  the reserve alone is no plan: before the trade's first run (or off the Binance venue) the page keeps its own tile",
   T0['plan']['n'] == 0 and 'reserve' not in {r['key'] for r in T0['rows']}, str(T0['plan']))
ok("  its tax: the trades' net profit at the slab (one speculative business), the reserve untaxed",
   T['tax']['business'] == round(R['xvenue']['pnl'], 2) and T['tax']['vda'] == 0)
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=bot.c524x,
                             c530p=bot.c530p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
de.guard()
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line))
rep.status(fbot)
keys = [r.strip().split(' ')[0] for r in rows if r.strip()]
ok("the 8-minute block opens with YOUR PLAN, then 'experiments, not your money', then the Binance book's EQUITY and OPEN",
   keys.index('PLAN') < keys.index('BELOW') < keys.index('EQUITY') and keys.index('OPEN') == keys.index('EQUITY') + 1
   and keys.count('PLAN') == 1, ' '.join(keys[:8]))
pl = ' '.join(r.strip() for r in rows if r.strip().startswith('PLAN') or (rows.index(r) > 0 and False))
ix = [i for i, r in enumerate(rows) if r.strip().startswith('PLAN')][0]
blk = ' '.join(r.strip() for r in rows[ix:ix + 3])
ok("  the PLAN row: $X of $600.00, after tax, its parts by name", 'of $600.00' in blk and 'Delta vs Pi42' in blk
   and 'Reserve $50.00' in blk, blk)
ok("  DELTA says it is an experiment; XVENUE names Pi42", any('paper experiment: the book on Delta' in r for r in rows)
   and any('paper, Delta vs Pi42' in r for r in rows))


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000); pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})")   # C535: folded panels opened
        G = {k: pg.inner_text('#' + k) for k in ('eqk', 'eqs', 'dayk', 'day', 'days', 'recs', 'running', 'alltotal', 'xvenue', 'plantotal')}
        G['alltotal'] = G['plantotal'] + '\n' + G['alltotal']   # C539: the plan's total, tax and budget lines moved to "Your plan in detail" (#plantotal)
        br.close()
    ok("the top tile: your plan of $600 = Delta vs Pi42 + the reserve; the books listed as experiments",
       G['eqk'].lower() == 'your plan · paper' and 'of $600.00' in G['eqs'] and 'Delta vs Pi42 $' in G['eqs']
       and 'reserve $50.00' in G['eqs'] and 'experiments, not in your plan: Binance book' in G['eqs'] and 'Delta book $' in G['eqs'], G['eqs'])
    ok("the risk tile: your two accounts, the weaker side's %, the even-out and the reserve",
       G['dayk'].lower() == 'risk · your two accounts' and 'weaker side' in G['day'] and 'Pi42 side' in G['days']
       and 'reserve below 50%' in G['days'], G['day'] + ' | ' + G['days'])
    ok("the record tile: Delta vs Pi42 and the reserve held; no Delta book (not in the plan)",
       'Delta vs Pi42' in G['recs'] and 'reserve $50.00 held' in G['recs'] and 'Delta book' not in G['recs'], G['recs'])
    ok("what is running: YOUR PLAN first; the Binance book an EXPERIMENT", G['running'].startswith('YOUR PLAN')
       and 'EXPERIMENT the paper account (Binance, not your plan)' in G['running'], G['running'][:200])
    ok("the totals: $600 = $550 trading + $50 reserve; the slab note with Rs 12 lakh", 'your equity $600.00 = $550.00 trading + $50.00 reserve' in G['alltotal']
       and '₹12 lakh' in G['alltotal'] and 'carried 4 years' in G['alltotal'], G['alltotal'][-400:])
    ok("the cross-venue panel: Delta vs Pi42, rupees, the Binance-read note, the reserve rule",
       'Delta vs Pi42' in G['xvenue'] and 'in rupees' in G['xvenue'] and 'read from Binance' in G['xvenue']   # C542 wording
       and 'reserve (half on each venue) tops it up at once' in G['xvenue'], G['xvenue'][:400])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
