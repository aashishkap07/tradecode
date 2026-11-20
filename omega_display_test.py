"""Does an ASCII report line still reach the screen? It has no glyph left."""
import ast, logging, os, sys, time, threading
from datetime import datetime
src=open('/home/user/tradecode/omega_v60_reconstructed.py',encoding='utf-8').read()
t=ast.parse(src)
# C467-C: _c466_paint and _c466_resolve were added by C466 and never added to
# this list, so _C463Formatter.format raised NameError and this harness has not
# actually run since C466 shipped. A verification tool that cannot run is not a
# tool (standing rule 16) -- and it silently stopped being one the moment
# colour was introduced, which is exactly the failure mode it exists to catch.
want={'CustomLogger','_c465_flagged','_c463_is_report','_C460ConsoleFilter',
      '_C460Verbose','_C463Formatter','_c462_width','_C462Report','_c462_money',
      '_c462_spark','_c462_bar','_c465_gauge','_c466_paint','_c466_resolve',
      '_c467_ruler'}
nodes=[n for n in t.body if getattr(n,'name',None) in want]
missing = want - {getattr(n,'name',None) for n in nodes}
assert not missing, missing
g={'logging':logging,'os':os,'time':time,'threading':threading,'datetime':datetime,
   're':__import__('re'),'sys':sys,'shutil':__import__('shutil'),
   '_C466_RESET':'\033[0m','_C466_STRIP':__import__('re').compile(r'\x1b\[[0-9;]*m'),
   '_c467_cfg_ref':[None]}
# the module-level regex/palette tables C466 compiles at import time
import re as _re_
for _blk in ('_C466_PALETTES','_C466_TOKENS'):
    _m=_re_.search(r'^'+_blk+r'\s*=.*?(?=\n[A-Za-z_]|\n\n\n)',src,_re_.M|_re_.S)
    if _m: exec(compile(_m.group(0),_blk,'exec'),g)
g['_fmt_px']=lambda p,**k: str(p)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<f>','exec'),g)
g['cfg_console_verbose']=g['_C460Verbose']()
for fn in (g['_C460ConsoleFilter'].filter, g['_C463Formatter'].format,
           g['_c466_paint'], g['_C462Report']._emit):
    fn.__globals__.update({'cfg_console_verbose':g['cfg_console_verbose'],
                           '_c465_flagged':g['_c465_flagged'],
                           '_c463_is_report':g['_c463_is_report'],
                           '_c466_paint':g['_c466_paint'],
                           '_c467_cfg_ref':g['_c467_cfg_ref'],
                           '_C466_RESET':g['_C466_RESET'],
                           '_C466_STRIP':g['_C466_STRIP'],
                           '_C466_PALETTES':g.get('_C466_PALETTES'),
                           '_C466_TOKENS':g.get('_C466_TOKENS')})

# a real CustomLogger with a capturing handler behind the real filter
log = g['CustomLogger']('t465')
g['logger']=log
captured=[]
class Cap(logging.Handler):
    def emit(self, rec):
        captured.append(self.format(rec))
log.logger.handlers.clear()
h=Cap(); h.addFilter(g['_C460ConsoleFilter']())
h.setFormatter(g['_C463Formatter']('%(asctime)s | %(message)s', datefmt='%H:%M:%S', wrap=True))
log.logger.addHandler(h)

os.environ['OMEGA_LOG_WIDTH']='44'
# C467-C: TRUNCATE FIRST. The reporter APPENDS, so without this the "written"
# count accumulated across every previous run of this harness while the
# "reached the screen" count was per-run -- and the harness therefore reported
# a growing "lost: N" that was pure arithmetic, not a real loss. A test that
# manufactures its own failures is worse than no test.
_LOGP='/tmp/claude-0/t465.log'
try: os.remove(_LOGP)
except OSError: pass
rep=g['_C462Report'](_LOGP)
for fn in (g['_C460ConsoleFilter'].filter, g['_C463Formatter'].format,
           g['_c466_paint'], g['_C462Report']._emit):
    fn.__globals__['_c462_report']=rep
rep.set_glyphs('ascii')
rep.header('C465','PAPER',250.00,day_barrier=0.68)
rep.risk_frame({'equity':250.0,'cap_pct':0.68,'per_trade_pct':0.341,'dd_pct':15,'max_trades':4},
               edge=0.059, markets=790, payoff=0.78)
rep.note_open('UNI/USDT:USDT','long',7.4210,3.2,24.00,1,9.9,2.9,0.70,maker=True,fee=0.005)
rep.note_close('UNI/USDT:USDT','long',7.4210,7.7180,4.00,0.48,'EARLY_PEAK_CAPTURE',18.0,
               equity=250.82,maker=True,fee=0.005,r_mult=1.03,peak_pct=4.92,info=0.31)
n_written = sum(1 for _ in open(_LOGP))
print(f"  report lines written to the file : {n_written}")
print(f"  report lines that reached the screen: {len(captured)}")
print(f"  lost: {max(0, n_written - len(captured))}")
print()
print("  and a report line carries NO timestamp (the block header has it):")
for c in captured[:4]: print("   ", repr(c))
print()
print("  ordinary log lines still get their stamp and still filter normally:")
log.info("\U0001f4ca Step 3 result: 127 analyzed -> 0 passed")
log.info("   \U0001f9ec SOMEPAIR: per-pair working that must NOT reach the screen")
log.info("⚠️ something failed")
for c in captured[-3:]: print("   ", repr(c[:70]))
