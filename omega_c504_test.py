#!/usr/bin/env python3
"""C504: the data watchdog -- every feed against its own schedule, on every block.

28 Sep 2026, checked by hand from three days of server logs before this was
built: the intraday shadow scored every hour from C495 on (36-39 coins); the
book booked funding at every 8h settlement and, for PUMP, every 4h one, to the
cent against Bitget; the rebalance, carry and spot runs were on time; no fetch
failed. C504 makes the bot check this itself.

1. ALL ON TIME: prices, funding, the rebalance, K4, the shadow hour, carry, the
   spot pot and its prices, Savings -- ok, with what it checked.
2. EACH FEED LATE, ONE AT A TIME: named in words; a daily run is late only an
   hour after its time (not before it is due).
3. THE STATUS BLOCK carries a DATA row; the 8-minute warning is said when the
   set of late feeds changes, repeated hourly, and its recovery once; both reach
   the session log.
4. THE PAGE (Chromium): the scanning tile says "data on time" or "DATA LATE".
5. THE SHADOW'S GATE is saved with its state, so a restart does not paint
   "gate shut" over an hour the log recorded as "gate OPEN".
"""
import os, sys, io, time, glob, socket, types, logging, contextlib, importlib.util, tempfile
import datetime as dt
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c504_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c504-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om504', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C504: EVERY FEED AGAINST ITS OWN SCHEDULE"); print("=" * 66)

NOW = dt.datetime(2026, 9, 28, 9, 30, tzinfo=dt.timezone.utc).timestamp()
TODAY, YDAY = '2026-09-28', '2026-09-27'
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = 15.0; cfg.C488_ENGINE = 'portfolio'
om._c467_cfg_ref[0] = cfg
pf = om.Portfolio(cfg); pf.equity = 250.39; pf.available_balance = 226.45; pf.session_start_equity = 250.39
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 15.0, 'month_eq0': 252.81, 'month_budget': 37.92,
                                                      'month_used': 2.42, 'day_cap': 9.0, 'day_used': 0.0, 'halt': ''})
e = om.C488Engine(bot); e.reset(); bot.c488 = e; pf._c488 = e
e.marks = {'ETH/USDT:USDT': dict(bid=1999.0, ask=2001.0, last=2000.0, fr=0.0001, vol=9e9)}
e.book['ETH/USDT:USDT'] = dict(qty=0.0132, avg=2010.0, fees=0.0, funding=0.0, realized=0.0, opened=NOW - 86400)
bot.c489 = om.C489Shadow(bot); bot.c490 = om.C490Carry(bot)
bot.c501s = om.C501Spot(bot); bot.c501v = om.C501Savings(bot); bot.c501k = om.C501Allostatic(bot)
H = lambda now=None: om.TradingBot._c504_data_health(bot, NOW if now is None else now)


def on_time():
    e._marks_at = NOW - 12
    e.fund_next = {'ETH/USDT:USDT': int((NOW // 28800 + 1) * 28800 * 1000)}      # the next 8h settlement
    e.last_rebal = TODAY
    e._last_M = (TODAY, 20, None)                                                # C506: this process ran it
    bot.c501k.last_obs = TODAY
    bot.c489.last_hour = int(NOW // 3600 * 3600 * 1000)                          # 09:00 scored
    bot.c490.last_run = TODAY
    bot.c501s.last_run = TODAY; bot.c501s.pos = {'BTCUSDT': dict(qty=0.0001, avg=83000.0, opened=NOW, realised=0.0)}
    bot.c501s._book_at = NOW - 30
    bot.c501v._tick_at = NOW - 20


# ─────────────────────────────────────────────────────────────────────────────
print("\n1. ALL ON TIME")
on_time(); h = H()
ok("ok, with every feed it checked", h['ok'] and h['late'] == []
   and h['bits'] == ['prices 12s', 'funding booked', 'book today', 'shadow 09:00', 'carry today', 'spot pot today'],
   str(h))

# ─────────────────────────────────────────────────────────────────────────────
print("\n2. EACH FEED LATE, ONE AT A TIME")
cases = [
    ("book prices 7 min old", lambda: setattr(e, '_marks_at', NOW - 420), None,
     "book prices 7 min old (every 30 s expected)"),
    ("funding 20 min after a settlement", lambda: e.fund_next.update({'ETH/USDT:USDT': int((NOW - 1200) * 1000)}),
     None, "funding not booked for ETH"),
    ("the rebalance missing at 09:30", lambda: setattr(e, 'last_rebal', YDAY), None,
     "book rebalance not run today (due 00:05 UTC)"),
    ("K4 missing on a day the book ran", lambda: setattr(bot.c501k, 'last_obs', YDAY), None,
     "K4 shadow missed today's rebalance"),
    ("no shadow hour for 2h", lambda: setattr(bot.c489, 'last_hour', int((NOW // 3600 - 2) * 3600 * 1000)), None,
     "intraday shadow: no hour scored in 90 min"),
    ("the carry ledger missing", lambda: setattr(bot.c490, 'last_run', YDAY), None,
     "carry ledger not run today (due 00:10 UTC)"),
    ("the spot pot missing", lambda: setattr(bot.c501s, 'last_run', YDAY), None,
     "spot pot not run today (due 00:20 UTC)"),
    ("spot prices 10 min old while it holds", lambda: setattr(bot.c501s, '_book_at', NOW - 600), None,
     "spot prices 10 min old"),
    ("Savings without a tick for 10 min", lambda: setattr(bot.c501v, '_tick_at', NOW - 600), None,
     "Savings ledger 10 min without a tick"),
]
for name, spoil, when, want in cases:
    on_time(); spoil(); h = H(when)
    ok(f"{name}: '{want}'", not h['ok'] and h['late'] == [want], str(h['late']))
on_time(); e.last_rebal = YDAY; bot.c490.last_run = YDAY; bot.c501s.last_run = YDAY
early = dt.datetime(2026, 9, 28, 0, 50, tzinfo=dt.timezone.utc).timestamp()
e._marks_at = early - 5; bot.c489.last_hour = int(early // 3600 * 3600 * 1000); bot.c501s._book_at = early - 5
bot.c501v._tick_at = early - 5; e.fund_next = {'ETH/USDT:USDT': int((early // 28800 + 1) * 28800 * 1000)}
h = H(early)
ok("00:50 UTC, before an hour's grace: the daily runs are not yet late", h['ok'], str(h['late']))
on_time(); bot.c501s.pos = {}; bot.c501s._book_at = NOW - 3600
ok("an empty spot pot needs no spot prices", H()['ok'])
on_time(); cfg.PAPER_MODE = False; e.fund_next = {'ETH/USDT:USDT': int((NOW - 1200) * 1000)}
ok("live: funding comes from Bitget's bills, so the paper accrual is not checked", H()['ok'] or
   'funding not booked for ETH' not in H()['late'])
cfg.PAPER_MODE = True

# ─────────────────────────────────────────────────────────────────────────────
print("\n3. THE STATUS BLOCK AND THE WARNING")
bot._c504_data_health = lambda now=None: om.TradingBot._c504_data_health(bot, NOW if now is None else now)
on_time()
rep = om._C462Report(os.path.join(BASE, 'r.log')); rows = []
rep._emit = lambda line: rows.append(str(line)); rep.status(bot)
d = ' '.join(r for r in rows if r.strip().startswith('DATA') or (rows.index(r) > 0 and rows[rows.index(r) - 1].strip().startswith('DATA')))
ok("DATA row: 'on time' and what was checked", 'on time' in d and 'prices 12s' in d, d)
e._marks_at = NOW - 420
rows.clear(); rep.status(bot)
d = ' '.join(r for r in rows if 'DATA' in r or 'LATE' in r or 'book prices' in r)
ok("DATA row when late: 'LATE book prices 7 min old'", 'LATE' in d and 'book prices 7 min old' in d, d)
LOG.clear(); bot._c504_said = ''; bot._c504_said_at = 0.0


def W(now, stale_prices=True):
    # everything else keeps ticking; only the book's prices stop at NOW - 420
    bot.c489.last_hour = int(now // 3600 * 3600 * 1000); bot.c501s._book_at = now - 5; bot.c501v._tick_at = now - 5
    e.fund_next = {'ETH/USDT:USDT': int((now // 28800 + 1) * 28800 * 1000)}
    e._marks_at = (NOW - 420) if stale_prices else now - 5
    om.TradingBot._c504_warn(bot, now)


W(NOW); W(NOW + 480); W(NOW + 3700)
warn = [m for lv, m in LOG if lv == logging.WARNING and 'C504 DATA LATE' in m]
ok("the warning: once when the prices go stale, silent 8 min later (same feed, older), again after an hour",
   len(warn) == 2 and all('book prices' in m and 'spot' not in m for m in warn), str(warn))
LOG.clear(); bot._c504_said = ''; bot._c504_said_at = 0.0
bot._c504_data_health = lambda now=None: {'ok': False, 'bits': [], 'late': ['book prices stale']}
om.TradingBot._c504_warn(bot, NOW); om.TradingBot._c504_warn(bot, NOW + 480); om.TradingBot._c504_warn(bot, NOW + 3700)
ok("  the same late set: said once, silent 8 min later, repeated after an hour",
   len([m for lv, m in LOG if lv == logging.WARNING]) == 2, str(LOG))
bot._c504_data_health = lambda now=None: om.TradingBot._c504_data_health(bot, NOW if now is None else now)
bot._c504_said = 'book prices'
LOG.clear(); W(NOW + 3710, stale_prices=False)
ok("the recovery is said once", [m for lv, m in LOG] == ['✅ C504 data: every feed back on time'], str(LOG))
F = om._C460ConsoleFilter()
rec = lambda m, lv: logging.LogRecord('OmegaV60', lv, __file__, 1, m, None, None)
ok("both reach the session log",
   F.filter(rec('⚠️ C504 DATA LATE: book prices 7 min old (every 30 s expected)', logging.WARNING))
   and F.filter(rec('✅ C504 data: every feed back on time', logging.INFO)))

# ─────────────────────────────────────────────────────────────────────────────
print("\n4. THE PAGE (Chromium)")
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
on_time()
pf.positions = om.PositionsManager(); pf.get_live_equity = lambda *a: pf.equity
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')),
                             exchange=types.SimpleNamespace(get_current_price=lambda s: None),
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard)
STATE = {'now': None}
fbot._c504_data_health = lambda now=None: om.TradingBot._c504_data_health(fbot, STATE['now'] or time.time())
real_now = time.time()
e._marks_at = real_now - 5; bot.c489.last_hour = int(real_now // 3600 * 3600 * 1000); bot.c501s._book_at = real_now - 5
bot.c501v._tick_at = real_now - 5; e.fund_next = {'ETH/USDT:USDT': int((real_now // 28800 + 1) * 28800 * 1000)}
today_real = dt.datetime.utcfromtimestamp(real_now).strftime('%Y-%m-%d')
e.last_rebal = bot.c490.last_run = bot.c501s.last_run = bot.c501k.last_obs = today_real
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = b.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        t_ok = pg.inner_text('#scans')
        e._marks_at = time.time() - 900
        pg.wait_for_timeout(6000)
        t_late = pg.inner_text('#scans')
        b.close()
    ok("scanning tile: 'next rebalance 00:05 UTC · data on time'", 'data on time' in t_ok, t_ok)
    ok("  and 'DATA LATE: book prices 15 min old …' when the prices stop", 'DATA LATE' in t_late
       and 'book prices' in t_late, t_late)
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n5. THE SHADOW'S GATE SURVIVES A RESTART")
bot.c489.gate_last = True; bot.c489.model_used = 'warm-up (14, no flow)'; bot.c489.save()
g2 = om.C489Shadow(bot)
ok("an hour logged 'gate OPEN' still reads open after a restart (28 Sep 09:00 UTC: 'shut' after the 14:46 restart)",
   g2.gate_last is True and g2.model_used == 'warm-up (14, no flow)')
bot.c489.gate_last = False; bot.c489.save()
ok("  and a shut gate stays shut", om.C489Shadow(bot).gate_last is False)
ok("version C504 or later", int(om._OMEGA_VERSION[1:4]) >= 504)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
