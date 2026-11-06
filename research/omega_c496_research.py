#!/usr/bin/env python3
"""C496 round 6 (research/c496_preregistration.md): W1 weekend clock, G1 neutral grid, D1 drawdown loop.

    python3 research/omega_c496_research.py grid    ONE_MIN_DIR NEED_JSON
    python3 research/omega_c496_research.py dd      BNC_DIR
    python3 research/omega_c496_research.py weekend RWA1H_DIR

Timestamps in W1 are read as instants: "the close of the Friday 21:00 UTC hour"
= the price at 21:00 UTC (the close of the candle that opened at 20:00). The
other reading (the candle that OPENS at that hour) is reported as a diagnostic.
"""
import os, sys, json, math, glob, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R

warnings.simplefilter('ignore')
H, DAY = 3600000, 86400000


def nw_t(x, L=5):
    return R.nw_t(np.asarray(x, float), L)


def q4(x):
    return int(sum(v.mean() > 0 for v in np.array_split(np.asarray(x, float), 4)))


# ─── G1: the neutral grid ───────────────────────────────────────────────────
def grid_month(t, o, h, l, c, steps=20, width=0.15, maker=0.0002, taker=0.0008):
    """one coin-month; returns P&L as a fraction of the allocation"""
    P0 = o[0]
    lv = P0 * (1 + width * (2 * np.arange(steps + 1) / steps - 1))
    unit = 1.0 / steps / P0                       # coin quantity per step
    last, pos, cash, fees, live = steps // 2, 0, 0.0, 0.0, True
    for i in range(len(t)):
        if not live:
            break
        seq = ('dn', 'up') if c[i] < o[i] else ('up', 'dn')
        for d in seq:
            if d == 'dn':
                while last > 0 and l[i] <= lv[last - 1]:
                    last -= 1; px = lv[last]
                    pos += 1; cash -= unit * px; fees += unit * px * maker
            else:
                while last < steps and h[i] >= lv[last + 1]:
                    last += 1; px = lv[last]
                    pos -= 1; cash += unit * px; fees += unit * px * maker
        if l[i] < lv[0] or h[i] > lv[-1]:
            live = False                          # out of range: stop, hold the inventory
    end = c[-1]
    close_fee = abs(pos) * unit * end * taker
    return cash + pos * unit * end - fees - close_fee


def grid(mdir, need_path):
    need = json.load(open(need_path))
    months = {}
    for s, ms in need.items():
        p = os.path.join(mdir, s + '.npz')
        if not os.path.exists(p):
            continue
        z = np.load(p); t = z['t'].astype(np.int64)
        for m in ms:
            a = int(dt.datetime.strptime(m + '-01', '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
            nm = (dt.datetime.strptime(m + '-01', '%Y-%m-%d') + dt.timedelta(days=32)).replace(day=1)
            b = int(nm.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
            i0, i1 = np.searchsorted(t, a), np.searchsorted(t, b)
            if i1 - i0 < 0.9 * (b - a) / 60000:
                continue
            sl = slice(i0, i1)
            months.setdefault(m, []).append(grid_month(t[sl], z['o'][sl], z['h'][sl], z['l'][sl], z['c'][sl]))
    ks = sorted(months)
    x = np.array([np.mean(months[k]) for k in ks])
    allcm = np.concatenate([months[k] for k in ks])
    t_ = nw_t(x, 2)
    rec = x[[k >= '2024-01' for k in ks]]
    adm = bool(t_ >= 2.45 and q4(x) >= 3 and x.mean() > 0 and rec.mean() > 0)
    print(f"G1 neutral grid (+-15%, 20 steps, maker 0.02%): {len(ks)} months ({ks[0]}..{ks[-1]}), "
          f"{len(allcm)} coin-months")
    print(f"  mean month {100*x.mean():+.2f}%  t {t_:+.2f}  quarters+ {q4(x)}/4  months positive {100*(x>0).mean():.0f}%  "
          f"best {100*x.max():+.2f}%  worst {100*x.min():+.2f}%  -> {'ADMIT' if adm else 'not admitted'}")
    print(f"  per coin-month: {100*(allcm>0).mean():.0f}% positive, median {100*np.median(allcm):+.2f}%, "
          f"mean {100*allcm.mean():+.2f}%, worst {100*allcm.min():+.1f}%, best {100*allcm.max():+.1f}%; "
          f"left the range in its month: loss tail = mean of the worst 10% {100*np.sort(allcm)[:max(1,len(allcm)//10)].mean():+.1f}%")
    return dict(months=ks, monthly=[float(v) for v in x], t=float(t_), admit=adm,
                coin_months=len(allcm), pos_share=float((allcm > 0).mean()))


# ─── D1: the drawdown loop ──────────────────────────────────────────────────
def dd(bdir):
    from omega_c493_research import TRADFI
    R.EXCLUDE = set(R.EXCLUDE) | TRADFI
    T, syms, close, qv, fund = R.load_crypto(bdir)
    r, W, elig = R.crypto_sleeves(T, close, qv, fund)
    Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1)
    base = R.pnl(Wc, r, fund, 1)[0]
    n = len(T)
    rr = np.nan_to_num(r)
    Wd = np.zeros_like(Wc); ret = np.zeros(n)
    eq, peak, m = 1.0, 1.0, 1.0
    for i in range(n):
        if i >= 1:
            wl = Wd[i - 1]
            wl2 = Wd[i - 2] if i >= 2 else np.zeros_like(wl)
            ret[i] = float(np.nansum(wl * rr[i]) - np.nansum(wl * fund[i]) - np.abs(wl - wl2).sum() * R.COST)
            eq *= 1 + ret[i]; peak = max(peak, eq)
        ddn = 1 - eq / peak
        m = min(1.0, max(0.25, 1 - ddn / 0.30))
        Wd[i] = m * Wc[i]
    diff = ret - base
    sB, sD, sX = R.stats(base, T), R.stats(ret, T), R.stats(diff, T)
    adm = bool(sX['t'] >= 2.0 and sX['npos'] >= 3 and sD['maxdd'] < sB['maxdd'])
    for lab, s in (('COMBO-C (crypto, dial 15%)', sB), ('D1 drawdown loop', sD), ('D1 minus COMBO-C (the test)', sX)):
        R.show(lab, s)
    print(f"  max drawdown {100*sB['maxdd']:.1f}% -> {100*sD['maxdd']:.1f}%  |  D1 {'ADMITTED' if adm else 'not admitted'}")
    return dict(base=sB, d1=sD, diff=sX, admit=adm)


# ─── W1: the weekend clock ──────────────────────────────────────────────────
def weekend(rdir, instant=True):
    files = [p for p in glob.glob(os.path.join(rdir, '*.json')) if not p.endswith('contracts.json')]
    rows = []                                     # (friday_ms, symbol, D, R)
    off = 0 if instant else H                     # instant: the candle that opened an hour earlier
    for p in files:
        s = os.path.basename(p)[:-5]
        c = {int(k): v[0] for k, v in json.load(open(p)).items()}
        if len(c) < 24 * 14:
            continue
        ts = sorted(c)
        d0 = dt.datetime.utcfromtimestamp(ts[0] / 1000).date()
        d1 = dt.datetime.utcfromtimestamp(ts[-1] / 1000).date()
        d = d0 + dt.timedelta(days=(4 - d0.weekday()) % 7)          # first Friday
        while d <= d1:
            fri = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)
            kF = fri + 21 * H - H + off
            kS = fri + 2 * DAY + 22 * H - H + off
            kM = fri + 3 * DAY + 15 * H - H + off
            if kF in c and kS in c and kM in c and c[kF] > 0 and c[kS] > 0 and c[kM] > 0:
                rows.append((fri, s, math.log(c[kS] / c[kF]), math.log(c[kM] / c[kS])))
            d += dt.timedelta(days=7)
    split = int(dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
    disc = [x for x in rows if x[0] < split]; hold = [x for x in rows if x[0] >= split]
    def slope(rs):
        D = np.array([x[2] for x in rs]); Rr = np.array([x[3] for x in rs])
        if len(D) < 30 or D.std() == 0:
            return float('nan'), float('nan')
        b = (D * Rr).sum() / (D * D).sum()
        e = Rr - b * D
        se = math.sqrt((e @ e) / (len(D) - 1) / (D @ D))
        return b, b / se
    def trade(rs, sign):
        wk = {}
        for fri, s, D, Rr in rs:
            if D == 0:
                continue
            wk.setdefault(fri, []).append(sign * np.sign(D) * Rr - 0.0016 - 0.0002)
        ks = sorted(wk)
        return ks, np.array([np.mean(wk[k]) for k in ks])
    b0, t0 = slope(disc)
    sign = 1.0 if b0 > 0 else -1.0
    out = dict(n_disc=len(disc), n_hold=len(hold), slope_disc=b0, t_disc=t0,
               contracts=len({x[1] for x in rows}), rule='continuation' if sign > 0 else 'reversal')
    kd, xd = trade(disc, sign)
    kh, xh = trade(hold, sign)
    b1, t1 = slope(hold)
    th = nw_t(xh, 3) if len(xh) > 8 else float('nan')
    adm = bool(len(xh) > 8 and th >= 2.0 and xh.mean() > 0 and q4(xh) >= 3)
    out.update(slope_hold=b1, t_slope_hold=t1, weeks_hold=len(xh), mean_hold=float(xh.mean()) if len(xh) else float('nan'),
               t_hold=float(th), q_hold=q4(xh) if len(xh) >= 4 else 0, admit=adm,
               weeks_disc=len(xd), mean_disc=float(xd.mean()) if len(xd) else float('nan'))
    lab = 'W1 (instants)' if instant else 'W1 diagnostic (candles opening at the hour)'
    print(f"{lab}: {out['contracts']} contracts; discovery {len(disc)} contract-weekends, holdout {len(hold)}")
    print(f"  discovery slope of Monday on weekend drift {b0:+.3f} (t {t0:+.2f}) -> rule: {out['rule']}; "
          f"its own net {100*out['mean_disc']:+.3f}%/weekend over {len(xd)} weekends")
    print(f"  HOLDOUT (from 2026-03): slope {b1:+.3f} (t {t1:+.2f}); rule net {100*out['mean_hold']:+.3f}%/weekend "
          f"t {th:+.2f} quarters+ {out['q_hold']}/4 over {len(xh)} weekends -> {'ADMIT' if adm else 'not admitted'}")
    return out


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'grid':
        res = grid(sys.argv[2], sys.argv[3])
    elif cmd == 'dd':
        res = dd(sys.argv[2])
    else:
        res = weekend(sys.argv[2], True)
        res['diag'] = weekend(sys.argv[2], False)
    if '--out' in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1, default=float)
