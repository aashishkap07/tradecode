#!/usr/bin/env python3
"""C513: what the first C512 dashboard (30 Sep 2026, 09:35 IST) showed.

Every figure on the four screens reconciled with the server's files and
Bitget's minute prices. Two wordings did not say exactly what is true:

1. THE RULE TOURNAMENT'S DATES. C512 dropped the 29 Sep row (scored on an
   unfinished candle), so the first day it will score is 30 Sep -- but the
   page said "first scores at the next rebalance since 2026-09-29", and from
   tomorrow would have said "1 days scored since 2026-09-29" about a record
   that starts on 30 Sep. The dates are now the days scored: "first score at
   the next rebalance, for 2026-09-30", then "1 day scored, from 2026-09-30".
   The log's tournament line and the 8-minute TOURNEY row say the same.
2. C509 UNDER A DAY. The page wrote "since the book began (29 Sep): 0.12%"
   without the sign or the span the log gives; it now reads "+0.12% in 0.8
   days", as the log does.
"""
import os, io, json, time, glob, socket, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c513_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c513-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om513', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C513: THE TOURNAMENT'S DATES ARE THE DAYS IT SCORED"); print("=" * 66)
DAY = 86400000
d_ = lambda ms: dt.datetime.utcfromtimestamp(ms / 1000).strftime('%Y-%m-%d')

# ─── synthetic matrices (as omega_c510_test.py): 420 days x 30 coins ───
g = np.random.default_rng(513); n, k = 420, 30
T = (np.arange(n) + 19000) * DAY
ret = g.normal(0.0004, 0.035, size=(n, k)) + g.normal(0, 0.02, size=(n, 1))
close = np.exp(np.cumsum(ret, axis=0)) * 10
op = np.vstack([close[:1], close[:-1]])
hi = np.maximum(op, close) * np.exp(np.abs(g.normal(0, 0.02, size=(n, k))))
lo = np.minimum(op, close) * np.exp(-np.abs(g.normal(0, 0.02, size=(n, k))))
qv = np.exp(g.normal(16, 0.7, size=(n, k)))
fund = g.normal(0.00005, 0.00025, size=(n, k)) * 3
keep = [f"K{j:02d}/USDT:USDT" for j in range(k)]

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 20.0; cfg.C488_ENGINE = 'portfolio'
om._c467_cfg_ref[0] = cfg
pf = om.Portfolio(cfg); pf.equity = 249.93; pf.available_balance = 227.0; pf.session_start_equity = 250.0
pf.get_live_equity = lambda *a: 250.29
pf.lifetime_trades = pf.lifetime_wins = pf.lifetime_losses = 0; pf.lifetime_pnl = -0.07
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={1: 1}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 250.0, 'month_budget': 50.0,
                                                      'month_used': 0.0, 'day_cap': 12.5, 'day_used': 0.0, 'halt': ''})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot)
bot.c501s = om.C501Spot(bot); bot.c501v = om.C501Savings(bot); bot.c501k = om.C501Allostatic(bot)
bot.c510t = om.C510Tournament(bot); bot.c510t.reset()

print("\n1. THE LOG LINE AND STATUS, THROUGH observe()")
t = bot.c510t
LOG.clear(); t.observe(T[:n - 1], keep, close[:n - 1], qv[:n - 1], fund[:n - 1], (op[:n - 1], hi[:n - 1], lo[:n - 1]),
                       20, 0.2667, 3.0, 250.0)
s0 = t.status(); l0 = ' '.join(m for lv, m in LOG if 'C510 tournament' in m)
ok("first observation: no day scored; the next score is for the day after the last close in the matrices",
   s0['days'] == 0 and s0['first'] == '' and s0['next_day'] == d_(int(T[n - 1])), str((s0['first'], s0['next_day'])))
ok(f"  the log: 'first score, for {d_(int(T[n - 1]))}, at the next rebalance'",
   f"first score, for {d_(int(T[n - 1]))}, at the next rebalance" in l0 and 'days scored since' not in l0, l0[:160])
LOG.clear(); t.observe(T, keep, close, qv, fund, (op, hi, lo), 20, 0.2667, 3.0, 250.0)
s1 = t.status(); l1 = ' '.join(m for lv, m in LOG if 'C510 tournament' in m)
ok("a day later: 1 day scored, and 'first' is the day scored (not the day the books were first held)",
   s1['days'] == 1 and s1['first'] == d_(int(T[n - 1])) and s1['next_day'] == d_(int(T[n - 1]) + DAY),
   str((s1['days'], s1['first'], s1['next_day'], s1['since'])))
ok(f"  the log: '1 day scored from {d_(int(T[n - 1]))}' (singular)",
   f"1 day scored from {d_(int(T[n - 1]))}" in l1 and '1 days' not in l1, l1[:160])

print("\n2. AFTER C512'S DROP: THE SERVER'S 30 SEP STATE")
# the server's c510_tournament.json at 03:47 UTC 30 Sep (logs branch): books held since the 29 Sep
# first rebalance, one row scored for 29 Sep, last_day = 29 Sep 00:00 UTC; C512 drops the row on load
D29, D30 = 1790640000000, 1790726400000
p = os.path.join(om.BASE_PATH, 'c510_tournament.json')
json.dump(dict(w={'n2n3': {'ZEC/USDT:USDT': 0.03}, 'base': {'ZEC/USDT:USDT': 0.04}}, pend={'n2n3': 0.0},
               last_day=D29, last_obs='2026-09-30', daily=[[D29, {'n2n3': -0.0018206, 'base': -0.001751}]],
               eq0=250.0, since='2026-09-29', skipped={}), open(p, 'w'))
bot.c510t = om.C510Tournament(bot)
s2 = bot.c510t.status()
ok("the 29 Sep row dropped; the next score is for 2026-09-30 (the record the report promised)",
   s2['days'] == 0 and s2['next_day'] == '2026-09-30' and s2['first'] == '', str((s2['days'], s2['next_day'])))
e.born = dict(ts=time.time() - 0.8 * 86400, eq=250.0, approx=False)
e.month = {'key': dt.datetime.now().strftime('%Y-%m'), 'eq0': 250.0}
e.marks = {'NEAR/USDT:USDT': dict(bid=4.92, ask=4.93, last=4.925, fr=0.0001, vol=9e9)}
e.book = {'NEAR/USDT:USDT': dict(qty=2.0, avg=4.7466, fees=0.006, funding=0.0, realized=0.0, opened=time.time() - 69000)}
e._marks_at = time.time(); e.last_rebal = dt.datetime.utcnow().strftime('%Y-%m-%d')
e.fills_run = [1, 0.004, 6.16]; e.tally = dict(n=0, w=0, l=0, pnl=0.0)
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep.status(bot)
tr = ' '.join(r for r in rows if r.strip().startswith('TOURNEY') or (rows.index(r) > 0 and 'first score' in r))
ok("the 8-minute TOURNEY row: '2 rules held | first score at the next rebalance, for 2026-09-30'",
   '2 rules held' in tr and 'first score at the next rebalance, for 2026-09-30' in tr and 'since 2026-09-29' not in tr, tr)
bot.c510t.daily = [[D30, {'n2n3': 0.0021, 'base': 0.0015}]]; bot.c510t.last_day = D30
rows.clear(); rep.status(bot)
tr1 = next((r for r in rows if r.strip().startswith('TOURNEY')), '')
ok("  tomorrow: 'TOURNEY 1d from 2026-09-30 | base +0.15% | N2+N3* +0.21%'",
   '1d from 2026-09-30' in tr1 and 'N2+N3* +0.21%' in tr1, tr1)
bot.c510t.daily = []; bot.c510t.last_day = D29

print("\n3. THE PAGE (Chromium)")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


pf.positions = om.PositionsManager()
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t,
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
        tt0 = pg.inner_text('#tourney'); bk = pg.inner_text('#book')
        bot.c510t.daily = [[D30, {'n2n3': 0.0021, 'base': 0.0015}]]; bot.c510t.last_day = D30
        pg.reload(); pg.wait_for_timeout(3000)
        tt1 = pg.inner_text('#tourney')
        pf.get_live_equity = lambda *a: 249.80
        pg.reload(); pg.wait_for_timeout(3000)
        bk2 = pg.inner_text('#book')
        br.close()
    ok("the tournament today: 'first score at the next rebalance, for 2026-09-30', not 'since 2026-09-29'",
       'first score at the next rebalance, for 2026-09-30' in tt0 and 'since 2026-09-29' not in tt0, tt0[:200])
    ok("  tomorrow: '1 day scored, from 2026-09-30' (singular), and each rule's score",
       '1 day scored, from 2026-09-30' in tt1 and '1 days' not in tt1 and '+0.21%' in tt1, tt1[:200])
    ok("C509 under a day: 'since the book began (..): +0.12% in 0.8 days · under a day: too early to judge'",
       '+0.12% in 0.8 days' in bk and 'too early to judge' in bk, [x for x in bk.split('\n') if 'book began' in x])
    ok("  a loss keeps its minus sign, and gets no '+': '-0.08% in 0.8 days'",
       '-0.08% in 0.8 days' in bk2 and '+-' not in bk2, [x for x in bk2.split('\n') if 'book began' in x])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
ok("version C513 or later", int(om._OMEGA_VERSION[1:4]) >= 513)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
