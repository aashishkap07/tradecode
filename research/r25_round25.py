#!/usr/bin/env python3
"""Round 25 (pre-registered in research/r25_preregistration.md, pushed before this ran): the plan with CoinDCX's legs on
ISOLATED margin. CoinDCX's rupee (INR) futures offer no cross margin (the operator's app, 20 Nov 2026: "Cross margin mode
is currently only available in USDT margin Futures"); Delta India stays on cross.

    C524_MARK=1 python3 research/r25_round25.py XV_CACHE MINUTE_CACHE HL_CACHE

Variants (10 x 10%, the K6 cap; only CoinDCX's margin changes): I2 (each leg posts 1/2 of its size, no top-ups), I3T and
I5T (1/3 and 1/5, topped up from the free balance), against the cross reference (run3; XQ = cross booked at constant
quantity). The 24 months on daily mark highs/lows (top-ups assumed in time), Round 23's 46 days minute by minute (top-ups
one minute late; a liquidated leg's twin closed at the next minute's close). Engine: Round 23's legs3/sides3 copied as
legs5/sides5; with the switch at cross (and Round 23's booking) they must reproduce legs3/sides3 exactly.
"""
import os, sys, io, json, time, contextlib, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C
import c542_pairs as P
import r24_round24 as R
import r23_round23 as T

TAX, COSTB, MAINT, SLIP, K6, DAY = P.TAX, R.COSTB, R.MAINT, T.SLIP, T.K6, 86400
DCX_ONE = 'https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument'
VARIANTS = {'I2': dict(L=2.0, topup=False), 'I3T': dict(L=3.0, topup=True), 'I5T': dict(L=5.0, topup=True)}


# ── CoinDCX's own rules (rupee-margined), read once ──────────────────────────
def dcx_rules(coins, path):
    out = {}
    for c in sorted(coins):
        r = R._get(DCX_ONE, dict(pair=f'B-{c}_USDT', margin_currency_short_name='INR'), tries=3) or {}
        i = r.get('instrument', r) if isinstance(r, dict) else {}
        if isinstance(i, dict) and i.get('quantity_increment') is not None:
            tiers = sorted((float(k), float(v)) for k, v in (i.get('dynamic_safety_margin_details') or {}).items())
            mmr = (tiers[0][1] / 100.0) if tiers else 0.015
            out[c] = dict(listed=True, mmr=mmr, fee=float(i.get('liquidation_fee') or 1.5) / 100.0,
                          maxlev=min(float(i.get('max_leverage_long') or 5), float(i.get('max_leverage_short') or 5)),
                          status=str(i.get('status') or ''))
        else:
            out[c] = dict(listed=False, mmr=0.015, fee=0.015, maxlev=5.0, status='not listed')
    json.dump(dict(read=f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC", rules=out), open(path, 'w'), indent=1)
    return out


# ── the accounts: Round 23's sides3, with CoinDCX's margin mode and constant-quantity booking ──────────────
def sides5(allm, cap, cv, trigger=0.65, cost_mult=5.0, allow=None, costB=COSTB, maxp=10, size=0.10, capK=K6,
           iso=None, qbook=False, hl=None, rules=None, record=None, rec_pairs=None):
    """iso None + qbook False == T.sides3 (the engine check). iso = dict(L, topup): CoinDCX legs on isolated margin.
    Returns sides3's measures plus: liquidations [(i1, coin, frac_d, frac_b)], skipped entries {(i1, j)}, books on the
    recorded days (each leg's quantities, entry prices and posted margin), and per-pair day results on rec_pairs days"""
    Dd, names, fD, fB, pD, pB = allm
    hD, lD, hB, lB = hl if hl is not None else (None,) * 4
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    s7, _am = R._s7(Dd, names, fD, fB, allow if allow is not None else set(names))
    cB, cD = costB * cost_mult, X.COST_D * cost_mult
    held, size_, st = {}, {}, {}
    sd, sb = cap / 2.0, cap / 2.0
    cur, pend, transfers, low, lows_m = None, False, 0, 1.0, {}
    daily_low, books, liqs, skipped, dayres = {}, {}, [], set(), {}
    topups = 0.0
    low_free = 1.0
    nheld = []

    def eq_b(j, px):
        """a CoinDCX leg's equity (posted margin + price result since entry) at price px (a missing price: its last)"""
        z = st[j]
        if not np.isfinite(px):
            px = z.get('last', z['p0b'])
        return z['m'] + held[j] * z['qb'] * (px - z['p0b'])

    def free_b(i):
        return sb - sum(eq_b(j, pB[i, j]) for j in held) if iso is not None else sb

    for i in range(len(Dd) - 1):
        m = dt.datetime.utcfromtimestamp(int(Dd[i + 1])).strftime('%Y-%m')
        tot = sd + sb
        if i + 1 >= X.WIN and (m != cur or pend):
            if pend:
                transfers += 1
                tot -= 1.0
            if iso is None:
                sd = sb = tot / 2.0
            else:
                # money can leave CoinDCX only from its free balance
                want_b = tot / 2.0
                fee = (sd + sb) - tot
                if sb - fee / 2.0 > want_b:
                    send = min(sb - fee / 2.0 - want_b, max(0.0, free_b(i) - fee / 2.0))
                    sb, sd = sb - fee / 2.0 - send, sd - fee / 2.0 + send
                else:
                    sd, sb = tot - want_b, want_b
            cur, pend = m, False
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                sb -= size_[j] * cB; sd -= size_[j] * cD
                del held[j], size_[j]
                st.pop(j, None)
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        cand = [(j, int(np.sign(sig[j]))) for j in cand]
        eqn = sd + sb

        def sizer(j, i=i):
            nonlocal sd, sb
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            kq = int(round(size * eqn / (c_ * px)))
            if kq < 1:
                return False
            sz = kq * c_ * px
            if iso is not None:
                Lj = min(iso['L'], (rules.get(names[j]) or {}).get('maxlev', 5.0))
                if free_b(i) < sz / Lj + sz * cB:
                    skipped.add((i + 1, j))
                    return False
            size_[j] = sz
            sb -= sz * cB; sd -= sz * cD
            if qbook or iso is not None:
                pb0 = pB[i, j] if not np.isnan(pB[i, j]) else pB[i + 1, j]
                st[j] = dict(qd=kq * c_, p0d=px, qb=sz / pb0, p0b=pb0, m=0.0, u=0.0, L=None)
                if iso is not None:
                    st[j].update(m=sz / Lj, L=Lj)
            return True
        R._enter(i, cand, held, maxp - len(held), capK, sizer)
        if iso is not None and iso.get('topup'):                  # top-ups a leg no longer needs go back
            for j in held:
                z = st[j]
                if z['u'] > 0 and not np.isnan(pB[i, j]):
                    up = held[j] * z['qb'] * (pB[i, j] - z['p0b'])
                    r = max(0.0, min(z['u'], z['m'] + min(0.0, up) - z['qb'] * pB[i, j] / z['L']))
                    z['m'] -= r; z['u'] -= r
        if iso is not None:
            fb_ = free_b(i)
            if i + 1 >= X.WIN and sb > 0:
                low_free = min(low_free, fb_ / (cap / 2.0))
        if record is not None and int(Dd[i + 1]) in record:
            books[int(Dd[i + 1])] = dict(
                sd=sd, sb=sb, half=(sd + sb) / 2.0, free=(free_b(i) if iso is not None else None),
                legs=[dict(coin=names[j], side=s, size=size_[j], **({k_: st[j][k_] for k_ in ('qd', 'p0d', 'qb', 'p0b', 'm', 'u', 'L')}
                                                                  if j in st else {}),
                           eb0=(eq_b(j, pB[i, j]) if iso is not None else None),
                           pd_i=float(pD[i, j]), pb_i=float(pB[i, j]),
                           mmr=(rules.get(names[j]) or {}).get('mmr', 0.015) if rules else 0.015) for j, s in held.items()])
        # ── the day's moves ──
        liq_today = {}
        if iso is not None:
            need = {}
            for j, s in held.items():
                if not ok[i + 1, j]:
                    continue
                z = st[j]
                xb = (lB[i + 1, j] if s > 0 else hB[i + 1, j])
                if np.isnan(xb):
                    xb = pB[i + 1, j]
                z['x'] = xb
                if iso.get('topup'):
                    need[j] = max(0.0, z['qb'] * xb / z['L'] - eq_b(j, xb))
            if need and sum(need.values()) > 0:
                fr = max(0.0, free_b(i))
                f = min(1.0, fr / sum(need.values()))
                for j, nd in need.items():
                    a = nd * f
                    st[j]['m'] += a; st[j]['u'] += a
                    topups += a
            for j, s in held.items():
                if not ok[i + 1, j]:
                    continue
                z = st[j]
                mmr = (rules.get(names[j]) or {}).get('mmr', 0.015)
                xb = z['x']
                if eq_b(j, xb) <= mmr * z['qb'] * xb:
                    pl = ((z['p0b'] - z['m'] / z['qb']) / (1 - mmr)) if s > 0 else ((z['p0b'] + z['m'] / z['qb']) / (1 + mmr))
                    liq_today[j] = pl
        gone = []
        sd_b, sb_b = sd, sb
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            d0, b0 = sd, sb
            if j in liq_today:
                z = st[j]
                pl = liq_today[j]
                # CoinDCX: the leg's whole equity (posted margin incl. top-ups) is lost
                up_start = side * z['qb'] * (pB[i, j] - z['p0b'])
                sb -= z['m'] + up_start
                # the twin: the smaller of the move to the liquidation price and its own day's extreme, minus the slip
                mvb = abs(pl / pB[i, j] - 1)
                dx = (lD[i + 1, j] if side > 0 else hD[i + 1, j])
                mvd = abs(dx / pD[i, j] - 1) if not np.isnan(dx) else mvb
                g = z['qd'] * pD[i, j] * min(mvb, mvd) - SLIP * size_[j]
                sd += g
                tot_d = -side * z['qd'] * (pD[i, j] - z['p0d']) + g
                liqs.append((i + 1, names[j], tot_d / size_[j], -z['m'] / size_[j], side))
                gone.append(j)
            elif qbook or iso is not None:
                z = st[j]
                sb += side * z['qb'] * (pB[i + 1, j] - pB[i, j]) - side * fB[i + 1, j] * z['qb'] * pB[i, j]
                sd += -side * z['qd'] * (pD[i + 1, j] - pD[i, j]) + side * fD[i + 1, j] * z['qd'] * pD[i, j]
            else:
                sb += size_[j] * side * (rB[i + 1, j] - fB[i + 1, j])
                sd += size_[j] * side * (fD[i + 1, j] - rD[i + 1, j])
            if rec_pairs is not None and int(Dd[i + 1]) in rec_pairs:
                # the pair's day result without rent (for the calibration against the minute model)
                fund = 0.0
                if j not in liq_today and (qbook or iso is not None):
                    z = st[j]
                    fund = -side * fB[i + 1, j] * z['qb'] * pB[i, j] + side * fD[i + 1, j] * z['qd'] * pD[i, j]
                dayres[(int(Dd[i + 1]), names[j])] = dict(res=(sd - d0) + (sb - b0) - fund, liq=j in liq_today)
        for j in gone:
            sd -= size_[j] * cD                                  # Delta's exit; CoinDCX's fee is inside the margin lost
            if rec_pairs is not None and (int(Dd[i + 1]), names[j]) in dayres:
                dayres[(int(Dd[i + 1]), names[j])]['res'] -= size_[j] * cD
            del held[j], size_[j]
            st.pop(j, None)
        for j in held:
            if j in st and np.isfinite(pB[i + 1, j]):
                st[j]['last'] = pB[i + 1, j]
        if i + 1 >= X.WIN:
            nheld.append(len(held))
            half = (sd + sb) / 2.0
            f = min(sd, sb) / half if half > 0 else 0.0
            low = min(low, min(sd, sb) / (cap / 2.0))
            lows_m[m] = min(lows_m.get(m, 9.0), f)
            daily_low[int(Dd[i + 1])] = f
            if trigger is not None and f < trigger:
                pend = True
    lm = np.array(list(lows_m.values()))
    yrs = (Dd[-1] - Dd[X.WIN]) / 86400 / 365
    return dict(end=(sd + sb) / cap, low_side=float(low), months_lt50=float((lm < 0.50).mean()),
                transfers_yr=transfers / yrs, daily_low=daily_low, books=books, liqs=liqs, skipped=skipped,
                dayres=dayres, topups=topups, low_free=low_free, years=yrs,
                avg_held=float(np.mean(nheld)) if nheld else 0.0, skip_days=len({i1 for i1, _ in skipped}))


# ── profit and tax: Round 23's legs3, with sides5's liquidations and skipped entries applied ─────────────
def legs5(D, names, fD, fB, pD, pB, cv, cap, allow, costB, maxp=10, size=0.10, cost_mult=5.0, costD=None, gst=C.GST,
          capK=K6, liqs=None, skipped=None):
    """liqs None and skipped None == T.legs3 (the engine check)"""
    costD = X.COST_D if costD is None else costD
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    s7, am = R._s7(D, names, fD, fB, allow)
    ok &= am[None, :]
    cB, cD = costB * cost_mult, costD * cost_mult
    held, size_, cum = {}, {}, {}
    pnl = np.zeros(len(D)); entered = nliq = 0
    live = np.arange(len(D)) >= X.WIN
    fyD, fyB, legB, closedB = {}, {}, {}, []
    pc = np.zeros(k)
    LQ = {(i1, c): (fd_, fb_) for i1, c, fd_, fb_, _s in (liqs or [])}
    SK = skipped or set()

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
        cum.pop(j, None)

    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                close(i, j)
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        cand = [(j, int(np.sign(sig[j]))) for j in cand]

        def sizer(j, i=i):
            if (i + 1, j) in SK:
                return False
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            kq = int(round(size * cap / (c_ * px)))
            if kq < 1:
                return False
            sz = kq * c_ * px / cap
            size_[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            legB[j] = 0.0
            cum[j] = [0.0, 0.0]
            book(i + 1, j, -sz * cD, -sz * cB)
            return True
        entered += len(R._enter(i, cand, held, maxp - len(held), capK, sizer))
        gone = []
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            if (i + 1, names[j]) in LQ:
                fd_, fb_ = LQ[(i + 1, names[j])]
                d_ = size_[j] * fd_ - cum[j][0]                     # the pair's price result since entry, as liquidated
                b_ = size_[j] * fb_ - cum[j][1]
                pnl[i + 1] += d_ + b_
                book(i + 1, j, d_, b_)
                gone.append(j)
                continue
            fd_leg = side * fD[i + 1, j]
            fb_leg = -side * fB[i + 1, j]
            fd_leg = fd_leg * (1 + gst) if fd_leg < 0 else fd_leg
            fb_leg = fb_leg * (1 + gst) if fb_leg < 0 else fb_leg
            d_ = size_[j] * (fd_leg - side * rD[i + 1, j])
            b_ = size_[j] * (fb_leg + side * rB[i + 1, j])
            cum[j][0] += size_[j] * (-side * rD[i + 1, j])
            cum[j][1] += size_[j] * (side * rB[i + 1, j])
            pnl[i + 1] += d_ + b_
            book(i + 1, j, d_, b_)
        for j in gone:
            nliq += 1
            pnl[i + 1] -= size_[j] * cD                              # Delta's exit only
            book(i + 1, j, -size_[j] * cD, 0.0)
            closedB.append(legB.pop(j, 0.0))
            del held[j], size_[j]
            cum.pop(j, None)
    closedB += list(legB.values())
    x = pnl[live]; Dl = D[live]
    months = {}
    for d_, v in zip(Dl, x):
        mm = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        months[mm] = months.get(mm, 0.0) + v

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
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, liqs=nliq,
                pre=float(x.sum()), tax1=float(t1), tax2=float(t2), daily=x, days=Dl,
                per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def run5(allm, cv, allow, hl, rules, iso=None, qbook=False, cost=COSTB, cost_mult=5.0, with_sides=True):
    sd = sides5(allm, 1000.0, cv, trigger=0.65, allow=allow, cost_mult=cost_mult, costB=cost, iso=iso, qbook=qbook,
                hl=hl, rules=rules)
    r = legs5(*allm, cv=cv, cap=1000.0, allow=allow, costB=cost, cost_mult=cost_mult,
              liqs=sd['liqs'] if iso is not None else None, skipped=sd['skipped'] if iso is not None else None)
    ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
    nm = len(mv)
    r.update(mv=mv, avg=float(mv.mean()), worst=float(mv.min()), neg=int((mv < 0).sum()),
             after1=(r['pre'] - r['tax1']) / nm, after2=(r['pre'] - r['tax2']) / nm,
             y1=sum(v for k, v in r['months'].items() if '2024-10' <= k <= '2025-09'),
             y2=sum(v for k, v in r['months'].items() if '2025-10' <= k <= '2026-09'))
    r.update(low=sd['low_side'], transfers_yr=sd['transfers_yr'], liq_yr=len(sd['liqs']) / sd['years'],
             skipped_yr=sd['skip_days'] / sd['years'], topups=sd['topups'], low_free=sd['low_free'],
             liq_list=sd['liqs'], avg_held=sd['avg_held'], low_day=min(sd['daily_low'], key=sd['daily_low'].get))
    return r


# ── minute replays: CoinDCX isolated, top-ups one minute late, a liquidated leg's twin closed at the next close ──
def minute_day5(book, day0, prods, mcache, iso=None, qbook=True, cD=X.COST_D * 5.0):
    t0, t1 = day0 + 1800, day0 + 86400 + 1800
    legs = []
    for L in book['legs']:
        c = L['coin']
        dm = R.delta_1m(prods[c]['sym'], t0, t1, mcache)
        bm = R.bn_1m(c + 'USDT', t0, t1, mcache)
        legs.append(dict(L, missing=True) if (not dm or not bm) else dict(L, d=dm, b=bm, dead=None, eb=None))
    sd0, sb0 = book['sd'], book['sb']
    free = book.get('free') if iso is not None else None
    for L in legs:
        if L.get('missing'):
            continue
        L['dref'] = (L['d'].get(str(t0)) or next(iter(L['d'].values())))[2]
        L['bref'] = (L['b'].get(str(t0)) or next(iter(L['b'].values())))[2]
        if iso is not None:
            # its equity at the day's start, moved from the engine's daily mark to the minute data's first close
            L['eb'] = L['eb0'] + L['side'] * L['qb'] * (L['bref'] - L['pb_i'])
    pd_, pb_, liq, res = [], [], [], {}
    ts = list(range(t0, t1, 60))
    for n_, t in enumerate(ts):
        vd, vb = sd0, (free if iso is not None else sb0)
        for L in legs:
            if L.get('missing'):
                continue
            s = L['side']
            ks = str(t)
            dh, dl, dc = L['d'].get(ks, (None, None, None))
            bh, bl, bc = L['b'].get(ks, (None, None, None))
            nd_ = (L['qd'] * L['dref']) if qbook else L['size']
            nb_ = (L['qb'] * L['bref']) if qbook else L['size']
            if L['dead'] is not None:                              # liquidated: its twin closes at the next close
                if L['dead'][1] is None and dc is not None:
                    gd = -s * nd_ * (dc / L['dref'] - 1) - cD * L['size']
                    L['dead'] = (L['dead'][0], gd)
                vd += L['dead'][1] if L['dead'][1] is not None else (-s * nd_ * ((dh if s > 0 else dl) / L['dref'] - 1) if dh is not None else 0.0)
                continue
            if dh is None or bh is None:
                if iso is not None:
                    vb += L['eb']
                continue
            d_adv = (dh if s > 0 else dl) / L['dref'] - 1
            b_adv = (bl if s > 0 else bh) / L['bref'] - 1
            vd += -s * nd_ * d_adv
            if iso is None:
                vb += s * nb_ * b_adv
                continue
            xb = bl if s > 0 else bh
            e_x = L['eb'] + s * L['qb'] * (xb - L['bref'])
            if e_x <= L['mmr'] * L['qb'] * xb:
                L['dead'] = (t, None)
                liq.append(dict(coin=L['coin'], minute=dt.datetime.utcfromtimestamp(t).strftime('%H:%M'),
                                side=s, margin=L['eb']))
                res[L['coin']] = -L['eb']                         # CoinDCX: the leg's equity at the day's start, lost
                L['eb'] = 0.0
                continue
            vb += e_x
        if iso is not None and iso.get('topup'):
            need = {}
            for L in legs:
                if L.get('missing') or L['dead'] is not None:
                    continue
                bh, bl, bc = L['b'].get(str(t), (None, None, None))
                if bc is None:
                    continue
                need[id(L)] = (L, max(0.0, L['qb'] * bc / L['L'] - (L['eb'] + L['side'] * L['qb'] * (bc - L['bref']))))
            tn = sum(v for _, v in need.values())
            if tn > 0 and free > 0:
                f = min(1.0, free / tn)
                for L, v in need.values():
                    L['eb'] += v * f
                    free -= v * f
        pd_.append(vd); pb_.append(vb)
    # the pairs' day results (price only), for the calibration
    for L in legs:
        if L.get('missing'):
            continue
        s = L['side']
        nd_ = (L['qd'] * L['dref']) if qbook else L['size']
        dcl = L['d'].get(str(ts[-1]), (None, None, None))[2]
        bcl = L['b'].get(str(ts[-1]), (None, None, None))[2]
        if L['coin'] in res:
            res[L['coin']] = dict(res=res[L['coin']] + (L['dead'][1] if L['dead'] and L['dead'][1] is not None else 0.0), liq=True)
        elif dcl is not None and bcl is not None:
            res[L['coin']] = dict(res=-s * nd_ * (dcl / L['dref'] - 1) + s * L['qb'] * (bcl - L['bref']) if iso is not None
                                  else -s * nd_ * (dcl / L['dref'] - 1) + s * ((L['qb'] * L['bref']) if qbook else L['size']) * (bcl / L['bref'] - 1),
                                  liq=False)
    pd_, pb_ = np.array(pd_), np.array(pb_)
    nd = sum(L['size'] for L in book['legs'])
    return dict(day=dt.datetime.utcfromtimestamp(day0).strftime('%Y-%m-%d'), low_d=float(pd_.min() / sd0),
                low_b=float(pb_.min() / sb0), wiped=bool(pd_.min() <= MAINT * nd or pb_.min() <= MAINT * nd),
                liq=liq, res=res, missing=[L['coin'] for L in legs if L.get('missing')])


def prefetch(books_by_day, prods, mcache, threads=6):
    jobs = set()
    for d_, bk in books_by_day.items():
        t0, t1 = d_ + 1800, d_ + 86400 + 1800
        for L in bk['legs']:
            jobs.add(('d', prods[L['coin']]['sym'], t0, t1))
            jobs.add(('b', L['coin'] + 'USDT', t0, t1))
    jobs = sorted(j for j in jobs if not os.path.exists(os.path.join(mcache, f"{'d1m' if j[0] == 'd' else 'b1m'}_{j[1]}_{j[2]}.json")))

    def one(j):
        return (R.delta_1m if j[0] == 'd' else R.bn_1m)(j[1], j[2], j[3], mcache)
    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(one, jobs))
    return len(jobs)


def main(cache, mcache, hcache):
    t_start = time.time()
    for d_ in (mcache, hcache):
        os.makedirs(d_, exist_ok=True)
    print("ROUND 25: THE PLAN WITH COINDCX'S LEGS ON ISOLATED MARGIN (pre-registered: research/r25_preregistration.md)\n")
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
    R23 = json.load(open(os.path.join(HERE, 'r23_round23.json')))
    allow = set(R23['coins'])

    def lst(floor):
        return {c for c in prods if turn.get(c, 0) >= floor} & same & dcx
    OUT = dict(coins=sorted(allow), read=f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")
    print(f"the coin list: Round 23's {len(allow)} coins (research/r23_round23.json); 2024-10-01 -> 2026-09-30; "
          f"wobble floors on Delta turnover read {OUT['read']}\n")

    # engine check: the switch at cross and Round 23's booking == legs3 / sides3 exactly
    a = T.legs3(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB, capK=K6)
    b = legs5(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB, capK=K6)
    sa = T.sides3(allm, 1000.0, cv, allow=allow, capK=K6)
    sb_ = sides5(allm, 1000.0, cv, allow=allow, capK=K6)
    chk = (abs(a['net'] - b['net']) < 1e-12 and abs(sa['low_side'] - sb_['low_side']) < 1e-12
           and abs(sa['transfers_yr'] - sb_['transfers_yr']) < 1e-12)
    print(f"engine check (cross, Round 23's booking == legs3/sides3): {'OK' if chk else 'MISMATCH'} "
          f"(net {a['net']:.6f} / {b['net']:.6f}; lowest account {sa['low_side']:.6f} / {sb_['low_side']:.6f}; "
          f"transfers {sa['transfers_yr']:.3f} / {sb_['transfers_yr']:.3f})")
    OUT['engine_check'] = bool(chk)
    if not chk:
        json.dump(OUT, open(os.path.join(HERE, 'r25_round25.json'), 'w'), indent=1, default=float)
        raise SystemExit(1)
    coins_all = lst(75000) | allow
    hl = T.hl_matrices(allm[0], allm[1], prods, coins_all, hcache)
    rules = dcx_rules(coins_all, os.path.join(HERE, 'r25_dcx_rules.json'))
    lis = [c for c in sorted(allow) if rules[c]['listed']]
    print(f"daily mark highs/lows for {len(coins_all)} coins; CoinDCX's rules read for {len(coins_all)} "
          f"({len(lis)} of the {len(allow)} listed now; the rest at 1.5% / 1.5% / 5x)")
    mm = sorted({(rules[c]['mmr'], rules[c]['fee'], rules[c]['maxlev']) for c in allow if rules[c]['listed']})
    print(f"   the list's (maintenance, liquidation fee, max leverage) combinations: "
          + ', '.join(f"{100 * x:.1f}%/{100 * y:.1f}%/{z:g}x" for x, y, z in mm) + "\n")
    OUT['rules'] = {c: rules[c] for c in sorted(allow)}

    def wobble(**kw):
        r0 = run5(allm, cv, allow, hl, rules, **kw)
        top = [c for c, _ in sorted(r0['per_coin'].items(), key=lambda kv: -kv[1])[:5]]
        res_ = {}
        for c in top:
            x = run5(allm, cv, allow - {c}, hl, rules, **kw)
            res_['without ' + c] = (x['worst'], x['low'], x['after1'])
        for fl in (75000, 150000):
            x = run5(allm, cv, lst(fl), hl, rules, **kw)
            res_[f'floor ${fl // 1000}k'] = (x['worst'], x['low'], x['after1'])
        return res_

    def partA(r, wob):
        return {'average month >= +1.5%': r['avg'] >= 0.015, 'no month below -4%': r['worst'] >= -0.04,
                'poorer account >= 40%': r['low'] >= 0.40, 'HAC t >= 2': r['t'] >= 2.0,
                'both years positive': r['y1'] > 0 and r['y2'] > 0,
                'list wobble holds': all(w >= -0.04 and lo >= 0.40 for w, lo, _ in wob.values())}

    V = {'X': dict(iso=None, qbook=False), 'XQ': dict(iso=None, qbook=True)}
    V.update({k: dict(iso=v, qbook=True) for k, v in VARIANTS.items()})
    Rr, R1, W = {}, {}, {}
    for v, spec in V.items():
        Rr[v] = run5(allm, cv, allow, hl, rules, **spec)
        R1[v] = run5(allm, cv, allow, hl, rules, cost_mult=1.0, **spec)
        if v != 'X':
            W[v] = wobble(**spec)
    print(f"the 24 months done [{time.time() - t_start:.0f}s]")

    # the minute replays: Round 23's 46 days
    days = [int(dt.datetime.strptime(d_, '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp()) for d_ in R23['replay_days']]
    BK = {}
    for v, spec in V.items():
        if v == 'X':
            continue
        BK[v] = sides5(allm, 1000.0, cv, allow=allow, capK=K6, record=set(days), rec_pairs=set(days), hl=hl, rules=rules,
                       **spec)
    allbk = {}
    for v in BK:
        for d_, bk in BK[v]['books'].items():
            allbk.setdefault(d_, dict(legs=[]))['legs'] += bk['legs']
    n = prefetch(allbk, prods, mcache)
    print(f"minute data: {n} series fetched [{time.time() - t_start:.0f}s]")
    # the minute check: cross, Round 23's booking == minute_day3 on the six days
    bk0 = T.sides3(allm, 1000.0, cv, allow=allow, capK=K6, record=set(days[:6]))['books']
    prefetch(bk0, prods, mcache)
    mchk = all(abs(T.minute_day3(bk0[d_], d_, prods, mcache)['low_d'] - minute_day5(bk0[d_], d_, prods, mcache, None, False)['low_d']) < 1e-12
               and abs(T.minute_day3(bk0[d_], d_, prods, mcache)['low_b'] - minute_day5(bk0[d_], d_, prods, mcache, None, False)['low_b']) < 1e-12
               for d_ in days[:6] if d_ in bk0)
    print(f"minute check (cross, Round 23's booking == minute_day3, the six days): {'OK' if mchk else 'MISMATCH'}\n")
    OUT['minute_check'] = bool(mchk)
    if not mchk:
        json.dump(OUT, open(os.path.join(HERE, 'r25_round25.json'), 'w'), indent=1, default=float)
        raise SystemExit(1)
    REP, E = {}, {}
    for v in BK:
        spec = V[v]
        out = []
        e_tot = 0.0
        for d_ in days:
            if d_ not in BK[v]['books']:
                continue
            x = minute_day5(BK[v]['books'][d_], d_, prods, mcache, spec['iso'], True)
            out.append(x)
            if spec['iso'] is not None:
                for coin, rm in x['res'].items():
                    dr = BK[v]['dayres'].get((d_, coin))
                    if dr is None:
                        continue
                    if rm['liq'] or dr['liq']:
                        e_tot += dr['res'] - rm['res']
        REP[v] = out
        E[v] = e_tot
    low_of = {v: min(min(x['low_d'], x['low_b']) for x in REP[v]) for v in REP}
    wiped_of = {v: sum(1 for x in REP[v] if x['wiped']) for v in REP}
    nliq_rep = {v: sum(len(x['liq']) for x in REP[v]) for v in REP}
    crash_of = {v: next((min(x['low_d'], x['low_b']) for x in REP[v] if x['day'] == '2025-10-10'), float('nan')) for v in REP}

    b0 = Rr['X']
    print("THE VARIANTS (10 x 10% + K6, costs x5; x1 = the expected case; accounts booked at constant quantity except X)")
    print(f"{'':4} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} | {'after T1':>8} {'$/yr':>6} {'x1 T1':>6} | "
          f"{'liq/yr':>6} {'skip d/yr':>9} {'held':>5} {'top-ups':>8} {'free low':>8} | {'replays: lowest':>15} {'wiped':>5} {'liqs':>4} "
          f"{'10 Oct 25':>9} {'E $':>7}")
    for v in V:
        r = Rr[v]
        rp = REP.get(v)
        print(f"{v:4} | {100 * r['avg']:+7.2f}% {r['t']:5.2f} {100 * r['worst']:+6.2f}% {r['neg']:2d}/24 {100 * r['low']:5.1f}% | "
              f"{100 * r['after1']:+7.2f}% {(r['after1'] - b0['after1']) * 12000:+6.0f} {100 * R1[v]['after1']:+5.2f}% | "
              f"{r['liq_yr']:6.1f} {r['skipped_yr']:9.1f} {r['avg_held']:5.2f} {r['topups']:8.0f} {100 * r['low_free']:7.1f}% | "
              + (f"{100 * low_of[v]:14.1f}% {wiped_of[v]:5d} {nliq_rep[v]:4d} {100 * crash_of[v]:8.1f}% {E[v]:+7.1f}" if rp else '   (X: Round 23 booking; the replays use XQ)'))
    print("   ($/yr = after tax against X, the cross reference; skip d/yr = days a year with a pair not opened for lack of "
          "CoinDCX free margin; held = average pairs held; E = the minute model's extra loss from liquidations on the "
          "replayed days, in $ on a $1,000 plan)")
    for v in V:
        if v != 'X':
            print(f"   {v}: the poorer account's lowest day {dt.datetime.utcfromtimestamp(Rr[v]['low_day']).strftime('%Y-%m-%d')}")
    print()

    verdict = {}
    for v in VARIANTS:
        r = Rr[v]
        cost_yr = (r['after1'] - b0['after1']) * 12000 - max(0.0, E[v]) / 2.0
        bars = partA(r, W[v])
        b1 = all(bars.values())
        b2 = cost_yr >= -30
        b3 = r['low'] >= Rr['XQ']['low'] - 0.05
        b4 = wiped_of[v] == 0 and low_of[v] >= low_of['XQ'] - 0.05
        status = 'PASS' if (b1 and b2 and b3 and b4) else ('USABLE AT A COST' if (b1 and b3 and b4) else 'FAIL')
        verdict[v] = dict(partA=bars, cost_yr=cost_yr, bar2=b2, bar3=b3, bar4=b4, status=status)
        fails = [k for k, ok in bars.items() if not ok] + ([] if b2 else [f'cost {cost_yr:+.0f} $/yr after calibration (bar -30)']) \
            + ([] if b3 else [f"poorer account {100 * r['low']:.1f}% vs XQ {100 * Rr['XQ']['low']:.1f}% - 5"]) \
            + ([] if b4 else [f"replays: wiped {wiped_of[v]}, lowest {100 * low_of[v]:.1f}% vs XQ {100 * low_of['XQ']:.1f}% - 5"])
        print(f"{v}: {status}" + (f" -- {', '.join(fails)}" if fails else '') + f"  (cost after calibration {cost_yr:+.0f} $/yr)")
    pick = None
    for tier in ('PASS', 'USABLE AT A COST'):
        c_ = [v for v in VARIANTS if verdict[v]['status'] == tier]
        if c_:
            best = max(c_, key=lambda v: Rr[v]['after1'])
            close_ = [v for v in c_ if (Rr[best]['after1'] - Rr[v]['after1']) * 12000 <= 5]
            pick = min(close_, key=lambda v: Rr[v]['liq_yr'])
            break
    print(f"\nRESULT: {('the pick is ' + pick + ' (' + verdict[pick]['status'] + ')') if pick else 'every variant FAILS'}")
    OUT['pick'] = pick
    OUT['R'] = {v: dict(avg=Rr[v]['avg'], t=Rr[v]['t'], worst=Rr[v]['worst'], neg=Rr[v]['neg'], low=Rr[v]['low'],
                        after1=Rr[v]['after1'], x1_after1=R1[v]['after1'], liq_yr=Rr[v]['liq_yr'],
                        skipped_yr=Rr[v]['skipped_yr'], topups=Rr[v]['topups'], low_free=Rr[v]['low_free'],
                        y1=Rr[v]['y1'], y2=Rr[v]['y2'], transfers_yr=Rr[v]['transfers_yr'],
                        replay_low=low_of.get(v), replay_wiped=wiped_of.get(v), replay_liqs=nliq_rep.get(v),
                        crash_low=crash_of.get(v), E=E.get(v),
                        wobble={k: dict(worst=a_, low=lo, after1=af) for k, (a_, lo, af) in (W.get(v) or {}).items()})
                for v in V}
    OUT['liquidations'] = {v: [dict(day=dt.datetime.utcfromtimestamp(int(allm[0][i1])).strftime('%Y-%m-%d'), coin=c,
                                    on=('CoinDCX long' if s_ > 0 else 'CoinDCX short'), twin=fd_, lost=fb_)
                               for i1, c, fd_, fb_, s_ in Rr[v]['liq_list']] for v in VARIANTS}
    OUT['replay_days'] = R23['replay_days']
    OUT['replays'] = {v: [dict(day=x['day'], low_d=x['low_d'], low_b=x['low_b'], wiped=x['wiped'], liq=x['liq'],
                               missing=x['missing']) for x in REP[v]] for v in REP}
    OUT['verdict'] = verdict
    json.dump(OUT, open(os.path.join(HERE, 'r25_round25.json'), 'w'), indent=1, default=float)
    print(f"\n[{time.time() - t_start:.0f}s]")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
