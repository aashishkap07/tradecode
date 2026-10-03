#!/usr/bin/env python3
"""C506: the fixes from the first C504 night and the 29 Sep paper check.

1. THE K4 FALSE ALARM: C504 flagged "K4 shadow missed today's rebalance"
   hourly from 28 Sep 17:20 to 29 Sep 05:37 IST, because the 28 Sep rebalance
   ran at 05:35 in a process with no K4 (C501 arrived at 13:09). K4 is now
   judged only on a rebalance this process ran.
2. THE SPOT POT LISTS WHAT IT HOLDS in its run line, coin by coin (29 Sep: the
   log said "16 held", an independent rebuild said 15, and nothing could say
   which coin differed).
3. THE LOG PUSH carries the book's and the ledgers' state files.
4. THE REBALANCE SAVES ITS INPUTS (c488_inputs.npz): on 29 Sep a replay 78
   minutes later differed 1-5% because SOL's 7-day return was -0.01%. With the
   bot's own inputs the plan recomputes to the last bit.
"""
import os, sys, io, time, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp(prefix='c506_test_')
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om506', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C506: THE K4 FALSE ALARM, THE SPOT POT'S HOLDINGS, THE LOG PUSH"); print("=" * 66)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C488_ENGINE = 'portfolio'
pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 250.0
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            _c482_risk_guard=lambda: {'pct': 15.0})
e = om.C488Engine(bot); e.reset(); bot.c488 = e
bot.c501k = om.C501Allostatic(bot)

print("\n1. THE K4 FALSE ALARM")
# 28 Sep 2026, 17:20 IST (11:50 UTC): the book rebalanced at 05:35 IST in the C499 process; K4 never ran
NOW = dt.datetime(2026, 9, 28, 11, 50, tzinfo=dt.timezone.utc).timestamp()
e._marks_at = NOW - 5; e.last_rebal = '2026-09-28'; e._last_M = None; bot.c501k.last_obs = ''
h = om.TradingBot._c504_data_health(bot, NOW)
ok("a rebalance a previous process ran, before K4 existed: not a K4 miss (the 28 Sep case)",
   h['ok'] and 'K4' not in h['keys'], str(h))
e._last_M = ('2026-09-28', 20, None)
h = om.TradingBot._c504_data_health(bot, NOW)
ok("a rebalance THIS process ran, and K4 did not record it: late", h['keys'] == ['K4'], str(h['late']))
bot.c501k.last_obs = '2026-09-28'
ok("  and on time once K4 recorded it", om.TradingBot._c504_data_health(bot, NOW)['ok'])

print("\n2. THE SPOT POT LISTS WHAT IT HOLDS")
coins = ['BNB', 'BTC', 'ETH', 'LINK']
keep = [f"{c}/USDT:USDT" for c in coins]
W = np.array([9.36, 8.72, 7.69, 1.50]) / 250.0
om._c501_s1_targets = lambda *a, **k: (W, None)
T = np.array([0]); e._last_M = (dt.datetime.utcnow().strftime('%Y-%m-%d'), 20,
                                  (T, keep, np.ones((1, 4)), np.ones((1, 4)), np.zeros((1, 4))))
sp = om.C501Spot(bot)
sp.bk = {c + 'USDT': (1.0, 1.0) for c in coins}; sp.book = lambda force=False: sp.bk
sp.last_run = '2000-01-01'; sp._tick_at = 0.0; sp._fail_at = 0.0
LOG.clear()
sp.due = lambda now=None: True
sp.tick(now=time.time())
hl = [m for m in LOG if 'C501 spot pot holds:' in m]
ok("the run is followed by 'C501 spot pot holds: BNB $9.36, BTC $8.72, ETH $7.69' (LINK $1.50 < $2: not opened)",
   len(hl) == 1 and 'BNB $9.36' in hl[0] and 'BTC $8.72' in hl[0] and 'ETH $7.69' in hl[0] and 'LINK' not in hl[0],
   hl[0] if hl else str(LOG))
ok("  and it reaches the session log", om._C460ConsoleFilter().filter(
   logging.LogRecord('OmegaV60', logging.INFO, __file__, 1, hl[0] if hl else '', None, None)))

print("\n3. THE LOG PUSH")
sh = open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read()
ok("the book's and the ledgers' state files are pushed beside state_v60.json",
   all(f'"$REPO"/data/{f}' in sh for f in ('c488_book.json', 'c490_carry.json', 'c501_spot.json',
                                          'c501_savings.json', 'c501_allostatic.json')))
ok("  after the scrubber still runs over everything pushed", sh.index('c501_allostatic.json') < sh.index('# ─── SCRUB'))
print("\n4. THE REBALANCE SAVES ITS INPUTS; THE PLAN RECOMPUTES FROM THEM TO THE CENT")
g = np.random.default_rng(506); n, k = 420, 30
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
e2 = om.C488Engine(b2); e2.reset(); ref[0] = e2; p2._c488 = e2; b2.c488 = e2
for j, sy in enumerate(keep2):
    x = float(cl[-1, j]); e2.marks[sy] = dict(bid=x * 0.9999, ask=x * 1.0001, last=x, fr=0.0001, vol=float(qv2[-1, j]))
    b2.exchange.markets[sy] = dict(precision={'amount': 0.001}, limits={'amount': {'min': 0.0}})
e2._marks_at = time.time() + 1e6
e2.refresh_marks = lambda force=False: True; e2.refresh_rules = lambda force=False: True
e2.candidates = lambda nn: keep2; e2.matrices = lambda ss: (T2, keep2, cl, qv2, fd)
e2.rebalance('test')
fp = os.path.join(om.BASE_PATH, 'c488_inputs.npz')
ok("the rebalance saved c488_inputs.npz beside the book's state", os.path.exists(fp))
z = np.load(fp)
same = (np.array_equal(z['T'], T2) and [str(x) for x in z['keep']] == keep2 and np.array_equal(z['close'], cl)
        and np.array_equal(z['qv'], qv2) and np.array_equal(z['fund'], fd) and float(z['eq'][0]) > 0)
ok("  it holds exactly the data the rebalance used (T, coins, closes, volumes, funding, equity, top N)", same)
w_bot = om._c488_targets(T2, cl, qv2, fd, 20, e2.target_vol(), 3.0)[0]
w_rep = om._c488_targets(z['T'], z['close'], z['qv'], z['fund'], int(z['n_top'][0]), e2.target_vol(), 3.0)[0]
ok("  and the plan recomputed from the file equals the bot's to the last bit", np.array_equal(w_bot, w_rep))
rp = open(os.path.join(REPO, 'research', 'c498_plan_replay.py')).read()
ok("the replay tool reads the file ('--inputs')", "'--inputs' in sys.argv" in rp and "z['close']" in rp)
ok("version C506 or later", int(om._OMEGA_VERSION[1:4]) >= 506)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
