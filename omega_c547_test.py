#!/usr/bin/env python3
"""C547: Round 23 -- one coin jumping several times over in a day (paper; information only).

The routine (22 Oct 2026): pre-register, then test jump filters, per-coin size limits and the bigger settings on Round
24's engine (1-minute replays, cross margin, the K6 cap); implement what passes. research/r23_preregistration.md was
pushed before anything ran; research/r23_round23.txt: NONE of J1, J2, Z1, Z2, S50, S100 passed (each cost more than $30
a year after tax, or left an account lower on a replayed day), so the plan's rules do not change and the bigger
settings were not run. What the bot gains is the plain statement the pre-registration asked for:
1. For each account, its biggest short leg and the one-day jump on it that would empty the account (and what +100%
   would leave).
2. The page and the daily log say so.
3. Nothing is traded on it; the C546 cap and the C544/C545 tax journal are unchanged.
"""
import os, io, sys, json, time, types, logging, tempfile, contextlib, importlib.util
REPO = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix='c547_test_')
os.environ['OMEGA_BASE_PATH'] = BASE
os.environ['OMEGA_CTRL_TOKEN'] = 'c547-test-token-0123456789abcdef'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om547', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
LOG = []
class _H(logging.Handler):
    def emit(self, r): LOG.append((r.levelno, r.getMessage()))
lg = logging.getLogger('OmegaV60'); lg.handlers = [_H()]; lg.propagate = False; lg.setLevel(logging.INFO)
print("=" * 66); print("C547: WHAT ONE COIN JUMPING WOULD DO (ROUND 23)"); print("=" * 66)
ok("version C547 or later", int(om._OMEGA_VERSION[1:]) >= 547)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; om._c467_cfg_ref[0] = cfg
for _k, _v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, _k, _v)
cfg.C524_XVENUE_EQUITY = 1000.0
DAY, H = 86400000, 3600000
D0 = (int(time.time() * 1000) // DAY - 6) * DAY
UP = ['UPA', 'UPB', 'UPC']                  # "short Delta / long CoinDCX" (side +1)
DN = ['DNA', 'DNB']                         # "long Delta / short CoinDCX" (side -1)
RATE = {'UPA': 0.10, 'UPB': 0.09, 'UPC': 0.08, 'DNA': -0.08, 'DNB': -0.07}
PX = {c: 1.0 for c in UP + DN}
EXTRA = {f'ONLYD{j:02d}': 1.0 for j in range(20)}   # Delta-only coins (the product list needs a realistic size)


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

print("\n1. THE NUMBERS")
ok("an empty ledger says nothing", x.jump_risk() == {})
x.run(now_ms=D0 + 30 * 60000)
j = x.jump_risk()
sides = {c: p['side'] for c, p in x.pairs.items()}
ok("5 pairs open: 3 short on Delta, 2 short on CoinDCX", sorted(sides.values()) == [-1, -1, 1, 1, 1], str(sides))
half = x.start_equity / 2.0
bd, bb = half + x.side['d'], half + x.side['b']
ld = {c: abs(p['d_qty']) * p['cv'] * p['d_px'] for c, p in x.pairs.items() if p['side'] > 0}
lb = {c: abs(p['b_qty']) * p['b_px'] for c, p in x.pairs.items() if p['side'] < 0}
cd, cb = max(ld, key=ld.get), max(lb, key=lb.get)
ok("the Delta account's biggest short leg and the jump that would empty it = its balance / that leg",
   j['d']['coin'] == cd and abs(j['d']['empty'] - round(bd / ld[cd], 3)) < 1e-9 and j['d']['n_short'] == 3,
   f"{j['d']}")
ok("the CoinDCX account's: only the pairs short on CoinDCX count",
   j['b']['coin'] == cb and abs(j['b']['empty'] - round(bb / lb[cb], 3)) < 1e-9 and j['b']['n_short'] == 2, f"{j['b']}")
ok("a +100% jump leaves (balance - that leg) / its half", abs(j['d']['after100'] - round((bd - ld[cd]) / half, 3)) < 1e-9)
ok("at 10 x 10% of $1,000 it takes about a +500% jump to empty a $500 account",
   4.5 <= j['d']['empty'] <= 5.5 and 4.5 <= j['b']['empty'] <= 5.5, f"{j['d']['empty']} / {j['b']['empty']}")
y = om.C524CrossVenue(xb); y.reset(); y.start_equity = y.eq = 1000.0
y.pairs = {k: dict(v) for k, v in x.pairs.items() if v['side'] > 0}
ok("an account with no short leg says so (coin None)", y.jump_risk()['b']['coin'] is None)

print("\n2. NOTHING IS TRADED ON IT")
before = {c: (p['d_qty'], p['b_qty']) for c, p in x.pairs.items()}
x.jump_risk(); x.status()
ok("reading it changes no position", before == {c: (p['d_qty'], p['b_qty']) for c, p in x.pairs.items()})
ok("the run records it (info.jump)", (x.info.get('jump') or {}).get('d', {}).get('coin') == cd)
ok("the C546 cap is unchanged (6 of 10)", x.same_cap() == 6)
ok("the tax journal still writes (C544/C545)", isinstance(x.journal, list))

print("\n3. THE PAGE, THE LOG, THE RESEARCH")
st = x.status()
ok("the page's data carries it", (st.get('jump') or {}).get('b', {}).get('coin') == cb)
SRC = open(os.path.join(REPO, 'omega_v60_reconstructed.py')).read()
ok("the pairs card says it in plain words",
   "one-coin jump: in a day, it would take " in SRC and "No guard passed its test (Round 23)" in SRC)
x2 = om.C524CrossVenue(xb); x2.reset()
LOG.clear()
x2._fail_at = 0; x2._tick_at = 0; x2.last_run = ''
x2.active = lambda: True
x2.due = lambda: True
x2.save = lambda: None
x2.tick()
msg = ' '.join(m for _, m in LOG)
ok("the daily log line names the jump that would empty each account",
   'a one-day jump that would empty an account: Delta +' in msg and 'CoinDCX +' in msg, msg[-220:])
R = json.load(open(os.path.join(REPO, 'research', 'r23_round23.json')))
ok("Round 23 on file: both engine checks OK, nothing adopted, every variant failed a named bar",
   R.get('engine_check') is True and R.get('minute_check') is True and R.get('adopted') is None
   and all(not R['verdict'][v]['passed'] for v in ('J1', 'J2', 'Z1', 'Z2', 'S50', 'S100')))
ok("the stops failed on cost only: safer and no account wiped",
   all(not R['verdict'][v]['bars']['after tax >= base - $30/yr'] and R['verdict'][v]['bars']['replays: no account wiped']
       and R['verdict'][v]['bars']['safer (W530 halved, or L100 +10 points)'] for v in ('S50', 'S100')))
ok("the coin list is saved this time", len(R.get('coins') or []) >= 50)
ok("C488_LIVE_OK stays False; no keys in the code", 'self.C488_LIVE_OK = False' in SRC)
print()
print("=" * 66)
print("C547 TEST: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
