#!/usr/bin/env python3
"""C508 (research/c508_preregistration.md): I1, an Indian ETF trend pot through
Groww, long or flat, monthly, with Groww's real per-order costs on Rs 8,800.

    python3 research/omega_c508_research.py [--out results.json] [--eq RUPEES]

Data: Yahoo Finance daily adjusted closes (public; fetched live).
"""
import os, sys, json, math, datetime as dt, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R

NAMES = ['NIFTYBEES', 'JUNIORBEES', 'BANKBEES', 'GOLDBEES', 'MON100']
EQ0, CASH = 8800.0, 0.06
# descriptive only (not the pre-registered test): the same rule on a larger pot,
# to show how much of the result is the fixed per-order costs
if '--eq' in sys.argv:
    EQ0 = float(sys.argv[sys.argv.index('--eq') + 1])
HOLD = dt.date(2025, 1, 1)


def fetch(sym):
    u = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}.NS?range=10y&interval=1d'
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(req, timeout=40))['chart']['result'][0]
    ts = d['timestamp']
    adj = (d['indicators'].get('adjclose') or [{}])[0].get('adjclose') or d['indicators']['quote'][0]['close']
    return {dt.datetime.utcfromtimestamp(t).date(): v for t, v in zip(ts, adj) if v}


data = {n: fetch(n) for n in NAMES}
days = sorted(set().union(*[set(v) for v in data.values()]))
px = np.full((len(days), len(NAMES)), np.nan)
for j, n in enumerate(NAMES):
    last = np.nan
    for i, d in enumerate(days):
        v = data[n].get(d)
        last = v if v else last
        px[i, j] = last
r = np.zeros_like(px); r[1:] = px[1:] / px[:-1] - 1
r = np.nan_to_num(r)
art = np.abs(r) > 0.40
r[art] = 0.0
# the pre-registered rule: an artefact day's return is 0 -- EVERY use of prices
# (signals, volatility, benchmarks) reads this cleaned index, not Yahoo's raw
# closes, which carry unadjusted unit splits (e.g. GOLDBEES)
raw_px = px
px = np.where(np.isnan(raw_px), np.nan, np.cumprod(1 + r, axis=0))
n = len(days)
first_ok = [next(i for i in range(n) if not np.isnan(px[i, j])) for j in range(len(NAMES))]
print("=" * 110)
print(f"C508 I1 INDIAN ETF TREND POT (Groww costs, Rs {EQ0:,.0f}) | {days[0]} .. {days[-1]} | "
      f"first data: " + ", ".join(f"{NAMES[j]} {days[first_ok[j]]}" for j in range(len(NAMES))) +
      f" | artefact days zeroed: {int(art.sum())}")
print("=" * 110)
# signal on month-end days
lag = {L: np.full_like(px, np.nan) for L in (21, 63, 126, 252)}
for L in lag:
    lag[L][L:] = px[L:] / px[:-L] - 1
score = sum(np.sign(np.nan_to_num(lag[L])) for L in lag) / 4.0
sd60 = np.full_like(px, np.nan)
for i in range(60, n):
    sd60[i] = r[i - 59:i + 1].std(axis=0)
sc = np.clip(0.012 / np.where(sd60 > 0, sd60, np.nan), 0, 1.0); sc = np.nan_to_num(sc)
month_end = [i for i in range(n - 1) if days[i + 1].month != days[i].month]
W1 = np.zeros_like(px); cur = np.zeros(len(NAMES))
for i in range(n):
    if i in set(month_end) and i >= 252:
        valid = ~np.isnan(px[i]) & (np.arange(len(NAMES)) >= 0)
        cur = np.where(valid & (i - np.array(first_ok) >= 252), np.maximum(score[i], 0) * sc[i] / len(NAMES), 0.0)
    W1[i] = cur
u = np.zeros(n); u[1:] = (W1[:-1] * r[1:]).sum(1)
L = np.zeros(n)
for i in range(126 + 252, n):
    v = u[i - 126:i].std() * math.sqrt(252)
    L[i] = 0.12 / v if v > 0 else 0.0
# simulate rupees, trading on the day after a decision
hold = np.zeros(len(NAMES)); cash = EQ0; eq_hist = []; trades = 0; cost_total = 0.0
start = next(i for i in range(n) if L[i] > 0)
def buy_cost(v): return max(5.0, min(20.0, 0.001 * v)) * 1.18 + v * (0.00015 + 0.00003 + 0.0005)
def sell_cost(v): return max(5.0, min(20.0, 0.001 * v)) * 1.18 + (23.6 if v >= 100 else 0.0) + v * (0.00001 + 0.00003 + 0.0005)
for i in range(start, n):
    if i > start:
        hold = hold * (1 + r[i])
        cash *= 1 + CASH * (days[i] - days[i - 1]).days / 365.0
    eqv = cash + hold.sum()
    if i - 1 in set(month_end) and i - 1 >= start - 1:
        w = W1[i - 1] * L[i - 1]
        g = w.sum()
        if g > 1:
            w = w / g
        tgt = w * eqv
        for j in range(len(NAMES)):
            want = tgt[j] if tgt[j] >= 1000 else 0.0
            diff = want - hold[j]
            if want == 0.0 and hold[j] > 0:
                c = sell_cost(hold[j]); cash += hold[j] - c; cost_total += c; hold[j] = 0.0; trades += 1
            elif abs(diff) > 0.3 * want and abs(diff) >= 500:
                if diff > 0:
                    c = buy_cost(diff)
                    if cash >= diff + c:
                        cash -= diff + c; hold[j] += diff; cost_total += c; trades += 1
                else:
                    c = sell_cost(-diff); cash += -diff - c; hold[j] += diff; cost_total += c; trades += 1
    eq_hist.append(cash + hold.sum())
eqs = np.array(eq_hist); D = days[start:]
x = np.zeros(len(eqs)); x[1:] = eqs[1:] / eqs[:-1] - 1
cash_d = np.array([0.0] + [CASH * (D[k] - D[k - 1]).days / 365.0 for k in range(1, len(D))])
ex = (x - cash_d)[1:]
t = R.nw_t(ex); q = int(sum(v.mean() > 0 for v in np.array_split(ex, 4)))
hold_ex = ex[np.array([d >= HOLD for d in D[1:]])].mean()
dd = float((1 - eqs / np.maximum.accumulate(eqs)).max())
yrs = (D[-1] - D[0]).days / 365.25
cagr = (eqs[-1] / eqs[0]) ** (1 / yrs) - 1
mo = {}
for d, v in zip(D, eqs):
    mo[(d.year, d.month)] = v
mk = sorted(mo); mv = np.array([mo[mk[k]] / mo[mk[k - 1]] - 1 for k in range(1, len(mk))])
adm = bool(t >= 2.0 and q >= 3 and hold_ex > 0 and dd <= 0.25)
print(f"  I1: Rs {eqs[0]:,.0f} -> Rs {eqs[-1]:,.0f} over {yrs:.1f} years ({D[0]} .. {D[-1]}): CAGR {100*cagr:+.1f}%/yr "
      f"= {100*((1+cagr)**(1/12)-1):+.2f}%/month | max DD {100*dd:.1f}%")
print(f"      excess over 6% cash: NW t {t:+.2f}, quarters+ {q}/4, holdout 2025-26 {100*hold_ex*252:+.1f}%/yr -> "
      f"{'ADMIT' if adm else 'not admitted'}")
print(f"      trades {trades} ({trades/yrs:.1f}/yr), costs Rs {cost_total:,.0f} ({100*cost_total/EQ0/yrs:.2f}% of the start a year) | "
      f"months >= +2%: {100*np.mean(mv>=0.02):.0f}%, positive {100*np.mean(mv>0):.0f}%, worst {100*mv.min():+.1f}%, best {100*mv.max():+.1f}%")
ybr = {}
for d, v in zip(D, eqs):
    ybr.setdefault(d.year, [v, v]); ybr[d.year][1] = v
print("      by year: " + "  ".join(f"{y} {100*(b/a-1):+.0f}%" for y, (a, b) in sorted(ybr.items())))
# benchmarks over the same days
i0 = start
nb = px[i0:, 0] / px[i0, 0]
g = np.nan_to_num(px[i0:, 3] / px[i0, 3], nan=1.0)
mix = 0.5 * nb + 0.5 * g
for lab, s_ in (('buy-and-hold Nifty 50 (NIFTYBEES)', nb), ('50/50 Nifty + gold, buy-and-hold', mix)):
    c_ = s_[-1] ** (1 / yrs) - 1; d_ = float((1 - s_ / np.maximum.accumulate(s_)).max())
    print(f"  {lab:36} CAGR {100*c_:+.1f}%/yr = {100*((1+c_)**(1/12)-1):+.2f}%/month, max DD {100*d_:.1f}%")
res = dict(cagr=float(cagr), maxdd=dd, t=float(t), quarters=q, holdout_excess=float(hold_ex * 252), admit=adm,
           trades_per_year=trades / yrs, cost_pct_year=float(cost_total / EQ0 / yrs), p_month_ge2=float(np.mean(mv >= 0.02)),
           worst_month=float(mv.min()), years={str(y): float(b / a - 1) for y, (a, b) in ybr.items()})
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
