#!/usr/bin/env python3
"""C534: three fixes from the C533 screens (4 Oct 21:50 IST).

1. Pi42's coin list loads soon after a start (C533 said "loads at the next run" for up to a day, and a
   server that could not reach api.pi42.com would only have said so at 06:00 IST): one log line with the
   count and the held pairs it does not list; a failure warns once and retries every 10 minutes.
2. PLAN SO FAR: each part's figure is the live one, the same as the headline (C533: +0.11% above,
   "Delta vs Pi42 -0.01%" -- the figure booked at the daily run -- below).
3. The Delta book is "a paper experiment, the same book", not "same plan" (YOUR PLAN is the money).
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c534_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c534-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om534', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C534: PI42'S LIST AT START, THE PLAN TILE LIVE, THE DELTA BOOK AN EXPERIMENT"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C534 or later", int(om._OMEGA_VERSION[1:]) >= 534)

print("\n1. PI42'S COIN LIST SOON AFTER A START")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
x0 = json.load(open(os.path.join(SNAP, 'c524_xvenue.json')))
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
CALLS = []
PI42 = {'answer': None}


def _fake_pi42():
    CALLS.append(time.time())
    return PI42['answer']


om._c532_pi42_coins = _fake_pi42
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
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
LOG.clear()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
xv = bot.c524x; de = bot.c521d
ok("the server's ledger: 10 pairs held from the Binance days, Pi42's list not loaded yet", len(xv.pairs) == 10 and not xv.pi42)
LOG.clear(); CALLS.clear()
xv.pi42_boot()
w = [m for lv, m in LOG if lv >= logging.WARNING and 'C534' in m]
ok("api.pi42.com does not answer: one warning, with the check to run", len(CALLS) == 1 and len(w) == 1
   and "did not load" in w[0] and 'curl' in w[0] and 'api.pi42.com/v1/exchange/exchangeInfo' in w[0], w[0][:200] if w else '')
xv.pi42_boot()
ok("  no second try within 10 minutes", len(CALLS) == 1)
xv._pi42_try -= 601
xv.pi42_boot()
ok("  after 10 minutes it tries again, without a second warning", len(CALLS) == 2
   and len([m for lv, m in LOG if lv >= logging.WARNING and 'C534' in m]) == 1)
held = sorted(xv.pairs)
PI42['answer'] = set(held[:3]) | {'C%02d' % i for i in range(40)}
xv._pi42_try -= 601; LOG.clear()
xv.pi42_boot()
inf_ = [m for lv, m in LOG if 'C534 Pi42' in m]
gone = ', '.join(held[3:])
ok("it answers: one line with the count and the held pairs Pi42 does not list (closed at the daily run)",
   len(inf_) == 1 and f"loaded: {len(PI42['answer'])} rupee perps" in inf_[0] and gone in inf_[0], inf_[0][:240] if inf_ else '')
n = len(CALLS); xv.pi42_boot(); xv._pi42_try -= 601; xv.pi42_boot()
ok("  loaded once: no more tries from here (the 6-hour refresh and the daily run keep it fresh)", len(CALLS) == n)
ok("the minute loop asks for it before the daily-run check (so it loads whatever the hour)",
   SRC.index('self.pi42_boot()') < SRC.index("if not self.due() or time.time() - self._fail_at < 300:", SRC.index('def tick(self):', SRC.index('class C524CrossVenue'))))
off = om.C524CrossVenue(bot); cfg.C532_XV_VENUE = 'binance'; n = len(CALLS); off.pi42 = set(); off.pi42_boot()
ok("  with Binance as the second venue it asks nothing", len(CALLS) == n)
cfg.C532_XV_VENUE = 'pi42'

print("\n2. THE PAGE")
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOW
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
st = xv.status()
ok("the case on the page: the plan's live % differs from the ledger's booked %",
   round(R['xvenue']['pct'], 2) != round(100 * (st['eq'] / st['start_equity'] - 1), 2), f"{R['xvenue']['pct']} vs {st.get('pct')}")
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv,
                             c530p=bot.c530p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


def page():
    port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000); pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})")   # C535: folded panels opened
        G = {k: pg.inner_text('#' + k) for k in ('rec', 'recs', 'xvenue', 'delta')}
        G['h2'] = pg.inner_text('body')
        br.close()
    return G, errs


try:
    G, errs = page()
    ok("PLAN SO FAR: the part's figure is the headline's (live), the funding 'booked'",
       G['rec'].strip() in G['recs'] and 'Delta vs Pi42 ' + G['rec'].strip() in G['recs'] and 'booked' in G['recs'],
       G['rec'] + ' | ' + G['recs'].replace('\n', ' | '))
    ok("the cross-venue panel: Pi42's coins counted once the list loaded", "Pi42's 43 coins only" in G['xvenue'], G['xvenue'][:300])
    ok("the Delta book: 'paper experiment, the same book' and the Binance book's targets",
       'paper experiment, the same book' in G['h2'].lower() and '(paper, same plan)' not in G['h2'].lower(), '')
    ok("  its panel: 'the Binance book's own targets held on Delta's whole contracts'",
       "the Binance book\u2019s own targets held on Delta\u2019s whole contracts" in G['delta'], G['delta'][:120])
    xv.pi42 = set()
    G2, errs2 = page()
    ok("before the list loads, the panel says so in amber: not loaded yet, tried every 10 min",
       "Pi42's coin list not loaded yet (tried every 10 min; without it nothing new opens)" in G2['xvenue'], G2['xvenue'][:300])
    ok("no JavaScript errors", not errs and not errs2, str(errs + errs2))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
