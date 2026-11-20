#!/usr/bin/env python3
"""Round 22 (C542): the best exchange pair for the rent-gap trade, and its best settings, after tax. Rules and
bars fixed first in research/c542_preregistration.md (pushed before this ran).

    C524_MARK=1 python3 research/c542_pairs.py XV_CACHE

Engine: Round 21's (research/c532_india_only.py's xv_pi42 "ALL harder", research/c531_split_600.py's sides with
the 65% even-out), plus `legs`, a copy of xv_pi42's loop that keeps each position's two legs apart for tax and
takes the number of pairs and the bet size as arguments. `legs` must reproduce xv_pi42's pre-tax total exactly.
Tax at the operator's top slab, 31.2%:
  T1  both legs speculative business income, netted by Indian financial year (Apr-Mar), losses carried forward;
  T2  the second leg a VDA (31.2% of each closed position's leg gain, losses ignored), the Delta leg as T1.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C

TAX = 0.312
COST = {'pi42': 0.0010 * 1.18 + 0.0002, 'coindcx': 0.0005 * 1.18 + 0.0002, 'zebpay': 0.0010 * 1.18 + 0.0002}
MAKER = 0.0002 * 1.18                                           # Part C: a filled limit order, no half-spread


def fy_of(t):
    d = dt.datetime.utcfromtimestamp(int(t))
    return d.year if d.month >= 4 else d.year - 1


def legs(D, names, fD, fB, pD, pB, cv, cap, allow, costB, maxp, size, cost_mult=5.0, costD=None, gst=C.GST):
    """xv_pi42's loop, with each position's Delta and second legs kept apart; returns pre-tax and both taxes"""
    costD = X.COST_D if costD is None else costD
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
    cB, cD = costB * cost_mult, costD * cost_mult
    held, size_ = {}, {}
    pnl = np.zeros(len(D)); entered = 0
    live = np.arange(len(D)) >= X.WIN
    fyD, fyB, legB, closedB = {}, {}, {}, []                    # by financial year: Delta legs, second legs
    pc = np.zeros(k)

    def book(i1, j, d_, b_):
        if not live[i1]:
            return
        y = fy_of(D[i1])
        fyD[y] = fyD.get(y, 0.0) + d_; fyB[y] = fyB.get(y, 0.0) + b_
        legB[j] = legB.get(j, 0.0) + b_
        pc[j] += d_ + b_
    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                pnl[i + 1] -= size_[j] * (cB + cD)
                book(i + 1, j, -size_[j] * cD, -size_[j] * cB)
                closedB.append(legB.pop(j, 0.0))
                del held[j], size_[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        room = maxp - len(held)
        for j in cand:
            if room <= 0:
                break
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                continue
            kq = int(round(size * cap / (c_ * px)))
            if kq < 1:
                continue
            sz = kq * c_ * px / cap
            held[j] = int(np.sign(sig[j])); size_[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            legB[j] = 0.0
            book(i + 1, j, -sz * cD, -sz * cB)
            room -= 1; entered += 1
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            fd_leg = side * fD[i + 1, j]
            fb_leg = -side * fB[i + 1, j]
            fd_leg = fd_leg * (1 + gst) if fd_leg < 0 else fd_leg
            fb_leg = fb_leg * (1 + gst) if fb_leg < 0 else fb_leg
            d_ = size_[j] * (fd_leg - side * rD[i + 1, j])
            b_ = size_[j] * (fb_leg + side * rB[i + 1, j])
            pnl[i + 1] += d_ + b_
            book(i + 1, j, d_, b_)
    closedB += list(legB.values())                              # still open at the end: counted as closed
    x = pnl[live]; Dl = D[live]
    months = {}
    for d_, v in zip(Dl, x):
        m = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        months[m] = months.get(m, 0.0) + v

    def fy_tax(fy):
        carry, tax = 0.0, 0.0
        for y in sorted(fy):
            net = fy[y] + carry
            if net > 0:
                tax += TAX * net; carry = 0.0
            else:
                carry = net
        return tax
    tot = {y: fyD.get(y, 0.0) + fyB.get(y, 0.0) for y in set(fyD) | set(fyB)}
    t1 = fy_tax(tot)
    t2 = fy_tax(fyD) + TAX * sum(v for v in closedB if v > 0)
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, pre=float(x.sum()),
                tax1=float(t1), tax2=float(t2), per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def run(allm, cv, allow, cost, maxp=10, size=0.10, cost_mult=5.0, costD=None, with_sides=True):
    r = legs(*allm, cv=cv, cap=1000.0, allow=allow, costB=cost, maxp=maxp, size=size, cost_mult=cost_mult, costD=costD)
    ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
    nm = len(mv)
    r.update(mv=mv, avg=float(mv.mean()), worst=float(mv.min()), neg=int((mv < 0).sum()),
             after1=(r['pre'] - r['tax1']) / nm, after2=(r['pre'] - r['tax2']) / nm,
             ge2=float((mv >= 0.02 / (1 - TAX)).mean()),
             y1=sum(v for k, v in r['months'].items() if '2024-10' <= k <= '2025-09'),
             y2=sum(v for k, v in r['months'].items() if '2025-10' <= k <= '2026-09'))
    if with_sides:
        old = X.COST_B, X.MAXP, X.SIZE, X.COST_D
        try:
            X.COST_B, X.MAXP, X.SIZE = cost, maxp, size
            if costD is not None:
                X.COST_D = costD
            sd = S.sides(allm, 1000.0, cv, trigger=0.65, allow=allow, cost_mult=cost_mult)
        finally:
            X.COST_B, X.MAXP, X.SIZE, X.COST_D = old
        r['low'] = sd['low_side']
    return r


def main(cache):
    print("ROUND 22 (C542): THE BEST EXCHANGE PAIR AND ITS SETTINGS, AFTER TAX (pre-registered)\n")
    pi42 = set(json.load(open(os.path.join(HERE, 'c532_pi42', 'pi42_universe.json')))['both'])
    dcx = set(json.load(open(os.path.join(HERE, 'c541_coindcx', 'coindcx_universe.json')))['both'])
    zb = json.load(open(os.path.join(HERE, 'c542_census', 'zebpay_delta_20261008.json')))
    zi, za = set(zb['zeb_inr_delta']), set(zb['zeb_inr_delta']) | set(zb['zeb_usdt_delta'])
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
    V = {'P0': (pi42, 'pi42'), 'C': (dcx, 'coindcx'), 'Zi': (zi, 'zebpay'), 'Za': (za, 'zebpay')}
    print(f"Delta turnover read {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC; coins per pair (>= $100k a day on Delta, the same "
          f"asset): " + ", ".join(f"{v} {len(lst(V[v][0]))}" for v in V))

    # the engine check: legs == xv_pi42 (pre-tax) at today's settings, for every pair
    chk = []
    for v, (ven, cn) in V.items():
        old = C.COST_PI42
        C.COST_PI42 = COST[cn]
        try:
            a = C.xv_pi42(*allm, cv=cv, cap=1000.0, allow=lst(ven))['net']
        finally:
            C.COST_PI42 = old
        b = legs(*allm, cv=cv, cap=1000.0, allow=lst(ven), costB=COST[cn], maxp=X.MAXP, size=X.SIZE)['net']
        chk.append(abs(a - b) < 1e-12)
    print(f"engine check (legs == xv_pi42 pre-tax, all four pairs): {'OK' if all(chk) else 'MISMATCH ' + str(chk)}\n")
    if not all(chk):
        raise SystemExit(1)
    OUT = {'A': {}, 'B': {}, 'C': {}}

    def wobble(allow_fn, ven, cost, maxp, size, per_coin):
        top = [c for c, _ in sorted(per_coin.items(), key=lambda kv: -kv[1])[:5]]
        res_ = {}
        for c in top:
            r = run(allm, cv, allow_fn(ven) - {c}, cost, maxp, size)
            res_['without ' + c] = (r['worst'], r['low'], r['after1'])
        for fl in (75000, 150000):
            r = run(allm, cv, allow_fn(ven, fl), cost, maxp, size)
            res_[f'floor ${fl // 1000}k'] = (r['worst'], r['low'], r['after1'])
        return res_

    def bars(r, wob):
        return {'average month >= +1.5%': r['avg'] >= 0.015, 'no month below -4%': r['worst'] >= -0.04,
                'poorer account >= 40%': r['low'] >= 0.40, 'HAC t >= 2': r['t'] >= 2.0,
                'both years positive': r['y1'] > 0 and r['y2'] > 0,
                'list wobble holds': all(w >= -0.04 and lo >= 0.40 for w, lo, _ in wob.values())}

    print("PART A: THE PAIR (10 pairs x 10% a leg, costs x5 = the gate; costs x1 = the expected case)")
    print(f"{'':3} {'coins':>5} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} | {'after tax T1':>12} "
          f"{'T2':>6} {'mo>=2% net':>10} | {'x1 pre':>7} {'x1 T1':>6} {'x1 T2':>6} | bars")
    for v, (ven, cn) in V.items():
        r = run(allm, cv, lst(ven), COST[cn])
        r1 = run(allm, cv, lst(ven), COST[cn], cost_mult=1.0, with_sides=False)
        wob = wobble(lst, ven, COST[cn], 10, 0.10, r['per_coin'])
        b = bars(r, wob)
        OUT['A'][v] = dict(coins=len(lst(ven)), cost=COST[cn], avg=r['avg'], t=r['t'], worst=r['worst'], neg=r['neg'],
                           low=r['low'], after1=r['after1'], after2=r['after2'], ge2=r['ge2'], y1=r['y1'], y2=r['y2'],
                           x1_avg=r1['avg'], x1_after1=r1['after1'], x1_after2=r1['after2'],
                           wobble={k: dict(worst=a, low=lo, after1=af) for k, (a, lo, af) in wob.items()},
                           bars=b, passed=all(b.values()), months=dict(zip(sorted(r['months']), r['mv'].tolist())))
        print(f"{v:3} {len(lst(ven)):5d} | {100 * r['avg']:+7.2f}% {r['t']:5.2f} {100 * r['worst']:+6.2f}% {r['neg']:2d}/24 "
              f"{100 * r['low']:5.1f}% | {100 * r['after1']:+11.2f}% {100 * r['after2']:+5.2f}% {100 * r['ge2']:9.0f}% | "
              f"{100 * r1['avg']:+6.2f}% {100 * r1['after1']:+5.2f}% {100 * r1['after2']:+5.2f}% | "
              f"{'PASS' if all(b.values()) else 'fail: ' + ', '.join(k for k, ok in b.items() if not ok)}")
    print("   (after tax = per month on $1,000 over 24 months; 'mo>=2% net' = months >= 2% after a 31.2% tax)")
    for v in V:
        w = OUT['A'][v]['wobble']
        print(f"   {v} wobble: worst month {100 * min(x['worst'] for x in w.values()):+.2f}%, poorer account "
              f"{100 * min(x['low'] for x in w.values()):.1f}%, after tax T1 {100 * min(x['after1'] for x in w.values()):+.2f}% "
              f"to {100 * max(x['after1'] for x in w.values()):+.2f}% a month")
    cand = [v for v in V if v != 'P0' and OUT['A'][v]['passed']]
    win1 = max(cand, key=lambda v: OUT['A'][v]['after1']) if cand else None
    win2 = max(cand, key=lambda v: OUT['A'][v]['after2']) if cand else None
    print(f"\nTHE PAIR (T1, the plan's tax reading): {win1}   if a CA rules its second leg a VDA (T2): {win2}")
    OUT['winner_T1'], OUT['winner_T2'] = win1, win2
    if not win1:
        json.dump(OUT, open(os.path.join(HERE, 'c542_pairs.json'), 'w'), indent=1, default=float)
        return
    ven, cn = V[win1]

    print(f"\nPART B: {win1}'S SETTINGS (at most N pairs x S a leg; costs x5)")
    print(f"{'N':>3} {'S':>4} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} | {'after T1':>8} {'T2':>6} "
          f"{'$/yr vs 10x10%':>14} | {'wobble worst':>12} {'poorer':>6} | bars")
    base_r = None
    for n in (10, 15, 20):
        for s in (0.08, 0.10, 0.12):
            r = run(allm, cv, lst(ven), COST[cn], n, s)
            wob = wobble(lst, ven, COST[cn], n, s, r['per_coin'])
            b = bars(r, wob)
            if (n, s) == (10, 0.10):
                base_r = r
            OUT['B'][f'{n}x{int(round(s * 100))}'] = dict(n=n, s=s, avg=r['avg'], t=r['t'], worst=r['worst'], neg=r['neg'],
                                                          low=r['low'], after1=r['after1'], after2=r['after2'], ge2=r['ge2'],
                                                          wob_worst=min(w for w, _, _ in wob.values()),
                                                          wob_low=min(lo for _, lo, _ in wob.values()), bars=b,
                                                          all_bars=all(b.values()))
    for key, o in OUT['B'].items():
        gain = (o['after1'] - base_r['after1']) * 12 * 1000
        o['gain_yr'] = gain
        o['passed'] = (key != '10x10' and o['all_bars'] and gain >= 50 and o['neg'] <= base_r['neg'] + 1)
        print(f"{o['n']:3d} {int(round(o['s'] * 100)):3d}% | {100 * o['avg']:+7.2f}% {o['t']:5.2f} {100 * o['worst']:+6.2f}% "
              f"{o['neg']:2d}/24 {100 * o['low']:5.1f}% | {100 * o['after1']:+7.2f}% {100 * o['after2']:+5.2f}% "
              f"{gain:+13.0f} | {100 * o['wob_worst']:+11.2f}% {100 * o['wob_low']:5.1f}% | "
              f"{'PASS' if o['passed'] else ('base' if key == '10x10' else 'fail: ' + ', '.join(k for k, ok in o['bars'].items() if not ok) or 'fail: gain/months')}")
    ok_ = sorted((k for k, o in OUT['B'].items() if o['passed']), key=lambda k: -OUT['B'][k]['after1'])
    pick = '10x10'
    if ok_:
        best = OUT['B'][ok_[0]]
        close = [k for k in ok_ if (best['after1'] - OUT['B'][k]['after1']) * 12 * 1000 < 50]
        pick = min(close, key=lambda k: (OUT['B'][k]['n'], OUT['B'][k]['s']))
    OUT['B_pick'] = pick
    print(f"\nTHE SETTINGS: {pick}" + (" (no variant passed: 10 pairs x 10% stays)" if pick == '10x10' else ''))

    n_, s_ = OUT['B'][pick]['n'], OUT['B'][pick]['s']
    rm = run(allm, cv, lst(ven), MAKER, n_, s_, cost_mult=1.0, costD=MAKER, with_sides=False)
    rt = run(allm, cv, lst(ven), COST[cn], n_, s_, cost_mult=1.0, with_sides=False)
    OUT['C'] = dict(maker_avg=rm['avg'], maker_after1=rm['after1'], taker_x1_avg=rt['avg'], taker_x1_after1=rt['after1'])
    print(f"\nPART C (information only): {win1} {pick} at costs x1 -- taker {100 * rt['avg']:+.2f}%/month before tax "
          f"({100 * rt['after1']:+.2f}% after); every order a filled limit order at the maker fee: {100 * rm['avg']:+.2f}% "
          f"({100 * rm['after1']:+.2f}% after)")
    json.dump(OUT, open(os.path.join(HERE, 'c542_pairs.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
