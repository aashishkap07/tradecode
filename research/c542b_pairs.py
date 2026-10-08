#!/usr/bin/env python3
"""Round 22b: Mudrex and CoinSwitch (Bybit's rent) against the plan's Delta + CoinDCX. Rules fixed first in
research/c542b_preregistration.md (pushed before this ran).

    C524_MARK=1 python3 research/c542b_pairs.py XV_CACHE LOGS_DIR

LOGS_DIR holds the server's c542b_bybit.json.gz and c542b_source.json (the logs branch, research/c542b_server.py).
XV_CACHE is Round 22's cache (Delta and Binance history); Binance history for CoinDCX coins not on Delta is added to it.

Engine: Round 22's (research/c542_pairs.py) unchanged. `legs_ab` is a copy of its `legs` that also keeps each
position's FIRST leg apart, so that a pair of two rupee venues can be taxed with both legs as VDAs (T2 for CM/CS);
it must equal `legs` on everything `legs` returns before any figure is read.
"""
import os, sys, io, json, gzip, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C
import c542_pairs as P

TAX = P.TAX
COST = dict(P.COST)
COST['mudrex'] = 0.0005 * 1.18 + 0.0002
COST['coinswitch'] = 0.00055 * 1.18 + 0.0002
C_OCT8 = dict(after1=0.035479630415183774, x1_after1=0.04148093798076273)   # research/c542_pairs.json, A.C
TINY = 1e-12                                                                  # fractional sizing (no whole contracts)
DAY = X.DAY


def legs_ab(D, names, fD, fB, pD, pB, cv, cap, allow, costB, maxp, size, cost_mult=5.0, costD=None, gst=C.GST):
    """P.legs, line for line, plus the first leg's closed gains (closedA) for the both-legs-VDA reading"""
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
    fyD, fyB, legB, closedB, legA, closedA = {}, {}, {}, [], {}, []
    pc = np.zeros(k)

    def book(i1, j, d_, b_):
        if not live[i1]:
            return
        y = P.fy_of(D[i1])
        fyD[y] = fyD.get(y, 0.0) + d_; fyB[y] = fyB.get(y, 0.0) + b_
        legB[j] = legB.get(j, 0.0) + b_
        legA[j] = legA.get(j, 0.0) + d_
        pc[j] += d_ + b_
    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                pnl[i + 1] -= size_[j] * (cB + cD)
                book(i + 1, j, -size_[j] * cD, -size_[j] * cB)
                closedB.append(legB.pop(j, 0.0))
                closedA.append(legA.pop(j, 0.0))
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
            legB[j] = 0.0; legA[j] = 0.0
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
    closedB += list(legB.values())
    closedA += list(legA.values())
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
    t2ab = TAX * (sum(v for v in closedA if v > 0) + sum(v for v in closedB if v > 0))
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, pre=float(x.sum()),
                tax1=float(t1), tax2=float(t2), tax2ab=float(t2ab),
                per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def run(allm, cv, allow, cost, costD=None, cost_mult=5.0, both_vda=False):
    """P.run with legs_ab; T2 is the both-legs reading when both_vda"""
    old = P.legs
    try:
        P.legs = legs_ab
        r = P.run(allm, cv, allow, cost, 10, 0.10, cost_mult=cost_mult, costD=costD)
    finally:
        P.legs = old
    if both_vda:
        r['after2'] = (r['pre'] - r['tax2ab']) / len(r['mv'])
    return r


def bybit_mats(D, names, hist):
    idx = {int(t): i for i, t in enumerate(D)}
    f = np.full((len(D), len(names)), np.nan); p = f.copy()
    for j, c in enumerate(names):
        fr, dl = hist['funding'].get(c), hist['daily'].get(c)
        if not fr or not dl:
            continue
        bd = {}
        for t, r in fr:
            d = (int(t) // 1000 - 1) // DAY * DAY                         # shift00, as Round 22's Binance leg
            bd[d] = bd.get(d, 0.0) + float(r)
        for d, v in bd.items():
            if d in idx:
                f[idx[d], j] = v
        for row in dl:
            if int(row[0]) in idx:
                p[idx[int(row[0])], j] = float(row[1])
    return f, p


def binance_mats(cache, D, names):
    idx = {int(t): i for i, t in enumerate(D)}
    f = np.full((len(D), len(names)), np.nan); p = f.copy()
    for j, c in enumerate(names):
        bf = X.cached(cache, 'bfund_' + c, lambda: X.bn_funding(c + 'USDT'))
        bp = X.cached(cache, 'bpx_' + c, lambda: X.bn_daily(c + 'USDT'))
        bd = {}
        for t, r in bf or []:
            d = (t // 1000 - 1) // DAY * DAY
            bd[d] = bd.get(d, 0.0) + r
        for d, v in bd.items():
            if d in idx:
                f[idx[d], j] = v
        for t, x in bp or []:
            if t in idx:
                p[idx[t], j] = x
    return f, p


def same_asset(pa, pb, names):
    ra = np.full_like(pa, np.nan); rb = ra.copy()
    ra[1:] = pa[1:] / pa[:-1] - 1; rb[1:] = pb[1:] / pb[:-1] - 1
    out = set()
    for j, c in enumerate(names):
        m_ = ~np.isnan(ra[:, j]) & ~np.isnan(rb[:, j])
        if m_.sum() > 60 and np.corrcoef(ra[m_, j], rb[m_, j])[0, 1] >= 0.9:
            out.add(c)
    return out


def share(a, b, tol=2e-5):
    common = [c for c in a if c in b and a[c] is not None and b[c] is not None]
    return len(common), (sum(1 for c in common if abs(float(a[c]) - float(b[c])) <= tol) / len(common) if common else 0.0)


def main(cache, logs):
    print("ROUND 22b: MUDREX AND COINSWITCH (BYBIT'S RENT) AGAINST DELTA + COINDCX (pre-registered)\n")
    src = json.load(open(os.path.join(logs, 'c542b_source.json')))
    hist = json.load(gzip.open(os.path.join(logs, 'c542b_bybit.json.gz'), 'rt'))
    census = set(json.load(open(os.path.join(HERE, 'c542b_census', 'mudrex_list_20261009.json'))))
    OUT = dict(source={}, pairs={}, read_at=None)

    # STEP 1: the source test, from the server's one-moment read
    print(f"STEP 1: whose rent does each venue copy? (server read {dt.datetime.utcfromtimestamp(src['at']):%Y-%m-%d %H:%M} UTC)")
    venues = {}
    m = (src.get('mudrex') or {}).get('assets')
    if m:
        best = 0.0
        for unit, f in (('fraction', 1.0), ('percent', 0.01)):
            mm = {c: (float(v['fr']) * f if v.get('fr') not in (None, '') else None) for c, v in m.items()}
            row = {name: share(mm, ref) for name, ref in (('Bybit predicted', src['bybit_pred']), ('Bybit settled', src.get('bybit_last') or {}),
                                                          ('Binance settled', src['binance_last']))}
            print(f"  Mudrex ({unit}): " + "; ".join(f"{k} {s:.0%} of {n}" for k, (n, s) in row.items()))
            best = max(best, row['Bybit predicted'][1], row['Bybit settled'][1])
            OUT['source'][f'mudrex_{unit}'] = row
        venues['mudrex'] = dict(coins=set(m), bybit=best >= 0.8, confirmed=True)
    else:
        print(f"  Mudrex: no keyed read ({(src.get('mudrex') or {}).get('error')}); tested on the census prior (its book is Bybit's), "
              f"UNCONFIRMED; its {len(census)} census coins")
        venues['mudrex'] = dict(coins=census, bybit=True, confirmed=False)
    cs_coins, cs_best, cs_read = set(), 0.0, False
    for code, rows in ((src.get('coinswitch') or {}).get('tickers') or {}).items():
        if not isinstance(rows, dict):
            print(f"  CoinSwitch {code}: {rows}"); continue
        cs_read = True
        cs = {c: (float(v['fr']) if v.get('fr') not in (None, '') else None) for c, v in rows.items()}
        row = {name: share(cs, ref) for name, ref in (('Bybit predicted', src['bybit_pred']), ('Bybit settled', src.get('bybit_last') or {}),
                                                      ('Binance settled', src['binance_last']))}
        print(f"  CoinSwitch {code}: " + "; ".join(f"{k} {s:.0%} of {n}" for k, (n, s) in row.items()))
        OUT['source'][f'coinswitch_{code}'] = row
        if max(row['Bybit predicted'][1], row['Bybit settled'][1]) >= 0.8:
            cs_coins |= set(cs); cs_best = max(cs_best, row['Bybit predicted'][1], row['Bybit settled'][1])
    if cs_coins:
        venues['coinswitch'] = dict(coins=cs_coins, bybit=True, confirmed=True)
    else:
        why = (src.get('coinswitch') or {}).get('error') or ('copies neither Bybit nor Binance at >= 80%' if cs_read
                                                             else 'its keyed read failed')
        print(f"  CoinSwitch: not tested ({why})")
    for v, d in venues.items():
        if not d['bybit']:
            print(f"  {v}: copies neither Bybit nor Binance at >= 80%: out of the pair test (no history of its own)")
    print()

    # STEP 2: the pairs
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    D, names = allm[0], allm[1]
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    turn = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in prods}
    OUT['read_at'] = f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"; OUT['delta_turnover'] = turn
    base = X.matrices(prods, res)
    same_bn = same_asset(base[4], base[5], names)
    cv = S.delta_cv()
    dcx = set(json.load(open(os.path.join(HERE, 'c541_coindcx', 'coindcx_universe.json')))['both'])
    fBy, pBy = bybit_mats(D, names, hist)
    same_by = same_asset(base[4], pBy, names)
    allm_by = (D, names, allm[2], fBy, allm[4], pBy)

    def lst_d(venue, same, floor=100000):
        return {c for c in prods if turn.get(c, 0) >= floor} & same & venue

    # engine check 1: the new path (legs_ab inside run) == Round 22's run() on identical inputs (today's list)
    a = P.run(allm, cv, lst_d(dcx, same_bn), COST['coindcx'])
    b = run(allm, cv, lst_d(dcx, same_bn), COST['coindcx'])
    chk1 = all(abs(a[k] - b[k]) < 1e-12 for k in ('pre', 'tax1', 'tax2', 'avg', 'worst', 'low', 'after1', 'after2'))
    print(f"engine check 1 (new path == Round 22's run on today's CoinDCX list): {'OK' if chk1 else 'MISMATCH'}")
    if not chk1:
        raise SystemExit(1)

    def wobble(allm_, cv_, allow_fn, ven, same, cost, costD, floors, both_vda, per_coin):
        top = [c for c, _ in sorted(per_coin.items(), key=lambda kv: -kv[1])[:5]]
        w = {}
        for c in top:
            r = run(allm_, cv_, allow_fn(ven, same) - {c}, cost, costD, both_vda=both_vda)
            w['without ' + c] = (r['worst'], r['low'], r['after1'])
        for fl in floors:
            r = run(allm_, cv_, allow_fn(ven, same, fl), cost, costD, both_vda=both_vda)
            w[f'floor {fl:,.0f}'] = (r['worst'], r['low'], r['after1'])
        return w

    def bars(r, w):
        return {'average month >= +1.5%': r['avg'] >= 0.015, 'no month below -4%': r['worst'] >= -0.04,
                'poorer account >= 40%': r['low'] >= 0.40, 'HAC t >= 2': r['t'] >= 2.0,
                'both years positive': r['y1'] > 0 and r['y2'] > 0,
                'list wobble holds': all(x >= -0.04 and lo >= 0.40 for x, lo, _ in w.values())}

    def row(tag, allm_, cv_, allow_fn, ven, same, cost, costD, floors, both_vda):
        allow = allow_fn(ven, same)
        if len(allow) < 10:
            print(f"{tag:3} {len(allow):5} coins: too few to run"); return None
        r = run(allm_, cv_, allow, cost, costD, both_vda=both_vda)
        r1 = run(allm_, cv_, allow, cost, costD, cost_mult=1.0, both_vda=both_vda)
        w = wobble(allm_, cv_, allow_fn, ven, same, cost, costD, floors, both_vda, r['per_coin'])
        b_ = bars(r, w)
        ok_ = all(b_.values())
        print(f"{tag:3} {len(allow):5} | {r['avg']:+8.2%} {r['t']:5.2f} {r['worst']:+7.2%} {r['neg']:>2}/24 {r['low']:6.1%} | "
              f"{r['after1']:+12.2%} {r['after2']:+6.2%} | {r1['avg']:+7.2%} {r1['after1']:+6.2%} {r1['after2']:+6.2%} | "
              f"{'PASS' if ok_ else 'fail: ' + ', '.join(k for k, v in b_.items() if not v)}")
        wv = [x for x, _, _ in w.values()]; lv = [lo for _, lo, _ in w.values()]; av = [a_ for _, _, a_ in w.values()]
        print(f"      wobble: worst month {min(wv):+.2%}, poorer account {min(lv):.1%}, after tax T1 {min(av):+.2%} to {max(av):+.2%}")
        OUT['pairs'][tag] = dict(coins=sorted(allow), cost=cost, avg=r['avg'], t=r['t'], worst=r['worst'], neg=r['neg'], low=r['low'],
                                 after1=r['after1'], after2=r['after2'], y1=r['y1'], y2=r['y2'], x1_avg=r1['avg'],
                                 x1_after1=r1['after1'], x1_after2=r1['after2'], bars=b_, passed=ok_,
                                 wobble={k: list(v) for k, v in w.items()})
        return OUT['pairs'][tag]

    print("\nTHE PAIRS (10 pairs x 10% a leg; costs x5 = the gate, x1 = the expected case)")
    print(f"{'':3} {'coins':>5} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} | {'after tax T1':>12} {'T2':>6} | "
          f"{'x1 pre':>7} {'x1 T1':>6} {'x1 T2':>6} | bars")
    cref = row('C', allm, cv, lst_d, dcx, same_bn, COST['coindcx'], None, (75000, 150000), False)
    if 'mudrex' in venues:
        row('M', allm_by, cv, lst_d, venues['mudrex']['coins'], same_by, COST['mudrex'], None, (75000, 150000), False)
    if 'coinswitch' in venues:
        row('S', allm_by, cv, lst_d, venues['coinswitch']['coins'], same_by, COST['coinswitch'], None, (75000, 150000), False)

    # CM / CS: CoinDCX (Binance's rent and closes, fractional sizing) + a Bybit-copy venue
    dcx_all = set(src.get('coindcx_inr') or [])
    byturn = src.get('bybit_turnover') or {}
    pool = sorted(c for c in dcx_all if c in hist['funding'] and (c in venues.get('mudrex', {}).get('coins', set())
                                                                  or c in venues.get('coinswitch', {}).get('coins', set())))
    if pool:
        fBn2, pBn2 = binance_mats(cache, D, pool)
        fBy2, pBy2 = bybit_mats(D, pool, hist)
        allm_cm = (D, pool, fBn2, fBy2, pBn2, pBy2)
        same_cm = same_asset(pBn2, pBy2, pool)
        cv2 = {c: TINY for c in pool}

        def lst_b(venue, same, floor=1e6):
            return {c for c in pool if byturn.get(c, 0) >= floor} & same & venue
        # engine check 2: legs_ab == legs on everything legs returns (CM's inputs)
        al = lst_b(venues.get('mudrex', venues.get('coinswitch', {})).get('coins', set()), same_cm)
        e1 = P.legs(*allm_cm, cv=cv2, cap=1000.0, allow=al, costB=COST['mudrex'], maxp=10, size=0.10, costD=COST['coindcx'])
        e2 = legs_ab(*allm_cm, cv=cv2, cap=1000.0, allow=al, costB=COST['mudrex'], maxp=10, size=0.10, costD=COST['coindcx'])
        chk2 = all(abs(e1[k] - e2[k]) < 1e-12 for k in ('net', 'pre', 'tax1', 'tax2'))
        print(f"engine check 2 (legs_ab == legs on CM's inputs): {'OK' if chk2 else 'MISMATCH'}")
        if not chk2:
            raise SystemExit(1)
        if 'mudrex' in venues:
            row('CM', allm_cm, cv2, lst_b, venues['mudrex']['coins'], same_cm, COST['mudrex'], COST['coindcx'], (5e5, 2e6), True)
        if 'coinswitch' in venues:
            row('CS', allm_cm, cv2, lst_b, venues['coinswitch']['coins'], same_cm, COST['coinswitch'], COST['coindcx'], (5e5, 2e6), True)
    print("   (after tax = per month on $1,000 over 24 months; T2 for M/S: the second leg a VDA; for CM/CS: both legs VDAs)")

    # the decision, as pre-registered
    bar1 = max(C_OCT8['after1'], cref['after1'] if cref else 0) + 0.005
    bar_x1 = max(C_OCT8['x1_after1'], cref['x1_after1'] if cref else 0)
    print(f"\nTHE DECISION: a new pair must pass every bar, reach T1 >= {bar1:+.2%} a month at costs x5 (C + 0.50%) and beat "
          f"{bar_x1:+.2%} at costs x1, be readable with a key from the server, and the operator must agree.")
    win = None
    for tag in ('M', 'S', 'CM', 'CS'):
        o = OUT['pairs'].get(tag)
        if not o:
            continue
        ven = 'mudrex' if tag in ('M', 'CM') else 'coinswitch'
        reasons = []
        if not o['passed']:
            reasons.append('fails a bar')
        if o['after1'] < bar1:
            reasons.append(f"T1 {o['after1']:+.2%} < {bar1:+.2%}")
        if o['x1_after1'] <= bar_x1:
            reasons.append(f"x1 T1 {o['x1_after1']:+.2%} <= {bar_x1:+.2%}")
        if not venues[ven]['confirmed']:
            reasons.append('its keyed read has not worked yet')
        print(f"  {tag}: " + ('QUALIFIES (subject to the operator)' if not reasons else 'stays out: ' + '; '.join(reasons)))
        if not reasons and (win is None or o['after1'] > OUT['pairs'][win]['after1']):
            win = tag
    OUT['winner'] = win
    print(f"  => {'the plan may move to ' + win + ' (the operator decides)' if win else 'Delta + CoinDCX stays the plan'}")

    # information only: how wide each gap is on coins all three venues list
    tri = sorted(set(names) & dcx & venues.get('mudrex', {}).get('coins', set()))
    if tri:
        jj = [names.index(c) for c in tri]
        def s7(fa, fb):
            sp = (fa - fb)[:, jj]
            out = np.full_like(sp, np.nan)
            for i in range(X.WIN - 1, len(D)):
                blk = sp[i - X.WIN + 1:i + 1]
                n = (~np.isnan(blk)).sum(0)
                out[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
            return np.abs(out)
        g_db, g_dy, g_by = s7(allm[2], allm[3]), s7(allm[2], fBy), s7(allm[3], fBy)
        print(f"\nINFORMATION ONLY: the 7-day rent gap on the {len(tri)} coins all three venues list (median of days, %/yr):")
        for nm_, g in (('Delta vs Binance (C)', g_db), ('Delta vs Bybit (M)', g_dy), ('Binance vs Bybit (CM)', g_by)):
            v = g[~np.isnan(g)]
            print(f"  {nm_:24s} median {np.median(v):6.1%}  share of coin-days >= 20%/yr {np.mean(v >= 0.20):5.1%}")
    json.dump(OUT, open(os.path.join(HERE, 'c542b_pairs.json'), 'w'), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else float(o))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
