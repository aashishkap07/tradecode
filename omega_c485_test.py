#!/usr/bin/env python3
"""C485: two wrong-time votes and a silently dead engine.

1. N52 (compute_pressure_exhaustion) no longer crashes: a real trending window
   gives a real reading. The pre-C485 source, from git, returns the all-default
   dict on the same window -- the UnboundLocalError swallowed by `except: pass`.
2. OFF is exactly what production ran on: _n52_defaults() == the pre-C485
   engine's output, the switch defaults to False, and the scan's only call to
   the engine sits behind it -- so the repair changes no live decision.
3. (superseded by C486, which restored tier_model and score_accel to their
   exact pre-C485 values -- see omega_c486_test.py)
4. the unbound-local sweep is clean now, and flags the pre-C485 source.
"""
import os, sys, io, types, contextlib, importlib.util, subprocess, tempfile, shutil
import numpy as np
REPO = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('OMEGA_BASE_PATH', '/tmp/omega_c485_test')
os.makedirs(os.environ['OMEGA_BASE_PATH'], exist_ok=True)
MARK = 'C485: NEUTRALISED'
fails = []


def ok(n, c, d=''):
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ''))
    if not c:
        fails.append(n)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(m)
    return m


def bars(sym, a, b, corpus='corpusO'):
    rows = [list(map(float, ln.split(',')[:6])) for ln in open(os.path.join(REPO, corpus, f'{sym}USDT.csv'))
            if ln.count(',') >= 5]
    return np.asarray(sorted(rows))[a:b]


def engine_out(om, w):
    c, h, l, v = w[:, 4], w[:, 2], w[:, 3], w[:, 5]
    tr = [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(-14, 0)]
    atr = float(np.mean(tr)) / c[-1] * 100
    ta = om.TechnicalAnalysis(om.Config())
    return ta.compute_pressure_exhaustion(c, h, l, v, max(atr, 0.05))


def votes(om, sym, R, windows):
    """Run the LIVE _compute_skill_components once per window. score_accel
    only votes from the 4th scan (3 snapshots make a slope, 2 slopes make an
    acceleration), so callers pass 6 windows."""
    ta = om.TechnicalAnalysis(om.Config())
    ta._bot_ref = types.SimpleNamespace(_market_bias_resultant=R, _ohlcv_cache={})
    res = None
    for w in windows:
        res = {'symbol': sym, 'direction': 0, 'components': {}}
        ta._compute_skill_components(w[:, 4], w[:, 5], w[:, 2], w[:, 3], res, sym)
    comp = res['components']
    return comp.get('tier_model'), comp.get('score_accel'), len(comp)


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, cwd=REPO).stdout


print("=" * 64); print("C485: WRONG-TIME VOTES AND THE DEAD N52 ENGINE"); print("=" * 64)
om = load(os.path.join(REPO, 'omega_v60_reconstructed.py'), 'om485')
intro = git('log', '--format=%H', '-S', MARK, '--', 'omega_v60_reconstructed.py').split()
ref = (intro[-1] + '^') if intro else 'HEAD'
old_src = git('show', f'{ref}:omega_v60_reconstructed.py')
tmpd = tempfile.mkdtemp(prefix='c485_')
if MARK in old_src or not old_src:
    print(f"  cannot rebuild the pre-C485 source from {ref}"); om_old = None
    ok("the pre-C485 source can be rebuilt", False)
else:
    old_path = os.path.join(tmpd, 'omega_pre485.py'); io.open(old_path, 'w', encoding='utf-8').write(old_src)
    om_old = load(old_path, 'om_pre485')

W = bars('SOL', 4900, 5001)          # a real trending 15m window (Feb-Jun 2026 corpus)

print("\n1. THE N52 ENGINE RUNS")
o = engine_out(om, W)
ok("a trending window gives a real reading (no silent crash)", o['dir'] != 0 and o['x'] > 0 and o['n_legs'] > 0,
   f"dir={o['dir']} x={o['x']:.2f} legs={o['n_legs']}")
if om_old:
    oo = engine_out(om_old, W)
    ok("NEGATIVE CONTROL: pre-C485 returns the all-default dict on the same window",
       oo['dir'] == 0 and oo['x'] == 0.0 and oo['next_pct'] == 0.0, f"dir={oo['dir']} x={oo['x']}")

print("\n2. OFF IS EXACTLY WHAT PRODUCTION RAN ON")
ok("the switch defaults to OFF", om.Config().C485_N52_LIVE is False)
if om_old:
    ok("_n52_defaults() == what the pre-C485 engine returned (every key and value)",
       om.TechnicalAnalysis._n52_defaults() == engine_out(om_old, W))
src = open(os.path.join(REPO, 'omega_v60_reconstructed.py'), encoding='utf-8').read()
calls = [i for i in range(len(src)) if src.startswith('self.compute_pressure_exhaustion(', i)]
gate = src.rfind("if getattr(self.cfg, 'C485_N52_LIVE', False):", 0, calls[0]) if calls else -1
ok("the scan's one call to the engine sits directly behind the switch",
   len(calls) == 1 and gate > 0 and calls[0] - gate < 120, f"{len(calls)} call(s)")

print("\n3. TIER_MODEL AND SCORE_ACCEL")
print("  (superseded: C486 restored both votes to their exact pre-C485 values --")
print("   omega_c486_test.py proves the equivalence against the pre-C485 source)")

print("\n4. THE UNBOUND-LOCAL SWEEP")
r = subprocess.run([sys.executable, 'omega_unbound_local_sweep.py'], capture_output=True, text=True, cwd=REPO)
ok("clean on the current source", r.returncode == 0, r.stdout.strip().splitlines()[1] if r.stdout else r.stderr[-200:])
if om_old:
    r2 = subprocess.run([sys.executable, 'omega_unbound_local_sweep.py', old_path], capture_output=True, text=True, cwd=REPO)
    ok("POSITIVE CONTROL: flags the pre-C485 source (_zig reads atr_abs)", r2.returncode == 1 and "'atr_abs'" in r2.stdout)
shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 64)
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
sys.exit(1 if fails else 0)
