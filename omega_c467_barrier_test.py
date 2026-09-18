#!/usr/bin/env python3
"""C467-B: tabulate the dynamic day barrier across regimes, and prove its bounds.

A barrier that can move must be shown to move the RIGHT way, by a BOUNDED
amount, and never past its own mandate. Anything less is a dial, not a control.
"""
import ast, io, os, re, sys, time, types, datetime

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
src = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

# lift the four C467-B methods onto a stub bot
ns = {'time': time, 'logger': types.SimpleNamespace(info=lambda *a, **k: None,
                                                    warning=lambda *a, **k: None)}
body = []
for fn in ('_c467_note_stop', '_c467_vol_roll', '_c467_day_realised',
           '_c467_day_barrier', '_c467_month_note'):
    m = re.search(rf'^    def {fn}\(self.*?(?=\n    def )', src, re.M | re.S)
    assert m, fn
    body.append(m.group(0))
code = "class Bot:\n" + "\n".join(body)
exec(compile(ast.parse(code), 'c467b', 'exec'), ns)
Bot = ns['Bot']

class Cfg:
    DAY_RISK_CAP_PCT = 0.15 / 22 / 100 * 100      # 15% declared DD -> 0.682%/day
    C380_MAX_MONTHLY_DD_PCT = 15.0
    C467_DYN_BARRIER = True
    C467_BARRIER_VOL_LO = 0.70; C467_BARRIER_VOL_HI = 1.50
    C467_BARRIER_TRUST_LO = 0.60; C467_BARRIER_TRUST_HI = 1.25
    C467_BARRIER_TRUST_N = 8
    C467_BARRIER_REALISED = True
    C467_BARRIER_VOL_HALFLIFE_H = 24.0
Cfg.DAY_RISK_CAP_PCT = 0.15 / 22        # 15%/22 days, as a fraction = 0.00682

def mkbot(vol_ratio=1.0, payoff=0.78, n=20, wr=0.44, cash=250.0, day0=250.0,
          month_dd=0.0, month_days=1.0):
    b = Bot()
    b.cfg = Cfg()
    b.portfolio = types.SimpleNamespace(equity=cash)
    b.mode_mgr = types.SimpleNamespace(_day_start_equity=day0)
    b._c467_vol_state = {'ratio': vol_ratio, 'base': 2.0, 'med': 2.0 * vol_ratio,
                         'last': time.time(), 'n': 5}
    b._c463_realised_payoff = lambda: (payoff, n)
    b._c420_base_rate = lambda: wr
    b._c467_month = {'key': 'x', 'dd_usd': month_dd, 'days': month_days,
                     'eq0': 250.0, 'day': 1}
    return b

base = 250.0 * Cfg.DAY_RISK_CAP_PCT
print(f"\nDeclared monthly drawdown 15% -> base day allowance ${base:.2f} "
      f"({Cfg.DAY_RISK_CAP_PCT*100:.3f}% of $250)\n")

print("1. THE MARKET TERM (bot record held neutral)")
print(f"   {'vol ratio':>10} {'clamped':>8} {'limit $':>9} {'vs base':>8}")
lims = []
for vr in (0.30, 0.50, 0.70, 0.85, 1.00, 1.20, 1.50, 2.00, 4.00):
    b = mkbot(vol_ratio=vr, payoff=1.0, n=20, wr=0.50)   # trust ~= 1.00
    r = b._c467_day_barrier()
    lims.append(r['limit'])
    print(f"   {vr:>10.2f} {r['vol']:>8.2f} {r['limit']:>9.3f} {r['limit']/base:>7.2f}x")
ok("calm tape tightens the barrier", lims[0] < base * 0.75)
ok("wild tape widens it", lims[-1] > base * 1.4)
ok("both ends are CLAMPED (no runaway)",
   abs(lims[0] - lims[1]) < 1e-9 and abs(lims[-1] - lims[-2]) < 1e-9,
   "0.30 and 0.50 must agree; 2.00 and 4.00 must agree")
ok("the ratio is monotone", all(lims[i] <= lims[i+1] + 1e-12 for i in range(len(lims)-1)))

print("\n2. THE RECORD TERM (tape held neutral)")
print(f"   {'payoff':>7} {'win rate':>9} {'E real':>8} {'trust':>7} {'limit $':>9}")
tr = []
for pay, wr in ((0.30, 0.35), (0.50, 0.40), (0.78, 0.44), (1.00, 0.50),
                (1.50, 0.50), (2.00, 0.55), (3.00, 0.60)):
    b = mkbot(vol_ratio=1.0, payoff=pay, n=20, wr=wr)
    r = b._c467_day_barrier()
    e = wr * pay - (1 - wr)
    tr.append(r['trust'])
    print(f"   {pay:>7.2f} {wr:>9.2f} {e:>+8.3f} {r['trust']:>7.2f} {r['limit']:>9.3f}")
ok("a losing record tightens trust", tr[0] <= 0.61)
ok("a winning record loosens it, bounded", 1.0 < tr[-1] <= 1.25)
ok("trust is monotone in realised expectancy",
   all(tr[i] <= tr[i+1] + 1e-12 for i in range(len(tr)-1)))

print("\n3. TOO FEW CLOSES -> TRUST MUST NOT MOVE AT ALL")
for n in (0, 3, 7, 8, 20):
    b = mkbot(vol_ratio=1.0, payoff=3.0, n=n, wr=0.60)
    r = b._c467_day_barrier()
    print(f"   n={n:<3} trust {r['trust']:.2f}")
    if n < Cfg.C467_BARRIER_TRUST_N:
        ok(f"  n={n} leaves trust at exactly 1.00", abs(r['trust'] - 1.0) < 1e-9)
ok("n=8 is where trust is allowed to move",
   abs(mkbot(payoff=3.0, n=8, wr=0.60)._c467_day_barrier()['trust'] - 1.0) > 1e-9)

print("\n4. THE MONTH GUARD")
b = mkbot(vol_ratio=2.0, payoff=3.0, n=20, wr=0.60, month_dd=0.0, month_days=1.0)
free = b._c467_day_barrier()
b2 = mkbot(vol_ratio=2.0, payoff=3.0, n=20, wr=0.60, month_dd=40.0, month_days=10.0)
gd = b2._c467_day_barrier()
print(f"   month-to-date drawdown $0  -> limit ${free['limit']:.3f} (widened)")
print(f"   month-to-date drawdown $40 -> limit ${gd['limit']:.3f} ({gd['capped'] or 'not capped'})")
ok("the guard bites when the month is spent", gd['limit'] <= base + 1e-9)
ok("the guard names itself", gd['capped'] == 'month')
ok("and does NOT bite when the month is healthy", free['limit'] > base)

print("\n5. LOSS SIDE ONLY, REALISED ONLY")
win = mkbot(cash=253.0, day0=250.0)._c467_day_barrier()
lose = mkbot(cash=248.5, day0=250.0)._c467_day_barrier()
print(f"   day +$3.00 realised -> used ${win['used']:.2f}  ({100*win['frac']:.0f}% of barrier)")
print(f"   day -$1.50 realised -> used ${lose['used']:.2f}  ({100*lose['frac']:.0f}% of barrier)")
ok("a WINNING day spends nothing", win['used'] == 0.0 and win['frac'] == 0.0)
ok("a losing day spends exactly its realised loss", abs(lose['used'] - 1.5) < 1e-9)
ok("  ...the OLD symmetric rule would have read the winner at 176% used",
   abs(3.0 / base * 100 - 176) < 5, f"old: {3.0/base*100:.0f}%")

print("\n6. ABSOLUTE FLOOR: the barrier can never reach zero")
worst = mkbot(vol_ratio=0.01, payoff=0.0, n=99, wr=0.01)._c467_day_barrier()
print(f"   worst case anywhere: ${worst['limit']:.3f} = {worst['limit']/base:.2f}x base")
ok("worst case is still a real, positive allowance",
   worst['limit'] >= base * 0.70 * 0.60 - 1e-9 and worst['limit'] > 0,
   f"floor is vol_lo x trust_lo = {0.70*0.60:.2f}x base")

print("\n7. THE VOLATILITY ESTIMATOR")
b = Bot(); b.cfg = Cfg()
for v in [2.0] * 30:
    b._c467_note_stop(v)
b._c467_vol_roll()
s1 = dict(b._c467_vol_state)
print(f"   first roll seeds base at itself -> ratio {s1.get('ratio', 1.0):.3f}")
ok("first reading opens at exactly 1.00", abs(s1.get('ratio', 1.0) - 1.0) < 1e-9)
for v in [4.0] * 30:
    b._c467_note_stop(v)
b._c467_vol_state['last'] = time.time() - 3600 * 24     # one half-life later
b._c467_vol_roll()
print(f"   tape doubles, one half-life later -> ratio {b._c467_vol_state['ratio']:.3f}")
ok("a doubled tape is SEEN", b._c467_vol_state['ratio'] > 1.2)
ok("but the baseline has also moved (it is an EWMA, not a latch)",
   b._c467_vol_state['base'] > 2.0)
b._c467_note_stop(3.0); b._c467_vol_roll()
ok("a scan with too few readings is ignored, not averaged in",
   b._c467_vol_state['ratio'] > 1.2)

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
