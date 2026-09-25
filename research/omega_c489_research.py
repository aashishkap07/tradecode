#!/usr/bin/env python3
"""C489 research engine: the pre-registered intraday hypotheses.

    python3 research/omega_c489_research.py H1_DIR BNC_DIR [--out results.json]

H1_DIR  : <SYM>.json hourly [t, o, h, l, c, quote_vol, taker_buy_quote_vol]
          (research/c489_fetch_h1.py, Binance USDT-M archive)
BNC_DIR : the C488 daily archive (k/, f/) -- the daily universe and 8h funding.

Every rule, feature, parameter and the admission bar are fixed in
research/c489_preregistration.md (committed before any test). This file
implements exactly that. All maths is numpy; the logistic regression is a
Newton solver written here, so the bot needs no new dependency.
"""
import os, sys, json, glob, math, time, datetime as dt, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R488

H = 3600000
DAY = 86400000
COST = 0.0008            # per unit of turnover (0.06% taker + 0.02% half-spread)
HOLD = 4
TOPN = 40
OOS_FROM = int(dt.datetime(2021, 7, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
warnings.simplefilter('ignore')


# ─── data ────────────────────────────────────────────────────────────────────
def load(h1dir, bdir):
    syms = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(h1dir, '*.json')))
    rows = {s: json.load(open(os.path.join(h1dir, s + '.json'))) for s in syms}
    syms = [s for s in syms if len(rows[s]) > 24 * 30]
    t0 = min(rows[s][0][0] for s in syms) // H * H
    t1 = max(rows[s][-1][0] for s in syms) // H * H
    T = np.arange(t0, t1 + H, H, dtype=np.int64)
    n, k = len(T), len(syms)
    O = np.full((n, k), np.nan); Hh = O.copy(); L = O.copy(); C = O.copy(); QV = O.copy(); TB = O.copy()
    for j, s in enumerate(syms):
        a = np.array(rows[s], dtype=float)
        idx = ((a[:, 0].astype(np.int64) - t0) // H).astype(int)
        O[idx, j], Hh[idx, j], L[idx, j], C[idx, j], QV[idx, j], TB[idx, j] = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5], a[:, 6]
    # daily point-in-time universe (the C488 rule) mapped onto hours
    Td, dsyms, dclose, dqv, dfund = R488.load_crypto(bdir)
    R488.TOPN = TOPN
    el = R488.universe(dclose, dqv)
    col = {s: i for i, s in enumerate(dsyms)}
    U = np.zeros((n, k), bool)
    di = np.searchsorted(Td, (T // DAY) * DAY)
    di = np.clip(di, 0, len(Td) - 1)
    for j, s in enumerate(syms):
        if s in col:
            U[:, j] = el[di, col[s]] & ~np.isnan(C[:, j])
    # funding events, per hour
    F = np.zeros((n, k))
    for j, s in enumerate(syms):
        fp = os.path.join(bdir, 'f', s + '.json')
        if os.path.exists(fp):
            for t, rate in json.load(open(fp)):
                i = (t // H * H - t0) // H
                if 0 <= i < n:
                    F[i, j] += rate
    return T, syms, O, Hh, L, C, QV, TB, U, F


# ─── rolling helpers (pandas-free, NaN-aware) ────────────────────────────────
def roll_sum(x, w):
    c = np.nancumsum(np.nan_to_num(x), axis=0)
    out = np.full_like(x, np.nan, dtype=float)
    out[w:] = c[w:] - c[:-w]
    out[w - 1] = c[w - 1]
    return out


def roll_mean(x, w):
    s = roll_sum(np.nan_to_num(x), w)
    n = roll_sum((~np.isnan(x)).astype(float), w)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(n >= w * 0.8, s / n, np.nan)


def roll_std(x, w):
    m = roll_mean(x, w)
    m2 = roll_mean(x * x, w)
    with np.errstate(invalid='ignore'):
        return np.sqrt(np.maximum(m2 - m * m, 0.0))


def roll_median(x, w, step=1):
    """rolling median via sliding windows, per column (exact)"""
    out = np.full_like(x, np.nan, dtype=float)
    from numpy.lib.stride_tricks import sliding_window_view
    for j in range(x.shape[1]):
        v = sliding_window_view(x[:, j], w)
        out[w - 1:, j] = np.nanmedian(v, axis=1)
    return out


def lag(x, n):
    out = np.full_like(x, np.nan, dtype=float)
    out[n:] = x[:-n]
    return out


# ─── features ────────────────────────────────────────────────────────────────
def perm_entropy(r, w=48):
    """normalised permutation entropy, order 3, over the last w returns"""
    a, b, c = r[:-2], r[1:-1], r[2:]
    pat = np.full(r.shape, -1, dtype=np.int8)
    code = np.select([(a < b) & (b < c), (a < c) & (c <= b), (c <= a) & (a < b),
                      (b <= a) & (a < c), (b < c) & (c <= a), (c <= b) & (b <= a)],
                     [0, 1, 2, 3, 4, 5], default=-1)
    code[np.isnan(a) | np.isnan(b) | np.isnan(c)] = -1
    pat[2:] = code
    m = w - 2
    P = np.stack([roll_sum((pat == p).astype(float), m) for p in range(6)])
    tot = P.sum(0)
    with np.errstate(divide='ignore', invalid='ignore'):
        q = P / tot
        h = -np.nansum(np.where(q > 0, q * np.log(q), 0.0), axis=0) / math.log(6)
    return np.where(tot >= m * 0.9, h, np.nan)


def dfa_hurst(r, rows, w=168, scales=(8, 14, 28, 56)):
    """DFA Hurst exponent of the last w returns, computed only at `rows`"""
    out = np.full(len(r), np.nan)
    rows = rows[rows >= w]
    if len(rows) == 0:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    v = sliding_window_view(np.nan_to_num(r), w)[rows - w + 1]           # (m, w)
    ok = ~np.isnan(sliding_window_view(r, w)[rows - w + 1]).any(1)
    y = np.cumsum(v - v.mean(1, keepdims=True), axis=1)
    logF = []
    for s in scales:
        seg = y[:, : (w // s) * s].reshape(len(rows), w // s, s)
        x = np.arange(s, dtype=float); xm = x.mean(); xv = ((x - xm) ** 2).sum()
        ym = seg.mean(2, keepdims=True)
        b = ((seg - ym) * (x - xm)).sum(2, keepdims=True) / xv
        res = seg - ym - b * (x - xm)
        F = np.sqrt((res ** 2).mean(axis=(1, 2)))
        logF.append(np.log(np.maximum(F, 1e-18)))
    ls = np.log(np.array(scales, dtype=float)); lsm = ls.mean()
    LF = np.stack(logF, 1)
    slope = ((LF - LF.mean(1, keepdims=True)) * (ls - lsm)).sum(1) / ((ls - lsm) ** 2).sum()
    out[rows] = np.where(ok, slope, np.nan)
    return out


def markov_edges(z, w=720):
    """per-column Markov edge P(up) - P(down) next hour, 1st and 2nd order,
    rolling w transitions, Laplace-smoothed. States: z < -0.5, middle, > 0.5."""
    n, k = z.shape
    s = np.where(np.isnan(z), -1, np.where(z < -0.5, 0, np.where(z > 0.5, 2, 1))).astype(np.int8)
    mk1 = np.full((n, k), np.nan); mk2 = np.full((n, k), np.nan)
    for j in range(k):
        st = s[:, j]
        prev = np.r_[-1, st[:-1]]; prev2 = np.r_[-1, -1, st[:-2]]
        valid1 = (prev >= 0) & (st >= 0)
        valid2 = valid1 & (prev2 >= 0)
        # counts of transitions (a -> b) completed by hour u, windowed
        c1 = np.zeros((3, 3, n)); c2 = np.zeros((3, 3, 3, n))
        for a in range(3):
            for b in range(3):
                c1[a, b] = roll_sum(((prev == a) & (st == b) & valid1).astype(float)[:, None], w)[:, 0]
                for c in range(3):
                    c2[a, b, c] = roll_sum(((prev2 == a) & (prev == b) & (st == c) & valid2).astype(float)[:, None], w)[:, 0]
        cur = st; last = prev
        ok1 = cur >= 0
        idx = np.where(ok1, cur, 0)
        up = c1[idx, 2, np.arange(n)]; dn = c1[idx, 0, np.arange(n)]; tot = c1[idx, :, np.arange(n)].sum(1)
        mk1[:, j] = np.where(ok1, (up + 1) / (tot + 3) - (dn + 1) / (tot + 3), np.nan)
        ok2 = ok1 & (last >= 0)
        li = np.where(ok2, last, 0)
        up2 = c2[li, idx, 2, np.arange(n)]; dn2 = c2[li, idx, 0, np.arange(n)]; tot2 = c2[li, idx, :, np.arange(n)].sum(1)
        mk2[:, j] = np.where(ok2, (up2 + 1) / (tot2 + 3) - (dn2 + 1) / (tot2 + 3), np.nan)
    return mk1, mk2


def features(T, syms, O, Hh, L, C, QV, TB, U, F):
    t0 = time.time()
    r1 = C / lag(C, 1) - 1
    sig = roll_std(r1, 168)
    f = {}
    f['z_r1'] = r1 / sig
    f['z_r4'] = (C / lag(C, 4) - 1) / (sig * 2.0)
    f['z_r24'] = (C / lag(C, 24) - 1) / (sig * math.sqrt(24))
    r4 = C / lag(C, 4) - 1
    x = np.where(U, r4, np.nan)
    f['xs_r4'] = (np.argsort(np.argsort(np.where(np.isnan(x), np.inf, x), axis=1), axis=1)
                  / np.maximum((~np.isnan(x)).sum(1, keepdims=True) - 1, 1))
    f['xs_r4'] = np.where(np.isnan(x), np.nan, f['xs_r4'])
    with np.errstate(invalid='ignore', divide='ignore'):
        share1 = TB / QV
        share4 = roll_sum(TB, 4) / roll_sum(QV, 4)
    f['flow1'] = (share1 - roll_mean(share1, 168)) / roll_std(share1, 168)
    f['flow4'] = (share4 - roll_mean(share4, 168)) / roll_std(share4, 168)
    print(f"   returns/flow {time.time()-t0:.0f}s", flush=True)
    with np.errstate(invalid='ignore', divide='ignore'):
        f['vsurp'] = np.log(QV / roll_median(QV, 168))
    f['volreg'] = roll_std(r1, 24) / sig
    print(f"   volume {time.time()-t0:.0f}s", flush=True)
    b = syms.index('BTCUSDT')
    rb = r1[:, [b]]
    cov = roll_mean(r1 * rb, 168) - roll_mean(r1, 168) * roll_mean(rb, 168)
    var = roll_mean(rb * rb, 168) - roll_mean(rb, 168) ** 2
    beta = cov / var
    res1 = r1 - beta * rb
    f['resid4'] = (r4 - beta * r4[:, [b]]) / (roll_std(res1, 168) * 2.0)
    f['btc4'] = np.repeat(f['z_r4'][:, [b]], len(syms), axis=1)
    # funding: the latest rate, z-scored against the coin's own past 30 days
    last = np.where(F != 0, F, np.nan)
    for j in range(F.shape[1]):
        v = last[:, j]; m = ~np.isnan(v)
        if m.any():
            idx = np.where(m, np.arange(len(v)), 0); np.maximum.accumulate(idx, out=idx)
            last[:, j] = np.where(np.arange(len(v)) >= np.argmax(m), v[idx], np.nan)
    f['fundz'] = (last - roll_mean(last, 720)) / roll_std(last, 720)
    print(f"   beta/funding {time.time()-t0:.0f}s", flush=True)
    f['pe'] = np.column_stack([perm_entropy(r1[:, j]) for j in range(r1.shape[1])])
    f['hurst'] = np.column_stack([dfa_hurst(r1[:, j], np.nonzero(U[:, j])[0]) for j in range(r1.shape[1])])
    print(f"   chaos {time.time()-t0:.0f}s", flush=True)
    f['mk1'], f['mk2'] = markov_edges(f['z_r1'])
    print(f"   markov {time.time()-t0:.0f}s", flush=True)
    from numpy.lib.stride_tricks import sliding_window_view
    hi24 = np.full_like(Hh, np.nan); lo24 = np.full_like(L, np.nan)
    hi24[23:] = np.nanmax(sliding_window_view(Hh, 24, axis=0), axis=-1)
    lo24[23:] = np.nanmin(sliding_window_view(L, 24, axis=0), axis=-1)
    with np.errstate(invalid='ignore', divide='ignore'):
        f['rpos'] = (C - lo24) / (hi24 - lo24)
    print(f"   done {time.time()-t0:.0f}s", flush=True)
    return r1, f


FEATS = ['z_r1', 'z_r4', 'z_r24', 'xs_r4', 'flow1', 'flow4', 'vsurp', 'volreg', 'resid4', 'btc4',
         'fundz', 'pe', 'hurst', 'mk1', 'mk2', 'rpos']


# ─── portfolios ──────────────────────────────────────────────────────────────
def quintile_book(sig, U, frac=0.2):
    """one cohort per hour: +1/n_long top fifth, -1/n_short bottom fifth, gross 1"""
    q = np.zeros_like(sig)
    for i in range(len(sig)):
        m = U[i] & ~np.isnan(sig[i])
        if m.sum() < 10:
            continue
        v = sig[i][m]
        lo, hi = np.quantile(v, [frac, 1 - frac])
        o = np.zeros(m.sum())
        L_ = v >= hi; S_ = v <= lo
        if hi == lo:
            continue
        o[L_] = 0.5 / L_.sum(); o[S_] = -0.5 / S_.sum()
        q[i][m] = o
    return q


def overlap(q, hold=HOLD):
    w = np.zeros_like(q)
    for k in range(hold):
        w[k:] += q[:len(q) - k] / hold
    return w


def hourly_pnl(w, r1, F, cost=COST):
    """w decided at the close of hour i earns hour i+1's return and its funding"""
    wl = np.zeros_like(w); wl[1:] = w[:-1]
    g = np.nansum(wl * np.nan_to_num(r1), axis=1)
    fu = -np.nansum(wl * F, axis=1)
    dw = np.abs(np.diff(np.vstack([np.zeros(w.shape[1]), wl]), axis=0)).sum(1)
    return g + fu - dw * cost, dict(gross=g, funding=fu, cost=dw * cost, turnover=dw)


def to_daily(T, x):
    d = (T // DAY) * DAY
    u, inv = np.unique(d, return_inverse=True)
    return u, np.bincount(inv, weights=x)


# ─── the probability model (numpy logistic, L2, Newton) ──────────────────────
def logit_fit(X, y, C=0.1, iters=25):
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(p + 1)
    reg = np.eye(p + 1) / C; reg[0, 0] = 0.0
    for _ in range(iters):
        z = Xb @ w
        pr = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        g = Xb.T @ (pr - y) + reg @ w
        Hs = (Xb * (pr * (1 - pr))[:, None]).T @ Xb + reg
        step = np.linalg.solve(Hs, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


def logit_predict(w, X):
    return 1.0 / (1.0 + np.exp(-np.clip(np.hstack([np.ones((len(X), 1)), X]) @ w, -30, 30)))


def xs_standardise(Fm, U):
    out = {}
    for k, v in Fm.items():
        x = np.where(U, v, np.nan)
        mu = np.nanmean(x, axis=1, keepdims=True); sd = np.nanstd(x, axis=1, keepdims=True)
        with np.errstate(invalid='ignore', divide='ignore'):
            out[k] = np.clip((x - mu) / sd, -5, 5)
    return out


def model_signal(T, C, U, Z, retrain_days=30, train_days=180, Cl=0.1):
    """walk-forward: out-of-sample predicted probability for every hour from OOS_FROM"""
    n, k = C.shape
    fwd = np.vstack([C[HOLD:] / C[:-HOLD] - 1, np.full((HOLD, k), np.nan)])      # the next 4 hours
    rel = fwd - np.nanmedian(np.where(U, fwd, np.nan), axis=1, keepdims=True)
    P = np.full((n, k), np.nan)
    gate = np.zeros(n, bool)
    t = OOS_FROM
    fits = 0
    while t < T[-1]:
        a = np.searchsorted(T, t - train_days * DAY); b = np.searchsorted(T, t - HOLD * H)   # no look-ahead
        e = np.searchsorted(T, t + retrain_days * DAY)
        rows_i, rows_j = np.nonzero(U[a:b])
        rows_i = rows_i + a
        X = np.column_stack([Z[f][rows_i, rows_j] for f in FEATS]); y = rel[rows_i, rows_j]
        ok = ~np.isnan(X).any(1) & ~np.isnan(y)
        X, y = np.nan_to_num(X[ok]), (y[ok] > 0).astype(float)
        if len(y) < 5000:
            t += retrain_days * DAY; continue
        w = logit_fit(X, y, Cl)
        fits += 1
        # calibrate the gate on the training window: predicted-probability spread -> realised spread
        Xt = np.stack([Z[f][a:b] for f in FEATS], -1)
        ptr = logit_predict(w, np.nan_to_num(Xt).reshape(-1, len(FEATS))).reshape(b - a, k)
        ptr[np.isnan(Xt).any(-1) | ~U[a:b]] = np.nan
        sp_p, sp_r = [], []
        for i in range(b - a):
            m = ~np.isnan(ptr[i]) & ~np.isnan(fwd[a + i])
            if m.sum() < 10: continue
            v = ptr[i][m]; lo, hi = np.quantile(v, [0.2, 0.8])
            top = v >= hi; bot = v <= lo
            sp_p.append(v[top].mean() - v[bot].mean())
            sp_r.append(fwd[a + i][m][top].mean() - fwd[a + i][m][bot].mean())
        sp_p, sp_r = np.array(sp_p), np.array(sp_r)
        A = np.vstack([np.ones_like(sp_p), sp_p]).T
        coef = np.linalg.lstsq(A, sp_r, rcond=None)[0]
        # predict out-of-sample
        s0 = np.searchsorted(T, t)
        Xo = np.stack([Z[f][s0:e] for f in FEATS], -1)
        po = logit_predict(w, np.nan_to_num(Xo).reshape(-1, len(FEATS))).reshape(e - s0, k)
        bad = np.isnan(Xo).any(-1) | ~U[s0:e]
        po[bad] = np.nan
        P[s0:e] = po
        for i in range(e - s0):
            m = ~np.isnan(po[i])
            if m.sum() < 10: continue
            v = po[i][m]; lo, hi = np.quantile(v, [0.2, 0.8])
            gate[s0 + i] = (coef[0] + coef[1] * (v[v >= hi].mean() - v[v <= lo].mean())) > 2 * COST
        t += retrain_days * DAY
    return P, gate, fits


def main(argv):
    h1dir, bdir = argv[1], argv[2]
    outp = argv[argv.index('--out') + 1] if '--out' in argv else None
    t0 = time.time()
    T, syms, O, Hh, L, C, QV, TB, U, F = load(h1dir, bdir)
    print(f"{len(syms)} coins, {len(T)} hours, {dt.datetime.utcfromtimestamp(T[0]/1000):%Y-%m-%d} .. "
          f"{dt.datetime.utcfromtimestamp(T[-1]/1000):%Y-%m-%d}; universe {int(U.sum(1).max())} max  [{time.time()-t0:.0f}s]", flush=True)
    r1, Fm = features(T, syms, O, Hh, L, C, QV, TB, U, F)
    oos = T >= OOS_FROM
    res = {}
    sig = {
        'H1 1h reversal (-z_r1)': -Fm['z_r1'],
        'H2 24h continuation (+z_r24)': Fm['z_r24'],
        'H3 buying pressure persists (+flow4)': Fm['flow4'],
        'H4 Markov 1st order (+mk1)': Fm['mk1'],
        'H5 Markov 2nd order (+mk2)': Fm['mk2'],
        'H6 chaos switch (Hurst/PE)': np.where((Fm['hurst'] > 0.55) & (Fm['pe'] < np.nanmedian(np.where(U, Fm['pe'], np.nan), axis=1, keepdims=True)),
                                               Fm['z_r24'], np.where(Fm['hurst'] < 0.45, -Fm['z_r4'], np.nan)),
        'H7 catch-up to BTC (-resid4)': -Fm['resid4'],
        'H8 fade crowded funding (-fundz)': -Fm['fundz'],
    }
    print("\nINTRADAY HYPOTHESES (4-hour hold, overlapping cohorts, 0.08%/turnover, real funding; OOS 2021-07 on)")
    daily = {}
    for name, s in sig.items():
        w = overlap(quintile_book(np.where(U, s, np.nan), U))
        hp, d = hourly_pnl(w, r1, F)
        du, dr = to_daily(T[oos], hp[oos])
        st = R488.stats(dr, du); res[name] = st; daily[name] = (du, dr)
        R488.show(name, st, f"| gross {100*d['gross'][oos].mean()*24*365:+.0f}%/yr cost {100*d['cost'][oos].mean()*24*365:.0f}%/yr")
    print(f"\nPROBABILITY MODEL (walk-forward logistic, retrain 30d on 180d)  [{time.time()-t0:.0f}s]", flush=True)
    Z = xs_standardise(Fm, U)
    P, gate, fits = model_signal(T, C, U, Z)
    w = overlap(quintile_book(P, U))
    hp, d = hourly_pnl(w, r1, F)
    du, dr = to_daily(T[oos], hp[oos]); st = R488.stats(dr, du); res['M1'] = st; daily['M1'] = (du, dr)
    R488.show(f'M1 probability model ({fits} fits)', st, f"| gross {100*d['gross'][oos].mean()*24*365:+.0f}%/yr cost {100*d['cost'][oos].mean()*24*365:.0f}%/yr")
    qg = quintile_book(P, U); qg[~gate] = 0.0
    w = overlap(qg)
    hp, d = hourly_pnl(w, r1, F)
    du, dr = to_daily(T[oos], hp[oos]); st = R488.stats(dr, du); res['M1g'] = st; daily['M1g'] = (du, dr)
    R488.show(f'M1g gated ({100*gate[oos].mean():.0f}% of hours traded)', st,
              f"| gross {100*d['gross'][oos].mean()*24*365:+.0f}%/yr cost {100*d['cost'][oos].mean()*24*365:.0f}%/yr")
    # correlation with the C488 book
    Td, dsyms, dclose, dqv, dfund = R488.load_crypto(bdir)
    R488.TOPN = 20
    r, Wd, _ = R488.crypto_sleeves(Td, dclose, dqv, dfund)
    Wc = R488.combine({k: Wd[k] for k in ('C1', 'C2', 'C3')}, r, dfund, 1)
    book = dict(zip(Td.tolist(), R488.pnl(Wc, r, dfund, 1)[0]))
    print("\nCORRELATION WITH THE C488 BOOK (daily)")
    for name, (du, dr) in daily.items():
        common = [i for i, d_ in enumerate(du) if d_ in book]
        x = dr[common]; y = np.array([book[du[i]] for i in common])
        if len(x) > 60 and x.std() > 0:
            print(f"  {name:44} rho {np.corrcoef(x, y)[0, 1]:+.2f}")
            res[name]['rho_book'] = float(np.corrcoef(x, y)[0, 1])
    if outp:
        json.dump(res, open(outp, 'w'), indent=1, default=float)
    print(f"\n[{time.time()-t0:.0f}s]")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
