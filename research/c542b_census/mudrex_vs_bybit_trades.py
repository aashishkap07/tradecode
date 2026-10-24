import gzip,csv,json,sys,urllib.request
def get(u):
    req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())
D=sys.argv[1]; day0=1791331200  # 2026-10-07 00:00 UTC; D/bybit_dump/ holds public.bybit.com/trading/<C>USDT/<C>USDT2026-10-07.csv.gz
for c in sys.argv[2].split(','):
    by={}; byv={}
    with gzip.open(f'{D}/bybit_dump/{c}USDT2026-10-07.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            m=int(float(r['timestamp']))//60*60; by[m]=float(r['price']); byv[m]=byv.get(m,0)+float(r['size'])
    s=day0+6*3600; e=s+3*3600
    md=get(f"https://trade.mudrex.com/fapi/v1/price/kline?assets={c}/USDT&aggregation=1m&start_time={s}&end_time={e}")
    rows=md['data']['asset_ticks'][c.lower()+'/usdt']
    mc={int(k[0]):float(k[4]) for k in rows}; mv={int(k[0]):float(k[5]) for k in rows if len(k)>5}
    bn={int(k[0])//1000:(float(k[4]),float(k[5])) for k in get(f"https://www.binance.com/fapi/v1/klines?symbol={c}USDT&interval=1m&startTime={s*1000}&endTime={e*1000}&limit=1000")}
    ok={}
    for after in range(e+60, s, -100*60):
        for k in get(f"https://www.okx.com/api/v5/market/history-candles?instId={c}-USDT-SWAP&bar=1m&after={after*1000}&limit=100")['data']:
            ok[int(k[0])//1000]=float(k[4])
    print('==',c,'mudrex minutes',len(mc),'example row',rows[0])
    for name,src in [('bybit',by),('binance',{t:v[0] for t,v in bn.items()}),('okx',ok)]:
        ts=[t for t in mc if t in src]
        eq=sum(1 for t in ts if abs(mc[t]-src[t])<1e-12)
        print(f'  close == {name:8s}: {eq}/{len(ts)}')
    ts=[t for t in mv if t in byv]
    if ts:
        r=[mv[t]/byv[t] for t in ts if byv[t]>0]; r.sort(); print('  mudrex vol / bybit vol median',round(r[len(r)//2],4))
        r=[mv[t]/bn[t][1] for t in ts if t in bn and bn[t][1]>0]; r.sort(); print('  mudrex vol / binance vol median',round(r[len(r)//2],4))
