#!/usr/bin/env python3
"""Round 17 (C530): each venue's risk in the cross-venue trade, and legs scaled by each coin's own
volatility (X1v) -- as pre-registered in research/c530_preregistration.md (pushed first, 5bfde5f).

    python3 research/c530_xvenue_sizing.py XV_CACHE

The X1 loop of research/c524_xvenue.py with each venue's legs kept apart:
  Binance leg (long when side = +1): size x side x (Binance return - Binance funding paid by a long)
  Delta leg  (short when side = +1): size x side x (Delta funding paid by a long - Delta return)
  costs: each venue's own, in and out
Each side = half the capital + its own legs' P&L since the 1st of the month (a re-balance between the
venues assumed monthly). X1: every leg 10% of capital. X1v: 10% x min(1, sigma_med / sigma_c) at entry.
"""
import os, sys, json, math, datetime as dt
import numpy as np, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c524_xvenue as X


def run(Dd, names, fD, fB, pD, pB, scaled=False, cost_mult=1.0, allow=None):
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    sd30 = np.full_like(rB, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(Dd)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
        for i in range(30, len(Dd)):
            w = rB[i - 29:i + 1]
            n = (~np.isnan(w)).sum(0)
            sd30[i] = np.where(n >= 20, np.nanstd(w, 0), np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = X.COST_B * cost_mult, X.COST_D * cost_mult
    held, size = {}, {}
    pnl = np.zeros(len(Dd)); legB = np.zeros(len(Dd)); legD = np.zeros(len(Dd)); gross = np.zeros(len(Dd))
    for i in range(len(Dd) - 1):
        sig = s7[i]
        for j in list(held):
            side = held[j]
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != side:
                legB[i + 1] -= size[j] * cB; legD[i + 1] -= size[j] * cD
                del held[j], size[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        med = float(np.nanmedian([sd30[i, j] for j in cand])) if cand else float('nan')
        cand.sort(key=lambda j: -abs(sig[j]))
        for j in cand[:max(0, X.MAXP - len(held))]:
            sz = X.SIZE
            if scaled and np.isfinite(sd30[i, j]) and sd30[i, j] > 0 and np.isfinite(med):
                sz = X.SIZE * min(1.0, med / sd30[i, j])
            held[j] = int(np.sign(sig[j])); size[j] = sz
            legB[i + 1] -= sz * cB; legD[i + 1] -= sz * cD
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            legB[i + 1] += size[j] * side * (rB[i + 1, j] - fB[i + 1, j])
            legD[i + 1] += size[j] * side * (fD[i + 1, j] - rD[i + 1, j])
            gross[i + 1] += size[j]
    pnl = legB + legD
    live = np.arange(len(Dd)) >= X.WIN
    x = pnl[live]; Dl = Dd[live]; lb = legB[live]; ld = legD[live]
    # each side, re-balanced on the 1st of each month
    months = {}
    sideB = sideD = 0.5
    cur = None
    for d_, b_, dd_ in zip(Dl, lb, ld):
        m = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        if m != cur:
            tot = sideB + sideD
            sideB = sideD = tot / 2.0
            half = tot / 2.0
            cur = m
            months[m] = dict(half=half, low=1.0)
        sideB += b_; sideD += dd_
        months[m]['low'] = min(months[m]['low'], sideB / half, sideD / half)
    lows = np.array([v['low'] for v in months.values()])
    ann = x.mean() * 365
    t = X.hac_t(x)
    mon = {}
    for d_, v in zip(Dl, x):
        m = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        mon[m] = mon.get(m, 0.0) + v
    halves = [('2024-10', '2025-03'), ('2025-04', '2025-09'), ('2025-10', '2026-03'), ('2026-04', '2026-09')]
    hp = [sum(v for m, v in mon.items() if a <= m <= b) for a, b in halves]
    return dict(net_ann=float(ann), t=float(t), halves=hp, pos_halves=int(sum(h > 0 for h in hp)),
                low_median=float(np.median(lows)), low_worst=float(lows.min()),
                share65=float((lows < 0.65).mean()), share50=float((lows < 0.50).mean()), n_months=len(lows),
                avg_gross=float(gross[live].mean()), lows={m: round(v['low'], 3) for m, v in months.items()})


def main(cache):
    prods, res = X.load(cache)
    base = X.matrices(prods, res)
    Dd, names, fD, fB, pD, pB = base
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    rD = np.full_like(pD, np.nan); rB = rD.copy(); rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    same = set()
    for j, c in enumerate(names):
        m = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m.sum() > 60 and np.corrcoef(rD[m, j], rB[m, j])[0, 1] >= 0.9:
            same.add(c)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    out = {}
    print("ROUND 17 (C530): THE CROSS-VENUE TRADE'S TWO ACCOUNTS, 2024-10 -> 2026-09, daily closes\n")
    print("                          net/yr     t     halves+   gross   lowest side in a month: median  worst   months <65%  <50%")
    for tag, M, kw in (('X1  as pre-registered', base, {}), ('X1  ALL harder', allm, dict(cost_mult=5, allow=liq & same)),
                       ('X1v as pre-registered', base, dict(scaled=True)),
                       ('X1v ALL harder', allm, dict(scaled=True, cost_mult=5, allow=liq & same))):
        r = run(*M, **kw)
        out[tag] = r
        print(f"  {tag:22} {100 * r['net_ann']:+7.1f}%  {r['t']:+5.2f}   {r['pos_halves']}/4    {r['avg_gross']:.2f}       "
              f"{100 * r['low_median']:5.1f}%  {100 * r['low_worst']:5.1f}%     {100 * r['share65']:4.0f}%   {100 * r['share50']:4.0f}%")
    a, b = out['X1  ALL harder'], out['X1v ALL harder']
    ca = (100 * (b['low_worst'] - a['low_worst']) >= 10) or (a['share50'] > 0 and b['share50'] <= a['share50'] / 2) \
        or (a['share50'] == 0 and b['share50'] == 0 and 100 * (b['low_worst'] - a['low_worst']) >= 10)
    cb = b['net_ann'] >= 0.70 * a['net_ann']
    cc = b['t'] >= 2 and b['pos_halves'] >= 3
    print(f"\nBAR (on the ALL-harder runs): (a) worst lowest side +{100 * (b['low_worst'] - a['low_worst']):.1f} points "
          f"or months <50% {100 * a['share50']:.0f}% -> {100 * b['share50']:.0f}%: {'met' if ca else 'NOT met'}; "
          f"(b) net {100 * b['net_ann'] / a['net_ann'] if a['net_ann'] else 0:.0f}% of X1's: {'met' if cb else 'NOT met'}; "
          f"(c) t {b['t']:.2f}, {b['pos_halves']}/4 halves: {'met' if cc else 'NOT met'}")
    verdict = ca and cb and cc
    print(f"VERDICT: X1v {'REPLACES' if verdict else 'does NOT replace'} X1 in the ledger")
    out['verdict'] = bool(verdict)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c530_xvenue_sizing.json'), 'w'),
              indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
