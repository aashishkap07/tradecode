import os
"""EXPLORATION: intraday timing of the C488 book's daily trades (2021-07..2023-12 only)."""
import sys, numpy as np, datetime as dt, pickle, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c489_research as M, omega_c488_research as R488
SP = sys.argv[1]; WINDOW = sys.argv[2] if len(sys.argv) > 2 else 'explore'
d = pickle.load(open(SP + '/c489_cache.pkl', 'rb'))
T, syms, C, U, Fm = d['T'], d['syms'], d['C'], d['U'], d['Fm']
Td, dsyms, dclose, dqv, dfund = R488.load_crypto(SP + '/bnc')
R488.TOPN = 20
r, Wd, _ = R488.crypto_sleeves(Td, dclose, dqv, dfund)
Wc = R488.combine({k: Wd[k] for k in ('C1', 'C2', 'C3')}, r, dfund, 1)
DW = np.diff(np.vstack([np.zeros(Wc.shape[1]), Wc]), axis=0)          # the trade at the close of day d
E0 = M.OOS_FROM; E1 = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
lo, hi = (E0, E1) if WINDOW == 'explore' else (E1, 10**14)
hcol = {s: j for j, s in enumerate(syms)}
hidx = {t: i for i, t in enumerate(T.tolist())}
def rank_at(x, i):
    v = np.where(U[i], x[i], np.nan); m = ~np.isnan(v)
    rk = np.full(len(v), np.nan)
    if m.sum() >= 10:
        o = np.argsort(np.argsort(v[m])); rk[m] = o / (m.sum() - 1)
    return rk
preds = {'H2 z_r24 rank': Fm['z_r24'], 'H4 mk1 rank': Fm['mk1'], 'H3 flow4 rank': Fm['flow4']}
rng = np.random.default_rng(0)
print(f"C488 book (top 20) trades, window {WINDOW}: {dt.datetime.utcfromtimestamp(lo/1000):%Y-%m} .. ")
for pname, P in preds.items():
    for k in (2, 4, 8):
        gain = []; days = []; defer_n = 0; n = 0; rgain = []
        for di, t in enumerate(Td):
            if not (lo <= t < hi): continue
            h0 = hidx.get(int(t) + 23 * 3600000)             # the daily close = close of the 23:00 bar
            if h0 is None or h0 + k >= len(T): continue
            rk = rank_at(P, h0)
            g = 0.0; gr = 0.0
            for j in np.nonzero(np.abs(DW[di]) > 1e-9)[0]:
                c = hcol.get(dsyms[j])
                if c is None or np.isnan(C[h0, c]) or np.isnan(C[h0 + k, c]): continue
                dw = DW[di, j]; n += 1
                move = (C[h0 + k, c] / C[h0, c] - 1)
                p = rk[c]
                defer = (not np.isnan(p)) and ((dw > 0 and p < 0.5) or (dw < 0 and p > 0.5))
                if defer:
                    defer_n += 1
                    g += -dw * move                              # buy later: gain if the price fell
                if rng.random() < 0.5:                           # the same count of RANDOM deferrals
                    gr += -dw * move
            gain.append(g); rgain.append(gr); days.append(t)
        gain, rgain = np.array(gain), np.array(rgain)
        s = R488.stats(gain, np.array(days))
        print(f"  {pname:16} defer {k}h when against: {100*gain.mean()*365:+6.2f}%/yr of equity  t {s['t']:+.2f}  q+ {s['npos']}/4  "
              f"({100*defer_n/max(n,1):.0f}% of trades deferred)   random deferral {100*rgain.mean()*365:+6.2f}%/yr")
