#!/usr/bin/env python3
"""Round 14 (C521): was the research tested correctly, and can the book adjust itself better?
Pre-registered in research/c521_preregistration.md (pushed first, 4ff6175).

    python3 research/omega_c521_research.py BNC_DIR [A|B|C|all]     (Part D: research/c521_delta.py)

The book is built with the BOT's own functions (_c488_sleeves, _c488_combine,
_c488_combine_ewma, the n2n3 rule), checked to the last bit against a
parameterised copy that the grid (A4) and the new candidates (B1, B2) need.
Costs 0.07% per unit turnover (Binance), funding as paid, $500 with Binance's
minimums (max($6, the coin's minimum)), dial 20% (vol target 26.7%), top 20.
"""
import os, sys, io, json, glob, math, time, itertools, tempfile, contextlib, warnings, importlib.util, datetime as dt
import numpy as np

warnings.simplefilter('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from omega_c493_research import TRADFI                     # the research's 62 non-crypto names (+USDT)
import omega_c488_research as R
spec = importlib.util.spec_from_file_location('om', os.path.join(REPO, 'omega_v60_reconstructed.py'))
om = importlib.util.module_from_spec(spec)
os.environ.setdefault('OMEGA_BASE_PATH', tempfile.mkdtemp(prefix='c521_research_'))
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    spec.loader.exec_module(om)

DAY = 86400000
EQ, COST, TOPN, TV, LEV = 500.0, 0.0007, 20, 0.20 * 4 / 3, 3.0
BIG = {'BTCUSDT': 50.0, 'ETHUSDT': 20.0, 'LINKUSDT': 20.0, 'LTCUSDT': 20.0, 'BCHUSDT': 20.0, 'ETCUSDT': 20.0}
EXCL = set(R.EXCLUDE) | set(TRADFI)                         # exactly the research's exclusions
HOLD0 = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
OUT = {}


def load(bdir, drop_delisted=False):
    syms, K, F = [], {}, {}
    for p in sorted(glob.glob(os.path.join(bdir, 'k', '*.json'))):
        s = os.path.basename(p)[:-5]
        if s in EXCL:
            continue
        rows = json.load(open(p))
        if len(rows) < 120:
            continue
        K[s] = rows
        fp = os.path.join(bdir, 'f', s + '.json')
        F[s] = json.load(open(fp)) if os.path.exists(fp) else []
        syms.append(s)
    t1 = max(K[s][-1][0] for s in syms) // DAY * DAY
    if drop_delisted:
        syms = [s for s in syms if K[s][-1][0] >= t1 - 30 * DAY]
    t0 = min(K[s][0][0] for s in syms) // DAY * DAY
    T = np.arange(t0, t1 + DAY, DAY)
    idx = {t: i for i, t in enumerate(T)}
    n, k = len(T), len(syms)
    o, h, l, c, qv = (np.full((n, k), np.nan) for _ in range(5))
    fund = np.zeros((n, k))
    for j, s in enumerate(syms):
        for r in K[s]:
            i = idx.get(r[0] // DAY * DAY)
            if i is not None:
                o[i, j], h[i, j], l[i, j], c[i, j], qv[i, j] = r[1], r[2], r[3], r[4], r[6]
        for t, rate in F[s]:
            i = idx.get(t // DAY * DAY)
            if i is not None:
                fund[i, j] += rate
    return T, syms, o, h, l, c, qv, fund


# ── the book, parameterised (A4, B1) ─────────────────────────────────────────
def beta_mkt(close, r, elig):
    n = len(close)
    mkt = np.nan_to_num(np.nanmean(np.where(elig, r, np.nan), axis=1))
    beta = np.ones_like(close)
    for i in range(60, n):
        m = mkt[i - 59:i + 1]; vm = m.var()
        if vm <= 0:
            continue
        ri = r[i - 59:i + 1]; ok = ~np.isnan(ri)
        cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
        b = cov / vm; b[ok.sum(0) < 40] = np.nan
        beta[i] = np.where(np.isnan(b), 1.0, b)
    return mkt, beta


def lagret_k(close, k):
    """close[i] / close[i - k_i] - 1, with k a scalar or one lookback per day (the market clock)"""
    n = len(close)
    if np.isscalar(k):
        return om._c488_lagret(close, int(k))
    kk = np.asarray(k, int)
    out = np.full_like(close, np.nan)
    for i in range(n):
        if 0 < kk[i] <= i:
            out[i] = close[i] / close[i - kk[i]] - 1
    return out


def mret_k(mkt, k):
    n = len(mkt)
    kk = np.full(n, int(k)) if np.isscalar(k) else np.asarray(k, int)
    c = np.concatenate([[0.0], np.cumsum(np.log1p(mkt))])
    out = np.full(n, np.nan)
    for i in range(n):
        if 0 < kk[i] <= i:
            out[i] = math.exp(c[i + 1] - c[i + 1 - kk[i]]) - 1
    return out


def sleeves(D, l2=14, f3=7, hz=(7, 14, 28, 56), topn=TOPN, sd=None, clock=None):
    """the n2n3 sleeves with chosen lookbacks. clock: a function H -> per-day lookback (B1)"""
    T, close, r, qv, fund = D['T'], D['c'], D['r'], D['qv'], D['fund']
    elig = D['elig'][topn]
    mkt, beta = D['beta'][topn]
    sd = D['sd30'] if sd is None else sd
    sc = np.nan_to_num(om._c488_vol_scale(sd))
    L = (lambda H: clock(H)) if clock is not None else (lambda H: H)
    trend = sum(np.sign(np.nan_to_num(lagret_k(close, L(H)))) for H in hz) / 4.0
    f7 = om._c510_f7(fund, close)
    fw = f7 if f3 == 7 else _fwin(fund, close, f3)
    s = om._c488_xs_rank(lagret_k(close, L(l2)) - beta * mret_k(mkt, L(l2))[:, None], elig)
    s = np.where((s < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s)       # N2 keeps its 7-day rule
    W = {'C1': om._c488_banded(np.where(elig, trend * sc / topn, 0.0)),
         'C2': om._c488_weekly(s * sc / (2 * topn * 0.2), T),
         'C3': om._c488_weekly(-om._c488_xs_rank(fw, elig) * sc / (2 * topn * 0.2), T)}
    return W


def _fwin(fund, close, w):
    out = np.full_like(fund, np.nan)
    for i in range(w, len(fund)):
        out[i] = fund[i - w + 1:i + 1].sum(axis=0)
    out[np.isnan(close)] = np.nan
    return out


def book(D, W, sizing='base', scale=None):
    parts = {k: W[k] for k in ('C1', 'C2', 'C3')}
    if sizing == 'k4':
        Wc = om._c488_combine_ewma(parts, D['r'], D['fund'], 1, target_vol=TV, lev_cap=LEV)
    elif sizing == 'exante':
        Wc = combine_exante(D, parts)
    else:
        Wc = om._c488_combine(parts, D['r'], D['fund'], 1, target_vol=TV, lev_cap=LEV)
    if scale is not None:
        Wc = Wc * scale[:, None]
    Wc = np.where(np.abs(Wc) * EQ >= D['floor'][None, :], Wc, 0.0)
    x, info = om._c488_pnl(Wc, D['r'], D['fund'], 1, cost=COST)
    return x, Wc, info


def returns_of(x, D):
    live = np.nonzero(np.abs(x) > 0)[0]
    a = live[0] + 1 if len(live) else 0
    return x[a:], D['T'][a:]


# ── statistics ──────────────────────────────────────────────────────────────
def sstats(x, T):
    eq = np.cumprod(1 + x); dd = float((1 - eq / np.maximum.accumulate(eq)).max())
    mk = [dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m') for t in T]
    mon = {}
    for m, v in zip(mk, x):
        mon[m] = (1 + mon.get(m, 0.0)) * (1 + v) - 1
    mv = np.array(list(mon.values()))
    return dict(ann=float(x.mean() * 365), vol=float(x.std() * math.sqrt(365)),
                sharpe=float(x.mean() / x.std() * math.sqrt(365)), maxdd=dd, worst_month=float(mv.min()),
                cagr=float(eq[-1] ** (365 / len(x)) - 1), t=float(nw_t(x)))


def nw_t(x, L=5):
    x = np.asarray(x); n = len(x); m = x.mean(); e = x - m
    s = (e @ e) / n
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    return m / math.sqrt(s / n) if s > 0 else float('nan')


def lw_sharpe_diff(a, b):
    """Ledoit & Wolf (2008), HAC version: H0 SR_a <= SR_b. Delta method on
    (mu_a, mu_b, E a^2, E b^2) with a Bartlett-kernel long-run covariance."""
    a, b = np.asarray(a), np.asarray(b); n = len(a)
    ma, mb = a.mean(), b.mean(); ga, gb = (a * a).mean(), (b * b).mean()
    sa, sb = math.sqrt(ga - ma * ma), math.sqrt(gb - mb * mb)
    d = ma / sa - mb / sb
    y = np.column_stack([a - ma, b - mb, a * a - ga, b * b - gb])
    L = int(round(4 * (n / 100) ** (2 / 9)))
    S = y.T @ y / n
    for l in range(1, L + 1):
        G = y[l:].T @ y[:-l] / n
        S += (1 - l / (L + 1)) * (G + G.T)
    grad = np.array([ga / (ga - ma * ma) ** 1.5, -gb / (gb - mb * mb) ** 1.5,
                     -0.5 * ma / (ga - ma * ma) ** 1.5, 0.5 * mb / (gb - mb * mb) ** 1.5])
    se = math.sqrt(max(grad @ S @ grad / n, 1e-30))
    z = d / se
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return d * math.sqrt(365), z, p


def compare(name, xv, Tv, xb, Tb):
    """variant vs base on their common days: Sharpe difference (HAC), quarters, holdout, matched vol"""
    common = np.intersect1d(Tv, Tb)
    a = xv[np.isin(Tv, common)]; b = xb[np.isin(Tb, common)]
    d_sr, z, p = lw_sharpe_diff(a, b)
    q = [(sa.mean() / sa.std() - sb.mean() / sb.std()) * math.sqrt(365)
         for sa, sb in zip(np.array_split(a, 4), np.array_split(b, 4))]
    h = common >= HOLD0
    hold = (a[h].mean() / a[h].std() - b[h].mean() / b[h].std()) * math.sqrt(365)
    am = a * (b.std() / a.std())                       # the variant at the base's volatility
    sa_, sb_ = sstats(am, common), sstats(b, common)
    ok = (p < 0.05 and sum(v > 0 for v in q) >= 3 and hold > 0 and sa_['maxdd'] <= sb_['maxdd'] + 0.02)
    r = dict(name=name, d_sharpe=d_sr, z=z, p=p, quarters=q, holdout=hold, matched=sa_, base=sb_,
             raw=sstats(a, common), admitted=bool(ok))
    print(f"  {name:34} ΔSharpe {d_sr:+.2f} (z {z:+.2f}, p {p:.3f}) | quarters {' '.join(f'{v:+.2f}' for v in q)} | "
          f"holdout {hold:+.2f} | at equal vol: {100 * sa_['ann']:+.1f}%/yr vs {100 * sb_['ann']:+.1f}%, "
          f"max DD {100 * sa_['maxdd']:.1f}% vs {100 * sb_['maxdd']:.1f}%, worst month "
          f"{100 * sa_['worst_month']:+.1f}% vs {100 * sb_['worst_month']:+.1f}% -> {'ADMIT' if ok else 'not admitted'}")
    return r


# ── B1: the market's own clock ──────────────────────────────────────────────
def market_clock(D, topn=TOPN, lo=0.25, hi=4.0):
    elig = D['elig'][topn]; r = D['r']
    m2 = np.nanmean(np.where(elig, r * r, np.nan), axis=1)
    m2 = np.where(np.isfinite(m2), m2, np.nan)
    n = len(m2); dtau = np.ones(n)
    for i in range(n):
        w = m2[max(0, i - 364):i + 1]; w = w[np.isfinite(w)]
        if len(w) >= 60 and np.isfinite(m2[i]) and w.mean() > 0:
            dtau[i] = min(max(m2[i] / w.mean(), lo), hi)
    cum = np.concatenate([[0.0], np.cumsum(dtau)])          # cum[i+1] = clock through day i

    def lookback(H):
        k = np.zeros(n, int)
        for i in range(n):
            # the fewest days k with cum[i+1] - cum[i+1-k] >= H
            target = cum[i + 1] - H
            j = np.searchsorted(cum, target, side='right') - 1   # cum[j] <= target
            k[i] = max(1, min(i + 1 - j, int(4 * H))) if j >= 0 else int(H)
        return k
    return dtau, lookback


# ── B2: ex-ante risk of the book held now ────────────────────────────────────
def combine_exante(D, parts, hl_v=10.0, hl_c=30.0, shrink=0.5, win=60, periods=365):
    r, fund = D['r'], D['fund']
    unit = {k: om._c488_pnl(w, r, fund, 1)[0] for k, w in parts.items()}
    n, k = r.shape
    sw = {}
    for name, u in unit.items():
        s = np.full(n, np.nan)
        for i in range(win, n):
            x = u[i - win:i]
            s[i] = x.std() if x.std() > 0 else np.nan
        sw[name] = np.nan_to_num(1.0 / s) / len(unit)
    Wu = sum(sw[name][:, None] * parts[name] for name in parts)       # the unit book decided at close i
    av, ac = 1 - 0.5 ** (1 / hl_v), 1 - 0.5 ** (1 / hl_c)
    rz = np.nan_to_num(r)
    var = np.zeros(k); cov = np.zeros((k, k)); seen = np.zeros(k, int)
    L = np.zeros(n)
    for i in range(n):
        x = rz[i]
        live = ~np.isnan(r[i])
        var = np.where(live, (1 - av) * var + av * x * x, var)
        cov = (1 - ac) * cov + ac * np.outer(x, x)
        seen += live
        if i < 2 * win:
            continue
        w = Wu[i]; j = np.nonzero(w)[0]
        if len(j) == 0:
            continue
        ok = j[seen[j] >= 60]
        if len(ok) < 2:
            continue
        sd = np.sqrt(np.maximum(var[ok], 1e-12))
        cv = cov[np.ix_(ok, ok)]; dd = np.sqrt(np.maximum(np.diag(cv), 1e-12))
        C = cv / np.outer(dd, dd)
        off = C[~np.eye(len(ok), dtype=bool)]
        cbar = float(np.clip(off.mean(), -0.99, 0.99)) if len(off) else 0.0
        C = (1 - shrink) * C + shrink * (np.full_like(C, cbar) + (1 - cbar) * np.eye(len(ok)))
        S = np.outer(sd, sd) * C
        sp = math.sqrt(max(w[ok] @ S @ w[ok], 1e-18)) * math.sqrt(periods)
        L[i] = TV / sp if sp > 0 else 0.0
    W = Wu * L[:, None]
    g = np.abs(W).sum(1)
    return W * np.where(g > LEV, LEV / np.maximum(g, 1e-12), 1.0)[:, None]


# ── D1: the drawdown loop (round 9's L3/D1), path dependent ──────────────────
def drawdown_loop(D, Wbase, cap=0.30, floor=0.25):
    r, fund = D['r'], D['fund']
    n = len(r)
    scale = np.ones(n); eq, peak = 1.0, 1.0
    x = np.zeros(n)
    prev = np.zeros(Wbase.shape[1])
    for i in range(n):
        held = prev                                          # decided at close i-1 (costs left out: small)
        g = np.nansum(held * np.nan_to_num(r[i])) - np.nansum(held * fund[i])
        x[i] = g
        eq *= 1 + g; peak = max(peak, eq)
        ddv = 1 - eq / peak
        scale[i] = min(max(1 - ddv / cap, floor), 1.0)
        prev = Wbase[i] * scale[i]
    return scale


def prep(bdir, drop_delisted=False):
    t0 = time.time()
    T, syms, o, h, l, c, qv, fund = load(bdir, drop_delisted)
    r = om._c488_returns(c)
    D = dict(T=T, syms=syms, o=o, h=h, l=l, c=c, qv=qv, fund=fund, r=r, sd30=om._c488_trailing_std(r, 30),
             floor=np.array([max(6.0, BIG.get(s, 5.0)) for s in syms]), elig={}, beta={})
    for tn in (15, 20, 30):
        D['elig'][tn] = om._c488_universe(c, qv, tn)
        D['beta'][tn] = beta_mkt(c, r, D['elig'][tn])
    print(f"  data: {len(syms)} coins x {len(T)} days, {dt.datetime.utcfromtimestamp(T[0] / 1000).date()} -> "
          f"{dt.datetime.utcfromtimestamp(T[-1] / 1000).date()} [{time.time() - t0:.0f}s]")
    return D


def part_A(D, bdir):
    print("\nA. THE AUDIT")
    # parity: the parameterised book = the bot's own n2n3 book
    r_, Wb, el = om._c488_sleeves(D['T'], D['c'], D['qv'], D['fund'], TOPN, rule='n2n3')
    Wp = sleeves(D)
    par = max(float(np.nanmax(np.abs(Wb[k] - Wp[k]))) for k in Wb)
    print(f"  parity: the parameterised sleeves = the bot's _c488_sleeves(rule='n2n3'): max |diff| {par:.1e}")
    assert par < 1e-12
    xb, Wcb, _ = book(D, Wp)
    xb_, Tb = returns_of(xb, D)
    sb = sstats(xb_, Tb)
    print(f"  the base book (N2+N3, dial 20%, $500, Binance costs): {100 * sb['ann']:+.1f}%/yr, vol {100 * sb['vol']:.1f}%, "
          f"Sharpe {sb['sharpe']:.2f}, max DD {100 * sb['maxdd']:.1f}%, worst month {100 * sb['worst_month']:+.1f}%")
    OUT['base'] = sb
    # A1 survivorship
    D2 = prep(bdir, drop_delisted=True)
    x2, _, _ = book(D2, sleeves(D2)); x2_, T2 = returns_of(x2, D2); s2 = sstats(x2_, T2)
    nd = len(D['syms']) - len(D2['syms'])
    print(f"  A1 survivorship: the corpus holds {nd} coins delisted > 30 days before its end (LUNA among them). "
          f"Without them: Sharpe {s2['sharpe']:.2f} vs {sb['sharpe']:.2f} with them -> "
          f"{'PASS: including them is the conservative choice' if s2['sharpe'] >= sb['sharpe'] - 0.02 else 'no survivorship bias (they are in), but the book earned on them: shorting coins that later died'}")
    OUT['A1'] = dict(delisted=nd, sharpe_without=s2['sharpe'], sharpe_with=sb['sharpe'])
    # A2 look-ahead
    res = {}
    for lag in (0, 1, 2):
        if lag == 0:                                     # deliberate look-ahead: the close-i weights earn day i
            wl = Wcb
            dw = np.abs(np.diff(np.vstack([np.zeros(wl.shape[1]), wl]), axis=0)).sum(1)
            x = np.nansum(wl * np.nan_to_num(D['r']), axis=1) - np.nansum(wl * D['fund'], axis=1) - dw * COST
        else:
            x, _ = om._c488_pnl(Wcb, D['r'], D['fund'], lag, cost=COST)
        xx, TT = returns_of(x, D)
        res[lag] = sstats(xx, TT)['sharpe']
    ok2 = res[2] >= 0.5 * res[1] and res[0] > res[1] + 0.3
    print(f"  A2 look-ahead: Sharpe at lag 0 (cheating) {res[0]:.2f}, lag 1 (as traded) {res[1]:.2f}, lag 2 (a day late) "
          f"{res[2]:.2f} -> {'PASS' if ok2 else 'CHECK'}")
    OUT['A2'] = dict(lag=res, ok=bool(ok2))
    # A4 grid + PBO
    grid = list(itertools.product((7, 10, 14, 21, 28), (3, 7, 14), ((3, 7, 14, 28), (7, 14, 28, 56), (14, 28, 56, 112)),
                                  (15, 20, 30)))
    t0 = time.time()
    X = []
    for (l2, f3, hz, tn) in grid:
        x, _, _ = book(D, sleeves(D, l2=l2, f3=f3, hz=hz, topn=tn))
        X.append(x)
    X = np.array(X)
    start = max(np.nonzero(np.abs(X[i]) > 0)[0][0] for i in range(len(X))) + 1
    X = X[:, start:]
    srs = X.mean(1) / X.std(1) * math.sqrt(365)
    ci = grid.index((14, 7, (7, 14, 28, 56), 20))
    rank = int((srs > srs[ci]).sum()) + 1
    med = float(np.median(srs))
    print(f"  A4 grid: {len(grid)} neighbours [{time.time() - t0:.0f}s]: the chosen design's Sharpe {srs[ci]:.2f} ranks "
          f"{rank} of {len(grid)}; neighbours median {med:.2f}, 10th pct {np.percentile(srs, 10):.2f}, "
          f"90th {np.percentile(srs, 90):.2f}; {int((srs > 0).sum())}/{len(grid)} positive")
    for name, sel in (('C2 lookback', 0), ('C3 window', 1), ('trend horizons', 2), ('top N', 3)):
        vals = sorted({g[sel] for g in grid}, key=str)
        print(f"     by {name}: " + ', '.join(f"{v}: {np.median([srs[i] for i, g in enumerate(grid) if g[sel] == v]):.2f}"
                                             for v in vals))
    # PBO by CSCV, 16 blocks
    S = 16
    blocks = np.array_split(np.arange(X.shape[1]), S)
    m1 = np.array([[X[i, b].sum() for b in blocks] for i in range(len(X))])
    m2 = np.array([[(X[i, b] ** 2).sum() for b in blocks] for i in range(len(X))])
    nb = np.array([len(b) for b in blocks])
    lam = []
    for comb in itertools.combinations(range(S), S // 2):
        ins = np.zeros(S, bool); ins[list(comb)] = True
        def sr(mask):
            s1, s2, nn = m1[:, mask].sum(1), m2[:, mask].sum(1), nb[mask].sum()
            mu = s1 / nn
            return mu / np.sqrt(np.maximum(s2 / nn - mu * mu, 1e-18))
        si, so = sr(ins), sr(~ins)
        best = int(np.argmax(si))
        w = (so < so[best]).sum() + 0.5 * ((so == so[best]).sum() - 1) + 1
        om_ = w / (len(so) + 1)
        lam.append(math.log(om_ / (1 - om_)))
    lam = np.array(lam)
    pbo = float((lam <= 0).mean())
    print(f"  A4 PBO (CSCV, {S} blocks, {len(lam)} splits): {pbo:.3f} -> "
          f"{'PASS' if pbo < 0.25 and med >= 0.7 * srs[ci] else 'FAIL'} (bars: PBO < 0.25, median >= 70% of the chosen)")
    OUT['A4'] = dict(chosen=float(srs[ci]), rank=rank, n=len(grid), median=med, p10=float(np.percentile(srs, 10)),
                     p90=float(np.percentile(srs, 90)), pbo=pbo)
    # A3 deflated Sharpe and minimum track record
    x = xb_; T_ = len(x)
    sr_d = x.mean() / x.std()
    g3 = float(((x - x.mean()) ** 3).mean() / x.std() ** 3)
    g4 = float(((x - x.mean()) ** 4).mean() / x.std() ** 4)
    V = float((srs / math.sqrt(365)).var())
    Phi = lambda z: 0.5 * math.erfc(-z / math.sqrt(2))
    from statistics import NormalDist
    inv = NormalDist().inv_cdf
    eg = 0.5772156649
    out3 = {}
    for N in (60, 120):
        sr0 = math.sqrt(V) * ((1 - eg) * inv(1 - 1 / N) + eg * inv(1 - 1 / (N * math.e)))
        dsr = Phi((sr_d - sr0) * math.sqrt(T_ - 1) / math.sqrt(1 - g3 * sr_d + (g4 - 1) / 4 * sr_d ** 2))
        out3[N] = dict(sr0_ann=sr0 * math.sqrt(365), dsr=dsr)
        print(f"  A3 deflated Sharpe, N = {N} trials: the best of {N} worthless strategies would show Sharpe "
              f"{sr0 * math.sqrt(365):.2f}; the book's {sr_d * math.sqrt(365):.2f} -> DSR {dsr:.3f} "
              f"{'PASS' if dsr >= 0.95 else 'FAIL'}")
    z95 = inv(0.95)
    for lab, s_ in (('backtest', sr_d), ('with the 1/3 haircut', sr_d * 2 / 3)):
        mtrl = 1 + (1 - g3 * s_ + (g4 - 1) / 4 * s_ ** 2) * (z95 / s_) ** 2
        print(f"  A3 minimum track record to show Sharpe > 0 at 95% ({lab}, Sharpe {s_ * math.sqrt(365):.2f}): "
              f"{mtrl:.0f} days = {mtrl / 30.4:.1f} months")
        out3['mintrl_' + lab.split()[0]] = mtrl
    OUT['A3'] = dict(skew=g3, kurt=g4, trials_sr_var_ann=V * 365, **{str(k): v for k, v in out3.items()})
    return D, xb, Wp, Wcb


def part_A5_B(D, xb, Wp, Wcb):
    xb_, Tb = returns_of(xb, D)
    print("\nA5. RISK-MATCHED RE-TEST OF THE IDEAS JUDGED ON RAW RETURN (bar: p < 0.05, 3/4 quarters, holdout > 0, DD)")
    res = []
    xk, _, _ = book(D, Wp, sizing='k4'); res.append(compare('K4 (EWMA vol, 10-day half-life)', *returns_of(xk, D), xb_, Tb))
    sdg = om._c510_range_sd(D['o'], D['h'], D['l'], D['c'], kind='gk')
    sdgk = np.where(np.isnan(sdg), D['sd30'], sdg)
    xg, _, _ = book(D, sleeves(D, sd=sdgk)); res.append(compare('GK (range-based coin vol)', *returns_of(xg, D), xb_, Tb))
    sc = drawdown_loop(D, Wcb)
    xd, _, _ = book(D, Wp, scale=sc); res.append(compare('D1 (drawdown loop, 30%)', *returns_of(xd, D), xb_, Tb))
    xkg, _, _ = book(D, sleeves(D, sd=sdgk), sizing='k4')
    res.append(compare('K4 + GK', *returns_of(xkg, D), xb_, Tb))
    print("\nB. NEW CANDIDATES (same bar)")
    dtau, lookback = market_clock(D)
    print(f"  B1 the market clock: a calendar day counts {np.percentile(dtau[400:], 10):.2f}-{np.percentile(dtau[400:], 90):.2f} "
          f"proper days (10th-90th pct), mean {dtau[400:].mean():.2f}")
    cache = {}
    clock = lambda H: cache.setdefault(H, lookback(H))
    x1, _, _ = book(D, sleeves(D, clock=clock)); res.append(compare('B1 proper-time momentum (C1+C2)', *returns_of(x1, D), xb_, Tb))
    t0 = time.time()
    x2, _, _ = book(D, Wp, sizing='exante'); res.append(compare('B2 ex-ante risk (EWMA + shrunk corr)', *returns_of(x2, D), xb_, Tb))
    print(f"     (B2 {time.time() - t0:.0f}s)")
    OUT['A5_B'] = [{k: (v if not isinstance(v, np.floating) else float(v)) for k, v in r.items()} for r in res]
    return res


def part_C():
    print("\nC. WHAT THE MATHEMATICS ALLOWS")
    sb = OUT['base']
    for lab, sr in (('backtest', sb['sharpe']), ('with the 1/3 haircut', sb['sharpe'] * 2 / 3)):
        kelly_vol = sr                                      # full Kelly on a Sharpe-SR stream runs at vol = SR
        print(f"  Kelly ({lab}, Sharpe {sr:.2f}): full Kelly would run at {100 * kelly_vol:.0f}% volatility; "
              f"dial 20% runs at {100 * sb['vol']:.0f}% realised = {sb['vol'] / kelly_vol:.2f} of Kelly; "
              f"growth at that fraction {100 * (sr * sb['vol'] - sb['vol'] ** 2 / 2):.1f}%/yr vs "
              f"{100 * sr * sr / 2:.1f}%/yr at full Kelly")
    OUT['C'] = dict(kelly_frac_backtest=sb['vol'] / sb['sharpe'], kelly_frac_haircut=sb['vol'] / (sb['sharpe'] * 2 / 3))


def main():
    bdir = sys.argv[1]
    part = sys.argv[2] if len(sys.argv) > 2 else 'all'
    print("ROUND 14 (C521): THE AUDIT, THE ADAPTIVE CANDIDATES, THE MATHEMATICS")
    D = prep(bdir)
    D, xb, Wp, Wcb = part_A(D, bdir)
    if part in ('all', 'B'):
        part_A5_B(D, xb, Wp, Wcb)
    part_C()
    json.dump(OUT, open(os.path.join(HERE, 'c521_results.json'), 'w'), indent=1, default=lambda o: float(o)
              if isinstance(o, (np.floating, np.integer)) else str(o))


if __name__ == '__main__':
    main()
