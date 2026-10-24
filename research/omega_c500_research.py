#!/usr/bin/env python3
"""C500 round 7 (research/c500_preregistration.md): K1 crash guard, K2 horizon
ensemble, K3 Ichimoku trend, K4 allostatic (EWMA) vol; M1 the first three days
in context; M2 the BTC option-selling premium.

    python3 research/omega_c500_research.py BNC_DIR [--out results.json]
"""
import os, sys, json, math, warnings, datetime as dt, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
B = sys.argv[1]
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
T, syms, close, qv, fund = R.load_crypto(B)
r = R.returns(close)
sd = R.trailing_std(r, 30)
elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd))
N = R.TOPN
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)


def c1_trend():
    tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    return R.banded(np.where(elig, tr * sc / N, 0.0))


def fsum(k):
    f = np.full_like(fund, np.nan)
    for i in range(k, len(fund)):
        f[i] = fund[i - k + 1:i + 1].sum(axis=0)
    f[np.isnan(close)] = np.nan
    return f


def c2(lbs=(14,)):
    s = sum(R.xs_rank(R.lagret(close, L), elig) for L in lbs) / len(lbs)
    return R.weekly(s * sc / (2 * N * 0.2), T)


def c3(wins=(7,)):
    s = sum(R.xs_rank(fsum(k), elig) for k in wins) / len(wins)
    return R.weekly(-s * sc / (2 * N * 0.2), T)


def combine_ewma(parts, lag=1, target_vol=0.20, lev_cap=3.0, win=60, periods=365, hl=10.0):
    """R.combine with both vol estimates as a zero-mean EWMA (RiskMetrics), half-life hl days, past only"""
    a = 1.0 - 0.5 ** (1.0 / hl)
    unit = {k: R.pnl(w, r, fund, lag)[0] for k, w in parts.items()}
    n = len(r)
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
    L = np.where(np.arange(n) >= 2 * win, target_vol / (s * math.sqrt(periods)), 0.0)
    L = np.nan_to_num(L)
    W = sum((sw[k] * L)[:, None] * parts[k] for k in parts)
    g = np.abs(W).sum(1)
    return W * np.where(g > lev_cap, lev_cap / np.maximum(g, 1e-12), 1.0)[:, None]


def run(parts, ewma=False):
    Wc = combine_ewma(parts) if ewma else R.combine(parts, r, fund, 1, target_vol=0.20)
    Wc = np.where(np.abs(Wc) * EQ >= FLOOR, Wc, 0.0)
    return R.pnl(Wc, r, fund, 1)


base_parts = {'C1': c1_trend(), 'C2': c2(), 'C3': c3()}
xb, db = run(base_parts)
live = np.nonzero(np.abs(xb) > 0)[0][0]


def maxdd(x):
    eq = np.cumprod(1 + x); return float((1 - eq / np.maximum.accumulate(eq)).max())


def judge(name, x):
    d = (x - xb)[live:]; t = R.nw_t(d); TT = T[live:]
    q = sum(v.mean() > 0 for v in np.array_split(d, 4))
    hold = d[TT >= HOLD].mean()
    mb, mk = maxdd(xb[live:]), maxdd(x[live:])
    adm = bool(t >= 2.24 and q >= 3 and hold > 0 and mk <= mb + 0.02)
    s = R.stats(x, T)
    print(f"  {name:40} net {100*s['ann']:+6.1f}%/yr Sharpe {s['sharpe']:.2f} maxDD {100*mk:4.1f}% "
          f"month {100*s['month_mean']:+.2f}% worst month {100*s['worst_month']:+.1f}%")
    print(f"  {'':40} vs base: {100*d.mean()*365:+6.2f}%/yr  NW t {t:+.2f}  quarters+ {q}/4  "
          f"holdout 2025-26 {100*hold*365:+.2f}%/yr  -> {'ADMIT' if adm else 'not admitted'}")
    return dict(ann=s['ann'], sharpe=s['sharpe'], maxdd=mk, month=s['month_mean'], worst_month=s['worst_month'],
                diff_ann=float(d.mean() * 365), t=float(t), quarters=int(q), holdout_ann=float(hold * 365), admit=adm)


print("=" * 100)
print(f"C500 ROUND 7 | crypto only, top {N}, dial 15% (vol 20%), $6 floor at $250 | "
      f"{dt.datetime.utcfromtimestamp(T[live]/1000).date()} .. {dt.datetime.utcfromtimestamp(T[-1]/1000).date()}")
print("=" * 100)
sb = R.stats(xb, T)
print(f"  {'BASE (what runs)':40} net {100*sb['ann']:+6.1f}%/yr Sharpe {sb['sharpe']:.2f} maxDD {100*maxdd(xb[live:]):4.1f}% "
      f"month {100*sb['month_mean']:+.2f}% worst month {100*sb['worst_month']:+.1f}%")
res = {'base': dict(ann=sb['ann'], sharpe=sb['sharpe'], maxdd=maxdd(xb[live:]), month=sb['month_mean'])}

# K1 -- momentum-crash guard
m = np.where(elig, np.nan_to_num(r), np.nan); mkt = np.nanmean(m, axis=1); mkt = np.nan_to_num(mkt)
n = len(T); state = np.zeros(n, bool)
v10 = np.full(n, np.nan)
for i in range(10, n):
    v10[i] = mkt[i - 9:i + 1].std()
for i in range(180, n):
    r30 = np.prod(1 + mkt[i - 29:i + 1]) - 1
    state[i] = (r30 < 0) and (v10[i] > np.nanmedian(v10[i - 179:i + 1]))
k1 = dict(base_parts); k1['C2'] = base_parts['C2'] * np.where(state, 0.5, 1.0)[:, None]
print(f"\nK1 momentum-crash guard: 'rebound risk' state on {100*state[live:].mean():.0f}% of days")
res['K1'] = judge('K1 crash guard (C2 x0.5 in rebound risk)', run(k1)[0])

# K2 -- superposition of horizons
k2 = dict(base_parts); k2['C2'] = c2((7, 14, 28)); k2['C3'] = c3((3, 7, 14))
print("\nK2 horizon ensemble")
res['K2'] = judge('K2 C2 over 7/14/28, C3 over 3/7/14', run(k2)[0])

# K3 -- Ichimoku trend (close-based highs/lows)
def rmax(x, w):
    out = np.full_like(x, np.nan)
    for i in range(w - 1, len(x)):
        out[i] = np.nanmax(x[i - w + 1:i + 1], axis=0)
    return out
def rmin(x, w):
    out = np.full_like(x, np.nan)
    for i in range(w - 1, len(x)):
        out[i] = np.nanmin(x[i - w + 1:i + 1], axis=0)
    return out
ten = (rmax(close, 9) + rmin(close, 9)) / 2; kij = (rmax(close, 26) + rmin(close, 26)) / 2
spa = (ten + kij) / 2; spb = (rmax(close, 52) + rmin(close, 52)) / 2
A = np.full_like(close, np.nan); Bc = np.full_like(close, np.nan); A[26:] = spa[:-26]; Bc[26:] = spb[:-26]
top, bot = np.fmax(A, Bc), np.fmin(A, Bc)
ich = np.where(close > top, 1.0, np.where(close < bot, -1.0, 0.0)); ich[np.isnan(top) | np.isnan(close)] = 0.0
k3 = dict(base_parts); k3['C1'] = R.banded(np.where(elig, ich * sc / N, 0.0))
agree = (np.sign(ich) == np.sign(sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56))))[elig].mean()
print(f"\nK3 Ichimoku trend (sign agrees with the base trend on {100*agree:.0f}% of eligible coin-days)")
res['K3'] = judge('K3 Ichimoku cloud as C1', run(k3)[0])

# K4 -- allostatic (EWMA 10-day half-life) vol
print("\nK4 allostatic volatility")
res['K4'] = judge('K4 EWMA vol, half-life 10 days', run(base_parts, ewma=True)[0])

# M1 -- the first three days in context
x = xb[live:]; TT = T[live:]
c3d = np.array([np.prod(1 + x[i - 2:i + 1]) - 1 for i in range(2, len(x))])
hit = np.nonzero(c3d <= -0.034)[0] + 2
eps = [i for k, i in enumerate(hit) if k == 0 or i - hit[k - 1] > 3]
nxt = np.array([np.prod(1 + x[i + 1:i + 31]) - 1 for i in eps if i + 31 <= len(x)])
print(f"\nM1 three-day loss of 3.4% or more: {100*len(hit)/len(c3d):.1f}% of 3-day windows, {len(eps)} separate episodes "
      f"in {len(x)/365:.1f} years (about {len(eps)/(len(x)/365):.1f} a year)")
if len(nxt):
    print(f"   the next 30 days after an episode: median {100*np.median(nxt):+.1f}%, mean {100*nxt.mean():+.1f}%, "
          f"positive {100*(nxt>0).mean():.0f}%, worst {100*nxt.min():+.1f}%, best {100*nxt.max():+.1f}%")
res['M1'] = dict(share=float(len(hit) / len(c3d)), episodes=len(eps), per_year=float(len(eps) / (len(x) / 365)),
                 next30=[float(v) for v in nxt])

# M2 -- the option-selling premium (Deribit DVOL vs realised)
print("\nM2 BTC implied (Deribit DVOL) minus the following 30 days' realised volatility")
try:
    j = urllib.request.urlopen(urllib.request.Request(
        "https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1D"
        f"&start_timestamp={int(dt.datetime(2021,3,1).timestamp()*1000)}&end_timestamp={int(T[-1])}",
        headers={'User-Agent': 'research'}), timeout=30).read()
    rows = json.loads(j)['result']['data']
    dv = {int(x0) // 86400000 * 86400000: float(c_) / 100 for x0, o, h, l, c_ in rows}
    b = syms.index('BTCUSDT'); lr = np.log(close[1:, b] / close[:-1, b]); tpos = {int(t): i for i, t in enumerate(T)}
    out = []
    for t, iv in sorted(dv.items()):
        i = tpos.get(t)
        if i is None or i + 31 > len(close):
            continue
        rv = lr[i:i + 30].std() * math.sqrt(365)
        out.append((t, iv, rv))
    iv = np.array([o[1] for o in out]); rv = np.array([o[2] for o in out]); vrp = iv - rv
    print(f"   {len(out)} days ({dt.datetime.utcfromtimestamp(out[0][0]/1000).date()} .. {dt.datetime.utcfromtimestamp(out[-1][0]/1000).date()}): "
          f"implied {100*iv.mean():.0f}% vs realised {100*rv.mean():.0f}% on average; premium mean {100*vrp.mean():+.1f} vol points, "
          f"median {100*np.median(vrp):+.1f}; realised ABOVE implied on {100*(vrp<0).mean():.0f}% of days; worst {100*vrp.min():+.0f} points")
    res['M2'] = dict(days=len(out), iv=float(iv.mean()), rv=float(rv.mean()), vrp_mean=float(vrp.mean()),
                     vrp_median=float(np.median(vrp)), share_neg=float((vrp < 0).mean()), worst=float(vrp.min()))
except Exception as e:
    print(f"   Deribit not reachable from here ({type(e).__name__}: {str(e)[:80]}) -- mechanics only (Rule 17)")
    res['M2'] = dict(unavailable=str(e)[:120])

if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1, default=float)
