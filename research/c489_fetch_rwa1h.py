#!/usr/bin/env python3
"""C489 exploratory data: Bitget RWA perps (metals, energy, indices, US stocks), 1-hour, ~400 days."""
import sys, json, time, os; sys.path.insert(0, '/home/user/tradecode')
import omega_live_forensics as lf
SYMS = "XAUUSDT XAGUSDT COPPERUSDT XPTUSDT XPDUSDT CLUSDT BZUSDT NATGASUSDT SP500USDT NDX100USDT TSLAUSDT NVDAUSDT AAPLUSDT MSFTUSDT AMZNUSDT METAUSDT GOOGLUSDT COINUSDT MSTRUSDT AMDUSDT PLTRUSDT HOODUSDT QQQUSDT SPYUSDT".split()
t1 = int(time.time() * 1000)
for s in SYMS:
    p = f'rwa1h/{s}.json'
    if os.path.exists(p): continue
    r = lf.candles(s, t1 - 400 * 86400000, t1, gran='1H')
    json.dump(r, open(p, 'w')); print(s, len(r), flush=True)
print('DONE')
