#!/usr/bin/env python3
"""C511: what the 29 Sep fresh-start screenshots and a full read of C510 found.

1. THE OLD SCANNER'S RECORD after a fresh start: the account's counters are
   zero, and the boot said "(0 trades, 0W/0L, lost after fees)". It now gives
   the audited record (139 trades, 44W/95L before the fresh start) until the
   account has one of its own; the page says the same.
2. THE IDLE SCANNER'S BOOT DESCRIPTION (~80 lines: architecture, exit model,
   sizing, "edge" bookkeeping, "464 crypto + 340 RWA perps ... session-gated")
   is held back while the book trades -- through the real logger (the first
   C511 boot died because the module's `logger` is a wrapper with no
   addFilter; the sandbox dry run caught it). Warnings still pass.
3. "Day cap: 0.91% = $2.27" and the mode reset lines are labelled as the idle
   scanner's; the 8-minute and dashboard headers say "daily book", not "scan 0";
   the shutdown summary's RAN and COST describe the book (it said "fees $0.00"
   beside a book that had paid $0.06 on 11 fills).
4. ONE LEDGER PER QUESTION: the K4 shadow stands down while the rule
   tournament runs (its "N2+N3, K4 sizing" row is the same A/B).
5. Quantities read as numbers: 1,654,000 PEPE, not 1.655e+06.
"""
import os, io, time, glob, socket, types, logging, threading, contextlib, importlib.util, tempfile
import datetime as dt
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c511_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c511-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om511', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C511: THE FRESH-START SCREENS AND THE C510 READ-THROUGH"); print("=" * 66)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 20.0; cfg.C488_ENGINE = 'portfolio'
om._c467_cfg_ref[0] = cfg
pf = om.Portfolio(cfg); pf.equity = 249.94; pf.available_balance = 228.0; pf.session_start_equity = 250.0
pf.get_live_equity = lambda *a: 249.90
pf.lifetime_trades = pf.lifetime_wins = pf.lifetime_losses = 0; pf.lifetime_pnl = -0.06
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={1: 1}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 250.0, 'month_budget': 50.0,
                                                      'month_used': 0.10, 'day_cap': 12.5, 'day_used': 0.0, 'halt': ''})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot)
bot.c501s = om.C501Spot(bot); bot.c501v = om.C501Savings(bot); bot.c501k = om.C501Allostatic(bot)
bot.c510t = om.C510Tournament(bot)

print("\n1. THE OLD SCANNER'S RECORD AFTER A FRESH START")
LOG.clear(); om.TradingBot._c503_running(bot)
idle = ' '.join(m for lv, m in LOG if 'IDLE   the intraday scanner' in m)
ok("fresh account (counters 0): 'the OLD strategy (139 trades, 44W/95L before the 29 Sep 2026 fresh start; "
   "it lost after fees)'", '139 trades, 44W/95L before the 29 Sep 2026 fresh start; it lost after fees' in idle
   and '0 trades' not in idle, idle)
ok("  and it says its boot description is not printed", 'its boot description is not printed' in idle)
pf.lifetime_trades, pf.lifetime_wins, pf.lifetime_losses = 5, 2, 3
LOG.clear(); om.TradingBot._c503_running(bot)
idle2 = ' '.join(m for lv, m in LOG if 'IDLE' in m)
ok("an account with its own scanner trades: its own figures ('5 trades, 2W/3L')", '5 trades, 2W/3L' in idle2, idle2)
pf.lifetime_trades = pf.lifetime_wins = pf.lifetime_losses = 0
paper = ' '.join(m for lv, m in LOG if 'PAPER  never touches' in m)
ok("the boot's PAPER list has the tournament and no separate K4 shadow (one ledger per question)",
   'rule tournament' in paper and 'allostatic shadow (K4)' not in paper, paper)

print("\n2. THE IDLE SCANNER'S BOOT DESCRIPTION IS HELD BACK, THROUGH THE REAL LOGGER")
ok("the module's logger is the CustomLogger wrapper (no addFilter of its own -- the first C511 boot's crash)",
   not hasattr(om.logger, 'addFilter') and hasattr(om.logger, 'logger'))
LOG.clear()
flt = om.TradingBot._c511_scanner_quiet(True)
om.logger.info("📊 INTRADAY SCANNER -- IDLE ... 464 crypto + 340 RWA perps")
om.logger.warning("⚠️ something real went wrong")
th = threading.Thread(target=lambda: om.logger.info("🔄 Monitoring thread started (another thread)")); th.start(); th.join()
om.TradingBot._c511_scanner_quiet(False, flt)
om.logger.info("💡 Stop safely: sudo systemctl stop omega")
msgs = [m for lv, m in LOG]
ok("while held: this thread's INFO lines are not written", not any('INTRADAY SCANNER' in m for m in msgs), str(msgs))
ok("  a warning still is", any('something real went wrong' in m for m in msgs))
ok("  another thread's lines still are", any('another thread' in m for m in msgs))
ok("  and after release everything is written again", any('Stop safely' in m for m in msgs))
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
r0 = src.index('    def run(self):\n        # PHASE4')
ok("run() holds it back only while the book trades, and releases it before 'Stop safely'",
   src.index('_m511 = self._c511_scanner_quiet(True)', r0) < src.index('C458 EDGE STATE', r0)
   < src.index('📋 CONFIGURATION', r0) < src.index('self._c511_scanner_quiet(False, _m511)', r0)
   < src.index('Stop safely: sudo systemctl stop omega', r0))

print("\n3. SCANNER-ONLY LINES, HEADERS AND THE SHUTDOWN SUMMARY")
mm = om.TradingModeManager(cfg)
LOG.clear(); mm._session_cycles = 0; mm._day_start_equity = None; mm.reset(250.0)
day = ' '.join(m for lv, m in LOG)
ok("book on: 'Day start equity set: $250.00 [C309] -- the idle scanner's day cap does not apply to the book'",
   'the idle scanner\'s day cap does not apply to the book' in day and 'Day cap:' not in day
   and "Trading mode reset -- the idle scanner's" in day, day[:300])
ci = om.Config(); ci.C488_ENGINE = 'intraday'
mi = om.TradingModeManager(ci); LOG.clear(); mi._session_cycles = 0; mi._day_start_equity = None; mi.reset(250.0)
ok("  intraday (negative control): the day cap as before", any('Day cap:' in m for lv, m in LOG))
e.fills_run = [11, 0.06, 108.16]; e.tally = dict(n=0, w=0, l=0, pnl=0.0)
e.born = dict(ts=time.time() - 3600, eq=250.0, approx=False); e.month = {'key': dt.datetime.now().strftime('%Y-%m'), 'eq0': 250.0}
e.marks = {'NEAR/USDT:USDT': dict(bid=4.74, ask=4.75, last=4.745, fr=0.0001, vol=9e9)}
e.book = {'NEAR/USDT:USDT': dict(qty=2.0, avg=4.7466, fees=0.006, funding=0.0, realized=0.0, opened=time.time() - 3600)}
e._marks_at = time.time(); e.last_rebal = dt.datetime.utcnow().strftime('%Y-%m-%d')
bot._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep.status(bot)
hdr = next((r for r in rows if ' up ' in r and '---' in r), '')
ok("the 8-minute header: 'HH:MM  up ...  daily book', not 'scan 0'", 'daily book' in hdr and 'scan ' not in hdr, hdr)
rows.clear(); rep.session_summary()                 # the atexit path: no bot passed
sm = '\n'.join(rows)
ok("the shutdown summary (atexit, no bot passed): 'RAN ... daily book  11 book fills this run'",
   'daily book' in sm and '11 book fills this run' in sm and 'pair-analyses' not in sm, sm[:400])
ok("  'COST book fees $0.06  11 taker fills  0.055% of $108.16 traded', not 'fees $0.00'",
   'book fees $0.06' in sm and '11 taker fills' in sm and 'fees $0.00' not in sm, sm[-400:])

print("\n4. ONE LEDGER PER QUESTION")
ok("the K4 shadow stands down while the tournament runs", bot.c510t.active() and not bot.c501k.active())
b2 = types.SimpleNamespace(cfg=cfg); k2 = om.C501Allostatic(b2)
ok("  and runs as before where there is no tournament", k2.active())
cfg.C510_TOURNAMENT = False
ok("  and again if the tournament is switched off", bot.c501k.active())
cfg.C510_TOURNAMENT = True
TODAY = dt.datetime.utcnow().strftime('%Y-%m-%d')
e._last_M = (TODAY, 20, None); bot.c501k.last_obs = ''; bot.c510t.last_obs = TODAY
h = om.TradingBot._c504_data_health(bot, time.time())
ok("  so the watchdog does not call a stood-down K4 late", 'K4' not in h['keys'], str(h['late']))

print("\n5. QUANTITIES READ AS NUMBERS")
ok("1,654,000 PEPE, not 1.654e+06; 0.17 HYPE and 58 ENA as before",
   om._c511_q(-1654000.0) == '-1,654,000' and om._c511_q(0.17) == '+0.17' and om._c511_q(58.0) == '+58')
ok("  used for both numbers of the fill line", src.count('_c511_q(qty)') == 1 and src.count('holding {_c511_q(nq)}') == 1)

print("\n6. THE PAGE (Chromium)")


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
        sub = pg.inner_text('#sub'); run_ = pg.inner_text('#running')
        br.close()
    ok("the header: '... up N min · daily book, next rebalance 00:05 UTC', not '0 scans · 0 pair looks'",
       'daily book, next rebalance 00:05 UTC' in sub and 'scans' not in sub, sub)
    ok("'OFF the old intraday scanner (139 trades, 44W 95L before the 29 Sep 2026 fresh start; lost after fees)'",
       '139 trades, 44W 95L before the 29 Sep 2026 fresh start; lost after fees' in run_, run_)
    ok("  and PAPER lists no separate K4 shadow", 'K4 sizing shadow' not in run_ and 'rule tournament' in run_, run_)
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
ok("version C511 or later", int(om._OMEGA_VERSION[1:4]) >= 511)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
