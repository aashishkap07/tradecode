#!/usr/bin/env python3
# usage: python3 research/c490_diagnostics.py DATA_DIR carry|lp   (DATA_DIR holds bnc/, h1/, spot/, spot_map.json)
"""diagnostics, NOT admission tests: (1) carry by year + threshold sensitivity + realistic (capital-limited) add to the book;
(2) LP under the most OPTIMISTIC intra-hour ordering (no stop in the fill hour, target before stop)"""
import sys, os, json, math, datetime as dt, numpy as np, time
sys.path.insert(0, '/home/user/tradecode/research')
import omega_c490_research as X, omega_c488_research as R488, omega_c489_research as M
SP = sys.argv[1]; what = sys.argv[2]
if what == 'carry':
    Td, dsyms, dclose, dqv, dfund = R488.load_crypto(SP + '/bnc')
    smap = json.load(open(SP + '/spot_map.json'))
    o = Td >= X.OOS
    yrs = np.array([dt.datetime.utcfromtimestamp(t / 1000).year for t in Td])
    pnl, npos = X.carry(Td, dsyms, dclose, dqv, dfund, SP + '/spot', smap)
    for y in range(2021, 2027):
        m = o & (yrs == y)
        print(f"  carry {y}: {100*pnl[m].sum():+6.2f}%  avg pos {npos[m].mean():.1f}  days {m.sum()}")
    for en, ex in ((0.05, 0.02), (0.10, 0.05), (0.15, 0.08), (0.20, 0.10)):
        p2, n2 = X.carry(Td, dsyms, dclose, dqv, dfund, SP + '/spot', smap, enter=en, exit_=ex)
        s = R488.stats(p2[o], Td[o]); R488.show(f'  carry enter {en:.0%} exit {ex:.0%}', s, f"| avg {n2[o].mean():.1f} pos")
    R488.TOPN = 20
    rr, Wd, _ = R488.crypto_sleeves(Td, dclose, dqv, dfund)
    Wc = R488.combine({k: Wd[k] for k in ('C1', 'C2', 'C3')}, rr, dfund, 1)
    book, *_ = R488.pnl(Wc, rr, dfund, 1)
    R488.show('  book alone (dial 1)', R488.stats(book[o], Td[o]))
    R488.show('  book + carry as tested (additive)', R488.stats((book + pnl)[o], Td[o]))
    for y in range(2021, 2027):
        m = o & (yrs == y)
        print(f"  {y}: book {100*book[m].sum():+6.1f}%  book+carry {100*(book+pnl)[m].sum():+6.1f}%")
else:
    T, syms, O, Hh, L, C, QV, TB, U, F = M.load(SP + '/h1', SP + '/bnc')
    r1 = np.full_like(C, np.nan); r1[1:] = C[1:] / C[:-1] - 1
    sig = M.roll_std(r1, 168)
    src = open('/home/user/tradecode/research/omega_c490_research.py').read()
    a = src.index('def lp('); b = src.index('# ─── R3b')
    code = src[a:b]
    code = code.replace("            if (sd > 0 and lo < p['stop']) or (sd < 0 and hi > p['stop']):\n                ex, cost = p['stop'], TAKER\n            elif (sd > 0 and hi > p['target']) or (sd < 0 and lo < p['target']):\n                ex, cost = p['target'], MAKER; wins += 1",
                        "            if (sd > 0 and hi > p['target']) or (sd < 0 and lo < p['target']):\n                ex, cost = p['target'], MAKER; wins += 1\n            elif (sd > 0 and lo < p['stop']) or (sd < 0 and hi > p['stop']):\n                ex, cost = p['stop'], TAKER")
    code = code.replace("if (sd > 0 and L[h, j] < stop) or (sd < 0 and Hh[h, j] > stop):", "if False:")
    assert code.count('if False:') == 1 and code.index("ex, cost = p['target']") < code.index("ex, cost = p['stop']")
    ns = dict(X.__dict__); exec(code.replace('def lp(', 'def lp_opt('), ns)
    oos = T >= X.OOS
    pnl, fills, wins = ns['lp_opt'](T, O, Hh, L, C, U, F, sig, np.ones_like(U, bool))
    X.daily_stats(T[oos], pnl[oos], 'LP OPTIMISTIC ordering (diagnostic)', f"| {fills} fills, {100*wins/max(fills,1):.0f}% target")
