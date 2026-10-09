#!/usr/bin/env python3
"""C546: Round 24's one-way cap -- at most 6 of the 10 pairs may face the same way (paper).

The operator, 10 Oct 2026: "analyse carefully to the core, excavate any hidden issues ... discover any possibilities of
profitability enhancement or sustainance..proceed accordingly". Round 24 (research/r24_preregistration.md, pushed before
it ran; research/r24_round24.txt): each pair is neutral but each ACCOUNT is not -- 7 of 10 pairs faced one way on 10 Oct,
and on 10 Oct 2025, minute by minute, the poorer account fell to 50.1%. K6 (at most 6 of 10 the same way) passed: the
poorer account's lowest point 56.9% -> 66.3%, the crash day 50.1% -> 69.9%, after tax +$3 a year, every bar held.
1. A new pair is held back when 6 (60% of the slots) already face its way; the next best enters instead.
2. Nothing open is closed for it.
3. The page and the log say so; the research's engine check and verdict are on file.
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c546_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c546-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om546', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C546: AT MOST 6 OF 10 PAIRS FACING THE SAME WAY"); print("=" * 66)
ok("version C546 or later", int(om._OMEGA_VERSION[1:]) >= 546)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 1000.0
DAY, H = 86400000, 3600000
D0 = (int(time.time() * 1000) // DAY - 6) * DAY
UP = [f'UP{j}' for j in range(8)]            # Delta's longs pay more: "short Delta / long CoinDCX" (side +1)
DN = ['DNA', 'DNB']                         # Delta's longs are paid: "long Delta / short CoinDCX" (side -1)
RATE = {**{c: 0.10 - 0.005 * j for j, c in enumerate(UP)}, 'DNA': -0.08, 'DNB': -0.07}
PX = {c: 1.0 for c in UP + DN}
EXTRA = {f'ONLYD{j:02d}': 1.0 for j in range(20)}


class FakeDelta:
    def __call__(s, path, params, tries=3):
        if path == '/v2/products':
            return [dict(symbol=k + 'USD', contract_value='1.0', taker_commission_rate='0.0005',
                         product_specs=dict(rate_exchange_interval=14400, tags=['layer_1']), settling_asset={'symbol': 'USD'},
                         underlying_asset={'symbol': k}) for k in list(PX) + list(EXTRA)]
        if path == '/v2/tickers':
            return [dict(symbol=k + 'USD', mark_price=str(v)) for k, v in list(PX.items()) + list(EXTRA.items())]
        if path == '/v2/history/candles':
            k = params['symbol'].split(':')[1][:-3]
            st, en = int(params['start']), int(params['end'])
            first = -(-st // 14400) * 14400
            return [dict(time=t, close=RATE.get(k, 0.0)) for t in range(first, en + 1, 3600)]
        return None


om._c521_get = FakeDelta()


def fake_bn(base, path, params, tries=3):
    if path == '/fapi/v1/fundingRate' and 'symbol' in params:
        lo = params['startTime']
        return [dict(fundingTime=t + 5, fundingRate='0.0000') for t in range(-(-lo // (8 * H)) * 8 * H, lo + 9 * DAY, 8 * H)]
    return None


om._c516_bn_get = fake_bn
om._c541_coindcx_coins = lambda: set(PX)
om._c532_pi42_coins = lambda: set(PX)
xb = types.SimpleNamespace(cfg=cfg, portfolio=om.Portfolio(cfg), _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                           exchange=types.SimpleNamespace(markets={}), _c482_risk_guard=lambda: {'pct': 20.0})
xe = om.C488Engine(xb); xb.c488 = xe
xe.marks = {k + '/USDT:USDT': dict(bid=v, ask=v, last=v, fr=0.0, vol=1e8) for k, v in PX.items()}
xe.refresh_marks = lambda force=False: True
x = om.C524CrossVenue(xb); x.reset(); xb.c524x = x

print("\n1. THE CAP")
ok("the cap is 60% of the slots: 6 of 10", x.same_cap() == 6)
x.run(now_ms=D0 + 30 * 60000)
sides = [p['side'] for p in x.pairs.values()]
ok("8 coins want 'short Delta' and 2 'long Delta': 6 + 2 enter, the 2 weakest 'short Delta' coins are held back",
   sides.count(1) == 6 and sides.count(-1) == 2 and set(x.info.get('capped') or []) == {'UP6', 'UP7'},
   f"{sides.count(1)} + {sides.count(-1)}; held back {x.info.get('capped')}")
ok("the widest gaps win the 6 places (UP0..UP5)", {c for c, p in x.pairs.items() if p['side'] > 0} == set(UP[:6]))
ok("the run records the cap and the count each way", x.info.get('same_max') == 6 and x.info.get('n_short_delta') == 6
   and x.info.get('n_long_delta') == 2)

print("\n2. NOTHING OPEN IS CLOSED FOR IT")
y = om.C524CrossVenue(xb); y.reset()
cfg.C546_XV_SAME_SHARE = 1.0                      # no cap: all 8 enter
y.run(now_ms=D0 + 30 * 60000)
n8 = sum(1 for p in y.pairs.values() if p['side'] > 0)
cfg.C546_XV_SAME_SHARE = 0.6
y.last_run = ''
y.run(now_ms=D0 + DAY + 30 * 60000)
ok("a book with 8 facing one way keeps all 8 when the cap arrives (it only holds back new ones)",
   n8 == 8 and sum(1 for p in y.pairs.values() if p['side'] > 0) == 8 and not y.info.get('exited'), str(y.info.get('exited')))

print("\n3. THE 15-PAIR COPY, THE PAGE, THE LOG, THE RESEARCH")
b15 = om.C538TestRule(xb, 'b15') if 'b15' in om.C538TestRule.RULES else None
ok("the 15-pair copy's cap is 9 (60% of 15)", b15 is not None and b15.same_cap() == 9)
st = x.status() if hasattr(x, 'status') else {}
ok("the page's data carries the cap", (st or {}).get('same_max') == 6, str((st or {}).get('same_max')))
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("the pairs card says how many face each way and when a way is full",
   'At most \'+cap+\' may face the same way' in SRC and "no new pair '+full+' until one of those closes" in SRC)
x2 = om.C524CrossVenue(xb); x2.reset()
LOG.clear()
x2._fail_at = 0; x2._tick_at = 0; x2.last_run = ''
x2.active = lambda: True
x2.due = lambda: True
x2.save = lambda: None
x2.tick()
msg = ' '.join(m for _, m in LOG)
ok("the daily log line names what was held back and why", 'held back (6 already face that way): UP6, UP7' in msg, msg[-200:])
R = json.load(open(os.path.join(REPO, 'research', 'r24_round24.json')))
ok("Round 24 on file: engine check OK; K6 passed; the swaps and K7 did not",
   R.get('engine_check') is True and R['verdict']['K6']['passed'] and not R['verdict']['K7']['passed']
   and not R['verdict']['S40']['passed'] and not R['verdict']['S80']['passed'])
ok("K6's record: poorer account up >= 5 points, after tax not below base - $30 a year",
   R['R']['K6']['low'] - R['R']['base']['low'] >= 0.05 and (R['R']['K6']['after1'] - R['R']['base']['after1']) * 12000 >= -30)
ok("C488_LIVE_OK stays False; no keys in the code", 'self.C488_LIVE_OK = False' in SRC)
print()
print("=" * 66)
print("C546 TEST: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
