"""C486 bench: can the bot tell in advance whether chase entries are working?

THE LIVE FINDING that motivates it (24-25 Sep, 164 live trades replayed on
Bitget candles): the bot's picks do no better than any same-style 'chase'
entry in the same hour (selection edge ~0 before C485), and whether the day is
profitable tracks whether chase entries are working market-wide that day
(21 and 24 Sep good, 22/23/25 Sep bad for chase-longs). If that regime
persists for hours, a gate 'take chase-longs only while chase-longs have
recently been working across the market' would cut the bad days.

SETUP (15m corpus, 32 coins, corpusO Feb-Jun and corpusL May-Sep):
  chase-long  = 3h return >= +2% and price in the top quarter of its 3h range
  chase-short = mirror.  Outcome = the next 1h move in the trade's direction,
  minus 0.08% fees.  Non-overlapping per coin (one per hour).
  REGIME at time t = mean outcome of every same-side setup, on ANY coin, whose
  1h outcome had FULLY RESOLVED by t (no look-ahead), over the last K hours.
  Gate = take the setup only if REGIME > 0 (and at least N resolved setups).
Four-way split: time (corpusO / corpusL) x coins (alternate halves).
Admission (the project's bar): gated beats ungated in >= 3 of 4 splits AND
the gated-minus-ungated difference has |t| >= 2 (day-clustered).
"""
import os, sys, math, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omega_c485_tier1_bench import day_t

FEE = 0.08


def load(corpus, sym):
    rows = []
    for ln in open(os.path.join(corpus, f'{sym}USDT.csv')):
        p = ln.strip().split(',')
        if len(p) >= 6:
            try:
                rows.append([float(x) for x in p[:6]])
            except ValueError:
                pass
    rows.sort(key=lambda r: r[0])
    return rows


def setups(corpus, syms):
    """(t_ms, t_resolved_ms, sym, side, outcome%)"""
    out = []
    for sym in syms:
        R = load(corpus, sym)
        last = {1: -99, -1: -99}
        for i in range(12, len(R) - 4):
            c = R[i][4]; c0 = R[i - 12][4]
            hi = max(r[2] for r in R[i - 12:i + 1]); lo = min(r[3] for r in R[i - 12:i + 1])
            pos = (c - lo) / (hi - lo) if hi > lo else 0.5
            r3 = (c / c0 - 1) * 100
            for sg, ok in ((1, r3 >= 2 and pos >= 0.75), (-1, r3 <= -2 and pos <= 0.25)):
                if ok and i - last[sg] >= 4:
                    last[sg] = i
                    out.append((int(R[i][0]), int(R[i + 4][0]), sym, sg, sg * (R[i + 4][4] / c - 1) * 100 - FEE))
    return sorted(out)


def gate(S, side, K_h, N_min):
    """For each setup of `side`, the regime reading from resolved setups in the last K hours."""
    res = [(tr, o) for (t, tr, s, sg, o) in S if sg == side]
    res.sort()
    times = [x[0] for x in res]
    import bisect
    out = []
    for (t, tr, s, sg, o) in S:
        if sg != side:
            continue
        a = bisect.bisect_left(times, t - K_h * 3600000); b = bisect.bisect_right(times, t)
        window = [res[j][1] for j in range(a, b)]
        reg = st.mean(window) if len(window) >= N_min else None
        out.append((t, s, o, reg))
    return out


if __name__ == '__main__':
    syms = sorted(f[:-8] for f in os.listdir('corpusO') if f.endswith('USDT.csv')
                  and os.path.exists(os.path.join('corpusL', f)))
    half = {s: ('A' if i % 2 == 0 else 'B') for i, s in enumerate(syms)}
    data = {c: setups(c, syms) for c in ('corpusO', 'corpusL')}
    print('C486 regime bench - chase entries gated by whether chase entries have recently worked')
    for side, nm in ((1, 'LONG chases'), (-1, 'SHORT chases')):
        print(f'\n {nm}')
        base_all = [o for c in data for (t, tr, s, sg, o) in data[c] if sg == side]
        print(f'   ungated: n={len(base_all)}  mean {st.mean(base_all):+.4f}%')
        for K in (2, 4, 8, 24):
            for N in (10,):
                cells = {}; diffs = []
                for c in data:
                    G = gate(data[c], side, K, N)
                    for sp in ('A', 'B'):
                        rows = [(t, o, reg) for (t, s, o, reg) in G if half[s] == sp and reg is not None]
                        if not rows: continue
                        take = [o for t, o, reg in rows if reg > 0]
                        allr = [o for t, o, reg in rows]
                        cells[(c[6], sp)] = (st.mean(take) if take else float('nan'), st.mean(allr), len(take), len(allr))
                        # per-setup contribution for the t-stat: gated outcome minus ungated mean
                        for t, o, reg in rows:
                            diffs.append((t, (o if reg > 0 else 0.0) - o * 0 - (0.0)))
                better = sum(1 for v in cells.values() if v[0] == v[0] and v[0] > v[1])
                # t of 'taken minus skipped' mean difference, day-clustered via two means
                take_all = [(t, o) for c in data for (t, s, o, reg) in gate(data[c], side, K, N) if reg is not None and reg > 0]
                skip_all = [(t, o) for c in data for (t, s, o, reg) in gate(data[c], side, K, N) if reg is not None and reg <= 0]
                mt, tt = st.mean(o for _, o in take_all), day_t(take_all)[0]
                ms, ts_ = st.mean(o for _, o in skip_all), day_t(skip_all)[0]
                se = math.sqrt((mt / tt) ** 2 + (ms / ts_) ** 2) if tt and ts_ else float('inf')
                tdiff = (mt - ms) / se if se and math.isfinite(se) else 0.0
                cs = '  '.join(f"{k[0]}{k[1]}:{v[0]:+.3f}/{v[1]:+.3f}" for k, v in sorted(cells.items()))
                print(f'   K={K:>2}h: taken n={len(take_all):5} {mt:+.4f}%  skipped n={len(skip_all):5} {ms:+.4f}%  '
                      f'taken-minus-skipped t={tdiff:+.2f}  gated beats ungated {better}/4   [{cs}]')
