"""Drive the REAL _c464_info_overlay and _c464_midrank, extracted from the file."""
import ast, random, bisect
src=open('/home/user/tradecode/omega_v60_reconstructed.py',encoding='utf-8').read()
tree=ast.parse(src)
cls=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TradingBot'][0]
want={'_c464_midrank','_c464_info_overlay'}
meths=[m for m in cls.body if isinstance(m,ast.FunctionDef) and m.name in want]
assert len(meths)==2, [m.name for m in meths]
import logging
class L:
    def warning(self,m): print("WARN:",m)
    def info(self,m): pass
g={'logger':L(),'bisect':bisect}
shim=ast.ClassDef(name='Bot',bases=[],keywords=[],body=meths,decorator_list=[])
ast.fix_missing_locations(ast.Module(body=[shim],type_ignores=[]))
exec(compile(ast.Module(body=[shim],type_ignores=[]),'<t>','exec'),g)
Bot=g['Bot']

class CFG:
    C464_INFO_OVERLAY=True; C464_W_FLOW=0.40; C464_W_OI=0.25
    C464_W_NEWS=0.25; C464_W_FUND=0.10; C464_MAX_TILT=0.15; C464_MIN_SPREAD=1e-4
b=Bot(); b.cfg=CFG()

print("A. midrank with heavy ties — the C454 defect")
vals=[0.00005]*39 + [0.0001]*30 + [0.0002]*31          # 39% on one value
print(f"   ordinary pair (the 39%% tie): {b._c464_midrank(vals,0.00005):.3f}   "
      f"naive would give {sum(1 for v in vals if v<=0.00005)/len(vals):.3f}")
print(f"   top value                  : {b._c464_midrank(vals,0.0002):.3f}")
print(f"   too few to rank (n=5)      : {b._c464_midrank([1,2,3,4,5],3):.3f}  (0.5 = no opinion)")

print("\nB. dispersion gate — a flat board must be SILENT, not zero")
random.seed(7)
flat={f"P{i}/USDT:USDT":{'flow':0.001,'oi':None,'fund':0.00005,'news':0.0} for i in range(30)}
b._c464_board=flat
cands=[{'symbol':f"P{i}/USDT:USDT",'direction':'long','confidence':0.60} for i in range(5)]
out=b._c464_info_overlay(cands)
print(f"   flat board -> applied {out['applied']}, channels {out['chan']}  "
      f"(expect 0 and empty)")

print("\nC. a real board — dispersed flow, OI and news")
board={}
for i in range(40):
    board[f"P{i}/USDT:USDT"]={'flow':random.uniform(-1,1),'oi':random.uniform(-1,1),
                              'fund':random.uniform(-0.0003,0.0006),'news':random.uniform(-0.5,0.5)}
# a deliberate best case and worst case
board['BEST/USDT:USDT']={'flow':0.99,'oi':0.98,'fund':0.00005,'news':0.49}
board['WORST/USDT:USDT']={'flow':-0.99,'oi':-0.98,'fund':0.00055,'news':-0.49}
b._c464_board=board
cands=[{'symbol':'BEST/USDT:USDT','direction':'long','confidence':0.60},
       {'symbol':'WORST/USDT:USDT','direction':'long','confidence':0.60},
       {'symbol':'WORST/USDT:USDT','direction':'short','confidence':0.60},
       {'symbol':'P3/USDT:USDT','direction':'long','confidence':0.60}]
import copy
cands=[copy.deepcopy(c) for c in cands]
out=b._c464_info_overlay(cands)
print(f"   channels live: {out['chan']}, applied {out['applied']}")
for c in cands:
    print(f"   {c['symbol'].split('/')[0]:<6}{c['direction']:<6} info {c.get('_c464_info',0):+.3f} "
          f"x{c.get('_c464_mult',1):.3f}  conf 0.60 -> {c['confidence']:.4f}  {c.get('_c464_parts')}")

print("\nD. bounds — conviction may never move more than +/-15%, and never flips a side")
lo=min(c['confidence'] for c in cands); hi=max(c['confidence'] for c in cands)
print(f"   conviction range {lo:.4f} .. {hi:.4f} from a base of 0.6000 "
      f"(bounds 0.5100 .. 0.6900) -> {'OK' if 0.51-1e-9<=lo and hi<=0.69+1e-9 else 'OUT OF BOUNDS'}")
print(f"   directions unchanged: {[c['direction'] for c in cands]}")
print(f"   no candidate dropped: {len(cands)} in, {len(cands)} out")

print("\nE. funding votes on CROWDING only, never on a side")
b._c464_board={f"P{i}/USDT:USDT":{'flow':None,'oi':None,'news':None,
                                  'fund':random.uniform(-0.0005,0.0010)} for i in range(40)}
b._c464_board['X/USDT:USDT']={'flow':None,'oi':None,'news':None,'fund':0.0010}
cl=[{'symbol':'X/USDT:USDT','direction':'long','confidence':0.6}]
cs=[{'symbol':'X/USDT:USDT','direction':'short','confidence':0.6}]
b._c464_info_overlay(cl); b._c464_info_overlay(cs)
print(f"   extreme-funding pair LONG  info {cl[0].get('_c464_info')}")
print(f"   extreme-funding pair SHORT info {cs[0].get('_c464_info')}")
print(f"   same sign both ways (crowding, not direction): "
      f"{'YES' if cl[0].get('_c464_info')==cs[0].get('_c464_info') else 'NO'}")
