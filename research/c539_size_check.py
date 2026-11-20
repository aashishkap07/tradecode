#!/usr/bin/env python3
"""Round 20 (C539) engine check and sensitivity: why the 10% baseline did not reproduce C533 (4 Oct), and each size
on coin lists that differ by the few coins that move the result most. Not the pre-registered bar; it decides
whether the bar's result can be read.

    C524_MARK=1 python3 research/c539_size_check.py XV_CACHE PI42_DIR
"""
import os, sys, io, json, contextlib
import numpy as np, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c524_xvenue as X, c531_split_600 as S, c532_india_only as C
cache, pdir = sys.argv[1], sys.argv[2]
pi42 = set(json.load(open(os.path.join(pdir, 'pi42_universe.json')))['both'])
with contextlib.redirect_stdout(io.StringIO()):
    prods, res = X.load(cache)
allm = X.matrices(prods, res, shift00=True, mark=True)
tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'), timeout=30).json()['result']}
tov = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in prods}
liq = {c for c in prods if tov[c] >= 100000}
base = X.matrices(prods, res)
rD = np.full_like(base[4], np.nan); rB = rD.copy()
rD[1:] = base[4][1:] / base[4][:-1] - 1; rB[1:] = base[5][1:] / base[5][:-1] - 1
same = set()
for j, c in enumerate(base[1]):
    m_ = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
    if m_.sum() > 60 and np.corrcoef(rD[m_, j], rB[m_, j])[0, 1] >= 0.9:
        same.add(c)
allow = liq & same & pi42
cv = S.delta_cv()
def run(al):
    r = C.xv_pi42(*allm, cv=cv, cap=1000.0, allow=al)
    mv = np.array([r['months'][k] for k in sorted(r['months'])])
    old = X.COST_B; X.COST_B = C.COST_PI42
    sd = S.sides(allm, 1000.0, cv, trigger=0.65, allow=al); X.COST_B = old
    return r['net'], mv.min(), sd['low_side'], r['entered'], sorted(r['months'], key=lambda k: r['months'][k])[0]
out = sorted(same & pi42 - liq)
print('in the same-asset Pi42 set but under $100k today:', len(out))
res_ = []
for c in out:
    n, w, lo, en, wm = run(allow | {c})
    res_.append((w, c, n, lo, en, wm, tov[c]))
for w, c, n, lo, en, wm, t in sorted(res_)[:12]:
    print(f"  +{c:10} turnover today ${t/1e3:6.0f}k  net {100*n:+.1f}%  worst month {100*w:+.2f}% ({wm})  lowest acct {100*lo:.1f}%  entries {en}")
print('--- sensitivity (not the bar): each size on coin lists that differ by the coins that move the result most')
lists = [('today (53)', allow), ('+JTO', allow | {'JTO'}), ('+PENDLE', allow | {'PENDLE'}), ('+JTO +PENDLE', allow | {'JTO', 'PENDLE'}),
         ('+JTO +PENDLE +TIA', allow | {'JTO', 'PENDLE', 'TIA'})]
for lab, al in lists:
    row = []
    for sz in (0.10, 0.12, 0.15):
        X.SIZE = sz
        n, w, lo, en, wm = run(al)
        row.append(f"{int(sz*100)}%: net {100*n:+.1f}% worst {100*w:+.2f}% low {100*lo:.0f}%")
    X.SIZE = 0.10
    print(f"  {lab:20} " + ' | '.join(row))
