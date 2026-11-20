#!/usr/bin/env python3
"""C530 (descriptive planning, no new rule): the operator's new allocation, judged on real history.

    python3 research/c530_plan_odds.py BNC_DIR XV_CACHE

  $500  the book on Delta India (INR-settled): the traded rule (N2+N3, GK volatility, dial 20%, top 20,
        Binance minimums at $500, idle cash in Savings) from research/c528_budget_plan.py, its mean cut
        by 1/3 (the PBO haircut), less Delta's funding drag on its positions (+3.72%/yr, C528)
  $250  the cross-venue trade (X1, round 15), on the ALL-harder history, now with WHOLE Delta contracts at
        its own size: a leg is 10% of $250 = $25, rounded to whole contracts, skipped when one contract is
        more than the leg -- what the bot does. At $500 for comparison.
  $100  Pendle fixed yield, three readings: as registered (the 4 Oct qualifying market, $1 gas a purchase:
        -2.35%/yr held to its date), at 4 Oct's real Ethereum gas (~$0.20: +3.2%/yr), and the same $100
        in Binance Savings instead (6.69%)
The accounts compound apart (no transfers). 12-month paths: 3-month blocks of the book's whole history
(2020-02 -> 2026-08, 2022 included) and of the cross-venue months, drawn independently (correlation over
the overlap -0.02, C528), 20,000 draws. Pessimistic: the cross-venue mean halved again.
Tax on profits only: the book's and the cross-venue trade's NET profit for the year at the slab rate
(0 / 10.4 / 20.8 / 31.2%), a losing year taxed nothing; Pendle a VDA, 31.2% of its gain, its loss offsets
nothing. Returns are on the money in the plan ($850); the $100 reserve is shown apart.
"""
import os, sys, io, json, contextlib, datetime as dt
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c528_budget_plan as P
import c524_xvenue as X

DRAG = 0.0372                           # C528: the book's positions on Delta pay this much more funding a year
PENDLE = {'as registered ($1 gas)': -0.0235, "4 Oct's real gas (~$0.20)": 0.0325, 'Savings instead': P.SAV}
OUT = {}


def xv_contracts(D, names, fD, fB, pD, pB, cv, cap, cost_mult=1.0, allow=None):
    """X1 exactly (c524_xvenue.simulate), each leg in whole Delta contracts at a capital of `cap`"""
    k = len(names)
    rD = np.full_like(pD, np.nan); rB = rD.copy()
    rD[1:] = pD[1:] / pD[:-1] - 1; rB[1:] = pB[1:] / pB[:-1] - 1
    ok = ~np.isnan(fD) & ~np.isnan(fB) & ~np.isnan(rD) & ~np.isnan(rB)
    if allow is not None:
        ok &= np.array([n in allow for n in names])[None, :]
    sp = fD - fB
    s7 = np.full_like(sp, np.nan)
    with np.errstate(invalid='ignore'):
        for i in range(X.WIN - 1, len(D)):
            blk = sp[i - X.WIN + 1:i + 1]
            n = (~np.isnan(blk)).sum(0)
            s7[i] = np.where(n >= X.WIN, np.nanmean(blk, 0) * 365, np.nan)
    if allow is not None:
        s7[:, ~np.array([n in allow for n in names])] = np.nan
    cB, cD = X.COST_B * cost_mult, X.COST_D * cost_mult
    held, size = {}, {}
    pnl = np.zeros(len(D)); skipped = 0; entered = 0; dev = []
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
            dev.append(sz / X.SIZE)
            held[j] = int(np.sign(sig[j])); size[j] = sz
            pnl[i + 1] -= sz * (cB + cD)
            room -= 1; entered += 1
        for j, side in held.items():
            if ok[i + 1, j]:
                pnl[i + 1] += size[j] * side * (sp[i + 1, j] + rB[i + 1, j] - rD[i + 1, j])
    live = np.arange(len(D)) >= X.WIN
    x = pnl[live]; Dl = D[live]
    months = {}
    for d_, v in zip(Dl, x):
        m = dt.datetime.utcfromtimestamp(int(d_)).strftime('%Y-%m')
        months[m] = months.get(m, 0.0) + v
    return dict(net=float(x.mean() * 365), t=float(X.hac_t(x)), months=months, skipped=skipped, entered=entered,
                leg_med=float(np.median(dev)) if dev else None, leg_p90=float(np.percentile(dev, 90)) if dev else None)


def paths(hb, hx, pendle_m, wb, wx, wp, rng, n=20000):
    """12-month paths: (end value / start) per account"""
    Gb, Gx = np.ones(n), np.ones(n)
    for k in range(n):
        ib = []; ix = []
        while len(ib) < 12:
            s0 = rng.integers(0, len(hb) - 2); ib += [s0, s0 + 1, s0 + 2]
        while len(ix) < 12:
            s1 = rng.integers(0, len(hx) - 2); ix += [s1, s1 + 1, s1 + 2]
        Gb[k] = np.prod(1 + hb[ib[:12]]); Gx[k] = np.prod(1 + hx[ix[:12]])
    Gp = (1 + pendle_m) ** 12
    return Gb, Gx, Gp


def after_tax(Gb, Gx, Gp, wb, wx, wp, t_bus, t_vda=0.312):
    bus = wb * (Gb - 1) + wx * (Gx - 1)
    vda = wp * (Gp - 1)
    tax = np.maximum(0.0, bus) * t_bus + max(0.0, vda) * t_vda
    end = wb * Gb + wx * Gx + wp * Gp - tax
    return end / (wb + wx + wp)


def main(bdir, cache):
    print("C530: THE PLAN AT $500 DELTA BOOK + $250 CROSS-VENUE + $100 PENDLE, ON REAL HISTORY\n")
    with contextlib.redirect_stdout(io.StringIO()):
        D = P.B.prep(bdir)
    om = P.B.om
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    xb, Tb = P.book_series(D, sdgk, 500)
    bm = P.months_of(Tb, xb)
    kb = sorted(bm)[1:]
    mbF = np.array([bm[k] for k in kb])
    hb = mbF - mbF.mean() / 3.0 - DRAG / 12.0
    print(f"1. THE BOOK ON DELTA, $500: {len(kb)} months {kb[0]} -> {kb[-1]}; backtested avg {100 * mbF.mean():+.2f}%/month; "
          f"planning (mean -1/3, Delta funding drag -{100 * DRAG:.2f}%/yr) {100 * hb.mean():+.2f}%/month")

    prods, res = X.load(cache)
    allm = X.matrices(prods, res, shift00=True, mark=True)
    Dd, names = allm[0], allm[1]
    raw = requests.get(X.DELTA + '/v2/products', params=dict(contract_types='perpetual_futures', states='live'), timeout=30).json()['result']
    cv = {p['underlying_asset']['symbol']: float(p.get('contract_value') or 0) for p in raw}
    tk = {t['symbol']: t for t in requests.get(X.DELTA + '/v2/tickers', params=dict(contract_types='perpetual_futures'),
                                               timeout=30).json()['result']}
    liq = {c for c in prods if float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) >= 100000}
    base = X.matrices(prods, res)
    rD = np.full_like(base[4], np.nan); rB = rD.copy()
    rD[1:] = base[4][1:] / base[4][:-1] - 1; rB[1:] = base[5][1:] / base[5][:-1] - 1
    same = set()
    for j, c in enumerate(base[1]):
        m = ~np.isnan(rD[:, j]) & ~np.isnan(rB[:, j])
        if m.sum() > 60 and np.corrcoef(rD[m, j], rB[m, j])[0, 1] >= 0.9:
            same.add(c)
    print("\n2. THE CROSS-VENUE TRADE IN WHOLE DELTA CONTRACTS (ALL harder: midnight timing, Delta's mark, costs x5, "
          "$100k Delta turnover, the same asset)")
    print("   capital  net/yr     t    entries  skipped (1 contract > the leg)  leg size: median / 90th pct of 10%")
    XV = {}
    xs_ref = X.simulate(*allm, verbose=False, cost_mult=5, allow=liq & same)
    print(f"   any      {100 * xs_ref['net_ann']:+6.1f}%  {xs_ref['t']:5.2f}   (fractional legs, as round 15)")
    for cap in (500.0, 250.0):
        r = xv_contracts(*allm, cv=cv, cap=cap, cost_mult=5, allow=liq & same)
        XV[cap] = r
        OUT[f'xv_{int(cap)}'] = {k: v for k, v in r.items() if k != 'months'}
        print(f"   ${cap:<6.0f}  {100 * r['net']:+6.1f}%  {r['t']:5.2f}    {r['entered']:5d}       {r['skipped']:5d}"
              f"                        {r['leg_med']:.2f} / {r['leg_p90']:.2f}")
    common = sorted(set(XV[250.0]['months']) & set(XV[500.0]['months']))
    hx250 = np.array([XV[250.0]['months'][k] for k in common])
    hx500 = np.array([XV[500.0]['months'][k] for k in common])
    print(f"   months {common[0]} -> {common[-1]}: $250 avg {100 * hx250.mean():+.2f}%/month, worst {100 * hx250.min():+.2f}%; "
          f"$500 avg {100 * hx500.mean():+.2f}%/month")

    print("\n3. THE PLAN, 12-MONTH PATHS (20,000), AFTER TAX ON PROFITS ONLY (the trades' net at your slab; Pendle 31.2% of its gain)")
    print("   P(avg >= 2%/month after tax) / 12-month median per month, by slab;  bad year (10%), P(losing year) before tax")
    rows = {}
    for scen in ('planning', 'pessimistic'):
        print(f"   {scen.upper()}" + (": the cross-venue mean halved again" if scen == 'pessimistic' else ''))
        print("   plan                                         0%              10.4%           20.8%           31.2%        |  bad year  losing year  P(>=4%)")
        for tag, wb, wx, wp, pm, hxs in (
                ('C530: $500 + $250 + Pendle $100 (registered)', 500, 250, 100, PENDLE['as registered ($1 gas)'], hx250),
                ('C530: $500 + $250 + Pendle $100 (real gas)', 500, 250, 100, PENDLE["4 Oct's real gas (~$0.20)"], hx250),
                ('       $500 + $250 + $100 in Savings', 500, 250, 100, PENDLE['Savings instead'], hx250),
                ('       $500 + $250 alone ($750)', 500, 250, 0, 0.0, hx250),
                ('C528: $500 + $500 ($1,000)', 500, 500, 0, 0.0, hx500)):
            hx = hxs - (hxs.mean() / 2.0 if scen == 'pessimistic' else 0.0)
            rng = np.random.default_rng(11)
            Gb, Gx, Gp = paths(hb, hx, (1 + pm) ** (1 / 12) - 1, wb, wx, wp, rng)
            pre = (wb * Gb + wx * Gx + wp * Gp) / (wb + wx + wp)
            cells = []
            for t in (0.0, 0.104, 0.208, 0.312):
                g = after_tax(Gb, Gx, Gp, wb, wx, wp, t)
                cells.append((float((g >= 1.02 ** 12).mean()), float(np.median(g) ** (1 / 12) - 1), float((g >= 1.04 ** 12).mean())))
            bad = float(np.percentile(pre, 10) ** (1 / 12) - 1)
            plose = float((pre < 1).mean())
            rows[f"{scen}|{tag.strip()}"] = dict(cells=cells, bad=bad, plose=plose)
            print(f"   {tag:45}" + "".join(f"{100 * p:3.0f}% / {100 * m:+5.2f}%  " for p, m, _ in cells)
                  + f"|  {100 * bad:+5.2f}%     {100 * plose:3.0f}%      {100 * cells[1][2]:3.0f}%")
    OUT['plans'] = rows
    print("\n   the $100 reserve sits in Binance Savings (6.69%) until a cross-venue side needs it; it is not in these figures")
    print("   one month in 8 a cross-venue side fell below 50% of its half in the history (round 17): the reserve is for that")
    json.dump(OUT, open(os.path.join(HERE, 'c530_plan_odds.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
