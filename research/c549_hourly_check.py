#!/usr/bin/env python3
"""C549 (1 Nov 2026): how much Delta's temporary HOURLY settlements move the research behind the plan.

    C524_MARK=1 python3 research/c549_hourly_check.py XV_CACHE

Found in the monthly review: Delta switches a coin from 4-hourly to hourly settlements during a squeeze and back later.
The research engine counted only the usual timetable (1 of every 4 hourly payments). `c524_xvenue.C549_HOURLY` now
counts them; this script runs the plan's engine (Round 23's run3: 10 pairs x 10%, the K6 cap, CoinDCX's costs, after
tax) both ways on the same 24 months and the same coin list (research/r23_round23.json), and counts the hourly runs.
Descriptive: nothing is adopted or rejected here.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import r23_round23 as T


def hourly_days(recs, iv_now):
    """the UTC days with at least one settlement off the coin's usual timetable (2024-10-01 .. 2026-09-30)"""
    v = dict(recs)
    g = max(4, iv_now // 3600)
    out = set()
    for t in sorted(v):
        if X.START <= t < X.END and (t // 3600) % g and (t - 3600) in v and v[t] != v[t - 3600]:
            out.add(t // X.DAY * X.DAY)
    return out


def main(cache):
    coins = set(json.load(open(os.path.join(HERE, 'r23_round23.json')))['coins'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    cv = T.S.delta_cv()
    OUT = dict(read=f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC", coins=len(coins))
    print("C549: DELTA'S TEMPORARY HOURLY SETTLEMENTS IN THE 24 MONTHS (2024-10-01 .. 2026-09-30)\n")
    hd = {c: hourly_days(df, prods[c]['iv']) for c, df, *_ in res if df}
    alln = {c: len(d) for c, d in hd.items() if d}
    plan = {c: n for c, n in alln.items() if c in coins}
    print(f"  coins with hourly days: {len(alln)} of {len(hd)} (all Delta/Binance coins); {len(plan)} of the plan's "
          f"{len(coins)}")
    print(f"  coin-days hourly: all coins {sum(alln.values())} of {sum(len(df) for _, df, *_ in res if df) // 24}; "
          f"the plan's coins {sum(plan.values())}")
    print("  the plan's coins, most hourly days first: " + ', '.join(f"{c} {n}" for c, n in sorted(plan.items(), key=lambda k: -k[1])[:15]))
    OUT.update(hourly_coins_all=len(alln), hourly_coins_plan=plan)
    # an independent check: was Binance paying hourly on those days too (a squeeze on both)?
    bn = {'>= 9': 0, '6-8': 0, '<= 5': 0}
    for c, df, dp, dm, bf, bp in res:
        if c not in hd or not hd[c]:
            continue
        per = {}
        for t, r in bf or []:
            per[t // 1000 // X.DAY * X.DAY] = per.get(t // 1000 // X.DAY * X.DAY, 0) + 1
        for d in hd[c]:
            n = per.get(d, 0)
            bn['>= 9' if n >= 9 else ('6-8' if n >= 6 else '<= 5')] += 1
    print(f"  Binance's payments on those days: >= 9 a day (hourly too) {bn['>= 9']}, 6-8 {bn['6-8']}, <= 5 {bn['<= 5']}")
    OUT['binance_on_hourly_days'] = bn
    rows = {}
    for flag in (False, True):
        X.C549_HOURLY = flag
        allm = X.matrices(prods, res, shift00=True, mark=True)
        r = T.run3(allm, cv, coins)
        rows[flag] = dict(after1=r['after1'], avg=r['avg'], worst=r['worst'], neg=r['neg'], low=r['low'],
                          y1=r['y1'], y2=r['y2'], after2=r['after2'],
                          x1=T.run3(allm, cv, coins, cost_mult=1.0, with_sides=False)['after1'])
        if flag:
            fD_new = allm[2]
        else:
            fD_old = allm[2]
    X.C549_HOURLY = True
    o, n = rows[False], rows[True]
    print("\n  the plan's engine (10 pairs x 10%, K6, CoinDCX costs x5 as in Round 23; x1 = the expected case), the same "
          "coins, both ways:")
    print(f"  {'':22} {'before C549':>12} {'with C549':>12}")
    for k, nm, f in (('avg', 'before tax, a month', lambda x: f"{100 * x:+.2f}%"), ('after1', 'after tax, a month', lambda x: f"{100 * x:+.2f}%"),
                     ('x1', 'after tax, costs x1', lambda x: f"{100 * x:+.2f}%"),
                     ('worst', 'worst month', lambda x: f"{100 * x:+.2f}%"), ('neg', 'losing months', lambda x: f"{x}/24"),
                     ('low', 'poorer account lowest', lambda x: f"{100 * x:.1f}%"),
                     ('after2', 'after tax (2nd treatment)', lambda x: f"{100 * x:+.2f}%"),
                     ('y1', 'year 1 (Oct 24-Sep 25)', lambda x: f"{100 * x:+.1f}%"), ('y2', 'year 2 (Oct 25-Sep 26)', lambda x: f"{100 * x:+.1f}%")):
        print(f"  {nm:22} {f(o[k]):>12} {f(n[k]):>12}")
    diff = ~np.isnan(fD_old) & ~np.isnan(fD_new) & (np.abs(fD_old - fD_new) > 1e-12)
    print(f"\n  coin-days whose Delta funding changed: {int(diff.sum())} of {int((~np.isnan(fD_new)).sum())}")
    OUT.update(before=o, after=n, changed_days=int(diff.sum()))
    json.dump(OUT, open(os.path.join(HERE, 'c549_hourly_check.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
