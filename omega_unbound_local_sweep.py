"""Sweep: a name read before its local assignment (UnboundLocalError class).

C485 found compute_pressure_exhaustion dead since C432-3: a nested _zig()
gained `atr_abs = max(...)`, which made atr_abs LOCAL to _zig, so the line
above it that READ the enclosing atr_abs raised UnboundLocalError on every
call -- and a bare `except: pass` turned the crash into plausible defaults.
Python only reports this at run time, and only if nothing swallows it.

This walks every function scope (comprehensions are their own scopes), finds
names that are local to it (any binding: assignment, augmented assignment,
for/with/except targets, import, def/class, walrus) and reports every LOAD of
such a name that comes, in source order, before the name's first binding in
that scope -- with `x += 1` on a never-bound x counted as a read.
'shadow' = the same name is bound in an enclosing function or at module level
(the author very likely meant that one: the C432-3 shape).  Loops can make a
positional 'before' legitimate (read on iteration 2 of a value bound at the end
of iteration 1), so 'loop' findings are listed separately for a human to judge.
Exit 1 if any 'shadow' finding exists outside a loop.
"""
import ast, sys

PATH = sys.argv[1] if len(sys.argv) > 1 else 'omega_v60_reconstructed.py'
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def pos(n):
    return (getattr(n, 'lineno', 0), getattr(n, 'col_offset', 0))


class Scope:
    def __init__(self, node, parent):
        self.node, self.parent = node, parent
        self.binds = {}          # name -> first binding position
        self.loads = []          # (name, position, in_loop)
        self.declared = set()    # global / nonlocal


def walk_scope(scope, body_nodes, all_scopes, loop_depth=0):
    for node in body_nodes:
        visit(scope, node, all_scopes, loop_depth)


def bind(scope, name, p):
    if name not in scope.binds or p < scope.binds[name]:
        scope.binds[name] = p


def bind_target(scope, t, p):
    if isinstance(t, ast.Name):
        bind(scope, t.id, p)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            bind_target(scope, e, p)
    elif isinstance(t, ast.Starred):
        bind_target(scope, t.value, p)
    # attribute / subscript targets bind nothing locally (but load their base)


def visit(scope, node, all_scopes, loop_depth):
    if isinstance(node, SCOPES):
        # defaults / decorators evaluate in the ENCLOSING scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bind(scope, node.name, pos(node))
            for d in node.decorator_list + node.args.defaults + [x for x in node.args.kw_defaults if x]:
                visit(scope, d, all_scopes, loop_depth)
        elif isinstance(node, ast.Lambda):
            for d in node.args.defaults + [x for x in node.args.kw_defaults if x]:
                visit(scope, d, all_scopes, loop_depth)
        child = Scope(node, scope)
        all_scopes.append(child)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in a.posonlyargs + a.args + a.kwonlyargs + ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else []):
                bind(child, arg.arg, (0, 0))
            body = node.body if isinstance(node.body, list) else [node.body]
            walk_scope(child, body, all_scopes)
        else:   # comprehension: first iterator is evaluated in the enclosing scope
            gens = node.generators
            visit(scope, gens[0].iter, all_scopes, loop_depth)
            for k, g in enumerate(gens):
                if k:
                    visit(child, g.iter, all_scopes, 1)
                bind_target(child, g.target, (0, 0))
                for c in g.ifs:
                    visit(child, c, all_scopes, 1)
            elts = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            for e in elts:
                visit(child, e, all_scopes, 1)
        return
    if isinstance(node, ast.ClassDef):
        bind(scope, node.name, pos(node))
        for d in node.decorator_list + node.bases:
            visit(scope, d, all_scopes, loop_depth)
        cls = Scope(node, scope)          # class bodies do not enclose methods,
        cls.is_class = True               # but they are scanned for their own defs
        all_scopes.append(cls)
        walk_scope(cls, node.body, all_scopes)
        return
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        scope.declared.update(node.names)
        return
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            visit(scope, node.iter, all_scopes, loop_depth)
            bind_target(scope, node.target, pos(node.target))
        else:
            visit(scope, node.test, all_scopes, loop_depth + 1)
        for n in node.body + node.orelse:
            visit(scope, n, all_scopes, loop_depth + 1)
        return
    if isinstance(node, ast.AugAssign):
        if isinstance(node.target, ast.Name):
            scope.loads.append((node.target.id, pos(node.target), loop_depth > 0))
        visit(scope, node.value, all_scopes, loop_depth)
        bind_target(scope, node.target, pos(node.target))
        if not isinstance(node.target, ast.Name):
            visit(scope, node.target, all_scopes, loop_depth)
        return
    if isinstance(node, ast.Assign):
        visit(scope, node.value, all_scopes, loop_depth)
        for t in node.targets:
            bind_target(scope, t, pos(t))
            if not isinstance(t, (ast.Name, ast.Tuple, ast.List)):
                visit(scope, t, all_scopes, loop_depth)
        return
    if isinstance(node, ast.AnnAssign):
        if node.value is not None:
            visit(scope, node.value, all_scopes, loop_depth)
            bind_target(scope, node.target, pos(node.target))
        return
    if isinstance(node, ast.NamedExpr):
        visit(scope, node.value, all_scopes, loop_depth)
        bind(scope, node.target.id, pos(node.target))
        return
    if isinstance(node, (ast.With, ast.AsyncWith)):
        for it in node.items:
            visit(scope, it.context_expr, all_scopes, loop_depth)
            if it.optional_vars is not None:
                bind_target(scope, it.optional_vars, pos(it.optional_vars))
        for n in node.body:
            visit(scope, n, all_scopes, loop_depth)
        return
    if isinstance(node, ast.ExceptHandler):
        if node.type is not None:
            visit(scope, node.type, all_scopes, loop_depth)
        if node.name:
            bind(scope, node.name, pos(node))
        for n in node.body:
            visit(scope, n, all_scopes, loop_depth)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            bind(scope, (a.asname or a.name).split('.')[0], pos(node))
        return
    if isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Load):
            scope.loads.append((node.id, pos(node), loop_depth > 0))
        elif isinstance(node.ctx, ast.Store):
            bind(scope, node.id, pos(node))
        return
    for child in ast.iter_child_nodes(node):
        visit(scope, child, all_scopes, loop_depth)


def main():
    tree = ast.parse(open(PATH, encoding='utf-8').read())
    mod = Scope(tree, None)
    scopes = [mod]
    walk_scope(mod, tree.body, scopes)
    shadow, loop, plain = [], [], []
    for sc in scopes:
        if sc is mod or getattr(sc, 'is_class', False):
            continue
        for name, p, in_loop in sc.loads:
            if name in sc.declared or name not in sc.binds:
                continue
            if p >= sc.binds[name]:
                continue
            # bound in an enclosing FUNCTION scope or at module level?
            enc, up = False, sc.parent
            while up is not None:
                if not getattr(up, 'is_class', False) and name in up.binds:
                    enc = True
                    break
                up = up.parent
            where = getattr(sc.node, 'name', type(sc.node).__name__)
            rec = (p[0], where, name, sc.binds[name][0])
            (loop if in_loop else (shadow if enc else plain)).append(rec)
    for title, rows in (('SHADOW (reads a name an enclosing scope binds, before binding it locally)', shadow),
                        ('PLAIN (read before any binding in the same scope)', plain),
                        ('LOOP (positional-before inside a loop: may be legitimate)', loop)):
        rows = sorted(set(rows))
        print(f'\n{title}: {len(rows)}')
        for ln, where, name, bl in rows[:60]:
            print(f'  line {ln:>6}  in {where:<34} reads {name!r:<24} first bound at line {bl}')
    sys.exit(1 if shadow else 0)


if __name__ == '__main__':
    main()
