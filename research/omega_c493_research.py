#!/usr/bin/env python3
"""C493 round 5 (breadth): the seven pre-registered tests and COMBO-E.

    python3 research/omega_c493_research.py BNC_DIR METRICS_DIR [--out results.json]

BNC_DIR     : the C488 archive layout (k/<SYM>.json, f/<SYM>.json).
METRICS_DIR : <SYM>.json {"<day_ms>": [count_long_short_ratio, sum_toptrader_long_short_ratio]}
              from the Binance futures `metrics` archive, the last row of each UTC day
              (research/c493_fetch_metrics.py). Missing -> N4a/N4b report no data.

Every rule, parameter and the admission bar are fixed in
research/c493_preregistration.md (committed before any signal was computed).
The C488 functions are imported, not copied, so C1-C3 are exactly what trades.
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R

warnings.simplefilter('ignore')
DAY = R.DAY
TRADFI = set((s + 'USDT') for s in "AAPL ADBE AMD AMZN ARM AVGO BABA BZ CL COIN COPPER CRCL CRM CRWV DIS DRAM EWY GME GOOGL HOOD IBM INTC IREN IWM JPM KORU KO MARA META MSFT MSTR MU MUU NATGAS NFLX NVDA ORCL PLTR QCOM QQQ RIVN SAMSUNG SKDD SKHYNIX SKHY SMCI SNDK SNXX SOXL SOXS SPCX SPY TQQQ TSLA TSM TXN UBER V WMT XAUT XPD XPT".split())
T_BAR = 2.45                         # one-sided 5% / 7 tests
RECENT = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)


# ─── the sleeves ─────────────────────────────────────────────────────────────
def rolling_median(x, lo, hi):
    """median of x[i-lo : i-hi] for each i (rows), NaN-aware; lo > hi >= 0"""
    out = np.full_like(x, np.nan)
    for i in range(lo, len(x)):
        out[i] = np.nanmedian(x[i - lo:i - hi], axis=0)
    return out


def n1_newlist(close, qv, enter=14, exit_=120, top=100):
    r = R.returns(close)
    age = np.cumsum(~np.isnan(close), axis=0)
    med7 = rolling_median(qv, 7, 0)
    n, k = close.shape
    tg = np.zeros((n, k))
    for i in range(8, n):
        ok = ~np.isnan(close[i]) & ~np.isnan(med7[i])
        if ok.sum() == 0:
            continue
        rank = np.empty(k); rank[:] = np.inf
        order = np.argsort(-np.where(ok, med7[i], -1))
        rank[order[:ok.sum()]] = np.arange(1, ok.sum() + 1)
        act = ok & (age[i] >= enter) & (age[i] <= exit_) & (rank <= top)
        if not act.any():
            continue
        lo = max(0, i - 13)
        sd = np.nanstd(r[lo:i + 1], axis=0)
        cnt = np.sum(~np.isnan(r[lo:i + 1]), axis=0)
        sc = np.clip(0.02 / np.where((sd > 0) & (cnt >= 10), sd, np.nan), 0, 1.0)
        act &= ~np.isnan(sc)
        m = max(int(act.sum()), 10)
        tg[i] = np.where(act, -np.nan_to_num(sc) / m, 0.0)
    return R.banded(tg)


def weekly_xs(sig, elig, sc, T, sign):
    N = R.TOPN
    return R.weekly(sign * R.xs_rank(sig, elig) * sc / (2 * N * 0.2), T)


def n5_efficiency(close, elig, sc):
    lc = np.log(close)
    d = np.abs(np.diff(lc, axis=0, prepend=np.nan))
    net = np.full_like(close, np.nan); net[28:] = np.abs(lc[28:] - lc[:-28])
    path = np.full_like(close, np.nan)
    for i in range(28, len(close)):
        path[i] = np.sum(d[i - 27:i + 1], axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        er = np.where(path > 0, net / path, np.nan)
    m = np.zeros_like(er)
    for i in range(len(er)):
        v = er[i][elig[i] & ~np.isnan(er[i])]
        if len(v) and v.mean() > 0:
            m[i] = np.nan_to_num(er[i] / v.mean())
    trend = sum(np.sign(np.nan_to_num(R.lagret(close, dd))) for dd in (7, 14, 28, 56)) / 4.0
    return R.banded(np.where(elig, trend * sc * m / R.TOPN, 0.0)), er


def load_metrics(mdir, T, syms):
    idx = {t: i for i, t in enumerate(T)}
    crowd = np.full((len(T), len(syms)), np.nan); top = np.full_like(crowd, np.nan)
    if not mdir or not os.path.isdir(mdir):
        return crowd, top
    for j, s in enumerate(syms):
        p = os.path.join(mdir, s + '.json')
        if not os.path.exists(p):
            continue
        for t, v in json.load(open(p)).items():
            i = idx.get(int(t))
            if i is not None:
                if v[0] and v[0] > 0: crowd[i, j] = math.log(v[0])
                if v[1] and v[1] > 0: top[i, j] = math.log(v[1])
    return crowd, top


def zscore30(x, need=20):
    z = np.full_like(x, np.nan)
    for i in range(29, len(x)):
        w = x[i - 29:i + 1]
        cnt = np.sum(~np.isnan(w), axis=0)
        mu = np.nanmean(w, axis=0); sd = np.nanstd(w, axis=0)
        ok = (cnt >= need) & (sd > 0) & ~np.isnan(x[i])
        z[i] = np.where(ok, (x[i] - mu) / np.where(sd > 0, sd, 1), np.nan)
    return z


def combine_fm(parts, r, fund, lag, target_vol=0.20, lev_cap=3.0, win=60, lb=21, T=None, periods=365):
    """R.combine with each sleeve switched on only while its own trailing 21-day
    unit P&L is positive (fixed on Mondays). The switch in force during day i is
    the one decided at the close of day i-1."""
    unit = {k: R.pnl(w, r, fund, lag)[0] for k, w in parts.items()}
    n = len(r)
    sw, mm = {}, {}
    for k, u in unit.items():
        s = np.full(n, np.nan)
        for i in range(win, n):
            x = u[i - win:i]
            s[i] = x.std() if x.std() > 0 else np.nan
        sw[k] = np.nan_to_num(1.0 / s) / len(unit)
        m = np.zeros(n); cur = 0.0
        for i in range(n):
            if i == 0 or dt.datetime.utcfromtimestamp(T[i] / 1000).weekday() == 0:
                cur = 1.0 if i >= lb and u[i - lb + 1:i + 1].sum() > 0 else 0.0
            m[i] = cur
        mm[k] = m
    comb_unit = sum(sw[k] * np.concatenate([[0.0], mm[k][:-1]]) * unit[k] for k in unit)
    L = np.zeros(n)
    for i in range(2 * win, n):
        x = comb_unit[i - win:i]
        v = x.std() * math.sqrt(periods)
        L[i] = target_vol / v if v > 0 else 0.0
    W = sum((sw[k] * mm[k] * L)[:, None] * parts[k] for k in parts)
    gross = np.abs(W).sum(1)
    capf = np.where(gross > lev_cap, lev_cap / np.maximum(gross, 1e-12), 1.0)
    return W * capf[:, None], mm


# ─── judging ─────────────────────────────────────────────────────────────────
def verdict(ret, T):
    s = R.stats(ret, T)
    if not s:
        return None
    rr = np.asarray(ret)
    live = np.nonzero(np.abs(rr) > 0)[0]
    rec = rr[(T >= RECENT)]
    rec = rec[np.nonzero(np.abs(rec) > 0)[0][0]:] if np.any(np.abs(rec) > 0) else rec
    s['recent_ann'] = float(rec.mean() * 365) if len(rec) else float('nan')
    s['recent_t'] = float(R.nw_t(rec)) if len(rec) > 60 else float('nan')
    s['admit'] = bool(s['t'] >= T_BAR and s['npos'] >= 3 and s['ann'] > 0 and s['recent_ann'] > 0)
    return s


def show(name, s):
    if not s:
        print(f"  {name:46} (too little data)"); return
    print(f"  {name:46} {s['start']}..{s['end']} net {100*s['ann']:+6.1f}%/yr vol {100*s['vol']:5.1f}% "
          f"Sh {s['sharpe']:+.2f} t {s['t']:+.2f} q+ {s['npos']}/4 DD {100*s['maxdd']:4.1f}% "
          f"mo {100*s['month_mean']:+.2f}% | 2024+ {100*s['recent_ann']:+6.1f}%/yr "
          f"{'ADMIT' if s.get('admit') else '-'}", flush=True)


def by_year(ret, T):
    out = {}
    for t, x in zip(T, ret):
        y = dt.datetime.utcfromtimestamp(t / 1000).year
        out[y] = out.get(y, 0.0) + x
    return {int(y): round(100 * float(v), 1) for y, v in sorted(out.items()) if v != 0}


def main(argv):
    bdir, mdir = argv[1], argv[2]
    outp = argv[argv.index('--out') + 1] if '--out' in argv else None
    R.EXCLUDE = set(R.EXCLUDE) | TRADFI
    print("loading ...", flush=True)
    T, syms, close, qv, fund = R.load_crypto(bdir)
    print(f"  {len(syms)} symbols (stablecoins, indices and 2026 stock/commodity perps excluded), "
          f"{dt.datetime.utcfromtimestamp(T[0]/1000):%Y-%m-%d}..{dt.datetime.utcfromtimestamp(T[-1]/1000):%Y-%m-%d}", flush=True)
    r, W, elig = R.crypto_sleeves(T, close, qv, fund)
    sc = np.nan_to_num(R.vol_scale(R.trailing_std(r, 30)))
    OUT = {}

    print("\nTHE C488 SLEEVES ON THIS DATA (reference)")
    for k in ('C1', 'C2', 'C3'):
        s = verdict(R.pnl(W[k], r, fund, 1)[0], T); OUT[k] = s; show(k, s)
    Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1)
    retC = R.pnl(Wc, r, fund, 1)[0]
    OUT['COMBO-C'] = verdict(retC, T); show('COMBO-C', OUT['COMBO-C'])

    print("\nROUND 5 -- the seven pre-registered tests (bar: t >= 2.45, 3/4 quarters, positive, positive 2024+)")
    S = {}
    S['N1'] = n1_newlist(close, qv)
    S['N2'] = weekly_xs(R.trailing_std(r, 60), elig, sc, T, -1)
    att = rolling_median(qv, 7, 0) / rolling_median(qv, 60, 0)
    S['N3'] = weekly_xs(att, elig, sc, T, -1)
    crowd, top = load_metrics(mdir, T, syms)
    zc, zt = zscore30(crowd), zscore30(top)
    S['N4a'] = weekly_xs(zc, elig, sc, T, -1)
    S['N4b'] = weekly_xs(zt, elig, sc, T, +1)
    cover = np.sum(elig & ~np.isnan(zc), axis=1)
    days_ok = int((cover >= 10).sum())
    labels = {'N1': 'N1 new-listing short', 'N2': 'N2 low volatility', 'N3': 'N3 attention (abnormal volume)',
              'N4a': 'N4a crowd contrarian', 'N4b': 'N4b follow top traders'}
    for k in ('N1', 'N2', 'N3', 'N4a', 'N4b'):
        ret, d = R.pnl(S[k], r, fund, 1)
        if k.startswith('N4') and days_ok < 730:
            OUT[k] = dict(insufficient=True, days=days_ok)
            print(f"  {labels[k]:46} INSUFFICIENT DATA ({days_ok} days with >= 10 coins)"); continue
        s = verdict(ret, T)
        if s:
            s['funding_yr'] = float(d['funding'].mean() * 365); s['cost_yr'] = float(d['cost'].mean() * 365)
            s['gross_yr'] = float(d['gross'].mean() * 365); s['turnover_yr'] = float(d['turnover'].mean() * 365)
        OUT[k] = s; show(labels[k], s)
        if s:
            print(f"  {'':46}   gross {100*s['gross_yr']:+.1f}%/yr funding {100*s['funding_yr']:+.1f}%/yr "
                  f"cost {100*s['cost_yr']:.1f}%/yr turnover {s['turnover_yr']:.0f}x  by year {by_year(ret, T)}")
    S['N5'], er = n5_efficiency(close, elig, sc)
    r5 = R.pnl(S['N5'], r, fund, 1)[0]; r1 = R.pnl(W['C1'], r, fund, 1)[0]
    OUT['N5'] = verdict(r5, T); show('N5 efficiency-weighted trend', OUT['N5'])
    OUT['N5-C1'] = verdict(r5 - r1, T); show('N5 minus C1 (the test)', OUT['N5-C1'])
    Wfm, mm = combine_fm({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1, T=T)
    rfm = R.pnl(Wfm, r, fund, 1)[0]
    OUT['N6'] = verdict(rfm, T); show('N6 factor-momentum COMBO', OUT['N6'])
    OUT['N6-C'] = verdict(rfm - retC, T); show('N6 minus COMBO-C (the test)', OUT['N6-C'])
    print(f"  {'':46}   sleeves switched on: " + ", ".join(f"{k} {100*mm[k][400:].mean():.0f}% of days" for k in mm))

    adm = [k for k in ('N1', 'N2', 'N3', 'N4a', 'N4b') if (OUT.get(k) or {}).get('admit')]
    use5 = bool((OUT.get('N5-C1') or {}).get('admit'))
    use6 = bool((OUT.get('N6-C') or {}).get('admit'))
    print(f"\nADMITTED: {adm or 'none of N1-N4b'}; N5 replaces C1: {use5}; N6 factor momentum: {use6}")

    print("\nCORRELATIONS of daily sleeve P&L (days where both trade)")
    ser = {k: R.pnl(W[k], r, fund, 1)[0] for k in ('C1', 'C2', 'C3')}
    for k in ('N1', 'N2', 'N3', 'N4a', 'N4b', 'N5'):
        if isinstance(OUT.get(k), dict) and not OUT[k].get('insufficient'):
            ser[k] = R.pnl(S[k], r, fund, 1)[0]
    ks = list(ser); corr = {}
    for a in ks:
        row = []
        for b in ks:
            m = (np.abs(ser[a]) > 0) & (np.abs(ser[b]) > 0)
            c = float(np.corrcoef(ser[a][m], ser[b][m])[0, 1]) if m.sum() > 60 else float('nan')
            corr[f"{a}|{b}"] = c; row.append(f"{c:+.2f}")
        print(f"  {a:4} " + ' '.join(row))
    print("       " + '  '.join(f"{k:>4}" for k in ks))

    parts = {('N5' if use5 else 'C1'): (S['N5'] if use5 else W['C1']), 'C2': W['C2'], 'C3': W['C3']}
    for k in adm:
        parts[k] = S[k]
    def comboE(tv=0.20, pts=None):
        pts = pts or parts
        return combine_fm(pts, r, fund, 1, target_vol=tv, T=T)[0] if use6 else R.combine(pts, r, fund, 1, target_vol=tv)
    WE = comboE()
    retE = R.pnl(WE, r, fund, 1)[0]
    OUT['COMBO-E'] = verdict(retE, T); OUT['COMBO-E']['members'] = list(parts)
    print(f"\nCOMBO-E = {' + '.join(parts)}{' (factor momentum)' if use6 else ''}  vs  COMBO-C")
    show('COMBO-C', OUT['COMBO-C']); show('COMBO-E', OUT['COMBO-E'])
    print(f"  by year  COMBO-C {by_year(retC, T)}\n           COMBO-E {by_year(retE, T)}")
    for lab, lo in (('last 24 months', T[-1] - 730 * DAY), ('last 12 months', T[-1] - 365 * DAY)):
        for nm, x in (('C', retC), ('E', retE)):
            y = x[T >= lo]; print(f"  {lab} COMBO-{nm}: {100*y.mean()*365:+.1f}%/yr Sharpe "
                                  f"{y.mean()/y.std()*math.sqrt(365) if y.std() > 0 else float('nan'):+.2f} "
                                  f"month {100*y.mean()*30.4:+.2f}%")
    better = (OUT['COMBO-E']['sharpe'] > OUT['COMBO-C']['sharpe']) and \
             (retE[T >= RECENT].mean() / max(retE[T >= RECENT].std(), 1e-12) > retC[T >= RECENT].mean() / max(retC[T >= RECENT].std(), 1e-12))
    OUT['E_beats_C'] = bool(better and parts.keys() != {'C1', 'C2', 'C3'})

    print("\nTHE DIAL: what each monthly target would have taken on COMBO-E (same path, 3x gross cap)")
    for tv in (0.133, 0.20, 0.267, 0.33, 0.40):
        x = R.pnl(comboE(tv), r, fund, 1)[0]; s = R.stats(x, T)
        rec = x[T >= RECENT]
        print(f"  vol target {100*tv:4.1f}% (dial {100*tv*0.75:4.1f}%): month {100*s['month_mean']:+.2f}% "
              f"(2024+: {100*rec.mean()*30.4:+.2f}%), max DD {100*s['maxdd']:.0f}%, worst month {100*s['worst_month']:+.1f}%")

    print("\nCAPACITY (Rule 51): positions under $6 dropped")
    R.TOPN = 20
    r20, W20, elig20 = R.crypto_sleeves(T, close, qv, fund)
    sc20 = np.nan_to_num(R.vol_scale(R.trailing_std(r20, 30)))
    P20 = {('N5' if use5 else 'C1'): (n5_efficiency(close, elig20, sc20)[0] if use5 else W20['C1']),
           'C2': W20['C2'], 'C3': W20['C3']}
    for k in adm:
        P20[k] = {'N1': S['N1'], 'N2': weekly_xs(R.trailing_std(r, 60), elig20, sc20, T, -1),
                  'N3': weekly_xs(att, elig20, sc20, T, -1), 'N4a': weekly_xs(zc, elig20, sc20, T, -1),
                  'N4b': weekly_xs(zt, elig20, sc20, T, +1)}[k]
    for lab, pts in (('C (top 20)', {k: W20[k] for k in ('C1', 'C2', 'C3')}), ('E (top 20)', P20)):
        Wx = comboE(0.20, pts) if lab.startswith('E') else R.combine(pts, r, fund, 1)
        for eq in (250, 1000):
            Wm = np.where(np.abs(Wx) * eq >= 6.0, Wx, 0.0)
            s = verdict(R.pnl(Wm, r, fund, 1)[0], T); OUT[f'cap {lab} ${eq}'] = s
            show(f'COMBO-{lab} ${eq}', s)
    R.TOPN = 40

    print("\nDIAGNOSTICS (never used for admission)")
    for a in (7, 14, 30):
        for b in (60, 120, 180):
            s = R.stats(R.pnl(n1_newlist(close, qv, a, b), r, fund, 1)[0], T)
            print(f"  N1 enter day {a:3} exit day {b:3}: net {100*s['ann']:+6.1f}%/yr t {s['t']:+.2f} q+ {s['npos']}/4")
    for w in (30, 90):
        s = R.stats(R.pnl(weekly_xs(R.trailing_std(r, w), elig, sc, T, -1), r, fund, 1)[0], T)
        print(f"  N2 with {w}-day volatility: net {100*s['ann']:+6.1f}%/yr t {s['t']:+.2f} q+ {s['npos']}/4")
    if outp:
        json.dump(OUT, open(outp, 'w'), indent=1, default=float)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
