import json,time,urllib.request,urllib.parse
def get(u):
    req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())
bn=[s['symbol'][:-4] for s in get('https://www.binance.com/fapi/v1/exchangeInfo')['symbols'] if s.get('contractType')=='PERPETUAL' and s['symbol'].endswith('USDT')]
dl=get('https://api.india.delta.exchange/v2/products?contract_types=perpetual_futures&states=live')['result']
delta={p['underlying_asset']['symbol'] for p in dl if (p.get('settling_asset') or {}).get('symbol')=='USD'}
cands=sorted(set(bn)|delta)
now=int(time.time()); s=now-3*3600; e=s+60
have=set()
for i in range(0,len(cands),25):
    chunk=cands[i:i+25]
    q=','.join(c+'/USDT' for c in chunk)
    try:
        d=get('https://trade.mudrex.com/fapi/v1/price/kline?'+urllib.parse.urlencode({'assets':q,'aggregation':'1m','start_time':s,'end_time':e},safe='/,'))
        for k,v in (d.get('data') or {}).get('asset_ticks',{}).items():
            if v: have.add(k.split('/')[0].upper())
    except Exception as ex:
        # one bad symbol may fail the chunk: retry one by one
        for c in chunk:
            try:
                d=get('https://trade.mudrex.com/fapi/v1/price/kline?'+urllib.parse.urlencode({'assets':c+'/USDT','aggregation':'1m','start_time':s,'end_time':e},safe='/,'))
                if (d.get('data') or {}).get('asset_ticks',{}).get(c.lower()+'/usdt'): have.add(c)
            except Exception: pass
    time.sleep(0.25)
print('candidates',len(cands),'binance',len(bn),'delta',len(delta))
print('mudrex has',len(have),'| on Delta too',len(have&delta),'| on Binance too',len(have&set(bn)))
json.dump(sorted(have),open(__import__('sys').argv[1],'w'))
