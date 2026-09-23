#!/usr/bin/env python3
"""Trade forensics over the pushed report logs.

    python3 omega_trade_forensics.py <dir-of-omega_report_*.log>

Reads the end-of-session closed-trade tables, then answers one question the
per-trade statistics cannot: DID THE SIZING HELP OR HURT?

Win rate, payoff and expectancy are all computed per trade and are all blind to
how much money was on each one. A book can look fine in every one of them and
still lose (Standing Rule 37).

Position size is not in the log, so it is derived: pnl = N*(move/100) - N*fee,
hence N = pnl/(move/100 - fee). That derivation is biased -- for a small move
the fee dominates, so a small-move trade mechanically gets a big N and a
negative pnl. Every conclusion below is therefore re-run at |move| cuts that
remove the artefact, and the model-free line at the end uses no N at all.
"""
import re, sys, glob, os, math, random, collections, statistics as st

ROW = re.compile(r'^\s{2}(\S+)\s+(LONG|SHORT)\s+([+-][\d.]+)%\s+\$([+-][\d.]+)\s+'
                 r'(?:(\d+)h)?(\d+)m\s+(.*?)\s*\[([WL])\]\s*$')
FEE = 0.0008          # 0.08% round trip; sensitivity is reported where it matters


def load(d):
    T = []
    for p in sorted(glob.glob(os.path.join(d, 'omega_report_*.log'))):
        for line in open(p, encoding='utf-8', errors='replace'):
            m = ROW.match(line.rstrip('\n'))
            if m:
                T.append(dict(sym=m.group(1), side=m.group(2), move=float(m.group(3)),
                              pnl=float(m.group(4)),
                              mins=int(m.group(5) or 0) * 60 + int(m.group(6)),
                              reason=m.group(7).split(':')[0].strip(), wl=m.group(8),
                              src=os.path.basename(p)))
    for r in T:
        d_ = r['move'] / 100 - FEE
        r['N'] = r['pnl'] / d_ if abs(d_) > 1e-4 else None
    return T


def stats(rows):
    w = [r for r in rows if r['wl'] == 'W']; l = [r for r in rows if r['wl'] == 'L']
    net = sum(r['pnl'] for r in rows)
    aw = st.mean([r['pnl'] for r in w]) if w else 0.0
    al = st.mean([r['pnl'] for r in l]) if l else 0.0
    return len(rows), len(w), len(l), net, aw, al, (abs(aw / al) if al else 0.0)


def line(name, rows):
    if not rows: return
    n, w, l, net, aw, al, po = stats(rows)
    print(f"  {name:24} n={n:3}  {w:3}W {l:3}L  win {100*w/n:5.1f}%  payoff {po:5.2f}  "
          f"net ${net:+7.2f}  avg ${net/n:+6.3f}")


def permutation(rows, iters=20000, seed=11):
    """Re-pair the SAME sizes with the SAME moves at random."""
    rows = [r for r in rows if r['N'] and 0 < r['N'] < 3000]
    if len(rows) < 12: return None
    random.seed(seed)
    moves = [r['move'] for r in rows]; Ns = [r['N'] for r in rows]
    actual = sum(r['pnl'] for r in rows)
    sims = []
    for _ in range(iters):
        sh = Ns[:]; random.shuffle(sh)
        sims.append(sum(n * (mv / 100 - FEE) for n, mv in zip(sh, moves)))
    worse = sum(1 for s in sims if s <= actual)
    return len(rows), actual, st.mean(sims), worse / iters


def main(d):
    T = load(d)
    if not T:
        print(f"no closed-trade tables found in {d}"); return 1
    print("=" * 100); print(f"{len(T)} CLOSED TRADES from {d}"); print("=" * 100)
    line("EVERYTHING", T)
    print()
    for s in ('LONG', 'SHORT'): line(s, [r for r in T if r['side'] == s])

    print("\n" + "=" * 100); print("BY EXIT REASON (worst first)"); print("=" * 100)
    g = collections.defaultdict(list)
    for r in T: g[r['reason']].append(r)
    for k, v in sorted(g.items(), key=lambda kv: sum(r['pnl'] for r in kv[1])):
        line(k, v)

    print("\n" + "=" * 100); print("SIZE vs OUTCOME"); print("=" * 100)
    V = sorted([r for r in T if r['N'] and 0 < r['N'] < 3000], key=lambda r: r['N'])
    q = len(V) // 4
    print(f"  {'bucket':14} {'n':>3} {'notional':>9} {'win%':>6} {'avg WIN':>9} {'avg LOSS':>9} {'net':>9}")
    for i, nm in enumerate(('smallest 25%', '2nd', '3rd', 'largest 25%')):
        ch = V[i*q:(i+1)*q] if i < 3 else V[3*q:]
        if not ch: continue
        n, w, l, net, aw, al, _ = stats(ch)
        print(f"  {nm:14} {n:3} ${st.median([r['N'] for r in ch]):8.1f} {100*w/n:5.1f}% "
              f"${aw:+8.3f} ${al:+8.3f} ${net:+8.2f}")

    print("\n" + "=" * 100)
    print("DID THE SIZING HELP OR HURT?  (permutation test, artefact-controlled)")
    print("=" * 100)
    print(f"  {'filter':16} {'n':>4} {'actual':>9} {'random mean':>13} {'p':>8}")
    for lo in (0.0, 0.5, 1.0, 1.5, 2.0):
        res = permutation([r for r in T if abs(r['move']) >= lo])
        if not res:
            print(f"  |move|>={lo:.1f}%     too few trades"); continue
        n, act, rnd, p = res
        print(f"  |move| >= {lo:.1f}%   {n:4} ${act:+8.2f} ${rnd:+12.2f} {p:8.4f}")
    print("\n  p = share of RANDOM size-to-trade pairings at least as bad as the bot's own.")

    print("\n" + "=" * 100); print("THE MODEL-FREE LINE (no derived size at all)"); print("=" * 100)
    V2 = [r for r in T if r['N'] and 0 < r['N'] < 3000]
    sm = sum(r['move'] for r in V2)
    print(f"  sum of raw % moves over {len(V2)} trades : {sm:+.2f}%")
    print(f"  fees at {FEE*100:.2f}% round trip            : {-len(V2)*FEE*100:+.2f}%")
    print(f"  any EQUAL-sized book earns            : {sm - len(V2)*FEE*100:+.2f}% of one position")
    print(f"  the bot actually made                 : ${sum(r['pnl'] for r in V2):+.2f}")
    med = st.median([r['N'] for r in V2])
    print(f"\n  same trades at the median ${med:.0f}        : "
          f"${sum(med*(r['move']/100-FEE) for r in V2):+.2f}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))

# NOTE (C481): the size-vs-outcome section above derives notional from pnl and
# move. That derivation is NOT safe to test against the outcome -- see Standing
# Rule 40. Use the detail log's real `Margin:` and `x<lev>` figures instead;
# omega_entry_forensics.py does that. The permutation test here is retained only
# to show how the artefact looks, and its p-value means nothing.
