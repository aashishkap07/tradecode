#!/usr/bin/env python3
"""C482-A: a split trade must be RECORDED as the whole idea, and PAID as the
remainder.

The win partial banks half the position's cash at once. The final close then
books the remainder's cash, and C397-4 computed the whole idea -- but handed it
to ONE consumer. Every record below kept reading the remainder alone, so 18 of
25 winners in the 20-23 Sep session were recorded at exactly half, and the
session table read -$3.92 while equity made +$4.10.

This lifts the real block out of the shipped close path and runs it.
Rule 16: section 4 runs the pre-C482 block and requires it to be wrong.
"""
import ast, io, sys, types, textwrap

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
raw = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

START = "            _whole397 = net_pnl + float(getattr(pos, '_partial_booked_pnl', 0.0) or 0.0)\n"
END   = "            self.portfolio.positions.remove(symbol)\n"

def lift(text):
    a = text.index(START); b = text.index(END, a)
    return textwrap.dedent(text[a:b])

def run(block, banked, bfees, orig_margin, net, gross, fees, pnl_pct):
    booked = {}
    class PF:
        def release_margin(self, margin, net_pnl, fees, classify_pnl=None, count_trade=True):
            booked.update(margin=margin, cash=net_pnl, fees=fees, classify=classify_pnl)
    pos = types.SimpleNamespace(initial_margin=10.0, _partial_booked_pnl=banked,
                                _partial_booked_fees=bfees, _c482_orig_margin=orig_margin)
    self_ = types.SimpleNamespace(portfolio=PF())
    lg = types.SimpleNamespace(info=lambda *a: None, warning=lambda *a: None)
    ns = dict(pos=pos, self=self_, net_pnl=net, gross_pnl=gross, total_fees=fees,
              pnl_pct=pnl_pct, logger=lg)
    exec(compile(block, '<c482>', 'exec'), ns)
    return ns, booked

print("=" * 62); print("C482-A: RECORD THE WHOLE IDEA, PAY THE REMAINDER"); print("=" * 62)
NEW = lift(raw)

print("\n1. THE REAL CASE: JUP, banked a profit, remainder closed higher")
# remainder: margin $22.9 x1, +6.01% -> gross 1.376, fees 0.016 -> net 1.36
ns, bk = run(NEW, banked=1.33, bfees=0.012, orig_margin=45.8,
             net=1.36, gross=1.376, fees=0.016, pnl_pct=6.01)
ok("the CASH booking still receives the remainder only", abs(bk['cash'] - 1.36) < 1e-9,
   f"cash ${bk['cash']:+.2f}")
ok("the win/loss verdict is judged on the whole idea", abs(bk['classify'] - 2.69) < 1e-9,
   f"classify ${bk['classify']:+.2f}")
ok("every record downstream now sees the whole idea", abs(ns['net_pnl'] - 2.69) < 1e-9,
   f"net_pnl ${ns['net_pnl']:+.2f}  (was the remainder's $1.36)")
ok("  and the whole idea's fees", abs(ns['total_fees'] - 0.028) < 1e-9, f"${ns['total_fees']:.3f}")
ok("  and its gross", abs(ns['gross_pnl'] - (1.376 + 1.33 + 0.012)) < 1e-9)
ok("  and its % on the ORIGINAL margin",
   abs(ns['pnl_pct'] - ns['gross_pnl'] / 45.8 * 100) < 1e-9, f"{ns['pnl_pct']:.2f}%")

print("\n2. THE CASE C397-4 DESCRIBED: +$0.30 banked, remainder -$0.05")
ns, bk = run(NEW, banked=0.30, bfees=0.01, orig_margin=20.0,
             net=-0.05, gross=-0.04, fees=0.01, pnl_pct=-0.4)
ok("cash still books the remainder's -$0.05", abs(bk['cash'] + 0.05) < 1e-9)
ok("every record sees +$0.25 -- a WIN, not a loss", ns['net_pnl'] > 0, f"${ns['net_pnl']:+.2f}")
ok("  and pnl_pct agrees in SIGN (Guardian, meta-learning read it)", ns['pnl_pct'] > 0,
   f"{ns['pnl_pct']:+.2f}%")

print("\n3. A TRADE THAT NEVER SPLIT IS BYTE-IDENTICAL")
ns, bk = run(NEW, banked=0.0, bfees=0.0, orig_margin=0.0,
             net=-0.41, gross=-0.39, fees=0.02, pnl_pct=-1.7)
ok("net unchanged",   ns['net_pnl'] == -0.41)
ok("gross unchanged", ns['gross_pnl'] == -0.39)
ok("fees unchanged",  ns['total_fees'] == 0.02)
ok("pnl_pct unchanged", ns['pnl_pct'] == -1.7)

print("\n4. NEGATIVE CONTROL: THE PRE-C482 BLOCK")
MARK = "            # ═══ C482-A: C397-4 WAS APPLIED TO ONE LEDGER OUT OF ELEVEN"
if raw.count(MARK) != 1:
    ok("the pre-C482 block can be reconstructed", False, "marker gone -- this test can no longer fail")
else:
    a = raw.index(MARK); b = raw.index(END, a)
    OLD = lift(raw[:a] + raw[b:])
    ns, bk = run(OLD, banked=0.30, bfees=0.01, orig_margin=20.0,
                 net=-0.05, gross=-0.04, fees=0.01, pnl_pct=-0.4)
    ok("pre-C482 hands the records the remainder's -$0.05", ns['net_pnl'] < 0, f"${ns['net_pnl']:+.2f}")
    ns, bk = run(OLD, banked=1.33, bfees=0.012, orig_margin=45.8,
                 net=1.36, gross=1.376, fees=0.016, pnl_pct=6.01)
    ok("  and records JUP at half", abs(ns['net_pnl'] - 1.36) < 1e-9, f"${ns['net_pnl']:+.2f}")

print("\n5. THE ORIGINAL MARGIN IS CAPTURED BEFORE THE FIRST HALVING")
tree = ast.parse(raw)
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_c336_partial_close')
seg = ast.get_source_segment(raw, fn)
i_cap = seg.find('pos._c482_orig_margin = float(pos.initial_margin)')
i_half = seg.find('pos.initial_margin = pos.initial_margin / 2.0')
ok("captured, then halved (order matters)", 0 <= i_cap < i_half, f"{i_cap} < {i_half}")
ok("  and only the FIRST time (a second split must not overwrite it)",
   "if not float(getattr(pos, '_c482_orig_margin', 0.0) or 0.0):" in seg)
ok("persisted across a restart", raw.count("'_c482_orig_margin': getattr(pos, '_c482_orig_margin', 0.0)") == 1
   and raw.count("pos._c482_orig_margin = float(d.get('_c482_orig_margin', 0.0) or 0.0)") == 1)

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
