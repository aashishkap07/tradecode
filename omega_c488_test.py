#!/usr/bin/env python3
"""C488: the medium-term portfolio engine.

1. PARITY: the bot's _c488_* functions return exactly what the research engine
   (research/omega_c488_research.py) returns on the same data -- universe,
   every sleeve, the combination, today's targets -- at 20 and 40 coins. What
   trades is what was measured.
2. LEDGER: opens, adds, reduces, flips and closes against the real Portfolio:
   average price, realised P&L, fees, margin, and equity moves by exactly
   realised - fees + funding; available + locked == equity throughout; the
   open book shows up in get_unrealized_pnl.
3. FUNDING (paper): a long pays a positive rate, a short receives it, once per
   settlement, and the next settlement moves on by the contract's interval.
4. REBALANCE: reaches the targets to within one quantity step, holds nothing
   under the minimum, sends reductions before increases, and a second pass on
   the same data trades nothing.
5. GUARD AND MODES: a month loss past the dial flattens and halts until next
   month; dial 0 flattens; switching to 'intraday' closes the book; live mode
   refuses to trade without C488_LIVE_OK; a pause stops rebalancing only.
6. WIRING: the intraday scanner stands down while the engine runs (Force scan
   included); the engine ticks before the pause checks; a fresh start empties
   the book; the book survives a restart.
7. THE PAGE (Chromium): /api/status carries the book and the panel draws it.
8. THE PRE-REGISTRATION was committed once, before the engine, and never edited.
"""
import os, sys, io, re, ast, json, time, types, socket, glob, contextlib, importlib.util, subprocess, tempfile, shutil, datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c488_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c488-test-token-0123456789abcdef'
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


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd=REPO).stdout


print("=" * 66); print("C488: THE MEDIUM-TERM PORTFOLIO ENGINE"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om488')
R = load(os.path.join(REPO, 'research', 'omega_c488_research.py'), 'r488')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()


# ─── synthetic market: listings, delistings, regimes, funding ────────────────
def market(n=430, k=60, seed=7):
    g = np.random.default_rng(seed)
    T = (np.arange(n) + 19000) * 86400000                      # UTC days
    close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
    for j in range(k):
        a = int(g.integers(0, 150)); b = n if g.random() < 0.85 else int(g.integers(a + 120, n))
        drift = g.normal(0, 0.004, size=n).cumsum() * 0.02     # slowly wandering trend
        ret = drift + g.normal(0, 0.035, size=n)
        px = 10 ** g.uniform(-3, 4) * np.exp(np.cumsum(ret))
        close[a:b, j] = px[a:b]
        qv[a:b, j] = np.exp(g.normal(16 - 0.04 * j, 0.8, size=b - a))
        fund[a:b, j] = g.normal(0.0001, 0.0002, size=b - a) * 3
    return T, close, qv, fund


print("\n1. PARITY WITH THE RESEARCH ENGINE")
T, close, qv, fund = market()
with np.errstate(all='ignore'):
    import warnings; warnings.simplefilter('ignore')
    for topn in (20, 40):
        R.TOPN = topn
        e_r = R.universe(close, qv); e_b = om._c488_universe(close, qv, topn)
        r_r, W_r, _ = R.crypto_sleeves(T, close, qv, fund)
        r_b, W_b, _ = om._c488_sleeves(T, close, qv, fund, topn)
        same_w = all(np.allclose(W_r[k], W_b[k], atol=0, rtol=0, equal_nan=True) for k in ('C1', 'C2', 'C3'))
        Wc_r = R.combine({k: W_r[k] for k in ('C1', 'C2', 'C3')}, r_r, fund, 1)
        Wc_b = om._c488_combine({k: W_b[k] for k in ('C1', 'C2', 'C3')}, r_b, fund, 1)
        last, sl, _ = om._c488_targets(T, close, qv, fund, topn, 0.20)
        ok(f"top {topn}: universe, all three sleeves, the combination and today's row are IDENTICAL",
           np.array_equal(e_r, e_b) and same_w and np.array_equal(Wc_r, Wc_b) and np.array_equal(last, Wc_r[-1]),
           f"{int(e_b[-1].sum())} coins today, {int((np.abs(last) > 0).sum())} weights, gross {np.abs(last).sum():.3f}")
    ok("the targets actually hold positions both ways", (last > 0).sum() > 2 and (last < 0).sum() > 2)
    ok("the vol target scales the book linearly (dial doubles -> weights double, under the cap)",
       np.allclose(om._c488_targets(T, close, qv, fund, 40, 0.10)[0] * 2, om._c488_targets(T, close, qv, fund, 40, 0.20)[0]))


# ─── a small bot around the real Portfolio ───────────────────────────────────
class FakeCCXT:
    def __init__(self):
        self.markets = {'BTC/USDT:USDT': dict(precision={'amount': 0.0001}, limits={'amount': {'min': 0.0001}}),
                        'ETH/USDT:USDT': dict(precision={'amount': 0.01}, limits={'amount': {'min': 0.01}})}


class FakeEx:
    def __init__(self, eng_ref):
        self.exchange = FakeCCXT(); self.markets = self.exchange.markets; self.eng = eng_ref; self.orders = []

    def place_order(self, sym, side, qty, lev, order_type='market', price=None, reduce_only=False, post_only=None):
        m = self.eng[0].marks[sym]
        px = m['ask'] if side == 'buy' else m['bid']
        self.orders.append((sym, side, round(qty, 10), reduce_only))
        return {'id': 'p', 'status': 'closed', 'price': px, 'filled': qty}

    def c487_settle(self, sym, o, side, price, size, wait):
        return float(o['filled']), float(o['price']), 'filled'

    def get_current_price(self, sym):
        return None


def mkbot(guard=None, paper=True):
    cfg = om.Config(); cfg.PAPER_MODE = paper; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 1000.0
    ref = [None]
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(ref), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto',
                                _c482_risk_guard=guard or (lambda: {'pct': 15.0, 'month_eq0': 1000.0}))
    e = om.C488Engine(bot); e.reset(); ref[0] = e
    pf._c488 = e
    e.marks = {'BTC/USDT:USDT': dict(bid=49999.0, ask=50001.0, last=50000.0, fr=0.0001, vol=9e9),
               'ETH/USDT:USDT': dict(bid=1999.0, ask=2001.0, last=2000.0, fr=0.0001, vol=5e9)}
    e._marks_at = time.time() + 1e6
    e.refresh_marks = lambda force=False: True   # tests never touch the network
    return bot, e


def inv(pf):
    return abs(pf.available_balance + pf.get_locked_margin() - pf.equity) < 0.011


print("\n2. THE LEDGER")
bot, e = mkbot(); pf = bot.portfolio; B = 'BTC/USDT:USDT'
fee = lambda q, px: q * px * 0.0006
e.trade_to(B, 0.002, 't'); p = e.book[B]
ok("open 0.002 BTC at the ask: avg 50001, equity down by the fee only, margin locked",
   abs(p['avg'] - 50001) < 1e-9 and abs(pf.equity - (1000 - fee(0.002, 50001))) < 1e-9
   and abs(e.locked_margin() - 0.002 * 50001 / 5) < 1e-9 and inv(pf), f"equity {pf.equity:.4f}")
e.marks[B].update(bid=50999.0, ask=51001.0)
e.trade_to(B, 0.003, 't')
ok("add 0.001 at 51001 -> weighted average", abs(e.book[B]['avg'] - (0.002 * 50001 + 0.001 * 51001) / 0.003) < 1e-6 and inv(pf))
avg = e.book[B]['avg']; eq0 = pf.equity
e.marks[B].update(bid=51999.0, ask=52001.0)
e.trade_to(B, 0.001, 't')
ok("reduce to 0.001 at the bid -> realised 0.002 x (51999 - avg), less the fee",
   abs(pf.equity - eq0 - (0.002 * (51999 - avg) - fee(0.002, 51999))) < 1e-9 and inv(pf),
   f"realised {0.002 * (51999 - avg):+.4f}")
e.marks[B].update(bid=49999.0, ask=50001.0)
e.trade_to(B, -0.001, 't')
ok("flip to short 0.001: the long closes (reduce-only), then a short opens at the bid",
   abs(e.book[B]['qty'] + 0.001) < 1e-12 and abs(e.book[B]['avg'] - 49999) < 1e-9
   and [o[3] for o in bot.exchange.orders[-2:]] == [True, False] and inv(pf))
e.marks[B].update(bid=48999.0, ask=49001.0)
ok("the open book is in Portfolio.get_unrealized_pnl (0.001 short, price down $1000)",
   abs(pf.get_unrealized_pnl(bot.exchange) - (-0.001 * (49000 - 49999) - 0.001 * 49000 * 0.0006)) < 0.01,
   f"{pf.get_unrealized_pnl(bot.exchange):+.4f}")
e.trade_to(B, 0.0, 't')
tot_fee = sum(c['fees'] for c in e.closed)
ok("closed: the book is empty, the margin is back, and one whole-idea record per position",
   not e.book and abs(e.locked_margin()) < 1e-12 and len(e.closed) == 2 and inv(pf))
ok("equity moved by exactly realised - fees (to the cent, over five fills)",
   abs((pf.equity - 1000.0) - sum(c['pnl'] for c in e.closed)) < 0.01,
   f"equity {pf.equity - 1000:+.4f} vs records {sum(c['pnl'] for c in e.closed):+.4f}")

print("\n3. FUNDING (paper)")
bot, e = mkbot(); pf = bot.portfolio; E = 'ETH/USDT:USDT'
e.trade_to(E, 0.5, 't'); eq1 = pf.equity
now = int(time.time() * 1000)
e.fund_iv[E] = (8, time.time()); e.fund_next[E] = now - 1
e.accrue_funding()
paid = 0.5 * 2000.0 * 0.0001
ok("a long pays a positive rate once, at the settlement", abs(pf.equity - (eq1 - paid)) < 1e-9
   and abs(e.book[E]['funding'] + paid) < 1e-12, f"-${paid:.4f}")
ok("  and the next settlement is one interval (8 h) later", e.fund_next[E] == now - 1 + 8 * 3600000)
e.accrue_funding()
ok("  nothing more until then", abs(pf.equity - (eq1 - paid)) < 1e-9)
e.trade_to(E, -0.5, 't'); eq2 = pf.equity; e.fund_next[E] = int(time.time() * 1000) - 1
e.accrue_funding()
ok("a short RECEIVES a positive rate", abs(pf.equity - (eq2 + 0.5 * 2000.0 * 0.0001)) < 1e-9)

print("\n4. THE REBALANCE")
T, close, qv, fund = market(k=60, seed=11)
syms = [f"C{j:02d}/USDT:USDT" for j in range(close.shape[1])]
bot, e = mkbot(); pf = bot.portfolio
for j, s in enumerate(syms):
    px = float(close[-1, j]) if not np.isnan(close[-1, j]) else 1.0
    e.marks[s] = dict(bid=px * 0.9999, ask=px * 1.0001, last=px, fr=0.0001, vol=float(np.nan_to_num(qv[-1, j])))
    bot.exchange.markets[s] = dict(precision={'amount': 10 ** np.floor(np.log10(max(0.5 / px, 1e-9)))},
                                   limits={'amount': {'min': 0.0}})
e.candidates = lambda n: syms
e.matrices = lambda s: (T, syms, close, qv, fund)
e.rebalance('test')
eq = e.info['equity']
bad = []
for s, pl in e.plan.items():
    q = float((e.book.get(s) or {}).get('qty', 0.0)); px = e.mark(s); st = e._step(s)[0]
    if abs(q - pl['w'] * eq / px) > st * 0.51 + 1e-12:
        bad.append(s)
ok("every target reached to within half a quantity step", not bad and len(e.plan) > 5, f"{len(e.plan)} targets, off: {bad[:3]}")
ok("nothing held under the $6 minimum", all(abs(p['qty']) * e.mark(s) >= 6.0 - 1e-9 for s, p in e.book.items()))
ok("the account still balances after the whole book was built", inv(pf),
   f"available {pf.available_balance:.2f} + locked {pf.get_locked_margin():.2f} vs equity {pf.equity:.2f}")
n0 = len(bot.exchange.orders); e.last_rebal = ''; e.rebalance('again')
ok("a second pass on the same data trades nothing (the 30% band)", len(bot.exchange.orders) == n0 and e.info['n_trades'] == 0)
# shrink half the book, grow the rest: every reduction must come first
bot.exchange.orders.clear()
held = sorted(e.book)
fake = {s: dict(w=(0.0 if i % 2 else 1.6 * e.book[s]['qty'] * e.mark(s) / eq), c1=0, c2=0, c3=0) for i, s in enumerate(held)}
e.matrices = lambda s: (T, syms, close, qv, fund)
orig = om._c488_targets
def fake_targets(T_, close_, qv_, fund_, topn, tv, cap=3.0):
    w = np.array([fake.get(s, {}).get('w', 0.0) for s in syms])
    z = np.zeros(len(syms)); return w, {'C1': z, 'C2': z, 'C3': z}, np.ones(len(syms), bool)
om._c488_targets = fake_targets
try:
    e.last_rebal = ''; e.rebalance('reshape')
finally:
    om._c488_targets = orig
seq = []
for s, side, q, ro in bot.exchange.orders:
    grows = s in fake and fake[s]['w'] != 0 and not ro
    seq.append('grow' if grows else 'shrink')
ok("reductions are sent before increases (they free the margin)", 'grow' in seq and 'shrink' in seq
   and seq.index('grow') > max(i for i, k in enumerate(seq) if k == 'shrink'), ' '.join(x[0] for x in seq))

print("\n5. THE GUARD AND THE MODES")
bot, e = mkbot(guard=lambda: {'pct': 15.0, 'month_eq0': 1200.0})   # down $200 on a $180 budget
e.trade_to('ETH/USDT:USDT', 0.5, 't'); calls = []
e.rebalance = lambda why='': calls.append(why)
e._tick_at = 0; e.tick()
ok("a month loss past the dial flattens the book and halts", not e.book and e.halt.startswith('month:'), e.halt)
e._tick_at = 0; e.tick()
ok("  and no rebalance while halted", not calls)
e.halt = 'month:2000-01'
bot._c482_risk_guard = lambda: {'pct': 15.0, 'month_eq0': 1000.0}
e._tick_at = 0; e.tick()
ok("  a new month clears it and rebuilds the book at once", e.halt == '' and len(calls) == 1)
bot, e = mkbot(guard=lambda: {'pct': 0.0, 'month_eq0': 1000.0})
e.trade_to('ETH/USDT:USDT', 0.5, 't'); e.rebalance = lambda why='': None
e._tick_at = 0; e.tick()
ok("dial at 0% flattens and halts", not e.book and e.halt == 'dial')
bot, e = mkbot(); e.trade_to('ETH/USDT:USDT', 0.5, 't'); bot.cfg.C488_ENGINE = 'intraday'
e._tick_at = 0; e.tick()
ok("switching to 'intraday' closes the engine's book", not e.book)
bot, e = mkbot(paper=False); calls = []; e.rebalance = lambda why='': calls.append(why)
e._tick_at = 0; e.tick()
ok("live mode without C488_LIVE_OK never rebalances", not calls)
bot.cfg.C488_LIVE_OK = True; e._tick_at = 0; e.tick()
ok("  and does once it is set", calls == ['first'])
bot, e = mkbot(); calls = []; e.rebalance = lambda why='': calls.append(why)
e._tick_at = 0; e.tick(can_trade=False)
ok("a pause stops the rebalance", not calls)
e._tick_at = 0; e.tick(can_trade=True)
ok("  and lifting it lets the day's rebalance run", calls == ['first'])
e.last_rebal = dt.datetime.utcnow().strftime('%Y-%m-%d')
ok("one rebalance per UTC day (due() is False once done)", not e.due())

print("\n6. WIRING")
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_run_scan_and_trade')
first = fn.body[0]
ok("the intraday scanner stands down FIRST THING while the engine runs (Force scan too)",
   isinstance(first, ast.If) and 'c488' in ast.get_source_segment(src, first.test) and
   any(isinstance(x, ast.Return) for x in first.body))
i_tick = src.find("self.c488.tick(can_trade=self.mode_mgr.can_trade())")
i_pause = src.find("# 2. Check if paused (NO scanning when paused)")
ok("the engine ticks at the top of the main loop, before the pause check", 0 < i_tick < i_pause)
ok("a fresh start empties the book; OMEGA_ENGINE chooses the engine",
   "bot.c488.reset()" in src and "os.environ.get('OMEGA_ENGINE'" in src)
bot, e = mkbot(); e.trade_to('ETH/USDT:USDT', 0.5, 't'); e.last_rebal = '2026-09-25'; e.save()
e2 = om.C488Engine(bot)
ok("the book survives a restart (qty, average, rebalance date)",
   abs(e2.book['ETH/USDT:USDT']['qty'] - 0.5) < 1e-12 and e2.last_rebal == '2026-09-25')
ok("the default is the portfolio engine, and live money stays off", om.Config().C488_ENGINE == 'portfolio'
   and om.Config().C488_LIVE_OK is False)

print("\n7. THE PAGE (Chromium)")
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
bot, e = mkbot(); e.trade_to('ETH/USDT:USDT', 0.5, 'page'); e.last_rebal = '2026-09-25'
e.info = {'topn': 20}
pf = bot.portfolio
pf.session_start_equity = 1000.0
pf.positions = om.PositionsManager()
pf.get_live_equity = lambda *a: pf.equity + e.unrealized()
fbot = types.SimpleNamespace(cfg=bot.cfg, portfolio=pf, c488=e,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0})
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
import urllib.request
st = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status?t={TOKEN}', timeout=6).read())
c = st.get('c488') or {}
ok("/api/status carries the book", c.get('n') == 1 and c['positions'][0]['symbol'] == 'ETH' and c['mode'] == 'portfolio',
   f"{ {k: c.get(k) for k in ('n', 'gross', 'target_vol', 'last_rebal')} }")
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3500)
        book = pg.inner_text('#book'); mode = pg.inner_text('#bookmode')
        b.close()
    ok("the Portfolio book panel draws the position, gross, vol target and next rebalance",
       'ETH LONG' in book and '1 positions' in book and 'vol target 20%' in book and 'next' in book and mode.lower() == '(portfolio)',
       book.replace("\n", " | ") + " || mode=" + repr(mode))
    ok("no JavaScript errors", not errs, f"{errs}")
except ImportError:
    ok("Chromium/playwright available for the page check", False)

print("\n8. THE PRE-REGISTRATION")
commits = git('log', '--format=%H %s', '--', 'research/c488_preregistration.md').strip().splitlines()
ok("committed exactly once, never edited afterwards", len(commits) == 1, commits[0][:60] if commits else 'none')
if commits:
    h = commits[0].split()[0]
    same = git('show', f'{h}:research/c488_preregistration.md') == open(os.path.join(REPO, 'research', 'c488_preregistration.md'), encoding='utf-8').read()
    eng = git('log', '--format=%H', '-S', 'class C488Engine', '--', 'omega_v60_reconstructed.py').split()
    before = (not eng) or subprocess.run(['git', 'merge-base', '--is-ancestor', h, eng[-1]], cwd=REPO).returncode == 0
    ok("the file on disk is that commit's, and it predates the engine", same and before)

shutil.rmtree(BASE, ignore_errors=True)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
