#!/usr/bin/env python3
"""C491 research engine: round 4 (research/c491_preregistration.md, committed first).

    python3 research/omega_c491_research.py H1_DIR BNC_DIR M1_DIR [--out results.json]

The R3a limit-order (LP) rule, unchanged, on the point-in-time top 20,
2024-09 -> 2026-08:
  R4-M   (PRIMARY) fills and exits on the 1-minute path, stop first in a minute that touches both
  R4-Mo  the same, target first
  R4-H   the R3a hourly-bar simulator (stop first), same coins and window
  R4-Ho  the hourly optimistic ordering (no fill-hour stop, target first)
"""
import os, sys, json, math, time, datetime as dt, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R488
import omega_c489_research as M
import omega_c490_research as X

warnings.simplefilter('ignore')
H, DAY, MIN = 3600000, 86400000, 60000
MAKER, TAKER = X.MAKER, X.TAKER
W0 = int(dt.datetime(2024, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
W1 = int(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
K, HOLD, SIZE, CAP = 2.0, 12, 0.10, 10


def coin_trades(j, T, C, F, sig, allow, mm, optimistic):
    """pass 1: every candidate hour of coin j simulated on its own minute path,
    as if the coin were free. -> {fill hour: (exit hour, [(hour, pnl), ...])}"""
    t, o, hi, lo, cl = mm['t'], mm['o'], mm['h'], mm['l'], mm['c']
    out, n = {}, len(T)
    cover = miss = 0
    for h in range(1, n):
        if not (W0 <= T[h] < W1) or not allow[h - 1, j] or np.isnan(sig[h - 1, j]) or np.isnan(C[h, j]) or np.isnan(C[h - 1, j]):
            continue
        a, b = np.searchsorted(t, [T[h], T[h] + H])
        if b <= a:
            miss += 1
            continue
        cover += 1
        c0, s0 = C[h - 1, j], sig[h - 1, j]
        Lp, Sp = c0 * (1 - K * s0), c0 * (1 + K * s0)
        il = np.nonzero(lo[a:b] < Lp)[0]; ish = np.nonzero(hi[a:b] > Sp)[0]
        if not len(il) and not len(ish):
            continue
        if len(il) and (not len(ish) or il[0] <= ish[0]):
            sd, lim, mf = 1, Lp, a + il[0]
        else:
            sd, lim, mf = -1, Sp, a + ish[0]
        stop = lim * (1 - K * s0) if sd > 0 else lim * (1 + K * s0)
        tgt = c0
        end = np.searchsorted(t, T[h] + (HOLD + 1) * H)          # through the close of hour h + 12
        ex = None
        # the fill minute: only the stop (the path reached the limit first)
        if (sd > 0 and lo[mf] < stop) or (sd < 0 and hi[mf] > stop):
            gap = (sd > 0 and o[mf] < stop) or (sd < 0 and o[mf] > stop)
            ex, cost, mx = (o[mf] if gap else stop), TAKER, mf
            if gap:
                lim = o[mf]                                     # it gapped through both: filled and stopped at the open
        else:
            s_hit = (lo[mf + 1:end] < stop) if sd > 0 else (hi[mf + 1:end] > stop)
            g_hit = (hi[mf + 1:end] > tgt) if sd > 0 else (lo[mf + 1:end] < tgt)
            i_s = np.argmax(s_hit) if s_hit.any() else None
            i_g = np.argmax(g_hit) if g_hit.any() else None
            first = None
            if i_s is not None and (i_g is None or i_s < i_g or (i_s == i_g and not optimistic)):
                first = ('stop', i_s)
            elif i_g is not None:
                first = ('tgt', i_g)
            if first:
                m_ = mf + 1 + first[1]
                if first[0] == 'stop':
                    gap = (sd > 0 and o[m_] < stop) or (sd < 0 and o[m_] > stop)
                    ex, cost, mx = (o[m_] if gap else stop), TAKER, m_
                else:
                    ex, cost, mx = tgt, MAKER, m_
        if ex is None:                                          # time exit at the close of hour h + 12
            hx = min(h + HOLD, n - 1)
            px = C[hx, j]
            if np.isnan(px):
                px = cl[end - 1] if end > mf else lim
            ex, cost = px, TAKER
        else:
            hx = int((t[mx] - T[0]) // H)
        # hourly marks, as the R3a ledger books them
        rows = [(h, -MAKER * SIZE)]
        last = lim
        if hx == h:
            rows.append((h, sd * (ex / last - 1) * SIZE - cost * SIZE))
        else:
            rows.append((h, sd * (C[h, j] / last - 1) * SIZE)); last = C[h, j]
            for hh in range(h + 1, hx + 1):
                if F[hh, j]:
                    rows.append((hh, -sd * F[hh, j] * SIZE))
                if hh == hx:
                    rows.append((hh, sd * (ex / last - 1) * SIZE - cost * SIZE))
                elif not np.isnan(C[hh, j]):
                    rows.append((hh, sd * (C[hh, j] / last - 1) * SIZE)); last = C[hh, j]
        out[h] = (hx, rows, cost == MAKER)
    return out, cover, miss


def book(n, trades):
    """pass 2: one position per coin, at most CAP open, exits before fills,
    coins in index order -- the R3a ledger's own order"""
    pnl = np.zeros(n)
    by_hour = {}
    for j, tr in trades.items():
        for h, v in tr.items():
            by_hour.setdefault(h, []).append((j, v))
    open_ = {}                                   # j -> exit hour
    fills = wins = 0
    for h in sorted(by_hour):
        for j in [j for j, hx in open_.items() if hx <= h]:
            del open_[j]
        for j, (hx, rows, win) in sorted(by_hour[h]):
            if len(open_) >= CAP or j in open_:
                continue
            fills += 1; wins += int(win)
            for hh, v in rows:
                pnl[hh] += v
            if hx > h:
                open_[j] = hx
    return pnl, fills, wins


def main(argv):
    h1, bdir, m1 = argv[1:4]
    outp = argv[argv.index('--out') + 1] if '--out' in argv else None
    t0 = time.time(); res = {}
    M.TOPN = 20
    T, syms, O, Hh, L, C, QV, TB, U, F = M.load(h1, bdir)
    r1 = C / M.lag(C, 1) - 1
    sig = M.roll_std(r1, 168)
    w = (T >= W0) & (T < W1)
    print(f"loaded {len(syms)} coins, {w.sum()} window hours  [{time.time()-t0:.0f}s]", flush=True)
    # reference: the R3a hourly simulator on the same coins and window
    X.OOS = W0
    Cw = np.where(T[:, None] < W1, C, np.nan)
    pnl, fills, wins = X.lp(T, O, Hh, L, Cw, U, F, sig, U)
    s, _, _ = X.daily_stats(T[w], pnl[w], 'R4-H  hourly bars, stop first (R3a code)', f"| {fills} fills, {100*wins/max(fills,1):.0f}% target")
    res['R4-H'] = s
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'omega_c490_research.py')).read()
    code = src[src.index('def lp('):src.index('# ─── R3b')]
    code = code.replace("            if (sd > 0 and lo < p['stop']) or (sd < 0 and hi > p['stop']):\n                ex, cost = p['stop'], TAKER\n            elif (sd > 0 and hi > p['target']) or (sd < 0 and lo < p['target']):\n                ex, cost = p['target'], MAKER; wins += 1",
                        "            if (sd > 0 and hi > p['target']) or (sd < 0 and lo < p['target']):\n                ex, cost = p['target'], MAKER; wins += 1\n            elif (sd > 0 and lo < p['stop']) or (sd < 0 and hi > p['stop']):\n                ex, cost = p['stop'], TAKER")
    code = code.replace("if (sd > 0 and L[h, j] < stop) or (sd < 0 and Hh[h, j] > stop):", "if False:")
    assert code.count('if False:') == 1
    ns = dict(X.__dict__); ns['OOS'] = W0
    exec(code.replace('def lp(', 'def lp_opt('), ns)
    pnl, fills, wins = ns['lp_opt'](T, O, Hh, L, Cw, U, F, sig, U)
    s, _, _ = X.daily_stats(T[w], pnl[w], 'R4-Ho hourly bars, optimistic', f"| {fills} fills, {100*wins/max(fills,1):.0f}% target")
    res['R4-Ho'] = s
    # the minute paths
    have = {s_: os.path.join(m1, s_ + '.npz') for s_ in syms if os.path.exists(os.path.join(m1, s_ + '.npz'))}
    need = [j for j, s_ in enumerate(syms) if U[w][:, j].any()]
    print(f"minute data for {sum(1 for j in need if syms[j] in have)} of {len(need)} universe coins  [{time.time()-t0:.0f}s]", flush=True)
    for name, opt in (('R4-M  1-minute path, stop first (PRIMARY)', False), ('R4-Mo 1-minute path, target first', True)):
        trades, cov, miss = {}, 0, 0
        for j in need:
            if syms[j] not in have:
                continue
            z = np.load(have[syms[j]])
            mm = {k: z[k] for k in ('t', 'o', 'h', 'l', 'c')}
            trades[j], c_, m_ = coin_trades(j, T, C, F, sig, U, mm, opt)
            cov += c_; miss += m_
        pnl, fills, wins = book(len(T), trades)
        s, du, dr = X.daily_stats(T[w], pnl[w], name, f"| {fills} fills, {100*wins/max(fills,1):.0f}% target, minute coverage {100*cov/max(cov+miss,1):.1f}%")
        res[name.split()[0]] = s
        if not opt:
            yrs = {}
            for d, x in zip(du, dr):
                yrs.setdefault(dt.datetime.utcfromtimestamp(d / 1000).strftime('%Y-%m')[:4], []).append(x)
            print('      by year: ' + '  '.join(f"{y} {100*sum(v):+.1f}%" for y, v in sorted(yrs.items())), flush=True)
    pm, pmo = res.get('R4-M'), res.get('R4-Mo')
    verdict = 'ADMIT' if pm and pm['admitted'] else ('INCONCLUSIVE' if pmo and pmo['admitted'] else 'FAIL')
    print(f"\nVERDICT (pre-registered): {verdict}   [{time.time()-t0:.0f}s]", flush=True)
    res['verdict'] = verdict
    if outp:
        json.dump(res, open(outp, 'w'), indent=1, default=float)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
