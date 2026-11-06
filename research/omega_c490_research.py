#!/usr/bin/env python3
"""C490 research engine: round 3 (research/c490_preregistration.md, committed first).

    python3 research/omega_c490_research.py H1_DIR BNC_DIR SPOT_DIR SPOT_MAP [--out results.json]

R3a  LP / LPh / LPm  liquidity-provision mean reversion with resting limit orders (hourly)
R3b  IND             per-asset individualised selection of trend / revert / flat (4-hour holds)
R3c  CARRY           spot-perp cash-and-carry on funding (daily)
R3d  LOOKBACK        per-asset walk-forward trend lookback vs the pooled C1
"""
import os, sys, json, math, time, datetime as dt, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R488
import omega_c489_research as M

warnings.simplefilter('ignore')
H, DAY = 3600000, 86400000
MAKER, TAKER = 0.0002, 0.0008               # perp: maker fee; taker fee + half-spread
SPOT = 0.0012                               # spot taker 0.10% + half-spread 0.02%
OOS = M.OOS_FROM


def daily_stats(T, x, label, extra=''):
    du, dr = M.to_daily(T, x)
    s = R488.stats(dr, du)
    R488.show(label, s, extra)
    return s, du, dr


# ─── R3a: liquidity provision ────────────────────────────────────────────────
def lp(T, O, Hh, L, C, U, F, sig, allow, k=2.0, hold=12, size=0.10, cap=10):
    """event-driven, hour by hour. Limits placed at the close of hour h-1 at
    C(1 -/+ k sigma) fill in hour h only on a trade THROUGH the price; stop is
    checked before target; target never fills in the fill hour."""
    n, m = C.shape
    pnl = np.zeros(n)
    pos = []            # dict(j, side, last, stop, target, expiry)
    fills = wins = 0
    busy = np.zeros(m, bool)
    for h in range(1, n):
        # 1. open positions: mark, stop, target, time
        keep = []
        for p in pos:
            j, sd = p['j'], p['side']
            lo, hi, c = L[h, j], Hh[h, j], C[h, j]
            if np.isnan(c):
                keep.append(p); continue
            if F[h, j]:
                pnl[h] -= sd * F[h, j] * size
            ex = None
            if (sd > 0 and lo < p['stop']) or (sd < 0 and hi > p['stop']):
                ex, cost = p['stop'], TAKER
            elif (sd > 0 and hi > p['target']) or (sd < 0 and lo < p['target']):
                ex, cost = p['target'], MAKER; wins += 1
            elif h >= p['expiry']:
                ex, cost = c, TAKER
            if ex is not None:
                pnl[h] += sd * (ex / p['last'] - 1) * size - cost * size
                busy[j] = False
            else:
                pnl[h] += sd * (c / p['last'] - 1) * size
                p['last'] = c
                keep.append(p)
        pos = keep
        # 2. new fills from the limits placed at the close of h-1
        if T[h] < OOS:
            continue
        cand = np.nonzero(allow[h - 1] & U[h - 1] & ~busy & ~np.isnan(sig[h - 1]) & ~np.isnan(C[h]))[0]
        for j in cand:
            if len(pos) >= cap:
                break
            c0, s0 = C[h - 1, j], sig[h - 1, j]
            for sd, lim in ((1, c0 * (1 - k * s0)), (-1, c0 * (1 + k * s0))):
                if len(pos) >= cap or busy[j]:
                    continue
                hit = (L[h, j] < lim) if sd > 0 else (Hh[h, j] > lim)
                if not hit:
                    continue
                fills += 1
                stop = lim * (1 - k * s0) if sd > 0 else lim * (1 + k * s0)
                pnl[h] -= MAKER * size
                if (sd > 0 and L[h, j] < stop) or (sd < 0 and Hh[h, j] > stop):
                    pnl[h] += sd * (stop / lim - 1) * size - TAKER * size          # stopped in the fill hour
                    continue
                pnl[h] += sd * (C[h, j] / lim - 1) * size
                busy[j] = True
                pos.append(dict(j=j, side=sd, last=C[h, j], stop=stop, target=c0, expiry=h + hold))
    return pnl, fills, wins


# ─── R3b: per-asset individualised selection ─────────────────────────────────
def ind(T, C, U, Fm, size=0.05, look_days=60, gate=0.001):
    n, m = C.shape
    starts = np.nonzero((T // H) % 4 == 0)[0]
    starts = starts[starts + 4 < n]
    blk = np.full((len(starts), m), np.nan)
    for b, s in enumerate(starts):
        blk[b] = C[s + 4] / C[s] - 1
    sig = {'TREND': np.sign(np.nan_to_num(Fm['z_r24'][starts])), 'REVERT': -np.sign(np.nan_to_num(Fm['z_r4'][starts]))}
    net = {}
    for k, sg in sig.items():
        turn = np.abs(np.diff(np.vstack([np.zeros(m), sg]), axis=0))
        net[k] = sg * np.nan_to_num(blk) - turn * TAKER
    cum = {k: np.cumsum(v, axis=0) for k, v in net.items()}
    cnt = np.cumsum(np.abs(sig['TREND']) > 0, axis=0)
    L = look_days * 6
    pos = np.zeros((len(starts), m))
    choice = np.zeros(m, dtype=int)                 # 1 TREND, 2 REVERT, chosen once a day at 00:00 UTC
    chosen_ok = np.zeros(m, bool)
    for b in range(L + 1, len(starts)):
        if (T[starts[b]] // H) % 24 == 0:
            bestv = np.full(m, -np.inf); choice = np.zeros(m, dtype=int)
            for code, k in ((1, 'TREND'), (2, 'REVERT')):
                mv = (cum[k][b - 1] - cum[k][b - L - 1]) / L          # trailing mean net per block, past only
                better = mv > bestv
                bestv = np.where(better, mv, bestv); choice = np.where(better, code, choice)
            chosen_ok = bestv > gate
        live = chosen_ok & U[starts[b]]
        pos[b] = np.where(live, np.where(choice == 1, sig['TREND'][b], sig['REVERT'][b]), 0.0)
    pnl_b = np.nansum(pos * np.nan_to_num(blk), axis=1) * size - np.abs(np.diff(np.vstack([np.zeros(m), pos]), axis=0)).sum(1) * TAKER * size
    hourly = np.zeros(n)
    hourly[starts + 4] = pnl_b
    return hourly, int((np.abs(np.diff(np.vstack([np.zeros(m), pos]), axis=0)) > 0).sum())


# ─── R3c: spot-perp carry ────────────────────────────────────────────────────
def carry(Td, dsyms, dclose, dqv, dfund, spot_dir, spot_map, size=0.10, cap=8, enter=0.10, exit_=0.05):
    R488.TOPN = 40
    el = R488.universe(dclose, dqv)
    idx = {int(t): i for i, t in enumerate(Td)}
    sp = np.full_like(dclose, np.nan)
    for j, s in enumerate(dsyms):
        mp = spot_map.get(s)
        if not mp:
            continue
        p = os.path.join(spot_dir, mp[0] + '.json')
        if not os.path.exists(p):
            continue
        for t, c in json.load(open(p)):
            i = idx.get(int(t) // DAY * DAY)
            if i is not None:
                sp[i, j] = c
    f3 = np.full_like(dfund, np.nan)
    for i in range(3, len(dfund)):
        f3[i] = dfund[i - 2:i + 1].sum(0) / 3 * 365
    rp = R488.returns(dclose); rs = R488.returns(sp)
    held = np.zeros(dclose.shape[1], bool)
    pnl = np.zeros(len(Td)); npos = np.zeros(len(Td))
    for i in range(4, len(Td)):
        # the day's P&L on what was held from the previous close
        for j in np.nonzero(held)[0]:
            if np.isnan(rp[i, j]) or np.isnan(rs[i, j]):
                held[j] = False
                pnl[i] -= (SPOT + TAKER) * size                 # forced exit (delisting / gap)
                continue
            pnl[i] += (dfund[i, j] + rs[i, j] - rp[i, j]) * size
        # decide at this close
        ok = el[i] & ~np.isnan(sp[i]) & ~np.isnan(f3[i])
        for j in np.nonzero(held & (~ok | (np.nan_to_num(f3[i]) < exit_)))[0]:
            held[j] = False; pnl[i] -= (SPOT + TAKER) * size
        free = cap - held.sum()
        if free > 0:
            cand = np.nonzero(ok & ~held & (np.nan_to_num(f3[i]) > enter))[0]
            cand = cand[np.argsort(-f3[i][cand])][:free]
            for j in cand:
                held[j] = True; pnl[i] -= (SPOT + TAKER) * size
        npos[i] = held.sum()
    return pnl, npos


# ─── R3d: per-asset lookback ─────────────────────────────────────────────────
def lookback(Td, dclose, dqv, dfund):
    R488.TOPN = 40
    r = R488.returns(dclose); sd = R488.trailing_std(r, 30)
    el = R488.universe(dclose, dqv); sc = np.nan_to_num(R488.vol_scale(sd)); N = 40
    Wd = {d: R488.banded(np.where(el, np.sign(np.nan_to_num(R488.lagret(dclose, d))) * sc / N, 0.0)) for d in (7, 14, 28, 56)}
    pooled = R488.banded(np.where(el, sum(np.sign(np.nan_to_num(R488.lagret(dclose, d))) for d in (7, 14, 28, 56)) / 4.0 * sc / N, 0.0))
    def coin_pnl(W):
        wl = np.zeros_like(W); wl[1:] = W[:-1]
        dw = np.abs(np.diff(np.vstack([np.zeros(W.shape[1]), wl]), axis=0))
        return wl * np.nan_to_num(r) - wl * dfund - dw * R488.COST
    P = {d: coin_pnl(W) for d, W in Wd.items()}
    C = {d: np.cumsum(p, axis=0) for d, p in P.items()}
    Wi = np.zeros_like(pooled)
    ds = list(Wd)
    month = None; pick = np.full(dclose.shape[1], 28)
    for i in range(len(Td)):
        mo = dt.datetime.utcfromtimestamp(Td[i] / 1000).strftime('%Y-%m')
        if mo != month and i > 181:
            month = mo
            sc_ = np.stack([C[d][i - 1] - C[d][i - 181] for d in ds])
            pick = np.array(ds)[np.argmax(sc_, axis=0)]
        for d in ds:
            m_ = pick == d
            Wi[i, m_] = Wd[d][i, m_]
    return R488.pnl(Wi, r, dfund, 1)[0], R488.pnl(pooled, r, dfund, 1)[0]


def main(argv):
    h1, bdir, sdir, smap = argv[1:5]
    outp = argv[argv.index('--out') + 1] if '--out' in argv else None
    t0 = time.time(); res = {}
    print("loading the hourly archive ...", flush=True)
    T, syms, O, Hh, L, C, QV, TB, U, F = M.load(h1, bdir)
    r1, Fm = M.features(T, syms, O, Hh, L, C, QV, TB, U, F)
    sig = M.roll_std(r1, 168)
    oos = T >= OOS
    print(f"\nR3a LIQUIDITY PROVISION (limits at 2 sigma, maker in, maker target / taker stop+time)  [{time.time()-t0:.0f}s]", flush=True)
    # for a coin that just fell (state down), mk1 < 0 means continuation expected -> NOT a reversal;
    # the Markov filter keeps a coin only when its chain expects the move to revert
    mk_ok = np.where(Fm['z_r1'] < -0.5, Fm['mk1'] > 0, np.where(Fm['z_r1'] > 0.5, Fm['mk1'] < 0, True))
    for name, allow in (('LP  (primary)', np.ones_like(U)), ('LPh (Hurst < 0.5)', Fm['hurst'] < 0.5), ('LPm (Markov expects reversion)', mk_ok)):
        pnl, fills, wins = lp(T, O, Hh, L, C, U, F, sig, np.nan_to_num(allow).astype(bool))
        s, du, dr = daily_stats(T[oos], pnl[oos], 'R3a ' + name, f"| {fills} fills, {100*wins/max(fills,1):.0f}% hit the target")
        res['R3a ' + name] = s
    print(f"\nR3b PER-ASSET INDIVIDUALISED SELECTION  [{time.time()-t0:.0f}s]", flush=True)
    pnl, trades = ind(T, C, U, Fm)
    s, _, _ = daily_stats(T[oos], pnl[oos], 'R3b IND (trend/revert/flat per coin)', f"| {trades} position changes")
    res['R3b IND'] = s
    print(f"\nDAILY ITEMS  [{time.time()-t0:.0f}s]", flush=True)
    Td, dsyms, dclose, dqv, dfund = R488.load_crypto(bdir)
    smapd = json.load(open(smap))
    pnl, npos = carry(Td, dsyms, dclose, dqv, dfund, sdir, smapd)
    o = Td >= OOS
    s = R488.stats(pnl[o], Td[o]); R488.show('R3c CARRY (spot long + perp short)', s, f"| avg {npos[o].mean():.1f} positions")
    res['R3c CARRY'] = s
    ind_p, pooled_p = lookback(Td, dclose, dqv, dfund)
    s = R488.stats(ind_p[o], Td[o]); R488.show('R3d per-asset lookback C1', s); res['R3d ind'] = s
    s2 = R488.stats(pooled_p[o], Td[o]); R488.show('    pooled C1 (reference)', s2)
    s3 = R488.stats((ind_p - pooled_p)[o], Td[o]); R488.show('R3d difference (must be > 0)', s3); res['R3d diff'] = s3
    # correlation of CARRY with the C488 book, and the equal-risk mix
    R488.TOPN = 20
    rr, Wd, _ = R488.crypto_sleeves(Td, dclose, dqv, dfund)
    Wc = R488.combine({k: Wd[k] for k in ('C1', 'C2', 'C3')}, rr, dfund, 1)
    book = R488.pnl(Wc, rr, dfund, 1)[0]
    x, y = pnl[o], book[o]
    if x.std() > 0:
        rho = np.corrcoef(x, y)[0, 1]
        mix = y / y.std() + x / x.std()
        mix = mix * (y.std())                       # same risk as the book alone
        print(f"\n  CARRY vs book: rho {rho:+.2f}")
        R488.show('  book (top 20)', R488.stats(y, Td[o]))
        R488.show('  book + CARRY at equal risk (same vol)', R488.stats(mix / math.sqrt(2 + 2 * rho) * math.sqrt(1), Td[o]))
        res['carry_rho'] = float(rho)
    if outp:
        json.dump(res, open(outp, 'w'), indent=1, default=float)
    print(f"\n[{time.time()-t0:.0f}s]")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
