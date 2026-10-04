#!/usr/bin/env python3
"""C532 (descriptive planning, no new rule): the operator's $600 entirely on Indian, rupee-settled venues.

    python3 research/c532_india_only.py BNC_DIR XV_CACHE PI42_DIR

Why: acting as the operator's tax adviser (C532 report), USDT-settled futures on Binance are treated as
VDA income (s.115BBH: 31.2% of each gain, losses ignored; the conservative, defensible reading -- the USDT
received at settlement is a VDA), and an Indian resident sending money abroad for derivatives or margin
trading is outside the LRS (FEMA). Rupee-settled perps on Indian exchanges (Delta Exchange India, Pi42) are
speculative business income (s.43(5): not a recognised stock exchange) at the slab rate, no 1% TDS, with the
s.87A rebate below Rs 12 lakh of total income. So the cross-venue trade's Binance leg moves to Pi42.

Pi42 (checked 4 Oct 2026, PI42_DIR): its rupee perps quote Binance's pair ('ps': 'BTCUSDT'); of 246 with a
Binance twin, 216 settle funding at the same moment and 87% of the next rates are within 0.002% per
settlement of Binance's (median gap 0.0005% vs a median rate of 0.005%). So Binance's funding and prices
stand in for Pi42's history. Pi42 lists 113 of Delta's coins (Binance: 190). Fees 0.10% taker (+18% GST).
The X1 rule exactly as round 15, ALL harder (midnight timing, Delta's mark, costs x5, $100k Delta turnover,
the same asset), whole Delta contracts, and three Pi42 changes: only coins Pi42 lists; Pi42's fee
(0.10% x 1.18 + 0.02% spread a side) in place of Binance's; 18% GST on any funding PAID, on both venues
(stated conservatively: neither venue's terms settle it).
The book on Delta as in C531 (whole contracts, no interest on idle cash, Delta's extra funding).
Splits of the $600 with a reserve of $50 (the operator's minimum) or $0 -- the reserve held in rupees,
earning nothing, counted in the $600. Tax: one speculative business, net per year at the slab (0% = total
income under Rs 12 lakh with the s.87A rebate; 15.6%; 31.2%), a losing year untaxed (its loss carried).
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c528_budget_plan as P
import c524_xvenue as X
import c531_split_600 as S

TOTAL = 600
COST_PI42 = 0.0010 * 1.18 + 0.0002
GST = 0.18
OUT = {}


def xv_pi42(D, names, fD, fB, pD, pB, cv, cap, allow, cost_mult=5.0, gst=GST):
    """X1 (c530_plan_odds.xv_contracts) with Pi42 in Binance's place: its fee, GST on funding paid"""
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
    cB, cD = COST_PI42 * cost_mult, X.COST_D * cost_mult
    held, size = {}, {}
    pnl = np.zeros(len(D)); skipped = entered = 0
    for i in range(len(D) - 1):
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                pnl[i + 1] -= size[j] * (cB + cD)
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
                skipped += 1
                continue
            sz = kq * c_ * px / cap
            held[j] = int(np.sign(sig[j])); size[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            room -= 1; entered += 1
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            fd_leg = side * fD[i + 1, j]              # side +1: short Delta -> receives Delta's rate
            fb_leg = -side * fB[i + 1, j]             # ... long Pi42 -> pays Pi42's (Binance's) rate
            fd_leg = fd_leg * (1 + gst) if fd_leg < 0 else fd_leg
            fb_leg = fb_leg * (1 + gst) if fb_leg < 0 else fb_leg
            pnl[i + 1] += size[j] * (fd_leg + fb_leg + side * (rB[i + 1, j] - rD[i + 1, j]))
    live = np.arange(len(D)) >= X.WIN
    x = pnl[live]; Dl = D[live]
    months = {}
    for d_, v in zip(Dl, x):
        m = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        months[m] = months.get(m, 0.0) + v
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, entered=entered, skipped=skipped)


def main(bdir, cache, pdir):
    print("C532: THE $600 ON INDIAN RUPEE-SETTLED VENUES ONLY -- THE BOOK ON DELTA + DELTA vs PI42\n")
    uni = json.load(open(os.path.join(pdir, 'pi42_universe.json')))
    pi42 = set(uni['both'])
    cmp_ = json.load(open(os.path.join(pdir, 'pi42_vs_binance.json')))
    a = np.array([[r[1], r[2]] for r in cmp_])
    print(f"Pi42 vs Binance funding (4 Oct 2026, {len(cmp_)} rupee perps with a Binance twin): "
          f"{sum(r[3] for r in cmp_)} settle at the same moment; next rates within 0.002%/settlement: "
          f"{100 * (abs(a[:, 0] - a[:, 1]) < 2e-5).mean():.0f}%; median gap {100 * np.median(abs(a[:, 0] - a[:, 1])):.4f}%")
    print(f"coins on both Delta and Pi42 (rupee): {len(pi42)}")
    with contextlib.redirect_stdout(io.StringIO()):
        D = P.B.prep(bdir)
    om = P.B.om
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    P.B.EQ, P.B.TV = 1e9, 0.20 * 4 / 3
    W = P.B.sleeves(D, sd=sdgk, topn=20)
    _, Wc, _ = P.B.book(D, W)
    cv = S.delta_cv()
    BK = {}
    print("\n1. THE BOOK ON DELTA (whole contracts, no interest on idle cash), planning = backtest mean cut by 1/3")
    print("   size   plan held   avg/month backtested   planning")
    for eq in range(50, TOTAL + 1, 50):
        xs, Ts, held, nc = S.book_on_delta(D, Wc, cv, eq)
        mm = P.months_of(Ts, xs); kk = sorted(mm)[1:]
        mv = np.array([mm[k] for k in kk])
        BK[eq] = mv
        if eq % 100 == 0 or eq == 550:
            print(f"   ${eq:<5}   {100 * held:5.1f}%         {100 * mv.mean():+5.2f}%           {100 * mv.mean() * 2 / 3:+5.2f}%")
    prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    base = X.matrices(prods, res)
    rD = np.full_like(base[4], np.nan); rB = rD.copy()
    rD[1:] = base[4][1:] / base[4][:-1] - 1; rB[1:] = base[5][1:] / base[5][:-1] - 1
    same = set()
    for j, c in enumerate(base[1]):
        m_ = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m_.sum() > 60 and np.corrcoef(rD[m_, j], rB[m_, j])[0, 1] >= 0.9:
            same.add(c)
    allow = liq & same & pi42
    print(f"\n2. DELTA vs PI42 (X1, ALL harder, whole contracts; {len(allow)} coins pass liquidity + same asset + on Pi42; "
          f"Binance's version had {len(liq & same)})")
    print("   capital   net/yr     t     entries  skipped   avg/month   worst month")
    XV = {}
    for cap in range(50, TOTAL + 1, 50):
        r = xv_pi42(*allm, cv=cv, cap=float(cap), allow=allow)
        ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
        XV[cap] = mv
        OUT[f'xv_{cap}'] = dict(net=r['net'], t=r['t'], entered=r['entered'], skipped=r['skipped'], mean=float(mv.mean()))
        if cap % 100 == 0 or cap == 550:
            print(f"   ${cap:<6}  {100 * r['net']:+6.1f}%  {r['t']:5.2f}    {r['entered']:5d}    {r['skipped']:5d}      "
                  f"{100 * mv.mean():+5.2f}%      {100 * mv.min():+5.2f}%")
    rb = S.O.xv_contracts(*allm, cv=cv, cap=550.0, cost_mult=5, allow=liq & same)
    print(f"   (the same at $550 with Binance's coins and fees: {100 * rb['net']:+.1f}%/yr)")

    print(f"\n3. EVERY SPLIT OF ${TOTAL} (book + Delta-vs-Pi42 + reserve), 20,000 YEARS, AFTER TAX (one speculative business)")
    print("   avg = the median year's monthly average on the whole $600 after tax; P2/P4 = P(a year averages >= 2%/4% a month)")
    n = 20000
    rng = np.random.default_rng(11)

    def blocks(L):
        idx = np.empty((n, 12), int)
        for r_ in range(n):
            row = []
            while len(row) < 12:
                s0 = rng.integers(0, L - 2); row += [s0, s0 + 1, s0 + 2]
            idx[r_] = row[:12]
        return idx
    _bl = {}

    def blk(L):
        if L not in _bl:
            _bl[L] = blocks(L)
        return _bl[L]
    rows = {}
    for scen in ('planning', 'pessimistic'):
        print(f"\n   {scen.upper()}" + (" (the cross-venue edge halved again)" if scen == 'pessimistic' else ''))
        print("   reserve  book  xvenue |  0% (<= Rs 12L): avg   P2   P4 | 15.6%: avg   P2   P4 | 31.2%: avg   P2   P4 |"
              " bad year  losing yr  worst month  P($50+/month)")
        for R in (50, 0):
            for b in [0] + list(range(100, TOTAL - R + 1, 50)):        # under $100 the book holds almost nothing
                x_ = TOTAL - R - b
                hb = BK[b] - BK[b].mean() / 3.0 if b else np.zeros(len(BK[600]))
                hx = XV[x_] if x_ else np.zeros(len(XV[600]))
                if scen == 'pessimistic' and x_:
                    hx = hx - hx.mean() / 2.0
                IB, IX = blk(len(hb)), blk(len(hx))
                Mb, Mx = hb[IB], hx[IX]
                Gb, Gx = np.prod(1 + Mb, axis=1), np.prod(1 + Mx, axis=1)
                prof = b * (Gb - 1) + x_ * (Gx - 1)
                cells = []
                for t in (0.0, 0.156, 0.312):
                    g = (TOTAL + prof - np.maximum(0.0, prof) * t) / TOTAL
                    cells.append((float(np.median(g) ** (1 / 12) - 1), float((g >= 1.02 ** 12).mean()),
                                  float((g >= 1.04 ** 12).mean()), float((g >= 1 + 50 * 12 / TOTAL).mean())))
                vb = b * np.cumprod(1 + Mb, axis=1); vx = x_ * np.cumprod(1 + Mx, axis=1)
                tot = np.hstack([np.full((n, 1), float(TOTAL)), vb + vx + R])
                mon = tot[:, 1:] / tot[:, :-1] - 1
                pre = tot[:, -1] / TOTAL
                r_ = dict(cells=cells, bad=float(np.percentile(pre, 10) ** (1 / 12) - 1), plose=float((pre < 1).mean()),
                          w5=float(np.percentile(mon, 5)))
                rows[f"{scen}|{R}|{b}|{x_}"] = r_
                if b % 100 == 0 or b in (50, 150, 550, 600) or x_ == 0:
                    print(f"   ${R:<6} ${b:<4} ${x_:<5}|" + "|".join(f"     {100 * c[0]:+5.2f}% {100 * c[1]:3.0f}% {100 * c[2]:3.0f}% "
                                                                for c in cells)
                          + f"| {100 * r_['bad']:+5.2f}%    {100 * r_['plose']:3.0f}%      {100 * r_['w5']:+5.1f}%"
                          f"        {100 * cells[1][3]:3.0f}%")
    OUT['splits'] = rows
    print("\n   P($50+/month) = P(a year's after-tax gain >= $600 = 8.3% a month), at the 15.6% slab")

    print("\n4. THE TWO RUPEE ACCOUNTS (Delta / Pi42), whole contracts, ALL harder, daily closes")
    print("   capital  re-balance                     lowest side ever  months a side < 65%  < 50%   transfers/yr")
    old = X.COST_B
    X.COST_B = COST_PI42
    try:
        for cap in (400, 450, 550):
            for trig, lab in ((None, 'monthly only'), (0.65, 'monthly + when a side < 65%')):
                r = S.sides(allm, float(cap), cv, trigger=trig, allow=allow)
                OUT[f'sides_{cap}_{trig}'] = r
                print(f"   ${cap:<6}  {lab:30}     {100 * r['low_side']:5.1f}%            {100 * r['months_lt65']:4.0f}%          "
                      f"{100 * r['months_lt50']:3.0f}%       {r['transfers_yr']:5.1f}")
    finally:
        X.COST_B = old
    json.dump(OUT, open(os.path.join(HERE, 'c532_india_only.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
