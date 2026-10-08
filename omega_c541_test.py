#!/usr/bin/env python3
"""C541: the plan's rent-gap trade with CoinDCX in Pi42's place, run beside it as a third paper copy.

The operator, 8 Oct: Pi42's trading gateway refuses every network (a 403 page, even on their phone), and
"while i wait for their reply, it would be better to look for another Indian rupee exchange".
Round 21 (research/c541_preregistration.md, c541_coindcx.txt) found CoinDCX: its pairs and its rent are
Binance's (191 of 191 coins on 8 Oct), its fee half Pi42's, and on history the same plan passed every bar.
1. CoinDCX's coin list from its public instrument list ('B-<coin>_USDT', INR margin), or None.
2. The copy: an exact copy of the daily ledger, then CoinDCX's coins and fee -- everything else the same;
   at midnight it uses the daily rule's own records and prices (no extra request).
3. On only while the plan is on Pi42 and C541_DCX_TEST; its list failing opens nothing new, in words.
4. The page: three copies, CoinDCX's line in plain words, 412 px, no JavaScript errors.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util, datetime as _dt
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c541_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c541-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om541', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C541: COINDCX IN PI42'S PLACE, A THIRD PAPER COPY"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C541 or later", int(om._OMEGA_VERSION[1:]) >= 541)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
ok("on by default (C541_DCX_TEST), CoinDCX's fee 0.05% (+ GST); the plan itself stays on Pi42",
   cfg.C541_DCX_TEST is True and cfg.C541_DCX_FEE == 0.0005 and cfg.C532_XV_VENUE == 'pi42' and cfg.C488_LIVE_OK is False)
DAY = 86400000
H = 3600000

print("\n1. COINDCX'S COIN LIST")
SEEN = []


class _R:
    def __init__(s, code, body):
        s.status_code, s._b = code, body
    def json(s):
        if isinstance(s._b, Exception):
            raise s._b
        return s._b


real_get = om.requests.get
BODY = [None]
def fake_get(url, params=None, timeout=None, **kw):
    SEEN.append((url, dict(params or {})))
    return BODY[0]
om.requests.get = fake_get
BODY[0] = _R(200, ['B-BTC_USDT', 'B-1000SHIB_USDT', 'B-ETH_USDT', 'X-ODD_USDT', 'B-SOL_INR', 7]
             + [f'B-C{j:02d}_USDT' for j in range(20)])
got = om._c541_coindcx_coins()
ok("its public list of INR-margin futures (no key): 'B-BTC_USDT' -> BTC, 'B-1000SHIB_USDT' -> 1000SHIB; others ignored",
   got is not None and {'BTC', '1000SHIB', 'ETH'} <= got and 'ODD' not in got and 'SOL' not in got and len(got) == 23
   and SEEN[-1][0] == 'https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments'
   and SEEN[-1][1] == {'margin_currency_short_name[]': 'INR'}, str(sorted(got or []))[:120])
BODY[0] = _R(200, ['B-BTC_USDT', 'B-ETH_USDT'])
a1 = om._c541_coindcx_coins()
BODY[0] = _R(403, '<html>')
a2 = om._c541_coindcx_coins()
BODY[0] = _R(200, ValueError('not json'))
a3 = om._c541_coindcx_coins()
ok("fewer than 20 coins, an error page or a broken answer: None (the last good list is kept)", a1 is None and a2 is None and a3 is None)
om.requests.get = real_get

print("\n2. THE COPY: COINDCX'S COINS AND FEE, EVERYTHING ELSE THE SAME")
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C531_XV_REBALANCE = False
D0 = (int(time.time() * 1000) // DAY - 3) * DAY
D0s = D0 // 1000


def rate(k, t):
    if k in ('HOT', 'DCXONLY'):
        return 0.10                                                    # wide on every window
    if k == 'FADE':
        return 0.03 if t < D0s - 3 * 86400 else 0.0
    return 0.01


CALLS = {'d': 0, 'b': 0}


class FakeDelta:
    def __init__(s):
        s.c = {'HOT': (1.0, 2.0), 'FADE': (1.0, 1.0), 'RISE': (1.0, 1.0), 'DCXONLY': (1.0, 2.0)}
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
DCX = [{'HOT', 'RISE', 'DCXONLY', 'BTC'}]
NDCX = [0]


def fake_dcx():
    NDCX[0] += 1
    return set(DCX[0]) if DCX[0] else None


om._c541_coindcx_coins = fake_dcx
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
ok("your plan (on Pi42) at 06:00 IST: HOT and FADE; DCXONLY's gap is as wide as HOT's but Pi42 does not list it",
   set(x.pairs) == {'HOT', 'FADE'} and x.v2() == 'Pi42', str(sorted(x.pairs)))
xb.c538 = [om.C538TestRule(xb, 'f8'), om.C538TestRule(xb, 'dx')]
F8, DX = xb.c538
for t in xb.c538:
    t.reset()
cb_p, cb_d, cd = x.cost_b(), DX.cost_b(), om._C524_COST_D
ok("the copy's second account is CoinDCX at its fee: 0.05% x 1.18 + 0.02% = 0.079% a side (Pi42's 0.138%); "
   "rent paid still carries GST, as in the study",
   DX.v2() == 'CoinDCX' and abs(cb_d - (0.0005 * 1.18 + 0.0002)) < 1e-15 and abs(cb_p - (0.0010 * 1.18 + 0.0002)) < 1e-15
   and DX.fgst(-1.0) == x.fgst(-1.0) == -1.18 and F8.v2() == 'Pi42' and F8.cost_b() == cb_p)
LOG.clear()
NOW[0] = (D0 + 40 * 60000) / 1000
F8.tick(); DX.tick()
ok("it starts as an exact copy of your plan's ledger: the same pairs, quantities, prices and equity",
   DX.pairs == x.pairs and DX.eq == x.eq and DX.start_equity == x.start_equity and DX.since == x.last_run
   and DX.base == x.eq + x.transfer_fees)
cp = [m for _, m in LOG if 'C538 test' in m and 'starts as a copy' in m and 'CoinDCX' in m]
ok("  the log says so in words", len(cp) == 1 and 'not your plan' in cp[0]
   and 'uses CoinDCX instead of Pi42 as the second account: its coins and its lower fee' in cp[0], cp[0][:220] if cp else '')
NOW[0] = (D0 + 8 * H + 31 * 60000) / 1000
F8.tick(); DX.tick()
ok("14:00 IST: the 8-hour copy decides; the CoinDCX copy, like your rule, waits for 06:00 IST",
   F8.last_slot == D0 + 8 * H and DX.last_slot == D0)
NOW[0] = (D0 + DAY + 31 * 60000) / 1000
F8._tick_at = DX._tick_at = 0.0
F8.tick(); DX.tick()
ok("06:00 IST next day: it waits until your daily rule has run (it shares its data and prices)", DX.last_slot == D0)
x.run(now_ms=D0 + DAY + 30 * 60000); x.save()
c1 = dict(CALLS)
fade_n = abs(DX.pairs['FADE']['d_qty']) * DX.pairs['FADE']['cv'] * 1.0
fee0 = DX.fees
LOG.clear()
NOW[0] += 60
F8.tick(); DX.tick()
ok("  then runs on your rule's own records and prices: no request to Delta or Binance",
   CALLS == c1 and DX.last_slot == D0 + DAY, f"{CALLS} vs {c1}")
ok("  and the shared records are freed once every copy has them", x._got is None)
ok("your plan keeps HOT and FADE (Pi42 lists both)", set(x.pairs) == {'HOT', 'FADE'})
ok("the CoinDCX copy closes FADE ('not on CoinDCX') and opens DCXONLY, which only CoinDCX lists",
   set(DX.pairs) == {'HOT', 'DCXONLY'} and DX.closed and DX.closed[-1]['coin'] == 'FADE'
   and DX.closed[-1]['why'] == 'not on CoinDCX', str(DX.closed[-1:]))
p = DX.pairs['DCXONLY']
nd = abs(p['d_qty']) * p['cv'] * p['d_px']
ok("  each at CoinDCX's fee on that leg and Delta's on the other: new fees = FADE out + DCXONLY in, x (0.079% + 0.079%)",
   abs((DX.fees - fee0) - (fade_n + nd) * (cb_d + cd)) < 1e-9 and abs(p['pnl'] + nd * (cb_d + cd)) < 1e-12,
   f"{DX.fees - fee0:.6f} vs {(fade_n + nd) * (cb_d + cd):.6f}")
ok("  its entry is logged against CoinDCX", any('DCXONLY short Delta/long CoinDCX' in m for _, m in LOG),
   ([m for _, m in LOG if 'CoinDCX' in m] or [''])[-1][:240])
s = DX.test_status()
ok("its scoreboard row: venue CoinDCX, CoinDCX's coin count, history's +$11.40 a month, ahead in 22 of 24 months",
   s['venue'] == 'CoinDCX' and s['coins'] == 4 and s['short'] == 'CoinDCX' and s['month'] == 11.40 and s['ahead'] == 92
   and s['days'] == 1 and s['same'] == 1 and F8.test_status()['coins'] is None, json.dumps({k: s[k] for k in ('venue', 'coins', 'me', 'main', 'diff', 'same')}))

print("\n3. ITS OWN FETCH, ITS LIST, ON AND OFF")
c2 = dict(CALLS)
x._got = None
with DX._lock:
    coins, got_, bm, dm, p42 = DX._inputs(D0 + 2 * DAY, D0 + 2 * DAY + 31 * 60000)
ok("without your rule's records (another hour), it fetches its own -- only coins CoinDCX lists, plus what it holds",
   sorted(coins) == ['DCXONLY', 'HOT', 'RISE'] and CALLS['d'] - c2['d'] == 3 and CALLS['b'] - c2['b'] == 3 and p42,
   f"{sorted(coins)} {CALLS['d'] - c2['d']}/{CALLS['b'] - c2['b']}")
ok("  and keeps CoinDCX's list as its own (never Pi42's)", DX.pi42 == DCX[0] and x.pi42 == {'HOT', 'FADE', 'RISE', 'BTC'})
n0 = NDCX[0]
DX.pi42_refresh(); DX.pi42_refresh()
ok("CoinDCX's list is read at most every 6 hours", NDCX[0] == n0)
DX2 = om.C538TestRule(xb, 'dx')
DCX[0] = None
x.run(now_ms=D0 + 2 * DAY + 30 * 60000); x.save()
DX2.pairs = {}
with DX2._lock:
    DX2.run(D0 + 2 * DAY + 31 * 60000)
ok("its list fails to load: it opens nothing new and says so (the page and the log)",
   DX2.pairs == {} and DX2.info.get('pi42_missing') is True and DX2.info.get('venue') == 'CoinDCX'
   and "+ (f\" | {self.v2()}'s coin list did not load: no new pairs\" if inf.get('pi42_missing') else '')" in SRC)
DCX[0] = {'HOT', 'RISE', 'DCXONLY', 'BTC'}
cfg.C541_DCX_TEST = False
off1 = DX.active()
cfg.C541_DCX_TEST = True
cfg.C532_XV_VENUE = 'binance'
off2 = DX.active()
cfg.C532_XV_VENUE = 'pi42'
ok("off with C541_DCX_TEST = False, and whenever your plan is not on Pi42 (it is a copy of the Pi42 plan)",
   off1 is False and off2 is False and DX.active() is True and F8.active() is True)
ok("the bot runs three copies (every 8 h, 3-day average, CoinDCX); Start fresh resets them; the logs push carries c538_dx.json",
   "for k in ('f8', 'w3', 'dx')]" in SRC and "for _t538 in getattr(bot, 'c538', None) or []:" in SRC
   and 'c538_dx.json' in open(os.path.join(REPO, 'deploy', 'omega-logpush.sh')).read())
ok("the plan's total never counts the copies, and nothing here can trade (C488_LIVE_OK stays False)",
   'c538' not in SRC[SRC.index('def _c527_total'):SRC.index('def _c527_total') + 6000] and cfg.C488_LIVE_OK is False)
om.time = time

print("\n4. THE PAGE")
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
bot.c538 = [om.C538TestRule(bot, k) for k in ('f8', 'w3', 'dx')]
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
        G = dict(test=pg.inner_text('#s-test'), run=pg.evaluate("document.getElementById('running').textContent"),   # inside a closed fold
                 head=pg.evaluate("document.getElementById('s-test').closest('section').querySelector('h2').textContent"),
                 hidden=pg.evaluate("document.getElementById('s-test').closest('section').hidden"),
                 rows=pg.evaluate("document.querySelectorAll('#s-test table.pairs tr').length"),
                 W=pg.evaluate('document.documentElement.scrollWidth'))
        br.close()
    return G, errs


try:
    allerr = []
    for t in bot.c538:
        t.reset(save=False)
    bot.c538[2].pi42, bot.c538[2]._pi42_at = set(f'C{j:03d}' for j in range(191)), time.time()
    G0, er = page(); allerr += er
    ok("before the copies: 'three copies of your plan', under 'Other ways, tested on paper'",
       not G0['hidden'] and 'three copies of your plan' in G0['test'] and 'Starts after your plan' in G0['test']
       and G0['head'].strip().lower() == 'other ways, tested on paper', G0['test'][:200])
    f8, w3, dx = bot.c538
    for t in bot.c538:
        t.copy_main()
    snaps = {'2026-10-09': (0.40, 0.31), '2026-10-10': (1.10, 1.30), '2026-10-11': (1.95, 1.61), '2026-10-12': (2.60, 2.05),
             '2026-10-13': (3.20, 2.70), '2026-10-14': (3.70, 3.10), '2026-10-15': (4.50, 3.65), '2026-10-16': (5.40, 4.15)}
    for t in bot.c538:
        t.since = '2026-10-08'
    f8.snaps = {k: dict(me=a, main=b, n=10, same=9) for k, (a, b) in snaps.items()}
    w3.snaps = {k: dict(me=round(b - 0.9, 2), main=b, n=10, same=7) for k, (a, b) in snaps.items()}
    dx.snaps = {k: dict(me=round(b + 0.3 * i, 2), main=b, n=10, same=6) for i, (k, (a, b)) in enumerate(snaps.items())}
    G2, er = page(); allerr += er
    T = G2['test']
    ok("the scoreboard has your rule and the three copies; CoinDCX's row: +$6.25, ahead $2.10",
       G2['rows'] == 5 and 'CoinDCX instead of Pi42' in T and '+$6.25' in T and 'ahead $2.10' in T
       and 'Checks every 8 hours' in T and 'Uses a 3-day average' in T, T[:420])
    ok("CoinDCX's line in plain words: why (Pi42's door shut), its coins, history's figure, and that moving is your choice",
       "Pi42’s trading door is shut to the bot (8 Oct)" in T and '(191 coins listed there)' in T
       and 'about $11.40 a month (ahead in 9 months out of 10)' in T and 'half Pi42’s fee' in T
       and 'your choice once you have an account there; nothing moves on its own' in T, T[T.find('CoinDCX:'):][:420])
    ok("  and the 2 December line still speaks only of the two timing copies",
       'On 2 December the research checks whether either truly beats yours' in T)
    ok("'What is running' names three test copies, CoinDCX's in capitals",
       'three test copies of your plan (checks every 8 hours; uses a 3-day average; CoinDCX instead of Pi42)' in G2['run'],
       G2["run"][:600])
    ok("no codes or jargon (C54x, UTC, Binance's pair names, leverage)",
       not any(w in T for w in ('C54', 'C53', 'UTC', 'B-', 'leverage', 'variant')))
    ok("412 px wide (a phone): nothing overflows", max(G0['W'], G2['W']) <= 412, str((G0['W'], G2['W'])))
    ok("no JavaScript errors", not allerr, '; '.join(allerr)[:300])
except Exception as ex:
    import traceback; traceback.print_exc()
    ok("page check ran", False, f"{type(ex).__name__}: {ex}")

print("\n" + "=" * 66)
print(f"C541 TEST: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
shutil.rmtree(BASE, ignore_errors=True)
sys.exit(1 if fails else 0)
