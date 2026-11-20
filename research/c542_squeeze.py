#!/usr/bin/env python3
"""C542: how often a coin in CoinDCX's list moved 30% / 50% / 100% / 200% / 400% in one day (2024-10 .. 2026-09).

    C524_MARK=1 python3 research/c542_squeeze.py XV_CACHE
"""
import sys, io, json, contextlib, datetime as dt
import numpy as np, requests
sys.path.insert(0, '/home/user/tradecode/research')
import c524_xvenue as X, c531_split_600 as S
with contextlib.redirect_stdout(io.StringIO()):
    prods, res = X.load(sys.argv[1])
D, names, fD, fB, pD, pB = X.matrices(prods, res, shift00=True, mark=True)
tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'), timeout=30).json()['result']}
turn = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in prods}
dcx = set(json.load(open('/home/user/tradecode/research/c541_coindcx/coindcx_universe.json'))['both'])
allow = {c for c in prods if turn.get(c, 0) >= 100000} & dcx
idx = [j for j, n in enumerate(names) if n in allow]
r = np.full_like(pD, np.nan); r[1:] = pD[1:] / pD[:-1] - 1
R = r[:, idx]; live = ~np.isnan(R)
coin_days = live.sum(); yrs = coin_days / len(idx) / 365
print(f"{len(idx)} coins, {coin_days} coin-days (~{yrs:.1f} years each on average)")
for th in (0.3, 0.5, 1.0, 2.0, 4.0):
    up = (R >= th).sum(); dn = (R <= -th / (1 + th)).sum()
    ev = [(dt.datetime.utcfromtimestamp(int(D[i])).date(), names[idx[j]], round(100 * R[i, j])) for i, j in zip(*np.where(np.abs(R) >= min(th, 0.99) if th < 1 else R >= th))]
    print(f"daily move >= +{100*th:.0f}%: {up} times ({up / coin_days * 365 * 10:.2f} per 10 coins held a year); down by the same (to 1/(1+x)): {dn}")
    if th >= 1.0:
        print('    ', ev[:12])
