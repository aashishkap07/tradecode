#!/usr/bin/env python3
"""C498: what the C488 rule targets RIGHT NOW, computed by the bot's own code.

    python3 research/c498_plan_replay.py [EQUITY] [--dial 15] [--out FILE.json]

Runs the live bot's own C488Engine functions (candidates -> matrices ->
_c488_targets, the real asset classifier on Bitget's own market table) against
Bitget's public API, and prints the plan a rebalance at this moment would build:
every target with its sleeve parts, what falls under the $6 floor, the Monday
rankings the weekly sleeves (C2 momentum, C3 carry) hold, and how close each coin
sits to its sleeve's cutoff.

Why it exists: on 26 Sep the server's rebalance sold its 0.01 ETH (a target it
could no longer hold), yet the same completed days replayed later give ETH
+$17.42, i.e. one step held. The server logged only its trades, not its plan,
so the difference could not be traced. Run this within a minute of the 00:05 UTC
rebalance (same tickers, same completed days) and compare it with the server's
'C488 PLAN' line (C498+) or its trades.

Network: public endpoints only; no keys. requests/ccxt honour the proxy env.
"""
import io, os, sys, json, types, logging, tempfile, contextlib, importlib.util, datetime as dt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('OMEGA_BASE_PATH', tempfile.mkdtemp(prefix='c498_replay_'))
spec = importlib.util.spec_from_file_location('om', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)
logging.getLogger('OmegaV60').handlers = [logging.NullHandler()]
import ccxt

eq = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 250.0
dial = float(sys.argv[sys.argv.index('--dial') + 1]) if '--dial' in sys.argv else 15.0   # the operator's saved dial
x = ccxt.bitget({'options': {'defaultType': 'swap'}}); x.session.trust_env = True
mk = x.load_markets()
cfg = om.Config(); cfg.PAPER_MODE = True; cfg.C380_MAX_MONTHLY_DD_PCT = dial
pf = om.Portfolio(cfg); pf.equity = eq
ex = types.SimpleNamespace(markets=mk, exchange=types.SimpleNamespace(markets=mk))
bot = types.SimpleNamespace(cfg=cfg, portfolio=pf, exchange=ex, _c462_state_settled=True,
                            _c482_risk_guard=lambda: {'pct': float(cfg.C380_MAX_MONTHLY_DD_PCT)})
for k in ('_C411_INDEX', '_C411_METAL', '_C411_ENERGY', '_C411_US_LISTED', '_C411_KOREA'):
    setattr(bot, k, getattr(om.TradingBot, k))
bot._c408_asset_class = lambda s: om.TradingBot._c408_asset_class(bot, s)
e = om.C488Engine(bot)
assert e.refresh_marks(force=True), 'no tickers'
now = dt.datetime.utcnow()
n_top = e.topn(eq); syms = e.candidates(n_top)
T, keep, close, qv, fund = e.matrices(syms)
w, sl, el_now = om._c488_targets(T, close, qv, fund, n_top, e.target_vol(), float(getattr(cfg, 'C488_LEV_CAP', 3.0)))
mn = float(getattr(cfg, 'C488_MIN_NOTIONAL', 6.0))
elig = om._c488_universe(close, qv, n_top)
mi = max(i for i in range(len(T)) if dt.datetime.utcfromtimestamp(T[i] / 1000).weekday() == 0)
lr = om._c488_lagret(close, 14)
f7 = np.full_like(fund, np.nan)
for i in range(7, len(fund)):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan

print(f"C488 plan replay at {now:%Y-%m-%d %H:%M:%S} UTC | equity ${eq:.2f} | top {n_top} | vol target "
      f"{100 * e.target_vol():.0f}% | last completed day {dt.datetime.utcfromtimestamp(T[-1] / 1000).date()} | "
      f"weekly sleeves chosen on {dt.datetime.utcfromtimestamp(T[mi] / 1000).date()}")
print(f"candidates ({len(keep)}): {' '.join(s.split('/')[0] for s in keep)}")
rows = []
for j, s in enumerate(keep):
    wj = float(np.nan_to_num(w[j]))
    if abs(wj) < 1e-12:
        continue
    step, _ = e._step(s)
    px = e.mark(s)
    held = e.round_qty(s, wj * eq / px) if px > 0 and abs(wj) * eq >= mn else 0.0
    rows.append(dict(coin=s.split('/')[0], target=round(wj * eq, 2), c1=float(sl['C1'][j]), c2=float(sl['C2'][j]),
                     c3=float(sl['C3'][j]), in_plan=bool(abs(wj) * eq >= mn), qty=held,
                     held_usd=round(abs(held) * px, 2), step_usd=round(step * px, 2) if step else None))
rows.sort(key=lambda r: -abs(r['target']))
print(f"\n{'coin':8} {'target $':>9} {'C1':>8} {'C2':>8} {'C3':>8}  plan  held after rounding (step $)")
for r in rows:
    print(f"{r['coin']:8} {r['target']:+9.2f} {r['c1']:+8.4f} {r['c2']:+8.4f} {r['c3']:+8.4f}  "
          f"{'yes' if r['in_plan'] else 'no ($6)':7} {r['held_usd']:7.2f} ({r['step_usd']})")


def cut(sig, label, fmt):
    m = elig[mi] & ~np.isnan(sig[mi])
    v = sig[mi][m]
    lo, hi = np.quantile(v, [0.2, 0.8])
    print(f"\n{label} on {dt.datetime.utcfromtimestamp(T[mi] / 1000).date()}: {int(m.sum())} eligible; "
          f"bottom fifth <= {fmt(lo)}, top fifth >= {fmt(hi)}")
    order = [j for j in np.argsort(sig[mi]) if m[j]]
    print('   ' + ', '.join(f"{keep[j].split('/')[0]} {fmt(sig[mi][j])}" for j in order))
    return lo, hi


cut(lr, 'C2 momentum (14-day return; long top fifth, short bottom fifth)', lambda z: f"{100 * z:+.1f}%")
cut(f7, 'C3 carry (7-day funding; long bottom fifth, short top fifth)', lambda z: f"{1e4 * z:+.2f}bp")

if '--out' in sys.argv:
    json.dump(dict(at=now.isoformat(), equity=eq, candidates=[s.split('/')[0] for s in keep],
                   monday=str(dt.datetime.utcfromtimestamp(T[mi] / 1000).date()),
                   last_day=str(dt.datetime.utcfromtimestamp(T[-1] / 1000).date()), rows=rows),
              open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
