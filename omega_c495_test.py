#!/usr/bin/env python3
"""C495: what the operator's first C492 screenshots and the server's own logs showed.

1. THE BOOT RISK FRAME: with the portfolio engine on it no longer prints the
   idle scanner's per-trade risk, EDGE, NEED and DAY rows as if they governed
   the money; it prints the BOOK row. The intraday engine's frame is unchanged.
2. THE BOOK'S MONTH GUARD, ON MARKED EQUITY: the month it arrives in keeps
   C482's anchor (nothing jumps mid-month); at a month turn it anchors on
   MARKED equity, so open P&L at midnight on the 1st no longer leaks into the
   new month; it trips on marked losses; it survives a restart; a fresh start
   clears it; status carries it.
3. THE SHADOW: flow coverage is counted the way the model switch counts it
   (coins with a week of flow, and how many Bitget serves at all) instead of
   the minimum over all coins; the model in use survives a restart; an hour
   with fewer than 10 scoreable coins says WHY and is retried, not booked
   blind, until 20 minutes past the hour.
4. THE PAGE (Chromium): the equity tile shows the marked value and the book's
   open P&L; the risk tile shows the book guard on marked equity; the shadow
   panel shows Bitget's real flow coverage; no JavaScript errors.
"""
import os, sys, io, json, time, types, socket, glob, logging, contextlib, importlib.util, tempfile, shutil
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c495_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c495-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(m)
    return m


print("=" * 66); print("C495: WHAT THE FIRST C492 SCREENS AND THE SERVER LOGS SHOWED"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om495')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False

# ─────────────────────────────────────────────────────────────────────────────
print("\n1. THE BOOT RISK FRAME")
def frame(engine):
    cfg = om.Config(); cfg.C488_ENGINE = engine; om._c467_cfg_ref[0] = cfg
    rep = om._C462Report(os.path.join(BASE, f'r_{engine}.log')); rows = []
    rep._emit = lambda line: rows.append(str(line))
    rep.risk_frame({'equity': 252.22, 'per_trade_pct': 0.341, 'cap_pct': 3.7, 'dd_pct': 15.0}, edge=0.0474,
                   markets=805, wr='44W 95L realised', payoff=2.10,
                   guard={'pct': 15.0, 'month_budget': 37.92, 'month_used': 0.59, 'day_cap': 9.34})
    return '\n'.join(rows)
fb, fi = frame('portfolio'), frame('intraday')
ok("portfolio engine: a BOOK row, the month used marked 'realised', and no per-trade RISK / EDGE / NEED / DAY rows",
   'BOOK' in fb and 'month guard on MARKED equity' in fb and 'realised' in fb
   and not any(k in fb for k in ('EDGE', 'NEED', '/trade', 'DAY ')), fb.replace('\n', ' | ')[-200:])
ok("intraday engine: the frame is exactly as before (DAY, RISK, EDGE, NEED rows; no BOOK row)",
   all(k in fi for k in ('DAY', 'RISK', 'EDGE', 'NEED', '/trade')) and 'BOOK' not in fi)

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. THE BOOK'S MONTH GUARD, ON MARKED EQUITY")
class FakeEx:
    def __init__(s):
        s.exchange = types.SimpleNamespace(markets={'ETH/USDT:USDT': dict(precision={'amount': 0.01}, limits={'amount': {'min': 0.01}})})
        s.markets = s.exchange.markets
    def get_current_price(s, sym):
        return None
def mkbot(month_eq0=1000.0, pct=15.0):
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = pct
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 1000.0
    g = {'pct': pct, 'month_eq0': month_eq0}
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: dict(g))
    e = om.C488Engine(bot); e.reset(); pf._c488 = e; bot.c488 = e
    e.marks = {'ETH/USDT:USDT': dict(bid=1999.0, ask=2001.0, last=2000.0, fr=0.0001, vol=9e9)}
    e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
    return bot, e, g
bot, e, g = mkbot(month_eq0=1010.0)
r = e.guard()
key = dt.datetime.now().strftime('%Y-%m')
ok("the month C495 arrives in keeps C482's (realised) anchor -- nothing jumps mid-month",
   r == '' and e.month == {'key': key, 'eq0': 1010.0} and LOG and 'carried from C482' in LOG[-1], str(e.month))
e.book['ETH/USDT:USDT'] = dict(qty=1.0, avg=2100.0, fees=0.0, funding=0.0, realized=0.0, opened=time.time())
ok("  its view is marked: $10 realised down plus a $100 open loss = $110.xx used",
   (e.guard() or True) and abs(e._guard_view['used'] - (1010.0 - e.live_equity())) < 1e-6 and e._guard_view['used'] > 110,
   str(e._guard_view))
e.month = {'key': '2000-01', 'eq0': 1000.0}; LOG.clear()
e.guard()
ok("a month turn anchors on MARKED equity (the open -$101 is last month's, not the new month's)",
   e.month['key'] == key and abs(e.month['eq0'] - round(e.live_equity(), 4)) < 1e-6 and e._guard_view['used'] == 0.0
   and 'marked' in LOG[-1], f"{e.month}, live {e.live_equity():.2f}")
e.marks['ETH/USDT:USDT'].update(bid=1839.0, ask=1841.0)
ok("it trips on a marked loss past the dial (15% of the anchor)", e.guard() == 'month:' + key, str(e._guard_view))
e.marks['ETH/USDT:USDT'].update(bid=1999.0, ask=2001.0)
e.save(); e2 = om.C488Engine(bot)
ok("the anchor survives a restart", e2.month == e.month)
st = e.status()
ok("status carries the marked equity and the guard's view", st.get('marked') == round(e.live_equity(), 2)
   and st['guard'].get('budget') == round(e.month['eq0'] * 0.15, 2) and 'used' in st['guard'], str(st['guard']))
e.reset()
ok("a fresh start clears it (the next check anchors on the new account)", e.month == {})
g['pct'] = 0.0
ok("dial 0 is still 'dial'", e.guard() == 'dial')

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. THE SHADOW")
def mkshadow():
    cfg = om.Config(); cfg.PAPER_MODE = True
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 1000.0
    c488 = types.SimpleNamespace(marks={}, refresh_marks=lambda force=False: True, _is_crypto=lambda s: True)
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=c488, _c462_state_settled=True)
    sh = om.C489Shadow(bot); sh.reset()
    return bot, sh
bot, sh = mkshadow()
sh.syms = [f'S{j:02d}USDT' for j in range(40)]
h = int(time.time() * 1000) // 3600000 * 3600000
for j, s in enumerate(sh.syms):
    if j < 12:
        sh.flow[s] = {h - k * 3600000: 0.5 for k in range(1, 160)}      # a week of flow
    elif j < 16:
        sh.flow[s] = {h - k * 3600000: 0.5 for k in range(1, 20)}       # served, not a week yet
    elif j == 16:
        sh.flow[s] = {}                                                 # a coin new to the top 40
st = sh.status()
ok("flow coverage is counted as the switch counts it: 12 coins with a week, 16 served by Bitget -- not the minimum (0)",
   st['flow_week'] == 12 and st['flow_served'] == 16 and st['warming'] is True, f"week {st['flow_week']}, served {st['flow_served']}")
sh.model_used = 'warm-up (14, no flow)'; sh.save(); sh2 = om.C489Shadow(bot)
ok("the model in use survives a restart (the panel read 'model pending' after every restart)", sh2.model_used == 'warm-up (14, no flow)')

class _Clock(dt.datetime):
    M = 5
    @classmethod
    def utcnow(cls):
        n = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        return n.replace(minute=cls.M, second=0)
bot, sh = mkshadow()
sh.refresh = lambda: None
sh._diag = 'last-hour candle 40/40, BTC MISSING, blank: resid4 40, btc4 40'
sh.predict = lambda now_h: (np.full(40, np.nan), False, np.full(40, np.nan), 0)
sh.syms = [f'S{j:02d}USDT' for j in range(40)]
real_dt = om.datetime; om.datetime = _Clock
try:
    LOG.clear(); sh._tick_at = 0; sh.tick()
    ok("an hour with 0 scoreable coins at :05 is NOT booked; the log says why and when it retries",
       sh.last_hour == 0 and any('only 0 coins scoreable' in m and 'BTC MISSING' in m and 'retrying in 2 min' in m for m in LOG),
       (LOG[-1] if LOG else '')[:160])
    ok("  and the next try waits about 2 minutes (not 30 s)", sh._tick_at - time.time() > 60)
    _Clock.M = 21; LOG.clear(); sh._tick_at = 0; sh.tick()
    ok("after 20 minutes past the hour it books anyway, and says with how few",
       sh.last_hour > 0 and any('booked with 0 coins scoreable after 20 min' in m for m in LOG))
finally:
    om.datetime = real_dt
print("\n3b. THE ROOT CAUSE: A FEATURE THAT IS THE SAME FOR EVERY COIN")
R489 = load(os.path.join(REPO, 'research', 'omega_c489_research.py'), 'r489_495')
k = 40; U1 = np.ones((3, k), bool)
same = np.full((3, k), 0.8123456789)                       # btc4: BTC's own move, copied to every coin
g = np.random.default_rng(1).normal(size=(3, k))
inf = g.copy(); inf[:, 7] = -np.inf                          # one coin's funding z at -inf (RARE, 25 Sep)
Zb = om._c489_xs_standardise({'btc4': same, 'fundz': inf, 'z_r1': g}, U1)
ok("a feature identical across coins standardises to 0 for every coin (it was 0/0 = blank for ALL coins)",
   np.all(Zb['btc4'] == 0.0), f"{Zb['btc4'][0, :3]}")
ok("one coin at -inf blanks only that coin (it made the mean infinite and blanked all 40)",
   np.isnan(Zb['fundz'][:, 7]).all() and (~np.isnan(np.delete(Zb['fundz'], 7, axis=1))).all())
ok("ordinary features are unchanged", np.allclose(Zb['z_r1'], np.clip((g - g.mean(1, keepdims=True)) / g.std(1, keepdims=True), -5, 5)))
Zr = R489.xs_standardise({'btc4': same, 'fundz': inf, 'z_r1': g}, U1)
ok("the research engine has the identical fix (parity kept)",
   all(np.array_equal(Zb[f], Zr[f], equal_nan=True) for f in Zb))
ok("the fix says what it fixes, in the function", 'copied to all of them' in src and 'An infinite value is missing for that' in src)
ok("predict() leaves a diagnosis naming the last-hour candles, BTC and the blank features",
   "BTC {'ok' if U[-1, b] else 'MISSING'}" in src and 'blank: ' in src)

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. THE PAGE (Chromium)")
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
bot, e, g = mkbot(month_eq0=1000.0)
e.book['ETH/USDT:USDT'] = dict(qty=0.5, avg=2100.0, fees=0.0, funding=0.0, realized=0.0, opened=time.time())
e.last_rebal = '2026-09-26'; e.info = {'topn': 20}; e.guard()
pf = bot.portfolio; pf.session_start_equity = 1000.0; pf.positions = om.PositionsManager()
pf.get_live_equity = lambda *a: pf.equity + e.unrealized()
bot2, sh = mkshadow(); sh.syms = [f'S{j:02d}USDT' for j in range(40)]
for j, s in enumerate(sh.syms[:15]):
    sh.flow[s] = {int(time.time() * 1000) // 3600000 * 3600000 - k * 3600000: 0.5 for k in range(1, 30)}
fbot = types.SimpleNamespace(cfg=bot.cfg, portfolio=pf, c488=e, c489=sh,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0, 'month_budget': 150.0,
                                                       'month_used': 0.0, 'day_cap': 37.5, 'day_used': 0.0, 'halt': ''})
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        eqs, days, shadow = pg.inner_text('#eqs'), pg.inner_text('#days'), pg.inner_text('#shadow')
        posn = pg.inner_text('#pos')
        b.close()
    mk = f"{e.live_equity():,.2f}"
    ok("the equity tile shows the marked value and the book's open P&L", 'marked $' in eqs and 'book open' in eqs and mk.split('.')[0] in eqs,
       eqs.replace('\n', ' | '))
    ok("the risk tile shows the book guard on marked equity (no day limit while the book runs)",
       'on marked equity' in days and 'book guard' in days and 'today' not in days, days)
    ok("the shadow panel shows Bitget's real flow coverage, not '(now 0h)'",
       'Bitget serves flow for 15 of 40' in shadow and 'now 0h' not in shadow, shadow.replace('\n', ' | ')[:200])
    ok("the Open positions panel no longer says 'none -- flat' above a book that holds positions",
       'portfolio book holds 1 position' in posn and 'flat' not in posn, posn)
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)

shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
