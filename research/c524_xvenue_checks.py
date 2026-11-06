#!/usr/bin/env python3
"""Round 15 (C524) Part B, robustness (descriptive; the pre-registered verdict is c524_xvenue.py's).

    C524_MARK=1 python3 research/c524_xvenue_checks.py CACHE_DIR

A +97%/yr, t 12 result is first a suspect, so the same rule is re-run with each assumption
made harder:
  timing    the 00:00 UTC exchange credited to the day BEFORE (a position entered after the close
            would not receive it)
  price     Delta's daily MARK close instead of its last trade (a thin book's stale last trade)
  costs     x5 and x10 the assumed 0.07% / 0.079% per leg (Delta's small-coin spreads are 2-33 bp)
  liquidity only coins with >= $100k of Delta turnover today (a survivor-biased proxy: today's)
  identity  only coins whose daily returns correlate >= 0.9 across the two venues (same asset)
  all       everything at once
plus the coins' funding: how often Delta's per-exchange rate sits at one repeated extreme (a clamp).
"""
import os, sys, json, math
import numpy as np, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c524_xvenue as X


def main(cache):
    prods, res = X.load(cache)
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    base = X.matrices(prods, res)
    D, names, fD, fB, pD, pB = base
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    same = set()
    for j, c in enumerate(names):
        m = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m.sum() > 60 and np.corrcoef(rD[m, j], rB[m, j])[0, 1] >= 0.9:
            same.add(c)
    print(f"coins: {len(names)} on both; {len(liq & set(names))} with >= $100k Delta turnover today; "
          f"{len(same)} whose daily returns correlate >= 0.9 across venues")
    rows = []

    def run(tag, M, **kw):
        r = X.simulate(*M, verbose=False, **kw)
        rows.append((tag, r))
        print(f"  {tag:46} net {100 * r['net_ann']:+7.1f}%/yr  t {r['t']:+6.2f}  months+ {r['pos_months']}/{r['n_months']}  "
              f"worst month {100 * r['worst_month']:+6.2f}%  funding {100 * r['fund_ann']:+6.1f}  price {100 * r['price_ann']:+6.1f}  "
              f"costs {100 * r['cost_ann']:5.1f}  {'PASS' if r['passed'] else 'fail'}")
    print("\nTHE SAME RULE, EACH ASSUMPTION MADE HARDER")
    run('pre-registered', base)
    sh = X.matrices(prods, res, shift00=True)
    run('timing: 00:00 exchange to the day before', sh)
    mk = X.matrices(prods, res, mark=True)
    run("price: Delta's MARK close", mk)
    run('costs x5', base, cost_mult=5)
    run('costs x10', base, cost_mult=10)
    run('liquidity: Delta turnover >= $100k', base, allow=liq)
    run('identity: return correlation >= 0.9', base, allow=same)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    run('ALL: timing + mark + costs x5 + liquidity + identity', allm, cost_mult=5, allow=liq & same)
    run('ALL with costs x10', allm, cost_mult=10, allow=liq & same)
    # the spread's sign: who pays more
    sp = (fD - fB)
    v = sp[~np.isnan(sp)]
    print(f"\nthe daily spread Delta - Binance, all coin-days: mean {100 * 365 * v.mean():+.1f}%/yr, "
          f"Delta dearer for longs on {100 * (v > 0).mean():.0f}% of coin-days")
    # clamps: Delta's per-exchange values that repeat at an extreme
    print("\nDELTA'S PER-EXCHANGE RATE ON THE MOST-PICKED COINS (is it pinned at a clamp?)")
    for c in ('AIN', 'AIOT', '1000SATS', 'SOLV', 'AIO', 'IO', 'MANTA', 'VVV'):
        r_ = [x for x in res if x[0] == c]
        if not r_:
            continue
        recs = dict(r_[0][1])
        hrs = prods[c]['iv'] // 3600
        vals = np.array([v_ for t, v_ in recs.items() if (t // 3600) % hrs == 0 and X.START <= t < X.END])
        if len(vals) == 0:
            continue
        top = max(set(np.round(vals, 6)), key=lambda q: (np.round(vals, 6) == q).sum())
        print(f"  {c:9} {len(vals)} exchanges, median {np.median(vals):+.4f}%, 90th pct {np.percentile(vals, 90):+.4f}%, "
              f"max {vals.max():+.4f}%, the most common value {top:+.4f}% on {100 * (np.round(vals, 6) == top).mean():.0f}% of exchanges")
    json.dump({t: {k: v for k, v in r.items() if k != 'months'} for t, r in rows},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c524_xvenue_checks.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
