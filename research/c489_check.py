import os
import sys, numpy as np, datetime as dt, pickle, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c489_research as M, omega_c488_research as R488
SP = sys.argv[1]
T, syms, O, Hh, L, C, QV, TB, U, F = M.load(SP + '/h1', SP + '/bnc')
r1, Fm = M.features(T, syms, O, Hh, L, C, QV, TB, U, F)
pickle.dump(dict(T=T, syms=syms, C=C, U=U, F=F, r1=r1, Fm=Fm), open(SP + '/c489_cache.pkl', 'wb'), protocol=4)
oos = T >= M.OOS_FROM
fwd = np.vstack([C[4:] / C[:-4] - 1, np.full((4, C.shape[1]), np.nan)])
for name, s in (('LOOK-AHEAD (cheat) signal', fwd), ('random signal', np.random.default_rng(0).normal(size=C.shape))):
    w = M.overlap(M.quintile_book(np.where(U, s, np.nan), U))
    hp, d = M.hourly_pnl(w, r1, F)
    print(f"{name:28} gross {100*d['gross'][oos].mean()*24*365:+9.1f}%/yr  cost {100*d['cost'][oos].mean()*24*365:6.1f}%/yr  turnover/day {d['turnover'][oos].mean()*24:.2f}")
for name, key in (('H2 +z_r24', 'z_r24'), ('H4 +mk1', 'mk1'), ('H3 +flow4', 'flow4')):
    w = M.overlap(M.quintile_book(np.where(U, Fm[key], np.nan), U))
    hp, d = M.hourly_pnl(w, r1, F)
    yrs = {}
    for t, g in zip(T[oos], d['gross'][oos]):
        y = dt.datetime.utcfromtimestamp(t / 1000).year; yrs[y] = yrs.get(y, 0) + g
    print(f"{name:28} gross by year: " + '  '.join(f"{y}:{100*v:+.0f}%" for y, v in sorted(yrs.items())) + f"   turnover/day {d['turnover'][oos].mean()*24:.2f}")
