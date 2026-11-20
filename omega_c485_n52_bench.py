"""C485 bench 2: the N52 pressure & exhaustion engine, measured before revival.

WHAT WAS FOUND. compute_pressure_exhaustion() has raised UnboundLocalError on
every call since C432-3 put `atr_abs = max(...)` inside the nested _zig():
the assignment makes atr_abs local to _zig, so `thr = atr_abs * rev_mult`
(its first line) reads an unbound name.  The outer `except Exception: pass`
returns the all-default dict, so in production dir = 0, x = 0, next_pct = 0,
vel = 1, decel = False on every pair, every scan.  ~130 lines of the entry
pipeline read those fields.  Every live session on record ran with N52 inert.

WHY MEASURE INSTEAD OF JUST REPAIRING. Repairing the crash switches on, at
once, the leg_exhausted block, the climax veto, the 'fuel low' and 'burning
hot' penalties, the reversal bonus, the C285/C287/C291/C296 releases and every
reader of the next-candle forecast -- including a family ('already-travelled'
entry filters) the project refuted at 158,444 observations (Atlas, C382).
That is the largest entry change in weeks, and nothing ships untested.

The engine is run EXACTLY as the scan runs it -- same function source with the
one crash repaired (floor hoisted, same value), last 100 CLOSED 15m bars,
the same 14-bar true-range ATR floored at 0.05 %.  Four-way split: time
(corpusO early / corpusL late) x pairs (alternating halves of 32).  Entries
non-overlapping per pair (stride = horizon).  t with day-clustered errors.
Outcomes are raw % moves; the fee line is 0.04 % (maker both sides).

TESTS
  F  the next-candle forecast: sign(next_pct) x next move, |next_pct| >= 0.15
  B  leg_exhausted block: with-trend continuation when the leg is spent and
     decelerating (the block) vs when it is fresh (x < 0.6) -- does the block
     remove worse trades?
  C  climax veto: spent x >= 1.8 with the forecast opposing by >= 0.30
  V  the fading-volume leg of the C287 fuel guard, on the C287 release set
"""
import os, sys, io, math, contextlib, importlib.util, inspect, textwrap, tempfile, statistics
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omega_c485_tier1_bench import resultant_series, day_t  # noqa: E402

FEE = 0.04
CACHE = os.path.join(tempfile.gettempdir(), 'omega_c485_n52_cache.npz')
FIELDS = ('ts', 'close', 'dir', 'x', 'dir2', 'x2', 'decel', 'age', 'vel', 'travel',
          'next_pct', 'capsig', 'capstr', 'volr', 'R')


def load_bot():
    spec = importlib.util.spec_from_file_location('omega_bot_c485', 'omega_v60_reconstructed.py')
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(m)
    return m


def engines(bot):
    """(shipped, repaired).  If the shipped source no longer carries the
    in-_zig floor, the defect is fixed and shipped == repaired."""
    shipped = bot.TechnicalAnalysis.compute_pressure_exhaustion
    src = textwrap.dedent(inspect.getsource(shipped))
    bad = ("            atr_abs = max(float(atr_abs or 0.0),\n"
           "                          abs(float(px)) * 1e-4) if px else max(float(atr_abs or 0.0), 1e-12)\n")
    if bad not in src:
        return shipped, shipped
    src = src.replace(bad, '')
    src = src.replace("        seg = c[-96:] if n > 96 else c\n",
                      "        atr_abs = max(float(atr_abs or 0.0), abs(float(px)) * 1e-4)\n"
                      "        seg = c[-96:] if n > 96 else c\n", 1)
    ns = {}
    exec(src, bot.__dict__, ns)
    return shipped, ns['compute_pressure_exhaustion']


def load_ohlcv(corpus, sym):
    rows = []
    for ln in open(os.path.join(corpus, f'{sym}USDT.csv')):
        p = ln.strip().split(',')
        if len(p) < 6:
            continue
        try:
            rows.append([float(x) for x in p[:6]])
        except ValueError:
            pass
    rows.sort(key=lambda r: r[0])
    return np.asarray(rows)


def cap_candle(h, l, c, v):
    """_cap_sig/_cap_str exactly as quick_scan computes them (C119-N16)."""
    sig, st = 0, 0.0
    lh, ll, lc, lo = float(h[-1]), float(l[-1]), float(c[-1]), float(c[-2])
    rng = lh - ll
    av5 = float(np.mean(v[-6:-1]))
    spike = v[-1] > av5 * 1.8 if av5 > 0 else False
    if rng > 0:
        bl, bh = min(lo, lc), max(lo, lc)
        if bl - ll > rng * 0.40 and lc > ll + rng * 0.45:
            sig, st = 1, 0.5 + (0.5 if spike else 0)
        elif lh - bh > rng * 0.40 and lc < ll + rng * 0.55:
            sig, st = -1, 0.5 + (0.5 if spike else 0)
    return sig, st


def build(fn, bot):
    syms = sorted(f[:-8] for f in os.listdir('corpusO') if f.endswith('USDT.csv')
                  and os.path.exists(os.path.join('corpusL', f)))
    data = {}
    for corpus in ('corpusO', 'corpusL'):
        R = resultant_series(corpus)
        for sym in syms:
            a = load_ohlcv(corpus, sym)
            ts, hi, lo, cl, vo = a[:, 0].astype(np.int64), a[:, 2], a[:, 3], a[:, 4], a[:, 5]
            rec = {k: [] for k in FIELDS}
            for i in range(100, len(a)):
                c, h, l, v = cl[i - 99:i + 1], hi[i - 99:i + 1], lo[i - 99:i + 1], vo[i - 99:i + 1]
                tr = [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(-14, 0)]
                atr_pct = float(np.mean(tr)) / max(float(c[-1]), 1e-12) * 100
                o = fn(bot.TechnicalAnalysis, c, h, l, v, max(atr_pct, 0.05))
                sg, st = cap_candle(h, l, c, v)
                vals = (int(ts[i]), float(cl[i]), o['dir'], o['x'], o['dir2'], o['x2'], float(o['decel']),
                        o['age'], o['vel'], o['travel_atr'], o['next_pct'], sg, st,
                        float(np.mean(v[-3:])) / max(float(np.mean(v[-10:-3])), 1),
                        R.get(int(ts[i]), float('nan')))
                for k, x in zip(FIELDS, vals):
                    rec[k].append(x)
            data[(corpus, sym)] = {k: np.asarray(x, dtype=float) for k, x in rec.items()}
        print(f'   built {corpus}', flush=True)
    flat = {f'{c}|{s}|{k}': arr for (c, s), d in data.items() for k, arr in d.items()}
    np.savez_compressed(CACHE, **flat)
    return data


def load_cache():
    z = np.load(CACHE)
    data = {}
    for key in z.files:
        c, s, k = key.split('|')
        data.setdefault((c, s), {})[k] = z[key]
    return data


def collect(data, H, cond, sign):
    """cond(d, i) -> bool, sign(d, i) -> +1/-1 trade direction.  Returns
    {(time, pairhalf): [(ts, signed fwd %)]}, non-overlapping per pair."""
    syms = sorted({s for _, s in data})
    half = {s: ('A' if k % 2 == 0 else 'B') for k, s in enumerate(syms)}
    out = {}
    for (corpus, sym), d in data.items():
        tl = 'early' if corpus == 'corpusO' else 'late'
        cl, n, last = d['close'], len(d['close']), -10 ** 9
        for i in range(n - H):
            if i - last < H or not cond(d, i):
                continue
            s = sign(d, i)
            out.setdefault((tl, half[sym]), []).append((int(d['ts'][i]), s * (cl[i + H] / cl[i] - 1) * 100))
            last = i
    return out


def summary(res):
    allv = [o for obs in res.values() for o in obs]
    if len(allv) < 3:
        return None
    m = statistics.mean(v for _, v in allv)
    t, _ = day_t(allv)
    cells = {k: statistics.mean(v for _, v in obs) for k, obs in res.items() if obs}
    return m, t, len(allv), cells


def line(title, res):
    s = summary(res)
    if not s:
        print(f'   {title:<46} n<3'); return None
    m, t, n, cells = s
    pos = sum(1 for v in cells.values() if v > 0)
    cs = '  '.join(f'{k[0][0]}{k[1]}:{v:+.3f}' for k, v in sorted(cells.items()))
    print(f'   {title:<46} n={n:>6} mean {m:+.4f}% t={t:+5.2f}  +{pos}/4  [{cs}]')
    return s


def compare(title, blocked, kept):
    """Does the gate remove WORSE trades?  kept - blocked per split."""
    sb, sk = summary(blocked), summary(kept)
    if not sb or not sk:
        print(f'   {title}: too few'); return
    helps = sum(1 for k in sk[3] if k in sb[3] and sk[3][k] - sb[3][k] > 0)
    se_b = abs(sb[0] / sb[1]) if sb[1] else float('inf')
    se_k = abs(sk[0] / sk[1]) if sk[1] else float('inf')
    td = (sk[0] - sb[0]) / math.sqrt(se_b ** 2 + se_k ** 2) if math.isfinite(se_b + se_k) else 0.0
    print(f'   => {title}: blocked {sb[0]:+.4f}% (n={sb[2]}) vs kept {sk[0]:+.4f}% (n={sk[2]}), '
          f'kept-minus-blocked {sk[0] - sb[0]:+.4f}  t~{td:+.2f}  gate helps in {helps}/4 splits')


if __name__ == '__main__':
    bot = load_bot()
    shipped, fixed = engines(bot)
    probe = load_ohlcv('corpusO', 'SOL')[4900:5001]
    args = (probe[:, 4], probe[:, 2], probe[:, 3], probe[:, 5], 0.58)
    print('C485 bench 2 - N52 pressure & exhaustion engine')
    _o = fixed(bot.TechnicalAnalysis, *args)
    print(f"   engine on a live SOL window: dir={_o['dir']} x={_o['x']:.2f}"
          + ("   (shipped source still has the C432-3 crash; measuring the repaired copy)"
             if shipped is not fixed else "   (shipped source is repaired)"))
    if os.path.exists(CACHE) and '--rebuild' not in sys.argv:
        data = load_cache()
    else:
        print('   building engine readings for every bar (about 2-3 minutes) ...', flush=True)
        data = build(fixed, bot)

    spent = lambda d, i: (d['dir'][i] != 0 and (d['x'][i] >= 1.0 or (d['dir2'][i] == d['dir'][i] and d['x2'][i] >= 1.2))
                          and d['decel'][i] > 0 and d['age'][i] >= 3)
    fresh = lambda d, i: d['dir'][i] != 0 and d['x'][i] < 0.6
    with_leg = lambda d, i: d['dir'][i]

    print('\n F. NEXT-CANDLE FORECAST: sign(next_pct) x move, |next_pct| >= 0.15 %')
    for H in (1, 4):
        line(f'H={H} bar(s)', collect(data, H, lambda d, i: abs(d['next_pct'][i]) >= 0.15,
                                      lambda d, i: 1 if d['next_pct'][i] > 0 else -1))

    print('\n B. LEG_EXHAUSTED BLOCK: continuation (trade WITH the leg) outcomes')
    for H in (4, 8):
        b = line(f'H={H} spent+decelerating (BLOCKED)', collect(data, H, spent, with_leg))
        k = line(f'H={H} fresh leg x<0.6 (not blocked)', collect(data, H, fresh, with_leg))
        compare(f'H={H} leg_exhausted', collect(data, H, spent, with_leg), collect(data, H, fresh, with_leg))

    print('\n C. CLIMAX VETO: x >= 1.8 on either scale, forecast opposing by >= 0.30 %')
    climax = lambda d, i: (d['dir'][i] != 0 and (d['x'][i] >= 1.8 or d['x2'][i] >= 1.8)
                           and d['next_pct'][i] * d['dir'][i] <= -0.30)
    notclimax = lambda d, i: d['dir'][i] != 0 and d['x'][i] < 1.8 and d['x2'][i] < 1.8
    for H in (4, 8):
        compare(f'H={H} climax veto', collect(data, H, climax, with_leg), collect(data, H, notclimax, with_leg))

    print('\n V. FADING-VOLUME LEG on the C287 release set (other fuel checks pass, forecast and R agree)')
    def release(d, i):
        dd = d['dir'][i]
        return (spent(d, i) and d['next_pct'][i] * dd >= 0.15 and d['R'][i] * dd > 0
                and not (d['capstr'][i] >= 0.5 and d['capsig'][i] == -dd)
                and d['vel'][i] > -0.9 and not (d['travel'][i] > 0.01 and d['travel'][i] >= 6.0))
    for H in (4, 8):
        compare(f'H={H} fading-volume veto',
                collect(data, H, lambda d, i: release(d, i) and d['volr'][i] < 0.9, with_leg),
                collect(data, H, lambda d, i: release(d, i) and d['volr'][i] >= 0.9, with_leg))
    print(f'\n fee line: {FEE:.2f} % round trip (maker both).  cache: {CACHE}')
