"""C466 safety: colour on the console, NEVER in the files, width never changed."""
import ast, logging, os, sys, time, threading, re
from datetime import datetime
src=open('/home/user/tradecode/omega_v60_reconstructed.py',encoding='utf-8').read()
t=ast.parse(src)
want_n={'CustomLogger','_c465_flagged','_c463_is_report','_C460ConsoleFilter',
        '_C460Verbose','_C463Formatter','_c462_width','_C462Report','_c462_money',
        '_c462_spark','_c462_bar','_c465_gauge','_c466_paint','_c466_resolve'}
want_a={'_C466_PALETTES','_C466_RESET','_C466_STRIP','_C466_TOKENS'}
nodes=[]
for n in t.body:
    if getattr(n,'name',None) in want_n: nodes.append(n)
    elif isinstance(n,ast.Assign):
        for tg in n.targets:
            if isinstance(tg,ast.Name) and tg.id in want_a: nodes.append(n)
g={'logging':logging,'os':os,'sys':sys,'re':re,'time':time,
   'threading':threading,'datetime':datetime}
g['_fmt_px']=lambda p,**k: str(p)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<f>','exec'),g)
g['cfg_console_verbose']=g['_C460Verbose']()
for fn in (g['_C460ConsoleFilter'].filter, g['_C463Formatter'].format):
    fn.__globals__.update({k:g[k] for k in
        ('cfg_console_verbose','_c465_flagged','_c463_is_report','_c466_paint',
         '_C466_PALETTES','_C466_RESET','_C466_STRIP','_C466_TOKENS')})

log=g['CustomLogger']('t466'); g['logger']=log
log.logger.handlers.clear()
console=[]; filelines=[]
class Cap(logging.Handler):
    def __init__(self, sink): super().__init__(); self.sink=sink
    def emit(self, rec): self.sink.append(self.format(rec))
pal=g['_C466_PALETTES']['classic']
hc=Cap(console); hc.addFilter(g['_C460ConsoleFilter']())
hc.setFormatter(g['_C463Formatter']('%(asctime)s | %(message)s',datefmt='%H:%M:%S',
                                    wrap=True, palette=pal))
hf=Cap(filelines)
hf.setFormatter(g['_C463Formatter']('%(asctime)s | %(message)s',datefmt='%H:%M:%S',
                                    wrap=True, palette=None))   # file = never painted
log.logger.addHandler(hc); log.logger.addHandler(hf)

os.environ['OMEGA_LOG_WIDTH']='44'
rep=g['_C462Report']('/tmp/claude-0/t466.log')
for fn in (g['_C460ConsoleFilter'].filter, g['_C463Formatter'].format):
    fn.__globals__['_c462_report']=rep
rep.set_glyphs('ascii')
rep.header('C466','PAPER',250.00,day_barrier=0.68)
rep.note_open('UNI/USDT:USDT','long',7.4210,3.2,24.00,1,9.9,2.9,0.70,maker=True,fee=0.005)
rep.note_close('UNI/USDT:USDT','long',7.4210,7.7180,4.00,0.48,'EARLY_PEAK_CAPTURE',18.0,
               equity=250.82,maker=True,fee=0.005,r_mult=1.03,peak_pct=4.92)
rep.note_close('ZEC/USDT:USDT','long',55.0,54.2,-1.45,-0.44,'C377_HARD_STOP',38.0,
               equity=250.38,maker=False,fee=0.02,r_mult=-0.75,peak_pct=0.31)
log.info("⚠️ C378 stop level recorded")

ESC=re.compile(r'\x1b\[')
print("A. THE FILES MUST CONTAIN NO ESCAPE CODES")
rf=open('/tmp/claude-0/t466.log',encoding='utf-8').read()
print(f"   omega_report file       : {len(ESC.findall(rf))} escapes  "
      f"{'OK' if not ESC.search(rf) else '*** LEAK ***'}")
nf=sum(len(ESC.findall(l)) for l in filelines)
print(f"   session/detail handler  : {nf} escapes  {'OK' if nf==0 else '*** LEAK ***'}")
nc=sum(len(ESC.findall(l)) for l in console)
print(f"   console handler         : {nc} escapes  {'OK (painted)' if nc else '*** NOT PAINTED ***'}")

print("\nB. PAINTING MUST NOT CHANGE VISIBLE WIDTH")
strip=g['_C466_STRIP']; bad=0
for c in console:
    for row in c.split('\n'):
        if len(strip.sub('', row)) > 44 + 12:   # +12 allows the timestamp prefix
            bad+=1
print(f"   rows whose visible width grew: {bad}  {'OK' if bad==0 else 'FAIL'}")

print("\nC. WHAT THE CONSOLE ACTUALLY SHOWS")
for c in console[:14]:
    print("   " + c)
