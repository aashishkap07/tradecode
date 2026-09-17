"""C464-6: the sweep that catches the wrong-object family — instance nine and beyond.

    python3 omega_wrong_object_sweep.py                       # report
    python3 omega_wrong_object_sweep.py --baseline            # write the baseline
    python3 omega_wrong_object_sweep.py --diff                # NEW findings only

USE IT AS A DIFF, NOT AS A ZERO-FINDINGS GATE. This codebase decorates objects
from outside all the time -- `pos._c372_R_pct = ...` in TradingBot, read as
`self._c372_R_pct` in Position -- which is legitimate and accounts for almost
every one of the ~99 baseline findings. Distinguishing that from the real bug
statically would need type inference. What DOES work is the delta: with the
C464-6 bug reintroduced the count goes 99 -> 100, and the new line names it.
So: run --diff before every ship and read what is NEW.

THE FAMILY IT EXISTS FOR (nine instances and counting): C422-1, C433-1, C440-3,
C445, C462-4, C463-1 (the maker exit, dead for 87 versions), C464-6. All silent,
because getattr() has a default and a fresh dict is falsy rather than an error.

The existing sweep checked ALL-CAPS class attributes. It could not have caught
_c464_board, which is a lower-case instance attribute ASSIGNED inside one class
and READ inside another -- the failure is silent because getattr has a default
and a fresh dict is falsy rather than an error.

RULE: if `self.<name>` is read in class A and `self.<name>` is never assigned
anywhere in class A (or its bases), that is a wrong-object read.
"""
import ast, sys, os, collections
_files = [a for a in sys.argv[1:] if not a.startswith('--')]
src = open(_files[0] if _files else
           os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'omega_v60_reconstructed.py'), encoding='utf-8').read()
tree = ast.parse(src)
classes = {c.name: c for c in ast.walk(tree) if isinstance(c, ast.ClassDef)}
bases = {c.name: [b.id for b in c.bases if isinstance(b, ast.Name)] for c in classes.values()}

assigned = collections.defaultdict(set)   # class -> {attr}
read = collections.defaultdict(set)       # class -> {(attr, line)}
for cname, c in classes.items():
    for node in ast.walk(c):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
           and node.value.id == 'self':
            if isinstance(node.ctx, ast.Store):
                assigned[cname].add(node.attr)
            elif isinstance(node.ctx, ast.Load):
                read[cname].add((node.attr, node.lineno))
    # getattr(self, 'name', default) is a READ, and in this codebase it is the
    # DOMINANT one -- which is precisely why these bugs are silent: getattr's
    # default turns a wrong-object read into a plausible value instead of an
    # AttributeError. A sweep that only sees `self.name` misses the whole class.
    for node in ast.walk(c):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'getattr' and node.args and \
           isinstance(node.args[0], ast.Name) and node.args[0].id == 'self' \
           and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
           and isinstance(node.args[1].value, str):
            read[cname].add((node.args[1].value, node.lineno))
    for node in ast.walk(c):
        # setattr(self, 'x', ...) counts as an assignment
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'setattr' and node.args and \
           isinstance(node.args[0], ast.Name) and node.args[0].id == 'self' \
           and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            assigned[cname].add(str(node.args[1].value))

# An attribute may legitimately be INJECTED from outside its class:
#     self.ta._bot_ref = self        TradingBot sets it on its OWN member
#     bot.portfolio._x = ...         startup code, at module level
# Both are wiring, and both are fine. What is NOT fine is assigning onto a
# LOCAL VARIABLE inside a method and then reading the same name off `self`
# somewhere else -- that is C464-6 exactly, and the earlier version of this
# sweep waved it through by treating every non-self target as injection.
# So: self-based targets and module-level targets are injection; a bare local
# name inside a method is not.
def _selfbased(node):
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id == 'self'

module_level = set()
def _walk_module_only(nodes):
    """Statements at module scope, NOT recursing into classes or functions.

    C464-6 FIX #2, found by testing the sweep against a deliberately broken
    copy: the first version called ast.walk() on each top-level node, which
    for a ClassDef means the WHOLE CLASS -- so every `<local>.attr = ...`
    inside any method was recorded as a module-level injection and waved
    through. The sweep reported CLEAN on a file with the bug re-inserted.
    A verification tool that cannot fail its own test is not a tool.
    """
    for node in nodes:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield node
        for field in ('body', 'orelse', 'finalbody'):
            sub = getattr(node, field, None)
            if isinstance(sub, list):
                yield from _walk_module_only(sub)
        for h in getattr(node, 'handlers', []) or []:
            yield from _walk_module_only(h.body)

for node in _walk_module_only(tree.body):
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        tg = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in tg:
            if isinstance(t, ast.Attribute):
                module_level.add(t.attr)

injected = set(module_level)
for node in ast.walk(tree):
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            if isinstance(t, ast.Attribute) and not (
                    isinstance(t.value, ast.Name) and t.value.id == 'self'):
                if _selfbased(t.value):
                    injected.add(t.attr)

def owns(cname, attr, seen=None):
    seen = seen or set()
    if cname in seen: return False
    seen.add(cname)
    if attr in assigned.get(cname, ()): return True
    if attr in {m.name for m in classes.get(cname, ast.ClassDef(body=[])).body
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}: return True
    for n in classes.get(cname).body if cname in classes else []:
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == attr:
            return True
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == attr: return True
    return any(owns(b, attr, seen) for b in bases.get(cname, []))

# Attributes inherited from a STDLIB base this sweep cannot see (the classes
# here subclass http.server.BaseHTTPRequestHandler and threading.Thread).
# Named explicitly rather than silently widened, so the list stays auditable.
STDLIB_BASE = {'path', 'headers', 'rfile', 'wfile', 'command', 'client_address',
               'server', 'requestline', 'request_version', 'connection',
               'daemon', 'name', 'ident'}

bad = []
for cname, items in read.items():
    for attr, line in sorted(items):
        if attr.startswith('__'): continue
        if attr in injected or attr in STDLIB_BASE: continue
        if not owns(cname, attr):
            # Report even when NO class assigns it via self -- that is the
            # C464-6 shape exactly: written only as `<local>.attr = ...` and
            # read as `self.attr`, so it is owned by nobody and silently empty.
            other = [c for c in classes if attr in assigned.get(c, ())]
            bad.append((cname, attr, line, other or ['<never assigned via self>']))
lines = sorted(f"  self.{a} read in {c} (line {l}) but only assigned in {o}"
               for c, a, l, o in bad)
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.wrongobj_baseline')
if '--baseline' in sys.argv:
    open(BASE, 'w').write('\n'.join(lines))
    print(f"baseline written: {len(lines)} findings")
    sys.exit(0)
if '--diff' in sys.argv:
    try:
        old = set(l.split(' (line ')[0] for l in open(BASE).read().split('\n') if l.strip())
    except Exception:
        old = set()
    new = [l for l in lines if l.split(' (line ')[0] not in old]
    if new:
        print(f"NEW WRONG-OBJECT READS SINCE THE BASELINE: {len(new)}")
        for l in new: print(l)
        sys.exit(1)
    print(f"no new wrong-object reads ({len(lines)} known, baselined)")
    sys.exit(0)
if bad:
    print(f"WRONG-OBJECT READS: {len(bad)}")
    for cname, attr, line, other in bad[:30]:
        print(f"  self.{attr} read in {cname} (line {line}) but only assigned in {other}")
else:
    print("cross-class instance-attribute sweep: CLEAN")
