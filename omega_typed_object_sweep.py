#!/usr/bin/env python3
"""C483: TYPED wrong-object sweep.

The C464-6 sweep is a diff tool with ~99 accepted baseline findings, because
this codebase decorates objects from outside (pos.X = ... in TradingBot, read as
self.X in Position). That baseline ABSORBED real bugs: _guardian_peak_mult (set
on the bot, read from a Position) sat in it for weeks. This sweep infers the
CLASS of every assignment receiver (pos -> Position, bot/bot_ref -> TradingBot,
cfg -> Config, ...) and flags a self.X read in class C only when NO writer could
be a C. It found five real defects at C483 on its first run.

    python3 omega_typed_object_sweep.py

Handler.* findings are BaseHTTPRequestHandler inherits -- expected.
"""
import ast, io, re, collections
src=io.open('/home/user/tradecode/omega_v60_reconstructed.py',encoding='utf-8').read()
tree=ast.parse(src)
classes={n.name:n for n in ast.walk(tree) if isinstance(n,ast.ClassDef)}
_nl=src.count('\n')+2
_OWN=[None]*_nl
for n in sorted(classes.values(), key=lambda n:n.lineno):   # inner classes overwrite outer
    for i in range(n.lineno, n.end_lineno+1): _OWN[i]=n.name
def owner_of(lineno): return _OWN[lineno]
RECV={  # receiver source text -> class
 r'^(self\.)?(bot|_bot|bot_ref|_bot_ref|self\.bot|bot_ref\[0\])$':'TradingBot',
 r'^(pos|_pos|p|position|_p|pos_|_pos\d+|self\.pos|_position)$':'Position',
 r'^(self\.portfolio|pf|portfolio|_pf|self\.bot\.portfolio|bot\.portfolio|bot_ref\.portfolio)$':'Portfolio',
 r'^(self\.cfg|cfg|c|_cfg|self\.bot\.cfg|bot\.cfg|bot_ref\.cfg|self\.config|config)$':'Config',
 r'^(self\.mode_mgr|mode_mgr|self\.bot\.mode_mgr|bot\.mode_mgr|bot_ref\.mode_mgr)$':'TradingModeManager',
 r'^(self\.exchange|exchange|self\.bot\.exchange|bot\.exchange)$':'ExchangeManager',
 r'^(self\.guardian|guardian)$':'OmegaGuardian',
 r'^(self\.news|news)$':'NewsAnalyzer',
}
def recv_class(node, here):
    txt=ast.unparse(node)
    if txt=='self': return here
    for pat,c in RECV.items():
        if re.match(pat,txt): return c
    return '?'
reads=collections.defaultdict(list)      # (class, attr) -> [lines]
assigns=collections.defaultdict(set)     # attr -> {writer classes}
self_assign=collections.defaultdict(set) # class -> {attr}
for node in ast.walk(tree):
    if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store):
        here=owner_of(node.lineno); rc=recv_class(node.value, here)
        assigns[node.attr].add(rc)
        if rc==here: self_assign[here].add(node.attr)
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='setattr' and len(node.args)>=2:
        if isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str):
            here=owner_of(node.lineno); rc=recv_class(node.args[0],here)
            assigns[node.args[1].value].add(rc)
            if rc==here: self_assign[here].add(node.args[1].value)
    # reads on self
    if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Load) and isinstance(node.value,ast.Name) and node.value.id=='self':
        reads[(owner_of(node.lineno),node.attr)].append(node.lineno)
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('getattr','hasattr') and len(node.args)>=2:
        a0=node.args[0]
        if isinstance(a0,ast.Name) and a0.id=='self' and isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str):
            reads[(owner_of(node.lineno),node.args[1].value)].append(node.lineno)
# methods / class attrs count as defined
defined=collections.defaultdict(set)
for cn,cnode in classes.items():
    for b in cnode.body:
        if isinstance(b,(ast.FunctionDef,ast.AsyncFunctionDef)): defined[cn].add(b.name)
        if isinstance(b,ast.Assign):
            for t in b.targets:
                if isinstance(t,ast.Name): defined[cn].add(t.id)
        if isinstance(b,ast.AnnAssign) and isinstance(b.target,ast.Name): defined[cn].add(b.target.id)
bases={cn:[x.id for x in c.bases if isinstance(x,ast.Name)] for cn,c in classes.items()}
def has(cn,attr,seen=()):
    if cn is None or cn in seen: return False
    if attr in self_assign[cn] or attr in defined[cn]: return True
    return any(has(b,attr,seen+(cn,)) for b in bases.get(cn,[]))
never=[]; wrong=[]
for (cn,attr),lines in sorted(reads.items(), key=lambda kv:kv[1][0]):
    if cn is None or attr.startswith('__') or has(cn,attr): continue
    w=assigns.get(attr,set())
    if not w: never.append((cn,attr,lines))
    elif cn not in w and '?' not in w: wrong.append((cn,attr,lines,sorted(w)))
print(f"A. read on self in class C, assigned NOWHERE in the file ({len(never)}):")
for cn,attr,l in never: print(f"   {cn:18} {attr:34} lines {l[:4]}")
print(f"\nB. read on self in class C, but every writer is ANOTHER class ({len(wrong)}):")
for cn,attr,l,w in wrong: print(f"   {cn:18} {attr:34} read {l[:3]}  written on {w}")
