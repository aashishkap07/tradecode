#!/usr/bin/env python3
"""C535: the dashboard in plain English -- your money first, experiments folded away.

1. With a plan: the top is four plain sections (your money, your two accounts, your pairs, what happens
   next); experiments, controls and the log are folded; no internal codes or UTC times up there.
2. The two accounts' wording follows their health: healthy / getting low (< 65%) / move money now (< 50%).
3. Without a plan: the plain top hides and the old panels open by themselves, as before.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c535_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c535-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om535', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C535: THE DASHBOARD IN PLAIN ENGLISH"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C535 or later", int(om._OMEGA_VERSION[1:]) >= 535)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
cfg.C532_XV_VENUE = 'pi42'   # C542 made CoinDCX the default; this test checks the Pi42-era plan (still supported)
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


print("\n1. WITH A PLAN: FOUR PLAIN SECTIONS, THE REST FOLDED")
try:
    G, errs = page()
    T = om._c527_total(bot, now=NOW); pl = T['plan']
    ok("the plain top shows; experiments, controls and the log are folded (one tap away)",
       G['simple_hidden'] is False and not G['more_open'] and not G['ctl_open'] and not G['log_open'] and not G['tile_visible'])
    ok("the header in words: 'no real money moves · running … · prices up to date'",
       G['sub'].startswith('no real money moves \u00b7 running') and 'UTC' not in G['sub'], G['sub'])
    m = G['s-money']
    ok("your money: the value now, the change since $1,000.00, after tax, what it is in, the goal, paper",
       f"${pl['eq']:,.2f}" in m and 'since you started with $1,000.00' in m and 'after tax:' in m
       and 'all of it in the rent-gap trade (Delta vs Pi42)' in m and 'goal: +2% to +4% a month, after tax' in m
       and 'paper: no real money moves' in m, m.replace('\n', ' | '))
    a = G['s-acc']
    ok("your two accounts: Delta India and Pi42, money and % of the $500 each started with, and their health",
       'each started with $500.00' in a and 'Delta India' in a and 'Pi42' in a and a.count('%') >= 2
       and ('Healthy.' in a or 'Getting low' in a or 'Move money now' in a), a.replace('\n', ' | '))
    p_ = G['s-pairs']
    ok("your pairs: one row per pair, opposite bets on the two exchanges, the gap a year, the rent, the days",
       G['rows'] == len(xv.pairs) + 1 and 'gap/yr' in p_ and 'rent collected' in p_
       and all(('\u2193 down\t\u2191 up' in ln) or ('\u2191 up\t\u2193 down' in ln) for ln in p_.split('\n')[1:len(xv.pairs) + 1]),
       p_.split('\n')[:3])
    n_ = G['s-next']
    ok("what happens next: the daily run at 06:00 IST, the hourly check, live locked until March 2027",
       'Next daily run: 06:00 IST' in n_ and 'Every hour it checks both accounts' in n_ and 'Live trading is locked.' in n_
       and 'March 2027' in n_, n_.replace('\n', ' | '))
    ok("the folded part says what is in it: '(not your money: Binance book …)'",
       G['moresum'].startswith('(not your money: ') and 'Binance book' in G['moresum'], G['moresum'])
    top = ' '.join(G[k] for k in ('sub', 's-money', 's-acc', 's-pairs', 's-next'))
    bad = [w for w in ('C524', 'C527', 'C529', 'C531', 'C532', 'UTC', 'cross-venue', 'funding gap', 'portfolio', 'leverage', 'margin')
           if w in top]
    ok("no internal codes or jargon in the plain top (C5xx, UTC, cross-venue, leverage, margin …)", not bad, str(bad))
    ok("fits a phone (412 px, no sideways scroll); no JavaScript errors", G['W'] <= 412 and not errs, f"{G['W']} {errs}")

    print("\n2. THE ACCOUNTS' WORDS FOLLOW THEIR HEALTH")
    sd = dict(xv.side)
    xv.side = {'d': sd['d'] - 0.42 * 500.0, 'b': sd['b'] + 0.42 * 500.0}
    G2, e2 = page()
    ok("a side under 65%: 'Getting low: the Delta account is below 65% …'", 'Getting low: the Delta account is below 65%' in G2['s-acc'],
       G2['s-acc'].replace('\n', ' | '))
    xv.side = {'d': sd['d'] - 0.56 * 500.0, 'b': sd['b'] + 0.56 * 500.0}
    G3, e3 = page()
    ok("a side under 50%: 'Move money now: the Delta account is below half …'", 'Move money now: the Delta account is below half' in G3['s-acc'],
       G3['s-acc'].replace('\n', ' | '))
    xv.side = sd

    print("\n3. WITHOUT A PLAN: THE OLD PANELS, OPEN")
    cfg.C527_PLAN = ('none',)                       # nothing in the plan ('()' falls back to the default plan)
    G4, e4 = page()
    ok("no plan: the plain top hides and the panels open by themselves (as before C535)",
       G4['simple_hidden'] is True and G4['more_open'] is True and G4['tile_visible'], str({k: G4[k] for k in ('simple_hidden', 'more_open', 'tile_visible')}))
    ok("no JavaScript errors in any of them", not (e2 or e3 or e4), str(e2 + e3 + e4))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
