#!/usr/bin/env python3
"""C488 research engine: the pre-registered sleeves and their combination.

    python3 research/omega_c488_research.py BNC_DIR YAHOO_DIR [--out results.json]

BNC_DIR   : k/<SYM>.json daily klines [t, o, h, l, c, vol, quote_vol] and
            f/<SYM>.json funding [t, rate] from the Binance USDT-M archive
            (every symbol, delisted ones included), plus BTCUSDT_1h.json.
YAHOO_DIR : <name>.json daily [t, o, h, l, c, vol, adjclose] for the RWA proxies.

Every rule, parameter and the admission bar are fixed in
research/c488_preregistration.md. This file implements exactly that, and
nothing in it was tuned on its results.
"""
import os, sys, json, glob, math, datetime as dt
import numpy as np

DAY = 86400000
COST = 0.0008                       # per unit turnover: 0.06% taker + 0.02% half-spread
TOPN, AGE, VOLWIN = 40, 90, 30
EXCLUDE = {'USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'FDUSDUSDT', 'EURUSDT', 'GBPUSDT', 'AUDUSDT',
           'BTCDOMUSDT', 'DEFIUSDT', 'BLUEBIRDUSDT', 'FOOTBALLUSDT', 'USDEUSDT', 'XUSDUSDT', 'RLUSDUSDT',
           'USD1USDT', 'BFUSDUSDT', 'XAUUSDT', 'XAGUSDT', 'PAXGUSDT'}
RWA = ['gold', 'silver', 'copper', 'platinum', 'palladium', 'wti', 'brent', 'sp500', 'ndx100']
# Bitget's measured funding, % per year paid by a LONG (25 Sep 2026, ~3 months of history)
RWA_FUND = {'gold': 10.2, 'silver': 9.8, 'copper': 20.9, 'platinum': 10.0, 'palladium': 10.0,
            'wti': -49.5, 'brent': -60.4, 'sp500': -5.0, 'ndx100': 3.6}


# ─── data ────────────────────────────────────────────────────────────────────
def load_crypto(bdir):
    syms, K, F = [], {}, {}
    for p in sorted(glob.glob(os.path.join(bdir, 'k', '*.json'))):
        s = os.path.basename(p)[:-5]
        if s in EXCLUDE:
            continue
        rows = json.load(open(p))
        if len(rows) < AGE + 30:
            continue
        K[s] = rows
        fp = os.path.join(bdir, 'f', s + '.json')
        F[s] = json.load(open(fp)) if os.path.exists(fp) else []
        syms.append(s)
    t0 = min(r[0] for s in syms for r in K[s][:1]) // DAY * DAY
    t1 = max(r[0] for s in syms for r in K[s][-1:]) // DAY * DAY
    T = np.arange(t0, t1 + DAY, DAY)
    idx = {t: i for i, t in enumerate(T)}
    n, k = len(T), len(syms)
    close = np.full((n, k), np.nan); qv = np.full((n, k), np.nan); fund = np.zeros((n, k))
    for j, s in enumerate(syms):
        for r in K[s]:
            i = idx.get(r[0] // DAY * DAY)
            if i is not None:
                close[i, j], qv[i, j] = r[4], r[6]
        for t, rate in F[s]:
            i = idx.get(t // DAY * DAY)
            if i is not None:
                fund[i, j] += rate
    return T, syms, close, qv, fund


def load_yahoo(ydir, names):
    rows = {n: json.load(open(os.path.join(ydir, n + '.json'))) for n in names}
    t0 = max(min(r[0] for r in rows[n]) for n in names) // DAY * DAY
    t1 = max(max(r[0] for r in rows[n]) for n in names) // DAY * DAY
    T = np.arange(t0, t1 + DAY, DAY)
    idx = {t: i for i, t in enumerate(T)}
    close = np.full((len(T), len(names)), np.nan)
    for j, n in enumerate(names):
        for r in rows[n]:
            i = idx.get(r[0] // DAY * DAY)
            if i is not None and r[4]:
                close[i, j] = r[4]
    # carry the last price over weekends/holidays: no trading, no return
    for j in range(len(names)):
        last = np.nan
        for i in range(len(T)):
            if np.isnan(close[i, j]):
                close[i, j] = last
            else:
                last = close[i, j]
    return T, names, close


# ─── helpers ─────────────────────────────────────────────────────────────────
def returns(close):
    r = np.full_like(close, np.nan)
    r[1:] = close[1:] / close[:-1] - 1
    return r


def trailing_std(r, win):
    out = np.full_like(r, np.nan)
    for i in range(win, len(r)):
        out[i] = np.nanstd(r[i - win + 1:i + 1], axis=0)
    return out


def lagret(close, n):
    out = np.full_like(close, np.nan)
    out[n:] = close[n:] / close[:-n] - 1
    return out


def universe(close, qv):
    """point-in-time top-N by 30-day median quote volume through the previous day"""
    n, k = close.shape
    age = np.cumsum(~np.isnan(close), axis=0)
    elig = np.zeros((n, k), bool)
    for i in range(VOLWIN + 1, n):
        med = np.nanmedian(qv[i - VOLWIN:i], axis=0)
        ok = (age[i] >= AGE) & ~np.isnan(close[i]) & ~np.isnan(med)
        if ok.sum() == 0:
            continue
        rank = np.argsort(-np.where(ok, med, -1))
        elig[i, rank[:min(TOPN, ok.sum())]] = True
    return elig


def vol_scale(sd):
    return np.clip(0.02 / np.where(sd > 0, sd, np.nan), 0, 1.0)


def banded(target, band=0.30):
    """daily rebalance, but leave a position alone unless it must change sign/close
    or has drifted more than `band` of its target"""
    w = np.zeros_like(target)
    for i in range(len(target)):
        prev = w[i - 1] if i else np.zeros(target.shape[1])
        tg = target[i]
        move = (np.sign(tg) != np.sign(prev)) | (np.abs(tg - prev) > band * np.maximum(np.abs(tg), 1e-12))
        w[i] = np.where(move, tg, prev)
    return w


def weekly(target, T):
    """hold the target chosen on Mondays (UTC) all week"""
    w = np.zeros_like(target)
    for i in range(len(target)):
        if i == 0 or dt.datetime.utcfromtimestamp(T[i] / 1000).weekday() == 0:
            w[i] = target[i]
        else:
            w[i] = w[i - 1]
    return w


def xs_rank(sig, elig, frac=0.2):
    out = np.zeros_like(sig)
    for i in range(len(sig)):
        m = elig[i] & ~np.isnan(sig[i])
        if m.sum() < 10:
            continue
        v = sig[i][m]; lo, hi = np.quantile(v, [frac, 1 - frac])
        o = np.zeros(m.sum()); o[v >= hi] = 1.0; o[v <= lo] = -1.0
        out[i][m] = o
    return out


def pnl(w, r, fund, lag=1, cost=COST):
    """w decided at close i earns r[i+lag]; funding in the same period; cost on |dw|"""
    n = len(w)
    g = np.zeros(n); f = np.zeros(n); c = np.zeros(n)
    wl = np.zeros_like(w)
    wl[lag:] = w[:-lag]                  # the position actually held during day i
    g = np.nansum(wl * np.nan_to_num(r), axis=1)
    f = -np.nansum(wl * fund, axis=1)    # longs pay positive funding
    dw = np.abs(np.diff(np.vstack([np.zeros(w.shape[1]), wl]), axis=0))
    c = dw.sum(axis=1) * cost
    return g + f - c, dict(gross=g, funding=f, cost=c, gross_exp=np.abs(wl).sum(1), turnover=dw.sum(1))


def nw_t(x, L=5):
    x = np.asarray(x); n = len(x); m = x.mean(); e = x - m
    s = (e @ e) / n
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    return m / math.sqrt(s / n) if s > 0 else float('nan')


def stats(ret, T, periods=365):
    ret = np.asarray(ret)
    live = np.nonzero(np.abs(ret) > 0)[0]
    if len(live) < 60:
        return None
    ret, T = ret[live[0]:], T[live[0]:]
    q = np.array_split(ret, 4)
    eq = np.cumprod(1 + ret); dd = (1 - eq / np.maximum.accumulate(eq)).max()
    ann = ret.mean() * periods; vol = ret.std() * math.sqrt(periods)
    # calendar months
    mk = [dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m') for t in T]
    months = {}
    for m, x in zip(mk, ret):
        months[m] = months.get(m, 0.0) + x
    mv = np.array(list(months.values()))
    t = nw_t(ret)
    npos = int(sum(x.mean() > 0 for x in q))
    return dict(start=mk[0], end=mk[-1], days=len(ret), ann=ann, vol=vol, sharpe=ann / vol if vol else float('nan'),
                t=t, q=[float(x.mean() * periods) for x in q], npos=npos, maxdd=dd,
                month_mean=mv.mean(), month_pos=float((mv > 0).mean()), worst_month=mv.min(),
                admitted=bool(npos >= 3 and t >= 2 and ret.mean() > 0))


def show(name, s, extra=''):
    if not s:
        print(f"  {name:44} (too little data)"); return
    print(f"  {name:44} {s['start']}..{s['end']}  net {100*s['ann']:+6.1f}%/yr  vol {100*s['vol']:5.1f}%  "
          f"Sharpe {s['sharpe']:+.2f}  t {s['t']:+.2f}  quarters+ {s['npos']}/4  maxDD {100*s['maxdd']:4.1f}%  "
          f"month {100*s['month_mean']:+.2f}% ({100*s['month_pos']:.0f}% +)  {'ADMIT' if s['admitted'] else '-'} {extra}")


# ─── sleeves ─────────────────────────────────────────────────────────────────
def crypto_sleeves(T, close, qv, fund):
    r = returns(close)
    sd = trailing_std(r, 30)
    elig = universe(close, qv)
    sc = np.nan_to_num(vol_scale(sd))
    N = TOPN
    trend = sum(np.sign(np.nan_to_num(lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    W = {}
    W['C1'] = banded(np.where(elig, trend * sc / N, 0.0))
    W['C2'] = weekly(xs_rank(lagret(close, 14), elig) * sc / (2 * N * 0.2), T)
    # carry: rank by the trailing 7-day mean funding known at the close (21 events)
    f7 = np.full_like(fund, np.nan)
    for i in range(7, len(fund)):
        f7[i] = fund[i - 6:i + 1].sum(axis=0)
    f7[np.isnan(close)] = np.nan
    W['C3'] = weekly(-xs_rank(f7, elig) * sc / (2 * N * 0.2), T)
    return r, W, elig


def combine(parts, r, fund, lag, target_vol=0.20, lev_cap=3.0, win=60, periods=365):
    """parts: {name: weight matrix} on the same grid. Each sleeve scaled to equal
    trailing vol of its OWN unit-scale returns (past only), then the sum scaled to
    target_vol by the trailing vol of the combined unit returns (past only)."""
    unit = {k: pnl(w, r, fund, lag)[0] for k, w in parts.items()}
    n = len(r)
    sw = {}
    for k, u in unit.items():
        s = np.full(n, np.nan)
        for i in range(win, n):
            x = u[i - win:i]
            s[i] = x.std() if x.std() > 0 else np.nan
        sw[k] = np.nan_to_num(1.0 / s) / len(unit)
    comb_unit = sum(sw[k] * unit[k] for k in unit)
    L = np.zeros(n)
    for i in range(2 * win, n):
        x = comb_unit[i - win:i]
        v = x.std() * math.sqrt(periods)
        L[i] = target_vol / v if v > 0 else 0.0
    W = sum((sw[k] * L)[:, None] * parts[k] for k in parts)
    gross = np.abs(W).sum(1)
    capf = np.where(gross > lev_cap, lev_cap / np.maximum(gross, 1e-12), 1.0)
    W = W * capf[:, None]
    return W


def seasonality(bdir):
    rows = json.load(open(os.path.join(bdir, 'BTCUSDT_1h.json')))
    out = {}
    for label, cost in (('taker in + out (0.16% round trip)', 2 * COST), ('maker in + out (0.04%)', 0.0004),
                        ('before costs', 0.0)):
        daily, T = {}, []
        by = {r[0]: r for r in rows}
        for r in rows:
            h = dt.datetime.utcfromtimestamp(r[0] / 1000)
            if h.hour == 22:
                nxt = by.get(r[0] + 3600000)
                if nxt:
                    day = r[0] // DAY * DAY
                    daily[day] = nxt[4] / r[1] - 1 - cost     # buy 22:00 open, sell 23:59 close
        T = np.array(sorted(daily)); ret = np.array([daily[t] for t in T])
        out[label] = stats(ret, T)
    return out


def main(argv):
    bdir, ydir = argv[1], argv[2]
    outp = argv[argv.index('--out') + 1] if '--out' in argv else None
    R = {}
    print("loading the Binance perpetual archive ...", flush=True)
    T, syms, close, qv, fund = load_crypto(bdir)
    print(f"  {len(syms)} symbols, {dt.datetime.utcfromtimestamp(T[0]/1000):%Y-%m-%d} .. "
          f"{dt.datetime.utcfromtimestamp(T[-1]/1000):%Y-%m-%d}", flush=True)
    r, W, elig = crypto_sleeves(T, close, qv, fund)
    print(f"  universe: {int(elig.sum(1).max())} coins on the widest day; "
          f"{len(set(np.nonzero(elig)[1]))} different coins ever in the top {TOPN}\n")
    print("CRYPTO SLEEVES (net of 0.08%/turnover and actual funding)")
    for k, label in (('C1', 'C1 trend 1/2/4/8w (banded daily)'), ('C2', 'C2 cross-section momentum 2w (weekly)'),
                     ('C3', 'C3 funding carry (weekly)')):
        ret, d = pnl(W[k], r, fund, 1)
        s = stats(ret, T); R[k] = s
        show(label, s, f"| funding {100*d['funding'].mean()*365:+.1f}%/yr cost {100*d['cost'].mean()*365:.1f}%/yr "
                       f"turnover {d['turnover'].mean()*365:.0f}x")
    Wc = combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1)
    ret, d = pnl(Wc, r, fund, 1)
    R['COMBO-C'] = stats(ret, T)
    show('COMBO-C (C1+C2+C3, equal risk, 20% vol)', R['COMBO-C'],
         f"| avg gross {d['gross_exp'][d['gross_exp']>0].mean():.2f}x cost {100*d['cost'].mean()*365:.1f}%/yr")

    print("\nBTC EVENING EFFECT (C4: long 22:00-24:00 UTC daily)")
    for lab, s in seasonality(bdir).items():
        show('C4 ' + lab, s); R['C4 ' + lab] = s

    print("\nTRADITIONAL TREND (T1) on the RWA proxies, 2000-2026, one extra day of lag")
    Ty, names, cy = load_yahoo(ydir, RWA)
    ry = returns(cy); sdy = trailing_std(ry, 30); scy = np.nan_to_num(vol_scale(sdy))
    trend_y = sum(np.sign(np.nan_to_num(lagret(cy, d))) for d in (7, 14, 28, 56)) / 4.0
    Wy = banded(trend_y * scy / len(names))
    for lab, fr in (('no funding', {}), ('Bitget funding as measured', RWA_FUND),
                    ('adverse: always pay |funding|', None)):
        fund_y = np.zeros_like(cy)
        for j, n in enumerate(names):
            fund_y[:, j] = (fr or {}).get(n, 0.0) / 100.0 / 365.0
        if fr is None:
            # charge the absolute rate whatever the side: cost = |w| x |rate|
            ret, d = pnl(Wy, ry, np.zeros_like(cy), 2)
            wl = np.zeros_like(Wy); wl[2:] = Wy[:-2]
            ret = ret - np.abs(wl) @ np.array([abs(RWA_FUND[n]) / 100 / 365 for n in names])
        else:
            ret, d = pnl(Wy, ry, fund_y, 2)
        s = stats(ret, Ty); R['T1 ' + lab] = s
        show('T1 ' + lab, s)
    # the combination with crypto, on the crypto calendar
    common = np.intersect1d(T, Ty)
    ia = np.searchsorted(T, common); ib = np.searchsorted(Ty, common)
    rr = np.hstack([r[ia], ry[ib]])
    ff_meas = np.hstack([fund[ia], np.tile([RWA_FUND[n] / 100 / 365 for n in names], (len(common), 1))])
    ff_none = np.hstack([fund[ia], np.zeros((len(common), len(names)))])
    parts = {k: np.hstack([W[k][ia], np.zeros((len(common), len(names)))]) for k in ('C1', 'C2', 'C3')}
    parts['T1'] = np.hstack([np.zeros((len(common), len(syms))), Wy[ib]])
    for lab, ff in (('no RWA funding', ff_none), ('RWA funding as measured', ff_meas)):
        Wct = combine(parts, rr, ff, 1)
        ret, d = pnl(Wct, rr, ff, 1)
        s = stats(ret, common); R['COMBO-CT ' + lab] = s
        show('COMBO-CT (+T1) ' + lab, s)

    print("\nWHAT 2-4%/MONTH WOULD HAVE COST (COMBO-C scaled to each target, same path)")
    base = R['COMBO-C']
    Wc_ret, _ = pnl(Wc, r, fund, 1)
    live = np.nonzero(np.abs(Wc_ret) > 0)[0]
    x = Wc_ret[live[0]:]
    for m in (0.01, 0.02, 0.03, 0.04):
        k = m / max(x.mean() * 30.4, 1e-12)
        y = x * k
        eq = np.cumprod(1 + y); dd = (1 - eq / np.maximum.accumulate(eq)).max()
        print(f"  target {100*m:.0f}%/month -> scale {k:4.2f}x, annual vol {100*y.std()*math.sqrt(365):5.1f}%, "
              f"max drawdown {100*dd:5.1f}%, worst day {100*y.min():+.1f}%")
    if outp:
        json.dump(R, open(outp, 'w'), indent=1, default=float)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
