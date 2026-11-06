#!/usr/bin/env python3
"""Round 23 (C547), pre-registered in research/r23_preregistration.md (pushed before this ran): protection against one
coin jumping several times over in a day, on top of the plan (Delta India + CoinDCX, 10 x 10%, the K6 cap).

    C524_MARK=1 python3 research/r23_round23.py XV_CACHE MINUTE_CACHE HL_CACHE

J1/J2 entry filters, Z1/Z2 half-size legs, S50/S100 short-leg stops (the twin closed at once); W530/L100 stress on
the daily account book; Round 24's minute replays (+ every day a held coin moved >= 30% intraday, the 40 largest);
the bigger settings only with what passes. Engine: Round 24's legs2/sides2 copied as legs3/sides3 with the switches;
with every switch off they must reproduce legs2/sides2 (capK=6) exactly.
"""
import os, sys, io, json, math, time, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S
import c532_india_only as C
import c542_pairs as P
import r24_round24 as R

TAX, COSTB, MAINT, SLIP, K6 = P.TAX, R.COSTB, R.MAINT, 0.05, 6
DAY = 86400


# ── daily mark highs and lows ────────────────────────────────────────────────
def delta_hl(sym, hcache):
    f = os.path.join(hcache, f"dhl_{sym}.json")
    if os.path.exists(f):
        return json.load(open(f))
    r = (R._get(X.DELTA + '/v2/history/candles', dict(resolution='1d', symbol='MARK:' + sym, start=X.START - 10 * DAY,
                                                     end=X.END)) or {}).get('result') or []
    out = sorted((int(x['time']), float(x['high']), float(x['low']), float(x['close'])) for x in r)
    json.dump(out, open(f, 'w'))
    return out


def bn_hl(sym, hcache):
    f = os.path.join(hcache, f"bhl_{sym}.json")
    if os.path.exists(f):
        return json.load(open(f))
    r = R._get(X.BN + '/fapi/v1/markPriceKlines', dict(symbol=sym, interval='1d', startTime=(X.START - 10 * DAY) * 1000,
                                                       limit=1000)) or []
    out = [(int(x[0]) // 1000, float(x[2]), float(x[3]), float(x[4])) for x in r] if isinstance(r, list) else []
    json.dump(out, open(f, 'w'))
    return out


def hl_matrices(D, names, prods, coins, hcache):
    idx = {int(t): i for i, t in enumerate(D)}
    hD = np.full((len(D), len(names)), np.nan); lD = hD.copy(); hB = hD.copy(); lB = hD.copy()
    for j, c in enumerate(names):
        if c not in coins:
            continue
        for t, h, l, _ in delta_hl(prods[c]['sym'], hcache):
            i = idx.get(t // DAY * DAY)
            if i is not None:
                hD[i, j], lD[i, j] = h, l
        for t, h, l, _ in bn_hl(c + 'USDT', hcache):
            i = idx.get(t)
            if i is not None:
                hB[i, j], lB[i, j] = h, l
    return hD, lD, hB, lB


# ── the switches ─────────────────────────────────────────────────────────────
class Sw:
    """J1/J2 (entry filter), Z1/Z2 (half size), S (short-leg stop)"""
    def __init__(self, allm, hl, J=None, Z=None, stop=None):
        D, names, fD, fB, pD, pB = allm
        hD, lD, hB, lB = hl
        self.J, self.Z, self.stop = J, Z, stop
        jumpD = np.full_like(pD, np.nan); jumpB = jumpD.copy()
        jumpD[1:] = hD[1:] / pD[:-1] - 1; jumpB[1:] = hB[1:] / pB[:-1] - 1
        self.jump = np.fmax(jumpD, jumpB)                       # the day's largest up-jump on either exchange
        self.jumpD, self.jumpB = jumpD, jumpB
        rB = np.full_like(pB, np.nan); rB[1:] = pB[1:] / pB[:-1] - 1
        self.rB = rB
        first = np.full(len(names), 10 ** 9)
        for j in range(len(names)):
            nz = np.where(~np.isnan(pB[:, j]))[0]
            if len(nz):
                first[j] = nz[0]
        self.first = first

    def _maxjump(self, i, j, n):
        w = self.jump[max(0, i - n + 1):i + 1, j]
        w = w[~np.isnan(w)]
        return float(w.max()) if len(w) else 0.0

    def skip(self, i, j):
        if self.J == 'J1':
            return self._maxjump(i, j, 90) >= 1.0
        if self.J == 'J2':
            return i - self.first[j] < 90
        return False

    def mult(self, i, j, cand_js):
        if self.Z == 'Z2':
            return 0.5 if self._maxjump(i, j, 30) >= 0.5 else 1.0
        if self.Z == 'Z1':
            sig = {}
            for q in cand_js:
                w = self.rB[max(0, i - 29):i + 1, q]
                w = w[~np.isnan(w)]
                sig[q] = float(w.std()) if len(w) >= 10 else float('nan')
            vals = np.array([v for v in sig.values() if not np.isnan(v)])
            if len(vals) < 4 or np.isnan(sig.get(j, float('nan'))):
                return 1.0
            return 0.5 if sig[j] >= np.percentile(vals, 75) else 1.0
        return 1.0

    def stopped(self, i1, j, side):
        """(stopped?, short leg's move, twin's capped move) for day i1"""
        if self.stop is None:
            return False, 0.0, 0.0
        js, jt = (self.jumpD, self.jumpB) if side > 0 else (self.jumpB, self.jumpD)
        a = js[i1, j]
        if np.isnan(a) or a < self.stop:
            return False, 0.0, 0.0
        b = jt[i1, j]
        return True, self.stop + SLIP, (min(self.stop, b) if not np.isnan(b) else 0.0)

    def loss(self, J, size):
        return (min(J, self.stop + SLIP) if self.stop is not None else J) * size


# ── the engine, with the switches ────────────────────────────────────────────
def legs3(D, names, fD, fB, pD, pB, cv, cap, allow, costB, maxp=10, size=0.10, cost_mult=5.0, costD=None, gst=C.GST,
          capK=None, sw=None):
    costD = X.COST_D if costD is None else costD
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    s7, am = R._s7(D, names, fD, fB, allow)
    ok &= am[None, :]
    cB, cD = costB * cost_mult, costD * cost_mult
    held, size_ = {}, {}
    pnl = np.zeros(len(D)); entered = stops = 0
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
        if sw is not None and sw.J:
            cand = [j for j in cand if not sw.skip(i, j)]
        cand.sort(key=lambda j: -abs(sig[j]))
        cjs = list(cand)
        cand = [(j, int(np.sign(sig[j]))) for j in cand]

        def sizer(j, i=i):
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            m_ = sw.mult(i, j, cjs) if (sw is not None and sw.Z) else 1.0
            kq = int(round(size * m_ * cap / (c_ * px)))
            if kq < 1:
                return False
            sz = kq * c_ * px / cap
            size_[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            legB[j] = 0.0
            book(i + 1, j, -sz * cD, -sz * cB)
            return True
        entered += len(R._enter(i, cand, held, maxp - len(held), capK, sizer))
        gone = []
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            if sw is not None and sw.stop is not None:
                hit, a, b = sw.stopped(i + 1, j, side)
                if hit:
                    # the short leg stopped at the stop + slip; the twin closed at once, its gain capped
                    d_ = size_[j] * (-a if side > 0 else b)
                    b_ = size_[j] * (b if side > 0 else -a)
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
            pnl[i + 1] += d_ + b_
            book(i + 1, j, d_, b_)
        for j in gone:
            stops += 1
            pnl[i + 1] -= size_[j] * (cB + cD)
            book(i + 1, j, -size_[j] * cD, -size_[j] * cB)
            closedB.append(legB.pop(j, 0.0))
            del held[j], size_[j]
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
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, stops=stops,
                pre=float(x.sum()), tax1=float(t1), tax2=float(t2), daily=x, days=Dl,
                per_coin={names[j]: float(pc[j] / live.sum() * 365) for j in range(k) if pc[j]})


def sides3(allm, cap, cv, trigger=0.65, cost_mult=5.0, allow=None, costB=COSTB, maxp=10, size=0.10, capK=None, sw=None,
           record=None, log_held=False):
    Dd, names, fD, fB, pD, pB = allm
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    s7, _am = R._s7(Dd, names, fD, fB, allow if allow is not None else set(names))
    cB, cD = costB * cost_mult, X.COST_D * cost_mult
    held, size_ = {}, {}
    sd, sb = cap / 2.0, cap / 2.0
    cur, pend, transfers, low, lows_m = None, False, 0, 1.0, {}
    daily_low, daily_drop, books, held_log = {}, {}, {}, {}
    w530, ndays, l100 = 0, 0, 9.0
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
        if sw is not None and sw.J:
            cand = [j for j in cand if not sw.skip(i, j)]
        cand.sort(key=lambda j: -abs(sig[j]))
        cjs = list(cand)
        cand = [(j, int(np.sign(sig[j]))) for j in cand]
        eqn = sd + sb

        def sizer(j, i=i):
            nonlocal sd, sb
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                return False
            m_ = sw.mult(i, j, cjs) if (sw is not None and sw.Z) else 1.0
            kq = int(round(size * m_ * eqn / (c_ * px)))
            if kq < 1:
                return False
            size_[j] = kq * c_ * px
            sb -= size_[j] * cB; sd -= size_[j] * cD
            return True
        R._enter(i, cand, held, maxp - len(held), capK, sizer)
        if record is not None and int(Dd[i + 1]) in record:
            books[int(Dd[i + 1])] = dict(sd=sd, sb=sb, half=(sd + sb) / 2.0,
                                         legs=[dict(coin=names[j], side=s, size=size_[j]) for j, s in held.items()])
        if log_held:
            held_log[i + 1] = list(held.items())
        if i + 1 >= X.WIN and held:
            ndays += 1
            bad = False
            for j, s in held.items():
                acct = sd if s > 0 else sb                      # the account holding this pair's SHORT leg
                l5 = sw.loss(5.3, size_[j]) if sw is not None else 5.3 * size_[j]
                l1 = sw.loss(1.0, size_[j]) if sw is not None else 1.0 * size_[j]
                bad = bad or (acct - l5 <= 0)
                l100 = min(l100, (acct - l1) / (cap / 2.0))
            w530 += bad
        sd_b, sb_b = sd, sb
        gone = []
        for j, side in held.items():
            if ok[i + 1, j]:
                if sw is not None and sw.stop is not None:
                    hit, a, b = sw.stopped(i + 1, j, side)
                    if hit:
                        sd += size_[j] * (-a if side > 0 else b)
                        sb += size_[j] * (b if side > 0 else -a)
                        gone.append(j)
                        continue
                sb += size_[j] * side * (rB[i + 1, j] - fB[i + 1, j])
                sd += size_[j] * side * (fD[i + 1, j] - rD[i + 1, j])
        for j in gone:
            sb -= size_[j] * cB; sd -= size_[j] * cD
            del held[j], size_[j]
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
    return dict(end=(sd + sb) / cap, low_side=float(low), months_lt50=float((lm < 0.50).mean()),
                transfers_yr=transfers / yrs, daily_low=daily_low, daily_drop=daily_drop, books=books,
                held_log=held_log, w530=w530 / max(1, ndays), l100=float(l100))


def run3(allm, cv, allow, cost=COSTB, maxp=10, size=0.10, cost_mult=5.0, capK=K6, sw=None, with_sides=True):
    r = legs3(*allm, cv=cv, cap=1000.0, allow=allow, costB=cost, maxp=maxp, size=size, cost_mult=cost_mult,
              capK=capK, sw=sw)
    ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
    nm = len(mv)
    r.update(mv=mv, avg=float(mv.mean()), worst=float(mv.min()), neg=int((mv < 0).sum()),
             after1=(r['pre'] - r['tax1']) / nm, after2=(r['pre'] - r['tax2']) / nm,
             y1=sum(v for k, v in r['months'].items() if '2024-10' <= k <= '2025-09'),
             y2=sum(v for k, v in r['months'].items() if '2025-10' <= k <= '2026-09'))
    if with_sides:
        sd = sides3(allm, 1000.0, cv, trigger=0.65, allow=allow, cost_mult=cost_mult, costB=cost, maxp=maxp, size=size,
                    capK=capK, sw=sw)
        r.update(low=sd['low_side'], transfers_yr=sd['transfers_yr'], w530=sd['w530'], l100=sd['l100'])
    return r


# ── minute replays, with the stop ────────────────────────────────────────────
def minute_day3(book, day0, prods, mcache, stop=None):
    t0, t1 = day0 + 1800, day0 + 86400 + 1800
    legs = []
    for L in book['legs']:
        c = L['coin']
        dm = R.delta_1m(prods[c]['sym'], t0, t1, mcache)
        bm = R.bn_1m(c + 'USDT', t0, t1, mcache)
        legs.append(dict(L, missing=True) if (not dm or not bm) else dict(L, d=dm, b=bm, frozen=None))
    sd0, sb0 = book['sd'], book['sb']
    pd_, pb_, nstop = [], [], 0
    for t in range(t0, t1, 60):
        vd, vb = sd0, sb0
        for L in legs:
            if L.get('missing'):
                continue
            if L['frozen'] is not None:
                vd += L['frozen'][0]; vb += L['frozen'][1]
                continue
            ks = str(t)
            dref = L['d'].get(str(t0)) or next(iter(L['d'].values()))
            bref = L['b'].get(str(t0)) or next(iter(L['b'].values()))
            dh, dl, _ = L['d'].get(ks, (None, None, None))
            bh, bl, _ = L['b'].get(ks, (None, None, None))
            if dh is None or bh is None:
                continue
            s, n = L['side'], L['size']
            d_adv = (dh if s > 0 else dl) / dref[2] - 1
            b_adv = (bl if s > 0 else bh) / bref[2] - 1
            dv, bv = -s * n * d_adv, s * n * b_adv
            if stop is not None:
                up = (dh / dref[2] - 1) if s > 0 else (bh / bref[2] - 1)        # the short leg's rise
                if up >= stop:
                    a = -(stop + SLIP) * n
                    dv, bv = (a, bv) if s > 0 else (dv, a)
                    L['frozen'] = (dv, bv)
                    nstop += 1
            vd += dv; vb += bv
        pd_.append(vd); pb_.append(vb)
    pd_, pb_ = np.array(pd_), np.array(pb_)
    nd = sum(L['size'] for L in book['legs'])
    return dict(day=dt.datetime.utcfromtimestamp(day0).strftime('%Y-%m-%d'), low_d=float(pd_.min() / sd0),
                low_b=float(pb_.min() / sb0), wiped=bool(pd_.min() <= MAINT * nd or pb_.min() <= MAINT * nd),
                stops=nstop, missing=[L['coin'] for L in legs if L.get('missing')])


def main(cache, mcache, hcache):
    t_start = time.time()
    for d_ in (mcache, hcache):
        os.makedirs(d_, exist_ok=True)
    print("ROUND 23 (C547): ONE COIN JUMPING -- FILTERS, HALF-SIZE LEGS, SHORT-LEG STOPS (pre-registered: "
          "research/r23_preregistration.md)\n")
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
    OUT = dict(coins=sorted(allow), read=f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")
    print(f"Delta turnover read {OUT['read']}: {len(allow)} coins (Round 24 had 64 on 10 Oct); 2024-10-01 -> 2026-09-30\n")

    a = R.legs2(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB, capK=K6)
    b = legs3(*allm, cv=cv, cap=1000.0, allow=allow, costB=COSTB, capK=K6)
    sa = R.sides2(allm, 1000.0, cv, allow=allow, capK=K6)
    sb_ = sides3(allm, 1000.0, cv, allow=allow, capK=K6)
    chk = (abs(a['net'] - b['net']) < 1e-12 and abs(sa['low_side'] - sb_['low_side']) < 1e-12
           and abs(sa['transfers_yr'] - sb_['transfers_yr']) < 1e-12)
    print(f"engine check (switches off == Round 24's legs2/sides2 with the K6 cap): {'OK' if chk else 'MISMATCH'} "
          f"(net {a['net']:.6f} / {b['net']:.6f}; lowest account {sa['low_side']:.6f} / {sb_['low_side']:.6f})")
    OUT['engine_check'] = bool(chk)
    if not chk:
        json.dump(OUT, open(os.path.join(HERE, 'r23_round23.json'), 'w'), indent=1, default=float)
        raise SystemExit(1)
    hl = hl_matrices(allm[0], allm[1], prods, lst(75000), hcache)
    print(f"daily mark highs/lows read for {len(lst(75000))} coins\n")

    def wobble(r, **kw):
        top = [c for c, _ in sorted(r['per_coin'].items(), key=lambda kv: -kv[1])[:5]]
        res_ = {}
        for c in top:
            x = run3(allm, cv, allow - {c}, **kw)
            res_['without ' + c] = (x['worst'], x['low'], x['after1'])
        for fl in (75000, 150000):
            x = run3(allm, cv, lst(fl), **kw)
            res_[f'floor ${fl // 1000}k'] = (x['worst'], x['low'], x['after1'])
        return res_

    def partA(r, wob):
        return {'average month >= +1.5%': r['avg'] >= 0.015, 'no month below -4%': r['worst'] >= -0.04,
                'poorer account >= 40%': r['low'] >= 0.40, 'HAC t >= 2': r['t'] >= 2.0,
                'both years positive': r['y1'] > 0 and r['y2'] > 0,
                'list wobble holds': all(w >= -0.04 and lo >= 0.40 for w, lo, _ in wob.values())}

    def mk(spec):
        return None if not spec else Sw(allm, hl, J=spec.get('J'), Z=spec.get('Z'), stop=spec.get('stop'))
    V = {'base': {}, 'J1': dict(J='J1'), 'J2': dict(J='J2'), 'Z1': dict(Z='Z1'), 'Z2': dict(Z='Z2'),
         'S50': dict(stop=0.5), 'S100': dict(stop=1.0)}
    Rr, R1, W = {}, {}, {}
    for v, spec in V.items():
        Rr[v] = run3(allm, cv, allow, sw=mk(spec))
        R1[v] = run3(allm, cv, allow, cost_mult=1.0, with_sides=False, sw=mk(spec))
        W[v] = wobble(Rr[v], sw=mk(spec))

    # replay days: Round 24's six + every day a held coin (base book) moved >= 30% intraday, the 40 largest
    crash = int(dt.datetime(2025, 10, 10, tzinfo=dt.timezone.utc).timestamp())
    D = allm[0]
    bs = sides3(allm, 1000.0, cv, allow=allow, capK=K6, log_held=True)
    six = [crash]
    for d_, f in sorted(bs['daily_drop'].items(), key=lambda kv: kv[1]):
        if len(six) >= 6:
            break
        if all(abs(d_ - x) > 3 * DAY for x in six):
            six.append(d_)
    hD, lD, hB, lB = hl
    pD, pB = allm[4], allm[5]
    big = {}
    for i1, hh in bs['held_log'].items():
        if i1 < X.WIN:
            continue
        for j, _s in hh:
            mv = 0.0
            for h, l, p in ((hD, lD, pD), (hB, lB, pB)):
                if not np.isnan(h[i1, j]) and not np.isnan(p[i1 - 1, j]) and p[i1 - 1, j] > 0:
                    mv = max(mv, h[i1, j] / p[i1 - 1, j] - 1, 1 - l[i1, j] / p[i1 - 1, j])
            if mv >= 0.30:
                big[int(D[i1])] = max(big.get(int(D[i1]), 0.0), mv)
    extra = [d_ for d_, _ in sorted(big.items(), key=lambda kv: -kv[1]) if d_ not in six][:40]
    days = six + extra
    print(f"replay days: Round 24's six + {len(extra)} of the {len(big)} days a held coin moved >= 30% intraday\n")

    def replays(v, spec, maxp=10, size=0.10, capK=K6):
        bk = sides3(allm, 1000.0, cv, allow=allow, capK=capK, maxp=maxp, size=size, sw=mk(spec), record=set(days))['books']
        out = []
        for d_ in days:
            if d_ in bk:
                out.append(minute_day3(bk[d_], d_, prods, mcache, stop=(spec or {}).get('stop')))
        return out

    # second engine check: with no stop, the minute replay must equal Round 24's minute_day on the same books
    bk0 = R.sides2(allm, 1000.0, cv, allow=allow, capK=K6, record=set(six))['books']
    mchk = all(abs(R.minute_day(bk0[d_], d_, prods, mcache)['low_d'] - minute_day3(bk0[d_], d_, prods, mcache)['low_d']) < 1e-12
               and abs(R.minute_day(bk0[d_], d_, prods, mcache)['low_b'] - minute_day3(bk0[d_], d_, prods, mcache)['low_b']) < 1e-12
               for d_ in six if d_ in bk0)
    print(f"minute-replay check (no stop == Round 24's minute_day, the six days): {'OK' if mchk else 'MISMATCH'}\n")
    OUT['minute_check'] = bool(mchk)
    if not mchk:
        json.dump(OUT, open(os.path.join(HERE, 'r23_round23.json'), 'w'), indent=1, default=float)
        raise SystemExit(1)
    REP = {}
    for v, spec in V.items():
        REP[v] = replays(v, spec)
    low_of = {v: min(min(x['low_d'], x['low_b']) for x in REP[v]) for v in REP}
    wiped_of = {v: sum(1 for x in REP[v] if x['wiped']) for v in REP}
    crash_of = {v: next((min(x['low_d'], x['low_b']) for x in REP[v] if x['day'] == '2025-10-10'), float('nan')) for v in REP}

    print("THE PROTECTIONS (10 x 10% + K6, costs x5; x1 = expected case)")
    print(f"{'':5} | {'pre-tax':>8} {'t':>5} {'worst':>7} {'down':>5} {'poorer':>6} | {'after T1':>8} {'$/yr':>6} {'x1 T1':>6} | "
          f"{'W530':>6} {'L100':>7} | {'replays: lowest':>15} {'wiped':>5} {'10 Oct 25':>9} | stops/yr")
    yrs = len(Rr['base']['daily']) / 365
    for v in V:
        r = Rr[v]
        print(f"{v:5} | {100 * r['avg']:+7.2f}% {r['t']:5.2f} {100 * r['worst']:+6.2f}% {r['neg']:2d}/24 {100 * r['low']:5.1f}% | "
              f"{100 * r['after1']:+7.2f}% {(r['after1'] - Rr['base']['after1']) * 12000:+6.0f} {100 * R1[v]['after1']:+5.2f}% | "
              f"{100 * r['w530']:5.1f}% {100 * r['l100']:+6.1f}% | {100 * low_of[v]:14.1f}% {wiped_of[v]:5d} {100 * crash_of[v]:8.1f}% | "
              f"{r['stops'] / yrs:5.1f}")
    print("   (W530 = share of days a +530% jump on the largest short leg would empty its account; L100 = the lowest account "
          "after a +100% jump on it, any day)\n")

    verdict = {}
    b0 = Rr['base']
    for v in V:
        if v == 'base':
            continue
        r = Rr[v]
        bars = partA(r, W[v])
        bars.update({'after tax >= base - $30/yr': (r['after1'] - b0['after1']) * 12000 >= -30,
                     'safer (W530 halved, or L100 +10 points)': (r['w530'] <= 0.5 * b0['w530'] if b0['w530'] > 0 else False)
                     or (r['l100'] - b0['l100'] >= 0.10),
                     'replays: no account wiped': wiped_of[v] == 0,
                     'replays: poorer account >= base - 2 points': low_of[v] >= low_of['base'] - 0.02})
        verdict[v] = dict(bars=bars, passed=all(bars.values()))
        print(f"{v}: {'PASS' if all(bars.values()) else 'fail: ' + ', '.join(k for k, ok in bars.items() if not ok)}")
    passed = [v for v in verdict if verdict[v]['passed']]
    adopt = None
    if len(passed) >= 2:
        spec = {}
        for v in passed:
            spec.update(V[v])
        if sum(1 for v in passed if v.startswith('J')) > 1 or sum(1 for v in passed if v.startswith('Z')) > 1 \
                or sum(1 for v in passed if v.startswith('S')) > 1:
            # two of the same kind cannot both be on; keep each kind's best L100
            spec = {}
            for kind in ('J', 'Z', 'S'):
                ks = [v for v in passed if v.startswith(kind)]
                if ks:
                    spec.update(V[max(ks, key=lambda v: Rr[v]['l100'])])
        rc = run3(allm, cv, allow, sw=mk(spec))
        wc = wobble(rc, sw=mk(spec))
        repc = replays('combo', spec)
        lowc = min(min(x['low_d'], x['low_b']) for x in repc)
        bars = partA(rc, wc)
        bars.update({'after tax >= base - $30/yr': (rc['after1'] - b0['after1']) * 12000 >= -30,
                     'safer (W530 halved, or L100 +10 points)': (rc['w530'] <= 0.5 * b0['w530'] if b0['w530'] > 0 else False)
                     or (rc['l100'] - b0['l100'] >= 0.10),
                     'replays: no account wiped': not any(x['wiped'] for x in repc),
                     'replays: poorer account >= base - 2 points': lowc >= low_of['base'] - 0.02})
        print(f"\nCOMBINATION {spec}: after T1 {100 * rc['after1']:+.2f}% ({(rc['after1'] - b0['after1']) * 12000:+.0f} $/yr), "
              f"W530 {100 * rc['w530']:.1f}%, L100 {100 * rc['l100']:+.1f}%, replays lowest {100 * lowc:.1f}%: "
              f"{'PASS' if all(bars.values()) else 'fail: ' + ', '.join(k for k, ok in bars.items() if not ok)}")
        verdict['combination'] = dict(spec=spec, bars=bars, passed=all(bars.values()), after1=rc['after1'],
                                      w530=rc['w530'], l100=rc['l100'], replay_low=lowc)
        adopt = spec if all(bars.values()) else V[max(passed, key=lambda v: Rr[v]['l100'])]
    elif len(passed) == 1:
        adopt = V[passed[0]]
    print(f"\nADOPTED: {adopt if adopt else 'nothing -- the plan is unchanged'}")
    OUT['adopted'] = adopt

    # the bigger settings, only with the adopted protections
    G = {}
    if adopt:
        print("\nTHE BIGGER SETTINGS WITH THE ADOPTED PROTECTIONS (cap 60% of the slots)")
        gb = None
        for n in (10, 15):
            for s in (0.10, 0.12):
                capK = int(0.6 * n + 1e-9)
                r = run3(allm, cv, allow, maxp=n, size=s, capK=capK, sw=mk(adopt))
                wob = wobble(r, maxp=n, size=s, capK=capK, sw=mk(adopt))
                rep = replays(f'{n}x{s}', adopt, maxp=n, size=s, capK=capK)
                G[f'{n}x{int(round(s * 100))}'] = dict(r=r, wob=wob, rep=rep)
                if (n, s) == (10, 0.10):
                    gb = r
        for key, g in G.items():
            r, rep = g['r'], g['rep']
            low_rep = min(min(x['low_d'], x['low_b']) for x in rep)
            bars = partA(r, g['wob'])
            bars.update({'W530 no worse than 10x10%': r['w530'] <= gb['w530'] + 1e-12,
                         'replays: none wiped, poorer >= 40%': (not any(x['wiped'] for x in rep)) and low_rep >= 0.40,
                         '>= $50/yr more after tax': (r['after1'] - gb['after1']) * 12000 >= 50,
                         'at most one more losing month': r['neg'] <= gb['neg'] + 1})
            g['bars'] = bars
            g['passed'] = key != '10x10' and all(bars.values())
            print(f"{key:6} after T1 {100 * r['after1']:+.2f}% ({(r['after1'] - gb['after1']) * 12000:+.0f} $/yr) worst "
                  f"{100 * r['worst']:+.2f}% poorer {100 * r['low']:.1f}% W530 {100 * r['w530']:.1f}% L100 "
                  f"{100 * r['l100']:+.1f}% replays {100 * low_rep:.1f}% | "
                  + ('PASS' if g['passed'] else ('(the reference)' if key == '10x10' else
                                                 'fail: ' + ', '.join(k for k, ok in bars.items() if not ok))))
    else:
        print("\nTHE BIGGER SETTINGS: not run (nothing adopted; the pre-registration runs them only with what passes)")

    OUT['R'] = {v: dict(avg=Rr[v]['avg'], t=Rr[v]['t'], worst=Rr[v]['worst'], neg=Rr[v]['neg'], low=Rr[v]['low'],
                        after1=Rr[v]['after1'], x1_after1=R1[v]['after1'], w530=Rr[v]['w530'], l100=Rr[v]['l100'],
                        stops=Rr[v]['stops'], replay_low=low_of[v], replay_wiped=wiped_of[v], crash_low=crash_of[v],
                        wobble={k: dict(worst=a_, low=lo, after1=af) for k, (a_, lo, af) in W[v].items()})
                for v in V}
    OUT['replay_days'] = [dt.datetime.utcfromtimestamp(d_).strftime('%Y-%m-%d') for d_ in days]
    OUT['replays'] = {v: REP[v] for v in REP}
    OUT['verdict'] = verdict
    OUT['grid'] = {k: dict(after1=g['r']['after1'], w530=g['r']['w530'], l100=g['r']['l100'], low=g['r']['low'],
                           passed=g['passed'], bars=g['bars']) for k, g in G.items()}
    json.dump(OUT, open(os.path.join(HERE, 'r23_round23.json'), 'w'), indent=1, default=float)
    print(f"\n[{time.time() - t_start:.0f}s]")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
