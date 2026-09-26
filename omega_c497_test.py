#!/usr/bin/env python3
"""C497: the log's 8-minute status block and the recurring Day line, while the book trades.

The first C495 server log (26 Sep, 21:59 IST) showed the web page and the log
disagreeing about the same month:
  page  "month $4.85 of $37.92 on marked equity . book guard"
  log   "OPEN flat" above a BOOK row holding 8 positions,
        "DAY limit $9.34", "MONTH used $0.59 of $37.92"  (the idle scanner's
        realised figures), and every 8 minutes "Day: ... (loss limit $9.34)".

1. STATUS BLOCK, BOOK ON: OPEN points at the book; MONTH is the book guard on
   marked equity (the same numbers as the page); no DAY limit row.
2. STATUS BLOCK, INTRADAY ENGINE: exactly as before (OPEN flat, DAY row).
3. THE RECURRING LINE: "Book guard: $x of $y used this month on marked equity"
   while the book trades; C483's Day line otherwise.
4. BOOT LINES: the RISK line and Loss control line no longer print the
   scanner's per-trade risk and day limit while the book trades; the legacy
   banner is labelled as the scanner's.
"""
import os, sys, io, time, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c497_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c497-test-token-0123456789abcdef'
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


print("=" * 66); print("C497: THE LOG'S STATUS BLOCK DESCRIBES THE BOOK"); print("=" * 66)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om497')
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False


class FakeEx:
    def __init__(s):
        s.exchange = types.SimpleNamespace(markets={'ETH/USDT:USDT': dict(precision={'amount': 0.01}, limits={'amount': {'min': 0.01}})})
        s.markets = s.exchange.markets
    def get_current_price(s, sym):
        return None


# the server's own figures on 26 Sep: C482 anchor $252.81, realised $252.22,
# the book open about -$4.26 -> marked $247.96, guard used $4.85 of $37.92
G = {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92, 'month_used': 0.59,
     'day_cap': 9.34, 'day_used': 0.0, 'day0': 252.26, 'day_pnl': -0.04, 'halt': ''}


def mkbot(engine='portfolio', book=True):
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = engine
    om._c467_cfg_ref[0] = cfg
    pf = om.Portfolio(cfg); pf.equity = 252.22; pf.available_balance = 233.88
    pf.session_start_equity = 252.22
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: dict(G),
                                c489=None, c490=None)
    bot._c467_day_barrier = lambda: om.TradingBot._c467_day_barrier(bot)
    e = om.C488Engine(bot); e.reset(); pf._c488 = e; bot.c488 = e
    e.marks = {'ETH/USDT:USDT': dict(bid=1999.0, ask=2001.0, last=2000.0, fr=0.0001, vol=9e9)}
    e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
    if book:
        # 0.0426 ETH bought at 2100 marks at the 1999 bid: open -$4.30
        e.book['ETH/USDT:USDT'] = dict(qty=0.0426, avg=2100.0, fees=0.0, funding=0.0, realized=0.0,
                                       opened=time.time())
    if engine == 'portfolio':
        e.guard()
    return bot, e


def block(bot):
    rep = om._C462Report(os.path.join(BASE, f'r_{time.time_ns()}.log')); rows = []
    rep._emit = lambda line: rows.append(str(line))
    rep.status(bot)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. STATUS BLOCK, BOOK ON")
bot, e = mkbot('portfolio')
gv = dict(e._guard_view)
rows = block(bot); txt = '\n'.join(rows)
ok("the guard view is the server's arithmetic: anchor $252.81 carried from C482, used = anchor - marked",
   gv['eq0'] == 252.81 and abs(gv['used'] - (252.81 - e.live_equity())) < 0.011 and gv['budget'] == 37.92, str(gv))
opn = [r for r in rows if r.strip().startswith('OPEN')]
ok("OPEN no longer says 'flat' above the book: 'no intraday positions . book holds 1 (BOOK row)'",
   opn and 'flat' not in opn[0] and 'no intraday positions' in opn[0] and 'book holds 1' in opn[0], str(opn))
mon = [r for r in rows if r.strip().startswith('MONTH')]
ok("MONTH is the book guard on marked equity, with the page's numbers",
   mon and 'book guard' in mon[0] and f"${gv['used']:.2f} of $37.92" in mon[0] and 'marked' in txt
   and 'from $252.81' in txt, str(mon))
ok("no DAY limit row and no scanner 'used $0.59' while the book trades",
   not any(r.strip().startswith('DAY') for r in rows) and 'used $0.59' not in txt)
ok("the BOOK row is still there", any(r.strip().startswith('BOOK') for r in rows))
e.halt = 'month:' + dt.datetime.now().strftime('%Y-%m')
txt_h = '\n'.join(block(bot))
ok("a halted book says so on the MONTH row", 'HALTED month:' in txt_h)
e.halt = ''
bot.c488._guard_view = {}
txt_0 = '\n'.join(block(bot))
ok("before the guard's first check (no view yet) it falls back to the old rows instead of printing zeros",
   'book guard' not in txt_0 and ('DAY' in txt_0))
e.guard()                                            # the next check restores it

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. STATUS BLOCK, INTRADAY ENGINE (negative control)")
bot_i, e_i = mkbot('intraday', book=False)
rows_i = block(bot_i); txt_i = '\n'.join(rows_i)
ok("OPEN reads 'flat'; the DAY row and C482's MONTH row are unchanged",
   any(r.strip().startswith('OPEN') and 'flat' in r for r in rows_i)
   and any(r.strip().startswith('DAY') and 'limit $9.34' in r for r in rows_i)
   and 'used $0.59 of $37.92' in txt_i and 'book guard' not in txt_i, txt_i[-300:].replace('\n', ' | '))

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. THE RECURRING LINE")
ln = om.TradingBot._c497_day_line(bot, '\U0001f53b', -0.02, dict(G))
ok("book on: 'Book guard: $x of $37.92 used this month on marked equity'",
   ln.startswith('\U0001f53b Book guard:') and f"${gv['used']:.2f} of $37.92" in ln and 'marked' in ln
   and 'loss limit' not in ln and 'realised today -0.02%' in ln, ln)
ln_i = om.TradingBot._c497_day_line(bot_i, '\U0001f53b', -0.02, dict(G))
ok("intraday: C483's line, byte for byte",
   ln_i == "\U0001f53b Day: -0.02% realised (loss limit $9.34, 0% used · dial 15%/month) [C483]", ln_i)
ln_n = om.TradingBot._c497_day_line(types.SimpleNamespace(), '\U0001f535', 0.1, {})
ok("no engine and no cap: still a Day line, no crash", ln_n == "\U0001f535 Day: +0.10% realised [C483]", ln_n)

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. BOOT LINES")
def boot_risk(engine):
    cfg = om.Config(); cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = engine
    plan = dict(equity=252.22, normal_pct=0.5, hp_pct=0.2, cap_pct=3.7, per_trade_pct=0.341, binding=False)
    b = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, _c369_derive_budget=lambda eq: dict(plan),
                              _c463_realised_payoff=lambda: (2.10, 20), _c482_risk_guard=lambda: dict(G))
    LOG.clear(); om.TradingBot._c369_apply_budget(b, 252.22)
    return list(LOG)
rb, ri = boot_risk('portfolio'), boot_risk('intraday')
ok("boot RISK line, book on: dial and month budget, the book's guard, no per-trade risk and no day limit",
   len(rb) == 1 and 'monthly dial 15% = $37.92/month' in rb[0] and 'month guard' in rb[0]
   and 'per-trade' not in rb[0] and 'break-even' not in rb[0], str(rb))
ok("boot RISK lines, intraday (negative control): per-trade risk, break-even and the day limit as before",
   len(ri) == 2 and 'per-trade risk 0.341% = $0.86' in ri[0] and 'break-even win rate 32%' in ri[0]
   and "today's loss limit is 25%" in ri[1], str(ri))
ok("the Loss control line names the book guard while the book trades",
   "no day limit applies to the book (C497)" in src)
ok("the legacy banner is labelled as the scanner's", "The blocks below describe the " in src)
ok("version C497 or later", int(om._OMEGA_VERSION[1:]) >= 497)

print()
print("=" * 66)
print(f"C497: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}")
print("=" * 66)
sys.exit(1 if fails else 0)
