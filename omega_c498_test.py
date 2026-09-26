#!/usr/bin/env python3
"""C498: a session is measured MARKED to MARKED while the book trades.

The C497 screens (26 Sep, 22:41 IST restart) showed, twenty minutes into a run
in which the book had moved a few cents:
  SESSION   $-4.18 -1.66%  peak $252.22  dd 1.66%
  Session: $-4.18 (-1.7%)                       (8-minute POSITION SUMMARY)
  EQUITY THIS SESSION  low $247.79  high $252.22 (web)
because the session started from REALISED equity ($252.22) and was compared
with MARKED equity: the book's standing open P&L (about -$4.2) was booked as a
loss of the new run, and the curve's first point was $4 above anything the run
ever marked.

1. THE ENGINE: carried_open() is the book's open P&L at its FIRST full mark in
   this run; it does not move after; nothing is fixed before every position has
   a price; reset clears it.
2. THE STATUS BLOCK: SESSION is marked now minus (realised start + carried
   open): cents, not dollars; no phantom peak or drawdown.
3. THE 8-MINUTE SUMMARY: the same figure, and it now sees the book's REALISED
   P&L too (a rebalance that closes a position moves money from open to
   realised; the session figure must not jump).
4. THE CURVE: the boot header does not seed it with realised equity while the
   book trades; an unpriced book is not sampled.
5. NEGATIVE CONTROLS: with the intraday engine every figure is as before.
"""
import os, sys, io, time, types, logging, contextlib, importlib.util, tempfile
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c498_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c498-test-token-0123456789abcdef'
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


print("=" * 66); print("C498: THE SESSION IS MEASURED MARKED TO MARKED"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om498')
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False

G = {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92, 'month_used': 0.59,
     'day_cap': 9.34, 'day_used': 0.0, 'day0': 252.26, 'day_pnl': -0.04, 'halt': ''}
SYM = 'WLD/USDT:USDT'


class FakeEx:
    def __init__(s):
        s.exchange = types.SimpleNamespace(markets={SYM: dict(precision={'amount': 0.1}, limits={'amount': {'min': 0.1}})})
        s.markets = s.exchange.markets
    def get_current_price(s, sym):
        return None


def mkbot(engine='portfolio'):
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = engine
    om._c467_cfg_ref[0] = cfg
    pf = om.Portfolio(cfg); pf.equity = 252.22; pf.available_balance = 233.88
    pf._c462_mark_session_start()                          # the restart: realised $252.22
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: dict(G),
                                c489=None, c490=None)
    bot._c467_day_barrier = lambda: om.TradingBot._c467_day_barrier(bot)
    e = om.C488Engine(bot); e.reset(); pf._c488 = e; bot.c488 = e
    e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
    e.accrue_funding = lambda: None; e.due = lambda: False
    if engine == 'portfolio':
        # a WLD short carried over the restart: 10 WLD sold at 1.50
        e.book[SYM] = dict(qty=-10.0, avg=1.50, fees=0.0, funding=0.0, realized=0.0, opened=time.time() - 1e5)
    return bot, e


def tick(e):
    e._tick_at = 0.0
    e.tick(can_trade=True)


def price(e, px):
    e.marks[SYM] = dict(bid=px - 0.0005, ask=px + 0.0005, last=px, fr=0.0001, vol=9e9)


def block(bot):
    rep = om._C462Report(os.path.join(BASE, f'r_{time.time_ns()}.log')); rows = []
    rep._emit = lambda line: rows.append(str(line))
    rep.status(bot)
    return rep, rows


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. THE ENGINE")
bot, e = mkbot('portfolio')
e.marks = {}
tick(e)
ok("before the book is priced: marked_ok False, nothing fixed, carried_open 0",
   e.marked_ok() is False and e.open0 is None and e.carried_open() == 0.0)
price(e, 1.92)                                             # WLD ran 28% against the short
tick(e)
u0 = e.unrealized()
ok("the first full mark fixes it: the book's open P&L then (about -$4.2 plus the exit fee)",
   e.open0 is not None and abs(e.carried_open() - u0) < 1e-3 and -4.3 < u0 < -4.1, f"{e.carried_open():.4f}")
price(e, 1.945)
tick(e)
ok("it does not move afterwards", abs(e.carried_open() - u0) < 1e-3 and e.unrealized() < u0 - 0.2,
   f"carried {e.carried_open():.3f} now {e.unrealized():.3f}")
bot.cfg.C488_ENGINE = 'intraday'
ok("an inactive engine carries nothing", e.carried_open() == 0.0)
bot.cfg.C488_ENGINE = 'portfolio'
e.reset()
ok("reset clears it", e.open0 is None)

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. THE STATUS BLOCK")
bot, e = mkbot('portfolio')
price(e, 1.92); tick(e)                                    # first mark: carried about -4.21
price(e, 1.945)                                            # the run itself then loses 10 x 0.025 = $0.25
rep, rows = block(bot); txt = '\n'.join(rows)
sess = [r for r in rows if r.strip().startswith('SESSION')]
live = bot.portfolio.get_live_equity(bot.exchange)
exp = live - (252.22 + e.carried_open())
ok("SESSION is this run's move only (about -$0.25), not the carried -$4.2",
   sess and f"{om._c462_money(exp, sign=True)}" in sess[0] and -0.30 < exp < -0.20, f"{sess} expected {exp:+.3f}")
ok("no phantom peak at the realised $252.22", '252.22' not in (sess[0] if sess else ''), str(sess))
ok("the first curve sample is MARKED equity", rep.equity_curve and abs(rep.equity_curve[0] - live) < 0.011,
   f"{rep.equity_curve[:2]} vs {live:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. THE 8-MINUTE SUMMARY")
st = bot.portfolio.get_stats(bot.exchange)
p, pct = om.TradingBot._c498_session_pnl(bot, st)
ok("'Session:' is the same figure as the SESSION row", abs(p - exp) < 1e-6 and abs(pct - exp / (252.22 + e.carried_open()) * 100) < 1e-6,
   f"{p:+.3f} ({pct:+.2f}%)")
# a rebalance closes the WLD short at the mark: open P&L becomes realised
upl = e.unrealized()
bot.portfolio.equity += upl; e.book.clear()
st2 = bot.portfolio.get_stats(bot.exchange)
p2, _ = om.TradingBot._c498_session_pnl(bot, st2)
ok("a close moves money from open to realised and the session figure does not jump",
   abs(p2 - p) < 1e-6, f"before {p:+.4f} after {p2:+.4f}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. THE CURVE")
bot, e = mkbot('portfolio')
e.marks = {}                                               # restart, book not yet priced
rep = om._C462Report(os.path.join(BASE, 'h.log')); rep._emit = lambda line: None
rep.header('C498', 'PAPER', 252.22)
ok("the boot header does not seed the marked curve with realised equity while the book trades",
   rep.equity_curve == [] and rep.peak_equity == 0.0, str(rep.equity_curve))
rep.status(bot)
ok("an unpriced book is not sampled", rep.equity_curve == [], str(rep.equity_curve))

# ─────────────────────────────────────────────────────────────────────────────
print("\n5. NEGATIVE CONTROLS (intraday engine)")
bot_i, e_i = mkbot('intraday')
rep_i = om._C462Report(os.path.join(BASE, 'hi.log')); rep_i._emit = lambda line: None
rep_i.header('C498', 'PAPER', 252.22)
ok("the header still seeds the curve", rep_i.equity_curve == [252.22])
bot_i.portfolio.equity = 251.00
rep_i2, rows_i = block(bot_i)
sess_i = [r for r in rows_i if r.strip().startswith('SESSION')]
ok("SESSION is live minus the realised start, as before", sess_i and '$-1.22' in sess_i[0], str(sess_i))
st_i = bot_i.portfolio.get_stats(bot_i.exchange)
p_i, pct_i = om.TradingBot._c498_session_pnl(bot_i, st_i)
ok("'Session:' is the old sum (intraday realised + open)",
   p_i == bot_i.portfolio.session_pnl + (st_i.get('unrealized') or 0), f"{p_i}")
ok("version C498", om._OMEGA_VERSION == 'C498')

print()
print("=" * 66)
print(f"C498: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}")
print("=" * 66)
sys.exit(1 if fails else 0)
