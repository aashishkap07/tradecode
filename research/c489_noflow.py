"""C489 shadow warm-up model: M1 without the two taker-flow features (flow1, flow4).
Bitget serves only 30 h of taker flow, so the live shadow uses this model until a
week of flow is collected. Walk-forward OOS record + final fit (last 180 days).
Usage: python3 research/c489_noflow.py CACHE.pkl   (the pickle written by c489_check.py)"""
import os, sys, json, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c489_research as M, omega_c488_research as R488
d = pickle.load(open(sys.argv[1], 'rb'))
T, C, U, F, r1, Fm = d['T'], d['C'], d['U'], d['F'], d['r1'], d['Fm']
M.FEATS = [f for f in M.FEATS if f not in ('flow1', 'flow4')]
Z = M.xs_standardise(Fm, U)
P, gate, fits = M.model_signal(T, C, U, Z)
oos = T >= M.OOS_FROM
for name, q in (('M1nf (no flow)', M.quintile_book(P, U)), ('M1nfg (no flow, cost-gated)', None)):
    if q is None:
        q = M.quintile_book(P, U); q[~gate] = 0.0
    hp, dd = M.hourly_pnl(M.overlap(q), r1, F)
    du, dr = M.to_daily(T[oos], hp[oos])
    R488.show(name, R488.stats(dr, du), f"| gross {100*dd['gross'][oos].mean()*24*365:+.0f}%/yr cost {100*dd['cost'][oos].mean()*24*365:.0f}%/yr")
# final fit on the last 180 days, exactly as the full model was exported
k = C.shape[1]
fwd = np.vstack([C[4:] / C[:-4] - 1, np.full((4, k), np.nan)])
rel = fwd - np.nanmedian(np.where(U, fwd, np.nan), axis=1, keepdims=True)
t = T[-1] + M.H
a = np.searchsorted(T, t - 180 * M.DAY); b = np.searchsorted(T, t - 4 * M.H)
ri, rj = np.nonzero(U[a:b]); ri = ri + a
X = np.column_stack([Z[f][ri, rj] for f in M.FEATS]); y = rel[ri, rj]
ok = ~np.isnan(X).any(1) & ~np.isnan(y)
w = M.logit_fit(np.nan_to_num(X[ok]), (y[ok] > 0).astype(float), 0.1)
Xt = np.stack([Z[f][a:b] for f in M.FEATS], -1)
ptr = M.logit_predict(w, np.nan_to_num(Xt).reshape(-1, len(M.FEATS))).reshape(b - a, k)
ptr[np.isnan(Xt).any(-1) | ~U[a:b]] = np.nan
sp_p, sp_r = [], []
for i in range(b - a):
    m = ~np.isnan(ptr[i]) & ~np.isnan(fwd[a + i])
    if m.sum() < 10: continue
    v = ptr[i][m]; lo, hi = np.quantile(v, [0.2, 0.8]); top = v >= hi; bot = v <= lo
    sp_p.append(v[top].mean() - v[bot].mean()); sp_r.append(fwd[a + i][m][top].mean() - fwd[a + i][m][bot].mean())
coef = np.linalg.lstsq(np.vstack([np.ones(len(sp_p)), sp_p]).T, np.array(sp_r), rcond=None)[0]
out = dict(feats=M.FEATS, w=[float(x) for x in w], gate=[float(c) for c in coef], rows=int(ok.sum()), trained_to='2026-08-31', window_days=180, C=0.1)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c489_model_noflow.json'), 'w'), indent=1)
print('saved research/c489_model_noflow.json', len(M.FEATS), 'features')
