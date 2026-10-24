#!/usr/bin/env python3
"""Round 16 (C525) H1: Binance vs Hyperliquid funding spread -- round 15's X1 rule, unchanged.

    python3 research/c525_hyperliquid.py CACHE_DIR

Rules and bar fixed in research/c525_preregistration.md (committed first). The simulation is
research/c524_xvenue.simulate() itself, with Hyperliquid in Delta's place:
  s       trailing 7-day mean of (Hyperliquid - Binance) daily funding, annualised, as paid by a long
  enter   |s| >= 20%/yr: short the perp where longs pay more, long it on the other venue
  exit    |s| < 10%/yr or a sign change; at most 10 pairs, 10% of capital per leg
  costs   Binance 0.05% + 0.02%; Hyperliquid taker 0.045% + 0.02%, each leg in and out
  window  2024-10-01 .. 2026-09-30; decided on day t's data, earning day t+1
  bar     net HAC t >= 2, >= 3 of 4 half-years positive, the last 6 months positive
Hyperliquid: fundingHistory (hourly, positive = longs pay) and 1-day candles; its 'k' coins are
Binance's '1000' coins (kPEPE = 1000PEPE). Public endpoints only.
"""
import os, sys, json, time, math, datetime as dt, concurrent.futures as cf
import numpy as np, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c524_xvenue as X

HL = 'https://api.hyperliquid.xyz/info'
DAY = 86400


def post(d, tries=6):
    for k in range(tries):
        try:
            r = requests.post(HL, json=d, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(5 + 5 * k)
                continue
        except Exception:
            pass
        time.sleep(1 + 2 * k)
    return None


def hl_funding(coin):
    out, t = {}, (X.START - 10 * DAY) * 1000
    while t < X.END * 1000:
        r = post({'type': 'fundingHistory', 'coin': coin, 'startTime': t})
        if not r:
            break
        for x in r:
            out[int(x['time']) // 3600000 * 3600] = float(x['fundingRate'])
        last = int(r[-1]['time'])
        if len(r) < 500 or last <= t:
            break
        t = last + 1
        time.sleep(0.25)
    return sorted(out.items())


def hl_daily(coin):
    r = post({'type': 'candleSnapshot', 'req': {'coin': coin, 'interval': '1d', 'startTime': (X.START - 10 * DAY) * 1000,
                                                'endTime': X.END * 1000}}) or []
    return sorted((int(x['t']) // 1000, float(x['c'])) for x in r)


def bin_name(c):
    return ('1000' + c[1:]) if c.startswith('k') and c[1:].isupper() else c


def main(cache):
    os.makedirs(cache, exist_ok=True)
    meta = post({'type': 'meta'})
    hl = [u['name'] for u in meta['universe'] if not u.get('isDelisted')]
    bset = X.binance_perps()
    pairs = [(c, bin_name(c)) for c in hl if bin_name(c) + 'USDT' in bset]
    print(f"Hyperliquid perps {len(hl)}; on Binance USDⓈ-M too: {len(pairs)}", flush=True)

    def one(a):
        c, b = a
        hf = X.cached(cache, 'hlfund_' + c, lambda: hl_funding(c))
        hp = X.cached(cache, 'hlpx_' + c, lambda: hl_daily(c))
        bf = X.cached(cache, 'bfund_' + b, lambda: X.bn_funding(b + 'USDT'))
        bp = X.cached(cache, 'bpx_' + b, lambda: X.bn_daily(b + 'USDT'))
        return b, hf, hp, bf, bp
    with cf.ThreadPoolExecutor(2) as ex:
        res = list(ex.map(one, pairs))

    def mats(shift00=False):
        D = np.arange(X.START, X.END, DAY)
        idx = {int(t): i for i, t in enumerate(D)}
        k = len(res)
        fH = np.full((len(D), k), np.nan); fB = fH.copy(); pH = fH.copy(); pB = fH.copy()
        names = []
        for j, (c, hf, hp, bf, bp) in enumerate(res):
            names.append(c)
            if not hf or not bf or not hp or not bp:
                continue
            dd = {}
            for t, r in hf:
                d = (t - (1 if shift00 else 0)) // DAY * DAY
                dd[d] = dd.get(d, 0.0) + r
            first = min(t for t, _ in hf) // DAY * DAY + DAY             # whole days only
            for d, x in dd.items():
                if d in idx and d >= first: fH[idx[d], j] = x
            bd = {}
            for t, r in bf:
                d = (t // 1000 - (1 if shift00 else 0)) // DAY * DAY
                bd[d] = bd.get(d, 0.0) + r
            for d, x in bd.items():
                if d in idx: fB[idx[d], j] = x
            for t, x in hp:
                if t in idx: pH[idx[t], j] = x
            for t, x in bp:
                if t in idx: pB[idx[t], j] = x
        return D, names, fH, fB, pH, pB
    X.COST_D = 0.00045 + 0.0002                     # Hyperliquid in the "other venue" slot
    M = mats()
    out = X.simulate(*M, tag='H1 Binance vs Hyperliquid')
    D, names, fH, fB, pH, pB = M
    rH = np.full_like(pH, np.nan); rB = rH.copy()
    rH[1:] = pH[1:] / pH[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    same = set()
    for j, c in enumerate(names):
        m = ~np.isnan(rH[:, j]) & ~np.isnan(rB[:, j])
        if m.sum() > 60 and np.corrcoef(rH[m, j], rB[m, j])[0, 1] >= 0.9:
            same.add(c)
    print(f"\nTHE SAME RULE, EACH ASSUMPTION MADE HARDER ({len(same)} of {len(names)} coins correlate >= 0.9)")
    rows = {}
    for tag, MM, kw in (('timing: 00:00 payment to the day before', mats(True), {}),
                        ('costs x5', M, dict(cost_mult=5)), ('costs x10', M, dict(cost_mult=10)),
                        ('identity: return correlation >= 0.9', M, dict(allow=same)),
                        ('ALL: timing + costs x5 + identity', mats(True), dict(cost_mult=5, allow=same))):
        r = X.simulate(*MM, verbose=False, **kw)
        rows[tag] = {k: v for k, v in r.items() if k not in ('months', 'coins')}
        print(f"  {tag:42} net {100 * r['net_ann']:+7.1f}%/yr  t {r['t']:+6.2f}  months+ {r['pos_months']}/{r['n_months']}  "
              f"worst month {100 * r['worst_month']:+6.2f}%  funding {100 * r['fund_ann']:+6.1f}  price {100 * r['price_ann']:+6.1f}  "
              f"costs {100 * r['cost_ann']:5.1f}  {'PASS' if r['passed'] else 'fail'}")
    sp = fH - fB
    v = sp[~np.isnan(sp)]
    print(f"\nthe daily spread Hyperliquid - Binance, all coin-days: mean {100 * 365 * v.mean():+.1f}%/yr, "
          f"|spread| >= 20%/yr on {100 * (np.abs(v) * 365 >= 0.20).mean():.0f}% of coin-days")
    json.dump(dict(primary={k: v for k, v in out.items() if k != 'coins'}, checks=rows),
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c525_hyperliquid.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
