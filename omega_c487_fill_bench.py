#!/usr/bin/env python3
"""Paper fills vs what the market really did, trade by trade  [C487]

    python3 omega_c487_fill_bench.py LOGDIR WORKDIR [--spread-bp 3.91]

LOGDIR  : a folder of omega_report_*.log files (e.g. the `logs` branch).
WORKDIR : the candle cache omega_live_forensics.py uses (fetched if missing).

For every closed trade, from Bitget 1-minute candles:
 1. FIXED HOLD: the trade's move from its entry price after 5 min .. 6 h, in
    its own direction, before costs. Answers "do the ENTRIES carry an edge,
    or do the exits?"
 2. ENTRY FILLS: would a bid/ask resting at the entry price have been filled
    AFTER the entry minute? (a print strictly through it within 1/2/5 min).
    The trades the market never came back to are the ones a resting order
    misses live -- and paper, which judged fills by the 5 minutes BEFORE the
    order, kept all of them.
 3. MAKER EXITS: did the market reach the resting exit within 1 min?
 4. REALISTIC TOTALS: paper as booked; resting entries filled honestly; every
    entry crossing the spread as a taker; and taker-minus-honest-maker in a
    four-way split (time halves x coin halves) with a day-clustered t.
Times in the reports are minute-truncated, so "not back within k min" counts
from the END of the entry minute: the missed count is an upper bound.
"""
import os, re, sys, glob, json, math, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_live_forensics as lf


def exit_fill_types(logdir):
    fill = {}
    for p in sorted(glob.glob(os.path.join(logdir, 'omega_report_2026*.log'))):
        L = open(p, encoding='utf-8', errors='replace').read().split('\n')
        for i, ln in enumerate(L):
            m = re.match(r'^\s+<<\s+\d\d:\d\d\s+CLOSE\s+(\S+)\s+(LONG|SHORT)\s+@(\S+)', ln)
            if m and i + 1 < len(L):
                fill[(m.group(1), m.group(2), float(m.group(3)))] = L[i + 1].strip().split()[-1].lower()
    return fill


def after(rows, t_ms, k):
    m0 = t_ms // 60000 * 60000
    return [r for r in rows if r[0] > m0][:k]


def through(rows, t_str, k, price, want_low, strict=True):
    A = after(rows, lf.ms(t_str), k)
    if not A:
        return None
    if want_low:
        return any((c[3] < price) if strict else (c[3] <= price) for c in A)
    return any((c[2] > price) if strict else (c[2] >= price) for c in A)


def day_t(pairs):
    d = collections.defaultdict(list)
    for v, day in pairs:
        d[day].append(v)
    n = sum(len(x) for x in d.values())
    if len(d) < 3 or n == 0:
        return float('nan')
    m = sum(sum(x) for x in d.values()) / n
    se = math.sqrt(sum(sum(v - m for v in x) ** 2 for x in d.values())) / n
    return m / se if se else float('nan')


def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    logdir, work = argv[1], argv[2]
    sp_bp = float(argv[argv.index('--spread-bp') + 1]) if '--spread-bp' in argv else 3.91
    os.makedirs(work, exist_ok=True)
    trades = lf.parse_trades(logdir)
    C = lf.fetch_all(trades, work)
    fills = exit_fill_types(logdir)
    rows = []
    for t in trades:
        cs = C.get(f"{t['sym']}|{t['t_open']}|{t['t_close']}") or []
        if not cs:
            continue
        sg = 1 if t['side'] == 'LONG' else -1
        by = {c[0]: c for c in cs}
        t0 = lf.ms(t['t_open']) // 60000 * 60000
        r = dict(t=t, sg=sg, rows=cs, day=t['t_open'][:10], notl=(t.get('margin') or 0) * (t.get('lev') or 1),
                 xfill=fills.get((t['sym'], t['side'], t['exit']), '?'))
        for h in (5, 15, 30, 60, 120, 240, 360):
            c = by.get(t0 + h * 60000)
            r[h] = sg * (c[4] / t['entry'] - 1) * 100 if c else None
        rows.append(r)
    print(f"{len(rows)} closed trades with candles  ({rows[0]['day']} .. {rows[-1]['day']})\n")

    print("1. FIXED HOLD FROM THE ENTRY PRICE (the trade's own direction, before costs)")
    print(f"   {'hold':>6} {'n':>4} {'mean %':>8} {'median %':>9} {'up %':>5} {'t(day)':>7}")
    for h in (5, 15, 30, 60, 120, 240):
        R = [r for r in rows if r[h] is not None]
        if R:
            v = [r[h] for r in R]
            print(f"   {h:>4}m {len(v):>5} {st.mean(v):>+8.3f} {st.median(v):>+9.3f} {100 * sum(x > 0 for x in v) / len(v):>5.0f}"
                  f" {day_t([(r[h], r['day']) for r in R]):>+7.2f}")
    act = [100 * r['t']['whole'] / r['notl'] for r in rows if r['notl']]
    print(f"   what the bot's own exits made: {st.mean(act):+.3f} % of notional per trade after fees\n")

    print("2. ENTRY FILLS: did the market trade THROUGH the entry price after the entry minute?")
    for k in (1, 2, 5):
        R = [r for r in rows if through(r['rows'], r['t']['t_open'], k, r['t']['entry'], r['sg'] > 0) is not None]
        n = sum(through(r['rows'], r['t']['t_open'], k, r['t']['entry'], r['sg'] > 0) for r in R)
        print(f"   within {k} min: {100 * n / max(len(R), 1):.0f}% of {len(R)}")
    def show(name, R):
        if R:
            w = sum(r['t']['whole'] > 0 for r in R)
            print(f"   {name:44} n={len(R):3}  win {100 * w / len(R):3.0f}%  net ${sum(r['t']['whole'] for r in R):+6.2f}")
    fil = [r for r in rows if through(r['rows'], r['t']['t_open'], 2, r['t']['entry'], r['sg'] > 0) is not False]
    mis = [r for r in rows if through(r['rows'], r['t']['t_open'], 2, r['t']['entry'], r['sg'] > 0) is False]
    show("came back through it (a resting order fills)", fil)
    show("never came back (a resting order MISSES)", mis)

    print("\n3. MAKER EXITS: did the market reach the resting exit within 1 min?")
    M = [r for r in rows if r['xfill'] == 'maker']
    hitx = [through(r['rows'], r['t']['t_close'], 1, r['t']['exit'], r['sg'] < 0) for r in M]
    print(f"   {sum(bool(x) for x in hitx)} of {len(M)} maker exits")

    print("\n4. REALISTIC TOTALS")
    tot = collections.Counter(); diffs = []
    coins = sorted({r['t']['sym'] for r in rows}); half = {s: 'A' if i % 2 == 0 else 'B' for i, s in enumerate(coins)}
    cut = sorted(r['t']['t_open'] for r in rows)[len(rows) // 2]
    for r in rows:
        w, notl = r['t']['whole'], r['notl']
        cross = notl * (0.0004 + sp_bp / 1e4)                  # taker premium + the spread
        xr = cross if (r['xfill'] == 'maker' and not through(r['rows'], r['t']['t_close'], 1, r['t']['exit'], r['sg'] < 0)) else 0.0
        filled = through(r['rows'], r['t']['t_open'], 2, r['t']['entry'], r['sg'] > 0) is not False
        tot['paper'] += w
        tot['maker_honest'] += (w - xr) if filled else 0.0
        tot['taker'] += w - xr - cross
        g = ('early' if r['t']['t_open'] < cut else 'late') + half[r['t']['sym']]
        diffs.append(((w - xr - cross) - ((w - xr) if filled else 0.0), g, r['day']))
    print(f"   paper, as booked                         ${tot['paper']:+.2f}")
    print(f"   resting entries filled honestly          ${tot['maker_honest']:+.2f}")
    print(f"   every entry crossing as a taker          ${tot['taker']:+.2f}")
    by = collections.defaultdict(float)
    for d, g, _ in diffs:
        by[g] += d
    print(f"   taker - honest maker: ${sum(d for d, _, _ in diffs):+.2f}, t(day) {day_t([(d, day) for d, _, day in diffs]):+.2f}, "
          f"{sum(v > 0 for v in by.values())}/4 splits  " + ' '.join(f"{g}:{v:+.2f}" for g, v in sorted(by.items())))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
