#!/usr/bin/env python3
"""Round 15 (C524) Part A: the intraday shadow's weighting, M1 (equal) vs M1v (inverse volatility)
vs M1x (volatility filter), on the C489 research engine unchanged.

    python3 research/c524_shadow_weights.py H1_DIR BNC_DIR

Rules and bar fixed in research/c524_preregistration.md (committed first). Every variant uses M1's
out-of-sample probabilities (walk-forward logistic, retrain 30 days on 180) and the same cohorts,
4-hour overlap, 0.08% per unit of turnover and real funding events.
  M1   equal weight, 0.5/n per side
  M1v  w_i = 0.5 x (1/sigma_i) / sum_side(1/sigma_j); sigma_i = std of the coin's hourly returns over the
       last 168 hours (>= 120 valid; otherwise the side's median sigma)
  M1x  equal weight; a coin with sigma_i > 3 x the eligible coins' median sigma that hour is not eligible
Universe: the research rule (C488: top 40 by 30-day median quote volume, 90+ days), crypto only (the
C493 exclusion of stock/metal/oil perps, which the live shadow applies).
Bar (as a forward shadow ledger, not for trading): hourly P&L sd <= 0.8 x M1's, worst day better, Sharpe
difference vs M1 >= 0.
"""
import os, sys, json, math, time, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c489_research as R
import omega_c488_research as R488
from omega_c493_research import TRADFI
from omega_c521_research import lw_sharpe_diff, nw_t


def sigma_168(r1, need=120):
    x = np.nan_to_num(r1)
    v = (~np.isnan(r1)).astype(float)
    s1 = R.roll_sum(x, 168); s2 = R.roll_sum(x * x, 168); n = R.roll_sum(v, 168)
    with np.errstate(invalid='ignore', divide='ignore'):
        m = s1 / n
        sd = np.sqrt(np.maximum(s2 / n - m * m, 0.0))
    return np.where(n >= need, sd, np.nan)


def book_iv(sig, U, sd, frac=0.2):
    q = np.zeros_like(sig)
    for i in range(len(sig)):
        m = U[i] & ~np.isnan(sig[i])
        if m.sum() < 10:
            continue
        v = sig[i][m]
        lo, hi = np.quantile(v, [frac, 1 - frac])
        if hi == lo:
            continue
        s_ = sd[i][m]
        o = np.zeros(m.sum())
        for side, sel in ((+1, v >= hi), (-1, v <= lo)):
            ss = s_[sel]
            med = np.nanmedian(ss) if np.isfinite(ss).any() else 1.0
            ss = np.where(np.isfinite(ss) & (ss > 0), ss, med)
            inv = 1.0 / ss
            o[sel] = side * 0.5 * inv / inv.sum()
        q[i][m] = o
    return q


def run(name, q, r1, F, T, oos, out, ref=None):
    w = R.overlap(q)
    hp, d = R.hourly_pnl(w, r1, F)
    h = hp[oos]
    du, dr = R.to_daily(T[oos], h)
    st = R488.stats(dr, du)
    k = float(((h - h.mean()) ** 4).mean() / h.var() ** 2 - 3) if h.var() > 0 else float('nan')
    gross_d = R.to_daily(T[oos], d['gross'][oos])[1]
    gsh = float(gross_d.mean() / gross_d.std() * math.sqrt(365)) if gross_d.std() > 0 else float('nan')
    rec = dict(net_ann=float(dr.mean() * 365), sharpe=float(dr.mean() / dr.std() * math.sqrt(365)), t=float(nw_t(dr)),
               hourly_sd=float(h.std()), worst_hour=float(h.min()), worst_day=float(dr.min()),
               p999_abs_hour=float(np.percentile(np.abs(h), 99.9)), excess_kurtosis=k, gross_sharpe=gsh,
               gross_ann=float(d['gross'][oos].mean() * 24 * 365), cost_ann=float(d['cost'][oos].mean() * 24 * 365),
               funding_ann=float(d['funding'][oos].mean() * 24 * 365))
    years = {}
    for t_, v in zip(du, dr):
        y = dt.datetime.utcfromtimestamp(t_ / 1000).year
        years[y] = years.get(y, 0.0) + v
    rec['by_year'] = years
    if ref is not None:
        dd, z, p = lw_sharpe_diff(dr, ref)
        rec['sharpe_diff'] = float(dd); rec['sharpe_diff_p'] = float(p)
    out[name] = rec
    print(f"  {name:4} net {100 * rec['net_ann']:+8.1f}%/yr  Sharpe {rec['sharpe']:+.2f}  t {rec['t']:+.2f}  | hourly sd "
          f"{100 * rec['hourly_sd']:.3f}%  worst hour {100 * rec['worst_hour']:+.2f}%  worst day {100 * rec['worst_day']:+.2f}%  "
          f"|hour| 99.9% {100 * rec['p999_abs_hour']:.2f}%  kurtosis {k:6.1f}  | gross {100 * rec['gross_ann']:+.0f}%/yr "
          f"(Sharpe {gsh:+.2f})  cost {100 * rec['cost_ann']:.0f}%/yr"
          + (f"  | Sharpe diff vs M1 {rec['sharpe_diff']:+.2f} (p {rec['sharpe_diff_p']:.3f})" if ref is not None else ''), flush=True)
    print("       by year: " + "  ".join(f"{y} {100 * v:+.1f}%" for y, v in sorted(years.items())), flush=True)
    return dr


def main(h1dir, bdir):
    t0 = time.time()
    T, syms, O, Hh, L, C, QV, TB, U, F = R.load(h1dir, bdir)
    tf = np.array([s in TRADFI for s in syms])
    U[:, tf] = False
    print(f"{len(syms)} coins ({int(tf.sum())} stock/metal/oil perps left out), {len(T)} hours, "
          f"{dt.datetime.utcfromtimestamp(T[0] / 1000):%Y-%m-%d} .. {dt.datetime.utcfromtimestamp(T[-1] / 1000):%Y-%m-%d}; "
          f"universe max {int(U.sum(1).max())}  [{time.time() - t0:.0f}s]", flush=True)
    r1, Fm = R.features(T, syms, O, Hh, L, C, QV, TB, U, F)
    Z = R.xs_standardise(Fm, U)
    P, gate, fits = R.model_signal(T, C, U, Z)
    print(f"model: {fits} walk-forward fits  [{time.time() - t0:.0f}s]", flush=True)
    sd = sigma_168(r1)
    oos = T >= R.OOS_FROM
    out = {}
    print("\nTHE SHADOW'S WEIGHTING, out of sample 2021-07 .. 2026-08 (0.08%/turnover, real funding)")
    ref = run('M1', R.quintile_book(P, U), r1, F, T, oos, out)
    run('M1v', book_iv(P, U, sd), r1, F, T, oos, out, ref)
    with np.errstate(invalid='ignore'):
        med = np.nanmedian(np.where(U, sd, np.nan), axis=1, keepdims=True)
        Ux = U & ~(sd > 3 * med)
    run('M1x', R.quintile_book(P, Ux), r1, F, T, oos, out, ref)
    print(f"  M1x leaves out {100 * (U & ~Ux).sum() / max(U.sum(), 1):.1f}% of eligible coin-hours")
    verdict = {}
    for v in ('M1v', 'M1x'):
        a, b = out[v], out['M1']
        c1 = a['hourly_sd'] <= 0.8 * b['hourly_sd']; c2 = a['worst_day'] > b['worst_day']; c3 = a['sharpe_diff'] >= 0
        verdict[v] = dict(sd_ok=bool(c1), worst_day_ok=bool(c2), sharpe_ok=bool(c3), passed=bool(c1 and c2 and c3))
        print(f"  BAR {v}: hourly sd <= 0.8 x M1 {'yes' if c1 else 'NO'} ({a['hourly_sd'] / b['hourly_sd']:.2f}x), "
              f"worst day better {'yes' if c2 else 'NO'}, Sharpe diff >= 0 {'yes' if c3 else 'NO'} -> "
              f"{'PASSED' if verdict[v]['passed'] else 'NOT PASSED'}")
    passing = [v for v in verdict if verdict[v]['passed']]
    pick = min(passing, key=lambda v: out[v]['hourly_sd']) if passing else None
    print(f"  added to the shadow: {pick or 'none'}.  A trading candidate needs net t >= 2: "
          + ", ".join(f"{v} t {out[v]['t']:+.2f}" for v in out))
    out['verdict'] = verdict; out['pick'] = pick
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c524_shadow_weights.json'), 'w'),
              indent=1, default=float)
    print(f"[{time.time() - t0:.0f}s]")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
