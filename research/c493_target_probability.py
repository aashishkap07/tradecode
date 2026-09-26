#!/usr/bin/env python3
"""C493: how often did the C488 book actually make the operator's 2-4% a month?

    python3 research/c493_target_probability.py BNC_DIR

1. Reproduces the published C488 numbers (stock/commodity perps IN, as researched),
   then the crypto-only book the live bot actually trades (Bitget's isRwa filter).
2. For the crypto-only book at dial 10/15/20% (top 40, and top 20 with positions
   under $6 at $250 dropped): compounded monthly growth, the share of rolling
   12-month windows that made >= 2% and >= 3% a month, losing windows, the worst
   window and month, and where the money came from (gross, funding, fees).
"""
import sys, os, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
B = sys.argv[1]
base = set(R.EXCLUDE)

print("1. THE UNIVERSE THAT ACTUALLY TRADES (COMBO-C, top 40, dial 15%)")
for lab, ex in (('as originally researched (stock/commodity perps IN)', base),
                ('crypto only (what the live bot trades)', base | TRADFI)):
    R.EXCLUDE = ex
    T, syms, close, qv, fund = R.load_crypto(B)
    r, W, elig = R.crypto_sleeves(T, close, qv, fund)
    x = R.pnl(R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1), r, fund, 1)[0]
    s = R.stats(x, T)
    print(f"  {lab}: net {100*s['ann']:+.1f}%/yr Sharpe {s['sharpe']:.2f} t {s['t']:.2f} "
          f"maxDD {100*s['maxdd']:.0f}% month {100*s['month_mean']:+.2f}%")
    for L in (365, 730):
        y = x[-L:]
        print(f"      last {L // 365 * 12} months: {100*y.mean()*365:+.1f}%/yr Sharpe "
              f"{y.mean()/y.std()*math.sqrt(365):.2f} month {100*y.mean()*30.4:+.2f}%")

print("\n2. HOW OFTEN THE TARGET WAS MET (crypto only)")
R.EXCLUDE = base | TRADFI
for topn in (40, 20):
    R.TOPN = topn
    T, syms, close, qv, fund = R.load_crypto(B)
    r, W, elig = R.crypto_sleeves(T, close, qv, fund)
    print(f"  top {topn}{' at $250, positions under $6 dropped' if topn == 20 else ''}")
    for dial in (10, 15, 20):
        Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1, target_vol=dial * 4 / 3 / 100)
        if topn == 20:
            Wc = np.where(np.abs(Wc) * 250 >= 6, Wc, 0.0)
        x, d = R.pnl(Wc, r, fund, 1)
        live = np.nonzero(np.abs(x) > 0)[0][0]
        x, TT = x[live:], T[live:]
        eq = np.cumprod(1 + x)
        roll = eq[365:] / eq[:-365] - 1
        mo = (1 + roll) ** (1 / 12) - 1
        months = {}
        for t, v in zip(TT, x):
            k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m')
            months[k] = months.get(k, 1.0) * (1 + v)
        mv = np.array(list(months.values())) - 1
        cagr = eq[-1] ** (365 / len(x)) - 1
        print(f"    dial {dial:2}%: CAGR {100*cagr:+5.1f}%/yr = {100*((1+cagr)**(1/12)-1):+.2f}%/month | 12-month windows "
              f">=2%/mo {100*(mo>=0.02).mean():3.0f}%, >=3%/mo {100*(mo>=0.03).mean():3.0f}%, losing {100*(roll<0).mean():3.0f}%, "
              f"worst {100*roll.min():+.0f}% | months up {100*(mv>0).mean():.0f}%, worst month {100*mv.min():+.1f}% | "
              f"gross {100*d['gross'][live:].mean()*365:+.1f} funding {100*d['funding'][live:].mean()*365:+.1f} "
              f"fees {100*d['cost'][live:].mean()*365:.1f} %/yr")
