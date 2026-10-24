#!/usr/bin/env python3
"""C536: the page says when the last daily run happened and what it did.

The operator, 6 Oct 09:22 IST: "there was no daily run today .. is it expected?" -- it ran at 06:00:27 IST
(+$1.09: rent +$1.52, prices -$0.43, nothing to change), but nothing on the page said so.
1. C524CrossVenue.run() keeps the day's result in its parts (info: day_pnl, day_fund, day_price, day_cost, moved).
2. "What happens next" opens with "Last daily run: 6 Oct, 06:00 IST -- done: ..." in words.
3. The legacy 8-minute POSITION SUMMARY no longer prints the book's cash as "Equity" beside the marked EQUITY row.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c536_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c536-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om536', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C536: THE LAST DAILY RUN, IN WORDS"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C536 or later", int(om._OMEGA_VERSION[1:]) >= 536)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
x0 = json.load(open(os.path.join(SNAP, 'c524_xvenue.json')))
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
CALLS = []
PI42 = {'answer': {'KAITO', 'FARTCOIN', 'IO', 'TST', 'BEAT', 'LIT', 'STRK'} | {'C%02d' % i for i in range(40)}}


def _fake_pi42():
    CALLS.append(time.time())
    return PI42['answer']


om._c532_pi42_coins = _fake_pi42
L = lambda f: json.load(open(os.path.join(SNAP, f + '.json')))
PX = L('prices'); bk0 = L('c488_book')
pf = om.Portfolio(cfg)
cash = bk0['born']['eq'] + sum(c['pnl'] for c in bk0['closed']) + sum(p['funding'] - p['fees'] + p['realized'] for p in bk0['book'].values())
pf.equity = pf.available_balance = cash
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0, 'month_used': 0.0,
                                                      'day_cap': 25.0, 'day_used': 0.0, 'halt': ''},
                            _c504_data_health=lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []})
e = om.C488Engine(bot); bot.c488 = e; pf._c488 = e; e.load()
pf.get_live_equity = lambda ex: pf.equity + e.unrealized()
pf.session_start_equity = 500.0; pf.positions = om.PositionsManager()
LOG.clear()
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
xv = bot.c524x; de = bot.c521d
xv = bot.c524x; de = bot.c521d
NOW = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOW
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOW
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOW
T = om._c527_total(bot, now=NOW)
R = {r['key']: r for r in T['rows']}
st = xv.status()
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv,
                             c530p=bot.c530p,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk



def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


def page(open_all=False):
    port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        G = {k: pg.inner_text('#' + k) for k in ('sub', 's-money', 's-acc', 's-pairs', 's-next', 'moresum')}
        G['simple_hidden'] = pg.evaluate("document.getElementById('simple').hidden")
        G['more_open'] = pg.evaluate("document.getElementById('more').open")
        G['ctl_open'] = pg.evaluate("document.getElementById('ctl').open")
        G['log_open'] = pg.evaluate("document.getElementById('logd').open")
        G['rows'] = pg.evaluate("document.querySelectorAll('#s-pairs table.pairs tr').length")
        G['tile_visible'] = pg.is_visible('#eqk')
        G['W'] = pg.evaluate('document.documentElement.scrollWidth')
        br.close()
    return G, errs



print("\n1. THE DAILY RUN KEEPS ITS PARTS")
i0 = SRC.index('    def run(self, now_ms=None):', SRC.index('class C524CrossVenue')); i1 = SRC.index('    def tick(self):', i0)
RUN = SRC[i0:i1]
ok("every change to the day's result has its part: rent, prices, fees (exits and entries), the transfer fee",
   RUN.count('day_pnl -= cost; d_cost += cost') == 2 and 'd_price += pr; d_fund += fu_d + fu_b' in RUN
   and "day_pnl -= tr['fee']" in RUN and "moved=(dict(amt=tr['amt'], frm=tr['frm'], to=tr['to'], fee=tr['fee'])" in RUN)
ok("  and the record carries them (day_pnl, day_fund, day_price, day_cost, moved)",
   all(k in RUN for k in ('day_pnl=round(day_pnl, 2)', 'day_fund=round(d_fund, 2)', 'day_price=round(d_price, 2)', 'day_cost=round(d_cost, 2)')))
ok("the legacy 8-minute summary: the book's marked equity, split into cash and open (no bare 'Equity: cash')",
   'marked (the Binance book, an experiment) = "' in SRC and 'f"cash ${stats[\'equity\']:.2f} + open ${_u536:+.2f}")' in SRC)

print("\n2. THE PAGE SAYS IT")
AT = int(__import__('datetime').datetime(2026, 10, 6, 0, 30, 27, tzinfo=__import__('datetime').timezone.utc).timestamp() * 1000)
CASES = [
    ("a quiet day (6 Oct): rent added, nothing changed, nothing moved",
     dict(at=AT, entered=[], exited=[], day_pnl=1.09, day_fund=1.52, day_price=-0.43, day_cost=0.0, moved=None),
     ['Last daily run: 6 Oct, 06:00 IST', 'done: +$1.09', 'rent +$1.52', 'price moves -$0.43', 'No pairs needed changing.', 'No money needed moving.']),
    ("a busy day (5 Oct): pairs closed and opened, money moved",
     dict(at=AT - 86400000, entered=['TST short Delta/long Pi42 +101%/yr', 'BEAT short Delta/long Pi42 +100%/yr'],
          exited=['ORDER (not on Pi42)', 'AIN (not on Pi42)'], day_pnl=-4.66, day_fund=0.55, day_price=-0.83, day_cost=3.39,
          moved=dict(amt=163.07, frm='Pi42', to='Delta', fee=1.0)),
     ['Last daily run: 5 Oct, 06:00 IST', 'done: -$4.66', 'fees -$3.39', 'moving money -$1.00', 'Closed ORDER, AIN', 'opened TST, BEAT',
      'Moved $163.07 from Pi42 to Delta.']),
    ("an older record without the parts: when, and the changes, nothing invented",
     dict(at=AT, entered=[], exited=[]),
     ['Last daily run: 6 Oct, 06:00 IST', 'done.', 'No pairs needed changing.']),
]
try:
    allerr = []
    for name, info, want in CASES:
        xv.info = dict(info)
        G, errs = page(); allerr += errs
        n_ = G['s-next']
        miss = [w for w in want if w not in n_]
        if name.startswith('an older'):
            miss += [w for w in ('No money needed moving', 'rent ') if w in n_]
        ok(name, not miss, (str(miss) + ' | ' + n_.replace('\n', ' | '))[:400])
    ok("the next run still follows: 'Next daily run: 06:00 IST'", 'Next daily run: 06:00 IST' in n_)
    ok("no JavaScript errors", not allerr, str(allerr))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
