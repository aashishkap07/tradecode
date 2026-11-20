#!/usr/bin/env python3
"""Round 22c: Delta + the better of two second exchanges, coin by coin (CoinDCX = Binance's rent, CoinSwitch = Bybit's).
An UPPER BOUND: the two rupee accounts are pooled as one. Rules fixed first in research/c542b_preregistration.md
(section "Round 22c", pushed before this ran).

    C524_MARK=1 python3 research/c542c_best.py XV_CACHE LOGS_DIR
"""
import os, sys, io, json, gzip, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C
import c542_pairs as P
import c542b_pairs as B

TAX = P.TAX


def s7_of(D, fD, fB, allow_mask):
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(D)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    s7[:, ~allow_mask] = np.nan
    return s7


def legs_best(D, names, fD, pD, venues, cv, cap, maxp, size, cost_mult=5.0, costD=None, gst=C.GST):
    """P.legs with several candidate second legs: venues = [(fB, pB, costB, allow), ...] in tie-break order"""
    costD = X.COST_D if costD is None else costD
    k = len(names)
    rD = np.full_like(pD, np.nan); rD[1:] = pD[1:] / pD[:-1] - 1
    V = []
    for fB, pB, costB, allow in venues:
        rB = np.full_like(pB, np.nan); rB[1:] = pB[1:] / pB[:-1] - 1
        am = np.array([n in allow for n in names])
        ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB) & am[None, :]
        V.append(dict(fB=fB, rB=rB, cB=costB * cost_mult, ok=ok, s7=s7_of(D, fD, fB, am)))
    cD = costD * cost_mult
    held, size_, where = {}, {}, {}
    pnl = np.zeros(len(D)); entered = 0
    live = np.arange(len(D)) >= X.WIN
    fyD, fyB, legB, closedB = {}, {}, {}, []
    pc = np.zeros(k); used = [0] * len(V)

    def book(i1, j, d_, b_):
        if not live[i1]:
            return
        y = P.fy_of(D[i1])
        fyD[y] = fyD.get(y, 0.0) + d_; fyB[y] = fyB.get(y, 0.0) + b_
        legB[j] = legB.get(j, 0.0) + b_
        pc[j] += d_ + b_
    for i in range(len(D) - 1):
        for j in list(held):
            v = V[where[j]]; sg = v['s7'][i, j]
            if np.isnan(sg) or abs(sg) < X.EXIT_ or np.sign(sg) != held[j]:
                pnl[i + 1] -= size_[j] * (v['cB'] + cD)
                book(i + 1, j, -size_[j] * cD, -size_[j] * v['cB'])
                closedB.append(legB.pop(j, 0.0))
                del held[j], size_[j], where[j]
        cand = []
        for j in range(k):
            if j in held:
                continue
            best = None
            for vi, v in enumerate(V):
                sg = v['s7'][i, j]
                if np.isnan(sg) or abs(sg) < X.ENTER or not v['ok'][i + 1, j]:
                    continue
                if best is None or abs(sg) > abs(V[best]['s7'][i, j]):
                    best = vi
            if best is not None:
                cand.append((j, best))
        cand.sort(key=lambda t: -abs(V[t[1]]['s7'][i, t[0]]))
        room = maxp - len(held)
        for j, vi in cand:
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
            held[j] = int(np.sign(V[vi]['s7'][i, j])); size_[j] = sz; where[j] = vi
            pnl[i + 1] -= sz * (V[vi]['cB'] + cD)
            legB[j] = 0.0
            book(i + 1, j, -sz * cD, -sz * V[vi]['cB'])
            room -= 1; entered += 1; used[vi] += 1
        for j, side in held.items():
            v = V[where[j]]
            if not v['ok'][i + 1, j]:
                continue
            fd_leg = side * fD[i + 1, j]
            fb_leg = -side * v['fB'][i + 1, j]
            fd_leg = fd_leg * (1 + gst) if fd_leg < 0 else fd_leg
            fb_leg = fb_leg * (1 + gst) if fb_leg < 0 else fb_leg
            d_ = size_[j] * (fd_leg - side * rD[i + 1, j])
            b_ = size_[j] * (fb_leg + side * v['rB'][i + 1, j])
            pnl[i + 1] += d_ + b_
            book(i + 1, j, d_, b_)
    closedB += list(legB.values())
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
    mv = np.array([months[m] for m in sorted(months)])
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, pre=float(x.sum()),
                tax1=float(t1), tax2=float(t2), used=used, avg=float(mv.mean()), worst=float(mv.min()), neg=int((mv < 0).sum()),
                after1=(float(x.sum()) - t1) / len(mv), after2=(float(x.sum()) - t2) / len(mv),
                y1=sum(v for m, v in months.items() if '2024-10' <= m <= '2025-09'),
                y2=sum(v for m, v in months.items() if '2025-10' <= m <= '2026-09'),
                per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def main(cache, logs):
    print("ROUND 22c: DELTA + THE BETTER OF COINDCX (BINANCE'S RENT) AND COINSWITCH (BYBIT'S), COIN BY COIN -- UPPER BOUND\n")
    src = json.load(open(os.path.join(logs, 'c542b_source.json')))
    hist = json.load(gzip.open(os.path.join(logs, 'c542b_bybit.json.gz'), 'rt'))
    census = set(json.load(open(os.path.join(HERE, 'c542b_census', 'mudrex_list_20261009.json'))))
    cs = set(src['coinswitch']['tickers']['EXCHANGE_2'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    D, names = allm[0], allm[1]
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    turn = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in prods}
    base = X.matrices(prods, res)
    fBy, pBy = B.bybit_mats(D, names, hist)
    same_bn = B.same_asset(base[4], base[5], names)
    same_by = B.same_asset(base[4], pBy, names)
    cv = S.delta_cv()
    dcx = set(json.load(open(os.path.join(HERE, 'c541_coindcx', 'coindcx_universe.json')))['both'])
    liq = {c for c in prods if turn.get(c, 0) >= 100000}
    a_dcx, a_cs, a_mx = liq & same_bn & dcx, liq & same_by & cs, liq & same_by & census
    print(f"Delta turnover read {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC; coins: CoinDCX leg {len(a_dcx)}, CoinSwitch leg {len(a_cs)}, "
          f"either {len(a_dcx | a_cs)}, both {len(a_dcx & a_cs)}")
    kw = dict(cv=cv, cap=1000.0, maxp=10, size=0.10)
    vd = (allm[3], allm[5], B.COST['coindcx'], a_dcx)
    vc = (fBy, pBy, B.COST['coinswitch'], a_cs)
    vm = (fBy, pBy, B.COST['mudrex'], a_mx)
    # engine checks
    r_c = P.legs(*allm, allow=a_dcx, costB=B.COST['coindcx'], **kw)
    r_s = P.legs(D, names, allm[2], fBy, allm[4], pBy, allow=a_cs, costB=B.COST['coinswitch'], **kw)
    e1 = legs_best(D, names, allm[2], allm[4], [vd, (fBy, pBy, B.COST['coinswitch'], set())], **kw)
    e2 = legs_best(D, names, allm[2], allm[4], [(allm[3], allm[5], B.COST['coindcx'], set()), vc], **kw)
    ok1 = all(abs(e1[k_] - r_c[k_]) < 1e-12 for k_ in ('net', 'pre', 'tax1', 'tax2'))
    ok2 = all(abs(e2[k_] - r_s[k_]) < 1e-12 for k_ in ('net', 'pre', 'tax1', 'tax2'))
    print(f"engine checks: CoinSwitch off == C {'OK' if ok1 else 'MISMATCH'}; CoinDCX off == S {'OK' if ok2 else 'MISMATCH'}")
    if not (ok1 and ok2):
        raise SystemExit(1)
    out = {}
    print(f"\n{'':28} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} | {'after T1':>8} {'T2':>6} | {'x1 pre':>7} {'x1 T1':>6} |")
    for tag, vs in (('C   Delta + CoinDCX', [vd]), ('S   Delta + CoinSwitch', [vc]),
                    ('B   best of CoinDCX/CoinSwitch', [vd, vc]), ('Bm  best of CoinDCX/Mudrex', [vd, vm])):
        r = legs_best(D, names, allm[2], allm[4], vs, **kw)
        r1 = legs_best(D, names, allm[2], allm[4], vs, cost_mult=1.0, **kw)
        print(f"{tag:28} | {r['avg']:+8.2%} {r['t']:5.2f} {r['worst']:+7.2%} {r['neg']:>2}/24 | {r['after1']:+8.2%} {r['after2']:+6.2%} | "
              f"{r1['avg']:+7.2%} {r1['after1']:+6.2%} | entries per venue {r['used']}")
        out[tag.split()[0]] = dict(avg=r['avg'], t=r['t'], worst=r['worst'], neg=r['neg'], after1=r['after1'], after2=r['after2'],
                                   x1_avg=r1['avg'], x1_after1=r1['after1'], used=r['used'], y1=r['y1'], y2=r['y2'])
    c, b = out['C'], out['B']
    bar = max(c['after1'], B.C_OCT8['after1']) + 0.005
    bar1 = max(c['x1_after1'], B.C_OCT8['x1_after1'])
    print(f"\nTHE DECISION (pre-registered): the upper bound B must reach T1 >= {bar:+.2%} at costs x5 and beat {bar1:+.2%} at x1")
    go = b['after1'] >= bar and b['x1_after1'] > bar1
    print(f"  B: T1 {b['after1']:+.2%} at x5, {b['x1_after1']:+.2%} at x1 => "
          + ('build the full three-account engine (its own round, before B2)' if go else
             'DROPPED: even pooled (an upper bound) it does not beat Delta + CoinDCX by the margin'))
    out['decision'] = 'build' if go else 'dropped'
    json.dump(out, open(os.path.join(HERE, 'c542c_best.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
