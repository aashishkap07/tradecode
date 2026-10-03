#!/usr/bin/env python3
"""C482-B: ONE loss control, set by the operator's monthly dial.

Lifts the real methods out of the shipped bot class and runs them on a stub bot.
Rule 16: section 7 rebuilds the pre-C482 barrier FROM GIT and requires it to
un-breach itself when volatility rises after a loss -- the 23 Sep defect.
"""
import ast, io, os, subprocess, sys, time, types, datetime

SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
raw = io.open(SRC, encoding='utf-8').read()
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)

LOG = []
class L:
    def info(self, m): LOG.append(('info', str(m)))
    def warning(self, m): LOG.append(('warn', str(m)))
    def debug(self, m): pass

def lift(text, names):
    tree = ast.parse(text)
    got = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names and node.name not in got:
            got[node.name] = node
    miss = set(names) - set(got)
    if miss: raise SystemExit(f"cannot lift {miss}")
    g = {'time': time, 'logger': L(), 'datetime': datetime, 'os': os}
    mod = ast.Module(body=[ast.ClassDef(name='B', bases=[], keywords=[], body=list(got.values()),
                                        decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, '<b>', 'exec'), g)
    return g['B']

B = lift(raw, ['_c482_risk_guard', '_c482_scan_halted', '_c467_day_barrier',
               '_c482_poll_commands', '_c482_set_dial'])

class Cfg:
    C380_MAX_MONTHLY_DD_PCT = 15.0; C482_DAY_SHARE = 0.25; C482_MIN_ROOM_FRAC = 0.30
    C482_HALT_NOTE_MIN = 60; PER_TRADE_RISK_PCT = 0.00341
def mk(eq, day0, month=None, settled=True, pct=15.0):
    b = B()
    b.cfg = Cfg(); b.cfg.C380_MAX_MONTHLY_DD_PCT = pct
    saves = []
    b.portfolio = types.SimpleNamespace(equity=eq, save_state=lambda: saves.append(1))
    if month is not None: b.portfolio._c482_month = month
    b.mode_mgr = types.SimpleNamespace(_day_start_equity=day0)
    b._c462_state_settled = settled
    b._saves = saves
    return b
KEY = datetime.date.today().strftime('%Y-%m')

print("=" * 66); print("C482-B: ONE LOSS CONTROL, SET BY THE MONTHLY DIAL"); print("=" * 66)

print("\n1. TODAY'S NUMBERS: 15% dial, month anchored at $254.10, day down $1.90")
b = mk(252.20, 254.10, {'key': KEY, 'eq0': 254.10})
g = b._c482_risk_guard()
ok("month budget = 15% of $254.10", abs(g['month_budget'] - 38.115) < 1e-6, f"${g['month_budget']:.2f}")
ok("day cap = 25% of what the month had left at the day's start",
   abs(g['day_cap'] - 0.25 * 38.115) < 1e-6, f"${g['day_cap']:.2f}")
ok("$1.90 down is NOT a halt -- an ordinary losing run is not a broken day",
   g['halt'] == '', f"used ${g['day_used']:.2f} of ${g['day_cap']:.2f}")

print("\n2. THE DAY CAP CANNOT MOVE DURING THE DAY")
caps = []
for eq in (254.10, 253.00, 251.50, 249.00, 246.00):
    caps.append(round(mk(eq, 254.10, {'key': KEY, 'eq0': 254.10})._c482_risk_guard()['day_cap'], 6))
ok("same cap at every point of a losing day", len(set(caps)) == 1, f"{caps[0]:.2f} x{len(caps)}")
ok("  and nothing volatility-dependent is read", 'vol' not in ast.get_source_segment(
   raw, next(n for n in ast.walk(ast.parse(raw)) if isinstance(n, ast.FunctionDef)
             and n.name == '_c482_risk_guard')).split('"""')[2])

print("\n3. THE THREE HALTS")
ok("dial 0% -> halt 'dial'", mk(254.10, 254.10, {'key': KEY, 'eq0': 254.10}, pct=0)._c482_risk_guard()['halt'] == 'dial')
g = mk(254.10 - 9.40, 254.10, {'key': KEY, 'eq0': 254.10})._c482_risk_guard()
ok("day spent -> halt 'day'", g['halt'] == 'day', f"used ${g['day_used']:.2f} of ${g['day_cap']:.2f}")
g = mk(215.0, 216.0, {'key': KEY, 'eq0': 254.10})._c482_risk_guard()
ok("month spent -> halt 'month'", g['halt'] == 'month', f"used ${g['month_used']:.2f} of ${g['month_budget']:.2f}")

print("\n4. THE MONTH IS NET, NOT GROSS LOSSES")
g = mk(260.0, 258.0, {'key': KEY, 'eq0': 254.10})._c482_risk_guard()
ok("a month that is UP has used nothing", g['month_used'] == 0.0, f"equity $260 vs anchor $254.10")

print("\n5. A RUN OF BAD DAYS PACES ITSELF")
eq0 = 254.10; eq = eq0; caps = []
for day in range(4):
    gg = mk(eq, eq, {'key': KEY, 'eq0': eq0})._c482_risk_guard()
    caps.append(gg['day_cap']); eq -= gg['day_cap']
left = mk(eq, eq, {'key': KEY, 'eq0': eq0})._c482_risk_guard()['month_left']
ok("four maximal days in a row still leave about a third of the month",
   0.30 < left / (eq0 * 0.15) < 0.34, f"{100 * left / (eq0 * 0.15):.0f}% left; caps "
   + ", ".join(f"${c:.2f}" for c in caps))

print("\n6. BOOT ORDER, THE STOP BUTTON, AND THE DIAL")
b = mk(250.0, 250.0, None, settled=False)
g = b._c482_risk_guard()
ok("no month anchor before the saved state has loaded", not hasattr(b.portfolio, '_c482_month'))
ok("  and no save_state call (it would overwrite the real file)", b._saves == [])
b = mk(252.0, 252.0, None, settled=True); b._c482_risk_guard()
ok("anchors once the state is settled", getattr(b.portfolio, '_c482_month', {}).get('eq0') == 252.0)

LOG.clear()
b = mk(254.10 - 9.40, 254.10, {'key': KEY, 'eq0': 254.10})
ok("halted -> no scan", b._c482_scan_halted() is True)
b._c482_scan_halted(); b._c482_scan_halted()
ok("  says so ONCE, not every tick", sum(1 for k, m in LOG if 'NOT SCANNING' in m) == 1)
ok("  and says open positions are still watched",
   any('still watched' in m for k, m in LOG))

class Remote:
    def __init__(self, q): self.q = list(q)
    def check_commands(self): return self.q.pop(0) if self.q else None
b = mk(254.10 - 9.40, 254.10, {'key': KEY, 'eq0': 254.10})
b._remote = Remote(['stop'])
stopped = False
try:
    b._c482_poll_commands()
except KeyboardInterrupt:
    stopped = True
ok("the STOP button works while the scan is halted", stopped)

applied = []
b = mk(254.10, 254.10, {'key': KEY, 'eq0': 254.10})
b._c369_apply_budget = lambda eq: applied.append(eq)
b._remote = Remote([('risk', 8.0)])
b._c482_poll_commands()
ok("a dial change from the panel is applied", b.cfg.C380_MAX_MONTHLY_DD_PCT == 8.0)
ok("  and re-derives per-trade risk from it", applied == [254.10])
ok("  and is saved", len(b._saves) >= 1)
b._c482_set_dial(35)
ok("  and is clamped to 0-20", b.cfg.C380_MAX_MONTHLY_DD_PCT == 20.0)

print("\n7. THE WIRING IN THE SHIPPED FILE")
tree = ast.parse(raw)
def fn(name): return ast.get_source_segment(raw, next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == name))
ok("the scan gate asks the guard", 'and not self._c482_scan_halted():' in raw)
ok("the panel is polled EVERY tick, before that gate",
   raw.index('self._c482_poll_commands()\n\n                    # 10. Scan') <
   raw.index('and not self._c482_scan_halted():'))
ok("the Guardian reports but does not act by default",
   "if not bool(getattr(_cfg482, 'C482_GUARDIAN_ACT', False)):" in fn('should_intervene'))
ok("the session breaker is off by default",
   "if bool(getattr(self.cfg, 'C482_SESSION_BREAKER', False)):" in raw)
_keep = raw.index('_r397 = _c468_input(f"  Keep it? Enter to keep')
ok("a headless RESTART no longer overwrites the saved dial from OMEGA_MAX_DD",
   'OMEGA_MAX_DD' not in raw[_keep:raw.index('.strip()', _keep)])
_fresh = raw.index('Max monthly drawdown you accept')
ok("  while a FRESH start still takes OMEGA_MAX_DD as its seed",
   "env='OMEGA_MAX_DD'" in raw[_fresh:_fresh + 200])
ok("the month anchor is persisted and restored",
   "'c482_month': getattr(self, '_c482_month', None)," in raw and "self._c482_month = {'key'" in raw)

print("\n8. NEGATIVE CONTROL: THE PRE-C482 BARRIER, FROM GIT")
# Pinned to the commit BEFORE C482 introduced the guard, not to HEAD: once
# C482 is committed HEAD *is* the fixed version, and a control that reads HEAD
# quietly stops being a control (the C479 watchdog test's lesson).
def _git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True,
                          cwd='/home/user/tradecode').stdout.strip()
_intro = _git('log', '--format=%H', '-S', 'def _c482_risk_guard', '--', 'omega_v60_reconstructed.py').split()
_ref = (_intro[-1] + '^') if _intro else 'HEAD'
old = _git('show', f'{_ref}:omega_v60_reconstructed.py')
if '_c482_risk_guard' in old or 'def _c467_day_barrier' not in old:
    ok("the pre-C482 barrier can be rebuilt from history", False, f"{_ref} is not pre-C482")
else:
    OB = lift(old, ['_c467_day_barrier', '_c467_day_realised'])
    def old_used(vol_ratio):
        b = OB()
        b.cfg = types.SimpleNamespace(DAY_RISK_CAP_PCT=15.0 / 22 / 100, C467_DYN_BARRIER=True,
                                      C467_BARRIER_REALISED=True, C380_MAX_MONTHLY_DD_PCT=15.0)
        b.portfolio = types.SimpleNamespace(equity=254.10 - 1.90)
        b.mode_mgr = types.SimpleNamespace(_day_start_equity=254.10)
        b._c467_vol_state = {'ratio': vol_ratio}
        b._c463_realised_payoff = lambda: (0.0, 0)
        return b._c467_day_barrier()['frac']
    a, z = old_used(1.08), old_used(1.41)
    ok("pre-C482: $1.90 down reads OVER the limit at vol x1.08", a >= 1.0, f"{100 * a:.0f}% used")
    ok("  and UNDER it once vol rises to x1.41 -- same loss, limit moved away",
       z < 1.0, f"{100 * z:.0f}% used  (this is how GRT, EVAA and MET were opened)")

print("\n" + "=" * 66)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
