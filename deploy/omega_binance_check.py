#!/usr/bin/env python3
"""C516: a READ-ONLY check of the bot's Binance feeds, run on the server.

It uses Binance's PUBLIC market data only: no API key, no order, no change to
the running bot. It imports a copy of the bot from a temporary folder, so no
log or state file of the live bot is touched. It then does what a Binance
rebalance would do, up to the plan, and prints what it found.

    sudo -u omega /home/omega/omega/venv/bin/python /home/omega/omega/deploy/omega_binance_check.py 500

The number is the paper equity to plan for (default 500). It takes 1-2
minutes: it loads 330 days of history for about 80 coins, as a rebalance does.
"""
import os, sys, io, time, shutil, tempfile, contextlib, importlib.util

EQ = float(sys.argv[1]) if len(sys.argv) > 1 else 500.0
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix='omega_binance_check_')
os.environ['OMEGA_BASE_PATH'] = TMP
shutil.copy(os.path.join(HERE, 'omega_v60_reconstructed.py'), TMP)
spec = importlib.util.spec_from_file_location('omega_bn_check', os.path.join(TMP, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
import numpy as np
import requests

ok_all = []


def say(ok, what, detail=''):
    ok_all.append(bool(ok))
    print(f"{'OK  ' if ok else 'FAIL'} {what}" + (f"  -- {detail}" if detail else ''))


print(f"C516 Binance check ({om._OMEGA_VERSION}), planning for ${EQ:.0f}, {time.strftime('%Y-%m-%d %H:%M:%S')}")
r = requests.get(om._C516_BN_FAPI + '/fapi/v1/time', timeout=15)
say(r.status_code == 200, f"fapi.binance.com answers ({r.status_code})")
if r.status_code != 200:
    sys.exit(1)

cfg = om.Config(); cfg.PAPER_MODE = True; cfg.VENUE = 'binance'; cfg.C380_MAX_MONTHLY_DD_PCT = 20.0
for k, v in om._C516_VENUE_DEFAULTS['binance'].items():
    setattr(cfg, k, v)
om._c467_cfg_ref[0] = cfg
pf = om.Portfolio(cfg); pf.equity = pf.available_balance = EQ
import types
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, _c462_state_settled=True, _c408_asset_class=lambda s: 'crypto',
                            exchange=types.SimpleNamespace(markets={}, get_current_price=lambda s: None),
                            _c482_risk_guard=lambda: {'pct': 20.0, 'month_eq0': EQ})
e = om.C488Engine(bot); e.reset()

t0 = time.time()
say(e.refresh_marks(force=True), f"prices: {len(e.marks)} USDT perpetuals (bid/ask, last, funding, 24 h volume)")
say(e.refresh_rules(force=True), f"contract rules: {len(e.rules)} perpetuals",
    'BTC min ${:g}, step {:g}; ETH min ${:g}'.format(e._min_usdt('BTC/USDT:USDT'), e._step('BTC/USDT:USDT')[0],
                                                    e._min_usdt('ETH/USDT:USDT')))
# C516: what is quoted but is not a USDT-margined PERPETUAL (the 30 Sep check: 739 quoted, 658 in the table)
exi = requests.get(om._C516_BN_FAPI + '/fapi/v1/exchangeInfo', timeout=20).json().get('symbols') or []
from collections import Counter
ct = Counter((x.get('contractType'), x.get('quoteAsset'), x.get('marginAsset'), x.get('status')) for x in exi
             if str(x.get('symbol', '')).endswith('USDT'))
print("     exchangeInfo, USDT-named contracts by (type, quote, margin, status): "
      + '; '.join(f"{k}: {v}" for k, v in ct.most_common(8)))
gone = sorted(k.split('/')[0] for k in e.marks if k not in e.rules)
print(f"     quoted but not in the book's table ({len(gone)}): {', '.join(gone[:40])}")
big = sorted((round(v['min_usdt']), k.split('/')[0]) for k, v in e.rules.items() if v.get('min_usdt', 0) > 5)
print(f"     minimums above $5: {', '.join(f'{b} ${m}' for m, b in big) or 'none'}")
n_top = e.topn(EQ)
cands = e.candidates(n_top)
say(len(cands) >= 3 * n_top, f"candidates: {len(cands)} (the {n_top}-coin book fetches 4x its width)",
    ', '.join(c.split('/')[0] for c in cands[:12]) + ' ...')
# C516: stock, ETF, commodity and metal perps must never reach the book (the research is crypto only)
busy = [k for k in sorted(e.marks, key=lambda k: -e.marks[k].get('vol', 0.0)) if k in e.rules][:4 * n_top + 40]
out = [k.split('/')[0] for k in busy if not e._is_crypto(k)]
tradfi_in = [c.split('/')[0] for c in cands if c.split('/')[0].upper() in om._C516_TRADFI]
say(not tradfi_in, "no stock/ETF/commodity/metal perp among the candidates"
    + (f" -- FOUND {', '.join(tradfi_in)}" if tradfi_in else ''),
    f"left out among the busiest: {', '.join(out[:20]) or 'none'}")
labels = sorted({(e.rules[k].get('kind') or '-', e.rules[k].get('sub') or '-') for k in e.rules
                 if k.split('/')[0].upper() in om._C516_TRADFI})
print(f"     Binance's own labels on the research's non-crypto names (underlyingType / subType): "
      f"{'; '.join(f'{a} / {b}' for a, b in labels[:6]) or 'none listed'}")
tagged = [k.split('/')[0] for k in e.rules if k.split('/')[0].upper() not in om._C516_TRADFI
          and any(t in str(e.rules[k].get('sub') or '').upper() for t in om._C516_TRADFI_TAGS)]
print(f"     newer contracts caught by Binance's tag alone: {', '.join(sorted(tagged)[:20]) or 'none'}")
fails = []
t1 = time.time()
try:
    M = e.matrices(cands)
except Exception as ex:
    M = None
    fails.append(f"{type(ex).__name__}: {ex}")
if M is None:
    say(False, 'history', '; '.join(fails)[:300])
    sys.exit(1)
T, keep, close, qv, fund = M
yday = (int(time.time() * 1000) // om._C488_DAY - 1) * om._C488_DAY
say(int(T[-1]) == yday, f"history: {len(keep)} coins x {len(T)} days in {time.time() - t1:.0f}s; the last day is "
    f"yesterday, final (checked against its 23:59 minute)")
fdays = int(np.sum(np.any(~np.isnan(fund) & (fund != 0), axis=1)))
say(fdays >= 150, f"funding: settlements on {fdays} of the {len(T)} days")
w, sleeves, elig = om._c488_targets(T, close, qv, fund, n_top, e.target_vol(), 3.0, rule=e.c2_rule(),
                                     ohlc=e.ohlc_for(T, keep), volest=e.volest(), sizing=e.sizing())
plan = []
for s, x in zip(keep, np.nan_to_num(w)):
    usd = float(x) * EQ
    if abs(usd) < float(cfg.C488_MIN_NOTIONAL):
        continue
    px = e.mark(s)
    q = e.round_qty(s, usd / px) if px > 0 else 0.0
    plan.append((s.split('/')[0], usd, q * px, e._min_usdt(s)))
held = [p for p in plan if abs(p[2]) >= p[3] and p[2] != 0]
dropped = [p for p in plan if not (abs(p[2]) >= p[3] and p[2] != 0)]
say(not any(p[0].upper() in om._C516_TRADFI for p in plan), "the plan is crypto only")
say(len(held) > 0, f"today's plan at ${EQ:.0f}, dial 20% (paper, nothing is sent): {len(held)} positions, "
    f"gross ${sum(abs(p[2]) for p in held):.2f} ({sum(abs(p[2]) for p in held) / EQ:.2f}x)")
for b, usd, act, mn in sorted(held, key=lambda p: -abs(p[2])):
    print(f"     {b:10} target {usd:+8.2f}  held {act:+8.2f}")
if dropped:
    print("     too small for Binance's step or minimum: "
          + ', '.join(f"{b} {usd:+.2f} (min ${mn:g})" for b, usd, act, mn in dropped))
sp = om._c516_bn_spot_book()
say(len(sp) > 300, f"spot bid/ask (carry ledger, spot pot): {len(sp)} pairs")
sh = om.C489Shadow(types.SimpleNamespace(cfg=cfg, c488=e))
raw, got, flow, fund1 = sh._pull('BTCUSDT', 200)
say(len(got) >= 190 and len(flow) >= 190, f"shadow: BTC {len(got)} hourly candles, taker flow on {len(flow)} of them")
fi = e._bn_fund_interval('BTC/USDT:USDT')
say(fi in (1, 2, 4, 8), f"funding intervals (fundingInfo): BTC every {fi} h; "
    f"{sum(1 for v in (e._bn_fi or {}).values() if v != 8)} contracts on a shorter clock")
try:
    import ccxt
    x = ccxt.binanceusdm({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    mk = x.load_markets()
    sw = [k for k, m in mk.items() if m.get('swap') and m.get('quote') == 'USDT' and m.get('active')]
    say(len(sw) > 300, f"ccxt {ccxt.__version__} binanceusdm: {len(sw)} active USDT perpetuals")
except Exception as ex:
    say(False, f"ccxt binanceusdm ({type(ex).__name__}: {ex})")
w1 = requests.get(om._C516_BN_FAPI + '/fapi/v1/time', timeout=15).headers.get('X-MBX-USED-WEIGHT-1M')
print(f"     Binance request weight used this minute: {w1} of 2400; whole check {time.time() - t0:.0f}s")
print('ALL OK' if all(ok_all) else f"{ok_all.count(False)} CHECK(S) FAILED")
shutil.rmtree(TMP, ignore_errors=True)
