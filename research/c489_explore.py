import os
"""C489b EXPLORATION: low-turnover designs, measured on 2021-07..2023-12 ONLY."""
import sys, numpy as np, datetime as dt, pickle, math, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c489_research as M, omega_c488_research as R488
SP = sys.argv[1]
d = pickle.load(open(SP + '/c489_cache.pkl', 'rb'))
T, C, U, F, r1, Fm = d['T'], d['C'], d['U'], d['F'], d['r1'], d['Fm']
E0 = M.OOS_FROM; E1 = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
ex = (T >= E0) & (T < E1)
def xrank(s):
    x = np.where(U, s, np.nan)
    r = np.argsort(np.argsort(np.where(np.isnan(x), np.inf, x), axis=1), axis=1).astype(float)
    n = (~np.isnan(x)).sum(1, keepdims=True)
    return np.where(np.isnan(x), np.nan, r / np.maximum(n - 1, 1))
def hyst(rank, enter=0.9, exit_=0.5, min_hold=4, size=0.125):
    n, k = rank.shape
    w = np.zeros((n, k)); st = np.zeros(k); age = np.zeros(k)
    for i in range(n):
        p = rank[i]
        inu = ~np.isnan(p)
        age += (st != 0)
        # exits
        out = (~inu & (st != 0)) | ((st > 0) & inu & (p < exit_) & (age >= min_hold)) | ((st < 0) & inu & (p > 1 - exit_) & (age >= min_hold))
        st[out] = 0; age[out] = 0
        # entries
        el = inu & (st == 0) & (p >= enter); es = inu & (st == 0) & (p <= 1 - enter)
        st[el] = 1; st[es] = -1; age[el | es] = 0
        w[i] = st * size
    return w
def ev(w, label, rows=ex):
    hp, dd = M.hourly_pnl(w, r1, F)
    du, dr = M.to_daily(T[rows], hp[rows])
    s = R488.stats(dr, du)
    print(f"  {label:48} net {100*s['ann']:+6.1f}%/yr  Sharpe {s['sharpe']:+.2f}  t {s['t']:+.2f}  q+ {s['npos']}/4  "
          f"gross {100*dd['gross'][rows].mean()*24*365:+5.1f}%  cost {100*dd['cost'][rows].mean()*24*365:4.1f}%  turn/day {dd['turnover'][rows].mean()*24:.2f}", flush=True)
    return s
z = lambda a: (a - np.nanmean(a, axis=1, keepdims=True)) / np.nanstd(a, axis=1, keepdims=True)
combo = np.nanmean(np.stack([z(np.where(U, Fm['z_r24'], np.nan)), z(np.where(U, Fm['mk1'], np.nan)), z(np.where(U, Fm['flow4'], np.nan))]), axis=0)
SIG = {'H2 z_r24': Fm['z_r24'], 'H4 mk1': Fm['mk1'], 'CMB z_r24+mk1+flow4': combo}
print("EXPLORATION WINDOW 2021-07 .. 2023-12 (the holdout 2024-01 .. 2026-08 is not touched here)")
for name, s in SIG.items():
    rk = xrank(s)
    for enter, exit_, mh in itertools.product((0.9, 0.95), (0.5, 0.7), (4, 24)):
        ev(hyst(rk, enter, exit_, mh), f"{name} enter {enter} exit {exit_} minhold {mh}h")
