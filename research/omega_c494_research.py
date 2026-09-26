#!/usr/bin/env python3
"""C494: maker-first vs taker for the C488 daily rebalance (research/c494_preregistration.md).

    python3 research/omega_c494_research.py need BNC_DIR NEED_JSON     # the coin-months to fetch
    python3 research/omega_c494_research.py run  BNC_DIR ONE_MIN_DIR   # the test

ONE_MIN_DIR holds <SYM>.npz from research/c491_fetch_1m.py (t, o, h, l, c per minute).
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
DAY, MIN = R.DAY, 60000
H, TAKER, MAKER = 0.0002, 0.0006, 0.0002
START = int(dt.datetime(2024, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
END = int(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)


def trades(bdir, tv=0.20, equity=250.0, floor=6.0):
    """the $250 top-20 book's daily trades: (exec_ms, symbol, side, |dw|, liquidity)"""
    R.EXCLUDE = set(R.EXCLUDE) | TRADFI
    R.TOPN = 20
    T, syms, close, qv, fund = R.load_crypto(bdir)
    r, W, elig = R.crypto_sleeves(T, close, qv, fund)
    Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1, target_vol=tv)
    Wm = np.where(np.abs(Wc) * equity >= floor, Wc, 0.0)
    med30 = np.full_like(qv, np.nan)
    for i in range(31, len(qv)):
        med30[i] = np.nanmedian(qv[i - 30:i], axis=0)
    out = []
    for i in range(1, len(T)):
        ex = int(T[i]) + DAY + 5 * MIN            # decided at the close of day i, executed 00:05 next day
        if not (START <= ex < END):
            continue
        dw = Wm[i] - Wm[i - 1]
        for j in np.nonzero(np.abs(dw) > 1e-12)[0]:
            out.append((ex, syms[j], 1 if dw[j] > 0 else -1, float(abs(dw[j])), float(med30[i, j])))
    turn = {}
    for i in range(1, len(T)):
        y = dt.datetime.utcfromtimestamp(T[i] / 1000).year
        turn[y] = turn.get(y, 0.0) + float(np.abs(Wm[i] - Wm[i - 1]).sum())
    return out, turn


def need(bdir, outp):
    tr, _ = trades(bdir)
    nd = {}
    for ex, s, side, q, liq in tr:
        nd.setdefault(s, set()).add(dt.datetime.utcfromtimestamp(ex / 1000).strftime('%Y-%m'))
    json.dump({s: sorted(v) for s, v in nd.items()}, open(outp, 'w'))
    print(f"{len(tr)} trades, {len(nd)} coins, {sum(len(v) for v in nd.values())} coin-months")


def cost_pair(M, ex, side, W):
    """(taker cost, maker-first cost, filled?) or None if the minutes are missing"""
    t, o, h, l = M
    i0 = np.searchsorted(t, ex)
    if i0 >= len(t) or t[i0] != ex:
        return None
    iw = np.searchsorted(t, ex + W * MIN)
    if iw >= len(t) or t[iw] != ex + W * MIN:
        return None
    A = o[i0]
    seg = slice(i0 + 1, iw)
    if side > 0:
        lim = A * (1 - H)
        filled = bool(np.any(l[seg] < lim))
        miss = TAKER + H + (o[iw] - A) / A
    else:
        lim = A * (1 + H)
        filled = bool(np.any(h[seg] > lim))
        miss = TAKER + H + (A - o[iw]) / A
    return TAKER + H, (MAKER - H) if filled else miss, filled


def run(bdir, mdir):
    tr, turn = trades(bdir)
    cache = {}
    def M(s):
        if s not in cache:
            p = os.path.join(mdir, s + '.npz')
            if not os.path.exists(p):
                cache[s] = None
            else:
                z = np.load(p); cache[s] = (z['t'].astype(np.int64), z['o'], z['h'], z['l'])
        return cache[s]
    liqs = np.array([x[4] for x in tr if not np.isnan(x[4])])
    cuts = np.quantile(liqs, [1 / 3, 2 / 3]) if len(liqs) else [0, 0]
    res = {}
    for W in (30, 10, 60):
        days, fills, drift_miss, per_terc = {}, [], [], {0: [], 1: [], 2: []}
        dropped = 0
        for ex, s, side, q, liq in tr:
            m = M(s)
            c = cost_pair(m, ex, side, W) if m is not None else None
            if c is None:
                dropped += 1; continue
            tk, mk, f = c
            d = days.setdefault(ex // DAY * DAY, [0.0, 0.0, 0.0])
            d[0] += q * tk; d[1] += q * mk; d[2] += q
            fills.append((q, f))
            if not f:
                drift_miss.append(mk - TAKER - H)
            terc = int(np.searchsorted(cuts, liq)) if not np.isnan(liq) else 1
            per_terc[terc].append((q, tk - mk))
        Td = np.array(sorted(days)); sv = np.array([(days[t][0] - days[t][1]) / days[t][2] for t in Td])
        mk_mean = sum(days[t][1] for t in Td) / sum(days[t][2] for t in Td)
        q4 = np.array_split(sv, 4)
        fr = sum(q for q, f in fills if f) / sum(q for q, f in fills)
        t_nw = R.nw_t(sv)
        ok = bool(t_nw >= 2 and sum(x.mean() > 0 for x in q4) >= 3 and sv.mean() >= 0.0002)
        yr = np.mean([v for k, v in turn.items() if 2021 <= k <= 2025])
        res[W] = dict(trades=len(fills), dropped=dropped, days=len(Td), fill_rate=fr, maker_cost=mk_mean,
                      saving=float(sv.mean()), t=float(t_nw), q=[float(x.mean()) for x in q4],
                      drift_missed=float(np.mean(drift_miss)) if drift_miss else float('nan'),
                      terciles=[float(sum(q * x for q, x in v) / max(sum(q for q, x in v), 1e-12)) for k, v in sorted(per_terc.items())],
                      turnover_yr=float(yr), saving_yr_dial15=float(sv.mean() * yr), adopt=ok)
        x = res[W]
        print(f"W={W:2} min{' (PRIMARY)' if W == 30 else ''}: {x['trades']} trades on {x['days']} days "
              f"(dropped {dropped} without minutes) | fill rate {100*fr:.0f}% | maker-first cost "
              f"{100*mk_mean:.3f}% vs taker 0.080% | saving {100*x['saving']:+.3f}% t {t_nw:+.2f} "
              f"quarters {['%+.3f' % (100*v) for v in x['q']]} | missed fills drifted {100*x['drift_missed']:+.3f}% "
              f"| by liquidity (low/mid/high) {['%+.3f' % (100*v) for v in x['terciles']]} "
              f"| {100*x['saving_yr_dial15']:+.2f}%/yr at dial 15 (turnover {yr:.0f}x) | {'ADOPT' if ok else '-'}", flush=True)
    return res


if __name__ == '__main__':
    if sys.argv[1] == 'need':
        need(sys.argv[2], sys.argv[3])
    else:
        out = run(sys.argv[2], sys.argv[3])
        if '--out' in sys.argv:
            json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1, default=float)
