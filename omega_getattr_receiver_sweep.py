"""Sweep: getattr/hasattr on a known component for a field that component never has.

C486 found the dashboard's session P&L reading
    getattr(bot_ref.mode_mgr, 'session_start_equity', eq)
TradingModeManager never has that field, so the default came back on every
poll and the tile said +$0.00 since it was built. C483 was the same shape
(getattr(positions, '_positions', {})). The typed sweep missed it because the
receiver was reached through a CHAIN (bot_ref.mode_mgr), not through self.

Method: learn which class each component attribute holds from assignments of
the form  <x>.<attr> = ClassName(...)  (e.g. self.mode_mgr = TradingModeManager).
Learn every field each class ever has: self.<f> = ... inside the class,
<anything>.<attr>.<f> = ... anywhere, setattr(..., '<f>', ...), and
@property / method names. Then flag every getattr/hasattr whose receiver is a
chain ending in a known component attribute and whose field name that class
NEVER has. Exit 1 on any finding.
"""
import ast, sys, collections

PATH = sys.argv[1] if len(sys.argv) > 1 else 'omega_v60_reconstructed.py'
tree = ast.parse(open(PATH, encoding='utf-8').read())
classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}

# 1. component attribute -> class, from  x.attr = ClassName(...)
comp = collections.defaultdict(set)
for n in ast.walk(tree):
    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) \
            and n.value.func.id in classes:
        for t in n.targets:
            if isinstance(t, ast.Attribute):
                comp[t.attr].add(n.value.func.id)

# the settings object is passed around, never built with Config(...) at its use
# sites, so name it explicitly: every *.cfg / *.config and a bare `cfg` is Config
if 'Config' in classes:
    comp['cfg'].add('Config'); comp['config'].add('Config')

# 2. fields each class ever has
fields = collections.defaultdict(set)
for cname, c in classes.items():
    for n in ast.walk(c):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fields[cname].add(n.name)
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            tg = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in tg:
                for e in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                    if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name) and e.value.id == 'self':
                        fields[cname].add(e.attr)
    for b in c.bases:                                  # inherited names count
        if isinstance(b, ast.Name) and b.id in classes:
            fields[cname] |= {x.name for x in ast.walk(classes[b.id]) if isinstance(x, ast.FunctionDef)}
external = collections.defaultdict(set)                # <...>.<attr>.<f> = ...
setattr_names = set()
for n in ast.walk(tree):
    if isinstance(n, (ast.Assign, ast.AugAssign)):
        tg = n.targets if isinstance(n, ast.Assign) else [n.target]
        for t in tg:
            for e in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Attribute):
                    external[e.value.attr].add(e.attr)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'setattr' \
            and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str):
        setattr_names.add(n.args[1].value)

def has(attr, field):
    kinds = comp.get(attr, set())
    if not kinds:
        return True
    if field in setattr_names or field in external.get(attr, set()):
        return True
    return any(field in fields[k] for k in kinds)

findings = []
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('getattr', 'hasattr') \
            and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str):
        recv = n.args[0]
        if isinstance(recv, ast.Name) and recv.id in ('cfg', 'config'):
            recv = ast.Attribute(value=ast.Name(id='_', ctx=ast.Load()), attr=recv.id, ctx=ast.Load())
        if isinstance(recv, ast.Attribute) and recv.attr in comp:
            f = n.args[1].value
            if f.startswith('__'):
                continue
            if not has(recv.attr, f):
                findings.append((n.lineno, n.func.id, recv.attr, sorted(comp[recv.attr]), f))
print(f"components learned: {len(comp)}  ({', '.join(sorted(comp)[:14])}{' ...' if len(comp) > 14 else ''})")
print(f"getattr/hasattr on a component for a field its class never has: {len(findings)}")
for ln, fn, attr, kinds, f in sorted(findings):
    print(f"  line {ln:>6}  {fn}(<..>.{attr} [{'/'.join(kinds)}], '{f}')")
sys.exit(1 if findings else 0)
