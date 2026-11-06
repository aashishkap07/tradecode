import os
import sys, numpy as np, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c488_research as R
SP = sys.argv[1]
T, syms, close, qv, fund = R.load_crypto(SP)
r, W, elig = R.crypto_sleeves(T, close, qv, fund)
Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1)
live = Wc[400:]
npos = (np.abs(live) > 1e-9).sum(1)
print(f"positions per day: median {np.median(npos):.0f}, max {npos.max()}")
for eq in (250, 1000, 5000):
    notl = np.abs(live[np.abs(live) > 1e-9]) * eq
    print(f"equity ${eq}: median position ${np.median(notl):.1f}, share of positions under $6: {100*(notl<6).mean():.0f}%")
print("\nWHAT DROPPING POSITIONS BELOW A MINIMUM DOES (equity $250; the weights are otherwise identical)")
for eq, mn in ((250, 0), (250, 6), (250, 10), (500, 6), (1000, 6)):
    Wm = np.where(np.abs(Wc) * eq >= mn, Wc, 0.0)
    R.show(f'COMBO-C equity ${eq}, min ${mn}', R.stats(R.pnl(Wm, r, fund, 1)[0], T))
