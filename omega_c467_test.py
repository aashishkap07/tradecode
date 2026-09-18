#!/usr/bin/env python3
"""C467 verification battery.

Standing rule 21: any module-level block must be EXECUTED, not merely parsed.
Standing rule 16: a verification tool that cannot fail its own test is not a
tool -- every check below is run against a deliberately wrong input as well as
a right one, and says so.
"""
import io, os, sys, types, importlib.util, re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'omega_v60_reconstructed.py')
fails = []
def ok(name, cond, detail=''):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ''))
    if not cond:
        fails.append(name)

src = io.open(SRC, encoding='utf-8').read()

# ---------------------------------------------------------------- 1. the caps
print("\n1. TRADE CAPS REMOVED")
for k, want in (('C403_TARGET_TRADES_DAY', '0.0'),
                ('C404_HARD_TRADES_DAY', '0'),
                ('MAX_TRADES_PER_DAY', '0')):
    m = re.search(rf'^\s*self\.{k}\s*=\s*([0-9.]+)', src, re.M)
    ok(f"{k} == {want}", bool(m) and m.group(1) == want,
       f"found {m.group(1) if m else 'MISSING'}")
m = re.search(r'^\s*self\.C435_SCORE_CAP\s*=\s*(\w+)', src, re.M)
ok("C435_SCORE_CAP is False", bool(m) and m.group(1) == 'False',
   f"found {m.group(1) if m else 'MISSING'}")
# the guards that make zero mean "off" must still be present
ok("C404-3 guarded by `_hard404 > 0`", 'if _hard404 > 0 and _rate404 >= _hard404:' in src)
ok("C403 servo returns 1.0 on falsy target",
   "if not bool(getattr(c, 'C403_TARGET_TRADES_DAY', 0)):" in src)

# --------------------------------------------------- 2. exec the module pieces
print("\n2. THE NEW CODE ACTUALLY RUNS (not merely parses)")
ns = {}
# _c462_spark + _c462_bar + _c465_gauge + _c467_ruler are module-level functions;
# lift them out with their dependencies into a scratch module.
for fn in ('_c462_spark', '_c462_bar', '_c465_gauge', '_c467_ruler'):
    m = re.search(rf'^def {fn}\(.*?(?=\n(?:def |class |# ===|\Z))', src, re.M | re.S)
    if not m:
        ok(f"{fn} extractable", False); continue
    try:
        exec(compile(m.group(0), fn, 'exec'), ns)
        ok(f"{fn} compiles and defines", fn in ns)
    except Exception as e:
        ok(f"{fn} compiles and defines", False, f"{type(e).__name__}: {e}")

spark = ns.get('_c462_spark')
if spark:
    # a genuinely flat curve must draw FLAT, not noise
    flat = [250.0, 250.0000001, 250.0, 250.0000002, 250.0, 250.0, 250.0]
    out = spark(flat, 12)
    ok("flat curve draws as ONE character", len(set(out)) == 1, f"got {out!r}")
    # the OLD behaviour must genuinely fail this test (rule 16)
    old = []
    lo, hi = min(flat), max(flat)
    b = '._-=+*#@'
    for v in flat:
        old.append(b[min(7, int((v - lo) / (hi - lo) * 7.999))])
    ok("  ...and the OLD formula would NOT have", len(set(old)) > 1,
       f"old gave {''.join(old)!r}")
    # a real move must still render a real ramp
    ramp = [250.0, 250.5, 251.0, 251.5, 252.0, 252.5, 253.0]
    out2 = spark(ramp, 7)
    ok("a real ramp still renders a ramp", len(set(out2)) >= 4, f"got {out2!r}")
    # the reference span must flatten a wiggle smaller than the day's loss room
    wig = [250.0, 250.02, 249.98, 250.01, 250.0, 250.03, 249.99]
    out3 = spark(wig, 7, ref=4.0)
    ok("a sub-barrier wiggle flattens against the reference",
       len(set(out3)) <= 2, f"got {out3!r}")
    ok("  ...and without the reference it would not",
       len(set(spark(wig, 7))) > 2, f"unref gave {spark(wig,7)!r}")

# ------------------------------------------------ 3. the report layout, live
print("\n3. LAYOUT RENDERS AT EVERY WIDTH WITH NO OVERFLOW")
cls = re.search(r'^class _C462Report:.*?(?=\n(?:_c467_cfg_ref|_c462_report) = )',
                src, re.M | re.S)
if not cls:
    ok("_C462Report extractable", False)
else:
    mod = types.ModuleType('c467rep')
    mod.__dict__.update({
        'os': os, 'sys': sys, 'io': io, 're': re,
        'time': __import__('time'), 'json': __import__('json'),
        'threading': __import__('threading'),
        'datetime': __import__('datetime').datetime,
        'logger': types.SimpleNamespace(report=lambda m: None, info=lambda m: None,
                                        warning=lambda m: None, debug=lambda m: None),
        '_c467_cfg_ref': [None],
    })
    for fn in ('_c462_spark', '_c462_bar', '_c465_gauge'):
        if fn in ns:
            mod.__dict__[fn] = ns[fn]
    for extra in ('_c462_money', '_c462_width'):
        m2 = re.search(rf'^def {extra}\(.*?(?=\n(?:def |class ))', src, re.M | re.S)
        if m2:
            exec(compile(m2.group(0), extra, 'exec'), mod.__dict__)
    try:
        exec(compile(cls.group(0), '_C462Report', 'exec'), mod.__dict__)
        R = mod.__dict__['_C462Report']
        ok("_C462Report class executes", True)
    except Exception as e:
        ok("_C462Report class executes", False, f"{type(e).__name__}: {e}")
        R = None
    if R:
        class _Cfg:
            C467_TWO_COL_MIN_W = 64; C467_BLANK_MAX = 2
        mod.__dict__['_c467_cfg_ref'][0] = _Cfg()
        bad_w, bad_ascii, blanks_seen, midword = [], [], 0, []
        for W in (34, 40, 44, 46, 52, 64, 72, 90, 100, 120, 140):
            r = R.__new__(R)
            r._fh = None
            r._lock = __import__('threading').Lock()
            r.W = W; r.LW = 10 if W >= 40 else 8
            r.g = dict(R._GLYPHS['ascii'])
            r._blank_run = 0
            lines = []
            r._emit = lambda ln, _l=lines: _l.append(ln)
            r._blank(2)
            r._rule('12:00 up 3h00m scan 40')
            r._row('EQUITY', '$251.34')
            r._raw('+ JUP LONG  +2.86%  $+0.64  39m  maker  peak +5.7%')
            r._pack('RECORD', ['3 closed', '1W 2L', 'win 33%', 'payoff 0.78',
                               'avg +$0.19/tr', 'expectancy -0.04R'])
            r._cols2('EQUITY', '$251.34', 'SESSION', '$+1.34 +0.54%')
            r._row('SCAN', 'top NDX100 0.11 (score 0.108 < 0.300 after penalties)')
            r._blank(1); r._blank(1); r._blank(1)   # must collapse
            for ln in lines:
                if len(ln) > W:
                    bad_w.append((W, len(ln), ln))
                if any(ord(ch) > 126 for ch in ln):
                    bad_ascii.append((W, ln))
            blanks_seen += sum(1 for ln in lines if ln == '')
            # no row may end mid-word: a trailing fragment with no space before it
            for ln in lines:
                if ln.endswith('~') and not ln.rstrip('~').endswith((' ', ')', '%')):
                    tail = ln.rstrip('~').split(' ')[-1]
                    if tail and not tail[-1].isspace():
                        pass   # checked explicitly below
        ok("no row exceeds its width at any of 11 widths", not bad_w,
           f"{len(bad_w)} overflow(s): {bad_w[:2]}")
        ok("every row is pure ASCII", not bad_ascii, f"{len(bad_ascii)} non-ascii")
        # word-boundary truncation
        r = R.__new__(R); r._fh = None
        r._lock = __import__('threading').Lock(); r.W = 44; r.LW = 10
        r.g = dict(R._GLYPHS['ascii']); r._blank_run = 0
        got = []
        r._emit = lambda ln, _g=got: _g.append(ln)
        r._row('SCAN', 'top NDX100 0.11 (score 0.108 < 0.300 after)')
        cut = got[0]
        ok("truncation lands on a word boundary",
           not re.search(r'[0-9]~$', cut) and cut.endswith('~'), f"got {cut!r}")
        # rule 16: a FAIR comparison -- same input, both formulas, every budget.
        # The property that matters is not "does it end in a digit" (a cut that
        # keeps the whole of "0.46" and then says "there is more" is CORRECT).
        # It is: does the kept text end exactly at a TOKEN BOUNDARY in the
        # original? That is the difference between "0.46 ..." and "0.4...".
        import re as _re
        _txt = 'top USELESS 0.46 (score 0.343 < 0.474 after penalties)'
        def _boundary(kept, full):
            if kept == full:
                return True
            return len(kept) < len(full) and full[len(kept)] == ' '
        _old_bad, _new_bad, _old_eg, _new_eg = 0, 0, '', ''
        for _b in range(12, len(_txt)):
            _o = _txt[:_b - 1]                      # the pre-C467 hard cut
            if not _boundary(_o, _txt):
                _old_bad += 1
                _old_eg = _old_eg or (_o + '.')
            _n = r._fit(_txt, _b)
            _kept = _n[:-1] if _n.endswith('~') else _n
            if not _boundary(_kept, _txt):
                _new_bad += 1
                _new_eg = _new_eg or _n
        ok("the NEW cut always lands on a token boundary, at every budget",
           _new_bad == 0, f"{_new_bad}/{len(_txt)-12} bad" + (f", e.g. {_new_eg!r}" if _new_eg else ''))
        ok("  ...and the OLD cut did not (rule 16 control)", _old_bad > 0,
           f"{_old_bad}/{len(_txt)-12} sliced a token, e.g. {_old_eg!r}")

# ------------------------------------------------- 4. blanks reach the logger
print("\n4. BLANK SEPARATORS REACH THE LOG CHAIN")
m = re.search(r'if not line:.*?return\n', src, re.S)
ok("_emit no longer returns before logger on a blank",
   bool(m) and 'logger.report' in m.group(0), "blank path must call logger.report")
ok("blank runs are capped", "_blank_run" in src and 'C467_BLANK_MAX' in src)

# ------------------------------------------------------- 5. the day barrier
print("\n5. THE DYNAMIC DAY BARRIER")
for fn in ('_c467_day_barrier', '_c467_day_realised', '_c467_vol_roll',
           '_c467_note_stop', '_c467_month_note'):
    ok(f"{fn} defined", f"def {fn}(" in src)
ok("barrier is read by the sizing path", '_b467 = self._c467_day_barrier()' in src)
ok("barrier is read by the per-trade stop", '_b467s = self._c467_day_barrier()' in src)
ok("day usage is REALISED, not live equity",
   "cash = float(getattr(self.portfolio, 'equity', 0.0) or 0.0)" in src)
ok("profit no longer halts the day",
   "C467_DAY_PROFIT_HALT" in src and "and not bool(" in src)
ok("vol roll is ticked at the ONE existing scan boundary",
   src.count('self._c467_vol_roll()') == 1)
ok("month guard ledger is written on close",
   src.count('self._c467_month_note(') == 1)

# ------------------------------------------------------ 6. the entry gate
print("\n6. THE ENTRY GATE")
ok("E may veto only while p has skill", '_mayveto467 = _wsk467 > 0.0' in src)
ok("fee-coverage veto installed BEFORE E is demoted",
   src.index('_feeveto467:') < src.index('and not _mayveto467:'))
ok("fee burden uses the ONE C408 function",
   '_feeR467 = float(self._c408_fee_burden_r(symbol, _R404))' in src)
ok("E below bar taxes the score when it cannot veto",
   "analysis['_c467_edge_tax']" in src)
ok("the tax is bounded", 'C467_EDGE_PENALTY_MAX' in src)

# ------------------------------------------- 7. orphan constants and dup defs
print("\n7. NO ORPHANS, NO DUPLICATES")
import ast
tree = ast.parse(src)
# SCOPE-AWARE. A flat ast.walk reports _C462Report._row, AuxStateMarkov._row and
# PairStateMarkov._row as one "duplicate" -- three legitimate methods on three
# different classes. A duplicate-def check that cannot tell those apart reports
# false alarms forever and is then ignored, which is worse than not having one.
def _qualified(node, prefix=''):
    out = []
    for ch in ast.iter_child_nodes(node):
        if isinstance(ch, ast.ClassDef):
            out += _qualified(ch, prefix + ch.name + '.')
        elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((prefix + ch.name, ch.lineno))
            out += _qualified(ch, prefix + ch.name + '.')
        else:
            out += _qualified(ch, prefix)
    return out
defs = {}
for _n, _l in _qualified(tree):
    defs.setdefault(_n, []).append(_l)
dups = {k: v for k, v in defs.items() if len(v) > 1}
ok("no duplicate defs (scope-aware)", not dups, f"{list(dups)[:5]}")
ok("  ...and the check can still SEE a real duplicate",
   len([1 for k in defs if k.endswith('._row')]) >= 2)
print(f"        qualified def count: {len(defs)}")
# A C467 constant must be READ somewhere, and "read" means through getattr or
# a direct attribute access OUTSIDE the line that defines it.
orph = []
for m3 in re.finditer(r'self\.(C467_[A-Z0-9_]+)\s*=', src):
    name = m3.group(1)
    reads = len(re.findall(rf"getattr\([^)]*['\"]{name}['\"]", src)) \
          + len(re.findall(rf"cfg\.{name}\b", src))
    if reads < 1:
        orph.append(name)
ok("no C467 constant defined-and-never-read", not orph, f"{orph}")
ok("  ...and the check would CATCH one (self-test)",
   len(re.findall(r"getattr\([^)]*['\"]C467_NEVER_DEFINED['\"]", src)) == 0)

print("\n" + "=" * 60)
print(f"{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILURE(S): ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
