#!/usr/bin/env python3
"""C503: every boot and status line says something true on its own.

The operator asked, after the C502 deploy (28 Sep 13:36 IST), that every line of
the detail and session logs be true. Checked line by line against the code,
Bitget and the arithmetic, these were not:
  "ARCHITECTURE -- what is actually running:" heading a scanner that is idle;
  "756 markets" and "294 RWA perps" (literals; 804 and 340 on 28 Sep);
  "Version history: see CHANGELOG.md (auto-updated each revision)" (the table
   stops at C466);
  "RISK @ $250.39: monthly dial 15% = $37.92" (15% of the ANCHOR $252.81);
  "Loaded state: ... 0 positions" beside $23.94 of the book's margin;
  "free $226.45" / "Available: $226.45" (Bitget nets the open P&L: $220.66);
  "Limit Orders: ENABLED", sizing, leverage, the edge state, the DRI block,
   "Normal start" -- all the idle scanner's, unlabelled;
  "4 EXIT ... HARD STOP ..." copied into the session log as an alert;
  "Same WiFi" on a server; "Press Ctrl+C" under systemd;
  the spot pot's run and the K4 shadow never reached the session log;
  "MARKET bias +0.00 breadth +0.00" every 8 min, never measured;
  "LIFETIME 139tr 44W 95L $+0.39" (intraday trades, the account's dollars);
  "Win Rate: Session 0% | Open 0%" with no trades and no intraday positions;
  the shutdown summary "+$0.08 from $244.60" beside a SESSION row of +$0.11
   (from $244.57); "Log saved" written twice at every stop.

1. THE SUMMARY OF WHAT RUNS, read from the settings (and nothing when the
   scanner is the engine).
2. THE SESSION FILTER: the boot description is no longer an alert; C501's
   ledger lines, the summary, "Local network" and "Stop safely" reach it.
3. THE RISK LINE names the anchor; the RISK FRAME and header say "realised".
4. THE STATUS BLOCK: OPEN's free is after the open P&L; no MARKET row while the
   book trades; LIFETIME labels its two halves; the session curve starts at the
   book's first full mark (the SESSION row's baseline); the log is sealed once.
5. SOURCE: no literal market counts; the changelog line reads the table.
"""
import os, sys, io, time, types, logging, contextlib, importlib.util, tempfile
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c503_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c503-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om503', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append(r.getMessage())
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C503: EVERY BOOT AND STATUS LINE IS TRUE ON ITS OWN"); print("=" * 66)

# the server's figures, 28 Sep 13:36 IST
G = {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92, 'month_used': 2.42,
     'day_cap': 9.34, 'day_used': 0.0, 'day0': 252.26, 'day_pnl': -0.04, 'halt': ''}


class FakeEx:
    def __init__(s):
        s.exchange = types.SimpleNamespace(markets={'ETH/USDT:USDT': dict(precision={'amount': 0.01},
                                                                          limits={'amount': {'min': 0.01}})})
        s.markets = s.exchange.markets
    def get_current_price(s, sym):
        return None


def mkbot(engine='portfolio'):
    cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = engine
    om._c467_cfg_ref[0] = cfg
    pf = om.Portfolio(cfg); pf.equity = 250.39; pf.available_balance = 226.45; pf.session_start_equity = 250.39
    bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=FakeEx(), _c462_state_settled=True,
                                _c408_asset_class=lambda s: 'crypto', _c482_risk_guard=lambda: dict(G))
    bot._c467_day_barrier = lambda: om.TradingBot._c467_day_barrier(bot)
    e = om.C488Engine(bot); e.reset(); pf._c488 = e; bot.c488 = e
    e.marks = {'ETH/USDT:USDT': dict(bid=1999.0, ask=2001.0, last=2000.0, fr=0.0001, vol=9e9)}
    e.refresh_marks = lambda force=False: True; e.refresh_rules = lambda force=False: True
    e.book['ETH/USDT:USDT'] = dict(qty=0.0426, avg=2100.0, fees=0.0, funding=0.0, realized=0.0, opened=time.time())
    bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot); bot.c501s = om.C501Spot(bot)
    if engine == 'portfolio':
        e.guard()
    return bot, e


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. WHAT RUNS, READ FROM THE SETTINGS")
bot, e = mkbot('portfolio')
LOG.clear(); om.TradingBot._c503_running(bot); run_txt = '\n'.join(LOG)
ok("the book: C1+C2+C3, vol target 20% from the 15% dial, gross <= 3x, top 20, $6, 30% band",
   'trend (C1) + momentum (C2) + carry (C3)' in run_txt and 'vol target 20% from the 15% dial' in run_txt
   and 'gross <= 3x' in run_txt and 'top 20 crypto' in run_txt and '$6 minimum' in run_txt and '30% band' in run_txt,
   LOG[1] if len(LOG) > 1 else '')
ok("  market orders at the ask/bid, taker 0.06%, 5x cross, funding per coin's interval, the month guard",
   'market orders (paper fills at the ask/bid, taker 0.06%)' in run_txt and '5x cross margin' in run_txt
   and "each coin's own interval" in run_txt and 'month guard on MARKED equity' in run_txt)
ok("  the paper ledgers with their times, and that they never touch the account",
   'never touches the account' in run_txt and 'intraday shadow (C489) hourly' in run_txt
   and 'carry (C490) 00:10 UTC' in run_txt and 'spot pot (C501/C502) $250, spot minimum $1, 00:20 UTC' in run_txt
   and 'Savings at 7.63% every minute' in run_txt and 'allostatic shadow (K4) at each rebalance' in run_txt)
ok("  and that everything after it describes the idle scanner", 'IDLE   the intraday scanner' in run_txt)
cfg20 = bot.cfg; cfg20.C380_MAX_MONTHLY_DD_PCT = 20.0
LOG.clear(); om.TradingBot._c503_running(bot)
ok("  it reads the dial: 20% -> vol target 27%", 'vol target 27% from the 20% dial' in '\n'.join(LOG))
cfg20.C380_MAX_MONTHLY_DD_PCT = 15.0
bot_i, _ = mkbot('intraday')
LOG.clear(); om.TradingBot._c503_running(bot_i)
ok("with the scanner as the engine it prints nothing", LOG == [], str(LOG))

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. THE SESSION LOG")
F = om._C460ConsoleFilter()


def passes(msg, level=logging.INFO):
    r = logging.LogRecord('OmegaV60', level, __file__, 1, msg, None, None)
    return bool(F.filter(r))


ok("the scanner's exit description is no longer copied in as an alert",
   not passes("  4 EXIT       4 questions: hard stop · thesis dead (C399 retention)"))
ok("  (negative control: the old capitals did pass, which is how it reached the 28 Sep session log)",
   passes("  4 EXIT       4 questions: HARD STOP · THESIS DEAD (C399 retention)"))
ok("  a real C377 hard stop still reaches it",
   passes("   \U0001f6d1 C377 HARD STOP ETH: -1.50R reached, closing"))
ok("the spot pot's daily run and the K4 shadow reach it",
   passes("   \U0001fa99 C501 spot pot (paper) 2026-09-29: $250.40 (+0.16%) | 18 held, 34% invested")
   and passes("   \U0001f9ec C501 allostatic shadow (paper): K4 0.66x vs running 0.40x"))
ok("the summary of what runs reaches it, line by line",
   all(passes(m) for m in LOG_RUN) if (LOG_RUN := run_txt.split('\n')) else False, str(len(LOG_RUN)))
ok("'Local network' and 'Stop safely' reach it",
   passes("   \U0001f4f1 Local network: http://10.0.0.160:8138/?t=<your token> (this machine's own address)")
   and passes("\U0001f4a1 Stop safely: sudo systemctl stop omega (Ctrl+C only when run by hand)"))

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. THE RISK LINE, THE RISK FRAME, THE HEADER")
plan = dict(equity=250.39, normal_pct=0.5, hp_pct=0.2, cap_pct=3.7, per_trade_pct=0.341, binding=False)
b = types.SimpleNamespace(cfg=bot.cfg, _c462_state_settled=True, _c369_derive_budget=lambda eq: dict(plan),
                          _c463_realised_payoff=lambda: (2.10, 20), _c482_risk_guard=lambda: dict(G))
LOG.clear(); om.TradingBot._c369_apply_budget(b, 250.39)
rl = next((m for m in LOG if 'RISK @' in m), '')
ok("RISK: '$37.92/month (15% of this month's anchor $252.81)' -- not 15% of the $250.39 beside it",
   "= $37.92/month (15% of this month's anchor $252.81)" in rl, rl[:120])
om._c467_cfg_ref[0] = bot.cfg
rep = om._C462Report(os.path.join(BASE, 'r_hdr.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep._raw = lambda line: rows.append(str(line))
rep.header('C503', 'PAPER', 250.39, day_barrier=15.0)
rep.risk_frame(dict(equity=250.39, cap_pct=3.7, dd_pct=15.0), markets=804, guard=dict(G))
hdr = '\n'.join(rows)
ok("the header's start and the RISK FRAME's EQUITY say 'realised' while the book trades",
   'start $250.39 realised' in hdr and any(r.strip().startswith('EQUITY') and '$250.39 realised' in r for r in rows),
   hdr.replace('\n', ' | ')[:240])

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. THE STATUS BLOCK")
rep2 = om._C462Report(os.path.join(BASE, 'r_st.log')); rows2 = []
rep2._emit = lambda line: rows2.append(str(line))
rep2.status(bot)
i_open = next(i for i, r in enumerate(rows2) if r.strip().startswith('OPEN'))
opn = ' '.join(rows2[i_open:i_open + 2])                       # a long row wraps onto a continuation line
live, locked = e.live_equity(), float(bot.portfolio.get_locked_margin())
ok("OPEN: free is marked equity - margin, after the open P&L (what Bitget shows)",
   f"free ${live - locked:.2f} after open P&L" in opn, f"{opn} | live {live:.2f} locked {locked:.2f}")

mk = [r for r in rows2 if r.strip().startswith('MARKET')]
ok("no MARKET row while the book trades (the scanner reads it; not read is not zero)", mk == [], str(mk))
i_life = next((i for i, r in enumerate(rows2) if r.strip().startswith('LIFETIME')), None)
bot.portfolio.lifetime_trades, bot.portfolio.lifetime_wins, bot.portfolio.lifetime_losses = 139, 44, 95
bot.portfolio.lifetime_pnl = 0.39
rows3 = []; rep2._emit = lambda line: rows3.append(str(line)); rep2.status(bot)
lf = ' '.join(r for r in rows3 if r.strip().startswith('LIFETIME'))
ok("LIFETIME: the trades are the intraday scanner's, the dollars the account's",
   '139tr 44W 95L' in lf and ('intraday' in lf or 'old scanner' in lf)          # C510: "old scanner"
   and 'account $+0.39 realised' in lf, lf)

# ─────────────────────────────────────────────────────────────────────────────
print("\n4b. THE SESSION SUMMARY STARTS WHERE THE SESSION ROW STARTS")
bot.portfolio.session_start_equity = bot.portfolio.equity
e.open0 = None; e._tick_at = 0.0
e.accrue_funding = lambda: None; e.due = lambda: False
om._c462_report.equity_curve.clear()
try:
    e.tick(can_trade=False)
except Exception as ex:
    print('   (tick raised after the baseline:', type(ex).__name__, ex, ')')
cv = list(om._c462_report.equity_curve)
ok("the first full mark fixes open0 AND starts the curve at the same marked equity",
   e.open0 is not None and cv and abs(cv[0] - e.live_equity()) < 1e-9, f"open0 {e.open0} curve {cv[:2]}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n4c. THE LOG IS SEALED ONCE")
_lp = om._C52_LOG_PATH
_n0 = open(_lp, encoding='utf-8').read().count('Log saved') if os.path.exists(_lp) else 0
om._c52_flush(); om._c52_flush()
_n1 = open(_lp, encoding='utf-8').read().count('Log saved') if os.path.exists(_lp) else 0
ok("a stop (SIGTERM flush, then atexit flush) writes 'Log saved' once", _n1 - _n0 == 1, f"{_n1 - _n0}")
om._c52_sealed[0] = True                                 # this test's own exit must not add another

# ─────────────────────────────────────────────────────────────────────────────
print("\n5. SOURCE")
ok("win rates with no trades say so ('no trades yet', 'none open') instead of 0%",
   "'no trades yet'" in src and "'none open'" in src)
ok("the page's record tile: 'all-time 44W 95L intraday · account +$0.39'",
   "'L intraday \\u00b7 account <span class=\"'" in src)
ok("no literal market counts in the scanner block ('756 markets', '294 RWA perps')",
   '"  1 SCANNER    756 markets' not in src and '"  UNIVERSE     crypto + 294' not in src
   and '{len(_mk503) - _nx503} crypto + {_nx503} RWA perps' in src)
ok("the changelog line reads the table's newest entry (C466), no 'auto-updated each revision'",
   'auto-updated each revision")' not in src
   and om.TradingBot._write_changelog(types.SimpleNamespace()) == 'C466')
ok("Loaded state: 'intraday positions' and 'available ... before open P&L'",
   'intraday positions | "' in src and 'before open P&L "' in src)
ok("Limit orders, sizing, leverage, edge state, DRI, shared learning: labelled the idle scanner's",
   "the idle intraday scanner's; the book trades with market orders" in src
   and '_sc503 = " (idle scanner)" if _b503 else ""' in src
   and "C458 EDGE STATE (the idle scanner's own trade record)" in src
   and "-- the idle scanner's exit model:" in src)
ok("the monitor line says it watches intraday positions; the engine line counts the book",
   'it watches INTRADAY positions; the book has no stops' in src and 'the book holds {len(self.c488.book)} positions' in src)
ok("the stop line follows systemd", "os.environ.get('INVOCATION_ID')" in src and 'sudo systemctl stop omega' in src)
ok("version C503 or later", int(om._OMEGA_VERSION[1:4]) >= 503)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
