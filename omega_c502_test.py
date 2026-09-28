#!/usr/bin/env python3
"""C502: the spot pot trades at Bitget SPOT's minimums, not the futures $6.

1. CONFIG: position floor $2, order minimum $1; the futures book keeps its $6.
2. THE REAL DAY (28 Sep 2026, weights rebuilt from Bitget history, both the bot
   and the research library agree to 0.0e+00): with C501's $6 the pot holds
   exactly what the server held (BNB $9.36, BTC $8.72, ETH $7.69); with C502 it
   holds the 18 coins at or above $2 (ARB $1.97 and TRUMP $1.89 are not opened).
3. THE MINIMUMS: a target under $2 is not opened, one at $2+ is; a change under
   $1 is not traded even where the 30% band would allow it; a position under $1
   cannot be sold (dust) and is kept; one above $1 whose trend turned is sold.
4. THE DECISION is the pre-registered one (research/c502_results.json).
"""
import os, sys, io, json, types, contextlib, importlib.util, tempfile, logging
import datetime as dt
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
os.environ['OMEGA_BASE_PATH'] = tempfile.mkdtemp(prefix='c502_test_')
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


spec = importlib.util.spec_from_file_location('om502', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
logging.getLogger('OmegaV60').handlers = [logging.NullHandler()]
print("=" * 66); print("C502: THE SPOT POT AT BITGET SPOT'S REAL MINIMUMS"); print("=" * 66)

print("\n1. CONFIG")
cfg = om.Config(); cfg.PAPER_MODE = True
ok("spot position floor $2, spot order minimum $1", cfg.C502_SPOT_FLOOR == 2.0 and cfg.C502_SPOT_MIN_ORDER == 1.0)
ok("  the futures book keeps Bitget futures' $6 floor", cfg.C488_MIN_NOTIONAL == 6.0)

# the 28 Sep 2026 weights (fresh Bitget history, last complete day 27 Sep)
REAL = dict(BNB=3.74, BTC=3.49, ETH=3.08, LINK=2.34, SOL=2.31, XRP=2.21, DOGE=2.10, ADA=1.82, SUI=1.78, UNI=1.51,
            TAO=1.43, ONDO=1.40, PEPE=1.32, NEAR=1.23, PUMP=1.22, HYPE=1.18, ZEC=1.09, ENA=1.03, ARB=0.79, TRUMP=0.76)
USD = dict(BNB=9.36, BTC=8.72, ETH=7.69, ARB=1.97, TRUMP=1.89)   # the dollar figures printed on 28 Sep
coins = list(REAL)
keep = [f"{c}/USDT:USDT" for c in coins]
W = {'w': np.array([USD[c] / 250.0 if c in USD else REAL[c] / 100.0 for c in coins])}
om._c501_s1_targets = lambda *a, **k: (W['w'], None)           # run() looks the rule up at call time
T = np.array([0]); M = (T, keep, np.ones((1, len(keep))), np.ones((1, len(keep))), np.zeros((1, len(keep))))
PX = {c + 'USDT': 1.0 for c in coins}


def pot(floor=None, order=None):
    c = om.Config(); c.PAPER_MODE = True
    if floor is not None:
        c.C502_SPOT_FLOOR = floor
    if order is not None:
        c.C502_SPOT_MIN_ORDER = order
    pf = om.Portfolio(c); pf.equity = pf.available_balance = 250.0
    bot = types.SimpleNamespace(cfg=c, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                                _c482_risk_guard=lambda: {'pct': 15.0})
    e = om.C488Engine(bot); e.reset(); bot.c488 = e
    e._last_M = (dt.datetime.utcnow().strftime('%Y-%m-%d'), 20, M)
    sp = om.C501Spot(bot)
    sp.bk = {s: (p, p) for s, p in PX.items()}                 # zero spread: the arithmetic is exact
    sp.book = lambda force=False: sp.bk
    return sp


print("\n2. THE REAL DAY, 28 SEP 2026")
old = pot(floor=6.0, order=6.0)
old.run()
held = {s[:-4]: round(p['qty'] * p['avg'], 2) for s, p in old.pos.items()}
ok("with C501's $6 the pot holds exactly what the server held", held == {'BNB': 9.36, 'BTC': 8.72, 'ETH': 7.69}, str(held))
new = pot()
new.run()
st = new.status()
ok("with C502 it holds the 18 coins at or above $2; ARB ($1.97) and TRUMP ($1.89) are not opened",
   len(new.pos) == 18 and 'ARBUSDT' not in new.pos and 'TRUMPUSDT' not in new.pos,
   f"{len(new.pos)} held, {st['invested_pct']}% invested")
ok("  invested 34.3% (the rule's 35.8% less ARB and TRUMP), against 10.3% at $6",
   abs(st['invested_pct'] - 34.3) < 0.1 and abs(old.status()['invested_pct'] - 10.3) < 0.1)

print("\n3. THE MINIMUMS")
sp = pot()
W['w'] = np.zeros(len(coins)); W['w'][coins.index('BNB')] = 1.90 / 250; W['w'][coins.index('BTC')] = 2.10 / 250
sp.run()
ok("a $1.90 target is not opened, a $2.10 one is", set(sp.pos) == {'BTCUSDT'}, str(sorted(sp.pos)))
W['w'][coins.index('BTC')] = 2.90 / 250                        # +$0.80: the band (30% = $0.87) ... under $1
sp.last_run = '2000-01-01'; q0 = sp.pos['BTCUSDT']['qty']; sp.run()
ok("a $0.80 change is not traded (under the $1 order minimum)", sp.pos['BTCUSDT']['qty'] == q0)
W['w'][coins.index('BTC')] = 3.30 / 250                        # +$1.20, above the band and the minimum
sp.last_run = '2000-01-01'; sp.run()
ok("  a $1.20 change is (the target is the pot's own equity x weight)", abs(sp.pos['BTCUSDT']['qty'] * 1.0 - 3.30) < 0.001,
   f"${sp.pos['BTCUSDT']['qty']:.4f}")
W['w'][coins.index('BTC')] = 0.0
sp.bk['BTCUSDT'] = (0.27, 0.27)                                 # BTC falls 73%: $3.30 -> $0.89
sp.last_run = '2000-01-01'; sp.run()
ok("a position worth $0.89 whose trend turned cannot be sold (under $1): it is kept, not lost",
   'BTCUSDT' in sp.pos, f"${sp.pos.get('BTCUSDT', {}).get('qty', 0) * 0.27:.2f}")
sp.bk['BTCUSDT'] = (0.50, 0.50)                                 # back to $1.65
sp.last_run = '2000-01-01'; cash0 = sp.cash; sp.run()
ok("  worth $1.65 it is sold", 'BTCUSDT' not in sp.pos and sp.cash > cash0 and sp.closed[-1]['coin'] == 'BTC')

print("\n4. THE DECISION")
res = json.load(open(os.path.join(REPO, 'research', 'c502_results.json')))
k = '$2 floor + $1 order minimum (C502)'
ok("research/c502_results.json: the $2 floor passes C501's four bars, so the pot adopts it",
   res['decision_adopt_2'] is True and res[k]['admit'] and res[k]['t'] >= 2.0 and res[k]['q'] >= 3
   and res[k]['hold'] > 0 and res[k]['dd'] <= 0.35,
   f"t {res[k]['t']:.2f}, quarters {res[k]['q']}/4, max DD {100 * res[k]['dd']:.1f}%")
ok("version C502 or later", int(om._OMEGA_VERSION[1:4]) >= 502)
print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
