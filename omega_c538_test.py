#!/usr/bin/env python3
"""C538: round 19's two near-misses run beside the daily rule as paper copies, scored on the page.

The operator, 6 Oct: "The every 8 hours, and the 3-day average close calls will be running parallel to
the current daily call .. i want the results of those too displayed at appropriate intervals in the
dashboard in simple lay man terms".
1. _c538_signal: the trailing gap up to any hour; at midnight with 7 days it IS the daily rule's signal.
2. Each test starts as an exact copy of the daily ledger, then follows its own rule: an 8-hour copy that
   makes no different decision ends the day equal to the daily ledger to the cent; the 3-day copy's
   different choice shows as exactly its extra fees.
3. At midnight the tests use the daily rule's own records and prices (no second fetch), and wait for it.
4. The scoreboard: once a day after the 06:00 IST runs; the page and the log say it in words.
"""
import os, io, sys, json, time, glob, random, datetime as _dt, shutil, types, socket, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c538_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c538-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om538', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C538: TWO TEST RULES BESIDE THE DAILY RULE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C538 or later", int(om._OMEGA_VERSION[1:]) >= 538)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
ok("on by default (C538_TESTS), paper only; the plan is untouched (C527_PLAN, C524_XVENUE_RUN_UTC 00:30)",
   cfg.C538_TESTS is True and tuple(cfg.C527_PLAN) == ('xvenue', 'reserve') and tuple(cfg.C524_XVENUE_RUN_UTC) == (0, 30))
DAY = 86400000
H = 3600000

print("\n1. THE SIGNAL UP TO ANY HOUR")
rnd = random.Random(538)
same = nn = 0
for trial in range(300):
    iv = rnd.choice((3600, 14400, 28800))
    cut = (1790000000 // 86400 + rnd.randint(0, 50)) * 86400
    lo = cut - 8 * 86400
    gap = rnd.randint(0, 9) if trial % 3 == 0 else None            # a day with no Delta record
    d = [dict(time=t, close=rnd.uniform(-0.05, 0.08)) for t in range(lo, cut, 3600)
         if gap is None or (t - lo) // 86400 != gap]
    b = [dict(fundingTime=t * 1000 + 5, fundingRate=str(rnd.uniform(-0.0004, 0.0006))) for t in range(lo, cut + 86400, 28800)]
    fD = om._c524_delta_daily(d, iv, lo, cut)
    fB = {}
    for x in b:
        t = int(x['fundingTime']) // 1000
        if t < cut:
            fB[t // 86400 * 86400] = fB.get(t // 86400 * 86400, 0.0) + float(x['fundingRate'])
    days = [cut - k * 86400 for k in range(7, 0, -1)]
    a1, a2 = om._c524_signal(fD, fB, days), om._c538_signal(d, b, iv, cut, 7)
    nn += 1
    same += (a1 is None and a2 is None) or (a1 is not None and a2 is not None and abs(a1 - a2) < 1e-12)
ok("at midnight over 7 days it equals the daily rule's signal: 300 random coins, every interval, missing days",
   same == nn, f"{same}/{nn}")
d = [dict(time=t, close=0.01) for t in range(0, 10 * 86400, 3600)]
b = [dict(fundingTime=t * 1000, fundingRate='0.0001') for t in range(0, 10 * 86400, 28800)]
cut8 = 9 * 86400 + 8 * 3600
ok("at 08:00 UTC over 3 days: (Delta 18 x 0.01% - Binance 9 x 0.01%) / 3 x 365, settlements before the cut only",
   abs(om._c538_signal(d, b, 14400, cut8, 3) - (18 * 0.0001 - 9 * 0.0001) / 3 * 365) < 1e-12
   and om._c538_signal(d, b, 14400, 30 * 86400, 3) is None)

print("\n2. COPIES OF THE DAILY LEDGER, EACH WITH ONE CHANGE")
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C531_XV_REBALANCE = False
D0 = (int(time.time() * 1000) // DAY - 3) * DAY
D0s = D0 // 1000


def rate(k, t):
    if k == 'HOT':
        return 0.10                                                    # wide on every window
    if k == 'FADE':
        return 0.03 if t < D0s - 3 * 86400 else 0.0                    # wide 4+ days ago, nothing since
    if k == 'RISE':
        return 0.02 if t >= D0s - 3 * 86400 else 0.0                   # nothing until 3 days ago
    return 0.01


CALLS = {'d': 0, 'b': 0}


class FakeDelta:
    def __init__(s):
        s.c = {'HOT': (1.0, 2.0), 'FADE': (1.0, 1.0), 'RISE': (1.0, 1.0)}
        for j in range(20):
            s.c[f'ONLYD{j:02d}'] = (1.0, 1.0)
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value=str(v[0]), taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k, v in s.c.items()]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(v[1])) for k, v in s.c.items()]
        if path == '/v2/history/candles':
            CALLS['d'] += 1
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=rate(k, t)) for t in range(first, en + 1, 3600)]
        return None


fdl = FakeDelta()
om._c521_get = fdl


def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        CALLS['b'] += 1
        lo = params['startTime']
        return [dict(fundingTime=t, fundingRate='0.0001') for t in range(-(-lo // (8 * H)) * 8 * H, lo + 9 * DAY, 8 * H)]
    return None


om._c516_bn_get = fake_bn
om._c532_pi42_coins = lambda: {'HOT', 'FADE', 'RISE', 'BTC'}
NOW = [0.0]


class _T:
    def __getattr__(s, k):
        return getattr(time, k)
    def time(s):
        return NOW[0]


om.time = _T()
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v[1], ask=v[1], last=v[1], fr=0.0, vol=1e8) for k, v in fdl.c.items() if not k.startswith('ONLYD')}
xe.refresh_marks = lambda force=False: True
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
x = om.C524CrossVenue(xb); x.reset(); xb.c524x = x
NOW[0] = (D0 + 30 * 60000) / 1000
x.run(now_ms=D0 + 30 * 60000); x.save()
ok("the daily rule at 06:00 IST (00:30 UTC): HOT and FADE (7-day gaps 208% and 27%/yr); RISE's 8%/yr is too small",
   set(x.pairs) == {'HOT', 'FADE'}, str({c: round(p['s_entry'], 3) for c, p in x.pairs.items()}))
ok("  and it keeps its records and prices for the tests (cut = midnight)", x._got and x._got['cut'] == D0)
xb.c538 = [om.C538TestRule(xb, 'f8'), om.C538TestRule(xb, 'w3')]
F8, W3 = xb.c538
for t in xb.c538:
    t.reset()
LOG.clear()
NOW[0] = (D0 + 40 * 60000) / 1000
F8.tick(); W3.tick()
ok("each test starts as an exact copy: the same pairs, quantities, prices and equity",
   all(t.pairs == x.pairs and t.eq == x.eq and t.start_equity == x.start_equity and t.base == x.eq + x.transfer_fees
       and t.since == x.last_run for t in (F8, W3)))
ok("  and its first decision is the next one (the copy is the daily rule's 00:30 decision)",
   F8.last_slot == D0 and W3.last_slot == D0 and not F8.slots and not W3.slots)
cp = [m for _, m in LOG if 'C538 test' in m and 'starts as a copy' in m]
ok("  the log says so in words, for each", len(cp) == 2 and 'Checks every 8 hours' in cp[0] and 'not your plan' in cp[0]
   and 'decides at 06:00, 14:00 and 22:00 IST' in cp[0] and 'judges each gap on its last 3 days' in cp[1]
   and 'compared every day after the 06:00 IST run' in cp[0], cp[0][:200] if cp else '')

c0 = dict(CALLS)
NOW[0] = (D0 + 8 * H + 31 * 60000) / 1000
F8.tick(); W3.tick()
nf8 = CALLS['d'] - c0['d']
hot = F8.pairs['HOT']
ok("14:00 IST: the 8-hour test decides (W3 waits for tomorrow); nothing changes, and it books the one Delta rent "
   "since 06:00 IST (04:00 UTC): 25 contracts x $2 x 0.10% = +$0.05",
   F8.last_slot == D0 + 8 * H and W3.last_slot == D0 and set(F8.pairs) == {'HOT', 'FADE'}
   and abs(hot['funding'] - 0.05) < 1e-12 and abs(F8.eq - x.eq - 0.05) < 1e-9, f"{hot['funding']:.6f}")
ok("  it fetches its own records then, only for coins it may hold (Pi42's list): 3 of 23",
   nf8 == 3 and CALLS['b'] - c0['b'] == 3, f"{nf8} Delta, {CALLS['b'] - c0['b']} Binance")
NOW[0] = (D0 + 16 * H + 31 * 60000) / 1000
F8.tick(); W3.tick()
ok("22:00 IST: the 8-hour test again; W3 still waits", F8.last_slot == D0 + 16 * H and W3.last_slot == D0 and len(F8.slots) == 2)
NOW[0] = (D0 + DAY + 31 * 60000) / 1000
F8._tick_at = W3._tick_at = 0.0
F8.tick(); W3.tick()
ok("06:00 IST next day: both tests wait until the daily rule has run (they share its data and prices)",
   F8.last_slot == D0 + 16 * H and W3.last_slot == D0)
x.run(now_ms=D0 + DAY + 30 * 60000); x.save()
c1 = dict(CALLS)
NOW[0] += 60
F8.tick(); W3.tick()
ok("  then both run on the daily rule's own records and prices: no request to either exchange",
   CALLS == c1 and F8.last_slot == D0 + DAY and W3.last_slot == D0 + DAY, f"{CALLS} vs {c1}")
ok("  and the shared records are freed once both have them", x._got is None)
ok("the daily rule keeps HOT and FADE (FADE's 7-day gap 17%/yr, above the 10% exit)", set(x.pairs) == {'HOT', 'FADE'})
ok("the 8-hour test made no different decision, so after three bookings it equals the daily ledger to the cent",
   set(F8.pairs) == set(x.pairs) and abs(F8.eq - x.eq) < 1e-9 and abs(F8.funding - x.funding) < 1e-9,
   f"{F8.eq:.6f} vs {x.eq:.6f}")
cb, cd = x.cost_b(), om._C524_COST_D
ok("the 3-day test sees FADE's last 3 days (no rent: -11%/yr, the gap changed side) and swaps it for RISE (+33%/yr)",
   set(W3.pairs) == {'HOT', 'RISE'} and W3.closed and W3.closed[-1]['coin'] == 'FADE'
   and W3.closed[-1]['why'] == 'spread changed sign' and abs(W3.pairs['RISE']['s_entry'] - 0.3285) < 1e-3,
   str(W3.closed[-1:]))
me, mm = W3.score()
ok("  its score = the daily rule's minus exactly the swap's fees: 2 x $50 x (0.138% + 0.079%)",
   abs((me - mm) + 2 * 50.0 * (cb + cd)) < 1e-9, f"{me - mm:.6f}")
s8, s3 = F8.test_status(), W3.test_status()
day1 = _dt.datetime.utcfromtimestamp((D0 + DAY) / 1000).strftime('%Y-%m-%d')
ok("the scoreboard: one row a day, written at the midnight run (none at 14:00/22:00 IST)",
   list(F8.snaps) == [day1] and list(W3.snaps) == [day1] and s3['days'] == 1 and s3['at'] == day1)
ok("  with the daily rule's result over the same period beside it",
   abs(s3['main'] - round(mm, 2)) < 1e-9 and abs(s3['diff'] - round(s3['me'] - s3['main'], 2)) < 1e-9 and s8['diff'] == 0.0,
   json.dumps({k: s3[k] for k in ('me', 'main', 'diff', 'n', 'same')}))
ok("  and how many of its pairs are the same as the daily rule's", s3['same'] == 1 and s8['same'] == 2)
ok("history's expectation travels with it (per month on $1,000, share of months ahead)",
   (s8['month'], s8['ahead'], s3['month'], s3['ahead']) == (2.90, 82, 6.40, 62))
lg_ = [m for _, m in LOG if 'C538 test' in m and ' IST: ' in m]
ok("each decision is logged in words; the midnight one carries the score since the copy",
   any('14:00 IST' in m and 'the same as yours' in m for m in lg_)
   and any('06:00 IST' in m and 'Uses a 3-day average' in m and 'since ' in m and 'your daily rule' in m and 'behind by $0.22' in m
           and 'out FADE (spread changed sign)' in m for m in lg_), (lg_[-1][:260] if lg_ else ''))
ok("tests never move money between the venues (that costs both ledgers the same and is left out)",
   F8.even_out(_dt.datetime.utcnow()) is None and 'transfer_fees - self.base' in SRC)

print("\n3. RESTARTS, ALLOCATION CHANGES, OFF")
F8b = om.C538TestRule(xb, 'f8')
ok("a restart keeps the copy's base, its date, the last decision and the scoreboard",
   F8b.base == F8.base and F8b.since == F8.since and F8b.last_slot == F8.last_slot and F8b.snaps == F8.snaps
   and F8b.pairs == F8.pairs)
cfg.C524_XVENUE_EQUITY = 600.0
LOG.clear()
W3b = om.C538TestRule(xb, 'w3')
ok("the plan's amount changes: the test starts again as a fresh copy after the daily rule's next run, and says so",
   not W3b.start_equity and not W3b.pairs and any('restarts as a copy' in m for _, m in LOG))
cfg.C524_XVENUE_EQUITY = 500.0
cfg.C538_TESTS = False
ok("C538_TESTS = False: off (no runs; the page hides the section)", not F8.active() and F8.test_status()['mode'] == 'off')
cfg.C538_TESTS = True
ok("Start fresh resets them too; the plan's total never counts them",
   "for _t538 in getattr(bot, 'c538', None) or []:" in SRC and 'c538' not in SRC[SRC.index('def _c527_total'):SRC.index('def _c527_total') + 6000])
ok("the logs push carries their files (c538_f8.json, c538_w3.json)",
   'c538_f8.json' in open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read())
ok("ticked every loop, after the daily rule (which shares its data with them)",
   "for _t538 in self.c538:               # C538: the test rules, after the daily rule" in SRC
   and SRC.index('self.c524x, self.c530p,\n') < SRC.index('for _t538 in self.c538:'))
ok("the 8-minute status block has one TESTS line in words",
   "self._pack('TESTS'" in SRC and "'scored from 06:00 IST'" in SRC and s3['short'] == '3-day avg' and s8['short'] == 'every 8 h')
om.time = time

print("\n4. THE PAGE")
x0 = json.load(open(os.path.join(SNAP, 'c524_xvenue.json')))
for f in glob.glob(os.path.join(BASE, 'c5*.json')):
    os.remove(f)
for f in glob.glob(os.path.join(SNAP, 'c*.json')):
    shutil.copy(f, BASE)
cfg.C524_XVENUE_EQUITY = 1000.0; cfg.C531_XV_REBALANCE = True
om._c532_pi42_coins = lambda: None
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
for a, k in (('c501v', 'C501Savings'), ('c501s', 'C501Spot'), ('c490', 'C490Carry'), ('c521d', 'C521Delta'), ('c521b', 'C521Bfusd'),
             ('c524x', 'C524CrossVenue'), ('c530p', 'C530Pendle'), ('c489', 'C489Shadow'), ('c501k', 'C501Allostatic'),
             ('c510t', 'C510Tournament')):
    setattr(bot, a, getattr(om, k)(bot))
bot.c538 = [om.C538TestRule(bot, 'f8'), om.C538TestRule(bot, 'w3')]
xv, de = bot.c524x, bot.c521d
NOWs = time.time()
e.marks = {om.C488Engine._ccxt(s): dict(bid=b, ask=a, last=(b + a) / 2, fr=0.0, vol=1e9) for s, (b, a) in PX['perp'].items()}
e._marks_at = NOWs
bot.c501s.bk = {s: (b, a) for s, (b, a) in PX['spot'].items()}; bot.c501s._book_at = NOWs
de.marks = {s: dict(mark=m_, bid=b or m_, ask=a or m_, fr=0.0) for s, (m_, b, a) in PX['delta'].items()}
de._marks_at = NOWs
e.refresh_marks = lambda force=False: True
de.refresh_marks = lambda force=False: True
bot.c501s.book = lambda force=False: bot.c501s.bk
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pf, c488=e, c501s=bot.c501s, c501v=bot.c501v, c501k=bot.c501k,
                             c489=bot.c489, c490=bot.c490, c510t=bot.c510t, c521b=bot.c521b, c521d=de, c524x=xv,
                             c530p=bot.c530p, c538=bot.c538,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bot.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bot._c482_risk_guard, _c504_data_health=bot._c504_data_health)


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


def page():
    port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda e_: errs.append(str(e_)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        G = dict(test=pg.inner_text('#s-test'), next=pg.inner_text('#s-next'),
                 hidden=pg.evaluate("document.getElementById('s-test').closest('section').hidden"),
                 rows=pg.evaluate("document.querySelectorAll('#s-test table.pairs tr').length"),
                 W=pg.evaluate('document.documentElement.scrollWidth'))
        br.close()
    return G, errs


try:
    allerr = []
    for t in bot.c538:
        t.reset(save=False)
    G0, er = page(); allerr += er
    ok("before the copy: one line saying when the two tests start, and why", not G0['hidden']
       and 'Starts after your plan' in G0['test'] and 'two copies of your plan' in G0['test'], G0['test'][:160])
    f8, w3 = bot.c538
    for t in bot.c538:
        t.copy_main()
    G1, er = page(); allerr += er
    ok("copied, before the first score: 'First score after the next 06:00 IST run'",
       'First score after the next 06:00 IST run' in G1['test'] and 'Nothing here is your money' in G1['test'], G1['test'][:200])
    snaps = {'2026-10-07': (0.40, 0.31), '2026-10-08': (1.10, 1.30), '2026-10-09': (1.95, 1.61), '2026-10-10': (2.60, 2.05),
             '2026-10-11': (3.20, 2.70), '2026-10-12': (3.70, 3.10), '2026-10-13': (4.50, 3.65), '2026-10-14': (5.40, 4.15)}
    f8.since = w3.since = '2026-10-06'
    f8.snaps = {k: dict(me=a, main=b, n=10, same=9) for k, (a, b) in snaps.items()}
    w3.snaps = {k: dict(me=round(b - 0.9, 2), main=b, n=10, same=7) for k, (a, b) in snaps.items()}
    f8.slots = [dict(at=0, cut=int(_dt.datetime(2026, 10, 14, 8, tzinfo=_dt.timezone.utc).timestamp() * 1000), day=0.1,
                     out=['FADE (spread under 10%/yr)'], inn=['RISE short Delta/long Pi42 +35%/yr'], n=10)]
    G2, er = page(); allerr += er
    T = G2['test']
    ok("the scoreboard in words: your rule, then each test, its result and ahead/behind yours",
       G2['rows'] == 4 and 'Your rule: once a day' in T and '+$4.15' in T and 'Checks every 8 hours' in T and '+$5.40' in T
       and 'ahead $1.25' in T and 'Uses a 3-day average' in T and '+$3.25' in T and 'behind $0.90' in T, T[:400])
    ok("  when it was scored and how often: 'score as of 14 Oct, 06:00 IST (8 days); updated every day after that run'",
       'score as of 14 Oct, 06:00 IST (8 days)' in T and 'updated every day after that run' in T)
    ok("  what each test does, its last decision in IST and its pairs vs yours now (a fresh copy: all 10)",
       'decides at 06:00, 14:00 and 22:00 IST instead of once a day' in T and 'Last decision 14 Oct, 14:00 IST: closed FADE; opened RISE' in T
       and T.count('10 pairs, 10 the same as yours') == 2 and 'judges each gap on its last 3 days instead of 7' in T, T[T.find('Checks every 8 hours \u2014'):][:300])
    ok("  the last 7 days, and how to read it (history's per-month figure, 2 December, your rule stays)",
       'Last 7 days: ahead $1.16' in T and 'Last 7 days: level' in T and 'How to read it: a few days mean little' in T
       and 'about $2.90 a month (ahead in 8 months out of 10)' in T and '$6.40 a month, but only in 6 months out of 10' in T
       and '2 December' in T and 'Until then your rule stays' in T, T[-420:])
    ok("  no codes or jargon (C5xx, UTC, shadow, variant, leverage)",
       not any(w in T for w in ('C53', 'C52', 'UTC', 'shadow', 'variant', 'leverage', 'F8', 'W3')))
    cfg.C538_TESTS = False
    G3, er = page(); allerr += er
    ok("tests off: the section is hidden", G3['hidden'] is True)
    cfg.C538_TESTS = True
    ok("412 px wide (a phone): nothing overflows", max(G0['W'], G1['W'], G2['W']) <= 412, str((G0['W'], G1['W'], G2['W'])))
    ok("no JavaScript errors", not allerr, '; '.join(allerr)[:300])
except Exception as ex:
    import traceback; traceback.print_exc()
    ok("page check ran", False, f"{type(ex).__name__}: {ex}")

print("\n" + "=" * 66)
print(f"C538 TEST: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
shutil.rmtree(BASE, ignore_errors=True)
sys.exit(1 if fails else 0)
