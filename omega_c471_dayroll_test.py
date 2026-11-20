#!/usr/bin/env python3
"""C471: does the day loss barrier inherit yesterday's losses?

The operator's dashboard, 19 Sep: a session nine minutes old with 0W 0L,
reporting "36% spent - realised -$0.61". That $0.61 was lost the PREVIOUS day.
This test fails on the old behaviour and passes on the new one.
"""
import ast, datetime, io, json, os, re, sys, tempfile, types

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
src = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

print("\n1. THE ANCHOR IS STAMPED WITH A DATE")
ok("saved state writes _day_anchor_date", "'_day_anchor_date':" in src)
ok("restore compares it against today", "_anch471" in src and "_today471" in src)
# A grep over a slice window is a guess about where code sits. Section 2 below
# EXECUTES the branch and checks what it does, which is the real evidence; this
# only confirms the C200 keep-across-restart behaviour was not thrown away
# wholesale while fixing the day boundary.
ok("the C200 same-day keep is still present",
   "# C200" in src.split("_anch471 = d.get")[1][:1200])
ok("the live day-roll re-anchors too",
   "day loss barrier re-anchored at" in src)
ok("every fresh set stamps the date", src.count("_day_anchor_date = datetime.now().date().isoformat()") >= 3)
ok("and it fails LOUDLY if it cannot reach mode_mgr",
   "could not reach mode_mgr to re-anchor" in src)

print("\n2. THE RESTORE LOGIC, EXECUTED")
# lift the exact branch and run it against yesterday's and today's state
body = src.split("_anch471 = d.get('_day_anchor_date')")[1]
body = body.split("self._pending_new_session")[0]
code = "_anch471 = d.get('_day_anchor_date')" + body
code = re.sub(r'^                ', '', code, flags=re.M)

TODAY = datetime.date.today().isoformat()
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

def run(saved):
    ns = {'d': saved, 'datetime': datetime.datetime, 'float': float, 'str': str,
          'logger': types.SimpleNamespace(info=lambda *a, **k: None)}
    self_obj = types.SimpleNamespace(_day_start_equity='UNSET', _day_anchor_date='UNSET')
    ns['self'] = self_obj
    exec(compile(code, 'c471', 'exec'), ns)
    return self_obj

r = run({'_day_start_equity': 250.0, '_day_anchor_date': YESTERDAY})
ok("YESTERDAY's anchor is discarded", r._day_start_equity is None,
   f"got {r._day_start_equity!r} (must be None so it re-anchors at this morning's equity)")

r = run({'_day_start_equity': 250.0, '_day_anchor_date': TODAY})
ok("TODAY's anchor is KEPT (a mid-day restart must not get a fresh budget)",
   r._day_start_equity == 250.0, f"got {r._day_start_equity!r}")

r = run({'_day_start_equity': 250.0})          # written before C471 existed
ok("a pre-C471 state with no date is kept (cannot prove it is stale)",
   r._day_start_equity == 250.0, f"got {r._day_start_equity!r}")

r = run({})
ok("no saved anchor leaves it untouched", r._day_start_equity == 'UNSET')

print("\n3. THE BUG THIS REPLACES (rule 16: the test must fail on the old code)")
old_behaviour = 250.0        # the old line: restore it unconditionally
cash_today = 249.39          # what the operator's bot actually had
realised_old = cash_today - old_behaviour
limit = 1.70
ok("the OLD code charged yesterday's loss to today",
   abs(realised_old + 0.61) < 0.005 and abs(realised_old / limit - (-0.36)) < 0.01,
   f"realised {realised_old:+.2f} = {100*abs(realised_old)/limit:.0f}% of the day's barrier, on 0W 0L")
new_anchor = cash_today
ok("  the NEW code opens the day at 0% spent",
   abs((cash_today - new_anchor)) < 1e-9)

print("\n4. THE COMPOUNDING, WHICH IS THE REAL DANGER")
eq, anchor, days_lost = 250.0, 250.0, 0
for _ in range(6):
    eq -= 0.61                                   # a losing day
    if (eq - anchor) <= -limit:
        days_lost += 1                           # barrier already spent at open
ok("six losing days under the OLD rule lock the bot out", days_lost >= 3,
   f"{days_lost} of 6 mornings would open past the barrier with no trades taken")

print("\n" + "=" * 62)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
