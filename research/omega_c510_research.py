#!/usr/bin/env python3
"""C510 round 11 (research/c510_preregistration.md): the idle scanner's information
as a sensor -- V1 Parkinson and V2 Garman-Klass range volatility (EWMA, 10-day
half-life) for the per-coin risk scale; plus, DESCRIPTIVE ONLY, round 10's N2 and
N3 combined, with and without K4 sizing, at dial 15% and 20%.

    python3 research/omega_c510_research.py BNC_DIR [--out results.json]
"""
import os, sys, json, glob, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
rng = np.random.default_rng(510)


def load_ohlc(bdir):
    """R.load_crypto, unchanged, plus the open, high and low of each day"""
    syms, K, F = [], {}, {}
    for p in sorted(glob.glob(os.path.join(bdir, 'k', '*.json'))):
        s = os.path.basename(p)[:-5]
        if s in R.EXCLUDE:
            continue
        rows = json.load(open(p))
        if len(rows) < R.AGE + 30:
            continue
        K[s] = rows
        fp = os.path.join(bdir, 'f', s + '.json')
        F[s] = json.load(open(fp)) if os.path.exists(fp) else []
        syms.append(s)
    t0 = min(r[0] for s in syms for r in K[s][:1]) // R.DAY * R.DAY
    t1 = max(r[0] for s in syms for r in K[s][-1:]) // R.DAY * R.DAY
    T = np.arange(t0, t1 + R.DAY, R.DAY)
    idx = {t: i for i, t in enumerate(T)}
    n, k = len(T), len(syms)
    close, qv, fund = np.full((n, k), np.nan), np.full((n, k), np.nan), np.zeros((n, k))
    op, hi, lo = np.full((n, k), np.nan), np.full((n, k), np.nan), np.full((n, k), np.nan)
    for j, s in enumerate(syms):
        for r in K[s]:
            i = idx.get(r[0] // R.DAY * R.DAY)
            if i is not None:
                op[i, j], hi[i, j], lo[i, j], close[i, j], qv[i, j] = r[1], r[2], r[3], r[4], r[6]
        for t, rate in F[s]:
            i = idx.get(t // R.DAY * R.DAY)
            if i is not None:
                fund[i, j] += rate
    return T, syms, close, qv, fund, op, hi, lo


T, syms, close, qv, fund, op, hi, lo = load_ohlc(sys.argv[1])
T2, syms2, close2, qv2, fund2 = R.load_crypto(sys.argv[1])
assert syms == syms2 and np.array_equal(np.nan_to_num(close), np.nan_to_num(close2)) \
    and np.array_equal(np.nan_to_num(qv), np.nan_to_num(qv2)) and np.array_equal(fund, fund2), \
    "the OHLC loader must reproduce R.load_crypto exactly"
del close2, qv2, fund2
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
N = R.TOPN; n = len(T)


def ewma_sd(x, hl=10.0, min_obs=20):
    """per-coin EWMA of a daily variance proxy x (n, k), past and today only"""
    a = 1.0 - 0.5 ** (1.0 / hl)
    out = np.full_like(x, np.nan)
    v = np.zeros(x.shape[1]); seen = np.zeros(x.shape[1], int)
    for i in range(len(x)):
        ok = ~np.isnan(x[i])
        v = np.where(ok, np.where(seen > 0, (1 - a) * v + a * np.nan_to_num(x[i]), np.nan_to_num(x[i])), v)
        seen = seen + ok
        out[i] = np.where((seen >= min_obs) & ~np.isnan(close[i]), np.sqrt(np.maximum(v, 0.0)), np.nan)
    return out


with np.errstate(divide='ignore', invalid='ignore'):
    lhl = np.log(hi / lo); lco = np.log(close / op)
    bad = ~(np.isfinite(lhl) & (lhl >= 0))
    lhl[bad] = np.nan; lco[bad] = np.nan
    park = lhl ** 2 / (4 * math.log(2))
    gk = np.maximum(0.5 * lhl ** 2 - (2 * math.log(2) - 1) * lco ** 2, 0.0)
    gk[np.isnan(lhl)] = np.nan
sd_v1 = ewma_sd(park); sd_v2 = ewma_sd(gk)


def scale(sd_new):
    """the pre-registered fallback: the base's sd where the range estimate is not ready"""
    return np.nan_to_num(R.vol_scale(np.where(np.isnan(sd_new), sd, sd_new)))


sc0 = np.nan_to_num(R.vol_scale(sd))


def fsum(k):
    f = np.full_like(fund, np.nan)
    for i in range(k, len(fund)):
        f[i] = fund[i - k + 1:i + 1].sum(axis=0)
    f[np.isnan(close)] = np.nan
    return f


f7 = fsum(7)


def sleeves(sc, c2rank):
    tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    return {'C1': R.banded(np.where(elig, tr * sc / N, 0.0)),
            'C2': R.weekly(c2rank * sc / (2 * N * 0.2), T),
            'C3': R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)}


def combine_ewma(parts, target_vol=0.20, lev_cap=3.0, win=60, periods=365, hl=10.0):
    """omega_c500_research.combine_ewma (K4), verbatim in substance"""
    a = 1.0 - 0.5 ** (1.0 / hl)
    unit = {k: R.pnl(w, r, fund, 1)[0] for k, w in parts.items()}

    def ew_sd(u):
        out = np.full(n, np.nan); v = 0.0; seen = 0
        for i in range(n):
            if i >= win and seen >= win and v > 0:
                out[i] = math.sqrt(v)
            x = u[i]
            if x != 0.0 or seen:
                v = (1 - a) * v + a * x * x if seen else x * x
                seen += 1
        return out
    sw = {k: np.nan_to_num(1.0 / ew_sd(u)) / len(unit) for k, u in unit.items()}
    comb = sum(sw[k] * unit[k] for k in unit)
    s = ew_sd(comb)
    L = np.nan_to_num(np.where(np.arange(n) >= 2 * win, target_vol / (s * math.sqrt(periods)), 0.0))
    W = sum((sw[k] * L)[:, None] * parts[k] for k in parts)
    g = np.abs(W).sum(1)
    return W * np.where(g > lev_cap, lev_cap / np.maximum(g, 1e-12), 1.0)[:, None]


def run(parts, dial=15.0, k4=False):
    tv = dial * 4.0 / 3.0 / 100.0
    Wc = combine_ewma(parts, target_vol=tv) if k4 else R.combine(parts, r, fund, 1, target_vol=tv)
    Wc = np.where(np.abs(Wc) * EQ >= FLOOR, Wc, 0.0)
    x, info = R.pnl(Wc, r, fund, 1)
    return x, info['gross_exp']


# the C2 rankings: base, N2 (no crowded short), N3 (residual momentum) -- exactly as C507
s_base = R.xs_rank(R.lagret(close, 14), elig)
crowded = (s_base < 0) & (np.nan_to_num(f7, nan=0.0) < 0)
s_n2 = np.where(crowded, 0.0, s_base)
mkt = np.nan_to_num(np.nanmean(np.where(elig, np.nan_to_num(r, nan=np.nan), np.nan), axis=1))
beta = np.ones_like(close)
for i in range(60, n):
    m = mkt[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r[i - 59:i + 1]; ok = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm; b[ok.sum(0) < 40] = np.nan
    beta[i] = np.where(np.isnan(b), 1.0, b)
m14 = np.full(n, np.nan)
for i in range(14, n):
    m14[i] = np.prod(1 + mkt[i - 13:i + 1]) - 1
s_n3 = R.xs_rank(R.lagret(close, 14) - beta * m14[:, None], elig)
# N2+N3: residual ranking, and no short where the crowd already is
s_n23 = np.where((s_n3 < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s_n3)

xb, gb = run(sleeves(sc0, s_base))
live = np.nonzero(np.abs(xb) > 0)[0][0]
TT = T[live:]


def maxdd(x):
    e = np.cumprod(1 + x); return float((1 - e / np.maximum.accumulate(e)).max())


def months(y):
    m = {}
    for t, v in zip(TT, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


def years(y):
    m = {}
    for t, v in zip(TT, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).year; m[k] = m.get(k, 1.0) * (1 + v)
    return {k: v - 1 for k, v in sorted(m.items())}


def judge(name, x):
    d = (x - xb)[live:]; t = R.nw_t(d)
    q = sum(v.mean() > 0 for v in np.array_split(d, 4))
    hold = d[TT >= HOLD].mean()
    mb, mk = maxdd(xb[live:]), maxdd(x[live:])
    adm = bool(t >= 1.96 and q >= 3 and hold > 0 and mk <= mb + 0.02)
    s = R.stats(x, T); mv = months(x[live:])
    print(f"  {name:44} net {100*s['ann']:+6.1f}%/yr Sharpe {s['sharpe']:.2f} maxDD {100*mk:4.1f}% "
          f"months>=2% {100*(mv>=0.02).mean():3.0f}%  worst month {100*mv.min():+.1f}%  worst day {100*x[live:].min():+.1f}%")
    print(f"  {'':44} vs base: {100*d.mean()*365:+6.2f}%/yr  NW t {t:+.2f}  quarters+ {q}/4  "
          f"holdout 2025-26 {100*hold*365:+.2f}%/yr  -> {'ADMIT' if adm else 'not admitted'}")
    return dict(ann=s['ann'], sharpe=s['sharpe'], maxdd=mk, p_month_ge2=float((mv >= 0.02).mean()),
                worst_month=float(mv.min()), worst_day=float(x[live:].min()), diff_ann=float(d.mean() * 365),
                t=float(t), quarters=int(q), holdout_ann=float(hold * 365), admit=adm)


print("=" * 118)
print(f"C510 ROUND 11 | crypto only, top {N}, dial 15% (vol 20%), $6 floor at $250 | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()}")
print("=" * 118)
sb = R.stats(xb, T); mvb = months(xb[live:])
print(f"  {'BASE (what runs)':44} net {100*sb['ann']:+6.1f}%/yr Sharpe {sb['sharpe']:.2f} maxDD {100*maxdd(xb[live:]):4.1f}% "
      f"months>=2% {100*(mvb>=0.02).mean():3.0f}%  worst month {100*mvb.min():+.1f}%  worst day {100*xb[live:].min():+.1f}%")
res = {'base': dict(ann=sb['ann'], sharpe=sb['sharpe'], maxdd=maxdd(xb[live:]))}
cov1 = np.mean(~np.isnan(sd_v1[live:][elig[live:]])); cov2 = np.mean(~np.isnan(sd_v2[live:][elig[live:]]))
ratio = np.nanmedian((sd_v1 / sd)[live:][elig[live:]])
print(f"\n  range estimates ready on {100*cov1:.1f}% / {100*cov2:.1f}% of eligible coin-days; "
      f"median Parkinson sd / 30-day sd = {ratio:.2f}")
print("\nV1 Parkinson range volatility (EWMA, 10-day half-life)")
res['V1'] = judge('V1 per-coin sd from (ln H/L)^2', run(sleeves(scale(sd_v1), s_base))[0])
print("\nV2 Garman-Klass range volatility (EWMA, 10-day half-life)")
res['V2'] = judge('V2 per-coin sd from Garman-Klass', run(sleeves(scale(sd_v2), s_base))[0])


# ── DESCRIPTIVE ONLY: the round-10 variants combined, as the bot will score them forward ──
def savings(gross, dial, apr=0.05):
    idle = np.clip(1.0 - gross / 5.0 - dial / 100.0 - 0.05, 0.0, 1.0)
    return idle * apr / 365.0


def boot_years(y, horizon_days=365, reps=10000, block=30):
    nb = int(math.ceil(horizon_days / block)); out = np.empty(reps)
    starts = rng.integers(0, len(y) - block, size=(reps, nb))
    for k in range(reps):
        out[k] = np.prod(1 + np.concatenate([y[a:a + block] for a in starts[k]])[:horizon_days]) - 1
    return out


def describe(name, x):
    y = x[live:]; mv = months(y); need = 1.02 ** 12 - 1
    hair = y - y.mean() / 3.0
    pb = float((boot_years(y) >= need).mean()); ph = float((boot_years(hair) >= need).mean())
    yr = years(y)
    print(f"  {name:34} {100*(np.prod(1+y)**(365/len(y)/12)-1):+5.2f}%/mo | months>=2% {100*(mv>=0.02).mean():3.0f}% "
          f"<0 {100*(mv<0).mean():3.0f}% | year avg>=2%/mo: boot {100*pb:3.0f}% haircut {100*ph:3.0f}% | "
          f"worst month {100*mv.min():+5.1f}% maxDD {100*maxdd(y):4.1f}% | "
          + " ".join(f"{k}:{100*v:+.0f}%" for k, v in yr.items()))
    return dict(month=float(np.prod(1 + y) ** (365 / len(y) / 12) - 1), p_month_ge2=float((mv >= 0.02).mean()),
                p_month_neg=float((mv < 0).mean()), p_year_boot=pb, p_year_haircut=ph,
                worst_month=float(mv.min()), maxdd=maxdd(y), years={str(k): v for k, v in yr.items()})


print("\n" + "=" * 118)
print("DESCRIPTIVE ONLY (chosen after seeing round 10; cannot be admitted on this data) -- book + idle cash in Savings at 5%/yr")
print("=" * 118)
res['descriptive'] = {}
for dial in (15.0, 20.0):
    for lab, rank, k4 in (('base', s_base, False), ('N2', s_n2, False), ('N3', s_n3, False),
                          ('N2+N3', s_n23, False), ('base, K4 sizing', s_base, True), ('N2+N3, K4 sizing', s_n23, True)):
        x, g = run(sleeves(sc0, rank), dial=dial, k4=k4)
        key = f"{lab} @ dial {dial:.0f}%"
        res['descriptive'][key] = describe(key, x + savings(g, dial))
    print()
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
