#!/usr/bin/env python3
"""C501: three paper ledgers -- the spot pot (S1), idle cash in Savings (F2),
the allostatic shadow of the book (K4 / F1). None may touch the account.

1. PARITY: _c501_s1_targets is the pre-registered S1 rule, built independently
   from the research library; _c488_combine_ewma is the research's own
   combine_ewma (extracted from research/omega_c500_research.py).
2. THE SPOT POT: fills at the spot ask/bid with a 0.08% fee, only targets of
   $6+, never above 100% invested, never a negative cash balance, sells before
   buys, a coin with no spot pair is reported and skipped, a coin whose trend
   turns is sold, the cash earns Savings, it survives a restart.
3. SAVINGS: reserve = margin + dial x equity + 5%; interest = idle x APR x
   time; the account's equity is untouched; it survives a restart.
4. K4: scored exactly as yesterday's weights x today's returns - funding -
   0.08% of turnover, for both books alike; it differs from the running book
   on clustered volatility; NaN funding (C499) passes through.
5. THE REBALANCE: it caches its matrices for the spot pot, hands them to K4,
   and trades exactly what it traded without C501.
6. THE PAGE (Chromium): the spot pot, Savings and K4 lines render; no JS errors.
"""
import os, sys, io, ast, json, math, time, types, socket, glob, logging, contextlib, importlib.util, tempfile, shutil
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c501_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c501-test-token-0123456789abcdef'
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


print("=" * 66); print("C501: THE SPOT POT, IDLE CASH IN SAVINGS, THE ALLOSTATIC SHADOW"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om501')
R = load(os.path.join(REPO, 'research', 'omega_c488_research.py'), 'r501')
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
import warnings; warnings.simplefilter('ignore')


def market(n=430, k=40, seed=11):
    """synthetic daily market with listings, wandering trends and volatility clusters"""
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 20000) * 86400000
    close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
    vol = 0.02 + 0.03 * (np.sin(np.arange(n) / 23.0) > 0.4)               # calm and stormy spells
    for j in range(k):
        a = int(g.integers(0, 120))
        drift = g.normal(0, 0.004, size=n).cumsum() * 0.02
        ret = drift + g.normal(0, 1, size=n) * vol
        close[a:, j] = 10 ** g.uniform(-2, 3) * np.exp(np.cumsum(ret))[a:]
        qv[a:, j] = np.exp(g.normal(16 - 0.04 * j, 0.8, size=n - a))
        fund[a:, j] = g.normal(0.0001, 0.0002, size=n - a) * 3
    return T, close, qv, fund


T, close, qv, fund = market()
keep = [f"C{j:02d}/USDT:USDT" for j in range(close.shape[1])]

# ─────────────────────────────────────────────────────────────────────────────
print("\n1. PARITY")
R.TOPN = 20
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv); sc = np.nan_to_num(R.vol_scale(sd))
s_ = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
W1 = R.banded(np.where(elig, np.maximum(s_, 0.0) * sc / 20, 0.0))
u = R.pnl(W1, r, np.zeros_like(fund), 1, cost=0.0010)[0]
L = np.zeros(len(T))
for i in range(60, len(T)):
    v = u[i - 60:i].std() * math.sqrt(365); L[i] = 0.20 / v if v > 0 else 0.0
Wr = W1 * L[:, None]; gg = np.abs(Wr).sum(1); Wr = Wr * np.where(gg > 1, 1 / np.maximum(gg, 1e-12), 1.0)[:, None]
wlast, Wb = om._c501_s1_targets(T, close, qv, 20)
ok("S1: the bot's weights are the pre-registered rule, row for row (research library, built independently)",
   np.allclose(Wb, Wr, atol=1e-12) and np.array_equal(wlast, Wb[-1]),
   f"{int((wlast > 0).sum())} coins today, invested {100 * wlast.sum():.0f}%")
ok("  long or flat, never above 100% invested, every weight >= 0",
   (Wb >= -1e-15).all() and (np.abs(Wb).sum(1) <= 1 + 1e-9).all())
src500 = open(os.path.join(REPO, 'research', 'omega_c500_research.py')).read()
fn = [n for n in ast.parse(src500).body if isinstance(n, ast.FunctionDef) and n.name == 'combine_ewma'][0]
ns = dict(np=np, math=math, R=R)
r2, Wsl, _ = om._c488_sleeves(T, close, qv, fund, 20)
parts = {k: Wsl[k] for k in ('C1', 'C2', 'C3')}
ns.update(r=r2, fund=fund)
exec(compile(ast.Module(body=[fn], type_ignores=[]), 'c500', 'exec'), ns)
Kr = ns['combine_ewma'](parts)
Kb = om._c488_combine_ewma(parts, r2, fund, 1)
ok("K4: _c488_combine_ewma is the research's own combine_ewma (extracted from omega_c500_research.py)",
   np.allclose(Kb, Kr, atol=1e-12, equal_nan=True), f"gross today {np.abs(Kb[-1]).sum():.3f}")
base = om._c488_targets(T, close, qv, fund, 20, 0.20)[0]
ok("  and it sizes differently from the running 60-day window on clustered volatility",
   not np.allclose(Kb[-1], base), f"K4 gross {np.abs(Kb[-1]).sum():.3f} vs {np.abs(base).sum():.3f}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. THE SPOT POT")
cfg = om.Config(); cfg.PAPER_MODE = True
pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 250.0
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 250.0})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
today = dt.datetime.utcnow().strftime('%Y-%m-%d')
e._last_M = (today, 20, (T, keep, close, qv, fund))
px = {k.replace('/USDT:USDT', 'USDT'): float(close[-1, j]) for j, k in enumerate(keep)}
BK = {s: (p * 0.999, p * 1.001) for s, p in px.items()}
nospot = next(k for j, k in enumerate(keep) if wlast[j] * 250 >= 6)          # one target coin with no spot pair
del BK[nospot.replace('/USDT:USDT', 'USDT')]
sp = om.C501Spot(bot)
sp.book = lambda force=False: (setattr(sp, 'bk', BK) or BK)
sp.bk = BK
n1 = sp.run()
eq1 = sp.equity()
want = {k.replace('/USDT:USDT', 'USDT'): wlast[j] * 250 for j, k in enumerate(keep)
        if wlast[j] * 250 >= 6 and k != nospot}
buys = sum(p['qty'] * p['avg'] for p in sp.pos.values())
ok("the first run buys every $6+ target that has a spot pair, at the ask",
   set(sp.pos) == set(want) and all(abs(p['avg'] - BK[s][1]) < 1e-12 for s, p in sp.pos.items()), f"{len(sp.pos)} held, {n1} trades")
ok("  0.08% fees, the cash never negative, never above 100% invested",
   abs(sp.fees - 0.0008 * buys) < 1e-9 and sp.cash >= 0 and buys <= 250.0, f"fees ${sp.fees:.4f}, cash ${sp.cash:.2f}")
ok("  the equity is cash + holdings at mid: $250 less fees and half the spread",
   abs(eq1 - (250.0 - sp.fees - sum(p['qty'] * (BK[s][1] - (BK[s][0] + BK[s][1]) / 2) for s, p in sp.pos.items()))) < 1e-6,
   f"${eq1:.4f}")
ok("  a target with no spot pair is skipped and reported", nospot.split('/')[0] in sp.info.get('no_spot', []), str(sp.info))
# a day later: one held coin collapses (its trend turns), prices otherwise the same
held = sorted(sp.pos, key=lambda s: -sp.pos[s]['qty'] * sp.mid(s))[0]
j = keep.index(held.replace('USDT', '/USDT:USDT'))
close2 = close.copy(); close2[-1, j] = np.nanmin(close[:, j]) * 0.5
T2 = T
e._last_M = (today, 20, (T2, keep, close2, qv, fund))
BK[held] = (BK[held][0] * 0.5, BK[held][1] * 0.5)
sp.last_run = '2000-01-01'; cash0 = sp.cash
sp.run()
ok("the next run sells a coin whose trend turned (sells come first), and books the day's return",
   held not in sp.pos and sp.closed and sp.closed[-1]['coin'] == held[:-4] and len(sp.daily) == 1 and sp.cash > cash0,
   f"closed {sp.closed[-1] if sp.closed else None}, day {list(sp.daily.values())}")
c0 = sp.cash; sp._last_ts = time.time() - 3600; sp._tick_at = 0.0; sp.last_run = today
sp.tick(now=time.time())
exp = c0 * 0.0763 * 3600 / (365 * 86400)
ok("the cash earns Savings at 7.63% (one hour)", abs((sp.cash - c0) - exp) < exp * 0.01 + 1e-9,
   f"+${sp.cash - c0:.6f} vs ${exp:.6f}")
sp.save(); sp2 = om.C501Spot(bot)
ok("it survives a restart", abs(sp2.cash - sp.cash) < 1e-9 and set(sp2.pos) == set(sp.pos) and sp2.last_run == today)
st = sp.status()
ok("status: paper, $, invested %, positions, the record", st['mode'] == 'paper' and st['start_equity'] == 250.0
   and 0 <= st['invested_pct'] <= 100 and len(st['positions']) == len(sp.pos), f"{st['usd']} {st['invested_pct']}%")
ok("it never touches the account", pf.equity == 250.0 and not e.book)

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. IDLE CASH IN SAVINGS")
cfg.C380_MAX_MONTHLY_DD_PCT = 15.0                                      # the operator's dial (Config's default is 20)
e.live_equity = lambda: 250.0
pf.get_locked_margin = lambda: 25.0
sv = om.C501Savings(bot)
eqm, lk, res, idle = sv.measure()
ok("reserve = margin $25 + dial 15% x $250 + 5% x $250 = $75, idle $175", abs(res - 75.0) < 1e-9 and abs(idle - 175.0) < 1e-9)
t0 = time.time(); sv.tick(now=t0); sv._tick_at = 0.0; sv.tick(now=t0 + 3600)
exp = 175.0 * 0.0763 * 3600 / (365 * 86400)
ok("one hour of idle cash earns idle x 7.63% / 8760", abs(sv.interest - exp) < 1e-12, f"+${sv.interest:.6f}")
cfg.C380_MAX_MONTHLY_DD_PCT = 20.0
ok("  self-adjusting: dial 20% keeps $12.50 more in futures", abs(sv.measure()[3] - 162.5) < 1e-9)
cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
ok("  the account's equity is untouched", pf.equity == 250.0)
sv.save(); sv2 = om.C501Savings(bot)
ok("  it survives a restart", abs(sv2.interest - sv.interest) < 1e-12 and sv2.since == sv.since)

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. THE ALLOSTATIC SHADOW (K4)")
k4 = om.C501Allostatic(bot)
n0 = len(T) - 1
fnan = fund.copy(); fnan[:50] = np.nan                                  # C499: unknown funding is NaN
T1, c1, q1, f1 = T[:n0], close[:n0], qv[:n0], fnan[:n0]
wb1 = om._c488_targets(T1, c1, q1, f1, 20, 0.20)[0]
k4.observe(T1, keep, c1, q1, f1, 20, 0.20, 3.0, 250.0, wb1)
wb_prev, wk_prev, pend = dict(k4.wb), dict(k4.wk), list(k4.pend)
ok("the first observation holds both books and charges entry costs; nothing scored yet",
   k4.wb and k4.wk and k4.daily == [] and pend[0] > 0 and pend[1] > 0)
wb2 = om._c488_targets(T, close, qv, fnan, 20, 0.20)[0]
k4.observe(T, keep, close, qv, fnan, 20, 0.20, 3.0, 250.0, wb2)
rr = R.returns(close)
man = lambda w, pc: sum(x * float(np.nan_to_num(rr[-1, keep.index(s)])) - x * float(np.nan_to_num(fnan[-1, keep.index(s)]))
                        for s, x in w.items()) - pc
ok("a day later: each book's return = yesterday's weights x today's returns - funding - entry cost",
   len(k4.daily) == 1 and abs(k4.daily[0][1] - man(wb_prev, pend[0])) < 1e-6 and abs(k4.daily[0][2] - man(wk_prev, pend[1])) < 1e-6,
   str(k4.daily[0]))
st = k4.status()
ok("status: days, both books' return, vol, drawdown, gross", st['days'] == 1 and st['mode'] == 'paper'
   and 'gross' in st['k4'] and 'maxdd' in st['base'], f"K4 {st['k4']['gross']}x vs {st['base']['gross']}x")
ok("a log line says what it compared", any('C501 allostatic shadow' in m for m in LOG))

# ─────────────────────────────────────────────────────────────────────────────
print("\n5. THE REBALANCE")
class FakeCCXT:
    def __init__(s): s.markets = {}
class FakeEx:
    def __init__(s, ref): s.exchange = FakeCCXT(); s.markets = s.exchange.markets; s.ref = ref; s.orders = []
    def place_order(s, sym, side, qty, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        m = s.ref[0].marks[sym]; s.orders.append((sym, side, round(qty, 10)))
        return {'id': 'p', 'status': 'closed', 'price': m['ask'] if side == 'buy' else m['bid'], 'filled': qty}
    def c487_settle(s, sym, o, side, price, size, wait): return float(o['filled']), float(o['price']), 'filled'
    def get_current_price(s, sym): return None
def rebalance(with_k4):
    c = om.Config(); c.PAPER_MODE = True; c.C380_MAX_MONTHLY_DD_PCT = 15.0
    p = om.Portfolio(c); p.equity = p.available_balance = 900.0            # under $1000: the book is top 20, like the pot
    ref = [None]
    b = types.SimpleNamespace(cfg=c, portfolio=p, exchange=FakeEx(ref), _c462_state_settled=True,
                              _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 900.0})
    en = om.C488Engine(b); en.reset(); ref[0] = en; p._c488 = en; b.c488 = en
    if with_k4:
        b.c501k = om.C501Allostatic(b); b.c501k.reset()
    for j, s in enumerate(keep):
        x = float(close[-1, j]) if not np.isnan(close[-1, j]) else 1.0
        en.marks[s] = dict(bid=x * 0.9999, ask=x * 1.0001, last=x, fr=0.0001, vol=float(np.nan_to_num(qv[-1, j])))
        b.exchange.markets[s] = dict(precision={'amount': 10 ** np.floor(np.log10(max(0.5 / x, 1e-9)))}, limits={'amount': {'min': 0.0}})
    en._marks_at = time.time() + 1e6
    en.refresh_marks = lambda force=False: True; en.refresh_rules = lambda force=False: True
    en.candidates = lambda n: keep; en.matrices = lambda s: (T, keep, close, qv, fund)
    en.rebalance('test')
    return b, en
b0, e0 = rebalance(False); b1, e1 = rebalance(True)
ok("the rebalance caches its matrices for the spot pot", e1.cached_matrices(20) is not None and e1.cached_matrices(40) is None)
ok("  hands them to K4, which now holds both books", bool(b1.c501k.wb) and bool(b1.c501k.wk))
ok("  and trades exactly what it traded without C501", b0.exchange.orders == b1.exchange.orders and len(b0.exchange.orders) > 3,
   f"{len(b1.exchange.orders)} orders")

# ─────────────────────────────────────────────────────────────────────────────
print("\n6. THE PAGE (Chromium)")
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
pf.session_start_equity = 250.0; pf.positions = om.PositionsManager()
pf.get_live_equity = lambda *a: pf.equity
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=sp, c501v=sv, c501k=k4,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 250.0, 'month_budget': 37.5,
                                                       'month_used': 0.0, 'day_cap': 9.0, 'day_used': 0.0, 'halt': ''})
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        spot_t, sav_t, book_t = pg.inner_text('#spotpot'), pg.inner_text('#savings'), pg.inner_text('#book')
        b.close()
    ok("the spot pot panel shows the pot, its holdings and the Savings rate",
       'paper pot of $250.00' in spot_t and '% invested' in spot_t and 'Savings 7.63%' in spot_t, spot_t.replace('\n', ' | ')[:200])
    ok("the Savings panel shows idle cash, the reserve and what it earned", 'idle $' in sav_t and 'reserve $' in sav_t
       and '/month' in sav_t, sav_t.replace('\n', ' | ')[:200])
    ok("the book panel carries the allostatic shadow line", 'allostatic shadow (K4, paper)' in book_t, book_t.replace('\n', ' | ')[-160:])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)

src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
c501_src = src[src.index('def _c501_s1_targets'):src.index('\nclass TradingBot:')]
import re
ok("isolation: no order, no margin move, no write to the account anywhere in C501's code",
   'place_order' not in c501_src and 'create_order' not in c501_src and 'release_margin' not in c501_src
   and 'trade_to' not in c501_src and not re.search(r'portfolio\.\w+\s*[-+*/]?=(?!=)', c501_src)
   and [l.strip() for l in c501_src.splitlines() if 'portfolio' in l and not l.strip().startswith('#')]
       == ['eng, pf = self.bot.c488, self.bot.portfolio'])
ok("version C501", om._OMEGA_VERSION == 'C501')
shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
