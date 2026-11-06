"""C485 bench 1: does the market resultant R predict the next move of the majors?

WHY: the live N31 'tier_model' vote (_compute_skill_components) adds, for
BTC/ETH/SOL/BNB/XRP/DOGE/ADA, +0.20 when R*dir > 0.20 and -0.25 when
R*dir < -0.20.  It runs BEFORE result['direction'] is set, so dir is always
-1 and the vote that reaches the direction mix (avg_sig) is:
    R > +0.20  ->  -0.25   (a SHORT vote in a rising tape)
    R < -0.20  ->  +0.20   (a LONG  vote in a falling tape)
i.e. a contrarian vote on the majors.  The design meant the opposite
(back the majors WITH the tape).  This bench measures which sign, if any,
history supports.

R is rebuilt exactly as the scan builds it (C71/C93/C110): per BTC and ETH,
over the last 50 15m closes, ATR = mean |1-bar return| %, then
    h1  = tanh(0.5 * ret(4 bars)  / max(ATR,    0.1))
    h4  = tanh(0.5 * ret(16 bars) / max(3*ATR,  0.3))
    h12 = tanh(0.5 * ret(48 bars) / max(6*ATR,  0.5))
averaged over BTC and ETH, R = 0.55*h4 + 0.30*h12 + 0.15*h1.
(The C270 equity tilt, bounded to +/-0.10, is not reproducible offline.)

Signal: when |R| > 0.20 take sign(R) as the call on the coin's next H bars.
Score = sign(R) * forward return %.  Positive = continuation (the design);
negative = reversal (what the live bug votes for).  Non-overlapping entries
(stride = H).  t uses day-clustered standard errors.  Four-way split: time (corpusO =
early, corpusL = late) x pairs (A = BTC SOL DOGE, B = ETH XRP ADA).
Fee line: 0.04 % (maker both sides) — what a trade on the call alone must beat.
"""
import os, math, statistics

TIER1 = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA']
PAIRS_A, PAIRS_B = {'BTC', 'SOL', 'DOGE'}, {'ETH', 'XRP', 'ADA'}
FEE = 0.04
THR = 0.20


def load(corpus, sym):
    rows = {}
    for ln in open(os.path.join(corpus, f'{sym}USDT.csv')):
        p = ln.strip().split(',')
        if len(p) < 6:
            continue
        try:
            rows[int(float(p[0]))] = float(p[4])
        except ValueError:
            pass
    return rows


def ref_vec(cl):
    """h1, h4, h12 for one reference coin from its last 50 closes (as live)."""
    rets = [abs(cl[i] - cl[i - 1]) / cl[i - 1] * 100 for i in range(1, len(cl))]
    atr = sum(rets) / len(rets) if rets else 0.5
    h1 = math.tanh(0.5 * ((cl[-1] - cl[-5]) / cl[-5] * 100) / max(atr, 0.1))
    h4 = math.tanh(0.5 * ((cl[-1] - cl[-17]) / cl[-17] * 100) / max(atr * 3, 0.3))
    h12 = math.tanh(0.5 * ((cl[-1] - cl[-49]) / cl[-49] * 100) / max(atr * 6, 0.5))
    return h1, h4, h12


def resultant_series(corpus):
    b, e = load(corpus, 'BTC'), load(corpus, 'ETH')
    ts = sorted(set(b) & set(e))
    bc, ec = [b[t] for t in ts], [e[t] for t in ts]
    R = {}
    for i in range(49, len(ts)):
        v1 = ref_vec(bc[i - 49:i + 1])
        v2 = ref_vec(ec[i - 49:i + 1])
        h1, h4, h12 = [(x + y) / 2 for x, y in zip(v1, v2)]
        R[ts[i]] = 0.55 * h4 + 0.30 * h12 + 0.15 * h1
    return R


def day_t(obs):
    """obs: list of (ts_ms, value). t of the observation mean with standard
    errors clustered by calendar day (overlapping days are not independent)."""
    n = len(obs)
    if n < 3:
        return 0.0, 0
    m = sum(v for _, v in obs) / n
    days = {}
    for t, v in obs:
        d = t // 86_400_000
        days[d] = days.get(d, 0.0) + (v - m)
    var = sum(x * x for x in days.values())
    se = math.sqrt(var) / n
    return (m / se if se > 0 else 0.0), len(days)


def run(H, syms, label_sets, want_R=None):
    """Return per-split list of observations of sign(R)*fwd%."""
    res = {}
    for corpus, tlabel in (('corpusO', 'early'), ('corpusL', 'late')):
        R = resultant_series(corpus)
        for sym in syms:
            px = load(corpus, sym)
            ts = sorted(t for t in px if t in R)
            idx = {t: k for k, t in enumerate(ts)}
            last = -10 ** 9
            for k, t in enumerate(ts):
                if k - last < H or k + H >= len(ts):
                    continue
                r = R[t]
                if abs(r) <= THR:
                    continue
                if want_R is not None and (r > 0) != want_R:
                    continue
                f = (px[ts[k + H]] / px[t] - 1) * 100
                s = 1.0 if r > 0 else -1.0
                grp = next((g for g, members in label_sets.items() if sym in members), None)
                res.setdefault((tlabel, grp), []).append((t, s * f))
                last = k
    return res


def show(title, res):
    allv = [v for obs in res.values() for v in obs]
    if not allv:
        print(f'  {title}: no observations'); return
    m = statistics.mean(v for _, v in allv)
    t, nd = day_t(allv)
    pos = sum(1 for obs in res.values() if obs and statistics.mean(v for _, v in obs) > 0)
    neg = sum(1 for obs in res.values() if obs and statistics.mean(v for _, v in obs) < 0)
    cells = '  '.join(f'{k[0][0]}{k[1]}:{statistics.mean(v for _, v in obs):+.3f}'
                      for k, obs in sorted(res.items()))
    print(f'  {title:<34} n={len(allv):>5} mean {m:+.4f}% t={t:+5.2f} days={nd:>3}'
          f'  cont+ {pos}/4  rev+ {neg}/4   [{cells}]')


if __name__ == '__main__':
    labels = {'A': PAIRS_A, 'B': PAIRS_B}
    print('C485 bench 1 - sign(R) x forward return on the majors, |R| > 0.20')
    print('  positive mean = continuation pays (design intent); negative = reversal pays (live bug)')
    for H in (4, 8, 16):
        print(f'\n H = {H} bars ({H * 15} min)')
        show('tier-1, both R signs', run(H, TIER1, labels))
        show('tier-1, R > +0.20 only', run(H, TIER1, labels, want_R=True))
        show('tier-1, R < -0.20 only', run(H, TIER1, labels, want_R=False))
    # control: the other 26 coins, halves by alphabetical order
    others = sorted(f[:-8] for f in os.listdir('corpusO') if f.endswith('USDT.csv')
                    and f[:-8] not in TIER1 and os.path.exists(os.path.join('corpusL', f)))
    oA, oB = set(others[::2]), set(others[1::2])
    print('\n CONTROL - the non-tier-1 coins (does R carry the same sign for alts?)')
    for H in (4, 8, 16):
        show(f'alts H={H}', run(H, others, {'A': oA, 'B': oB}))
    print(f'\n fee line for a trade on the call alone: {FEE:.2f}% round trip (maker both)')
