#!/usr/bin/env python3
"""Round 24 (pre-registered in research/r24_preregistration.md, pushed before this ran): hidden risks and profit in
the running plan -- Delta India + CoinDCX, 10 pairs x 10%, the daily 7-day rule.

    C524_MARK=1 python3 research/r24_round24.py XV_CACHE [MINUTE_CACHE]

A. the 10-11 Oct 2025 crash (and the base plan's 5 worst days for the poorer account), minute by minute, on Delta's
   and Binance's 1-minute MARK prices: each account's lowest point, and what cross / isolated margin would have done;
B. a swap rule (S40, S80): when every slot is full, swap the weakest held pair for a waiting one whose gap beats it by
   >= 40 / 80 %/yr (one a day);
C. a cap on one-sidedness (K7, K6): at most K of the held pairs facing the same way;
D. is the edge fading? the widest gaps and the plan's monthly net over the 24 months.
Engine: Round 22's `legs` (profit, tax) and Round 21's `sides` (each account, the 65% even-out), copied here with the
two rules as switches; switched off they must reproduce the originals exactly.
"""
import os, sys, io, json, math, time, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C
import c542_pairs as P

TAX = P.TAX
COSTB = P.COST['coindcx']
MAINT = 0.005                      # maintenance margin taken for liquidation (see the report for the sensitivity)


# ── the selection rules ──────────────────────────────────────────────────────
def _enter(i, cand, held, room, capK, sizer):
    """the base rule's entries (widest first), skipping a candidate that would break the cap; returns entered js"""
    out = []
    cnt = {1: sum(1 for s in held.values() if s > 0), -1: sum(1 for s in held.values() if s < 0)}
    for j, d in cand:
        if room <= 0:
            break
        if capK is not None and cnt[d] >= capK:
            continue
        if not sizer(j):
            continue
        held[j] = d
        cnt[d] += 1
        out.append(j)
        room -= 1
    return out


def _swap(sig, cand, held, maxp, delta, capK, feasible):
    """at most one swap a day: (weakest held, candidate) or None"""
    if delta is None or len(held) < maxp or not held:
        return None
    w = min(held, key=lambda j: abs(sig[j]))
    for j, d in cand:
        if j in held:
            continue
        if abs(sig[j]) - abs(sig[w]) < delta:
            return None                                      # sorted widest first: no later one can beat it
        if capK is not None:
            n_d = sum(1 for s in held.values() if s == d) - (1 if held[w] == d else 0)
            if n_d >= capK:
                continue
        if not feasible(j):
            continue
        return w, j
    return None


def _s7(D, names, fD, fB, allow):
    am = np.array([n in allow for n in names])
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(D)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    s7[:, ~am] = np.nan
    return s7, am


def legs2(D, names, fD, fB, pD, pB, cv, cap, allow, costB, maxp=10, size=0.10, cost_mult=5.0, costD=None, gst=C.GST,
          swap=None, capK=None):
    """Round 22's legs, with the swap and the cap as switches"""
    costD = X.COST_D if costD is None else costD
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    s7, am = _s7(D, names, fD, fB, allow)
    ok &= am[None, :]
    cB, cD = costB * cost_mult, costD * cost_mult
    held, size_ = {}, {}
    pnl = np.zeros(len(D)); entered = swaps = 0
    live = np.arange(len(D)) >= X.WIN
    fyD, fyB, legB, closedB = {}, {}, {}, []
    pc = np.zeros(k)

    def book(i1, j, d_, b_):
        if not live[i1]:
            return
        y = P.fy_of(D[i1])
        fyD[y] = fyD.get(y, 0.0) + d_; fyB[y] = fyB.get(y, 0.0) + b_
        legB[j] = legB.get(j, 0.0) + b_
        pc[j] += d_ + b_

    def close(i, j):
        pnl[i + 1] -= size_[j] * (cB + cD)
        book(i + 1, j, -size_[j] * cD, -size_[j] * cB)
        closedB.append(legB.pop(j, 0.0))
        del held[j], size_[j]

    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                close(i, j)
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        cand = [(j, int(np.sign(sig[j]))) for j in cand]

        def sizer(j, i=i, dry=False):
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            kq = int(round(size * cap / (c_ * px)))
            if kq < 1:
                return False
            if dry:
                return True
            sz = kq * c_ * px / cap
            size_[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            legB[j] = 0.0
            book(i + 1, j, -sz * cD, -sz * cB)
            return True
        entered += len(_enter(i, cand, held, maxp - len(held), capK, sizer))
        sw = _swap(sig, cand, held, maxp, swap, capK, lambda j: sizer(j, dry=True))
        if sw:
            w, j = sw
            close(i, w)
            sizer(j)
            held[j] = int(np.sign(sig[j]))
            swaps += 1; entered += 1
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
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, swaps=swaps,
                pre=float(x.sum()), tax1=float(t1), tax2=float(t2), daily=x, days=Dl,
                per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def sides2(allm, cap, cv, trigger=0.65, cost_mult=5.0, allow=None, costB=COSTB, maxp=10, size=0.10, swap=None, capK=None,
           record=None):
    """Round 21's sides (each account; monthly re-balance and the 65% even-out), with the swap and the cap; `record` =
    a set of day timestamps whose book (held pairs, sizes, sides) and account values are kept"""
    Dd, names, fD, fB, pD, pB = allm
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    s7, _am = _s7(Dd, names, fD, fB, allow if allow is not None else set(names))
    cB, cD = costB * cost_mult, X.COST_D * cost_mult
    held, size_ = {}, {}
    sd, sb = cap / 2.0, cap / 2.0
    cur, pend, transfers, low, lows_m = None, False, 0, 1.0, {}
    daily_low, daily_drop, books, swaps, oneway = {}, {}, {}, 0, []
    for i in range(len(Dd) - 1):
        m = dt.datetime.utcfromtimestamp(int(Dd[i + 1])).strftime('%Y-%m')
        tot = sd + sb
        if i + 1 >= X.WIN and (m != cur or pend):
            if pend:
                transfers += 1
                tot -= 1.0
            sd = sb = tot / 2.0
            cur, pend = m, False
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                sb -= size_[j] * cB; sd -= size_[j] * cD
                del held[j], size_[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        cand = [(j, int(np.sign(sig[j]))) for j in cand]
        eqn = sd + sb

        def sizer(j, i=i, dry=False):
            nonlocal sd, sb
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            kq = int(round(size * eqn / (c_ * px)))
            if kq < 1:
                return False
            if dry:
                return True
            size_[j] = kq * c_ * px
            sb -= size_[j] * cB; sd -= size_[j] * cD
            return True
        _enter(i, cand, held, maxp - len(held), capK, sizer)
        sw = _swap(sig, cand, held, maxp, swap, capK, lambda j: sizer(j, dry=True))
        if sw:
            w, j = sw
            sb -= size_[w] * cB; sd -= size_[w] * cD
            del held[w], size_[w]
            sizer(j)
            held[j] = int(np.sign(sig[j]))
            swaps += 1
        if held:
            oneway.append(max(sum(1 for s in held.values() if s > 0), sum(1 for s in held.values() if s < 0)) / len(held))
        if record is not None and int(Dd[i + 1]) in record:
            books[int(Dd[i + 1])] = dict(sd=sd, sb=sb, half=(sd + sb) / 2.0,
                                         legs=[dict(coin=names[j], side=s, size=size_[j]) for j, s in held.items()])
        sd_b, sb_b = sd, sb
        for j, side in held.items():
            if ok[i + 1, j]:
                sb += size_[j] * side * (rB[i + 1, j] - fB[i + 1, j])
                sd += size_[j] * side * (fD[i + 1, j] - rD[i + 1, j])
        if i + 1 >= X.WIN and sd_b > 0 and sb_b > 0:
            daily_drop[int(Dd[i + 1])] = min(sd / sd_b, sb / sb_b) - 1
        if i + 1 >= X.WIN:
            half = (sd + sb) / 2.0
            f = min(sd, sb) / half if half > 0 else 0.0
            low = min(low, min(sd, sb) / (cap / 2.0))
            lows_m[m] = min(lows_m.get(m, 9.0), f)
            daily_low[int(Dd[i + 1])] = f
            if trigger is not None and f < trigger:
                pend = True
    lm = np.array(list(lows_m.values()))
    yrs = (Dd[-1] - Dd[X.WIN]) / 86400 / 365
    return dict(end=(sd + sb) / cap, low_side=float(low), months_lt65=float((lm < 0.65).mean()),
                months_lt50=float((lm < 0.50).mean()), worst_month_side=float(lm.min()), transfers_yr=transfers / yrs,
                daily_low=daily_low, daily_drop=daily_drop, books=books, swaps=swaps, oneway=float(np.mean(oneway)) if oneway else float('nan'))


def run2(allm, cv, allow, cost=COSTB, maxp=10, size=0.10, cost_mult=5.0, swap=None, capK=None, with_sides=True):
    r = legs2(*allm, cv=cv, cap=1000.0, allow=allow, costB=cost, maxp=maxp, size=size, cost_mult=cost_mult,
              swap=swap, capK=capK)
    ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
    nm = len(mv)
    r.update(mv=mv, avg=float(mv.mean()), worst=float(mv.min()), neg=int((mv < 0).sum()),
             after1=(r['pre'] - r['tax1']) / nm, after2=(r['pre'] - r['tax2']) / nm,
             y1=sum(v for k, v in r['months'].items() if '2024-10' <= k <= '2025-09'),
             y2=sum(v for k, v in r['months'].items() if '2025-10' <= k <= '2026-09'))
    if with_sides:
        sd = sides2(allm, 1000.0, cv, trigger=0.65, allow=allow, cost_mult=cost_mult, costB=cost, maxp=maxp, size=size,
                    swap=swap, capK=capK)
        r['low'] = sd['low_side']; r['transfers_yr'] = sd['transfers_yr']; r['oneway'] = sd['oneway']
        r['months_lt50'] = sd['months_lt50']
    return r


# ── A: minute marks ──────────────────────────────────────────────────────────
def _get(url, params, tries=4):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1.5 * (k + 1))
    return None


def delta_1m(sym, t0, t1, mcache):
    f = os.path.join(mcache, f"d1m_{sym}_{t0}.json")
    if os.path.exists(f):
        return json.load(open(f))
    out = {}
    t = t0
    while t < t1:
        r = (_get(X.DELTA + '/v2/history/candles', dict(resolution='1m', symbol='MARK:' + sym, start=t, end=min(t1, t + 6 * 3600))) or {}).get('result') or []
        for x in r:
            out[int(x['time'])] = (float(x['high']), float(x['low']), float(x['close']))
        t += 6 * 3600
    out = {str(k): v for k, v in sorted(out.items())}
    json.dump(out, open(f, 'w'))
    return out


def bn_1m(sym, t0, t1, mcache):
    f = os.path.join(mcache, f"b1m_{sym}_{t0}.json")
    if os.path.exists(f):
        return json.load(open(f))
    out = {}
    t = t0 * 1000
    while t < t1 * 1000:
        r = _get(X.BN + '/fapi/v1/markPriceKlines', dict(symbol=sym, interval='1m', startTime=t, endTime=t1 * 1000 - 1, limit=1500)) or []
        if not r:
            break
        for x in r:
            out[int(x[0]) // 1000] = (float(x[2]), float(x[3]), float(x[4]))
        if len(r) < 1500:
            break
        t = int(r[-1][0]) + 60000
    out = {str(k): v for k, v in sorted(out.items())}
    json.dump(out, open(f, 'w'))
    return out


def minute_day(book, day0, prods, mcache):
    """each account's value through one day (00:30 UTC -> 00:30 UTC) from the legs' 1-minute marks; the worst case in
    each minute takes each leg's adverse extreme (a long's low, a short's high)"""
    t0, t1 = day0 + 1800, day0 + 86400 + 1800
    legs = []
    for L in book['legs']:
        c = L['coin']
        dm = delta_1m(prods[c]['sym'], t0, t1, mcache)
        bm = bn_1m(c + 'USDT', t0, t1, mcache)
        if not dm or not bm:
            legs.append(dict(L, missing=True))
            continue
        legs.append(dict(L, d=dm, b=bm))
    minutes = range(t0, t1, 60)
    sd0, sb0 = book['sd'], book['sb']
    path_d, path_b = [], []
    worst_leg = {}
    iso = {1 / 3: set(), 1 / 2: set()}
    for t in minutes:
        vd, vb = sd0, sb0
        for L in legs:
            if L.get('missing'):
                continue
            ks = str(t)
            dref = L['d'].get(str(t0)) or next(iter(L['d'].values()))
            bref = L['b'].get(str(t0)) or next(iter(L['b'].values()))
            dh, dl, _ = L['d'].get(ks, (None, None, None))
            bh, bl, _ = L['b'].get(ks, (None, None, None))
            if dh is None or bh is None:
                continue
            s, n = L['side'], L['size']
            # Delta leg: short when side=+1 (loses when the price rises) -> its adverse extreme is the high
            d_adv = (dh if s > 0 else dl) / dref[2] - 1
            b_adv = (bl if s > 0 else bh) / bref[2] - 1
            vd += -s * n * d_adv
            vb += s * n * b_adv
            for m_ in iso:
                if (-s * d_adv) <= -(m_ - MAINT):
                    iso[m_].add((L['coin'], 'Delta'))
                if (s * b_adv) <= -(m_ - MAINT):
                    iso[m_].add((L['coin'], 'CoinDCX'))
            worst_leg[(L['coin'], 'Delta')] = min(worst_leg.get((L['coin'], 'Delta'), 0.0), -s * d_adv)
            worst_leg[(L['coin'], 'CoinDCX')] = min(worst_leg.get((L['coin'], 'CoinDCX'), 0.0), s * b_adv)
        path_d.append(vd); path_b.append(vb)
    pd_, pb_ = np.array(path_d), np.array(path_b)
    nd = sum(L['size'] for L in book['legs'])
    out = dict(day=dt.datetime.utcfromtimestamp(day0).strftime('%Y-%m-%d'), sd0=sd0, sb0=sb0,
               n_legs=len(book['legs']), missing=[L['coin'] for L in legs if L.get('missing')],
               short_delta=sum(1 for L in book['legs'] if L['side'] > 0),
               low_d=float(pd_.min() / sd0), low_b=float(pb_.min() / sb0),
               when_d=dt.datetime.utcfromtimestamp(t0 + 60 * int(pd_.argmin())).strftime('%H:%M UTC'),
               when_b=dt.datetime.utcfromtimestamp(t0 + 60 * int(pb_.argmin())).strftime('%H:%M UTC'),
               cross_wiped_d=bool(pd_.min() <= MAINT * nd), cross_wiped_b=bool(pb_.min() <= MAINT * nd),
               iso_third=sorted(f"{c} on {v}" for c, v in iso[1 / 3]), iso_half=sorted(f"{c} on {v}" for c, v in iso[1 / 2]),
               worst_legs=sorted(((f"{c} on {v}", round(100 * x, 1)) for (c, v), x in worst_leg.items()), key=lambda z: z[1])[:5])
    return out


def main(cache, mcache):
    t_start = time.time()
    os.makedirs(mcache, exist_ok=True)
    print("ROUND 24: HIDDEN RISKS AND PROFIT IN THE RUNNING PLAN (pre-registered: research/r24_preregistration.md)\n")
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

    def lst(floor=100000):
        return {c for c in prods if turn.get(c, 0) >= floor} & same & dcx
    allow = lst()
    print(f"Delta turnover read {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC: {len(allow)} coins (Delta + CoinDCX, >= $100k a "
          f"day on Delta, the same asset); 2024-10-01 -> 2026-09-30\n")
    OUT = dict(coins=len(allow))

    # engine check
    a = P.legs(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB, maxp=10, size=0.10)
    b = legs2(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB)
    old = X.COST_B, X.MAXP, X.SIZE
    try:
        X.COST_B, X.MAXP, X.SIZE = COSTB, 10, 0.10
        sa = S.sides(allm, 1000.0, cv, trigger=0.65, allow=allow, cost_mult=5.0)
    finally:
        X.COST_B, X.MAXP, X.SIZE = old
    sb_ = sides2(allm, 1000.0, cv, allow=allow)
    chk = abs(a['net'] - b['net']) < 1e-12 and abs(sa['low_side'] - sb_['low_side']) < 1e-12 \
        and abs(sa['transfers_yr'] - sb_['transfers_yr']) < 1e-12
    print(f"engine check (switches off == Round 22's legs and Round 21's sides): {'OK' if chk else 'MISMATCH'} "
          f"(net {a['net']:.6f} / {b['net']:.6f}; lowest account {sa['low_side']:.6f} / {sb_['low_side']:.6f})\n")
    OUT['engine_check'] = bool(chk)
    if not chk:
        json.dump(OUT, open(os.path.join(HERE, 'r24_round24.json'), 'w'), indent=1, default=float)
        raise SystemExit(1)

    # base and the variants
    def wobble(r, **kw):
        top = [c for c, _ in sorted(r['per_coin'].items(), key=lambda kv: -kv[1])[:5]]
        res_ = {}
        for c in top:
            x = run2(allm, cv, allow - {c}, **kw)
            res_['without ' + c] = (x['worst'], x['low'], x['after1'])
        for fl in (75000, 150000):
            x = run2(allm, cv, lst(fl), **kw)
            res_[f'floor ${fl // 1000}k'] = (x['worst'], x['low'], x['after1'])
        return res_

    def partA(r, wob):
        return {'average month >= +1.5%': r['avg'] >= 0.015, 'no month below -4%': r['worst'] >= -0.04,
                'poorer account >= 40%': r['low'] >= 0.40, 'HAC t >= 2': r['t'] >= 2.0,
                'both years positive': r['y1'] > 0 and r['y2'] > 0,
                'list wobble holds': all(w >= -0.04 and lo >= 0.40 for w, lo, _ in wob.values())}

    def halves(x, days):
        hs = {}
        for d_, v in zip(days, x):
            dd = dt.datetime.utcfromtimestamp(int(d_))
            h = f"{dd.year}{'H1' if dd.month <= 6 else 'H2'}"
            hs[h] = hs.get(h, 0.0) + v
        return hs

    V = {'base': {}, 'S40': dict(swap=0.40), 'S80': dict(swap=0.80), 'K7': dict(capK=7), 'K6': dict(capK=6)}
    R, R1, W = {}, {}, {}
    print("B and C: THE VARIANTS (10 pairs x 10%, costs x5 = the bar; x1 = the expected case)")
    print(f"{'':5} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} {'xfer/yr':>7} {'one-way':>7} | "
          f"{'after T1':>8} {'$/yr vs base':>12} | {'x1 T1':>6} | swaps/yr")
    for v, kw in V.items():
        R[v] = run2(allm, cv, allow, **kw)
        R1[v] = run2(allm, cv, allow, cost_mult=1.0, with_sides=False, **kw)
        W[v] = wobble(R[v], **kw)
    for v in V:
        r = R[v]
        gain = (r['after1'] - R['base']['after1']) * 12 * 1000
        yrs = len(r['daily']) / 365
        print(f"{v:5} | {100 * r['avg']:+7.2f}% {r['t']:5.2f} {100 * r['worst']:+6.2f}% {r['neg']:2d}/24 {100 * r['low']:5.1f}% "
              f"{r['transfers_yr']:7.1f} {100 * r['oneway']:6.0f}% | {100 * r['after1']:+7.2f}% {gain:+12.0f} | "
              f"{100 * R1[v]['after1']:+5.2f}% | {r['swaps'] / yrs:5.1f}")
    print("   (one-way = the average share of held pairs facing the same way; after tax per month on $1,000; 24 months)\n")

    verdict = {}
    for v in ('S40', 'S80'):
        r, b0 = R[v], R['base']
        diff = r['daily'] - b0['daily']
        hs = halves(diff, r['days'])
        bars = partA(r, W[v])
        bars.update({'>= $50 a year more after tax': (r['after1'] - b0['after1']) * 12000 >= 50,
                     'at most one more losing month': r['neg'] <= b0['neg'] + 1,
                     'daily difference HAC t >= 2.5': X.hac_t(diff) >= 2.5,
                     'ahead in >= 3 of 4 half-years': sum(1 for x in hs.values() if x > 0) >= 3,
                     'ahead at costs x1 too': R1[v]['after1'] > R1['base']['after1']})
        verdict[v] = dict(bars=bars, passed=all(bars.values()), diff_t=float(X.hac_t(diff)), halves=hs)
        print(f"{v}: {'PASS' if all(bars.values()) else 'fail: ' + ', '.join(k for k, ok in bars.items() if not ok)}"
              f" (difference HAC t {X.hac_t(diff):.2f}; half-years " + ', '.join(f"{k} {1000 * x:+.1f}$" for k, x in hs.items()) + ")")
    OUT['A_pending'] = True

    # A: the crash day and the 5 worst days, minute by minute
    crash = int(dt.datetime(2025, 10, 10, tzinfo=dt.timezone.utc).timestamp())
    base_s = sides2(allm, 1000.0, cv, allow=allow, record=None)
    worst5 = sorted(base_s['daily_drop'].items(), key=lambda kv: kv[1])     # the largest one-day fall of either account
    days = [crash]
    for d_, f in worst5:
        if len(days) >= 6:
            break
        if all(abs(d_ - x) > 3 * 86400 for x in days):
            days.append(d_)
    recs = {}
    for v in ('base', 'K7', 'K6'):
        recs[v] = sides2(allm, 1000.0, cv, allow=allow, record=set(days), **V[v])['books']
    print("\nA. MINUTE BY MINUTE (1-minute MARK prices; each leg at its worst extreme each minute; start = 00:30 UTC)")
    print(f"{'day':10} {'rule':4} {'legs':>4} {'short Delta':>11} | {'Delta low':>9} {'at':>9} | {'CoinDCX low':>11} {'at':>9} | "
          f"cross wiped? | isolated 1/3 liquidated | isolated 1/2 liquidated")
    A = {}
    for d_ in days:
        for v in ('base', 'K7', 'K6'):
            bk = recs[v].get(d_)
            if not bk:
                continue
            m = minute_day(bk, d_ - 86400 * 0, prods, mcache)
            A[f"{m['day']} {v}"] = m
            print(f"{m['day']:10} {v:4} {m['n_legs']:4d} {m['short_delta']:11d} | {100 * m['low_d']:8.1f}% {m['when_d']:>9} | "
                  f"{100 * m['low_b']:10.1f}% {m['when_b']:>9} | {('Delta ' if m['cross_wiped_d'] else '') + ('CoinDCX' if m['cross_wiped_b'] else '') or 'no':>12} | "
                  f"{len(m['iso_third']):2d} {', '.join(m['iso_third'][:4])} | {len(m['iso_half']):2d} {', '.join(m['iso_half'][:3])}")
            if v == 'base':
                print(f"{'':16} worst legs: " + ', '.join(f"{a_} {b_:+.1f}%" for a_, b_ in m['worst_legs']) +
                      (f"; no minute data: {', '.join(m['missing'])}" if m['missing'] else ''))
    OUT['A'] = A

    # C's bar needs A: the crash replay no worse for either account
    for v in ('K7', 'K6'):
        r, b0 = R[v], R['base']
        bars = partA(r, W[v])
        cr_b, cr_v = A.get(dt.datetime.utcfromtimestamp(crash).strftime('%Y-%m-%d') + ' base'), \
            A.get(dt.datetime.utcfromtimestamp(crash).strftime('%Y-%m-%d') + ' ' + v)
        bars.update({'safer (poorer account +5 points, or transfers -30%)':
                     (r['low'] - b0['low'] >= 0.05) or (r['transfers_yr'] <= 0.7 * b0['transfers_yr']),
                     'crash replay no worse for either account':
                     bool(cr_b and cr_v and cr_v['low_d'] >= cr_b['low_d'] - 1e-9 and cr_v['low_b'] >= cr_b['low_b'] - 1e-9),
                     'costs at most $30 a year after tax': (r['after1'] - b0['after1']) * 12000 >= -30})
        verdict[v] = dict(bars=bars, passed=all(bars.values()))
        print(f"\n{v}: {'PASS' if all(bars.values()) else 'fail: ' + ', '.join(k for k, ok in bars.items() if not ok)}")
    OUT['verdict'] = verdict

    # D: is the edge fading?
    Dd, names, fD, fB = allm[0], allm[1], allm[2], allm[3]
    s7, am = _s7(Dd, names, fD, fB, allow)
    mon, top10 = {}, {}
    for i in range(X.WIN, len(Dd)):
        m = dt.datetime.utcfromtimestamp(int(Dd[i])).strftime('%Y-%m')
        row = np.abs(s7[i][~np.isnan(s7[i])])
        if len(row) >= 10:
            top10.setdefault(m, []).append(float(np.sort(row)[-10:].mean()))
    for k_, v_ in R['base']['months'].items():
        mon[k_] = v_
    ks = sorted(set(top10) & set(mon))
    g = np.array([np.mean(top10[k_]) for k_ in ks]); n_ = np.array([mon[k_] for k_ in ks])
    tt = np.arange(len(ks)) / 12.0

    def slope(y):
        A_ = np.vstack([tt, np.ones_like(tt)]).T
        beta = np.linalg.lstsq(A_, y, rcond=None)[0]
        e = y - A_ @ beta
        # HAC t of the slope (Newey-West, 3 lags) on the monthly series
        xc = tt - tt.mean(); s = (xc ** 2 * e ** 2).sum()
        for l in range(1, 4):
            s += 2 * (1 - l / 4) * (xc[l:] * e[l:] * xc[:-l] * e[:-l]).sum()
        se = math.sqrt(s) / (xc ** 2).sum()
        return float(beta[0]), float(beta[0] / se) if se > 0 else float('nan')
    sg, tg = slope(g); sn, tn = slope(n_)
    print("\nD. IS THE EDGE FADING? (monthly)")
    print("   month    widest-10 gap   plan's net (costs x5)")
    for k_, a_, b_ in zip(ks, g, n_):
        print(f"   {k_}   {100 * a_:7.0f}%/yr      {100 * b_:+6.2f}%")
    print(f"   trend: widest-10 gap {100 * sg:+.0f} points a year (HAC t {tg:.2f}); plan's net {100 * sn:+.2f} points a year "
          f"(HAC t {tn:.2f})")
    print(f"   first 18 months vs last 6: gap {100 * g[:18].mean():.0f}% -> {100 * g[-6:].mean():.0f}%/yr; plan's net "
          f"{100 * n_[:18].mean():+.2f}% -> {100 * n_[-6:].mean():+.2f}% a month")
    OUT['D'] = dict(months=ks, gap=g.tolist(), net=n_.tolist(), gap_slope=sg, gap_t=tg, net_slope=sn, net_t=tn,
                    gap_first18=float(g[:18].mean()), gap_last6=float(g[-6:].mean()),
                    net_first18=float(n_[:18].mean()), net_last6=float(n_[-6:].mean()))
    OUT['R'] = {v: dict(avg=R[v]['avg'], t=R[v]['t'], worst=R[v]['worst'], neg=R[v]['neg'], low=R[v]['low'],
                        transfers_yr=R[v]['transfers_yr'], oneway=R[v]['oneway'], after1=R[v]['after1'],
                        after2=R[v]['after2'], x1_after1=R1[v]['after1'], swaps=R[v]['swaps'],
                        wobble={k: dict(worst=a_, low=lo, after1=af) for k, (a_, lo, af) in W[v].items()})
                for v in V}
    OUT.pop('A_pending', None)
    json.dump(OUT, open(os.path.join(HERE, 'r24_round24.json'), 'w'), indent=1, default=float)
    print(f"\n[{time.time() - t_start:.0f}s]")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(sys.argv[1], 'minutes'))
