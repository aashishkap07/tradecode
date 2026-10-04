#!/usr/bin/env python3
"""C529: the 3 Oct 22:58 IST screens and the detail log, audited.

On the server's own ledgers (research/c527_snapshot/) and real prices:
1. The plan's book (the Delta copy) has its own exit: a month guard on its own marked equity (the
   operator's dial) that closes everything and opens nothing until next month, and it closes when the
   main book halts (no fresh plan). Before C529 the main book's guard left the Delta copy open with no
   exit at all.
2. The cross-venue trade's two venues kept apart: each side's P&L, its equity, leverage, and a margin
   watch (warn at 65%, the reserve at 50%); the funding settled since the last run per pair.
3. The screens: no "every account" sum, the plan in "what is running", the cross-venue paper ledger
   listed, "this run" on marked equity like the log, "today realised", the banner's realised
   month figure said plainly, the boot line's Savings rate, the PLAN status row.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
from datetime import datetime
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c529_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c529-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
spec = importlib.util.spec_from_file_location('om529', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C529: THE SCREENS AND THE LOG, AUDITED"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C529 or later", int(om._OMEGA_VERSION[1:]) >= 529)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg

# C530 changed the operator's allocation ($250 cross-venue, Pendle $100 in the plan, a $100 reserve); this
# test checks its own version's mechanics at the allocation it was written for (omega_c530_test.py checks C530's)
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C527_PLAN = ('delta', 'xvenue'); cfg.C528_RESERVE = 200.0; cfg.C530_PENDLE = False
cfg.C521_DELTA_EQUITY = 500.0; cfg.C528_BUDGET = 1000.0; cfg.C531_XV_REBALANCE = False   # and C531's ($600, no reserve)
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); de0 = L('c521_delta'); xv0 = L('c524_xvenue'); bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
bot.c501v = om.C501Savings(bot); bot.c501s = om.C501Spot(bot); bot.c490 = om.C490Carry(bot)
bot.c521d = om.C521Delta(bot); bot.c521b = om.C521Bfusd(bot); bot.c524x = om.C524CrossVenue(bot)
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de = bot.c521d
de.marks = {s: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s, (m, b, a) in PX['delta'].items()}
de._marks_at = NOW
de.prods = {s[:-3]: dict(sym=s, cv=p['cv'], iv=28800, taker=0.0005) for s, p in de0['pos'].items()}

print("\n1. THE PLAN'S BOOK (THE DELTA COPY) HAS ITS OWN EXIT")
key = datetime.now().strftime('%Y-%m')
eq_a = de.equity()
ok("the snapshot's Delta book: 9 positions", len(de.pos) == 9, str(len(de.pos)))
de.guard()
ok("its month anchor is set on its own marked equity, budget = the dial (20%) of it",
   de.month.get('key') == key and abs(de.month['eq0'] - eq_a) < 1e-4 and abs(de._guard_view['budget'] - round(0.2 * eq_a, 2)) < 0.011
   and de.halt == '', str(de._guard_view))
de.month['eq0'] = eq_a / 0.79                                   # the book is now 21% below its month anchor
cash0, n0 = de.cash, len(de.pos)
exp_close = sum(p['qty'] * p['cv'] * ((de.marks[s]['bid'] if p['qty'] > 0 else de.marks[s]['ask']) - p['avg'])
                for s, p in de.pos.items())
de.guard()
ok("21% below the anchor: every position closed at Delta's bid/ask, and it halts for the month",
   not de.pos and de.halt == 'month:' + key and any('C529 Delta book' in m and 'positions closed' in m for _, m in LOG),
   f"{len(de.pos)} left, halt {de.halt!r}")
ok("  the cash takes each position's realised P&L less the closing fees",
   de.cash < cash0 + exp_close + 1e-9 and de.cash > cash0 + exp_close - 0.25, f"{de.cash - cash0:+.4f} vs {exp_close:+.4f}")
LOG.clear()
de.rebalance(list(e.book), [0.05] * len(e.book), 'daily')
ok("  while halted, a rebalance opens nothing (and says why)", not de.pos and any('no new positions' in m for _, m in LOG))
de.month = dict(key='2026-09', eq0=1.0); de.halt = 'month:2026-09'
de.guard()
ok("a new month: a fresh anchor, the halt clears, it rebuilds at the next rebalance",
   de.halt == '' and de.month['key'] == key, de.halt)
bot.c521d = om.C521Delta(bot)                                   # back to the snapshot's 9 positions
de = bot.c521d
de.marks = {s: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s, (m, b, a) in PX['delta'].items()}
de.prods = {s[:-3]: dict(sym=s, cv=p['cv'], iv=28800, taker=0.0005) for s, p in de0['pos'].items()}
e.halt = 'month:' + key
de.guard()
ok("the main book halted by ITS guard: no fresh plan arrives, so the Delta copy closes too",
   not de.pos and de.halt.startswith('main book halted'), de.halt)
e.halt = ''
de.guard()
ok("  and clears when the main book resumes", de.halt == '')
ok("the guard is saved and loaded", 'month=self.month, halt=self.halt' in SRC and "self.halt = str(d.get('halt') or '')" in SRC)
ok("its status carries the guard for the panel", 'guard' in de.status() and 'halt' in de.status())
bot.c521d = om.C521Delta(bot); de = bot.c521d
de.marks = {s: dict(mark=m, bid=b or m, ask=a or m, fr=0.0) for s, (m, b, a) in PX['delta'].items()}
de._marks_at = NOW

print("\n2. THE CROSS-VENUE TRADE'S TWO ACCOUNTS")
xv = bot.c524x
ok("a ledger begun before C529: its two sides are seeded so they sum to its P&L exactly",
   abs(xv.side['d'] + xv.side['b'] - (xv0['eq'] - xv0['start_equity'])) < 1e-9, str(xv.side))
m = xv.margins()
mid = lambda ba: (ba[0] + ba[1]) / 2
mv_d = sum(p['d_qty'] * p['cv'] * (PX['delta'][p['d_sym']][0] - p['d_px']) for p in xv0['pairs'].values())
mv_b = sum(p['b_qty'] * (mid(PX['perp'][c + 'USDT']) - p['b_px']) for c, p in xv0['pairs'].items())
ok("each side = its half of the start + its own P&L + the move since the last mark; the two sum to the ledger",
   abs(m['d']['eq'] - (250 + xv.side['d'] + mv_d)) < 0.011 and abs(m['b']['eq'] - (250 + xv.side['b'] + mv_b)) < 0.011
   and abs(m['d']['eq'] + m['b']['eq'] - (xv0['eq'] + mv_d + mv_b)) < 0.021, json.dumps(m))
ok("  leverage = the side's notional / its equity (about 2x at 10 pairs of 10%)",
   1.8 < m['d']['lev'] < 2.2 and 1.8 < m['b']['lev'] < 2.2, f"{m['d']['lev']} {m['b']['lev']}")
LOG.clear()
xv.side['d'] = -0.45 * 250
xv.margin_watch(); xv.margin_watch()
w = [m_ for _, m_ in LOG if 'C529 cross-venue' in m_]
ok("a side at ~55%: one warning a day (not every hour)", len(w) == 1 and 'Delta side' in w[0] and 'at 50% the reserve' in w[0], str(w))
LOG.clear()
xv.side['d'] = -0.60 * 250
xv.margin_watch()
w = [m_ for _, m_ in LOG if 'C529 cross-venue' in m_]
ok("  at ~40%: the reserve line (live, the reserve tops that side up)", len(w) == 1 and 'reserve tops it up' in w[0], str(w))
xv.side = {'d': 0.0, 'b': 0.0}
ok("run() keeps the sides: each leg's price move and funding, each venue's own costs in and out",
   "self.side['d'] += p['d_qty'] * p['cv'] * (dpx - p['d_px']) + fu_d" in SRC and "self.side['b'] += p['b_qty'] * (bpx - p['b_px']) + fu_b" in SRC
   and SRC.count("self.side['b'] -= n * _C524_COST_B; self.side['d'] -= n * _C524_COST_D") == 1
   and SRC.count("self.side['b'] -= nd * _C524_COST_B; self.side['d'] -= nd * _C524_COST_D") == 1)

H = 3600000
f0 = min(p['fund_from'] for p in xv.pairs.values())
NOWP = f0 / 1000 + 6 * 3600 + 600
om._C527_EARN.update(at=1e12)
om._c516_bn_get = lambda base, path, params, tries=3: [
    {'symbol': c + 'USDT', 'fundingTime': params['startTime'] + 60007, 'fundingRate': '0.0001'}
    for c in xv.pairs if ((params['startTime'] + 60000) // H) % 4 == 0]
om._c521_get = lambda path, params, tries=3: [{'time': t, 'close': 0.02} for t in range(params['start'], params['end'] + 1, 3600)]
xv.prods = {c: dict(sym=p['d_sym'], cv=p['cv'], iv=4 * 3600, taker=0.0005) for c, p in xv.pairs.items()}
bot.c527p = om.C527Pending(bot)
bot.c527p.tick(now=NOWP)
st = xv.status()
ok("the funding settled since the run, per pair, on the cross-venue panel (it read 'funding +$0.00' beside the total's +$0.79)",
   st['pending'] is not None and set(st['pending']['by']) == set(xv.pairs)
   and abs(sum(st['pending']['by'].values()) - st['pending']['total']) < 1e-3 and st['pending']['total'] != 0, str(st['pending'])[:200])
ok("  and the carry panel gets its own figure", 'pending' in bot.c490.status())

print("\n3. THE SCREENS AND THE LOG")
ok("the boot banner says the month figure is realised and that the guard counts marked equity",
   'realised (the guard counts MARKED equity once prices load)' in SRC)
ok("the boot description gives the Savings rate as Binance's own, read every 6 h", "idle cash -> Savings at Binance's own rate (read every 6 h; " in SRC)
pf.session_start_equity = cash
pf.positions = om.PositionsManager()
e.open0 = 0.5
bot._c482_risk_guard = lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                'day_cap': 25.0, 'day_used': 0.0, 'halt': ''}
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
bot.c489 = om.C489Shadow(bot); bot.c501k = om.C501Allostatic(bot); bot.c510t = om.C510Tournament(bot)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
de.refresh_products = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv, c527p=bot.c527p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
xv.bot = de.bot = fbot
de.guard()
port = socket.socket(); port.bind(('127.0.0.1', 0)); P_ = port.getsockname()[1]; port.close()
om.RemoteControl(fbot, port=P_).start(); time.sleep(0.6)
import urllib.request
api = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{P_}/api/status?t={TOKEN}', timeout=20).read())
exp_s = round(e.live_equity() - (cash + 0.5), 2)
ok("the API's session figure is MARKED (the log's SESSION row): marked now - (realised start + open P&L carried in)",
   api.get('session_marked') is not None and abs(api['session_marked'] - exp_s) < 0.011, f"{api.get('session_marked')} vs {exp_s}")
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{P_}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        T = {k: pg.inner_text('#' + k) for k in ('running', 'alltotal', 'xvenue', 'delta', 'eqs', 'carry')}
        br.close()
    ok("what is running: YOUR PLAN named, and the cross-venue ledger listed (it ran but was missing)",
       'YOUR PLAN' in T['running'] and 'Same book on Delta India + Delta vs Binance funding gap' in T['running']
       and 'Delta vs Binance funding $500' in T['running'], T['running'][:400])
    ok("all accounts: the plan is the only total; experiments listed apart, never added up (no $2,000 figure)",
       'every paper account' not in T['alltotal'] and 'never added up' in T['alltotal'] and '$2' not in T['alltotal'].split('experiments')[0][:120],
       T['alltotal'][:300])
    ok("the equity tile: 'this run' is the marked figure (the log's SESSION), not realised",
       ('this run ' + ('+' if exp_s >= 0 else '-') + f"${abs(exp_s):.2f}") in T['eqs'], T['eqs'])
    ok("the cross-venue panel: booked and settled-since funding, each venue's side and leverage",
       'settled since (booked at the next run)' in T['xvenue'] and 'Delta side' in T['xvenue'] and 'Binance side' in T['xvenue'],
       T['xvenue'][:400])
    ok("the Delta panel: its own month guard", 'its own month guard (C529)' in T['delta'], T['delta'][-300:])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)

rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line))
rep.status(fbot)
ok("the log's status block: a PLAN row (the plan and after tax), no 'all 6 accounts'",
   any(r.strip().startswith('PLAN') for r in rows) and not any('all 6 accounts' in r for r in rows), '\n'.join(r for r in rows if 'PLAN' in r))
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
