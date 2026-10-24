import re, json, sys
L='/root/.claude/uploads/181034ad-5716-5207-b4c2-0e80567df12e/9fb5254b-omega_detail_20260916_123947.log'
lines=open(L,encoding='utf-8',errors='replace').read().split('\n')

# scan boundaries
starts=[i for i,l in enumerate(lines) if 'STEP 1: SCREENING' in l]
ends=[i for i,l in enumerate(lines) if 'Step 3 result' in l]

def scan_block(k):
    s=starts[k]
    e=next(x for x in ends if x>s)
    return lines[s:e+1]

SYM=re.compile(r'\|\s+(?:\S+\s)?([A-Z0-9]{2,12}):\s')
def parse(block):
    pairs={}
    for l in block:
        m=re.search(r'\|\s+\S+\s+([A-Z0-9]{2,14}):\s(.*)$', l)
        if not m: continue
        sym, rest = m.group(1), m.group(2)
        d=pairs.setdefault(sym, {'sym':sym,'dir':None,'reason':None,'score':None,'conf':None,'notes':[]})
        for k,v in (('long','long'),('LONG','long'),('short','short'),('SHORT','short')):
            if re.search(r'\b'+k+r'\b', rest): d['dir']=d['dir'] or v
        mm=re.search(r'(long|short)\s+(?:post-penalty\s+)?scr=([\d.]+)\s+conf=([\d.]+)\s+→\s+(.*)$', rest)
        if mm:
            d['dir']=mm.group(1); d['score']=float(mm.group(2)); d['conf']=float(mm.group(3))
            d['reason']=mm.group(4).strip()
        mm=re.search(r'(long|short)\s+post-penalty score ([\d.]+) < ([\d.]+)', rest)
        if mm:
            d['dir']=mm.group(1); d['score']=float(mm.group(2))
            d['reason']=f'post-penalty {mm.group(2)} < {mm.group(3)}'
        if '→ blocked' in rest or 'BLOCKED' in rest:
            d['reason']=d['reason'] or rest.split('→')[0].strip()[:60]
        if 'session left' in rest:
            d['reason']=d['reason'] or 'session_short'
        d['notes'].append(rest[:70])
    return pairs

out={}
for k in range(len(starts)):
    b=scan_block(k)
    t=b[0][:8]
    out[t]=parse(b)
    if k==0:
        p=out[t]
        print(f"scan 1 @ {t} IST — {len(p)} pairs seen in the per-pair stream")
        scored=[v for v in p.values() if v['score'] is not None]
        print(f"  with an explicit score+refusal: {len(scored)}")
json.dump(out, open('/tmp/claude-0/scans.json','w'))
print("scans captured:", len(out), "->", list(out)[:4], '...')
