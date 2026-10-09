#!/usr/bin/env python3
"""C539: the 7 Oct 18:04 IST screens audited against the exchanges, and what it found.

The operator, 7 Oct: "isn't the pi vs delta Cross funding in the experiments section same as 'my current plan'?
check all the strategies and their numbers in all dimensions and optimise wherever feasible".
1. The plan's paper ledger books rent up to the run itself: a pair closed at 00:30 UTC keeps its 00:00 UTC payment
   (7 exits on 5 Oct lost +$0.12), and each payment carries its own 18% GST (not the day's net).
2. Each account's balance includes its own rent paid in since the daily run, as the exchange shows it.
3. The plan appears once: its detailed panel has its own fold; its old tiles, its rows in "All accounts" and its
   entry among the paper experiments are gone while the plain top shows it.
4. Round 20 (bet size) ran as pre-registered; 10% a leg stays.
"""
import os, io, sys, json, time, glob, shutil, types, socket, logging, tempfile, contextlib, importlib.util, datetime as _dt
REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, 'research', 'c527_snapshot')
BASE = tempfile.mkdtemp(prefix='c539_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c539-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om539', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C539: THE PLAN BOOKED EXACTLY, SHOWN ONCE"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C539 or later", int(om._OMEGA_VERSION[1:]) >= 539)
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
cfg.C532_XV_VENUE = 'pi42'   # C542 made CoinDCX the default; this test checks the Pi42-era plan (still supported)
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 500.0; cfg.C531_XV_REBALANCE = False
DAY, H = 86400000, 3600000
D0 = (int(time.time() * 1000) // DAY - 4) * DAY
D0s = D0 // 1000
RATE = {'HOT': 0.10}


class FakeDelta:
    def __init__(s):
        s.c = {'HOT': (1.0, 2.0), 'SWING': (1.0, 1.0)}
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
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=RATE.get(k, 0.06)) for t in range(first, en + 1, 3600)]
        return None


fdl = FakeDelta()
om._c521_get = fdl


def bn_rate(k, t_ms):
    if k == 'SWING':                                    # Pi42's rate swings: +0.08% at 00/16 UTC, -0.08% at 08 UTC
        return -0.0008 if (t_ms // H) % 24 == 8 else 0.0008
    return 0.0001


def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        k = params['symbol'][:-4]
        lo = params['startTime']
        return [dict(fundingTime=t + 5, fundingRate=str(bn_rate(k, t))) for t in range(-(-lo // (8 * H)) * 8 * H, lo + 9 * DAY, 8 * H)]
    return None


om._c516_bn_get = fake_bn
om._c532_pi42_coins = lambda: {'HOT', 'SWING', 'BTC'}
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v[1], ask=v[1], last=v[1], fr=0.0, vol=1e8) for k, v in fdl.c.items() if not k.startswith('ONLYD')}
xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset(); xb.c524x = x

print("\n1. RENT BOOKED UP TO THE RUN, GST ON EACH PAYMENT")
x.run(now_ms=D0 + 30 * 60000)
ok("day 0, 06:00 IST: HOT and SWING open (short Delta, long Pi42)", set(x.pairs) == {'HOT', 'SWING'}
   and x.pairs['HOT']['fund_from'] == D0 + 30 * 60000, str({c: round(p['s_entry'], 2) for c, p in x.pairs.items()}))
f0 = {c: p['funding'] for c, p in x.pairs.items()}
x.last_run = ''
x.run(now_ms=D0 + DAY + 30 * 60000)
hot = x.pairs['HOT']
want = 6 * 25 * 2.0 * 0.10 / 100 - 3 * 1.18 * 50.0 * 0.0001     # Delta 04..20 + the next 00:00; Pi42 08, 16, 00
ok("day 1: HOT books 6 Delta payments and 3 Pi42 payments -- the next day's 00:00 UTC included (it was held through it)",
   abs(hot['funding'] - want) < 1e-9 and hot['fund_from'] == D0 + DAY + 30 * 60000, f"{hot['funding']:.6f} vs {want:.6f}")
sw = x.pairs['SWING']; nb = abs(sw['b_qty']) * 1.0
per = -nb * 0.0008 * 1.18 + nb * 0.0008 - nb * 0.0008 * 1.18      # long Pi42: pays +0.08% at 16 and 00, receives at 08
ok("each Pi42 payment carries its own 18% GST; a received one carries none (not 18% on the day's net)",
   abs((sw['funding'] - f0['SWING']) - (6 * abs(sw['d_qty']) * 1.0 * 0.0006 + per)) < 1e-9,
   f"{sw['funding'] - f0['SWING']:.6f} vs {6 * abs(sw['d_qty']) * 0.0006 + per:.6f}")
RATE['HOT'] = 0.0                                                   # HOT's gap fades: closed at day 9's run
for k in range(2, 10):
    x.last_run = ''
    x.run(now_ms=D0 + k * DAY + 30 * 60000)
cl = [c for c in x.closed if c['coin'] == 'HOT']
ok("a pair closed at 00:30 UTC kept its 00:00 UTC payment: the window ends at the run, not at midnight",
   cl and 'HOT' not in x.pairs and ("since <= int(x['time']) * 1000 < now_ms)" in SRC or "since <= int(x['time']) * 1000 < now_ms]" in SRC) and "p['fund_from'] = now_ms" in SRC,
   str(cl[-1:]))
ok("the signal still uses the 7 completed UTC days (the records run to the run; the daily sums stop at midnight)",
   "'end': max(today // 1000 - 1, int(upto or 0) // 1000)}" in SRC and 'fD = _c524_delta_daily(d, p[\'iv\'], lo, today // 1000)' in SRC)

print("\n2. EACH ACCOUNT INCLUDES ITS OWN RENT SINCE THE RUN")
pend = om.C527Pending(xb); xb.c527p = pend
de = types.SimpleNamespace(marks={}, prods={}, _marks_at=0.0)
xb.c521d = de
x2 = om.C524CrossVenue(xb); x2.reset(); xb.c524x = x2
RATE['HOT'] = 0.10
x2.run(now_ms=D0 + 30 * 60000)
m0 = x2.margins()
pend.xv_side = {'d': 0.35, 'b': -0.05}; pend.at = time.time(); pend.sig = pend._sigs()
m1 = x2.margins()
ok("the pending rent is split by venue and added to that venue's account (Delta +$0.35, Pi42 -$0.05)",
   abs(m1['d']['eq'] - m0['d']['eq'] - 0.35) < 0.006 and abs(m1['b']['eq'] - m0['b']['eq'] + 0.05) < 0.006
   and m1['d']['rent'] == 0.35 and m1['b']['rent'] == -0.05, f"{m0['d']['eq']} -> {m1['d']['eq']}, {m0['b']['eq']} -> {m1['b']['eq']}")
x2.pairs['HOT']['fund_from'] += 1                                   # the next run moves the booked-to point
ok("once the ledger has booked it (a run), the old read is dropped, never counted twice",
   pend.side_pending() is None and x2.margins()['d']['rent'] == 0.0)
ok("the hourly read keeps each venue's part, with GST on each payment",
   "self.xv_side = {'d': xs_d, 'b': xs_b}" in SRC and "xd = sum(xv.fgst(-p['d_qty']" in SRC)

print("\n3. ROUND 20: THE BET SIZE")
pre = open(os.path.join(REPO, 'research', 'c539_preregistration.md')).read()
res = open(os.path.join(REPO, 'research', 'c539_size.txt')).read()
ok("pre-registered (with its amendment made before any variant ran)", 'Amendment (7 Oct' in pre and 'before any variant was run' in pre)
ok("the result says why it could not be taken at face value and what stays: 10% a leg",
   'ENGINE CHECK' in res and 'FAILED' in res and '10% a leg stays' in res and "+PENDLE" in res)
ok("the bot's bet size is unchanged (C524_XVENUE_SIZE 10%)", cfg.C524_XVENUE_SIZE == 0.10)

print("\n4. THE PAGE: YOUR PLAN SHOWN ONCE")
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
for t in bot.c538:
    t.reset(save=False); t.copy_main()
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
        G = dict(more_has_xv=pg.evaluate("!!document.querySelector('#more #xvenue')"),
                 plandet_has_xv=pg.evaluate("!!document.querySelector('#plandet #xvenue')"),
                 plandetk=pg.inner_text('#plandetk'),
                 tiles_hidden=pg.evaluate("['eq','day','rec'].map(function(k){return document.getElementById(k).closest('.tile').hidden})"),
                 scan_hidden=pg.evaluate("document.getElementById('scan').closest('.tile').hidden"),
                 order=pg.evaluate("Array.from(document.querySelectorAll('#simple, #plandet, #more')).map(function(n){return n.id})"),
                 more_open=pg.evaluate("document.getElementById('more').open"))
        pg.evaluate("document.querySelectorAll('details').forEach(function(x){x.open=true})")
        pg.wait_for_timeout(300)
        G.update(running=pg.inner_text('#running'), alltotal=pg.inner_text('#alltotal'), alltotalk=pg.inner_text('#alltotalk'),
                 xvenue=pg.inner_text('#xvenue'), acc=pg.inner_text('#s-acc'), plantotal=pg.inner_text('#plantotal'),
                 plantotal_hidden=pg.evaluate("document.getElementById('plantotal').closest('section').hidden"), curve=pg.inner_text('#curvewrap h2') if
                 pg.evaluate("!!document.querySelector('#curvewrap h2')") else '',
                 W=pg.evaluate('document.documentElement.scrollWidth'))
        br.close()
    return G, errs


try:
    G, errs = page()
    ok("your plan's detailed panel sits in its own fold, 'Your plan in detail', between the plain top and the experiments",
       G['plandet_has_xv'] and not G['more_has_xv'] and G['plandetk'] == 'Your plan in detail'
       and G['order'] == ['simple', 'plandet', 'more'], str(G['order']))
    ok("  and it still carries every pair's numbers", 'short Delta' in G['xvenue'] or 'long Delta' in G['xvenue'], G['xvenue'][:120])
    ok("the old 'Your plan', 'Risk' and 'Plan so far' tiles are hidden (the plain top says it); the book's own tile stays",
       G['tiles_hidden'] == [True, True, True] and G['scan_hidden'] is False, str(G['tiles_hidden']))
    A = G['alltotal']
    ok("'All accounts' becomes 'Experiments (as if each were real money)': no plan headline, rows, tax or budget line",
       G['alltotalk'].lower().startswith('experiments') and 'your plan (' not in A and 'budget:' not in A
       and 'after tax on its net profit' not in A and 'your plan is at the top of the page' in A, A[:300])
    ok("  the experiments are all still there", 'Spot pot' in A and 'Main book' in A, A[:400])
    PT = G['plantotal']
    ok("your plan's total as if live, its tax and its budget sit once, in 'Your plan in detail'",
       not G['plantotal_hidden'] and 'your plan (' in PT and 'after tax on its net profit' in PT and 'budget: your equity $1000.00' in PT
       and '₹12 lakh' in PT, PT[:300])
    R = G['running']
    ok("'What is running': your plan once (YOUR PLAN), not again among the paper experiments; the two test copies listed",
       'YOUR PLAN' in R and 'Delta vs Pi42 funding $' not in R and 'two test copies of your plan' in R, R[:500])
    ok("the accounts legend says the rent paid in since the run is included", 'rent paid in since the daily run included' in G['acc'])
    ok("the session chart is labelled as the Binance book's, an experiment", 'Binance book this session' in G['curve'], G['curve'])
    ok("412 px, no JavaScript errors", G['W'] <= 412 and not errs, f"{G['W']} {errs[:2]}")
    cfg.C527_PLAN = ('none',)
    G2, errs2 = page()
    ok("no plan: the old tiles come back, the detail fold is named as an experiment, Experiments opens (the pre-C535 page)",
       G2['tiles_hidden'] == [False, False, False] and G2['plandetk'].startswith('Delta vs Pi42 rent-gap trade')
       and G2['more_open'] is True and G2['alltotalk'].lower().startswith('all accounts') and not errs2,
       f"{G2['tiles_hidden']} {G2['plandetk']} more_open={G2['more_open']} {G2['alltotalk'][:30]} {errs2[:2]}")
    cfg.C527_PLAN = ('xvenue', 'reserve')
except Exception as ex:
    import traceback; traceback.print_exc()
    ok("page check ran", False, f"{type(ex).__name__}: {ex}")

print("\n" + "=" * 66)
print(f"C539 TEST: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
shutil.rmtree(BASE, ignore_errors=True)
sys.exit(1 if fails else 0)
