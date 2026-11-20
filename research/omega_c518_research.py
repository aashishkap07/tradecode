#!/usr/bin/env python3
"""C518 round 13 (research/c518_preregistration.md): selling crypto volatility --
a ladder of short 30-day variance swaps on BTC and ETH (strike from Deribit's
DVOL, less 3 vol points) -- as a second stream beside the N2+N3 book.

    python3 research/omega_c518_research.py BNC_DIR DVOL_DIR [--out results.json]

DVOL_DIR holds dvol_BTC.json / dvol_ETH.json: Deribit get_volatility_index_data
daily rows [t_ms, open, high, low, close], 2021-03-24 -> 2026-09-30.
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
DAY = 86400000
rng = np.random.default_rng(518)

T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
N = 20; n = len(T)
sc = np.nan_to_num(R.vol_scale(sd))
f7 = np.full_like(fund, np.nan)
for i in range(7, n):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan
mkt = np.nan_to_num(np.nanmean(np.where(elig, r, np.nan), axis=1))
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
s3 = R.xs_rank(R.lagret(close, 14) - beta * m14[:, None], elig)
s23 = np.where((s3 < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s3)
tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
parts = {'C1': R.banded(np.where(elig, tr * sc / N, 0.0)),
         'C2': R.weekly(s23 * sc / (2 * N * 0.2), T),
         'C3': R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)}
W = R.combine(parts, r, fund, 1, target_vol=20 * 4 / 3 / 100)
W = np.where(np.abs(W) * EQ >= FLOOR, W, 0.0)
xb, ib = R.pnl(W, r, fund, 1)
sav = np.clip(1.0 - ib['gross_exp'] / 5.0 - 0.20 - 0.05, 0.0, 1.0) * 0.05 / 365.0
book = xb + sav                                  # the book with idle cash in Savings (the C504/C510 series)


def dvol(cur):
    rows = json.load(open(os.path.join(sys.argv[2], f'dvol_{cur}.json')))
    d = {int(x[0]) // DAY * DAY: float(x[4]) for x in rows}
    return np.array([d.get(int(t), np.nan) for t in T])


def ladder(sym, cur, c=3.0, tenor=30):
    """the unit stream: 1/tenor of a new short variance swap each day, realized accrual"""
    j = syms.index(sym)
    lr = np.log(close[:, j])
    ret = np.full(n, np.nan); ret[1:] = lr[1:] - lr[:-1]
    iv = dvol(cur)
    K = ((iv - c) / 100.0) ** 2
    Nv = 1.0 / (2.0 * np.sqrt(K))
    u = np.zeros(n); live = np.zeros(n, bool)
    for t in range(n):
        if np.isnan(ret[t]):
            continue
        acc, cnt = 0.0, 0
        for e in range(max(0, t - tenor), t):     # tranches entered at the close of days t-30 .. t-1
            if np.isnan(K[e]):
                continue
            acc += Nv[e] * (K[e] / 365.0 - ret[t] ** 2)
            cnt += 1
        if cnt == tenor:
            u[t] = acc / tenor
            live[t] = True
    return u, live


def scaled(u, live, target=0.20, win=60, cap=3.0):
    s = np.zeros(n)
    for t in range(n):
        if not live[t]:
            continue
        h = u[max(0, t - win):t][live[max(0, t - win):t]]
        if len(h) < win // 2:
            continue
        v = h.std() * math.sqrt(365)
        s[t] = u[t] * (min(cap, target / v) if v > 0 else 0.0)
    return s


def trail_sd(x, t, win=60):
    h = x[max(0, t - win):t]
    return h.std() if len(h) >= win // 2 else np.nan


def blend(a, b):
    """equal risk from trailing 60-day vols (lag 1), scaled back to a's own trailing vol"""
    z = np.zeros(n); out = np.zeros(n)
    for t in range(n):
        sa, sb = trail_sd(a, t), trail_sd(b, t)
        if not (sa > 0 and sb > 0):
            z[t] = a[t]
            continue
        z[t] = 0.5 * a[t] / sa + 0.5 * b[t] / sb
    for t in range(n):
        sa, sz = trail_sd(a, t), trail_sd(z, t)
        out[t] = z[t] * (sa / sz) if (sa > 0 and sz > 0) else a[t]
    return out


def maxdd(y):
    e = np.cumprod(1 + y); return float((1 - e / np.maximum.accumulate(e)).max())


def months(y, TT):
    m = {}
    for t, v in zip(TT, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


def boot_years(y, horizon_days=365, reps=10000, block=30):
    nb = int(math.ceil(horizon_days / block)); out = np.empty(reps)
    starts = rng.integers(0, len(y) - block, size=(reps, nb))
    for q in range(reps):
        out[q] = np.prod(1 + np.concatenate([y[a:a + block] for a in starts[q]])[:horizon_days]) - 1
    return out


def p_target(y):
    need = 1.02 ** 12 - 1
    return float((boot_years(y) >= need).mean()), float((boot_years(y - y.mean() / 3.0) >= need).mean())


print("=" * 118)
print("C518 ROUND 13 | selling 30-day volatility (short variance-swap ladder, strike DVOL - 3 pts) beside the N2+N3 book")
print("=" * 118)
res = {}
streams = {}
for key, sym, cur in (('V1', 'BTCUSDT', 'BTC'), ('V2', 'ETHUSDT', 'ETH')):
    u, lv = ladder(sym, cur)
    streams[key] = (scaled(u, lv), lv)
lv3 = streams['V1'][1] & streams['V2'][1]
u3 = np.where(lv3, 0.5 * streams['V1'][0] + 0.5 * streams['V2'][0], 0.0)
streams['V3'] = (scaled(u3, lv3), lv3)
start = int(np.nonzero(lv3)[0][0]) + 60                       # both ladders full and 60 days of scaling history
TT = T[start:]
print(f"window {dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()} "
      f"({len(TT)} days)")
bk = book[start:]
mb = months(bk, TT)
pb = p_target(bk)
print(f"\n  BOOK (N2+N3, dial 20%, + Savings), same window: {100*(np.prod(1+bk)**(365/len(bk)/12)-1):+.2f}%/mo "
      f"Sharpe {bk.mean()/bk.std()*math.sqrt(365):.2f} maxDD {100*maxdd(bk):.1f}% worst month {100*mb.min():+.1f}% "
      f"| year avg>=2%/mo: boot {100*pb[0]:.0f}% haircut {100*pb[1]:.0f}%")
res['book'] = dict(month=float(np.prod(1 + bk) ** (365 / len(bk) / 12) - 1), sharpe=float(bk.mean() / bk.std() * math.sqrt(365)),
                   maxdd=maxdd(bk), worst_month=float(mb.min()), p_boot=pb[0], p_haircut=pb[1])
worst_book_months = mb <= np.quantile(mb, 0.10)
for key, words in (('V1', 'V1 BTC short volatility'), ('V2', 'V2 ETH short volatility'), ('V3', 'V3 BTC+ETH, equal risk')):
    s = streams[key][0][start:]
    ms = months(s, TT)
    t = R.nw_t(s)
    q = sum(v.mean() > 0 for v in np.array_split(s, 4))
    hold = s[TT >= HOLD].mean() * 365
    w30 = min(np.prod(1 + s[i:i + 30]) - 1 for i in range(len(s) - 30))
    corr_d = float(np.corrcoef(s, bk)[0, 1]); corr_m = float(np.corrcoef(ms, mb)[0, 1])
    in_bad = float(ms[worst_book_months].mean())
    bl = blend(book, streams[key][0])[start:]
    mbl = months(bl, TT)
    pbl = p_target(bl)
    adm = bool(t >= 2.0 and q >= 3 and hold > 0 and pbl[1] - pb[1] >= 0.05 and maxdd(bl) <= maxdd(bk) + 0.02)
    print(f"\n{words}")
    print(f"  stream  {100*(np.prod(1+s)**(365/len(s)/12)-1):+.2f}%/mo  Sharpe {s.mean()/s.std()*math.sqrt(365):.2f}  "
          f"vol {100*s.std()*math.sqrt(365):.0f}%  maxDD {100*maxdd(s):.1f}%  worst month {100*ms.min():+.1f}%  "
          f"worst 30 days {100*w30:+.1f}%  months>0 {100*(ms>0).mean():.0f}%")
    print(f"          NW t {t:+.2f}  quarters+ {q}/4  holdout 2025-26 {100*hold:+.1f}%/yr  "
          f"corr with the book: daily {corr_d:+.2f}, monthly {corr_m:+.2f}; in the book's worst 10% of months "
          f"the stream averaged {100*in_bad:+.1f}%")
    print(f"  blend   {100*(np.prod(1+bl)**(365/len(bl)/12)-1):+.2f}%/mo  Sharpe {bl.mean()/bl.std()*math.sqrt(365):.2f}  "
          f"maxDD {100*maxdd(bl):.1f}% (book {100*maxdd(bk):.1f}%)  worst month {100*mbl.min():+.1f}%  "
          f"| year avg>=2%/mo: boot {100*pbl[0]:.0f}% haircut {100*pbl[1]:.0f}% (book {100*pb[1]:.0f}%)"
          f"  -> {'ADMIT (paper ledger first)' if adm else 'not admitted'}")
    res[key] = dict(month=float(np.prod(1 + s) ** (365 / len(s) / 12) - 1), sharpe=float(s.mean() / s.std() * math.sqrt(365)),
                    maxdd=maxdd(s), worst_month=float(ms.min()), worst_30d=float(w30), t=float(t), quarters=int(q),
                    holdout_ann=float(hold), corr_daily=corr_d, corr_monthly=corr_m, in_book_worst_months=in_bad,
                    blend=dict(month=float(np.prod(1 + bl) ** (365 / len(bl) / 12) - 1),
                               sharpe=float(bl.mean() / bl.std() * math.sqrt(365)), maxdd=maxdd(bl),
                               worst_month=float(mbl.min()), p_boot=pbl[0], p_haircut=pbl[1]), admit=adm)

print("\nDESCRIPTIVE: the cost assumption (V3, BTC+ETH)")
for c in (1.5, 5.0):
    a1, l1 = ladder('BTCUSDT', 'BTC', c); a2, l2 = ladder('ETHUSDT', 'ETH', c)
    s1, s2 = scaled(a1, l1), scaled(a2, l2)
    lvx = l1 & l2
    s = scaled(np.where(lvx, 0.5 * s1 + 0.5 * s2, 0.0), lvx)[start:]
    print(f"  cost {c:.1f} vol pts: {100*(np.prod(1+s)**(365/len(s)/12)-1):+.2f}%/mo  Sharpe {s.mean()/s.std()*math.sqrt(365):.2f}  "
          f"maxDD {100*maxdd(s):.1f}%  NW t {R.nw_t(s):+.2f}")
    res[f'V3_cost_{c}'] = dict(month=float(np.prod(1 + s) ** (365 / len(s) / 12) - 1), sharpe=float(s.mean() / s.std() * math.sqrt(365)))
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
