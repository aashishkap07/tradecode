#!/usr/bin/env python3
"""Round 21 (C541): CoinDCX in Pi42's place as the rent-gap trade's second leg. Rules and bar fixed first in
research/c541_preregistration.md (pushed before this ran).

    C524_MARK=1 python3 research/c541_coindcx.py XV_CACHE

The Round 20 engine unchanged: research/c532_india_only.py's xv_pi42 ("ALL harder") at $1,000, 10% a leg,
whole Delta contracts; research/c531_split_600.py's sides with the 65% even-out. Only the second leg's coin
list and its cost a side change:
  P0  Pi42's coins,    Pi42's fee    (0.10% x 1.18 + 0.02%)   -- today's plan, the reference
  D1  Pi42's coins,    CoinDCX's fee (0.05% x 1.18 + 0.02%)   -- the fee alone
  D2  CoinDCX's coins, CoinDCX's fee                          -- the candidate
CoinDCX's rent = Binance's (identical on 191 of 191 coins, 8 Oct: research/c541_coindcx/), as for Pi42.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C

COST_DCX = 0.0005 * 1.18 + 0.0002


def per_coin(D, names, fD, fB, pD, pB, cv, cap, allow, cost_mult=5.0, gst=C.GST):
    """xv_pi42's own loop, with each coin's P&L kept apart (checked against xv_pi42's total below)"""
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    am = np.array([n in allow for n in names])
    ok &= am[None, :]
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(D)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    s7[:, ~am] = np.nan
    cB, cD = C.COST_PI42 * cost_mult, X.COST_D * cost_mult
    held, size = {}, {}
    pc = np.zeros(k); days = np.zeros(k, int)
    for i in range(len(D) - 1):
        sig = s7[i]
        live = i + 1 >= X.WIN
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                if live: pc[j] -= size[j] * (cB + cD)
                del held[j], size[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        room = X.MAXP - len(held)
        for j in cand:
            if room <= 0:
                break
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                continue
            kq = int(round(X.SIZE * cap / (c_ * px)))
            if kq < 1:
                continue
            sz = kq * c_ * px / cap
            held[j] = int(np.sign(sig[j])); size[j] = sz
            if live: pc[j] -= sz * (cB + cD)
            room -= 1
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            fd_leg = side * fD[i + 1, j]
            fb_leg = -side * fB[i + 1, j]
            fd_leg = fd_leg * (1 + gst) if fd_leg < 0 else fd_leg
            fb_leg = fb_leg * (1 + gst) if fb_leg < 0 else fb_leg
            if live:
                pc[j] += size[j] * (fd_leg + fb_leg + side * (rB[i + 1, j] - rD[i + 1, j])); days[j] += 1
    nl = (np.arange(len(D)) >= X.WIN).sum()
    return {names[j]: (float(pc[j] / nl * 365), int(days[j])) for j in range(k) if days[j] or pc[j]}


def run(allm, cv, allow, cost):
    """one variant: (xv_pi42 result, monthly array, sides) with the second leg's cost set to `cost`"""
    old = C.COST_PI42, X.COST_B
    try:
        C.COST_PI42 = cost
        r = C.xv_pi42(*allm, cv=cv, cap=1000.0, allow=allow)
        X.COST_B = cost
        sd = S.sides(allm, 1000.0, cv, trigger=0.65, allow=allow)
    finally:
        C.COST_PI42, X.COST_B = old
    ks = sorted(r['months'])
    return r, np.array([r['months'][k] for k in ks]), sd, ks


def years(r):
    y1 = sum(v for k, v in r['months'].items() if '2024-10' <= k <= '2025-09')
    y2 = sum(v for k, v in r['months'].items() if '2025-10' <= k <= '2026-09')
    h = [sum(v for k, v in r['months'].items() if a <= k <= b) for a, b in
         (('2024-10', '2025-03'), ('2025-04', '2025-09'), ('2025-10', '2026-03'), ('2026-04', '2026-09'))]
    return y1, y2, h


def main(cache):
    print("ROUND 21 (C541): COINDCX IN PI42'S PLACE AS THE SECOND LEG, $1,000 (pre-registered)\n")
    pi42 = set(json.load(open(os.path.join(HERE, 'c532_pi42', 'pi42_universe.json')))['both'])
    dcx = set(json.load(open(os.path.join(HERE, 'c541_coindcx', 'coindcx_universe.json')))['both'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
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
    cv = S.delta_cv()

    def lst(venue, floor=100000):
        return {c for c in prods if turn.get(c, 0) >= floor} & same & venue
    L = {'P0': lst(pi42), 'D1': lst(pi42), 'D2': lst(dcx)}
    print(f"Delta turnover read {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC. Coins (>= $100k a day on Delta, the same asset):")
    print(f"  Pi42's list: {len(L['P0'])}   CoinDCX's list: {len(L['D2'])}   in CoinDCX's but not Pi42's: "
          f"{len(L['D2'] - L['P0'])}   in Pi42's but not CoinDCX's: {sorted(L['P0'] - L['D2'])}\n")
    cost = {'P0': C.COST_PI42, 'D1': COST_DCX, 'D2': COST_DCX}
    OUT, R = {}, {}
    hdr = (f"{'':4} {'net/yr':>7} {'t':>5} {'entries':>7} {'avg/month':>9} {'worst month':>11} {'months<0':>8} "
           f"{'months>=2%':>10} | {'poorer acct':>11} {'transfers/yr':>12} | {'Oct24-Sep25':>11} {'Oct25-Sep26':>11}")
    print(hdr)
    for v in ('P0', 'D1', 'D2'):
        r, mv, sd, ks = run(allm, cv, L[v], cost[v])
        y1, y2, h = years(r)
        R[v] = (r, mv, sd)
        OUT[v] = dict(coins=len(L[v]), cost=cost[v], net=r['net'], t=r['t'], entered=r['entered'],
                      avg_month=float(mv.mean()), worst_month=float(mv.min()), months_neg=int((mv < 0).sum()),
                      months_ge2=float((mv >= 0.02).mean()), low_side=sd['low_side'], transfers_yr=sd['transfers_yr'],
                      year1=y1, year2=y2, halves=h, months=dict(zip(ks, mv.tolist())))
        print(f"{v:4} {100 * r['net']:+6.1f}% {r['t']:5.2f} {r['entered']:7d} {100 * mv.mean():+8.2f}% {100 * mv.min():+10.2f}% "
              f"{int((mv < 0).sum()):5d}/{len(mv)} {100 * (mv >= 0.02).mean():9.0f}% | {100 * sd['low_side']:10.1f}% "
              f"{sd['transfers_yr']:12.1f} | {100 * y1:+10.1f}% {100 * y2:+10.1f}%")
    print("\nhalf-years (Oct-Mar, Apr-Sep, Oct-Mar, Apr-Sep):")
    for v in ('P0', 'D1', 'D2'):
        print(f"  {v}: " + "  ".join(f"{100 * x:+6.1f}%" for x in OUT[v]['halves']))

    # the engine check: the per-coin loop must give xv_pi42's own total
    old = C.COST_PI42
    C.COST_PI42 = COST_DCX
    try:
        pcs = per_coin(*allm, cv=cv, cap=1000.0, allow=L['D2'])
    finally:
        C.COST_PI42 = old
    tot = sum(x for x, _ in pcs.values())
    print(f"\nengine check: D2's per-coin sum {100 * tot:+.3f}%/yr vs xv_pi42 {100 * OUT['D2']['net']:+.3f}%/yr "
          f"-> {'OK' if abs(tot - OUT['D2']['net']) < 1e-9 else 'MISMATCH'}")
    top = sorted(pcs.items(), key=lambda kv: -kv[1][0])
    print("D2's coins by P&L (%/yr of $1,000, days held): " +
          ", ".join(f"{c} {100 * x:+.1f} ({d}d)" for c, (x, d) in top[:12]))
    print("  ... the five largest losers: " + ", ".join(f"{c} {100 * x:+.1f} ({d}d)" for c, (x, d) in top[-5:]))
    OUT['D2']['per_coin'] = {c: dict(net=x, days=d) for c, (x, d) in pcs.items()}

    print("\nLIST WOBBLE (D2): worst month and poorer account")
    wob = {}
    for c, _ in top[:5]:
        r, mv, sd, _k = run(allm, cv, L['D2'] - {c}, COST_DCX)
        wob['without ' + c] = (r['net'], float(mv.min()), sd['low_side'])
    for fl in (75000, 150000):
        r, mv, sd, _k = run(allm, cv, lst(dcx, fl), COST_DCX)
        wob[f'turnover floor ${fl // 1000}k ({len(lst(dcx, fl))} coins)'] = (r['net'], float(mv.min()), sd['low_side'])
    for k_, (n, w, lo) in wob.items():
        print(f"  {k_:34} net {100 * n:+6.1f}%/yr   worst month {100 * w:+6.2f}%   poorer account {100 * lo:5.1f}%   "
              f"{'ok' if w >= -0.04 and lo >= 0.40 else 'FAILS'}")
    OUT['D2']['wobble'] = {k_: dict(net=n, worst_month=w, low_side=lo) for k_, (n, w, lo) in wob.items()}

    d = OUT['D2']
    bar = {
        'G1 average month >= +1.5%': d['avg_month'] >= 0.015,
        'G1 no month below -4%': d['worst_month'] >= -0.04,
        'G1 poorer account >= 40%': d['low_side'] >= 0.40,
        'HAC t >= 2.0': d['t'] >= 2.0,
        'both years positive': d['year1'] > 0 and d['year2'] > 0,
        'list wobble holds': all(w >= -0.04 and lo >= 0.40 for _, w, lo in wob.values()),
    }
    print("\nTHE BAR FOR D2:")
    for k_, ok in bar.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k_}")
    d['bar'] = bar
    d['passed'] = all(bar.values())
    print(f"\nRESULT: D2 {'PASSES -- CoinDCX can take Pi42' + chr(39) + 's place as the second leg' if d['passed'] else 'FAILS -- the plan stays on Pi42'}")
    json.dump(OUT, open(os.path.join(HERE, 'c541_coindcx.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
