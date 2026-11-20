#!/usr/bin/env python3
"""Round 23, after the verdict: DESCRIPTIVE checks (not tests -- nothing here adopts anything).

    C524_MARK=1 python3 research/r23_descriptive.py XV_CACHE HL_CACHE

1. Every stop S50 / S100 booked: the day, the coin, which exchange held the short leg, and both exchanges' day-high jump
   (a stop set off by one exchange's wick alone would show the other exchange far lower).
2. What a one-coin jump would cost: on each account-day of the base book (10 x 10%, K6), the jump on that account's
   largest short leg that would empty it; and how often an emergency stop -- set where the account would fall to 25%
   (or 40%) of its half -- would have fired.
3. How much the 24-month figures move with the coin list: today's list, and today's + each coin with $30k-$100k of
   Delta turnover.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r23_round23 as T
X, S, R = T.X, T.S, T.R


def main(cache, hcache):
    coins = set(json.load(open(os.path.join(HERE, 'r23_round23.json')))['coins'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    cv = S.delta_cv()
    hl = T.hl_matrices(allm[0], allm[1], prods, coins, hcache)
    D, names = allm[0], allm[1]
    OUT = {}
    print("ROUND 23, DESCRIPTIVE (after the verdict; nothing here is a test)\n")

    print("1. EVERY STOP BOOKED (day, coin, short leg on, its exchange's day-high jump %, the other exchange's %)")
    for stop in (0.5, 1.0):
        sw = T.Sw(allm, hl, stop=stop)
        ev, orig = [], sw.stopped

        def rec(i1, j, side, orig=orig, ev=ev, sw=sw):
            out = orig(i1, j, side)
            if out[0]:
                js, jt = (sw.jumpD, sw.jumpB) if side > 0 else (sw.jumpB, sw.jumpD)
                ev.append((dt.datetime.utcfromtimestamp(int(D[i1])).strftime('%Y-%m-%d'), names[j],
                           'Delta' if side > 0 else 'CoinDCX', int(round(100 * js[i1, j])),
                           None if np.isnan(jt[i1, j]) else int(round(100 * jt[i1, j]))))
            return out
        sw.stopped = rec
        T.legs3(*allm, cv=cv, cap=1000.0, allow=coins, costB=T.COSTB, capK=T.K6, sw=sw)
        wick = sum(1 for e in ev if e[4] is not None and e[4] < 100 * stop * 0.5)
        print(f"\n  S{int(stop * 100)}: {len(ev)} stops in 24 months; set off by one exchange alone (the other under half "
              f"the stop): {wick}")
        for e in ev:
            print(f"    {e[0]}  {e[1]:9} short on {e[2]:7}  +{e[3]}% / +{e[4]}%")
        OUT[f'S{int(stop * 100)}'] = ev

    print("\n2. WHAT A ONE-COIN JUMP WOULD COST (base book, cross margin)")
    sw = T.Sw(allm, hl)
    idx = {int(t): i for i, t in enumerate(D)}
    bk = T.sides3(allm, 1000.0, cv, allow=coins, capK=T.K6, record=set(int(t) for t in D[X.WIN:]))['books']
    need, acs, szs, fires = [], [], [], {0.25: [], 0.40: []}
    for d_, b in sorted(bk.items()):
        i1 = idx[d_]
        for key, side in (('sd', 1), ('sb', -1)):
            legs = [L for L in b['legs'] if L['side'] == side]
            if not legs:
                continue
            acct = b[key]
            big = max(legs, key=lambda L: L['size'])
            need.append(acct / big['size']); acs.append(acct); szs.append(big['size'])
            for lv in fires:
                for L in legs:
                    g = (acct - lv * 500.0) / L['size']
                    jj = (sw.jumpD if side > 0 else sw.jumpB)[i1, names.index(L['coin'])]
                    if not np.isnan(jj) and jj >= g:
                        fires[lv].append((dt.datetime.utcfromtimestamp(d_).strftime('%Y-%m-%d'), L['coin']))
    need = np.array(need)
    OUT['empty'] = dict(n=len(need), median=float(np.median(need)), p5=float(np.percentile(need, 5)), min=float(need.min()),
                        under530=float((need < 5.3).mean()), under346=float((need < 3.46).mean()),
                        leg_median=float(np.median(szs)), acct_median=float(np.median(acs)),
                        acct_p5=float(np.percentile(acs, 5)), fires25=fires[0.25], fires40=fires[0.40])
    e = OUT['empty']
    print(f"  {e['n']} account-days. The jump on the account's largest short leg that would empty it: median "
          f"+{100 * e['median']:.0f}%, 5th percentile +{100 * e['p5']:.0f}%, the worst day +{100 * e['min']:.0f}%.")
    print(f"  A +530% jump (BLESS) would empty it on {100 * e['under530']:.0f}% of account-days; a +346% jump (AKE on 2 Sep "
          f"2026, on its short leg's exchange; +384% on Delta) on {100 * e['under346']:.1f}%.")
    print(f"  The largest short leg: median ${e['leg_median']:.0f}; its account: median ${e['acct_median']:.0f} (5th "
          f"percentile ${e['acct_p5']:.0f}) -- the book grows with its profits.")
    for lv in (0.25, 0.40):
        print(f"  An emergency stop where the account would fall to {int(100 * lv)}% of its half: fired "
              f"{len(fires[lv])} times in 24 months {fires[lv][:10] if fires[lv] else ''}")

    print("\n3. HOW MUCH THE FIGURES MOVE WITH THE COIN LIST (today's list + one coin with $30k-$100k of Delta turnover)")
    dcx = set(json.load(open(os.path.join(HERE, 'c541_coindcx', 'coindcx_universe.json')))['both'])
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    turn = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in prods}
    base = X.matrices(prods, res)
    rD = np.full_like(base[4], np.nan); rB = rD.copy()
    rD[1:] = base[4][1:] / base[4][:-1] - 1; rB[1:] = base[5][1:] / base[5][:-1] - 1
    same = set()
    for j, c in enumerate(base[1]):
        m_ = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m_.sum() > 60 and np.corrcoef(rD[m_, j], rB[m_, j])[0, 1] >= 0.9:
            same.add(c)
    near = sorted(c for c in (same & dcx) - coins if turn.get(c, 0) >= 30000)
    r0 = T.run3(allm, cv, coins)
    rows = [(c, T.run3(allm, cv, coins | {c})) for c in near]
    af = [r['after1'] for _, r in rows]; lo = [r['low'] for _, r in rows]
    print(f"  today's {len(coins)} coins: after tax {100 * r0['after1']:+.2f}% a month, the poorer account's lowest "
          f"{100 * r0['low']:.1f}%")
    print(f"  + one of {len(near)} coins: after tax {100 * min(af):+.2f}% .. {100 * max(af):+.2f}%, lowest "
          f"{100 * min(lo):.1f}% .. {100 * max(lo):.1f}%")
    print("  Round 24's 64-coin list of 10 Oct (not saved): after tax +3.44%, lowest 66.3% -- several coins differ, not one.")
    OUT['list'] = dict(today=dict(after1=r0['after1'], low=r0['low']), near={c: dict(after1=r['after1'], low=r['low'])
                                                                          for c, r in rows})
    json.dump(OUT, open(os.path.join(HERE, 'r23_descriptive.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
