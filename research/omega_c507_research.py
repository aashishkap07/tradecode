#!/usr/bin/env python3
"""C507 round 10 (research/c507_preregistration.md): N1 momentum long-only, N2 no
shorting a crowded short, N3 residual momentum; and the base's C2 legs measured.

    python3 research/omega_c507_research.py BNC_DIR [--out results.json]
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
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
n = len(T)


def c1_trend():
    tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    return R.banded(np.where(elig, tr * sc / N, 0.0))


def fsum(k):
    f = np.full_like(fund, np.nan)
    for i in range(k, len(fund)):
        f[i] = fund[i - k + 1:i + 1].sum(axis=0)
    f[np.isnan(close)] = np.nan
    return f


def c2_from_rank(s):
    return R.weekly(s * sc / (2 * N * 0.2), T)


def c3():
    return R.weekly(-R.xs_rank(fsum(7), elig) * sc / (2 * N * 0.2), T)


def run(parts):
    Wc = R.combine(parts, r, fund, 1, target_vol=0.20)
    Wc = np.where(np.abs(Wc) * EQ >= FLOOR, Wc, 0.0)
    return R.pnl(Wc, r, fund, 1)


s_base = R.xs_rank(R.lagret(close, 14), elig)
base_parts = {'C1': c1_trend(), 'C2': c2_from_rank(s_base), 'C3': c3()}
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
    print(f"  {name:44} net {100*s['ann']:+6.1f}%/yr Sharpe {s['sharpe']:.2f} maxDD {100*mk:4.1f}% "
          f"months>=2% {100*(mv>=0.02).mean():3.0f}%  worst {100*mv.min():+.1f}%")
    print(f"  {'':44} vs base: {100*d.mean()*365:+6.2f}%/yr  NW t {t:+.2f}  quarters+ {q}/4  "
          f"holdout 2025-26 {100*hold*365:+.2f}%/yr  -> {'ADMIT' if adm else 'not admitted'}")
    return dict(ann=s['ann'], sharpe=s['sharpe'], maxdd=mk, p_month_ge2=float((mv >= 0.02).mean()),
                worst_month=float(mv.min()), diff_ann=float(d.mean() * 365), t=float(t), quarters=int(q),
                holdout_ann=float(hold * 365), admit=adm)


print("=" * 110)
print(f"C507 ROUND 10 | crypto only, top {N}, dial 15% (vol 20%), $6 floor at $250 | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()}")
print("=" * 110)
sb = R.stats(xb, T); mvb = months(xb[live:])
print(f"  {'BASE (what runs)':44} net {100*sb['ann']:+6.1f}%/yr Sharpe {sb['sharpe']:.2f} maxDD {100*maxdd(xb[live:]):4.1f}% "
      f"months>=2% {100*(mvb>=0.02).mean():3.0f}%  worst {100*mvb.min():+.1f}%")
res = {'base': dict(ann=sb['ann'], sharpe=sb['sharpe'], maxdd=maxdd(xb[live:]))}

# the base's C2 legs, each on its own (unit weights, costs and funding charged)
for lab, s_leg in (('long leg', np.maximum(s_base, 0)), ('short leg', np.minimum(s_base, 0))):
    W = c2_from_rank(s_leg)
    x = R.pnl(W, r, fund, 1)[0][live:]
    ann = x.mean() * 365; vol = x.std() * math.sqrt(365)
    t = R.nw_t(x)
    yrs = {}
    for tt_, v in zip(TT, x):
        y = dt.datetime.utcfromtimestamp(tt_ / 1000).year; yrs[y] = yrs.get(y, 0.0) + v
    print(f"  C2 {lab:10} alone (unit size): {100*ann:+6.1f}%/yr on {100*vol:.0f}% vol, Sharpe {ann/vol:.2f}, NW t {t:+.2f} | by year: "
          + " ".join(f"{y} {100*v:+.0f}%" for y, v in sorted(yrs.items())))
    res[f'C2_{lab.replace(" ", "_")}'] = dict(ann=float(ann), vol=float(vol), t=float(t), years={str(k): float(v) for k, v in yrs.items()})

# N1 -- long-only momentum
print("\nN1 momentum long-only")
n1 = dict(base_parts); n1['C2'] = c2_from_rank(np.maximum(s_base, 0))
res['N1'] = judge('N1 C2 long leg only', run(n1)[0])

# N2 -- no shorting a crowded short (7-day funding < 0)
f7 = fsum(7)
crowded = (s_base < 0) & (np.nan_to_num(f7, nan=0.0) < 0)
print(f"\nN2 crowded-short filter: removes {100*crowded[live:].sum()/max(1,(s_base[live:]<0).sum()):.0f}% of C2 short signals")
n2 = dict(base_parts); n2['C2'] = c2_from_rank(np.where(crowded, 0.0, s_base))
res['N2'] = judge('N2 no C2 short where 7d funding < 0', run(n2)[0])

# N3 -- residual momentum: r14 - beta * market r14
mkt = np.nanmean(np.where(elig, np.nan_to_num(r, nan=np.nan), np.nan), axis=1); mkt = np.nan_to_num(mkt)
beta = np.ones_like(close)
for i in range(60, n):
    m = mkt[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r[i - 59:i + 1]
    ok = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm
    b[ok.sum(0) < 40] = np.nan
    beta[i] = np.where(np.isnan(b), 1.0, b)
m14 = np.full(n, np.nan)
for i in range(14, n):
    m14[i] = np.prod(1 + mkt[i - 13:i + 1]) - 1
resid = R.lagret(close, 14) - beta * m14[:, None]
print(f"\nN3 residual momentum: median beta {np.nanmedian(beta[live:][elig[live:]]):.2f}")
n3 = dict(base_parts); n3['C2'] = c2_from_rank(R.xs_rank(resid, elig))
res['N3'] = judge('N3 C2 on residual 14d return', run(n3)[0])
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
