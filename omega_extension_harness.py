#!/usr/bin/env python3
"""Does prior extension predict the next few hours? The proper test.

WHY THIS EXISTS. Step 1 ranks the universe by "liveliness", which is
definitionally recent movement, so the top of that ranking is the most-extended
cohort. Two live sessions now measure extension as ANTI-predictive:
C420-7 corr -0.212, and 19 Sep corr -0.257 across the bot's own 31 picks.
Two days agreeing is a reason to measure properly. It is not a reason to ship.

THE STANDING RULES THIS OBEYS:
  #9  a feature is not real until it replicates in a SEPARATE BATCH at a
      different time. Within-window splits are not evidence -- so the splits
      here are time-disjoint halves AND pair-disjoint halves, four cells, and
      a result must hold in at least 3 of 4.
  #4a never draw a conclusion from a one-sided excursion metric -- so this
      measures close-to-close forward returns, both tails, not favourable
      excursions.
  fees are charged. Maker both ways, 0.04% round trip, the operator's real
      Bitget BASIC schedule.

NON-OVERLAPPING SAMPLES. Forward windows are stepped by their own length, so
no bar is counted twice and the t-statistics are not inflated by overlap.
"""
import csv, glob, math, os, statistics as st, sys

BAR_MIN   = 15
EXT_BARS  = 96          # 24h of prior movement -- what "liveliness" reads
FWD_BARS  = 16          # 4h forward, the bot's own horizon
FEE_RT    = 0.04        # maker both ways, %
QUANTILES = 5

def load(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        sym = os.path.basename(p)[:-4]
        rows = []
        with open(p) as fh:
            for r in csv.reader(fh):
                if len(r) < 5: continue
                try: rows.append((int(r[0]), float(r[4])))
                except ValueError: continue
        rows.sort()
        if len(rows) > EXT_BARS + FWD_BARS + 50:
            out[sym] = rows
    return out

def build(data):
    """One observation per (timestamp, pair): prior extension, forward return."""
    idx = {}
    for sym, rows in data.items():
        for i, (t, c) in enumerate(rows):
            idx.setdefault(t, {})[sym] = (i, c)
    obs = []
    stamps = sorted(idx)
    # step by FWD_BARS so forward windows never overlap
    for k in range(0, len(stamps), FWD_BARS):
        t = stamps[k]
        cell = []
        for sym, (i, c) in idx[t].items():
            rows = data[sym]
            if i < EXT_BARS or i + FWD_BARS >= len(rows): continue
            prior = (c - rows[i - EXT_BARS][1]) / rows[i - EXT_BARS][1] * 100.0
            fwd   = (rows[i + FWD_BARS][1] - c) / c * 100.0
            cell.append((sym, prior, fwd))
        if len(cell) >= 10:          # need a real cross-section to rank within
            obs.append((t, cell))
    return obs

def quintile_table(obs, keep=None):
    """Mean forward return by prior-extension quintile, ranked WITHIN each
    timestamp -- which is the decision the bot actually faces: of the pairs
    available right now, which do I buy?"""
    buckets = [[] for _ in range(QUANTILES)]
    for t, cell in obs:
        c = [x for x in cell if keep is None or keep(x[0])]
        if len(c) < QUANTILES * 2: continue
        c.sort(key=lambda x: x[1])                  # by prior extension
        n = len(c)
        for j, (sym, prior, fwd) in enumerate(c):
            q = min(QUANTILES - 1, j * QUANTILES // n)
            buckets[q].append(fwd - FEE_RT)          # fees charged on every trade
    return buckets

def tstat(v):
    if len(v) < 3: return 0.0
    s = st.pstdev(v)
    return 0.0 if s == 0 else st.mean(v) / (s / math.sqrt(len(v)))

def report(name, buckets):
    print(f"\n  {name}")
    print(f"    {'quintile':<26}{'n':>7}{'mean %':>10}{'t':>8}")
    for q, v in enumerate(buckets):
        if not v: continue
        lab = ('Q1 least extended' if q == 0 else
               f'Q{q+1} most extended' if q == QUANTILES-1 else f'Q{q+1}')
        print(f"    {lab:<26}{len(v):>7}{st.mean(v):>+10.4f}{tstat(v):>8.2f}")
    if buckets[0] and buckets[-1]:
        spread = st.mean(buckets[0]) - st.mean(buckets[-1])
        print(f"    {'Q1 minus Q5 (the edge)':<26}{'':>7}{spread:>+10.4f}")
        return spread
    return None

if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else 'corpusO'
    data = load(d)
    print(f"corpus {d}: {len(data)} pairs, "
          f"{sum(len(v) for v in data.values()):,} bars "
          f"({BAR_MIN}m) -- extension {EXT_BARS*BAR_MIN/60:.0f}h, "
          f"forward {FWD_BARS*BAR_MIN/60:.0f}h, fees {FEE_RT}% round trip")
    obs = build(data)
    print(f"non-overlapping cross-sections: {len(obs):,}")
    print("\n" + "=" * 62)
    print("POOLED (all pairs, all time) -- suggestive only, never decisive")
    print("=" * 62)
    report('pooled', quintile_table(obs))

    # ─── the four-way out-of-sample split ───
    syms = sorted(data)
    A = set(syms[0::2]); B = set(syms[1::2])
    half = len(obs) // 2
    early, late = obs[:half], obs[half:]
    print("\n" + "=" * 62)
    print("FOUR-WAY SPLIT -- time-disjoint x pair-disjoint (standing rule 9)")
    print("=" * 62)
    results = {}
    for tname, sub in (('early', early), ('late', late)):
        for pname, keep in (('pairs A', lambda s: s in A), ('pairs B', lambda s: s in B)):
            sp = report(f'{tname} / {pname}', quintile_table(sub, keep))
            results[f'{tname}/{pname}'] = sp
    print("\n" + "=" * 62)
    print("VERDICT")
    print("=" * 62)
    good = [k for k, v in results.items() if v is not None and v > 0]
    for k, v in results.items():
        print(f"  {k:<18} Q1-Q5 {v:+.4f}%  {'least-extended wins' if v and v>0 else 'no'}")
    print(f"\n  splits where LEAST-extended beat MOST-extended: {len(good)} of 4")
    print("  standing rule: a result ships only at 3 of 4 or better.")
    print(f"  -> {'REPLICATES' if len(good)>=3 else 'DOES NOT REPLICATE — do not act on it'}")
