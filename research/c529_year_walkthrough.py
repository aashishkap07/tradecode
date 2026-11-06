#!/usr/bin/env python3
"""C529 (descriptive): one real year of the operator's plan, month by month -- what the bot did and why.

    python3 research/c529_year_walkthrough.py BNC_DIR XV_CACHE

The plan: $500 book on Delta India + $500 cross-venue (C528). Both from the research's own simulators,
on real data, no parameter chosen here:
  BOOK   the traded rule (N2+N3 + GK, dial 20% = vol target 26.7%, top 20, 30% band, Binance minimums at
         $500), paying DELTA's funding on its positions (Delta - Binance funding, coin by coin, day by day)
  XVENUE round 15's X1 rule with every assumption made harder at once ("ALL": the midnight payment to the
         day before, Delta's mark, costs x5, liquid coins only, same asset on both)
Every 12-month window where both exist (2024-10 .. 2026-08) is scored; the year shown is the one ranked
just below the best ("better than the worst, a little short of the best"). Its rank among the 20,000
bootstrapped years of C528 is printed too. The month guard is NOT simulated: the largest fall from each
month's start is printed against its 20% budget instead.
"""
import os, sys, io, json, math, contextlib, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import omega_c521_research as B
import c524_xvenue as X
import c528_budget_plan as P

TAXES = (0.312, 0.104)


def ym(t_s):
    return dt.datetime.utcfromtimestamp(t_s).strftime('%Y-%m')


def xv_daily(Dd, names, fD, fB, pD, pB, cost_mult=1.0, allow=None):
    """the X1 loop (c524_xvenue.simulate) keeping each day's parts and each day's entries/exits"""
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
    held = {}
    out = {k_: np.zeros(len(Dd)) for k_ in ('fund', 'px', 'cost', 'n', 'ent', 'ext')}
    for i in range(len(Dd) - 1):
        sig = s7[i]
        for j in list(held):
            side = held[j]
            if np.isnan(sig[j]) or abs(sig[j]) < X.EXIT_ or np.sign(sig[j]) != side:
                out['cost'][i + 1] += X.SIZE * (cB + cD); out['ext'][i + 1] += 1
                del held[j]
        cand = [j for j in range(k) if j not in held and not np.isnan(sig[j]) and abs(sig[j]) >= X.ENTER and ok[i + 1, j]]
        cand.sort(key=lambda j: -abs(sig[j]))
        for j in cand[:max(0, X.MAXP - len(held))]:
            held[j] = int(np.sign(sig[j])); out['cost'][i + 1] += X.SIZE * (cB + cD); out['ent'][i + 1] += 1
        for j, side in held.items():
            if not ok[i + 1, j]:
                continue
            out['fund'][i + 1] += X.SIZE * side * sp[i + 1, j]
            out['px'][i + 1] += X.SIZE * side * (rB[i + 1, j] - rD[i + 1, j])
        out['n'][i + 1] = len(held)
    return out


def main(bdir, cache):
    with contextlib.redirect_stdout(io.StringIO()):
        D = B.prep(bdir)
    om = B.om
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    B.EQ, B.TV = 500.0, 0.20 * 4 / 3
    W = B.sleeves(D, sd=sdgk)
    xb, Wc, info = B.book(D, W)
    gross = np.abs(Wc).sum(1)
    npos = (np.abs(Wc) > 0).sum(1)
    prods, res = X.load(cache)
    import requests
    base = X.matrices(prods, res)
    Dd, names, fD, fB, pD, pB = base
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    rD = np.full_like(pD, np.nan); rB = rD.copy(); rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    same = {c for j, c in enumerate(names)
            if (lambda m: m.sum() > 60 and np.corrcoef(rD[m, j], rB[m, j])[0, 1] >= 0.9)(~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j]))}
    allm = X.matrices(prods, res, shift00=True, mark=True)
    xd = xv_daily(*allm, cost_mult=5, allow=liq & same)
    # the book on Delta: each day, its positions pay Delta's funding instead of Binance's
    col = {s: j for j, s in enumerate(D['syms'])}
    bidx = {int(t) // 86400000: i for i, t in enumerate(D['T'])}
    drag = np.zeros(len(D['T']))
    for i, d in enumerate(Dd):
        bi = bidx.get(int(d) // 86400)
        if bi is None or bi == 0:
            continue
        w = Wc[bi - 1]
        drag[bi] = sum(w[col[c + 'USDT']] * (fD[i, j] - fB[i, j]) for j, c in enumerate(names)
                       if c + 'USDT' in col and w[col[c + 'USDT']] != 0 and not np.isnan(fD[i, j]) and not np.isnan(fB[i, j]))
    xbd = xb - drag
    # monthly
    Tb = D['T'] // 1000
    mb, mx = {}, {}
    for i, t in enumerate(Tb):
        m = ym(t)
        r = mb.setdefault(m, dict(eq=[], gross=[], n=[], price=0.0, fund=0.0, cost=0.0, turn=0.0, drag=0.0, days=[]))
        r['days'].append(xbd[i]); r['gross'].append(gross[i - 1] if i else 0); r['n'].append(npos[i - 1] if i else 0)
        r['price'] += info['gross'][i]; r['fund'] += info['funding'][i] - drag[i]; r['cost'] += info['cost'][i]
        r['turn'] += info['turnover'][i]
    for i, t in enumerate(Dd):
        if i < X.WIN:
            continue
        m = ym(t)
        r = mx.setdefault(m, dict(fund=0.0, px=0.0, cost=0.0, n=[], ent=0, ext=0))
        r['fund'] += xd['fund'][i]; r['px'] += xd['px'][i]; r['cost'] += xd['cost'][i]
        r['n'].append(xd['n'][i]); r['ent'] += int(xd['ent'][i]); r['ext'] += int(xd['ext'][i])
    months = [m for m in sorted(mx) if m in mb and m <= '2026-08']
    bret = {m: float(np.prod(1 + np.array(mb[m]['days'])) - 1) for m in months}
    xret = {m: mx[m]['fund'] + mx[m]['px'] - mx[m]['cost'] for m in months}
    # every 12-month window
    wins = []
    for a in range(len(months) - 11):
        ms = months[a:a + 12]
        b_, x_ = 500.0, 500.0
        for m in ms:
            b_ *= 1 + bret[m]; x_ *= 1 + xret[m]
        wins.append(((b_ + x_) / 1000.0, ms))
    wins.sort(key=lambda z: z[0])
    print("C529: ONE REAL YEAR OF THE PLAN ($500 book on Delta India + $500 cross-venue), month by month\n")
    print("every 12-month window where both exist, worst to best (the plan's year, pre-tax):")
    for g, ms in wins:
        print(f"   {ms[0]} -> {ms[-1]}: {100 * (g - 1):+6.1f}%  ({100 * (g ** (1 / 12) - 1):+.2f}%/month)")
    G, ms = wins[-2]
    # its rank among C528's bootstrapped years (backtested: book full history, X1 ALL), pre-tax
    with contextlib.redirect_stdout(io.StringIO()):
        pass
    bfull = P.months_of(D['T'][1:], xbd[1:]); kb = sorted(bfull)[1:]
    hb = np.array([bfull[k] for k in kb if k <= '2026-08'])
    hx = np.array([xret[m] for m in months])
    rng = np.random.default_rng(29)
    sims = []
    for _ in range(20000):
        ib, ix = [], []
        while len(ib) < 12:
            s0 = rng.integers(0, len(hb) - 2); ib += [s0, s0 + 1, s0 + 2]
        while len(ix) < 12:
            s1 = rng.integers(0, len(hx) - 2); ix += [s1, s1 + 1, s1 + 2]
        b_, x_ = 500.0, 500.0
        for i, j in zip(ib[:12], ix[:12]):
            b_ *= 1 + hb[i]; x_ *= 1 + hx[j]
        sims.append((b_ + x_) / 1000.0)
    sims = np.array(sims)
    print(f"\nTHE YEAR SHOWN: {ms[0]} -> {ms[-1]} (second-best window): {100 * (G - 1):+.1f}% pre-tax; it beats "
          f"{100 * (sims < G).mean():.0f}% of the 20,000 simulated years (as backtested; the book's whole history, "
          f"2022 included). Worst simulated 1%: {100 * (np.percentile(sims, 1) - 1):+.1f}%; best 1%: {100 * (np.percentile(sims, 99) - 1):+.1f}%.")
    print("\nmonth     | BOOK on Delta ($500 at start)                                       | CROSS-VENUE ($500)                          | PLAN")
    print("          | return  coins gross  turnover  price  funding  costs  worst day  fall | return pairs in/out funding price  costs   | total     cum")
    b_, x_ = 500.0, 500.0
    rows = []
    for m in ms:
        r = mb[m]; q = mx[m]
        days = np.array(r['days']); eqd = np.cumprod(1 + days); fall = float((1 - eqd / np.maximum.accumulate(np.r_[1.0, eqd])[1:]).max())
        b0, x0 = b_, x_
        b_ *= 1 + bret[m]; x_ *= 1 + xret[m]
        row = dict(m=m, b=bret[m], x=xret[m], coins=float(np.mean(r['n'])), gross=float(np.mean(r['gross'])), turn=r['turn'],
                   price=r['price'] * b0, fund=r['fund'] * b0, cost=r['cost'] * b0, worst=float(days.min()), fall=fall,
                   pairs=float(np.mean(q['n'])), ent=q['ent'], ext=q['ext'], xf=q['fund'] * x0, xp=q['px'] * x0, xc=q['cost'] * x0,
                   tot=b_ + x_)
        rows.append(row)
        print(f"{m}   | {100 * row['b']:+6.2f}%  {row['coins']:4.1f}  {row['gross']:.2f}x   {row['turn']:5.2f}   {row['price']:+6.2f}  "
              f"{row['fund']:+6.2f}  {row['cost']:5.2f}  {100 * row['worst']:+6.2f}%  {100 * fall:4.1f}% | {100 * row['x']:+5.2f}% "
              f"{row['pairs']:4.1f}  {row['ent']:2d}/{row['ext']:<2d} {row['xf']:+6.2f} {row['xp']:+6.2f} {row['xc']:5.2f}  | "
              f"${row['tot']:8.2f} {100 * (row['tot'] / 1000 - 1):+6.1f}%")
    gain = rows[-1]['tot'] - 1000.0
    print(f"\nyear: ${gain:+.2f} pre-tax ({100 * gain / 1000:+.1f}%, {100 * ((rows[-1]['tot'] / 1000) ** (1 / 12) - 1):+.2f}%/month); "
          f"months >= +2%: {sum(1 for r in rows if (r['tot'] / (rows[rows.index(r) - 1]['tot'] if rows.index(r) else 1000) - 1) >= 0.02)}/12; "
          f"losing months: {sum(1 for r in rows if (r['tot'] / (rows[rows.index(r) - 1]['tot'] if rows.index(r) else 1000) - 1) < 0)}/12")
    for t in TAXES:
        at = gain * (1 - t) if gain > 0 else gain
        print(f"   after tax on net profit at {100 * t:.1f}%: ${at:+.2f} ({100 * at / 1000:+.1f}%, {100 * ((1 + at / 1000) ** (1 / 12) - 1):+.2f}%/month)")
    hcut = np.mean([r['b'] for r in rows]) / 3
    print(f"\nTHE SAME YEAR, PLANNING CASE (the book's mean cut by a third, {100 * hcut:.2f}%/month off; the cross-venue months as above):")
    b_, x_ = 500.0, 500.0
    for r in rows:
        b_ *= 1 + r['b'] - hcut; x_ *= 1 + r['x']
    g2 = b_ + x_ - 1000
    print(f"   ${g2:+.2f} pre-tax ({100 * ((1 + g2 / 1000) ** (1 / 12) - 1):+.2f}%/month); after tax at 31.2% "
          f"{100 * ((1 + g2 * 0.688 / 1000) ** (1 / 12) - 1):+.2f}%/month")
    json.dump(dict(year=[ms[0], ms[-1]], rows=rows, gain=gain, rank=float((sims < G).mean()),
                   windows=[[w[1][0], float(w[0])] for w in wins]),
              open(os.path.join(HERE, 'c529_year_walkthrough.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
