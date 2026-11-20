#!/usr/bin/env python3
"""C549 (1 Nov 2026): G6(b)'s three tax readings re-computed on today's 63-coin list, before and after C549.

    C524_MARK=1 python3 research/c549_tax_readings.py XV_CACHE

The written opinion (reports/2026-10-09_tax_opinion.md) quoted +3.71% / +0.23% / -2.95% a month after tax (costs x5)
from Round 22's engine on 9 Oct's 71 coins, before Round 24's one-way cap. Round 22b's `legs_ab` (both legs apart)
has no cap, so all three readings are given here WITHOUT the cap, on the same 63 coins, both ways; Round 23's capped
engine gives the first two WITH the cap (research/c549_hourly_check.txt). Descriptive only.
"""
import os, sys, io, json, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c524_xvenue as X
import c542_pairs as P
import c542b_pairs as B
import c531_split_600 as S


def main(cache):
    coins = set(json.load(open(os.path.join(HERE, 'r23_round23.json')))['coins'])
    with contextlib.redirect_stdout(io.StringIO()):
        prods, res = X.load(cache)
    cv = S.delta_cv()
    out = {}
    for flag in (False, True):
        X.C549_HOURLY = flag
        allm = X.matrices(prods, res, shift00=True, mark=True)
        row = {}
        for cm in (5.0, 1.0):
            a = B.run(allm, cv, coins, P.COST['coindcx'], cost_mult=cm)
            b = B.run(allm, cv, coins, P.COST['coindcx'], cost_mult=cm, both_vda=True)
            row[cm] = dict(t1=a['after1'], t2=a['after2'], both=b['after2'], pre=a['avg'])
        out['with C549' if flag else 'before C549'] = row
    X.C549_HOURLY = True
    print("G6(b)'s TAX READINGS, today's 63 coins, 10 pairs x 10%, NO one-way cap (Round 22b's engine), after tax a month")
    print(f"  {'':52} {'before C549':>18} {'with C549':>18}")
    for k, nm in (('pre', 'before tax'), ('t1', 'business income, both legs netted (the opinion)'),
                  ('t2', 'the CoinDCX leg alone a VDA'), ('both', 'both legs VDAs')):
        f = lambda r: f"{100 * r[5.0][k]:+.2f}% ({100 * r[1.0][k]:+.2f}%)"
        print(f"  {nm:52} {f(out['before C549']):>18} {f(out['with C549']):>18}")
    print("  (costs x5; in brackets costs x1)")
    json.dump(out, open(os.path.join(HERE, 'c549_tax_readings.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main(sys.argv[1])
