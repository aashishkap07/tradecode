#!/usr/bin/env python3
# C491 side finding: Binance listed stock/commodity perps in 2026 and the C488 research universe counted them as crypto.
# usage: python3 research/c488_tradfi_check.py DATA_DIR   (holds bnc/)
import sys, datetime as dt, numpy as np
sys.path.insert(0, '/home/user/tradecode/research')
import omega_c488_research as R488
SP = sys.argv[1]
TRADFI = set((s + 'USDT') for s in "AAPL ADBE AMD AMZN ARM AVGO BABA BZ CL COIN COPPER CRCL CRM CRWV DIS DRAM EWY GME GOOGL HOOD IBM INTC IREN IWM JPM KORU KO MARA META MSFT MSTR MU MUU NATGAS NFLX NVDA ORCL PLTR QCOM QQQ RIVN SAMSUNG SKDD SKHYNIX SKHY SMCI SNDK SNXX SOXL SOXS SPCX SPY TQQQ TSLA TSM TXN UBER V WMT XAUT XPD XPT".split())
def book(excl):
    R488.EXCLUDE = set(R488.EXCLUDE) | excl
    Td, dsyms, dclose, dqv, dfund = R488.load_crypto(SP + '/bnc')
    R488.TOPN = 20
    rr, Wd, _ = R488.crypto_sleeves(Td, dclose, dqv, dfund)
    Wc = R488.combine({k: Wd[k] for k in ('C1', 'C2', 'C3')}, rr, dfund, 1)
    p = R488.pnl(Wc, rr, dfund, 1)[0]
    el = R488.universe(dclose, dqv)
    tf = [j for j, s in enumerate(dsyms) if s in TRADFI]
    days_tf = int(el[:, tf].any(1).sum()) if tf else 0
    return Td, p, days_tf
T0, p0, d0 = book(set())
T1, p1, d1 = book(TRADFI)
assert np.array_equal(T0, T1)
print('days a TradFi perp was in the top 20:', d0)
for lab, a, b in (('2020-01..2026-08', int(dt.datetime(2020,1,1).timestamp()*1000), T0[-1] + 1),
                  ('2021-07..2026-08', int(dt.datetime(2021,7,1).timestamp()*1000), T0[-1] + 1),
                  ('2026 only', int(dt.datetime(2026,1,1).timestamp()*1000), T0[-1] + 1)):
    m = (T0 >= a) & (T0 < b)
    s0 = R488.stats(p0[m], T0[m]); s1 = R488.stats(p1[m], T0[m])
    print(f"{lab:18s} as researched: {100*s0['ann']:+.1f}%/yr t {s0['t']:+.2f}   crypto only: {100*s1['ann']:+.1f}%/yr t {s1['t']:+.2f}")
