#!/usr/bin/env python3
"""C531 (descriptive planning, no new rule): $600 in total, no reserve -- how to split it between the
book on Delta India and the Delta-vs-Binance cross-venue trade for the highest average month.

    python3 research/c531_split_600.py BNC_DIR XV_CACHE

Corrections to the C528/C530 planning, both made here:
  * the book on Delta holds WHOLE Delta contracts at its own size: q = round(w x equity / (contract value x
    price)), nothing under one contract or the $6 floor, nothing not listed on Delta -- the bot's own rule
    (C521Delta.rebalance). C528/C530 used Binance's minimums.
  * the book on Delta earns NO Savings on its idle cash: it sits in the Delta account. C528/C530 added
    Binance Savings to it (~0.3%/month too much).
Parts, from the research's own simulators:
  BOOK    the traded rule (N2+N3, GK volatility, dial 20%, top 20), whole Delta contracts at its size, Delta's
          costs (0.05% + 18% GST + 0.02%), Delta's extra funding (-3.72%/yr, C528); planning: mean cut by 1/3
  XVENUE  round 15's X1 on the ALL-harder history (midnight timing, Delta's mark, costs x5, $100k Delta turnover,
          the same asset), whole Delta contracts at its own size (research/c530_plan_odds.py)
Paths: 20,000 years of 3-month blocks, the book's whole history (2020-02 -> 2026-08) and the cross-venue months
drawn independently (overlap correlation -0.02, C528). Pessimistic: the cross-venue mean halved again.
Tax: (A) both parts business income, a year's NET profit at the slab, a loss untaxed; (B) the cross-venue
trade's Binance leg a VDA (31.2% of each winning leg, losses ignored; research/c528_budget_plan.xv_mixed) --
modelled as that history's average tax drag, paid whatever the year.
No reserve: the cross-venue trade's two accounts re-balanced (a) monthly, (b) whenever a side is below 65% of
its half at a daily close (moved the next day, $1 a transfer): the lowest a side reached, the transfers a year.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c528_budget_plan as P
import c524_xvenue as X
import c530_plan_odds as O

TOTAL = 600
DRAG = 0.0372
COST_DELTA = 0.0005 * 1.18 + 0.0002
OUT = {}


def delta_cv():
    raw = requests.get(X.DELTA + '/v2/products', params=dict(contract_types='perpetual_futures', states='live'),
                       timeout=30).json()['result']
    return {p['underlying_asset']['symbol']: float(p.get('contract_value') or 0) for p in raw
            if (p.get('settling_asset') or {}).get('symbol') == 'USD'}


def book_on_delta(D, Wc, cv, eq):
    """the book's weights held in whole Delta contracts at `eq`: daily returns and the share of the plan held"""
    om = P.B.om
    syms = D['syms']
    cn_unit = np.zeros(len(syms))                     # contract value in the Binance symbol's price units
    for j, s in enumerate(syms):
        c = s[:-4]
        if c in cv and cv[c] > 0:
            cn_unit[j] = cv[c]
        elif c.startswith('1000') and c[4:] in cv and cv[c[4:]] > 0:
            cn_unit[j] = cv[c[4:]] / 1000.0
    px = D['c']
    cn = cn_unit[None, :] * px
    with np.errstate(invalid='ignore', divide='ignore'):
        q = np.where(cn > 0, np.round(np.abs(Wc) * eq / cn), 0.0)
        q = np.where(np.isfinite(q), q, 0.0)
        Wr = np.sign(Wc) * q * np.nan_to_num(cn) / eq
    Wr = np.where(np.abs(Wc) * eq >= 6.0, Wr, 0.0)
    x, _ = om._c488_pnl(Wr, D['r'], D['fund'], 1, cost=COST_DELTA)
    g_full, g_held = np.abs(Wc).sum(1), np.abs(Wr).sum(1)
    x = x - DRAG / 365.0 * np.where(g_full > 0, g_held / np.maximum(g_full, 1e-12), 0.0)
    on = g_full > 0
    held = float(np.mean(g_held[on] / g_full[on])) if on.any() else 0.0
    ncoins = float(np.mean((np.abs(Wr[on]) > 0).sum(1)))
    xs, Ts = P.B.returns_of(x, D)
    return xs, Ts, held, ncoins


def sides(allm, cap, cv, trigger=None, cost_mult=5.0, allow=None):
    """X1 in whole contracts with each venue's legs apart; the two accounts re-balanced monthly, or also
    whenever a side is under `trigger` of its half at a daily close (moved the next day, $1 each)"""
    Dd, names, fD, fB, pD, pB = allm
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(Dd)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = X.COST_B * cost_mult, X.COST_D * cost_mult
    held, size = {}, {}
    sd, sb = cap / 2.0, cap / 2.0
    cur, pend, transfers, low, lows_m = None, False, 0, 1.0, {}
    for i in range(len(Dd) - 1):
        m = dt.datetime.utcfromtimestamp(int(Dd[i + 1])).strftime('%Y-%m')
        tot = sd + sb
        if i + 1 >= X.WIN and (m != cur or pend):
            if pend:
                transfers += 1
                tot -= 1.0                                     # a transfer's cost
            sd = sb = tot / 2.0
            cur, pend = m, False
        sig = s7[i]
        for j in list(held):
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != held[j]:
                sb -= size[j] * cB; sd -= size[j] * cD
                del held[j], size[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        room = X.MAXP - len(held)
        eqn = sd + sb
        for j in cand:
            if room <= 0:
                break
            px = pD[i, j] if not np.isnan(pD[i, j]) else pD[i + 1, j]
            c_ = cv.get(names[j])
            if not c_ or not np.isfinite(px) or px <= 0:
                continue
            kq = int(round(X.SIZE * eqn / (c_ * px)))
            if kq < 1:
                continue
            held[j] = int(np.sign(sig[j])); size[j] = kq * c_ * px
            sb -= size[j] * cB; sd -= size[j] * cD
            room -= 1
        for j, side in held.items():
            if ok[i + 1, j]:
                sb += size[j] * side * (rB[i + 1, j] - fB[i + 1, j])
                sd += size[j] * side * (fD[i + 1, j] - rD[i + 1, j])
        if i + 1 >= X.WIN:
            half = (sd + sb) / 2.0
            f = min(sd, sb) / half if half > 0 else 0.0
            low = min(low, min(sd, sb) / (cap / 2.0))
            lows_m[m] = min(lows_m.get(m, 9.0), f)
            if trigger is not None and f < trigger:
                pend = True
    lm = np.array(list(lows_m.values()))
    yrs = (Dd[-1] - Dd[X.WIN]) / 86400 / 365
    return dict(end=(sd + sb) / cap, low_side=float(low), months_lt65=float((lm < 0.65).mean()),
                months_lt50=float((lm < 0.50).mean()), worst_month_side=float(lm.min()), transfers_yr=transfers / yrs)


def main(bdir, cache):
    print(f"C531: ${TOTAL} IN TOTAL, NO RESERVE -- THE BOOK ON DELTA vs THE CROSS-VENUE TRADE\n")
    with contextlib.redirect_stdout(io.StringIO()):
        D = P.B.prep(bdir)
    om = P.B.om
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    P.B.EQ, P.B.TV = 1e9, 0.20 * 4 / 3                      # the plan's raw weights; Delta's contracts applied below
    W = P.B.sleeves(D, sd=sdgk, topn=20)
    _, Wc, _ = P.B.book(D, W)
    cv = delta_cv()
    print("1. THE BOOK ON DELTA INDIA, IN WHOLE DELTA CONTRACTS, NO SAVINGS ON ITS IDLE CASH, 2020-02 -> 2026-08")
    print("   (backtested; the planning case cuts the mean by 1/3)")
    print("   size   plan held   coins held   avg/month   planning   months<0   worst month")
    BK = {}
    xb5, Tb5 = P.book_series(D, sdgk, 500)                  # C528/C530's series, for the correction's size
    m5 = P.months_of(Tb5, xb5); k5 = sorted(m5)[1:]
    old = np.array([m5[k] for k in k5])
    for eq in (100, 200, 300, 400, 500, 600):
        xs, Ts, held, nc = book_on_delta(D, Wc, cv, eq)
        mm = P.months_of(Ts, xs); kk = sorted(mm)[1:]
        mv = np.array([mm[k] for k in kk])
        BK[eq] = (kk, mv)
        OUT[f'book_{eq}'] = dict(held=held, coins=nc, mean=float(mv.mean()), planning=float(mv.mean() * 2 / 3),
                                 pneg=float((mv < 0).mean()), worst=float(mv.min()))
        print(f"   ${eq:<5}   {100 * held:5.1f}%      {nc:5.1f}       {100 * mv.mean():+5.2f}%     {100 * mv.mean() * 2 / 3:+5.2f}%"
              f"      {100 * (mv < 0).mean():3.0f}%      {100 * mv.min():+6.1f}%")
    print(f"   C528/C530 used, at $500: {100 * old.mean():+.2f}%/month backtested ({100 * (old.mean() * 2 / 3 - DRAG / 12):+.2f}% "
          f"planning after the Delta drag) -- Binance's minimums and Savings on idle cash")

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
        mm_ = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if mm_.sum() > 60 and np.corrcoef(rD[mm_, j], rB[mm_, j])[0, 1] >= 0.9:
            same.add(c)
    print("\n2. THE CROSS-VENUE TRADE IN WHOLE DELTA CONTRACTS (ALL harder), 2024-10 -> 2026-09")
    print("   capital   net/yr     t     entries  skipped   avg/month   worst month")
    XV = {}
    for cap in (100, 200, 300, 400, 500, 600):
        r = O.xv_contracts(*allm, cv=cv, cap=float(cap), cost_mult=5, allow=liq & same)
        ks = sorted(r['months']); mv = np.array([r['months'][k] for k in ks])
        XV[cap] = (ks, mv)
        OUT[f'xv_{cap}'] = dict(net=r['net'], t=r['t'], entered=r['entered'], skipped=r['skipped'],
                                mean=float(mv.mean()), worst=float(mv.min()))
        print(f"   ${cap:<6}  {100 * r['net']:+6.1f}%  {r['t']:5.2f}    {r['entered']:5d}    {r['skipped']:5d}      "
              f"{100 * mv.mean():+5.2f}%      {100 * mv.min():+5.2f}%")
    vda = {}
    for tb in (0.104, 0.312):
        pre, aft = P.xv_mixed(*allm, tb, cost_mult=5, allow=liq & same)
        vda[tb] = pre - aft
    OUT['vda_drag'] = vda
    print(f"   if its Binance leg is a VDA (each winning leg taxed 31.2%, losses ignored): a tax drag of "
          f"{100 * vda[0.104]:.1f}%/yr (Delta leg at 10.4%) / {100 * vda[0.312]:.1f}%/yr (at 31.2%) on its capital")

    print(f"\n3. EVERY SPLIT OF ${TOTAL}: 20,000 YEARS (3-month blocks), AFTER TAX ON PROFITS ONLY")
    print("   avg = the median year's monthly average after tax; P2 / P4 = P(a year averages >= 2% / >= 4% a month)")
    print("   tax B: the VDA tax on the Binance leg grows with the trade, so it is taken off each month "
          "(its history's drag / 12), with the Delta leg's business tax inside it")
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
    rows, robust = {}, {}
    scens = (('planning', 'A', 'PLANNING, tax A (both business income)'),
             ('planning', 'B', "PLANNING, tax B (the cross-venue trade's Binance leg a VDA)"),
             ('pessimistic', 'A', 'PESSIMISTIC (the cross-venue edge halved again), tax A'),
             ('pessimistic', 'B', 'PESSIMISTIC, tax B'))
    for scen, taxr, title in scens:
        print(f"\n   {title}")
        print("   book  xvenue |  slab 10.4%: avg    P2    P4  |  slab 31.2%: avg    P2    P4  | bad year (1 in 10)  losing year  worst month (1 in 20)")
        for b in range(0, TOTAL + 1, 100):
            x_ = TOTAL - b
            hb = BK[b][1] - BK[b][1].mean() / 3.0 if b else np.zeros(len(BK[600][1]))
            hx = XV[x_][1] if x_ else np.zeros(len(XV[600][1]))
            IB, IX = blk(len(hb)), blk(len(hx))
            if scen == 'pessimistic' and x_:
                hx = hx - hx.mean() / 2.0
            Mb = hb[IB]; Gb = np.prod(1 + Mb, axis=1)
            cells = []
            for t in (0.104, 0.312):
                hxt = hx - (vda[t] / 12.0 if (taxr == 'B' and x_) else 0.0)
                Mx = hxt[IX]; Gx = np.prod(1 + Mx, axis=1)
                if taxr == 'A':
                    prof = b * (Gb - 1) + x_ * (Gx - 1)
                    end = TOTAL + prof - np.maximum(0.0, prof) * t
                else:
                    pb_ = b * (Gb - 1)
                    end = TOTAL + pb_ - np.maximum(0.0, pb_) * t + x_ * (Gx - 1)
                g = end / TOTAL
                cells.append((float(np.median(g) ** (1 / 12) - 1), float((g >= 1.02 ** 12).mean()),
                              float((g >= 1.04 ** 12).mean()), float(g.mean() ** (1 / 12) - 1)))
            Mx0 = hx[IX]
            vb = b * np.cumprod(1 + Mb, axis=1); vx = x_ * np.cumprod(1 + Mx0, axis=1)
            tot = np.hstack([np.full((n, 1), float(TOTAL)), vb + vx])
            mon = tot[:, 1:] / tot[:, :-1] - 1
            pre = tot[:, -1] / TOTAL
            bad = float(np.percentile(pre, 10) ** (1 / 12) - 1)
            plose = float((pre < 1).mean())
            w5 = float(np.percentile(mon, 5))
            rows[f"{scen}|{taxr}|{b}|{x_}"] = dict(cells=cells, bad=bad, plose=plose, w5=w5)
            for k_, t in enumerate((0.104, 0.312)):
                robust.setdefault((b, t), []).append(cells[k_][0])
            print(f"   ${b:<4} ${x_:<5}|        {100 * cells[0][0]:+5.2f}%  {100 * cells[0][1]:3.0f}%  {100 * cells[0][2]:3.0f}%  |"
                  f"        {100 * cells[1][0]:+5.2f}%  {100 * cells[1][1]:3.0f}%  {100 * cells[1][2]:3.0f}%  |"
                  f"      {100 * bad:+5.2f}%          {100 * plose:3.0f}%          {100 * w5:+5.1f}%")
    OUT['splits'] = rows
    print("\n   THE FOUR CASES TOGETHER (equal weight): the median year's monthly average after tax, and the worst of the four")
    print("   book  xvenue |  slab 10.4%: average  worst case  |  slab 31.2%: average  worst case")
    rob = {}
    for b in range(0, TOTAL + 1, 100):
        a1, a3 = robust[(b, 0.104)], robust[(b, 0.312)]
        rob[b] = dict(avg104=float(np.mean(a1)), min104=float(min(a1)), avg312=float(np.mean(a3)), min312=float(min(a3)))
        print(f"   ${b:<4} ${TOTAL - b:<5}|           {100 * np.mean(a1):+5.2f}%     {100 * min(a1):+5.2f}%   |"
              f"           {100 * np.mean(a3):+5.2f}%     {100 * min(a3):+5.2f}%")
    OUT['robust'] = rob

    print("\n4. NO RESERVE: THE CROSS-VENUE TRADE'S TWO ACCOUNTS (whole contracts, ALL harder, daily closes)")
    print("   capital  re-balance                     lowest side ever  months a side < 65%  < 50%   transfers/yr   end value")
    for cap in (300, 400, 600):
        for trig, lab in ((None, 'monthly only'), (0.65, 'monthly + when a side < 65%')):
            r = sides(allm, float(cap), cv, trigger=trig, allow=liq & same)
            OUT[f'sides_{cap}_{trig}'] = r
            print(f"   ${cap:<6}  {lab:30}     {100 * r['low_side']:5.1f}%            {100 * r['months_lt65']:4.0f}%          "
                  f"{100 * r['months_lt50']:3.0f}%       {r['transfers_yr']:5.1f}        x{r['end']:.2f}")
    json.dump(OUT, open(os.path.join(HERE, 'c531_split_600.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
