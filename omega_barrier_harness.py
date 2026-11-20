"""
OMEGA barrier harness — the four-way out-of-sample test the Atlas's standing rule
requires before any entry/exit rule ships.

  ./omega_fetch_corpus.sh      # 35 pairs x 2400 live Bitget 15m bars -> corpus/
  python3 omega_barrier_harness.py

WHY RANDOM ENTRIES ARE THE HONEST NULL: the Atlas measured rho(score, win) = -0.022
on the bot's own logic. The entry score carries no cross-sectional information, so
an unbiased entry IS the bot's entry, statistically. This harness therefore isolates
the EXIT GEOMETRY, which is what C356 found dominates every entry filter.

DESIGN NOTES, each answering a specific Atlas standing rule:
  * NON-OVERLAPPING entries (stride = horizon). Rule: overlapping samples inflate n
    and were what killed the 24h/6-ATR finding.
  * ADVERSE extreme assumed first inside every bar. A reconstruction that books money
    may only ever be worse than reality.
  * BOTH directions on every bar, so drift cancels and no long/short tilt can leak in.
  * Four-way split (time-early/late x pairs A/B) reported per config. Rule 9: this is
    a NECESSARY check against overfitting and is NOT by itself evidence of an edge —
    a separate BATCH at a different time is what settles it.
  * Fees at the bot's real 0.02% maker in / 0.06% taker out.

C459 shipped on this harness agreeing with the independent C356 replay harness
(638k bars, a bear corpus) on a different corpus and a different regime.
"""
import os, glob, math

FEE = 0.08          # maker in 0.02 + taker out 0.06, % of notional
H   = 16            # 4h horizon (bot states 15m-4h)
STRIDE = 16         # non-overlapping (Atlas overlap warning)

def load():
    out = {}
    for f in sorted(glob.glob('corpus/*.csv')):
        sym = os.path.basename(f)[:-4]; rows = []
        for ln in open(f):
            p = ln.strip().split(',')
            if len(p) < 6: continue
            try: rows.append(tuple(float(x) for x in p[:6]))
            except: pass
        rows.sort(key=lambda r: r[0])
        ded = []
        for r in rows:
            if not ded or r[0] != ded[-1][0]: ded.append(r)
        if len(ded) > 400: out[sym] = ded
    return out

def atr_series(rows, n=14):
    out = [None]*len(rows); trs = []
    for i in range(1, len(rows)):
        _,o,h,l,c,_ = rows[i]; pc = rows[i-1][4]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        if len(trs) >= n:
            out[i] = sum(trs[-n:])/n / rows[i][4] * 100.0   # ATR as % of price
    return out

def walk(rows, i, long, atr_pct, tgt_a, stop_a, rung_a=None, be_a=None, rung_frac=0.5):
    """Return net % on notional. Adverse extreme assumed first inside a bar."""
    ep = rows[i][4]
    sgn = 1.0 if long else -1.0
    tgt = tgt_a*atr_pct; stop = -stop_a*atr_pct
    banked = 0.0; rem = 1.0
    cur_stop = stop
    rung_done = False
    for j in range(i+1, min(i+1+H, len(rows))):
        _,o,h,l,c,_ = rows[j]
        hi = (h/ep-1.0)*100.0*sgn; lo = (l/ep-1.0)*100.0*sgn
        adv, fav = (lo, hi) if sgn > 0 else (lo, hi)
        adv = min(hi, lo); fav = max(hi, lo)
        # adverse first
        if adv <= cur_stop:
            return banked + rem*cur_stop - FEE
        if rung_a is not None and not rung_done and fav >= rung_a*atr_pct:
            banked += rung_frac*(rung_a*atr_pct); rem = 1.0-rung_frac
            rung_done = True
            cur_stop = -be_a*atr_pct
            if adv <= cur_stop:                     # BE stop could also hit this bar
                return banked + rem*cur_stop - FEE
        if fav >= tgt:
            return banked + rem*tgt - FEE
    cl = (rows[min(i+H, len(rows)-1)][4]/ep-1.0)*100.0*sgn
    return banked + rem*cl - FEE

def run(data, cfgs):
    res = {k: {'n':0,'sum':0.0,'w':0,'wsum':0.0,'lsum':0.0,
               'splits':{s:{'n':0,'sum':0.0} for s in ('t_early','t_late','pair_A','pair_B')}}
           for k in cfgs}
    for pi,(sym,rows) in enumerate(sorted(data.items())):
        A = atr_series(rows); mid = len(rows)//2
        pset = 'pair_A' if pi % 2 == 0 else 'pair_B'
        for i in range(20, len(rows)-H-1, STRIDE):
            a = A[i]
            if a is None or a <= 0.05 or a > 8.0: continue
            tset = 't_early' if i < mid else 't_late'
            for long in (True, False):
                for k,c in cfgs.items():
                    r = walk(rows, i, long, a, **c)
                    d = res[k]; d['n'] += 1; d['sum'] += r
                    if r > 0: d['w'] += 1; d['wsum'] += r
                    else: d['lsum'] += -r
                    for s in (tset, pset):
                        d['splits'][s]['n'] += 1; d['splits'][s]['sum'] += r
    return res

def show(res, title):
    print(f"\n{title}")
    print(f"  {'config':34}{'n':>7}{'exp %/tr':>10}{'win%':>7}{'payoff':>8}   4-way splits (exp %/tr)")
    for k,d in res.items():
        if not d['n']: continue
        exp = d['sum']/d['n']; wr = d['w']/d['n']*100
        aw = d['wsum']/max(d['w'],1); al = d['lsum']/max(d['n']-d['w'],1)
        po = aw/al if al > 0 else 0
        sp = d['splits']
        parts = ' '.join(f"{sp[s]['sum']/max(sp[s]['n'],1):+.3f}" for s in ('t_early','t_late','pair_A','pair_B'))
        npos = sum(1 for s in ('t_early','t_late','pair_A','pair_B') if sp[s]['sum'] > 0)
        print(f"  {k:34}{d['n']:>7}{exp:+10.4f}{wr:7.1f}{po:8.2f}   {parts}  [{npos}/4]")
