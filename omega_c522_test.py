#!/usr/bin/env python3
"""C522: what the C521 screens (2 Oct 2026, 12:31 IST) showed.

1. The intraday shadow takes the RESEARCH's universe (the C488 rule: top 40 by 30-day
   median volume, listed >= 90 days) -- not the top 40 by 24-hour volume, which on
   Binance took in days-old listings swinging 20-36% an hour.
2. Its record on the wrong universe is archived (kept, shown), once; the ledgers restart.
3. Max drawdown counts from the starting point (a first-day loss is a drawdown).
4. Delta and the Binance book are compared over the SAME window; Delta's price age is shown.
5. The page (Chromium).
"""
import os, io, sys, json, time, glob, types, socket, logging, tempfile, contextlib, importlib.util
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c522_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
TOKEN = 'c522-test-token-0123456789abcdef'
os.environ['OMEGA_CTRL_TOKEN'] = TOKEN
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om522', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False
print("=" * 66); print("C522: THE SHADOW'S UNIVERSE, DRAWDOWN FROM THE START, DELTA ON ONE WINDOW"); print("=" * 66)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("version C522", om._OMEGA_VERSION == 'C522')


def cfg_bn():
    c = om.Config(); c.PAPER_MODE = True; c.VENUE = 'binance'
    for k, v in om._C516_VENUE_DEFAULTS['binance'].items():
        setattr(c, k, v)
    om._c467_cfg_ref[0] = c
    return c


print("\n1. THE SHADOW'S UNIVERSE IS THE RESEARCH'S")
DAY = 86400000
n, k = 330, 70
T = ((int(time.time() * 1000) // DAY) - n + np.arange(n)) * DAY
g = np.random.default_rng(3)
close = 1.0 + np.abs(g.normal(0, 1, (n, k))).cumsum(0) * 0.01
qv = np.full((n, k), np.nan)
for j in range(k):
    qv[:, j] = np.exp(18 - 0.05 * j + g.normal(0, 0.1, n))      # older coins: steady volume, falling with j
keep = [f"C{j:02d}/USDT:USDT" for j in range(k)]
# two days-old listings with HUGE recent volume: first in a 24-hour ranking, absent from the research's
for j in (60, 61):
    close[:n - 20, j] = np.nan; qv[:n - 20, j] = np.nan; qv[n - 20:, j] = np.exp(25)
cfg = cfg_bn()
marks = {s: dict(bid=1, ask=1, last=1, fr=0.0001, vol=float(qv[-1, j])) for j, s in enumerate(keep)}
marks['BTC/USDT:USDT'] = dict(bid=1, ask=1, last=1, fr=0.0001, vol=1.0)
eng = types.SimpleNamespace(marks=marks, _is_crypto=lambda s: True, refresh_marks=lambda force=False: True,
                            _last_M=(time.strftime('%Y-%m-%d', time.gmtime()), 20, (T, keep, close, qv, np.zeros((n, k)))))
bot = types.SimpleNamespace(cfg=cfg, c488=eng, portfolio=types.SimpleNamespace(equity=500.0), _c462_state_settled=True)
sh = om.C489Shadow(bot)
uni = sh.universe()
want = [om.C488Engine._raw(s) for j, s in enumerate(keep) if om._c488_universe(close, qv, 40)[-1][j]]
ok("the 40 coins of the C488 rule (30-day median volume through yesterday, listed 90+ days), plus BTC",
   uni[:-1] == want and len(want) == 40 and uni[-1] == 'BTCUSDT', f"{len(uni)} coins")
ok("  the days-old listings with the biggest 24-hour volume are NOT in it",
   'C60USDT' not in uni and 'C61USDT' not in uni)
ok("  and the shadow says which rule chose its coins", sh.universe_rule.startswith('research'), sh.universe_rule)
old = sorted(((v['vol'], s) for s, v in marks.items()), reverse=True)[:40]
ok("  (the 24-hour ranking would have put them first)", old[0][1] in ('C60/USDT:USDT', 'C61/USDT:USDT'))
eng._last_M = None
sh2 = om.C489Shadow(bot)
np.savez_compressed(os.path.join(om.BASE_PATH, 'c488_inputs.npz'), T=T, keep=np.array(keep, dtype=str), close=close, qv=qv,
                    fund=np.zeros((n, k)), at=np.array([time.time()]))
ok("after a restart (no matrices in memory) it reads the book's saved inputs: the same 40",
   sh2.universe()[:-1] == want and sh2.universe_rule.startswith('research'))
os.remove(os.path.join(om.BASE_PATH, 'c488_inputs.npz'))
sh3 = om.C489Shadow(bot)
u3 = sh3.universe()
ok("before the book has ever rebalanced: 24-hour volume, and it says so",
   sh3.universe_rule.startswith('24-hour') and u3[0] in ('C60USDT', 'C61USDT'), sh3.universe_rule)

print("\n2. THE OLD RECORD IS ARCHIVED, ONCE")
p = os.path.join(om.BASE_PATH, 'c489_shadow.json')
json.dump(dict(led={'M1': dict(eq=0.9291, w={'XUSDT': 0.1}, cohorts=[], daily={'1': -0.05, '2': -0.02}, trades=549, cost=0.007, funding=0.0),
                    'M1g': dict(eq=1.0, w={}, cohorts=[], daily={'1': 0.0, '2': 0.0}, trades=0, cost=0.0, funding=0.0)},
               last_hour=1, syms=['BTCUSDT'], start_equity=499.83, model_used='full (16 features)'), open(p, 'w'))
sh4 = om.C489Shadow(bot)
a = sh4.archive[-1] if sh4.archive else {}
ok("a pre-C522 record with trades is archived: M1 -7.09% over 2 days, 549 trades, and why",
   a.get('M1', {}).get('pct') == -7.09 and a['M1']['days'] == 2 and a['M1']['trades'] == 549
   and 'research' in a.get('why', '') and a.get('M1g', {}).get('pct') == 0.0, str(a))
ok("  the ledgers restart at 1.0 and the start equity is read again", all(L['eq'] == 1.0 and not L['trades'] for L in sh4.led.values())
   and sh4.start_equity == 0.0)
d4 = json.load(open(p))
ok("  saved at once with the C522 mark and the archive", d4.get('c522') is True and len(d4.get('archive') or []) == 1)
sh5 = om.C489Shadow(bot)
ok("  reloading does not archive again", len(sh5.archive) == 1 and sh5.led['M1']['eq'] == 1.0)
st5 = sh5.status()
ok("  the status carries the universe rule and the archive", 'archive' in st5 and st5['archive'][0]['M1']['pct'] == -7.09
   and 'universe' in st5)
LOG.clear()
sh6 = om.C489Shadow(bot); sh6._c522_restart = True; sh6.archive = sh5.archive
sh6.active = lambda: True; bot._c462_state_settled = True
sh6._fail_at = time.time()                                # stop it fetching after the message
sh6.tick()
ok("  the first tick says it once: 'the shadow's record restarts on the research's universe ... Archived: M1 -7.09%'",
   any('C522 the shadow' in m and 'M1 -7.09%' in m for lv, m in LOG), str([m for lv, m in LOG][:2]))

print("\n3. MAX DRAWDOWN COUNTS FROM THE START")
ok("a first-day loss of 0.86% is a 0.86% drawdown (C521 showed 0.0%)", om._c501_stats([-0.0086])['maxdd'] == 0.0086)
ok("  a gain then a loss: the drawdown from the peak", abs(om._c501_stats([0.10, -0.05])['maxdd'] - 0.05) < 1e-9)
ok("  no loss: 0", om._c501_stats([0.01, 0.02])['maxdd'] == 0.0)

print("\n4. DELTA AND THE BINANCE BOOK ON ONE WINDOW")


class FakeDelta:
    def __init__(s):
        s.px = {'BTC': 84000.0, 'ETH': 2700.0}; s.cv = {'BTC': 0.001, 'ETH': 0.01}
        for j in range(22):
            s.px[f"C{j:02d}"] = 1.0 + j; s.cv[f"C{j:02d}"] = 1.0
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=c + 'USD', contract_value=str(s.cv[c]), taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=28800, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': c}) for c in s.px]
        if path == '/v2/tickers':
            return [dict(symbol=c + 'USD', mark_price=str(p), funding_rate='0.01',
                         quotes={'best_bid': str(p * 0.9999), 'best_ask': str(p * 1.0001)}) for c, p in s.px.items()]
        return []


om._c521_get = FakeDelta()
beq = [499.19]
deng = types.SimpleNamespace(live_equity=lambda: beq[0], born={'eq': 500.0}, last_rebal='')
db = types.SimpleNamespace(cfg=cfg, _c462_state_settled=True, c488=deng)
dl = om.C521Delta(db); dl.reset()
dl.rebalance(['BTC/USDT:USDT', 'ETH/USDT:USDT'], np.array([0.17, -0.11]), 'first')
c0 = dict(dl.cmp0)
ok("the first rebalance takes one snapshot before its fills: the time, Delta's $500, the Binance book's marked $499.19",
   c0.get('book') == 499.19 and c0.get('delta') == 500.0 and c0.get('t'), str(c0))
beq[0] = 501.69
st = dl.status()
ok("  the panel compares both from it: the Binance book +0.50% (499.19 -> 501.69) beside Delta's own change",
   st['book_pct'] == round(100 * (501.69 / 499.19 - 1), 2) and st['delta_cmp_pct'] == round(100 * (dl.equity() / c0['delta'] - 1), 2)
   and st['cmp_since'], str({k: st[k] for k in ('book_pct', 'delta_cmp_pct', 'cmp_since')}))
ok("  and how old Delta's prices are (refreshed every 5 minutes)", st['marks_age_min'] is not None and st['marks_age_min'] < 1)
dl.save()
d = json.load(open(os.path.join(om.BASE_PATH, 'c521_delta.json'))); d.pop('cmp0', None)
json.dump(d, open(os.path.join(om.BASE_PATH, 'c521_delta.json'), 'w'))
dl2 = om.C521Delta(db)
ok("a Delta book begun under C521 (no snapshot) has none until its next tick", not dl2.cmp0 and dl2.status()['book_pct'] is None)
dl2.marks = dl.marks; dl2.prods = dl.prods; dl2._marks_at = time.time(); dl2._prod_at = time.time()
dl2._tick_at = 0; dl2.tick()
ok("  then takes it, so the window starts at the update", bool(dl2.cmp0) and dl2.cmp0['book'] == 501.69)
_keep = open(os.path.join(om.BASE_PATH, 'c521_delta.json')).read()
dl3 = om.C521Delta(db); dl3.reset(); dl3.marks = dl.marks; dl3.prods = dl.prods; dl3._marks_at = time.time()
dl3.rebalance(['BTC/USDT:USDT', 'C00/USDT:USDT', 'C05/USDT:USDT'], np.array([0.17, 0.008, -0.009]), 'floor')
z3 = dl3.info.get('zero') or []
ok("targets under the book's $6 floor are named and not held (C521 skipped them silently): C00 +$4.00 (4 contracts) and C05 -$4.50",
   'C00 +4.00 < $6' in z3 and 'C05 -4.50 < $6' in z3 and set(dl3.pos) == {'BTCUSD'}, str(z3) + ' ' + str(list(dl3.pos)))
open(os.path.join(om.BASE_PATH, 'c521_delta.json'), 'w').write(_keep)

print("\n5. THE PAGE (Chromium)")


def free_port():
    s_ = socket.socket(); s_.bind(('127.0.0.1', 0)); p_ = s_.getsockname()[1]; s_.close(); return p_


pfP = om.Portfolio(cfg); pfP.equity = pfP.available_balance = 500.0; pfP.session_start_equity = 500.0
pfP.positions = om.PositionsManager()
bP = types.SimpleNamespace(cfg=cfg, portfolio=pfP, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                           _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': 500.0, 'month_budget': 100.0,
                                                     'month_used': 0.0, 'day_cap': 25.0, 'day_used': 0.0, 'halt': ''})
eP = om.C488Engine(bP); eP.reset(); bP.c488 = eP; pfP._c488 = eP
dl.bot = types.SimpleNamespace(cfg=cfg, c488=types.SimpleNamespace(live_equity=lambda: 501.69))
bP.c489 = sh5; bP.c490 = om.C490Carry(bP); bP.c501s = om.C501Spot(bP); bP.c501v = om.C501Savings(bP)
bP.c501k = om.C501Allostatic(bP); bP.c510t = om.C510Tournament(bP); bP.c521b = om.C521Bfusd(bP); bP.c521d = dl
bP._c504_data_health = lambda now=None: {'ok': True, 'bits': [], 'late': [], 'keys': []}
fbot = types.SimpleNamespace(cfg=cfg, portfolio=pfP, c488=eP, c501s=bP.c501s, c501v=bP.c501v, c501k=bP.c501k,
                             c489=sh5, c490=bP.c490, c510t=bP.c510t, c521b=bP.c521b, c521d=dl,
                             mode_mgr=types.SimpleNamespace(mode=types.SimpleNamespace(value='normal')), exchange=bP.exchange,
                             _c467_day_barrier=lambda: {'pnl': 0.0, 'limit': 9.0, 'used': 0.0, 'frac': 0.0},
                             _c482_risk_guard=bP._c482_risk_guard, _c504_data_health=bP._c504_data_health)
sh5.universe_rule = 'research (30-day median volume, listed 90+ days)'
port = free_port(); om.RemoteControl(fbot, port=port).start(); time.sleep(0.6)
try:
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        pg = br.new_page(viewport={'width': 412, 'height': 900}); errs = []
        pg.on('pageerror', lambda x: errs.append(str(x)))
        pg.goto(f'http://127.0.0.1:{port}/?t={TOKEN}'); pg.wait_for_timeout(3000)
        sht, dlt = pg.inner_text('#shadow'), pg.inner_text('#delta')
        br.close()
    ok("the shadow panel names its universe and shows the archived record",
       'coins by research (30-day median volume, listed 90+ days)' in sht and 'archived' in sht and 'M1 -7.09%' in sht, sht[:400])
    ok("the Delta panel: 'since <time>: Delta x% vs the Binance book +0.50%' and the age of Delta's prices",
       'vs the Binance book +0.50%' in dlt and 'since ' in dlt and 'Delta prices' in dlt and 'min old' in dlt, dlt[:400])
    ok("no JavaScript errors", not errs, str(errs))
except ImportError:
    ok("Chromium/playwright available for the page check", False)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
os._exit(1 if fails else 0)
