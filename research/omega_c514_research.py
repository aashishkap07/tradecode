#!/usr/bin/env python3
"""C514 round 12 (research/c514_preregistration.md): is there a point where a
winning position is more likely to lose from here, and do exits built on it
beat holding?

Part A measures, on every held coin-day of the N2+N3 book (dial 20%), the
chance that the position loses over the next day, the next 7 days and the rest
of its episode, bucketed by its open profit in its own volatility units (z) and
by its 7-day stretch (u). Part B tests five exits (X1/X2 take profit at z > 2 /
3, X3 scale out at z > 2, S1 stop at z < -2, S2 3-sd trailing stop) against the
pre-registered bars.

    python3 research/omega_c514_research.py BNC_DIR [--out results.json]
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
EQ, FLOOR = 250.0, 6.0
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
rng = np.random.default_rng(514)

T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
N = R.TOPN; n, k = close.shape
sc0 = np.nan_to_num(R.vol_scale(sd))
lc = np.log(close)


def fsum(kk):
    f = np.full_like(fund, np.nan)
    for i in range(kk, len(fund)):
        f[i] = fund[i - kk + 1:i + 1].sum(axis=0)
    f[np.isnan(close)] = np.nan
    return f


f7 = fsum(7)
# the N2+N3 C2 rank, exactly as research/omega_c510_research.py
mkt = np.nan_to_num(np.nanmean(np.where(elig, r, np.nan), axis=1))
beta = np.ones_like(close)
for i in range(60, n):
    m = mkt[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r[i - 59:i + 1]; ok = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm; b[ok.sum(0) < 40] = np.nan
    beta[i] = np.where(np.isnan(b), 1.0, b)
m14 = np.full(n, np.nan)
for i in range(14, n):
    m14[i] = np.prod(1 + mkt[i - 13:i + 1]) - 1
s_n3 = R.xs_rank(R.lagret(close, 14) - beta * m14[:, None], elig)
s_n23 = np.where((s_n3 < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s_n3)


def sleeves(sc, c2rank):
    tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
    return {'C1': R.banded(np.where(elig, tr * sc / N, 0.0)),
            'C2': R.weekly(c2rank * sc / (2 * N * 0.2), T),
            'C3': R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)}


PARTS = sleeves(sc0, s_n23)


def base_weights(dial):
    W = R.combine(PARTS, r, fund, 1, target_vol=dial * 4.0 / 3.0 / 100.0)
    return np.where(np.abs(W) * EQ >= FLOOR, W, 0.0)


def episodes(W):
    """per coin: a list of (side, first day e, last day L) runs of one nonzero side"""
    out = []
    S = np.sign(W)
    for j in range(k):
        s = S[:, j]; i = 0
        while i < n:
            if s[i] == 0:
                i += 1
                continue
            e = i
            while i + 1 < n and s[i + 1] == s[e]:
                i += 1
            out.append((j, int(s[e]), e, i))
            i += 1
    return out


def zval(j, side, e, t):
    if t <= e or not (sd[t, j] > 0) or np.isnan(lc[t, j]) or np.isnan(lc[e, j]):
        return np.nan
    return side * (lc[t, j] - lc[e, j]) / (sd[t, j] * math.sqrt(t - e))


def apply_exit(W, EP, rule):
    """the rule on the base's weights: decided at close t, acting from day t+1"""
    Wx = W.copy()
    for j, side, e, L in EP:
        best = lc[e, j]
        for t in range(e, L + 1):
            if not np.isnan(lc[t, j]):
                best = max(best, lc[t, j]) if side > 0 else min(best, lc[t, j])
            fire = False
            if rule in ('X1', 'X2', 'X3', 'S1'):
                z = zval(j, side, e, t)
                if not np.isnan(z):
                    fire = (z > 2 if rule in ('X1', 'X3') else z > 3 if rule == 'X2' else z < -2)
            elif rule == 'S2' and sd[t, j] > 0 and not np.isnan(lc[t, j]):
                fire = side * (lc[t, j] - best) <= -3.0 * sd[t, j]
            if fire:
                if rule == 'X3':
                    Wx[t:L + 1, j] *= 0.5
                else:
                    Wx[t:L + 1, j] = 0.0
                break
    return Wx


# ── Part A: the measurement ────────────────────────────────────────────────────
W20 = base_weights(20.0)
EP20 = episodes(W20)
EDGES = [-np.inf, -2, -1, 0, 1, 2, 3, np.inf]
LAB = ['z <= -2', '-2 < z <= -1', '-1 < z <= 0', '0 < z <= 1', '1 < z <= 2', '2 < z <= 3', 'z > 3']
rowsz, rowsu = [], []
for j, side, e, L in EP20:
    end = min(L + 1, n - 1)
    for t in range(e + 1, L + 1):
        z = zval(j, side, e, t)
        if np.isnan(z) or t + 1 >= n or np.isnan(lc[t + 1, j]):
            continue
        f1 = side * (lc[t + 1, j] - lc[t, j])
        f7_ = side * (lc[t + 7, j] - lc[t, j]) if t + 7 < n and not np.isnan(lc[t + 7, j]) else np.nan
        rest = side * (lc[end, j] - lc[t, j]) if not np.isnan(lc[end, j]) else np.nan
        u = (side * (lc[t, j] - lc[t - 7, j]) / (sd[t, j] * math.sqrt(7))
             if t >= 7 and not np.isnan(lc[t - 7, j]) and sd[t, j] > 0 else np.nan)
        rowsz.append((z, f1, f7_, rest, T[t]))
        rowsu.append((u, f1, f7_, rest, T[t]))
Az = np.array(rowsz); Au = np.array(rowsu)


def table(A, name):
    out = []
    print(f"\n  by {name}: coin-days | P(loss) next day / next 7 days / rest of the trade | mean return (%) same")
    for a, b, lab in zip(EDGES[:-1], EDGES[1:], LAB):
        sel = (A[:, 0] > a) & (A[:, 0] <= b)
        x = A[sel]
        if len(x) == 0:
            continue
        p = [float(np.mean(x[~np.isnan(x[:, c]), c] < 0)) for c in (1, 2, 3)]
        mu = [float(np.nanmean(x[:, c])) for c in (1, 2, 3)]
        lab2 = lab.replace('z', name[0])
        print(f"  {lab2:15} {len(x):7d} | {100*p[0]:5.1f}%  {100*p[1]:5.1f}%  {100*p[2]:5.1f}% | "
              f"{100*mu[0]:+6.2f}  {100*mu[1]:+6.2f}  {100*mu[2]:+6.2f}")
        out.append(dict(bucket=lab2, n=int(len(x)), p_loss_1d=p[0], p_loss_7d=p[1], p_loss_rest=p[2],
                        mean_1d=mu[0], mean_7d=mu[1], mean_rest=mu[2]))
    return out


print("=" * 118)
print(f"C514 ROUND 12 | the N2+N3 book, crypto top {N}, dial 20%, $6 floor at $250 | "
      f"{dt.datetime.utcfromtimestamp(T[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(T[-1]/1000).date()}")
print("=" * 118)
print(f"\nPART A: {len(EP20)} position episodes, {len(Az)} held coin-days after the entry day "
      f"(median episode {int(np.median([L - e + 1 for _, _, e, L in EP20]))} days)")
res = {'A_z': table(Az, 'z (open profit, own-vol units)'), 'A_u': table(Au, 'u (7-day stretch, own-vol units)')}
cand = [b for b in res['A_z'] + res['A_u'] if b['n'] >= 500 and (b['p_loss_7d'] >= 0.70 or b['p_loss_rest'] >= 0.70)]
worst = max(res['A_z'] + res['A_u'], key=lambda b: max(b['p_loss_7d'], b['p_loss_rest']) if b['n'] >= 500 else 0)
print(f"\n  the highest P(loss) in any bucket with >= 500 coin-days: {worst['bucket']} "
      f"(7 days {100*worst['p_loss_7d']:.1f}%, rest of the trade {100*worst['p_loss_rest']:.1f}%)")
print(f"  a '70% point' (pre-registered: >= 500 coin-days and P >= 70%): {'FOUND' if cand else 'NOT FOUND'}")
res['A_found'] = bool(cand); res['A_worst'] = worst
# descriptive (not a test): each trade, entry close to the close after its last held day, price only
tr_ = np.array([side * (lc[min(L + 1, n - 1), j] - lc[e, j]) for j, side, e, L in EP20
                if not np.isnan(lc[min(L + 1, n - 1), j]) and not np.isnan(lc[e, j])])
srt = np.sort(tr_)[::-1]; top = srt[:max(1, len(srt) // 10)]
wins, losses = tr_[tr_ > 0], tr_[tr_ <= 0]
res['A_trades'] = dict(n=int(len(tr_)), win_rate=float(len(wins) / len(tr_)), avg_win=float(wins.mean()),
                       avg_loss=float(losses.mean()), top10_share=float(top.sum() / tr_.sum()),
                       best=float(srt[0]), worst=float(srt[-1]))
print(f"\n  DESCRIPTIVE, the {len(tr_)} trades (price only): won {100*len(wins)/len(tr_):.0f}% | average win "
      f"{100*wins.mean():+.1f}%, average loss {100*losses.mean():+.1f}% | the best 10% of trades made "
      f"{100*top.sum()/tr_.sum():.0f}% of the net | best {100*srt[0]:+.0f}%, worst {100*srt[-1]:+.0f}% (log)")

# ── Part B: the exits ──────────────────────────────────────────────────────────


def maxdd(x):
    e = np.cumprod(1 + x); return float((1 - e / np.maximum.accumulate(e)).max())


def savings(gross, dial, apr=0.05):
    idle = np.clip(1.0 - gross / 5.0 - dial / 100.0 - 0.05, 0.0, 1.0)
    return idle * apr / 365.0


def boot_years(y, horizon_days=365, reps=10000, block=30):
    nb = int(math.ceil(horizon_days / block)); out = np.empty(reps)
    starts = rng.integers(0, len(y) - block, size=(reps, nb))
    for q in range(reps):
        out[q] = np.prod(1 + np.concatenate([y[a:a + block] for a in starts[q]])[:horizon_days]) - 1
    return out


def run_all(dial, admit):
    W = W20 if dial == 20.0 else base_weights(dial)
    EP = EP20 if dial == 20.0 else episodes(W)
    xb, ib = R.pnl(W, r, fund, 1)
    live = np.nonzero(np.abs(xb) > 0)[0][0]
    TT = T[live:]

    def months(y):
        m = {}
        for t, v in zip(TT, y):
            kk = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[kk] = m.get(kk, 1.0) * (1 + v)
        return np.array([v - 1 for v in m.values()])

    def row(name, x, g):
        y = x[live:]; ys = (x + savings(g, dial))[live:]; mv = months(y); need = 1.02 ** 12 - 1
        pb = float((boot_years(ys) >= need).mean()); ph = float((boot_years(ys - ys.mean() / 3.0) >= need).mean())
        s = R.stats(x, T); mo = float(np.prod(1 + y) ** (365 / len(y) / 12) - 1)
        print(f"  {name:34} {100*mo:+5.2f}%/mo (simple {100*s['ann']:+5.1f}%/yr) Sharpe {s['sharpe']:.2f} maxDD {100*maxdd(y):4.1f}% "
              f"worst month {100*mv.min():+5.1f}% months>=2% {100*(mv>=0.02).mean():3.0f}% gross {g[live:].mean():.2f}x "
              f"| +Savings: year avg>=2%/mo boot {100*pb:3.0f}% haircut {100*ph:3.0f}%")
        return dict(month=mo, ann=s['ann'], sharpe=s['sharpe'], maxdd=maxdd(y), worst_month=float(mv.min()),
                    p_month_ge2=float((mv >= 0.02).mean()), gross=float(g[live:].mean()), p_year_boot=pb, p_year_haircut=ph)

    out = {'base': row('BASE N2+N3 (what runs)', xb, ib['gross_exp'])}
    for rule, words in (('X1', 'X1 take profit at z > 2'), ('X2', 'X2 take profit at z > 3'),
                        ('X3', 'X3 halve at z > 2'), ('S1', 'S1 stop at z < -2'),
                        ('S2', 'S2 trailing stop 3 sd from best')):
        x, info = R.pnl(apply_exit(W, EP, rule), r, fund, 1)
        o = row(words, x, info['gross_exp'])
        d = (x - xb)[live:]; t = R.nw_t(d)
        q = sum(v.mean() > 0 for v in np.array_split(d, 4))
        hold = d[TT >= HOLD].mean()
        o.update(diff_ann=float(d.mean() * 365), t=float(t), quarters=int(q), holdout_ann=float(hold * 365),
                 extra_turnover=float((info['turnover'] - ib['turnover'])[live:].mean() * 365))
        if admit:
            o['admit'] = bool(t >= 2.33 and q >= 3 and hold > 0 and o['maxdd'] <= out['base']['maxdd'] + 0.02)
        print(f"  {'':34} vs base {100*o['diff_ann']:+6.2f}%/yr (simple)  NW t {t:+.2f}  quarters+ {q}/4  "
              f"holdout 2025-26 {100*o['holdout_ann']:+.2f}%/yr  extra turnover {o['extra_turnover']:.1f}x/yr"
              + (f"  -> {'ADMIT' if o['admit'] else 'not admitted'}" if admit else ''))
        out[rule] = o
    return out


print("\nPART B: exits on the N2+N3 book, dial 20% (admission: NW t >= 2.33, >= 3/4 quarters, holdout > 0, DD <= base + 2)")
res['B20'] = run_all(20.0, True)
print("\nDESCRIPTIVE: the same at dial 15%")
res['B15'] = run_all(15.0, False)
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1, default=float)
