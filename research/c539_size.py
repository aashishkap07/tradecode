#!/usr/bin/env python3
"""Round 20 (C539): how big each bet in the rent-gap trade should be. Rules and bar fixed first in
research/c539_preregistration.md (amended before any variant ran).

    C524_MARK=1 python3 research/c539_size.py XV_CACHE PI42_DIR

The C533 study unchanged except X.SIZE: research/c532_india_only.py's xv_pi42 ("ALL harder": midnight
timing, Delta's mark, costs x5, Pi42's fee and GST) at $1,000 in whole contracts, and research/
c531_split_600.py's sides with the 65% even-out rule for each account's lowest point.
"""
import os, sys, io, json, contextlib
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C

SIZES = [('S8 ', 0.08), ('B0 ', 0.10), ('S12', 0.12), ('S15', 0.15)]


def main(cache, pdir):
    print("ROUND 20 (C539): THE BET SIZE PER LEG, $1,000, DELTA vs PI42 (pre-registered)\n")
    pi42 = set(json.load(open(os.path.join(pdir, 'pi42_universe.json')))['both'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
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
    print(f"coins: {len(allow)} (Pi42 lists it, Delta turnover >= $100k today, the same asset); "
          f"C533 had 52 on 4 Oct (Delta's turnover moves day to day)\n")
    print(f"{'size':5} {'net/yr':>7} {'t':>5} {'entries':>7} {'skipped':>7} {'avg/month':>9} {'worst month':>11} "
          f"{'months<0':>8} {'months>=2%':>10} | {'lowest acct':>11} {'months <50%':>11} {'transfers/yr':>12} | BAR")
    R, OUT = {}, {}
    old = X.COST_B, X.SIZE
    try:
        for name, sz in SIZES:
            X.SIZE = sz
            r = C.xv_pi42(*allm, cv=cv, cap=1000.0, allow=allow)
            ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
            X.COST_B = C.COST_PI42                               # as C532 called it: Pi42's fee on that leg
            sd = S.sides(allm, 1000.0, cv, trigger=0.65, allow=allow)
            X.COST_B = old[0]
            R[name] = (r, mv, sd)
    finally:
        X.COST_B, X.SIZE = old
    b, bm, bs = R['B0 ']
    for name, sz in SIZES:
        r, mv, sd = R[name]
        passed = (name != 'B0 ' and r['net'] >= b['net'] + 0.05 and mv.min() >= -0.04 and sd['low_side'] >= 0.40
                  and (mv < 0).sum() <= (bm < 0).sum() + 1)
        OUT[name.strip()] = dict(size=sz, net=r['net'], t=r['t'], entered=r['entered'], skipped=r['skipped'],
                                 avg_month=float(mv.mean()), worst_month=float(mv.min()), months_neg=int((mv < 0).sum()),
                                 months_ge2=float((mv >= 0.02).mean()), low_side=sd['low_side'],
                                 months_lt50=sd['months_lt50'], transfers_yr=sd['transfers_yr'], passed=bool(passed))
        print(f"{name:5} {100 * r['net']:+6.1f}% {r['t']:5.2f} {r['entered']:7d} {r['skipped']:7d} {100 * mv.mean():+8.2f}% "
              f"{100 * mv.min():+10.2f}% {int((mv < 0).sum()):5d}/{len(mv)} {100 * (mv >= 0.02).mean():9.0f}% | "
              f"{100 * sd['low_side']:10.1f}% {100 * sd['months_lt50']:10.0f}% {sd['transfers_yr']:12.1f} | "
              f"{'PASS' if passed else ('-' if name == 'B0 ' else 'fail')}")
    winners = [n for n in OUT if OUT[n]['passed']]
    print(f"\nPASSED: {', '.join(winners) if winners else 'none -- 10% a leg stays'}")
    print("(the account columns are relative to its starting $500; 'months <50%' counts months with a daily close where "
          "the poorer account was under half the two accounts' mean)")
    json.dump(OUT, open(os.path.join(HERE, 'c539_size.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
