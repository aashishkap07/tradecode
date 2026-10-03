#!/usr/bin/env python3
"""C528 (descriptive planning, no new strategy): how to split a $1,000 budget (at most $1,200) between
the book and the Delta-vs-Binance funding trade, judged on real history, month by month.

    python3 research/c528_budget_plan.py BNC_DIR XV_CACHE

Parts, both from the research's own simulators (no new rule, no parameter chosen here):
  BOOK   the traded rule: N2+N3 with range-based (GK) coin volatility, dial 20% (vol target 26.7%),
         top 20, Binance costs (0.07%/turnover) and minimums at the account's own size
         (research/omega_c521_research.py: the bot's own functions). Idle cash earns Binance
         Savings 6.69% on equity - margin (gross / 5) - the month budget (20%) - 5%, as C501Savings.
  XVENUE round 15's X1 rule unchanged (research/c524_xvenue.py): as pre-registered, and with every
         assumption made harder at once ("ALL": timing + Delta's mark + costs x5 + liquidity + identity).
Accounts compound separately (no transfers); the total's month is the change in their sum.
Scenarios:
  backtested   both as simulated
  planning     the book's mean cut by 1/3 (the PBO haircut); the cross-venue trade's "ALL" series
  pessimistic  planning, and the cross-venue trade's mean halved again (the live edge at half)
Tax: pre-tax figures; read A (31.2% of each Indian financial year's net profit) applied to the
average; read B (s.115BBH strict: each gain taxed, losses ignored) per closed position/leg.
"""
import os, sys, io, json, math, contextlib, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import omega_c521_research as B
import c524_xvenue as X

SAV, TAXA = 0.0669, 0.312
OUT = {}


def months_of(T_ms, x):
    m = {}
    for t, v in zip(T_ms, x):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m')
        m[k] = (1 + m.get(k, 0.0)) * (1 + v) - 1
    return m


def book_series(D, sdgk, eq, tv=0.20 * 4 / 3, topn=20):
    B.EQ, B.TV = eq, tv
    W = B.sleeves(D, sd=sdgk, topn=topn)
    x, Wc, _ = B.book(D, W)
    gross = np.abs(Wc).sum(1)
    idle = np.clip(1 - gross / 5.0 - 0.20 - 0.05, 0, 1)
    x = x + np.r_[0.0, idle[:-1]] * SAV / 365.0          # yesterday's idle cash earns today
    xs, Ts = B.returns_of(x, D)
    return xs, Ts


def stats_m(mv):
    mv = np.asarray(mv)
    eq = np.cumprod(1 + mv)
    return dict(mean=float(mv.mean()), median=float(np.median(mv)), geo=float(eq[-1] ** (1 / len(mv)) - 1),
                p2=float((mv >= 0.02).mean()), p4=float((mv >= 0.04).mean()), pneg=float((mv < 0).mean()),
                worst=float(mv.min()), best=float(mv.max()), maxdd=float((1 - eq / np.maximum.accumulate(eq)).max()),
                n=len(mv))


def boot12(mb, mx, wb, wx, n=20000, block=3, seed=7):
    """P(12 months average >= 2%/month): 3-month blocks of joint months, accounts compounding apart"""
    rng = np.random.default_rng(seed)
    k = len(mb); hits = 0; res = []
    for _ in range(n):
        idx = []
        while len(idx) < 12:
            s = rng.integers(0, k - block + 1)
            idx += list(range(s, s + block))
        idx = idx[:12]
        b, x_ = wb, wx
        for i in idx:
            b *= 1 + mb[i]; x_ *= 1 + mx[i]
        tot = (b + x_) / (wb + wx)
        res.append(tot)
        hits += tot >= 1.02 ** 12
    res = np.array(res)
    return hits / n, float(np.median(res) ** (1 / 12) - 1), float(np.percentile(res, 10) ** (1 / 12) - 1)


def xv_taxB(Dd, names, fD, fB, pD, pB, cost_mult=1.0, allow=None):
    """the X1 loop again, keeping each leg's own P&L (its funding + its price + its costs) from entry
    to exit; read B taxes every positive leg at 31.2% when the pair closes (and at the end)"""
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
            nn = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(nn >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = X.COST_B * cost_mult, X.COST_D * cost_mult
    held, legs = {}, {}
    pre = taxed = 0.0
    tax_m = {}

    def close(j, i):
        nonlocal taxed
        lb, ld = legs.pop(j)
        t = TAXA * (max(lb, 0.0) + max(ld, 0.0))
        taxed += t
        m = dt.datetime.utcfromtimestamp(int(Dd[min(i + 1, len(Dd) - 1)])).strftime('%Y-%m')
        tax_m[m] = tax_m.get(m, 0.0) + t
    for i in range(len(Dd) - 1):
        sig = s7[i]
        for j in list(held):
            side = held[j]
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != side:
                legs[j][0] -= X.SIZE * cB; legs[j][1] -= X.SIZE * cD
                pre -= X.SIZE * (cB + cD)
                del held[j]; close(j, i)
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        for j in cand[:max(0, X.MAXP - len(held))]:
            held[j] = int(np.sign(sig[j])); legs[j] = [-X.SIZE * cB, -X.SIZE * cD]
            pre -= X.SIZE * (cB + cD)
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            lb = X.SIZE * side * (rB[i + 1, j] - fB[i + 1, j])         # long Binance when side = +1: pays its funding
            ld = X.SIZE * side * (fD[i + 1, j] - rD[i + 1, j])         # short Delta when side = +1: receives Delta's
            legs[j][0] += lb; legs[j][1] += ld
            pre += lb + ld
    for j in list(held):
        close(j, len(Dd) - 2)
    yrs = (Dd[-1] - Dd[X.WIN]) / 86400 / 365
    return pre / yrs, (pre - taxed) / yrs, tax_m


def xv_mixed(Dd, names, fD, fB, pD, pB, t_bus, cost_mult=1.0, allow=None):
    """the X1 loop with each leg's P&L kept apart. The Binance (USDT-settled) leg taxed as a VDA:
    31.2% of every positive pair-leg, losses ignored. The Delta (INR-settled) leg as business income:
    netted over each Indian financial year (Apr-Mar), losses carried forward, the profit taxed at t_bus."""
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
            nn = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(nn >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = X.COST_B * cost_mult, X.COST_D * cost_mult
    held, legB = {}, {}
    pre = taxB = 0.0
    fy = {}                                                    # Indian financial year -> Delta legs' net

    def fy_of(i):
        d = dt.datetime.utcfromtimestamp(int(Dd[i]))
        return d.year if d.month >= 4 else d.year - 1
    for i in range(len(Dd) - 1):
        sig = s7[i]
        for j in list(held):
            side = held[j]
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != side:
                legB[j] -= X.SIZE * cB; fy[fy_of(i + 1)] = fy.get(fy_of(i + 1), 0.0) - X.SIZE * cD
                pre -= X.SIZE * (cB + cD)
                taxB += TAXA * max(legB.pop(j), 0.0)
                del held[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        for j in cand[:max(0, X.MAXP - len(held))]:
            held[j] = int(np.sign(sig[j])); legB[j] = -X.SIZE * cB
            fy[fy_of(i + 1)] = fy.get(fy_of(i + 1), 0.0) - X.SIZE * cD
            pre -= X.SIZE * (cB + cD)
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            lb = X.SIZE * side * (rB[i + 1, j] - fB[i + 1, j])
            ld = X.SIZE * side * (fD[i + 1, j] - rD[i + 1, j])
            legB[j] += lb
            fy[fy_of(i + 1)] = fy.get(fy_of(i + 1), 0.0) + ld
            pre += lb + ld
    for j in list(held):
        taxB += TAXA * max(legB.pop(j), 0.0)
    carry, taxD = 0.0, 0.0
    for y in sorted(fy):
        net = fy[y] + carry
        if net > 0:
            taxD += t_bus * net; carry = 0.0
        else:
            carry = net
    yrs = (Dd[-1] - Dd[X.WIN]) / 86400 / 365
    return pre / yrs, (pre - taxB - taxD) / yrs


def main(bdir, cache):
    print("C528: A $1,000 BUDGET (AT MOST $1,200), ON REAL HISTORY\n")
    with contextlib.redirect_stdout(io.StringIO()):
        D = B.prep(bdir)
    om = B.om
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    print(f"book data: {len(D['syms'])} coins, {dt.datetime.utcfromtimestamp(D['T'][0] / 1000).date()} -> "
          f"{dt.datetime.utcfromtimestamp(D['T'][-1] / 1000).date()}")

    # ── the book at each size ───────────────────────────────────────────────
    print("\n1. THE BOOK ALONE (traded rule, dial 20%, top 20, Binance minimums, idle cash in Savings), 2020-26")
    print("   size     avg/month  median  geo/month  months>=2%  months<0  worst   max DD")
    BK = {}
    for eq in (500, 700, 1000, 1200):
        xs, Ts = book_series(D, sdgk, eq)
        BK[eq] = (xs, Ts)
        mm = months_of(Ts, xs)
        keys = sorted(mm)[1:]                                           # the first month is partial
        s = stats_m([mm[k] for k in keys])
        OUT[f'book_{eq}'] = s
        print(f"   ${eq:<6}  {100 * s['mean']:+6.2f}%   {100 * s['median']:+6.2f}%   {100 * s['geo']:+6.2f}%     "
              f"{100 * s['p2']:4.0f}%       {100 * s['pneg']:4.0f}%   {100 * s['worst']:+6.1f}%  {100 * s['maxdd']:5.1f}%")
    # what the bot would do at $1,000 unprompted: C488_TOPN 'auto' widens to 40 from $1,000
    with contextlib.redirect_stdout(io.StringIO()):
        for tn in (40,):
            D['elig'][tn] = om._c488_universe(D['c'], D['qv'], tn)
            D['beta'][tn] = B.beta_mkt(D['c'], D['r'], D['elig'][tn])
    x40, T40 = book_series(D, sdgk, 1000, topn=40)
    m40 = months_of(T40, x40); k40 = sorted(m40)[1:]
    s40 = stats_m([m40[k] for k in k40 if k < '2026-10'])
    OUT['book_1000_top40'] = s40
    print(f"   $1000 top 40 (the 'auto' width at $1,000): avg {100 * s40['mean']:+.2f}%/month, geo {100 * s40['geo']:+.2f}%, "
          f"max DD {100 * s40['maxdd']:.1f}% -> set C488_TOPN = 20")
    xh, Th = book_series(D, sdgk, 1000, tv=0.30 * 4 / 3)
    mh = months_of(Th, xh); kh = sorted(mh)[1:]
    sh = stats_m([mh[k] for k in kh if k < '2026-10'])
    OUT['book_1000_dial30'] = sh
    print(f"   $1000 at dial 30% (vol target 40%, what-if): avg {100 * sh['mean']:+.2f}%/month, months<0 {100 * sh['pneg']:.0f}%, "
          f"worst {100 * sh['worst']:+.1f}%, max DD {100 * sh['maxdd']:.1f}%")

    # ── the cross-venue trade ───────────────────────────────────────────────
    prods, res = X.load(cache)
    base = X.matrices(prods, res)
    Dd, names, fD, fB, pD, pB = base
    import requests
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    same = set()
    for j, c in enumerate(names):
        m = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m.sum() > 60 and np.corrcoef(rD[m, j], rB[m, j])[0, 1] >= 0.9:
            same.add(c)
    xa = X.simulate(*base, verbose=False)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    xs_ = X.simulate(*allm, verbose=False, cost_mult=5, allow=liq & same)
    print("\n2. THE CROSS-VENUE TRADE ALONE, 2024-10 -> 2026-09 (on its own capital, both venues)")
    for tag, r in (('as pre-registered', xa), ('ALL harder at once', xs_)):
        s = stats_m([r['months'][k] for k in sorted(r['months'])])
        OUT['xv_' + tag] = s
        print(f"   {tag:20} avg {100 * s['mean']:+.2f}%/month, months>=2% {100 * s['p2']:.0f}%, months<0 {100 * s['pneg']:.0f}%, "
              f"worst {100 * s['worst']:+.2f}%, max DD {100 * s['maxdd']:.1f}%")
    pa, pt, _ = xv_taxB(*base)
    pa2, pt2, _ = xv_taxB(*allm, cost_mult=5, allow=liq & same)
    OUT['xv_taxB'] = dict(pre=pa, after=pt, pre_all=pa2, after_all=pt2)
    print(f"   tax read B (each leg's gain taxed 31.2%, its losses ignored): pre-registered {100 * pa:+.1f}%/yr -> {100 * pt:+.1f}%/yr; "
          f"ALL {100 * pa2:+.1f}%/yr -> {100 * pt2:+.1f}%/yr")

    # ── the splits ──────────────────────────────────────────────────────────
    bm_all = months_of(*BK[500][::-1])
    months = sorted(k for k in xa['months'] if k in bm_all)            # the book's data ends 2026-08-31
    print(f"\n3. SPLITS OF THE BUDGET, the {len(months)} months both exist ({months[0]} -> {months[-1]}), accounts compounding apart")
    splits = [(1000, 0), (700, 300), (500, 500), (400, 600), (0, 1000), (600, 600), (500, 700), (1200, 0)]
    rows = {}
    for scen in ('backtested', 'planning', 'pessimistic'):
        print(f"\n   {scen.upper()}" + {'backtested': ': both as simulated',
                                        'planning': ': book mean cut by 1/3; cross-venue = the ALL-harder series',
                                        'pessimistic': ': planning, and the cross-venue mean halved again'}[scen])
        print("   book  xvenue  total |  avg/month  median  months>=2%  months<0  worst   max DD | P(12-mo avg >= 2%)  12-mo median  bad year (10%)")
        for wb, wx in splits:
            bsz = wb if wb in BK else 500
            xb_, Tb_ = BK.get(bsz, BK[500])
            if scen != 'backtested':
                xb_ = xb_ - xb_.mean() / 3.0
            mb = months_of(Tb_, xb_)
            xvm = (xa if scen == 'backtested' else xs_)['months']
            mxv = np.array([xvm[k] for k in months])
            if scen == 'pessimistic':
                mxv = mxv - mxv.mean() / 2.0
            mbv = np.array([mb[k] for k in months])
            b, x_ = float(wb), float(wx); tot = [b + x_]
            for i in range(len(months)):
                b *= 1 + mbv[i]; x_ *= 1 + mxv[i]; tot.append(b + x_)
            tot = np.array(tot); mv = tot[1:] / tot[:-1] - 1
            s = stats_m(mv)
            p12, med12, bad12 = boot12(mbv, mxv, wb, wx)
            s.update(p12=p12, med12=med12, bad12=bad12)
            rows[(scen, wb, wx)] = s
            print(f"   ${wb:<4} ${wx:<5} ${wb + wx:<5}| {100 * s['mean']:+6.2f}%  {100 * s['median']:+6.2f}%     {100 * s['p2']:3.0f}%      "
                  f"{100 * s['pneg']:3.0f}%   {100 * s['worst']:+6.1f}%  {100 * s['maxdd']:5.1f}% |      {100 * p12:3.0f}%            "
                  f"{100 * med12:+5.2f}%        {100 * bad12:+5.2f}%")
    OUT['splits'] = {f"{a}|{b}|{c}": v for (a, b, c), v in rows.items()}

    # ── 4. the book's FULL history (2022's bear market included) with the cross-venue months ──
    bfull = months_of(*BK[500][::-1]); kb = sorted(bfull)[1:]
    mbF = np.array([bfull[k] for k in kb])
    mbO = np.array([bfull[k] for k in months]); mxO = np.array([xs_['months'][k] for k in months])
    rho = float(np.corrcoef(mbO, mxO)[0, 1])
    OUT['rho_overlap'] = rho
    print(f"\n4. THE BOOK'S WHOLE HISTORY ({kb[0]} -> {kb[-1]}, {len(kb)} months, 2022's -28% year included) WITH THE "
          f"CROSS-VENUE MONTHS,\n   drawn independently (their monthly correlation over the overlap: {rho:+.2f}); "
          f"12-month paths, 3-month blocks, 20,000 draws")
    print("   after tax A: a year's profit keeps 68.8%, so averaging 2%/month after tax needs +38.9% pre-tax (2.78%/month)")
    print("   (S$500 = the other $500 in Savings at 6.69%, the fallback if the cross-venue trade fails its paper trial)")
    print("   book  xvenue |   12-mo median   bad year (10%)  P(losing year)  P(avg>=2% pre-tax)  P(avg>=2% after tax A)  worst month (5%)")
    rng = np.random.default_rng(11)
    full = {}
    for scen in ('planning', 'pessimistic'):
        print(f"   {scen.upper()}")
        hb = mbF - mbF.mean() / 3.0
        hx = mxO - (mxO.mean() / 2.0 if scen == 'pessimistic' else 0.0)
        hxa = np.array([xs_['months'][k] for k in sorted(xs_['months'])])
        hxa = hxa - (hxa.mean() / 2.0 if scen == 'pessimistic' else 0.0)
        for wb, wx in ((1000, 0), (700, 300), (500, 500), (400, 600), (0, 1000), (500, -500)):
            sav = wx < 0                                   # the fallback: the other $500 in Savings, not the trade
            wx = abs(wx)
            G, W = [], []
            for _ in range(20000):
                ib = []; ix = []
                while len(ib) < 12:
                    s0 = rng.integers(0, len(hb) - 2); ib += [s0, s0 + 1, s0 + 2]
                while len(ix) < 12:
                    s1 = rng.integers(0, len(hxa) - 2); ix += [s1, s1 + 1, s1 + 2]
                b_, x_ = float(wb), float(wx); prev = b_ + x_
                for i, j in zip(ib[:12], ix[:12]):
                    b_ *= 1 + hb[i]; x_ *= 1 + (SAV / 12 if sav else hxa[j])
                    W.append((b_ + x_) / prev - 1); prev = b_ + x_
                G.append((b_ + x_) / (wb + wx))
            G = np.array(G); W = np.array(W)
            r_ = dict(med=float(np.median(G) ** (1 / 12) - 1), bad=float(np.percentile(G, 10) ** (1 / 12) - 1),
                      plose=float((G < 1).mean()), p2=float((G >= 1.02 ** 12).mean()),
                      p2tax=float((G >= 1 + (1.02 ** 12 - 1) / (1 - TAXA)).mean()), w5=float(np.percentile(W, 5)))
            full[f"{scen}|{wb}|{'savings' if sav else wx}"] = r_
            print(f"   ${wb:<4} {('S$' if sav else '$') + str(wx):<6}|     {100 * r_['med']:+5.2f}%         {100 * r_['bad']:+5.2f}%          {100 * r_['plose']:3.0f}%"
                  f"              {100 * r_['p2']:3.0f}%                  {100 * r_['p2tax']:3.0f}%                {100 * r_['w5']:+5.1f}%")
    OUT['full_history'] = full

    # ── 5. TAX ON PROFITS ONLY (business income), by slab; and the mixed case ──
    print("\n5. TAX ON PROFITS ONLY: a year's NET profit taxed at the slab rate (+4% cess), a losing year taxed nothing")
    print("   (the business-income treatment; the strongest case is INR-settled futures, i.e. Delta India)")
    print("   the same 20,000 12-month paths as section 4, planning case; after-tax average per month")
    print("   book  xvenue |  rate 0%: median / P(>=2%)   10.4%            20.8%            31.2%            | losing year")
    rng = np.random.default_rng(11)
    hb = mbF - mbF.mean() / 3.0
    hxa = np.array([xs_['months'][k] for k in sorted(xs_['months'])])
    taxtab = {}
    for scen in ('planning', 'pessimistic'):
        hx_ = hxa - (hxa.mean() / 2.0 if scen == 'pessimistic' else 0.0)
        print(f"   {scen.upper()}")
        for wb, wx in ((1000, 0), (500, 500), (0, 1000)):
            G = []
            for _ in range(20000):
                ib = []; ix = []
                while len(ib) < 12:
                    s0 = rng.integers(0, len(hb) - 2); ib += [s0, s0 + 1, s0 + 2]
                while len(ix) < 12:
                    s1 = rng.integers(0, len(hx_) - 2); ix += [s1, s1 + 1, s1 + 2]
                b_, x_ = float(wb), float(wx)
                for i, j in zip(ib[:12], ix[:12]):
                    b_ *= 1 + hb[i]; x_ *= 1 + hx_[j]
                G.append((b_ + x_) / (wb + wx))
            G = np.array(G)
            cells = []
            for t in (0.0, 0.104, 0.208, 0.312):
                Ga = np.where(G > 1, 1 + (G - 1) * (1 - t), G)
                cells.append((float(np.median(Ga) ** (1 / 12) - 1), float((Ga >= 1.02 ** 12).mean())))
            taxtab[f"{scen}|{wb}|{wx}"] = dict(cells=cells, plose=float((G < 1).mean()))
            print(f"   ${wb:<4} ${wx:<5}|  " + "   ".join(f"{100 * m:+5.2f}% / {100 * p:3.0f}%  " for m, p in cells)
                  + f"|   {100 * (G < 1).mean():3.0f}%")
    OUT['tax_profits_only'] = taxtab
    # the book hosted on Delta India: its positions pay Delta's funding instead of Binance's
    col = {sym: j for j, sym in enumerate(D['syms'])}
    idx = {int(t) // 86400000: i for i, t in enumerate(D['T'])}
    B.EQ, B.TV = 500.0, 0.20 * 4 / 3
    Wc5 = B.book(D, B.sleeves(D, sd=sdgk))[1]
    drag = []
    for i, d in enumerate(Dd):
        bi = idx.get(int(d) // 86400)
        if bi is None or bi == 0 or np.abs(Wc5[bi - 1]).sum() == 0:
            continue
        w = Wc5[bi - 1]
        drag.append(sum(w[col[c + 'USDT']] * (fD[i, j] - fB[i, j]) for j, c in enumerate(names)
                        if c + 'USDT' in col and w[col[c + 'USDT']] != 0 and not np.isnan(fD[i, j]) and not np.isnan(fB[i, j])))
    dragy = float(np.mean(drag) * 365)
    OUT['book_on_delta_funding_drag'] = dragy
    print(f"\n   THE BOOK ON DELTA INDIA (INR-settled): its positions' funding on Delta minus on Binance = {100 * dragy:+.2f}%/yr "
          f"(2024-10 -> 2026-08), charged daily")
    hbd = hb - dragy / 365 * 30.4
    for scen in ('planning', 'pessimistic'):
        hx_ = hxa - (hxa.mean() / 2.0 if scen == 'pessimistic' else 0.0)
        print(f"   {scen.upper()}")
        for wb, wx in ((1000, 0), (500, 500)):
            G = []
            for _ in range(20000):
                ib = []; ix = []
                while len(ib) < 12:
                    s0 = rng.integers(0, len(hbd) - 2); ib += [s0, s0 + 1, s0 + 2]
                while len(ix) < 12:
                    s1 = rng.integers(0, len(hx_) - 2); ix += [s1, s1 + 1, s1 + 2]
                b_, x_ = float(wb), float(wx)
                for i, j in zip(ib[:12], ix[:12]):
                    b_ *= 1 + hbd[i]; x_ *= 1 + hx_[j]
                G.append((b_ + x_) / (wb + wx))
            G = np.array(G); cells = []
            for t in (0.0, 0.104, 0.208, 0.312):
                Ga = np.where(G > 1, 1 + (G - 1) * (1 - t), G)
                cells.append((float(np.median(Ga) ** (1 / 12) - 1), float((Ga >= 1.02 ** 12).mean())))
            OUT['tax_profits_only'][f"delta_book|{scen}|{wb}|{wx}"] = dict(cells=cells, plose=float((G < 1).mean()))
            print(f"   ${wb:<4} ${wx:<5}|  " + "   ".join(f"{100 * m:+5.2f}% / {100 * p:3.0f}%  " for m, p in cells)
                  + f"|   {100 * (G < 1).mean():3.0f}%")
    print("\n   the cross-venue trade if its Binance leg (USDT-settled) were taxed as a VDA (31.2% of each winning leg,")
    print("   losses ignored) while its Delta leg is business income (net, by financial year):")
    for tb in (0.104, 0.312):
        a1, b1 = xv_mixed(*base, tb)
        a2, b2 = xv_mixed(*allm, tb, cost_mult=5, allow=liq & same)
        OUT[f'xv_mixed_{tb}'] = dict(pre=a1, after=b1, pre_all=a2, after_all=b2)
        print(f"   Delta leg at {100 * tb:4.1f}%: pre-registered {100 * a1:+6.1f}%/yr -> {100 * b1:+6.1f}%/yr; "
              f"ALL harder {100 * a2:+6.1f}%/yr -> {100 * b2:+6.1f}%/yr")
    print(f"\n   after tax read A (31.2% of each year's net profit), a pre-tax average of g/month is about g x 0.69: "
          f"2.9% -> 2.0%, 4.0% -> 2.8%")
    json.dump(OUT, open(os.path.join(HERE, 'c528_budget_plan.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
