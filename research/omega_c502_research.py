#!/usr/bin/env python3
"""C502 (research/c502_preregistration.md): S1 exactly as admitted at C501, with
Bitget spot's real minimums -- a $2 position floor and a $1 order minimum --
against the $6 futures floor C501 carried over.

    python3 research/omega_c502_research.py BNC_DIR [--out results.json]
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd)); N = R.TOPN
EQ, CASH, COST_SPOT = 250.0, 0.05, 0.0010
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
zero = np.zeros_like(fund)

# ── S1 before any minimum (identical to research/omega_c501_research.py) ─────
s = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
W1 = R.banded(np.where(elig, np.maximum(s, 0.0) * sc / N, 0.0))
u = R.pnl(W1, r, zero, 1, cost=COST_SPOT)[0]
n = len(T); L = np.zeros(n)
for i in range(60, n):
    v = u[i - 60:i].std() * math.sqrt(365)
    L[i] = 0.20 / v if v > 0 else 0.0
W0 = W1 * L[:, None]
g = np.abs(W0).sum(1)
W0 = W0 * np.where(g > 1.0, 1.0 / np.maximum(g, 1e-12), 1.0)[:, None]
live = np.nonzero(L > 0)[0][0] + 1


def minimums(W, floor_usd, order_usd):
    """Positions under `floor_usd` are not opened (target 0); a change under
    `order_usd` cannot be placed, so the position stays as it was -- which also
    leaves a position already under `order_usd` unsellable (dust)."""
    out = np.zeros_like(W)
    prev = np.zeros(W.shape[1])
    for i in range(len(W)):
        tg = np.where(W[i] * EQ >= floor_usd, W[i], 0.0)
        if order_usd > 0:
            tg = np.where(np.abs(tg - prev) * EQ < order_usd, prev, tg)
        out[i] = tg
        prev = tg
    return out


def maxdd(y):
    e = np.cumprod(1 + y); return float((1 - e / np.maximum.accumulate(e)).max())


def months(y, tt):
    m = {}
    for t, v in zip(tt, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


def run(W):
    x_risk = R.pnl(W, r, zero, 1, cost=COST_SPOT)[0]
    gl = np.zeros(n); gl[1:] = np.abs(W).sum(1)[:-1]          # yesterday's decision is today's exposure
    x = (x_risk + (1.0 - gl) * CASH / 365.0)[live:]
    TT = T[live:]
    ex = x - CASH / 365.0
    t = R.nw_t(ex); q = int(sum(v.mean() > 0 for v in np.array_split(ex, 4)))
    hold = float(ex[TT >= HOLD].mean()); dd = maxdd(x)
    mv = months(x, TT)
    cagr = np.prod(1 + x) ** (365 / len(x)) - 1
    npos = (np.abs(W[live - 1:-1]) > 0).sum(1)
    return dict(x=x, TT=TT, t=float(t), q=q, hold=hold, dd=dd, cagr=float(cagr), mv=mv,
                sharpe=float(x.mean() / x.std() * math.sqrt(365)), exposure=float(gl[live:].mean()),
                npos=float(npos.mean()), turnover=float(np.abs(np.diff(W, axis=0)).sum(1)[live:].mean() * 365),
                admit=bool(t >= 2.0 and q >= 3 and hold > 0 and dd <= 0.35))


V = {'$6 floor (C501, as admitted)': run(np.where(np.abs(W0) * EQ >= 6.0, W0, 0.0)),
     '$6 floor + $1 order minimum': run(minimums(W0, 6.0, 1.0)),
     '$2 floor + $1 order minimum (C502)': run(minimums(W0, 2.0, 1.0)),
     'no minimum at all (reference)': run(W0)}
TT = V['$2 floor + $1 order minimum (C502)']['TT']
print("=" * 112)
print(f"C502 S1 SPOT TREND WITH BITGET SPOT'S REAL MINIMUMS | top 20 crypto, vol set point 20%, gross <= 1, 0.10% cost, cash 5% | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()}")
print("=" * 112)
for k, v in V.items():
    mv = v['mv']
    print(f"  {k}")
    print(f"      CAGR {100*v['cagr']:+.1f}%/yr = {100*((1+v['cagr'])**(1/12)-1):+.2f}%/month | Sharpe {v['sharpe']:.2f} | "
          f"max DD {100*v['dd']:.1f}% | excess NW t {v['t']:+.2f}, quarters+ {v['q']}/4, holdout {100*v['hold']*365:+.1f}%/yr "
          f"-> {'PASSES' if v['admit'] else 'fails'} C501's bars")
    print(f"      exposure {100*v['exposure']:.0f}% average, {v['npos']:.1f} coins held on average, turnover {v['turnover']:.1f}x/yr | "
          f"months: mean {100*mv.mean():+.2f}%, median {100*np.median(mv):+.2f}%, >= +2% {100*(mv>=0.02).mean():.0f}%, "
          f"worst {100*mv.min():+.1f}%, best {100*mv.max():+.1f}%")
    yrs = {}
    for tt_, y in zip(v['TT'], v['x']):
        yy = dt.datetime.utcfromtimestamp(tt_ / 1000).year; yrs[yy] = yrs.get(yy, 1.0) * (1 + y)
    v['years'] = {str(a): float(b - 1) for a, b in sorted(yrs.items())}
    print("      by year: " + "  ".join(f"{a} {100*b:+.0f}%" for a, b in v['years'].items()))

# ── the two pots together ────────────────────────────────────────────────────
r2, Wb, eb = R.crypto_sleeves(T, close, qv, fund)
Wc = R.combine({k: Wb[k] for k in ('C1', 'C2', 'C3')}, r2, fund, 1, target_vol=0.20)
Wc = np.where(np.abs(Wc) * EQ >= 6.0, Wc, 0.0)
xb = R.pnl(Wc, r2, fund, 1)[0][live:]
print()
for k in ('$6 floor (C501, as admitted)', '$2 floor + $1 order minimum (C502)'):
    x = V[k]['x']; both = 0.5 * xb + 0.5 * x; mb = months(both, TT)
    c2 = np.prod(1 + both) ** (365 / len(both)) - 1
    V[k]['both'] = dict(cagr=float(c2), maxdd=maxdd(both), worst_month=float(mb.min()), corr=float(np.corrcoef(xb, x)[0, 1]),
                        sharpe=float(both.mean() / both.std() * math.sqrt(365)), ge2=float((mb >= 0.02).mean()))
    b = V[k]['both']
    print(f"  both pots with {k:36}: {100*((1+c2)**(1/12)-1):+.2f}%/month, Sharpe {b['sharpe']:.2f}, max DD {100*b['maxdd']:.1f}%, "
          f"worst month {100*b['worst_month']:+.1f}%, months >= +2% {100*b['ge2']:.0f}%, correlation {b['corr']:+.2f}")
dec = V['$2 floor + $1 order minimum (C502)']['admit']
print(f"\n  DECISION (pre-registered): the $2 floor {'PASSES' if dec else 'FAILS'} C501's four bars -> "
      f"{'ADOPT it in the spot pot' if dec else 'the pot stays at $6'}")
if '--out' in sys.argv:
    out = {k: {a: b for a, b in v.items() if a not in ('x', 'TT', 'mv')} | dict(month_mean=float(v['mv'].mean()),
                                                                             month_worst=float(v['mv'].min()))
           for k, v in V.items()}
    out['decision_adopt_2'] = dec
    json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
