#!/usr/bin/env python3
"""Round 19 (C537): when, and how often, the rent-gap trade should decide. Rules and bar fixed in
research/c537_preregistration.md (committed first).

    python3 research/c537_timing.py XV_CACHE PI42_DIR

One settlement-level simulator for every variant, on an hourly clock:
- Delta pays at its exchange hours (C524's interval detection), Binance/Pi42 at each recorded fundingTime;
  a held leg earns or pays every settlement it is held through, 18% GST on funding paid;
- a decision at hour h happens at h:30, after that hour's settlements;
- the signal at a decision: (Delta - Binance) settlements in the window before it, / days x 365;
- costs per entry and exit of both legs (Pi42 0.10% x 1.18 + 0.02%, Delta 0.05% x 1.18 + 0.02%), x1 and x5;
- $1,000, whole Delta contracts at the day's price; price legs left out (hedged; daily data only).
"""
import os, sys, io, json, math, datetime as dt, contextlib
import numpy as np, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c531_split_600 as S

H = 3600
CAP = 1000.0
GST = 0.18
COST_P = 0.0010 * 1.18 + 0.0002
COST_D = 0.0005 * 1.18 + 0.0002
OUT = {}


def delta_events(recs, iv_now):
    """{hour: rate as a fraction} at Delta's exchange hours (the same rule as X.delta_daily_funding)"""
    v = dict(recs)
    hrs = iv_now // 3600
    ts = sorted(v)
    blocks, ev = {}, {}
    for t in ts:
        blocks.setdefault((t - X.START) // (30 * X.DAY), []).append(t)
    for b, tt in blocks.items():
        h_iv = hrs
        if hrs == 4:
            ch4 = sum(1 for t in tt if (t // 3600) % 8 == 4 and (t - 3600) in v and v[t] != v[t - 3600])
            ch8 = sum(1 for t in tt if (t // 3600) % 8 == 0 and (t - 3600) in v and v[t] != v[t - 3600])
            if ch4 == 0 and ch8 > 0:
                h_iv = 8
        for t in tt:
            if (t // 3600) % h_iv == 0:
                ev[t // H] = v[t] / 100.0
    return ev


def build(cache, pdir):
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    uni = json.load(open(os.path.join(pdir, 'pi42_universe.json')))
    pi42 = set(uni['both'])
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
    allow = sorted(liq & same & pi42)
    tov = {c: float((tk.get(prods[c]['sym']) or {}).get('turnover_usd') or 0) for c in allow}
    drop = int(os.environ.get('C537_DROP_LOW') or 0)       # sensitivity only: drop the N quietest coins
    if drop:
        allow = sorted(sorted(allow, key=lambda c: -tov[c])[:len(allow) - drop])
    h0 = (X.START - 15 * X.DAY) // H
    h1 = X.END // H
    nh = h1 - h0
    k = len(allow)
    fD = np.zeros((nh, k)); fB = np.zeros((nh, k))
    cD = np.zeros((nh, k), bool); cB = np.zeros((nh, k), bool)      # a settlement happened (coverage)
    px = {}
    byc = {r[0]: r for r in res}
    for j, c in enumerate(allow):
        _, df, dp, dm, bf, bp = byc[c]
        for hh, x in delta_events(df, prods[c]['iv']).items():
            if h0 <= hh < h1:
                fD[hh - h0, j] = x; cD[hh - h0, j] = True
        for t, r in bf:
            hh = (t // 1000) // H
            if h0 <= hh < h1:
                fB[hh - h0, j] += r; cB[hh - h0, j] = True
        px[c] = {int(t) // X.DAY * X.DAY: float(x) for t, x in dp}
    return dict(allow=allow, h0=h0, fD=fD, fB=fB, cD=cD, cB=cB, px=px, cv=S.delta_cv(),
                tov={c: tov[c] for c in allow})


def simulate(B, freq=24, win=7, enter=0.20, exit_=0.10, maxp=10, size=0.10, cost_mult=1.0, stats=False):
    allow, h0, fD, fB, cD, cB, px, cv = (B[k] for k in ('allow', 'h0', 'fD', 'fB', 'cD', 'cB', 'px', 'cv'))
    nh, k = fD.shape
    sp = fD - fB
    csum = np.vstack([np.zeros((1, k)), np.cumsum(sp, 0)])
    nD = np.vstack([np.zeros((1, k)), np.cumsum(cD, 0)])
    nB = np.vstack([np.zeros((1, k)), np.cumsum(cB, 0)])
    wh = win * 24
    cp, cd = COST_P * cost_mult, COST_D * cost_mult
    held = {}                                      # j -> (side, size)
    pnl = np.zeros(nh); rent = np.zeros(nh); cost = np.zeros(nh)
    start_h = (X.START // H) - h0 + 0            # trading starts at START
    neg_rent = 0.0; n_ent = 0; hold_h = []; opened = {}; n_set = n_neg = 0
    for h in range(start_h, nh):
        for j, (side, sz) in held.items():        # settlements at hour h, held through them
            if cD[h, j] or cB[h, j]:
                ld = side * fD[h, j]
                lb = -side * fB[h, j]
                ld = ld * (1 + GST) if ld < 0 else ld
                lb = lb * (1 + GST) if lb < 0 else lb
                rent[h] += sz * (ld + lb)
                n_set += 1
                if ld + lb < 0:
                    neg_rent += sz * (ld + lb); n_neg += 1
        if (h + h0) % freq != 0:                    # decide at h:30 UTC, after hour h's settlements
            continue
        a = h + 1 - wh                             # window: hours (h-wh, h]
        if a < 0:
            continue
        s = (csum[h + 1] - csum[a]) / win * 365.0
        okw = ((nD[h + 1] - nD[a]) >= win) & ((nB[h + 1] - nB[a]) >= win)
        for j in list(held):
            side, sz = held[j]
            if (not okw[j]) or abs(s[j]) < exit_ or np.sign(s[j]) != side:
                cost[h] += sz * (cp + cd)
                hold_h.append(h - opened.pop(j))
                del held[j]
        room = maxp - len(held)
        if room > 0:
            cand = [j for j in range(k) if j not in held and okw[j] and abs(s[j]) >= enter]
            cand.sort(key=lambda j: -abs(s[j]))
            day = ((h + h0) * H) // X.DAY * X.DAY
            for j in cand:
                if room <= 0:
                    break
                c = allow[j]
                p_ = px[c].get(day) or px[c].get(day - X.DAY)
                cv_ = cv.get(c)
                if not p_ or not cv_:
                    continue
                kq = int(round(size * CAP / (cv_ * p_)))
                if kq < 1:
                    continue
                sz = kq * cv_ * p_ / CAP
                held[j] = (int(np.sign(s[j])), sz); opened[j] = h
                cost[h] += sz * (cp + cd)
                room -= 1; n_ent += 1
    pnl = rent - cost
    hrs = np.arange(nh) + h0
    day = (hrs * H) // X.DAY * X.DAY
    live = hrs >= X.START // H
    days = np.unique(day[live])
    di = np.searchsorted(days, day[live])
    daily = np.bincount(di, weights=pnl[live], minlength=len(days))
    out = dict(daily=daily, days=days, net=float(daily.mean() * 365), t=X.hac_t(daily),
               rent=float(rent[live].sum() / (len(days) / 365)), cost=float(cost[live].sum() / (len(days) / 365)),
               entries=n_ent, neg_rent=float(neg_rent / (len(days) / 365)),
               hold_med_h=float(np.median(hold_h)) if hold_h else None, neg_share=n_neg / max(n_set, 1))
    return out


HALVES = [('2024-10', '2025-03'), ('2025-04', '2025-09'), ('2025-10', '2026-03'), ('2026-04', '2026-09')]


def halves(days, x):
    m = np.array([dt.datetime.utcfromtimestamp(int(d)).strftime('%Y-%m') for d in days])
    return [float(x[(m >= a) & (m <= b)].sum()) for a, b in HALVES]


def main(cache, pdir):
    print("ROUND 19 (C537): WHEN, AND HOW OFTEN, THE RENT-GAP TRADE SHOULD DECIDE (pre-registered)\n")
    B = build(cache, pdir)
    print(f"coins: {len(B['allow'])} (Pi42 lists it, Delta turnover >= $100k today, the same asset)"
          + (f"; SENSITIVITY: the {os.environ['C537_DROP_LOW']} quietest dropped" if os.environ.get('C537_DROP_LOW') else '') + "\n")
    V = [('B0  daily 00:30 UTC (live)', {}),
         ('F8  every 8 h', dict(freq=8)), ('F4  every 4 h', dict(freq=4)), ('F1  every hour', dict(freq=1)),
         ('E0  exit only on a sign change', dict(exit_=0.0)), ('E5  exit under 5%/yr', dict(exit_=0.05)),
         ('E15 exit under 15%/yr', dict(exit_=0.15)),
         ('N15 enter at 15%/yr', dict(enter=0.15)), ('N30 enter at 30%/yr', dict(enter=0.30)),
         ('W3  3-day window', dict(win=3)), ('W14 14-day window', dict(win=14)),
         ('P15 15 pairs x 6.67%', dict(maxp=15, size=0.10 * 10 / 15))]
    R = {}
    for cm in (1.0, 5.0):
        for name, kw in V:
            R[(name, cm)] = simulate(B, cost_mult=cm, **kw)
    b1, b5 = R[(V[0][0], 1.0)], R[(V[0][0], 5.0)]
    print("rent - costs on $1,000 (price legs hedged, left out), 2024-10 .. 2026-09")
    print(f"{'variant':34} {'net/yr x1':>10} {'t':>6} {'rent/yr':>8} {'costs/yr':>9} {'entries':>8} {'hold (median)':>14} "
          f"{'net/yr x5':>10} | vs B0: {'diff/yr':>8} {'t':>6} {'half-years +':>13} {'last 6m':>8} {'x5 >= B0':>9}  BAR")
    for name, kw in V:
        r1, r5 = R[(name, 1.0)], R[(name, 5.0)]
        d = r1['daily'] - b1['daily']
        dh = halves(r1['days'], d)
        dt_ = X.hac_t(d) if name != V[0][0] else float('nan')
        passed = (name != V[0][0] and d.mean() * 365 >= 0.03 and dt_ >= 2.5 and sum(1 for v in dh if v > 0) >= 3
                  and dh[-1] > 0 and r5['net'] >= b5['net'])
        OUT[name] = dict(net1=r1['net'], t1=r1['t'], rent=r1['rent'], cost=r1['cost'], entries=r1['entries'],
                         hold_med_h=r1['hold_med_h'], net5=r5['net'], diff=float(d.mean() * 365), diff_t=dt_,
                         diff_halves=dh, passed=bool(passed), neg_rent=r1['neg_rent'], neg_share=r1['neg_share'])
        hold = f"{r1['hold_med_h'] / 24:.1f} days" if r1['hold_med_h'] else '-'
        print(f"{name:34} {100 * r1['net']:+9.1f}% {r1['t']:6.2f} {100 * r1['rent']:+7.1f}% {100 * r1['cost']:8.1f}% "
              f"{r1['entries']:8d} {hold:>14} {100 * r5['net']:+9.1f}% | {100 * d.mean() * 365:+7.1f}% "
              f"{dt_:6.2f} {sum(1 for v in dh if v > 0):>9}/4    {100 * dh[-1]:+7.2f}% {('yes' if r5['net'] >= b5['net'] else 'no'):>9}  "
              f"{'PASS' if passed else ('-' if name == V[0][0] else 'fail')}")
    print("\nDESCRIPTIVE (no bar)")
    print("  1. settlements where a held pair paid instead of earning (its gap ran the wrong way before the next decision):")
    for n in (V[0][0], V[1][0], V[2][0], V[3][0]):
        print(f"     {n:30} {100 * OUT[n]['neg_share']:4.1f}% of held settlements, {100 * OUT[n]['neg_rent']:+5.1f}%/yr of capital")
    fD, fB, cD, cB, h0 = B['fD'], B['fB'], B['cD'], B['cB'], B['h0']
    nh, k = fD.shape
    hrs = np.arange(nh) + h0
    live = hrs >= X.START // H
    # 2. base rent, per coin over the days both venues paid, then the median coin
    dayi = (hrs * H) // X.DAY
    aD, aB = [], []
    for j in range(k):
        dD = np.unique(dayi[live & cD[:, j]]); dB_ = np.unique(dayi[live & cB[:, j]])
        both = np.intersect1d(dD, dB_)
        if len(both) < 60:
            continue
        m_ = live & np.isin(dayi, both)
        aD.append(fD[m_, j].sum() / len(both) * 365); aB.append(fB[m_, j].sum() / len(both) * 365)
    aD, aB = np.array(aD), np.array(aB)
    print(f"  2. base rent, the median coin a year (+ = up-bettors pay): Delta {100 * np.median(aD):+.1f}%, "
          f"Pi42/Binance {100 * np.median(aB):+.1f}%, the gap {100 * np.median(aD - aB):+.1f}%; "
          f"Delta dearer for up-bettors on {100 * (aD > aB).mean():.0f}% of {len(aD)} coins")
    vb = fB[live[:, None] & cB]; vd = fD[live[:, None] & cD]
    dflt_b = np.isclose(vb, 0.0001, atol=1e-9) | np.isclose(vb, 0.00005, atol=1e-9)
    ub, cb = np.unique(np.round(vd, 8), return_counts=True)
    top = np.argsort(-cb)[:3]
    print(f"     Binance's default rent (0.01% a settlement on 8 h, 0.005% on 4 h, ~11%/yr) was the rate on "
          f"{100 * dflt_b.mean():.0f}% of its settlements; Delta's commonest rates: "
          + ", ".join(f"{100 * ub[i]:+.4f}% ({100 * cb[i] / len(vd):.0f}%)" for i in top))
    # 3. persistence: the 7-day gap at 00:30 UTC against the next 7 days'
    sp = fD - fB
    csum = np.vstack([np.zeros((1, k)), np.cumsum(sp, 0)])
    nD = np.vstack([np.zeros((1, k)), np.cumsum(cD, 0)]); nB = np.vstack([np.zeros((1, k)), np.cumsum(cB, 0)])
    pts = [h for h in range(nh) if (h + h0) % 24 == 0 and h + 1 - 168 >= 0 and h + 168 < nh and live[h]]
    x, y = [], []
    for h in pts:
        a, b = h + 1 - 168, h + 1 + 168
        s0 = (csum[h + 1] - csum[a]) / 7 * 365; s1 = (csum[b] - csum[h + 1]) / 7 * 365
        ok = ((nD[h + 1] - nD[a]) >= 7) & ((nB[h + 1] - nB[a]) >= 7) & ((nD[b] - nD[h + 1]) >= 7) & ((nB[b] - nB[h + 1]) >= 7)
        x.extend(s0[ok]); y.extend(s1[ok])
    x, y = np.array(x), np.array(y)
    print(f"  3. persistence: this week's gap vs next week's, correlation {np.corrcoef(x, y)[0, 1]:.2f} "
          f"({len(x)} coin-days); next week, as a share of this week's gap (median), the same side:")
    PB = []
    for lo, hi in ((0.10, 0.20), (0.20, 0.40), (0.40, 0.80), (0.80, 9e9)):
        m_ = (np.abs(x) >= lo) & (np.abs(x) < hi)
        kept = y[m_] * np.sign(x[m_]) / np.abs(x[m_])
        PB.append(dict(lo=lo, hi=hi, n=int(m_.sum()), kept=float(np.median(kept)), same=float((kept > 0).mean())))
        print(f"     gap {100 * lo:4.0f}%{'+' if hi > 9 else f'-{100 * hi:.0f}%':6}/yr: {m_.sum():6d} coin-days, "
              f"{100 * np.median(kept):4.0f}% of it remains, same sign {100 * (kept > 0).mean():3.0f}%")
    print(f"     a pair's median hold under the live rule: {OUT[V[0][0]]['hold_med_h'] / 24:.0f} days")
    # 4. settlement timing
    hd = hrs % 24
    shD = [int(cD[hd == hh].sum()) for hh in range(24)]; shB = [int(cB[hd == hh].sum()) for hh in range(24)]
    print("  4. settlements by hour of day (UTC): Delta " + ", ".join(f"{hh:02d}h {n}" for hh, n in enumerate(shD) if n)
          + "; Binance " + ", ".join(f"{hh:02d}h {n}" for hh, n in enumerate(shB) if n))
    OUT['_base'] = dict(delta=float(np.median(aD)), pi42=float(np.median(aB)), gap=float(np.median(aD - aB)),
                        delta_dearer=float((aD > aB).mean()), binance_default_share=float(dflt_b.mean()))
    OUT['_persist'] = dict(corr=float(np.corrcoef(x, y)[0, 1]), n=int(len(x)), buckets=PB)
    OUT['_hours'] = dict(delta=shD, binance=shB)
    OUT['_coins'] = B['tov']
    passed = [n for n in OUT if not n.startswith('_') and OUT[n].get('passed')]
    print(f"\nPASSED: {', '.join(passed) if passed else 'none -- the live rule (daily at 06:00 IST) stays'}")
    tag = ('_drop%s' % os.environ['C537_DROP_LOW']) if os.environ.get('C537_DROP_LOW') else ''
    json.dump(OUT, open(os.path.join(HERE, f'c537_timing{tag}.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
