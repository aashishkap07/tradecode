#!/usr/bin/env python3
import sys, os, numpy as np
# usage: python3 research/c491_breakdown.py DATA_DIR   (holds h1/, bnc/, m1/)
sys.path.insert(0, '/home/user/tradecode/research')
import omega_c491_research as R4, omega_c489_research as M
SP = sys.argv[1]
M.TOPN = 20
T, syms, O, Hh, L, C, QV, TB, U, F = M.load(SP + '/h1', SP + '/bnc')
sig = M.roll_std(C / M.lag(C, 1) - 1, 168)
w = (T >= R4.W0) & (T < R4.W1)
kinds = {'target': [], 'stop': [], 'time': []}
fill_to_exit = []
for j in [j for j in range(len(syms)) if U[w][:, j].any()]:
    z = np.load(f"{SP}/m1/{syms[j]}.npz"); mm = {k: z[k] for k in ('t', 'o', 'h', 'l', 'c')}
    tr, _, _ = R4.coin_trades(j, T, C, F, sig, U, mm, False)
    for h, (hx, rows, win) in tr.items():
        tot = sum(v for _, v in rows) / R4.SIZE
        k = 'target' if win else ('time' if hx == min(h + R4.HOLD, len(T) - 1) else 'stop')
        kinds[k].append(tot); fill_to_exit.append(hx - h)
n = sum(len(v) for v in kinds.values())
for k, v in kinds.items():
    v = np.array(v)
    print(f"  {k:6s} {len(v):6d} trades ({100*len(v)/n:4.1f}%)  mean {100*v.mean():+.3f}%  total {100*v.sum():+8.1f}%")
allv = np.concatenate([np.array(v) for v in kinds.values()])
print(f"  all    {n:6d} trades           mean {100*allv.mean():+.3f}%  (per trade, of its notional, costs included; before the cap of 10)")
print('  median hours held', np.median(fill_to_exit))
