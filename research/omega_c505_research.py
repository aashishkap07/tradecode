#!/usr/bin/env python3
"""C505 round 9 (research/c505_preregistration.md): L1 chaos (variance-ratio
trend gate), L2 information (dispersion-scaled momentum), L3 control (drawdown
feedback on the whole book).

    python3 research/omega_c505_research.py BNC_DIR [--out results.json]
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
r = R.returns(close)
sd = R.trailing_std(r, 30)
elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd))
N = R.TOPN
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
n = len(T)


# ── the base, exactly as omega_c500_research.py builds it ────────────────────
def c1_trend(gate=None):
    tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    g = 1.0 if gate is None else gate
    return R.banded(np.where(elig, tr * sc / N * g, 0.0))


def fsum(k):
    f = np.full_like(fund, np.nan)
    for i in range(k, len(fund)):
        f[i] = fund[i - k + 1:i + 1].sum(axis=0)
    f[np.isnan(close)] = np.nan
    return f


def c2(mult=None):
    s = R.xs_rank(R.lagret(close, 14), elig)
    tgt = s * sc / (2 * N * 0.2)
    if mult is not None:
        tgt = tgt * mult[:, None]
    return R.weekly(tgt, T)


def c3():
    return R.weekly(-R.xs_rank(fsum(7), elig) * sc / (2 * N * 0.2), T)


def run(parts):
    Wc = R.combine(parts, r, fund, 1, target_vol=0.20)
    Wc = np.where(np.abs(Wc) * EQ >= FLOOR, Wc, 0.0)
    return R.pnl(Wc, r, fund, 1)


base_parts = {'C1': c1_trend(), 'C2': c2(), 'C3': c3()}
xb, db = run(base_parts)
live = np.nonzero(np.abs(xb) > 0)[0][0]
TT = T[live:]


def maxdd(x):
    eq = np.cumprod(1 + x); return float((1 - eq / np.maximum.accumulate(eq)).max())


def months(y):
    m = {}
    for t, v in zip(TT, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


def judge(name, x):
    d = (x - xb)[live:]; t = R.nw_t(d)
    q = sum(v.mean() > 0 for v in np.array_split(d, 4))
    hold = d[TT >= HOLD].mean()
    mb, mk = maxdd(xb[live:]), maxdd(x[live:])
    adm = bool(t >= 2.13 and q >= 3 and hold > 0 and mk <= mb + 0.02)
    s = R.stats(x, T); mv = months(x[live:])
    print(f"  {name:46} net {100*s['ann']:+6.1f}%/yr Sharpe {s['sharpe']:.2f} maxDD {100*mk:4.1f}% "
          f"months>=2% {100*(mv>=0.02).mean():3.0f}%  >=0 {100*(mv>=0).mean():3.0f}%  worst {100*mv.min():+.1f}%")
    print(f"  {'':46} vs base: {100*d.mean()*365:+6.2f}%/yr  NW t {t:+.2f}  quarters+ {q}/4  "
          f"holdout 2025-26 {100*hold*365:+.2f}%/yr  -> {'ADMIT' if adm else 'not admitted'}")
    return dict(ann=s['ann'], sharpe=s['sharpe'], maxdd=mk, p_month_ge2=float((mv >= 0.02).mean()),
                p_month_ge0=float((mv >= 0).mean()), worst_month=float(mv.min()),
                diff_ann=float(d.mean() * 365), t=float(t), quarters=int(q), holdout_ann=float(hold * 365), admit=adm)


print("=" * 110)
print(f"C505 ROUND 9 | crypto only, top {N}, dial 15% (vol 20%), $6 floor at $250 | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()}")
print("=" * 110)
sb = R.stats(xb, T); mvb = months(xb[live:])
print(f"  {'BASE (what runs)':46} net {100*sb['ann']:+6.1f}%/yr Sharpe {sb['sharpe']:.2f} maxDD {100*maxdd(xb[live:]):4.1f}% "
      f"months>=2% {100*(mvb>=0.02).mean():3.0f}%  >=0 {100*(mvb>=0).mean():3.0f}%  worst {100*mvb.min():+.1f}%")
res = {'base': dict(ann=sb['ann'], sharpe=sb['sharpe'], maxdd=maxdd(xb[live:]),
                    p_month_ge2=float((mvb >= 0.02).mean()), worst_month=float(mvb.min()))}

# L1 -- chaos: variance-ratio (Hurst) gate on the trend sleeve
r7 = R.lagret(close, 7)
vr = np.full_like(close, np.nan)
for i in range(120, n):
    v1 = np.nanvar(r[i - 119:i + 1], axis=0)
    v7 = np.nanvar(r7[i - 119:i + 1], axis=0)
    vr[i] = np.where(v1 > 0, v7 / (7.0 * v1), np.nan)
gate = np.where(np.nan_to_num(vr, nan=1.0) > 1.0, 1.0, 0.5)
pers = (np.nan_to_num(vr) > 1.0)[live:][elig[live:]]
print(f"\nL1 variance ratio > 1 (persistent, H > 0.5) on {100*pers.mean():.0f}% of eligible coin-days")
l1 = dict(base_parts); l1['C1'] = c1_trend(gate)
res['L1'] = judge('L1 trend kept where VR>1, halved where not', run(l1)[0])

# L2 -- information: dispersion-scaled momentum
r14 = R.lagret(close, 14)
disp = np.array([np.nanstd(np.where(elig[i], r14[i], np.nan)) if elig[i].sum() >= 5 else np.nan for i in range(n)])
mult = np.ones(n)
for i in range(180, n):
    med = np.nanmedian(disp[i - 179:i + 1])
    if med > 0 and not np.isnan(disp[i]):
        mult[i] = min(1.5, max(0.5, disp[i] / med))
print(f"\nL2 dispersion multiplier: median {np.median(mult[live:]):.2f}, "
      f"at the 0.5 floor {100*(mult[live:] <= 0.5).mean():.0f}% / 1.5 cap {100*(mult[live:] >= 1.5).mean():.0f}% of days")
l2 = dict(base_parts); l2['C2'] = c2(mult)
res['L2'] = judge('L2 momentum x clip(dispersion/median, .5, 1.5)', run(l2)[0])

# L3 -- control: proportional drawdown feedback on the whole book
gross = db['gross_exp']
y = np.zeros(n); f = np.ones(n); eqv, peak = 1.0, 1.0; fprev = 1.0
for i in range(n):
    fi_1 = f[i - 1] if i else 1.0
    fi_2 = f[i - 2] if i > 1 else 1.0
    y[i] = fi_1 * xb[i] - abs(fi_1 - fi_2) * gross[i] * R.COST
    eqv *= 1 + y[i]; peak = max(peak, eqv)
    dd = 1 - eqv / peak
    f[i] = min(1.0, max(0.25, 1 - dd / 0.25))
print(f"\nL3 drawdown feedback: scale below 1 on {100*(f[live:] < 1).mean():.0f}% of days, "
      f"at the 0.25 floor {100*(f[live:] <= 0.25).mean():.0f}%")
res['L3'] = judge('L3 book x clip(1 - DD/25%, .25, 1)', y)
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
