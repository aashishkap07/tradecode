#!/usr/bin/env python3
"""C483: the whole-code audit's fixes, each checked on the SHIPPED source.

Rule 16: section 7 rebuilds the pre-C483 source from git and requires the
resume-path risk frame to be inside the header's `except` there -- proof this
check can fail.
"""
import ast, io, re, subprocess, sys
SRC = '/home/user/tradecode/omega_v60_reconstructed.py'
raw = io.open(SRC, encoding='utf-8').read()
tree = ast.parse(raw)
fails = []
def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c: fails.append(n)
def fn(name):
    return ast.get_source_segment(raw, next(n for n in ast.walk(tree)
                                  if isinstance(n, ast.FunctionDef) and n.name == name))
def frames_in_except(text):
    """risk_frame() calls that sit inside an `except` handler."""
    t = ast.parse(text); bad = 0; total = 0
    for h in ast.walk(t):
        if isinstance(h, ast.ExceptHandler):
            for c in ast.walk(h):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == 'risk_frame':
                    bad += 1
    for c in ast.walk(t):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == 'risk_frame':
            total += 1
    return bad, total

print("=" * 64); print("C483: THE WHOLE-CODE AUDIT'S FIXES"); print("=" * 64)
print("\n1. THE BUDGET STOP BELONGS TO THE POSITION (two threads, one cfg)")
ok("nothing writes it onto the shared cfg any more", 'cfg._budget_stop_pct' not in raw.replace('# ', ''))
ok("the monitor writes it on the position", 'pos._budget_stop_pct = -max(1.0,' in raw)
ok("the exit check reads the position's own", "_bstop = getattr(self, '_budget_stop_pct', None)" in fn('_should_exit_dri_raw'))
print("\n2. A METHOD THAT IS GIVEN cfg USES IT")
ok("_should_exit_dri_raw reads C404_DD_HARD_MULT from its cfg argument",
   "getattr(cfg, 'C404_DD_HARD_MULT', 1.35)" in fn('_should_exit_dri_raw')
   and "getattr(getattr(self, 'cfg', None), 'C404_DD_HARD_MULT'" not in raw)
print("\n3. VALUES READ FROM WHERE THEY LIVE")
ok("the +macro tag reads analysis, not the bot", "_macro_o = analysis.get('_macro_dir', 0)" in raw)
ok("the dashboard asks PositionsManager through get_all()", "getattr(bot_ref.portfolio.positions, '_positions'" not in raw)
print("\n4. EVERY 'DAY' DISPLAY READS THE ONE GUARD")
ok("the summary's Day line reads the guard, not normal_start_equity",
   'Day: {pnl:+.2f}% realised' in raw and "pnl = self.mode_mgr.get_normal_pnl_pct(stats['live_equity'])" not in raw)
ok("no 'barrier ±' / 'DD / 22' / 'day cap' left in any log line",
   not re.search(r'logger\.\w+\(f?".*(barrier \\u00b1|DD / 22|day cap \{)', raw))
ok("the header shows the monthly dial", 'risk dial {float(day_barrier):.0f}%/month' in raw)
ok("the budget banner waits for the saved dial", "if not bool(getattr(self, '_c462_state_settled', False)):\n                return" in fn('_c369_apply_budget'))
ok("'Flask not available' is no longer a warning", 'logger.warning("⚠️ Flask not available' not in raw)
print("\n5. REMOVED, BECAUSE THEY LIED ABOUT WHAT RUNS")
ok("eval-window odometer gone (live code, not the changelog)",
   'logger.info(f"   \U0001f9ee EVAL TRADE' not in raw and '🧮 EVAL TRADE #{' not in raw
   and 'self.cfg.EVAL_FILE' not in raw and '_eval_count' not in raw)
ok("is_dri_indecisive gone (read a field nothing assigns)", 'def is_dri_indecisive' not in raw)
ok("_apply_penalty gone (never called; the 45% floor is applied elsewhere)",
   'def _apply_penalty' not in raw and '* 0.45' in raw)
dead = "PROFIT_LOCK_ENABLED DRI_SMOOTHING MTF_AGREEMENT_THRESHOLD HURST_LOOKBACK SESSION_DRAWDOWN_STOP_SECONDS VOL_TRENDING_THRESHOLD".split()
ok("the 38 settings nothing read are gone (spot-check 6)", not any(re.search(r'self\.' + k + r'\s*=', raw) for k in dead))
print("\n6. THE RESUME PATH SHOWS THE RISK FRAME")
b, t = frames_in_except(raw)
ok("no risk_frame() call sits inside an except handler", b == 0 and t == 2, f"{b} of {t} inside an except")
print("\n7. NEGATIVE CONTROL: THE PRE-C483 SOURCE")
def _git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd='/home/user/tradecode').stdout
intro = _git('log', '--format=%H', '-S', 'C483: this block sat INSIDE the header', '--', 'omega_v60_reconstructed.py').split()
ref = (intro[-1] + '^') if intro else 'HEAD'
old = _git('show', f'{ref}:omega_v60_reconstructed.py')
if 'C483: this block sat INSIDE the header' in old:
    ok("the pre-C483 source can be rebuilt", False, f"{ref} already fixed")
else:
    b, t = frames_in_except(old)
    ok("pre-C483 had the resume risk frame inside the header's except", b == 1, f"{b} of {t}")
    ok("  and wrote the budget stop onto the shared cfg", 'self.cfg._budget_stop_pct = -max' in old)
    ok("  and printed 'Day:' from normal_start_equity",
       "pnl = self.mode_mgr.get_normal_pnl_pct(stats['live_equity'])" in old)
print("\n" + "=" * 64)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
