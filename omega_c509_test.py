#!/usr/bin/env python3
"""C509: is this normal? The book's result so far against its own tested range.

On 29 Sep 2026, four days after the book began, it was 4.5% down and the only
way to judge that was to ask. The rule's 2020-26 test (research/
c509_normal_range.py) gives the percentiles of its k-day returns; the bot now
says where the book stands among them.

1. THE TABLE in the bot equals the research file's, number for number.
2. THE START: a book file written before C509 is given its real start (the
   first build, 25 Sep 12:16:57 UTC, $252.63); any other old book is marked
   approximate; a fresh book's first rebalance records its own start.
3. THE ARITHMETIC: 29 Sep 05:41 UTC, marked $241.33 -> -4.47% in 3.7 days,
   normal -1.8% to +2.7%, the bottom 2%: rare. The dial scales the range; under
   a day is "too early"; the month appears once the book is older than it.
4. WHERE IT IS SAID: the status JSON, the 8-minute block's CONTEXT row, the
   rebalance log line (which reaches the session log), and the page (Chromium).
"""
import os, sys, io, json, time, glob, socket, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c509_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c509-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om509', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C509: IS THIS NORMAL?"); print("=" * 66)

print("\n1. THE TABLE")
R = json.load(open(os.path.join(REPO, 'research', 'c509_normal_range.json')))
ok("the bot's percentiles are the research file's, for all 16 spans",
   list(om._C509_P) == R['percentiles'] and sorted(om._C509_RANGES) == sorted(int(k) for k in R['days'])
   and all(list(om._C509_RANGES[int(k)]) == v for k, v in R['days'].items()))
ok("  every row rises from p1 to p99", all(all(a < b for a, b in zip(r, r[1:])) for r in om._C509_RANGES.values()))

print("\n2. THE START")
BUILD = dt.datetime(2026, 9, 25, 12, 16, 57, tzinfo=dt.timezone.utc).timestamp()
ok("the first build is 25 Sep 2026 12:16:57 UTC (17:46:57 IST in the log), $252.63",
   abs(om._C509_FIRST_BUILD[0] - BUILD) < 1 and om._C509_FIRST_BUILD[1] == 252.63)
# the server's book file as uploaded at 05:47 UTC on 29 Sep (logs/c488_book.json), trimmed
srv = {'book': {'NEAR/USDT:USDT': {'qty': 2.0, 'avg': 4.9602, 'opened': 1790338616.7848876},
                'ZEC/USDT:USDT': {'qty': 0.006, 'avg': 1642.71, 'opened': 1790467524.96552},
                'XRP/USDT:USDT': {'qty': -6.0, 'avg': 1.4982, 'opened': 1790640354.1201746}},
       'closed': [{'sym': 'ETH/USDT:USDT', 'days': 0.5, 't': 1790381135.0442028},
                  {'sym': 'PUMP/USDT:USDT', 'days': 3.5, 't': 1790640352.9179544}],
       'month': {'key': '2026-09', 'eq0': 252.8061}}
b = om.C488Engine._c509_backfill(srv)
ok("the server's book (NEAR opened at the first build) gets exactly that start, not approximate",
   b == dict(ts=om._C509_FIRST_BUILD[0], eq=252.63, approx=False), str(b))
ok("  a closed position's age (rounded to 0.1 day) does not pull the start 11 minutes early",
   b['ts'] == om._C509_FIRST_BUILD[0])
other = {'book': {'BTC/USDT:USDT': {'qty': 0.001, 'avg': 80000.0, 'opened': BUILD + 5 * 86400}},
         'closed': [{'t': BUILD + 9 * 86400, 'days': 6.0}], 'month': {'key': '2026-10', 'eq0': 300.0}}
b2 = om.C488Engine._c509_backfill(other)
ok("any other old book: its earliest position (here a closed one, clearly earlier), the month anchor, approximate",
   b2 == dict(ts=round(BUILD + 3 * 86400, 1), eq=300.0, approx=True), str(b2))
ok("  an empty book has no start", om.C488Engine._c509_backfill({'book': {}, 'closed': []}) == {})

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = 'portfolio'
om._c467_cfg_ref[0] = cfg
pf = om.Portfolio(cfg); pf.equity = 243.80; pf.available_balance = 223.0; pf.session_start_equity = 243.80
pf.get_live_equity = lambda *a: 241.33
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92,
                                                      'month_used': 11.48, 'day_cap': 9.0, 'day_used': 0.0, 'halt': ''})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
json.dump(dict(srv, last_rebal='2026-09-29'), open(e.path, 'w'))
e2 = om.C488Engine(bot)
ok("loading that file (no 'born' in it) backfills the start", e2.born.get('eq') == 252.63, str(e2.born))
e2.save(); d = json.load(open(e.path))
ok("  and the next save writes it, so it is read back, not re-derived", d.get('born') == e2.born, str(d.get('born')))
e2.reset()
ok("a reset (fresh start) clears it", e2.born == {} and json.load(open(e.path)).get('born') == {})

print("\n3. THE ARITHMETIC")
NOW = dt.datetime(2026, 9, 29, 5, 41, tzinfo=dt.timezone.utc).timestamp()        # 11:11 IST, the screenshot
e.born = dict(ts=om._C509_FIRST_BUILD[0], eq=252.63, approx=False)
e.month = {'key': '2026-09', 'eq0': 252.8061}
c = e.context(now=NOW)['start']
f = (NOW - BUILD) / 86400 - 3
row = [(1 - f) * a + f * b for a, b in zip(R['days']['3'], R['days']['4'])]
ret = 241.33 / 252.63 - 1
pct = 1 + 4 * (ret - row[0]) / (row[1] - row[0])
ok(f"since the book began: -$11.30 ({100 * ret:+.2f}%) in {(NOW - BUILD) / 86400:.2f} days",
   c['pnl'] == -11.3 and abs(c['ret'] - ret) < 1e-5 and abs(c['days'] - 3.73) < 0.01, str(c))
ok(f"  normal for that long (p10-p90, interpolated 3->4 days): {100 * row[2]:+.2f}% to {100 * row[6]:+.2f}%",
   abs(c['p10'] - row[2]) < 1e-5 and abs(c['p90'] - row[6]) < 1e-5)
ok(f"  rank {pct:.1f}th percentile: the bottom 2%, 'rare' (c507: a 4-day loss >= 3.9% came in 2.3% of spans)",
   abs(c['pct'] - round(pct, 1)) < 0.06 and c['word'] == 'rare', f"{c['pct']} {c['word']}")
ok("  no month line: the book is younger than September", 'month' not in e.context(now=NOW))
txt = om._c509_text(c, 'since the book began 25 Sep')
ok("the words: '-$11.30 (-4.47%) in 3.7 days | normal for that long -1.8% to +2.7% ... | bottom 2%: rare'",
   '-$11.30 (-4.47%) in 3.7 days' in txt and '-1.8% to +2.7%' in txt and 'bottom 2%: rare' in txt, txt)
cfg.C380_MAX_MONTHLY_DD_PCT = 20.0
c20 = e.context(now=NOW)['start']
ok("dial 20%: the range scales by 20/15 (vol target 26.7%) and the same loss ranks less rare",
   abs(c20['p10'] - row[2] * 4 / 3) < 1e-5 and c20['pct'] > c['pct'], f"{c20['p10']} {c20['pct']}")
cfg.C380_MAX_MONTHLY_DD_PCT = 0.0
ok("dial 0%: no context (the book is closed)", e.context(now=NOW) == {})
cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
cy = e.context(now=BUILD + 0.4 * 86400)['start']
ok("under a day: a number, but 'too early to judge'", 'pct' not in cy and 'too early' in om._c509_text(cy, 'x'), str(cy))
OCT5 = dt.datetime(2026, 10, 5, 6, 0).timestamp()                                # local calendar, as the guard's
e.month = {'key': '2026-10', 'eq0': 240.00}
cm = e.context(now=OCT5)
ok("in October the month appears too: from 1 Oct's anchor, 4.25 days",
   cm['month']['since'] == '01 Oct' and abs(cm['month']['days'] - 4.25) < 0.01 and cm['month']['pnl'] == 1.33
   and 'start' in cm, str(cm.get('month')))
c4 = om._c509_context(BUILD, 252.63, 252.63 * 1.40, BUILD + 400 * 86400)
ok("beyond a year the 365-day row is used; +40% is the median", c4['word'] == 'normal' and 45 < c4['pct'] < 55, str(c4))
c5 = om._c509_context(BUILD, 252.63, 252.63 * 0.9, BUILD + 2 * 86400)
ok("-10% in 2 days: 'beyond the tested range', 'worse than 99% of spans'",
   c5['word'] == 'beyond the tested range' and 'worse than 99% of spans' in om._c509_text(c5, 'x'))

print("\n4. WHERE IT IS SAID")
e.month = {'key': '2026-09', 'eq0': 252.8061}
e.marks = {'NEAR/USDT:USDT': dict(bid=4.9, ask=4.91, last=4.905, fr=0.0001, vol=9e9)}
e.book = {'NEAR/USDT:USDT': dict(qty=2.0, avg=4.9602, fees=0.006, funding=0.0, realized=0.0, opened=BUILD)}
e._marks_at = time.time(); e.last_rebal = '2026-09-29'
REAL = time.time()
e.born = dict(ts=REAL - (NOW - BUILD), eq=252.63, approx=False)        # the same 3.73 days, ending now
st = e.status()
ok("the status JSON carries it (c488.context.start)", abs(st['context']['start']['pct'] - c['pct']) < 0.1,
   str(st.get('context')))
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot)
bot.c501s = om.C501Spot(bot); bot.c501v = om.C501Savings(bot); bot.c501k = om.C501Allostatic(bot)
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep.status(bot)
i = [k for k, r in enumerate(rows) if r.strip().startswith('CONTEXT')]
blk = ' '.join(rows[i[0]:i[0] + 3]) if i else ''
ok("the 8-minute block: 'CONTEXT since .. -$11.30 (-4.47%) in 3.7d | normal -1.8% to +2.7% | bottom 2%: rare'",
   bool(i) and '-4.47%' in blk and 'in 3.7d' in blk and 'normal -1.8% to +2.7%' in blk and 'bottom 2%: rare' in blk,
   blk or '\n'.join(rows))
# the rebalance records a fresh book's start and says where it stands
g = np.random.default_rng(509); n, k = 420, 30
T2 = (np.arange(n) + 20000) * 86400000
cl = np.exp(np.cumsum(g.normal(0.0005, 0.03, size=(n, k)), axis=0)) * 10
qv2 = np.exp(g.normal(16, 0.7, size=(n, k))); fd = g.normal(0.0001, 0.0002, size=(n, k)) * 3
keep2 = [f"K{j:02d}/USDT:USDT" for j in range(k)]
class FakeEx:
    def __init__(s, ref): s.exchange = types.SimpleNamespace(markets={}); s.markets = s.exchange.markets; s.ref = ref
    def place_order(s, sym, side, qty, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        m = s.ref[0].marks[sym]
        return {'id': 'p', 'status': 'closed', 'price': m['ask'] if side == 'buy' else m['bid'], 'filled': qty}
    def c487_settle(s, sym, o, side, price, size, wait): return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym): return None
c2 = om.Config(); c2.PAPER_MODE = True; c2.C380_MAX_MONTHLY_DD_PCT = 15.0
p2 = om.Portfolio(c2); p2.equity = p2.available_balance = 250.0
ref = [None]
b2 = types.SimpleNamespace(cfg=c2, portfolio=p2, exchange=FakeEx(ref), _c462_state_settled=True,
                           _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 250.0})
f2 = om.C488Engine(b2); f2.reset(); ref[0] = f2; p2._c488 = f2; b2.c488 = f2
for j, sy in enumerate(keep2):
    x = float(cl[-1, j]); f2.marks[sy] = dict(bid=x * 0.9999, ask=x * 1.0001, last=x, fr=0.0001, vol=float(qv2[-1, j]))
    b2.exchange.markets[sy] = dict(precision={'amount': 0.001}, limits={'amount': {'min': 0.0}})
f2._marks_at = time.time() + 1e6
f2.refresh_marks = lambda force=False: True; f2.refresh_rules = lambda force=False: True
f2.candidates = lambda nn: keep2; f2.matrices = lambda ss: (T2, keep2, cl, qv2, fd)
t0 = time.time(); LOG.clear(); f2.rebalance('first')
ok("a fresh book's first rebalance records its start: now, the equity it sized from, not approximate",
   abs(f2.born.get('ts', 0) - t0) < 60 and f2.born.get('eq') == 250.0 and f2.born.get('approx') is False, str(f2.born))
f2.born['ts'] -= 2 * 86400; eq_b = f2.live_equity(); f2.last_rebal = ''; LOG.clear(); f2.rebalance('daily')
ll = [m for m in LOG if 'C509' in m]
ok("  the next rebalance keeps it, and logs 'C509 since the book began ..: ... | bottom/top N%: <word>'",
   f2.born.get('eq') == 250.0 and len(ll) == 1 and 'since the book began' in ll[0] and 'normal for that long' in ll[0],
   str(ll))
ok("  that line reaches the session log", om._C460ConsoleFilter().filter(
   logging.LogRecord('OmegaV60', logging.INFO, __file__, 1, ll[0] if ll else '', None, None)))
f2.born = {}; f2.last_rebal = ''; f2.rebalance('daily')
ok("  a book that already held positions when its start was first recorded is marked approximate",
   bool(f2.book) and f2.born.get('approx') is True, str(f2.born))

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


pf.positions = om.PositionsManager()
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        bk = pg.inner_text('#book')
        br.close()
    ok("the page: 'since the book began (.., 3.7 days): -$11.30 (-4.47%) · normal for that long: -1.8% to +2.7% "
       "... bottom 2%: rare'", 'since the book began (' in bk and '3.7 days' in bk and '-$11.30 (-4.47%)' in bk
       and '-1.8% to +2.7%' in bk and 'bottom 2%: rare' in bk, bk)
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
ok("version C509 or later", int(om._OMEGA_VERSION[1:4]) >= 509)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
