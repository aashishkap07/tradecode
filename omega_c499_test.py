#!/usr/bin/env python3
"""C499: the C488 book trades on COMPLETE history, or it waits.

Measured on 27 Sep against real Bitget data (research/c499_funding_depth.py):
the bot's 200-record funding fetch left 26 of the carry sleeve's last 60 days
ranked on coins with no funding data, so the book's size wandered from the
research spec (+3% one day, +43% the next). And a request that failed three
times was read as "no more data": one silently failed funding fetch (ARB)
reproduces the 26 Sep rebalance exactly (8 targets, ETH sold, gross 0.40x).

1. FUNDING DEPTH: every page Bitget serves is taken (it stops at a short page).
2. UNKNOWN IS NOT ZERO: before a coin's first funding record its funding is
   NaN, so it sits out the carry ranking for those days (a zero made it the
   "cheapest" coin); a coin with no funding at all is ranked on C1/C2 only.
3. A FAILED FETCH RAISES: candles or any funding page that did not load stop
   the rebalance before a single order; the tick logs it and retries in 10
   minutes; the held book is untouched. An EMPTY answer is not a failure.
4. NOTHING ELSE MOVES: with complete data the targets are what they were.
"""
import os, sys, io, time, types, logging, contextlib, importlib.util, tempfile
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c499_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c499-test-token-0123456789abcdef'
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


print("=" * 66); print("C499: COMPLETE HISTORY, OR THE REBALANCE WAITS"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om499')
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
DAY = 86400000
TODAY = int(time.time() * 1000) // DAY * DAY


class FakeEx:
    def __init__(s):
        s.exchange = types.SimpleNamespace(markets={}); s.markets = s.exchange.markets; s.orders = []
    def get_current_price(s, sym):
        return None


def mkbot():
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0
    pf = om.Portfolio(cfg); pf.equity = pf.available_balance = 1000.0
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 1000.0})
    e = om.C488Engine(bot); e.reset(); pf._c488 = e; bot.c488 = e
    return bot, e


class Venue:
    """a fake Bitget for history-candles / history-fund-rate: `fund_pages` pages
    per coin (the last one short), with optional failures (None) and empties"""
    def __init__(s, days=200, fund_pages=3, fail=None, empty=()):
        s.days, s.fund_pages, s.fail, s.empty, s.calls = days, fund_pages, fail or {}, set(empty), []
    def get(s, path, params, tries=3):
        sym = params['symbol']; s.calls.append((path, sym, params.get('pageNo'), tries))
        if s.fail.get((path, sym, params.get('pageNo'))):
            return None
        if path == 'history-candles':
            end = int(params['endTime']); rows = []
            rng = np.random.default_rng(abs(hash(sym)) % 2 ** 32)
            px = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.03, s.days)))
            for k in range(s.days):
                t = TODAY - (s.days - k) * DAY
                if t <= end:
                    rows.append([str(t), '0', '0', '0', f"{px[k]:.6f}", '0', f"{1e7 * (1 + k % 7):.2f}"])
            rows = rows[-200:]
            return rows[::-1]
        if path == 'history-fund-rate':
            if sym in s.empty:
                return []
            pn = int(params['pageNo'])
            if pn > s.fund_pages:
                return []
            n = 100 if pn < s.fund_pages else 70
            rng = np.random.default_rng((abs(hash(sym)) + pn) % 2 ** 32)
            t0 = int(time.time() * 1000) - (pn - 1) * 100 * 8 * 3600000
            return [dict(fundingTime=str(t0 - i * 8 * 3600000), fundingRate=f"{rng.normal(1e-4, 5e-5):.8f}")
                    for i in range(n)]
        return None


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. FUNDING DEPTH")
bot, e = mkbot(); v = Venue(fund_pages=3); e._get = v.get
c, f = e._history('ETH/USDT:USDT')
pages = [x[2] for x in v.calls if x[0] == 'history-fund-rate']
ok("every page Bitget serves: 3 pages (100 + 100 + 70 = 270 records), stopping at the short page",
   pages == [1, 2, 3] and len(f) == 270, f"pages {pages}, records {len(f)}")
ok("history requests are patient: 5 tries each (was 3)", all(x[3] == 5 for x in v.calls))
v6 = Venue(fund_pages=6); e._get = v6.get
ok("a 4-hour coin's six pages are all taken (the old code stopped at two)", len(e._history('PUMP/USDT:USDT')[1]) == 570)

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. UNKNOWN IS NOT ZERO")
syms = [f"C{j:02d}/USDT:USDT" for j in range(14)]
bot, e = mkbot(); v = Venue(days=200, fund_pages=3, empty={'C13USDT'}); e._get = v.get
T, keep, close, qv, fund = e.matrices(syms)
j0 = keep.index('C00/USDT:USDT'); jn = keep.index('C13/USDT:USDT')
first = min(int(x['fundingTime']) for pn in (1, 2, 3)
            for x in v.get('history-fund-rate', {'symbol': 'C00USDT', 'pageNo': pn})) // DAY * DAY
ok("before the first funding record the day is NaN; from it on, numbers",
   np.isnan(fund[T < first, j0]).all() and not np.isnan(fund[T >= first, j0]).any()
   and (T < first).sum() > 50, f"{int((T < first).sum())} unknown days of {len(T)}")
ok("a coin with no funding at all is unknown throughout", np.isnan(fund[:, jn]).all())
r, W, elig = om._c488_sleeves(T, close, qv, fund, 14)
ok("  so it never takes a carry position, but trend/momentum still see it",
   elig[:, jn].any() and np.all(W['C3'][:, jn] == 0) and np.any(W['C1'][:, jn] != 0),
   f"eligible {int(elig[:, jn].sum())} days, C3 {int((W['C3'][:, jn] != 0).sum())}, C1 {int((W['C1'][:, jn] != 0).sum())}")
old = np.nan_to_num(fund)                          # what the old code built: zeros
_, Wold, _ = om._c488_sleeves(T, close, qv, old, 14)
early = T < first
ok("negative control: with zeros the no-funding days DID carry positions (all tied, or the empty coin 'cheapest')",
   np.abs(Wold['C3'][early]).sum() > 0 and np.all(W['C3'][early] == 0),
   f"old {np.abs(Wold['C3'][early]).sum():.2f} vs new {np.abs(W['C3'][early]).sum():.2f}")
u = om._c488_pnl(W['C3'], r, fund, 1)[0]
ok("the P&L of a book with unknown funding stays a number (no NaN leaks)", np.isfinite(u).all())
w, sl, el = om._c488_targets(T, close, qv, fund, 10, e.target_vol(), 3.0)
ok("  and the targets are finite", np.isfinite(w).all() and np.abs(w).sum() > 0)

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. A FAILED FETCH RAISES; THE REBALANCE WAITS")
for what, key in (('funding page 2', ('history-fund-rate', 'C05USDT', 2)),
                  ('daily candles', ('history-candles', 'C05USDT', None))):
    bot, e = mkbot(); v = Venue(fail={key: True}); e._get = v.get
    try:
        e.matrices(syms); raised = ''
    except RuntimeError as x:
        raised = str(x)
    ok(f"{what} that did not load: matrices() raises, naming the coin", 'C05' in raised and what in raised, raised)
bot, e = mkbot(); v = Venue(fail={('history-fund-rate', 'C05USDT', 2): True}); e._get = v.get
e.book['C01/USDT:USDT'] = dict(qty=1.0, avg=100.0, fees=0.0, funding=0.0, realized=0.0, opened=time.time())
e.marks = {s: dict(bid=99.9, ask=100.1, last=100.0, fr=0.0001, vol=1e8 - i) for i, s in enumerate(syms)}
e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
e.accrue_funding = lambda: None; e.candidates = lambda n: syms
e.trade_to = lambda *a, **k: (_ for _ in ()).throw(AssertionError('traded on a partial picture'))
e.last_rebal = ''; LOG.clear(); e._tick_at = 0.0; e._fail_at = 0.0
e.tick(can_trade=True)
ok("the tick logs 'rebalance failed ... retrying in 10 min', trades nothing, keeps the book",
   any('C488 rebalance failed' in m and 'C05 funding page 2' in m and '10 min' in m for m in LOG)
   and e.last_rebal == '' and e._fail_at > 0 and e.book['C01/USDT:USDT']['qty'] == 1.0,
   next((m for m in LOG if 'rebalance failed' in m), 'no warning'))
bot, e = mkbot(); v = Venue(empty={'C05USDT'}); e._get = v.get
ok("an EMPTY funding answer (a new coin) is not a failure", e.matrices(syms) is not None)

# ─────────────────────────────────────────────────────────────────────────────
print("\n3b. THE HISTORY HOLDS THE COINS THAT WERE TOP 20 THEN")
bot, e = mkbot()
e.marks = {f"K{j:03d}/USDT:USDT": dict(bid=1.0, ask=1.0, last=1.0, fr=0.0, vol=1e9 - j) for j in range(200)}
c20 = e.candidates(20)
ok("the book fetches history for 4x its width: 80 coins at top 20, busiest first",
   len(c20) == 80 and c20[0] == 'K000/USDT:USDT' and c20[-1] == 'K079/USDT:USDT')
ok("  the carry ledger keeps its own width (2x: 80 at its top 40)", len(e.candidates(40, mult=2)) == 80)
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
ok("  and the ledger asks for it explicitly", "e.candidates(P['topn'], mult=2)" in src)

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. NOTHING ELSE MOVES")
bot, e = mkbot(); v = Venue(days=200, fund_pages=40); e._get = v.get   # funding covers every day
T, keep, close, qv, fund = e.matrices(syms)
ok("with funding covering every day nothing is unknown", not np.isnan(fund).any())
w1 = om._c488_targets(T, close, qv, fund, 10, e.target_vol(), 3.0)[0]
w0 = om._c488_targets(T, close, qv, np.nan_to_num(fund), 10, e.target_vol(), 3.0)[0]
ok("  and the targets are exactly the old ones", np.allclose(w1, w0))
ok("version C499 or later", int(om._OMEGA_VERSION[1:]) >= 499)

print()
print("=" * 66)
print(f"C499: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}")
print("=" * 66)
sys.exit(1 if fails else 0)
