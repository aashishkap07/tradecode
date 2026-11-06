#!/usr/bin/env python3
"""C549: Delta's hourly-settlement runs counted right, and no forced exit on a day's missing records (paper).

Found in the 1 Nov 2026 monthly review (reports/2026-11-01_monthly_review.md):
1. Delta switches a coin to HOURLY funding during a squeeze and back later (Oct 2026: ARK, BMT, GTC, IOST, IRYS, ORDER,
   RLC). The bot applied the coin's CURRENT interval to the whole 8-day window: read while hourly, each old 4-hour
   payment counted 4 times (ARK -1176%/yr on 27 Oct, truly -51%; BMT -1016% on 28 Oct, truly -27%: both entered the
   wrong way); read after, 3 of 4 hourly payments were missed (BMT +244% on 31 Oct, truly -86%; ARK's rent booked
   $0.32 of $0.90). `_c549_paid` finds the settlements from the records themselves.
2. A held pair whose 7-day spread is missing because a day's records did not load is held (closed at the third run
   in a row), not closed at once (BEAT, 27 Oct).
3. A pair is not opened where CoinDCX takes closing orders only (its `exit_only` flag; 30 Oct 2026, after Binance's
   security incident, every CoinDCX futures market for some hours, then ERA, GTC, LA and SOPH).
The real records are in test_fixtures/c549_hourly_funding.json (Delta and Binance, fetched 1 Nov 2026).
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c549_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c549-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om549', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C549: DELTA'S HOURLY RUNS; NO EXIT ON A DAY'S MISSING RECORDS; COINDCX CLOSE-ONLY"); print("=" * 66)
ok("version C549 or later", int(om._OMEGA_VERSION[1:]) >= 549)
FX = json.load(open(os.path.join(REPO, 'test_fixtures', 'c549_hourly_funding.json')))
DAYS = 86400
U = lambda y, m, d, h=0: int(time.mktime((y, m, d, h, 0, 0, 0, 0, 0)) - time.timezone)   # UTC


def recs(c):
    return [dict(time=t, close=x) for t, x in FX[c]['delta']]


def old_daily(rs, iv_s, lo, hi):
    """the C548 rule, kept here to show what it did"""
    hrs, out = max(1, int(iv_s) // 3600), {}
    for x in rs:
        t = int(x['time'])
        if (t // 3600) % hrs == 0 and lo <= t < hi:
            out[t // DAYS * DAYS] = out.get(t // DAYS * DAYS, 0.0) + float(x['close']) / 100.0
    return out


def bn_daily(c, lo, hi):
    out = {}
    for t, r in FX[c]['binance']:
        if lo * 1000 <= t < hi * 1000:
            out[t // 1000 // DAYS * DAYS] = out.get(t // 1000 // DAYS * DAYS, 0.0) + r
    return out


def sig(c, cut, iv, rule='new', grid=None):
    lo, days = cut - 8 * DAYS, [cut - k * DAYS for k in range(7, 0, -1)]
    fD = om._c524_delta_daily(recs(c), iv, lo, cut, grid) if rule == 'new' else old_daily(recs(c), iv, lo, cut)
    s = om._c524_signal(fD, bn_daily(c, lo, cut), days)
    return None if s is None else round(100 * s)


print("\n1. THE RULE ON OCTOBER'S REAL RECORDS")
a27, b28, b31 = U(2026, 10, 27), U(2026, 10, 28), U(2026, 10, 31)
ok("the old rule reproduces the bot's logged signals: ARK -1176%/yr (27 Oct), BMT -1016% (28 Oct), BMT +244% (31 Oct)",
   (sig('ARK', a27, 3600, 'old'), sig('BMT', b28, 3600, 'old'), sig('BMT', b31, 14400, 'old')) == (-1176, -1016, 244),
   f"{sig('ARK', a27, 3600, 'old')}, {sig('BMT', b28, 3600, 'old')}, {sig('BMT', b31, 14400, 'old')}")
ok("the new rule: ARK -51%, BMT -27% (28 Oct), BMT -86% (31 Oct)",
   (sig('ARK', a27, 3600), sig('BMT', b28, 3600), sig('BMT', b31, 14400)) == (-51, -27, -86),
   f"{sig('ARK', a27, 3600)}, {sig('BMT', b28, 3600)}, {sig('BMT', b31, 14400)}")
ok("the new rule does not depend on the interval Delta shows at the moment (hourly or 4-hourly: the same)",
   sig('ARK', a27, 3600) == sig('ARK', a27, 14400) and sig('BMT', b28, 3600) == sig('BMT', b28, 14400))
per = lambda c, d0: len(om._c549_paid(recs(c), 14400, d0, d0 + DAYS))
ok("payments a day: ARK 6 on 20 Oct (4-hourly), 17 on 24 Oct (switched at 10:00 UTC), 24 on 25 Oct (hourly)",
   (per('ARK', U(2026, 10, 20)), per('ARK', U(2026, 10, 24)), per('ARK', U(2026, 10, 25))) == (6, 17, 24),
   str((per('ARK', U(2026, 10, 20)), per('ARK', U(2026, 10, 24)), per('ARK', U(2026, 10, 25)))))
g = {t for t, _ in om._c549_paid(recs('GTC'), 14400, 0, 2 ** 40)}
ok("an hourly run of equal rates is counted (GTC 13 Oct 17-20 UTC at Delta's floor 0.00125%)",
   all(U(2026, 10, 13, h) in g for h in (17, 18, 19, 20)))
r = {t for t, _ in om._c549_paid(recs('RLC'), 14400, 0, 2 ** 40)}
ok("after the last hourly payment the repeated rate is not counted (RLC 9 Oct 02-03 UTC); 04 UTC is",
   U(2026, 10, 9, 1) in r and U(2026, 10, 9, 2) not in r and U(2026, 10, 9, 3) not in r and U(2026, 10, 9, 4) in r)

print("\n2. THE USUAL TIMETABLES")
t0 = U(2026, 9, 1)
flat = [dict(time=t0 + 3600 * h, close=0.01) for h in range(10 * 24)]
n = lambda rs, iv, grid=None: len(om._c549_paid(rs, iv, t0 + DAYS, t0 + 2 * DAYS, grid))
ok("a 4-hour coin at an unchanged rate: 6 a day; an 8-hour coin: 3 a day (equal payments are still payments)",
   n(flat, 14400) == 6 and n(flat, 28800) == 3)
ok("a coin reading hourly with no remembered timetable is taken as 4-hourly; one remembered as 8-hourly, 3 a day",
   n(flat, 3600) == 6 and n(flat, 3600, 28800) == 3)
gap = [x for x in flat if not (t0 + DAYS + 5 * 3600 <= x['time'] < t0 + DAYS + 8 * 3600)]
gap2 = [dict(x, close=0.02) if x['time'] >= t0 + DAYS + 8 * 3600 else x for x in gap]
ok("a missing hour is never taken for a change (the 4-hourly payment after a hole is counted once)",
   n(gap2, 14400) == 6, str(n(gap2, 14400)))

print("\n3. THE TEST COPIES' SIGNAL AND THE PRODUCT TABLE")
for c, cut in (('ARK', a27), ('BMT', b28), ('BMT', b31)):
    d_recs = recs(c)
    b_recs = [dict(fundingTime=t, fundingRate=str(r)) for t, r in FX[c]['binance']]
    s38 = om._c538_signal(d_recs, b_recs, 3600, cut, 7)
    ok(f"the test copies' signal equals the daily rule's at midnight ({c}, {time.strftime('%d %b', time.gmtime(cut))})",
       s38 is not None and round(100 * s38) == sig(c, cut, 3600), f"{None if s38 is None else round(100 * s38)}")
SEQ = [14400, 3600]


def prod_get(path, params, tries=3):
    if path == '/v2/products':
        iv = SEQ[0]
        return [dict(symbol=k + 'USD', contract_value='1', taker_commission_rate='0.0005',
                     product_specs=dict(rate_exchange_interval=(iv if k.startswith('A') else (28800 if k.startswith('E') else 3600)), tags=[]),
                     settling_asset={'symbol': 'USD'}, underlying_asset={'symbol': k}) for k in [f'A{j}' for j in range(10)]
                + [f'E{j}' for j in range(10)] + [f'H{j}' for j in range(5)]]
    return None


om._c521_get = prod_get
pb = types.SimpleNamespace(cfg=om.Config(), _c462_state_settled=True)
d0 = om.C521Delta.__new__(om.C521Delta); d0.prods, d0._prod_at, d0.cfg = {}, 0.0, pb.cfg
om.C521Delta.refresh_products(d0, force=True)
first = dict(d0.prods)
SEQ[0] = 3600
om.C521Delta.refresh_products(d0, force=True)
ok("the product table keeps each coin's usual timetable: 4-hourly stays 4-hourly when Delta reads hourly",
   first['A0']['grid'] == 14400 and d0.prods['A0']['iv'] == 3600 and d0.prods['A0']['grid'] == 14400)
ok("8-hourly coins keep 8 hours; a coin first seen hourly is taken as 4-hourly",
   d0.prods['E0']['grid'] == 28800 and first['H0']['grid'] == 14400 and d0.prods['H0']['grid'] == 14400)

print("\n4. THE DAILY RUN: BMT 30 -> 31 OCT, BOOKED AND HELD")
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 1000.0
PX = {'BMT': 0.02346838, 'GAPC': 1.0, 'SHUTC': 1.0}
MISS = set()


class FakeDelta:
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value='10' if k == 'BMT' else '1', taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=[]), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k in PX] + [
                dict(symbol=f'X{j}USD', contract_value='1', taker_commission_rate='0.0005',
                     product_specs=dict(rate_exchange_interval=14400, tags=[]), settling_asset={'symbol': 'USD'},
                     underlying_asset={'symbol': f'X{j}'}) for j in range(20)]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(v)) for k, v in PX.items()]
        if path == '/v2/history/candles':
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            if k in MISS:
                return None
            if k == 'BMT':
                return [dict(time=t, close=x) for t, x in FX['BMT']['delta'] if st <= t <= en]
            return [dict(time=t, close=-0.02) for t in range(-(-st // 3600) * 3600, en + 1, 3600)]
        return None


om._c521_get = FakeDelta()


def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        c, lo = params['symbol'][:-4], int(params['startTime'])
        if c in MISS:
            return None
        if c == 'BMT':
            return [dict(fundingTime=t, fundingRate=str(r)) for t, r in FX['BMT']['binance'] if t >= lo]
        return [dict(fundingTime=t + 5, fundingRate='0.0000') for t in range(-(-lo // 28800000) * 28800000, lo + 9 * 86400000, 28800000)]
    return None


om._c516_bn_get = fake_bn
om._c541_coindcx_coins = lambda: set(PX)
SHUT, ASKED = {'SHUTC'}, []
real_eo = om._c549_dcx_exit_only
om._c549_dcx_exit_only = lambda c, now=None: (ASKED.append(c), c in SHUT)[1]
om._c532_pi42_coins = lambda: set(PX)
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v, ask=v, last=v, fr=0.0, vol=1e8) for k, v in PX.items()}
xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset(); xb.c524x = x
since, now = 1793320220000, 1793406615524               # 30 Oct 00:30:20 -> 31 Oct 00:30:15 UTC (the ledger's runs)
jx = dict(opened=since, d_px0=0.0225, b_px0=0.0225, n_in=81.2, fee_d=0.0, fee_b=0.0, px_d=0.0, px_b=0.0, fm={},
          venue='CoinDCX', rates={}, carry=None)
x.pairs['BMT'] = dict(side=-1, d_sym='BMTUSD', cv=10.0, d_qty=361.0, b_qty=-3602.4, d_px=0.02346838, b_px=0.02346838,
                      notional=81.2, s_entry=-10.16, s_now=-6.9, opened=since, fund_from=since, pnl=0.0, funding=0.0, jx=jx)
GAP = lambda: dict(side=-1, d_sym='GAPCUSD', cv=1.0, d_qty=100.0, b_qty=-100.0, d_px=1.0, b_px=1.0, notional=100.0,
                   s_entry=-0.5, s_now=-0.5, opened=since, fund_from=since, pnl=0.0, funding=0.0, jx=dict(jx, fm={}))
x.pairs['GAPC'] = GAP()                                  # Delta's longs are paid (-0.02%/h): long Delta, side -1
x.last_run = '2026-10-30'
MISS.add('GAPC')
x.run(now_ms=now)
want = sum(-361.0 * 10.0 * 0.02346838 * r for t, r in om._c549_paid(recs('BMT'), 14400, -(-since // 1000), -(-now // 1000)))
got = sum((x.pairs['BMT']['jx']['fm'].get('2026-10') or [0.0] * 6)[:3])
ok("BMT's Delta rent for 30 -> 31 Oct: 13 payments ($0.2554, as recomputed from Delta's records), not 6 ($0.1774)",
   len(om._c549_paid(recs('BMT'), 14400, -(-since // 1000), -(-now // 1000))) == 13 and abs(got - want) < 1e-9
   and abs(got - 0.2554) < 0.0005, f"${got:.4f}")
ok("and BMT is held: its true spread (-86%/yr) agrees with its side (C548 closed it on +244% and turned it round)",
   'BMT' in x.pairs and x.pairs['BMT']['side'] == -1 and round(100 * x.pairs['BMT']['s_now']) == -86,
   str(x.info.get('exited')))

ok("a coin CoinDCX takes closing orders on only is not opened, and the run says so (30 Oct: ERA, GTC, LA, SOPH)",
   'SHUTC' not in x.pairs and x.info.get('shut') == ['SHUTC'] and ASKED == ['SHUTC'], f"{x.info.get('shut')}, asked {ASKED}")

print("\n5. A DAY'S MISSING RECORDS")
ok("a pair whose records did not load is held, not closed, and the run says so",
   'GAPC' in x.pairs and x.pairs['GAPC'].get('gap') == 1 and x.info.get('gaps') == ['GAPC (1 of 3)']
   and not any(e.startswith('GAPC') for e in x.info.get('exited') or []), str(x.info.get('gaps')))
ok("its last spread is kept on the page, and its rent waits for the records (booked the next day)",
   x.pairs['GAPC']['s_now'] == -0.5 and x.pairs['GAPC']['fund_from'] == since and x.pairs['GAPC']['funding'] == 0.0)
x.last_run = ''
x.run(now_ms=now + 86400000)
MISS.discard('GAPC')
x.last_run = ''
x.run(now_ms=now + 2 * 86400000)
ok("records again: the count starts over, and both days' rent is booked", x.pairs.get('GAPC', {}).get('gap') == 0
   and x.pairs['GAPC']['fund_from'] == now + 2 * 86400000 and x.pairs['GAPC']['funding'] != 0.0,
   str(x.pairs.get('GAPC', {}).get('gap')))
MISS.add('GAPC')
for k in (3, 4, 5):
    x.last_run = ''
    x.run(now_ms=now + k * 86400000)
ok("missing at the third run in a row: closed, as before ('no 7-day spread')",
   'GAPC' not in x.pairs and any(e == 'GAPC (no 7-day spread)' for e in x.info.get('exited') or []), str(x.info.get('exited')))
MISS.discard('GAPC')
x2 = om.C524CrossVenue(xb); x2.reset()
x2.pairs['GAPC'] = GAP()
MISS.add('GAPC')
LOG.clear()
x2._fail_at = 0; x2._tick_at = 0; x2.last_run = ''
x2.active = lambda: True
x2.due = lambda: True
x2.save = lambda: None
x2.tick()
msg = ' '.join(m for _, m in LOG)
ok("the daily log line names the pair held over a gap", 'held, no spread today (records did not load): GAPC (1 of 3)' in msg,
   msg[-160:])
ok("... and the coin not opened because CoinDCX takes closing orders only",
   'not opened, CoinDCX takes closing orders only: SHUTC' in msg, msg[-200:])
SHUT.clear()
x2.last_run = ''
x2.run(now_ms=now + 6 * 86400000)
ok("when CoinDCX opens it again, the pair is opened as usual", 'SHUTC' in x2.pairs and not x2.info.get('shut'))

print("\n6. CoinDCX'S OWN FLAG")
class _R:
    def __init__(s, code, js): s.status_code, s._js = code, js
    def json(s): return s._js
calls = []
def fake_get(url, params=None, timeout=None):
    calls.append(params)
    k = params['pair']
    if k == 'B-ERR_USDT':
        raise ValueError('no answer')
    return _R(200, {'instrument': {'exit_only': k == 'B-SOPH_USDT', 'status': 'active'}})
om.requests.get, real_get = fake_get, om.requests.get
om._c549_eo.clear()
ok("the instrument's exit_only flag is read (rupee margin): SOPH close-only, KAITO open",
   real_eo('SOPH', 1000.0) is True and real_eo('KAITO', 1000.0) is False
   and calls[0] == {'pair': 'B-SOPH_USDT', 'margin_currency_short_name': 'INR'})
n0 = len(calls)
ok("read once a coin per 30 minutes", real_eo('SOPH', 1500.0) is True and len(calls) == n0
   and real_eo('SOPH', 1000.0 + 1801) is True and len(calls) == n0 + 1)
ok("an unanswered read counts as open on paper, and is asked again next time",
   real_eo('ERR', 1000.0) is False and real_eo('ERR', 1001.0) is False and 'ERR' not in om._c549_eo)
om.requests.get = real_get
why = om._c540_why('coindcx', 422, {'code': 422, 'message': 'Api key expired abcdefABCDEF0123456789abcdef0123', 'status': 'error'})
ok("a CoinDCX refusal now carries CoinDCX's own reason, never a key-like token (28 Oct: 'HTTP 422', no reason)",
   why.startswith('the venue answered HTTP 422 ("Api key expired') and 'abcdefABCDEF' not in why, why)
ok("... and with no reason given, the old words", om._c540_why('coindcx', 422, None) == 'the venue answered HTTP 422')

print("\n7. NOTHING LEFT ON THE OLD RULE")
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("no Delta settlement is picked by 'every Nth hour' any more (signal, booking, test copies, waiting rent)",
   '% hrs == 0' not in SRC and SRC.count('_c549_paid(') >= 4)
ok("the page's waiting rent reads 8 hours before the last booking, to see an hourly run",
   "st = int(p['fund_from']) // 1000 - 8 * 3600" in SRC)
ok("the C530 comment is back on its own line (C548 had moved it onto C548_RETIRE)",
   "self.C530_PENDLE = False                # C531: off" in SRC and "self.C548_RETIRE = True\n" in SRC)

print("\n" + "=" * 66)
print(f"C549: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}")
sys.exit(1 if fails else 0)
